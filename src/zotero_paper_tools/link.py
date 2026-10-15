"""paper-link: attach (or update) the deck's obsidian:// link on the Zotero item."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from . import keystore
from .config import ConfigError, Vault, resolve_vault
from .keystore import KeystoreError
from .localapi import LocalApi, library_path, pdf_key_of
from .note import _SAFE_CITEKEY, find_decks
from .zotero import Paper, ZoteroError, resolve_citekey

VERIFY_ATTEMPTS = 5
VERIFY_INTERVAL = 1.0
ATTACHMENT_TITLE = "Obsidian deck"


class DeckError(Exception):
    """Raised when the deck cannot be uniquely located."""


def deck_uri(vault: Vault, rel_path: str) -> str:
    """``obsidian://open`` URI for a vault-relative path without extension."""
    return f"obsidian://open?vault={quote(vault.name)}&file={quote(rel_path)}"


def locate_deck(vault: Vault, citekey: str) -> str:
    """Vault-relative path (no extension) of the deck in normal or private area."""
    found = find_decks(vault, citekey)
    if not found:
        raise DeckError(f"deck not found (run paper-note first): {citekey}")
    if len(found) > 1:
        raise DeckError(
            "deck exists in both normal and private areas: "
            + ", ".join(str(p) for p in found)
        )
    return found[0].relative_to(vault.root).with_suffix("").as_posix()


def _data(child: dict[str, Any]) -> dict[str, Any]:
    return child.get("data") or {}


def find_deck_attachment(
    children: list[dict[str, Any]], vault: Vault
) -> dict[str, Any] | None:
    """The existing deck link: titled "Obsidian deck" or pointing into the vault."""
    prefix = f"obsidian://open?vault={quote(vault.name)}"
    for child in children:
        d = _data(child)
        if d.get("linkMode") != "linked_url":
            continue
        if d.get("title") == ATTACHMENT_TITLE or str(d.get("url", "")).startswith(
            prefix
        ):
            return child
    return None


def _has_url(children: list[dict[str, Any]], url: str) -> dict[str, Any] | None:
    for child in children:
        d = _data(child)
        if d.get("linkMode") == "linked_url" and d.get("url") == url:
            return child
    return None


def attachment_item(paper: Paper, url: str) -> dict[str, Any]:
    return {
        "itemType": "attachment",
        "linkMode": "linked_url",
        "parentItem": paper.item_key,
        "title": ATTACHMENT_TITLE,
        "url": url,
    }


def _with_key(
    api: LocalApi,
    write: Callable[[str], None],
    warn: Callable[[str], None] = lambda m: None,
) -> None:
    """Run ``write(key)`` with the Keychain key; (re)authorize when missing/rejected."""
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
    try:
        write(key)
    except ZoteroError as e:
        if getattr(e, "status", None) not in (401, 403):
            raise
        write(authorize())


def link_paper(
    api: LocalApi,
    paper: Paper,
    vault: Vault,
    url: str,
    sleep: Callable[[float], None] = time.sleep,
    warn: Callable[[str], None] = lambda m: None,
) -> tuple[str, dict[str, Any], str | None]:
    """Ensure the item carries the deck link.

    Returns (``exists`` | ``updated`` | ``created``, attachment, pdf key).
    """
    children = api.children(paper)
    pdf = pdf_key_of(children)
    existing = _has_url(children, url)
    if existing:
        return "exists", existing, pdf

    stale = find_deck_attachment(children, vault)
    lib = library_path(paper)
    if stale:
        status = "updated"
        version = int(stale.get("version") or _data(stale).get("version") or 0)

        def write(key: str) -> None:
            api.patch_item(lib, stale["key"], version, {"url": url}, key)
    else:
        status = "created"

        def write(key: str) -> None:
            api.post_items(lib, [attachment_item(paper, url)], key)

    write_error: ZoteroError | None = None
    try:
        _with_key(api, write, warn)
    except ZoteroError as e:
        # The write often succeeds without an HTTP response; verify by reading.
        write_error = e

    for attempt in range(VERIFY_ATTEMPTS):
        found = _has_url(api.children(paper), url)
        if found:
            return status, found, pdf
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
    parser.add_argument("--vault", help="vault root (overrides env and config)")
    parser.add_argument(
        "--vault-name",
        help="vault name registered in Obsidian (overrides env and config)",
    )
    parser.add_argument(
        "--forget-key",
        action="store_true",
        help="delete the stored Zotero API key from the Keychain and exit",
    )
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
        vault = resolve_vault(args.vault, cli_name=args.vault_name)
        rel = locate_deck(vault, args.citekey)
        paper = resolve_citekey(args.citekey)
        url = deck_uri(vault, rel)
        status, attachment, pdf = link_paper(LocalApi(), paper, vault, url, warn=warn)
    except (ConfigError, ZoteroError, DeckError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        if url and isinstance(e, ZoteroError):
            print(
                f"to attach by hand, add this link to the item: {url}", file=sys.stderr
            )
        return 2
    print(f"{status}: {attachment.get('key', '')}")
    print(f"item: {paper.select_uri}")
    if pdf:
        print(f"pdf: zotero://open-pdf/{paper.library}/items/{pdf}?page=1")
    print(f"deck: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
