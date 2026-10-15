"""paper-link: attach the deck's obsidian:// link to the Zotero item."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import quote

from . import keystore, zotero
from .config import ConfigError, Vault, resolve_vault
from .keystore import KeystoreError
from .note import _SAFE_CITEKEY, NOTE_DIR
from .zotero import Paper, ZoteroError, resolve_citekey

# Reading back is cheap; writes may be slow while the authorization dialog is up.
WRITE_TIMEOUT = 20.0
AUTH_TIMEOUT = 120.0
VERIFY_ATTEMPTS = 5
VERIFY_INTERVAL = 1.0
ATTACHMENT_TITLE = "Obsidian deck"


def deck_uri(vault: Vault, citekey: str) -> str:
    """``obsidian://open`` URI of the deck (vault-relative path, no extension)."""
    rel = (NOTE_DIR / citekey).as_posix()
    return f"obsidian://open?vault={quote(vault.name)}&file={quote(rel)}"


def _library_path(paper: Paper) -> str:
    return "users/0" if paper.library == "library" else paper.library


class LocalApi:
    """Minimal client for the Zotero local API (``/api``)."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or zotero.BASE_URL
        self._server_id: str | None = None

    def _open(self, req: urllib.request.Request, timeout: float):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            err = ZoteroError(f"{req.method} {req.full_url}: HTTP {e.code}")
            err.status = e.code  # type: ignore[attr-defined]
            raise err from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ZoteroError(f"{req.method} {req.full_url}: {e}") from e

    def get(self, path: str) -> object:
        req = urllib.request.Request(
            self.base_url + path, headers={"Zotero-API-Version": "3"}
        )
        with self._open(req, zotero.TIMEOUT) as resp:
            self._server_id = resp.headers.get("Zotero-Server-ID") or self._server_id
            try:
                return json.load(resp)
            except json.JSONDecodeError as e:
                raise ZoteroError(f"GET {path}: invalid JSON") from e

    def server_id(self) -> str:
        if self._server_id is None:
            self.get("/api/users/0/items?limit=1")
        if not self._server_id:
            raise ZoteroError("Zotero did not report Zotero-Server-ID")
        return self._server_id

    def authorize(self, app_name: str) -> tuple[str, bool]:
        """Ask Zotero for a write key; returns (key, remember).

        Shows a dialog unless a previous "always allow" is on record. With
        ``remember`` false the key is single-use.
        """
        req = urllib.request.Request(
            self.base_url + "/api/local/authorize",
            data=json.dumps({"appName": app_name}).encode(),
            headers={
                "Content-Type": "application/json",
                "Zotero-Server-ID": self.server_id(),
            },
            method="POST",
        )
        with self._open(req, AUTH_TIMEOUT) as resp:
            try:
                payload = json.load(resp)
                key = payload.get("key")
                remember = bool(payload.get("remember"))
            except (json.JSONDecodeError, AttributeError) as e:
                raise ZoteroError("unexpected authorization response") from e
        if not key:
            raise ZoteroError("authorization was not granted")
        return key, remember

    def post_items(self, library: str, items: list[dict], key: str) -> None:
        req = urllib.request.Request(
            f"{self.base_url}/api/{library}/items",
            data=json.dumps(items).encode(),
            headers={
                "Content-Type": "application/json",
                "Zotero-API-Version": "3",
                "Zotero-API-Key": key,
                "Zotero-Server-ID": self.server_id(),
            },
            method="POST",
        )
        with self._open(req, WRITE_TIMEOUT) as resp:
            resp.read()

    def children(self, paper: Paper) -> list[dict]:
        path = f"/api/{_library_path(paper)}/items/{paper.item_key}/children"
        result = self.get(path)
        if not isinstance(result, list):
            raise ZoteroError(f"unexpected children response for {paper.item_key}")
        return [c for c in result if isinstance(c, dict)]


def find_link(api: LocalApi, paper: Paper, url: str) -> dict | None:
    """Return the existing linked_url attachment with this url, if any."""
    for child in api.children(paper):
        data = child.get("data") or {}
        if data.get("linkMode") == "linked_url" and data.get("url") == url:
            return child
    return None


def attachment_item(paper: Paper, url: str) -> dict:
    return {
        "itemType": "attachment",
        "linkMode": "linked_url",
        "parentItem": paper.item_key,
        "title": ATTACHMENT_TITLE,
        "url": url,
    }


def _post_with_key(
    api: LocalApi, paper: Paper, item: dict, warn=lambda m: None
) -> None:
    """POST using the Keychain key; (re)authorize when missing or rejected."""
    try:
        key = keystore.load()
    except KeystoreError as e:
        warn(f"warning: {e}; authorizing without stored key")
        key = None

    def authorize() -> str:
        new_key, remember = api.authorize("paper-link")
        if remember:
            try:
                keystore.save(new_key)
            except KeystoreError as e:
                warn(f"warning: could not store key: {e}")
        else:
            warn(
                "warning: Zotero returned a single-use key (choose 'always allow' "
                "in the dialog to avoid being asked every time); not stored"
            )
        return new_key

    if key is None:
        key = authorize()
    path = _library_path(paper)
    try:
        api.post_items(path, [item], key)
    except ZoteroError as e:
        if getattr(e, "status", None) not in (401, 403):
            raise
        api.post_items(path, [item], authorize())


def link_paper(
    api: LocalApi, paper: Paper, url: str, sleep=time.sleep, warn=lambda m: None
) -> tuple[str, dict]:
    """Ensure the item has the link. Returns (``exists`` | ``created``, attachment)."""
    existing = find_link(api, paper, url)
    if existing:
        return "exists", existing

    write_error: ZoteroError | None = None
    try:
        _post_with_key(api, paper, attachment_item(paper, url), warn)
    except ZoteroError as e:
        # The write often succeeds without an HTTP response; verify by reading.
        write_error = e

    for attempt in range(VERIFY_ATTEMPTS):
        created = find_link(api, paper, url)
        if created:
            return "created", created
        if attempt < VERIFY_ATTEMPTS - 1:
            sleep(VERIFY_INTERVAL)
    detail = f" ({write_error})" if write_error else ""
    raise ZoteroError(f"attachment was not found after writing{detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="paper-link",
        description="Attach the deck's obsidian:// link to the Zotero item.",
    )
    parser.add_argument("citekey", nargs="?", help="Better BibTeX citekey")
    parser.add_argument(
        "--forget-key",
        action="store_true",
        help="delete the stored Zotero API key from the Keychain and exit",
    )
    parser.add_argument("--vault", help="vault root (overrides env and config)")
    args = parser.parse_args(argv)

    if args.forget_key:
        try:
            removed = keystore.forget()
        except KeystoreError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print("key removed" if removed else "no stored key")
        return 0
    if not args.citekey:
        parser.error("citekey is required")

    def warn(message: str) -> None:
        print(message, file=sys.stderr)

    url = ""
    try:
        if not _SAFE_CITEKEY.match(args.citekey):
            raise ValueError(f"citekey is not usable as a file name: {args.citekey!r}")
        vault = resolve_vault(args.vault)
        deck = vault.root / NOTE_DIR / f"{args.citekey}.md"
        if not deck.is_file():
            raise FileNotFoundError(f"deck not found (run paper-note first): {deck}")
        paper = resolve_citekey(args.citekey)
        url = deck_uri(vault, paper.citekey)
        status, attachment = link_paper(LocalApi(), paper, url, warn=warn)
    except (ConfigError, ZoteroError, ValueError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        if url and isinstance(e, ZoteroError):
            print(
                f"to attach by hand, add this link to the item: {url}", file=sys.stderr
            )
        return 2
    print(f"{status}: {attachment.get('key', '')}\t{url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
