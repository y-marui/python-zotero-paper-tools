"""Client for the Zotero local API (``/api``): reads and authorized writes."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from http.client import HTTPResponse
from typing import Any

from . import zotero
from .zotero import Paper, ZoteroError

# Reading back is cheap; writes may be slow while the authorization dialog is up.
WRITE_TIMEOUT = 20.0
AUTH_TIMEOUT = 120.0

_FILE_MODES = {"imported_file", "imported_url", "linked_file"}


def library_path(paper: Paper) -> str:
    return "users/0" if paper.library == "library" else paper.library


class LocalApi:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or zotero.BASE_URL
        self._server_id: str | None = None

    def _open(self, req: urllib.request.Request, timeout: float) -> HTTPResponse:
        try:
            resp: HTTPResponse = urllib.request.urlopen(req, timeout=timeout)
            return resp
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

    def _write(
        self,
        method: str,
        path: str,
        body: object,
        key: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        headers = {
            "Content-Type": "application/json",
            "Zotero-API-Version": "3",
            "Zotero-API-Key": key,
            "Zotero-Server-ID": self.server_id(),
            **(extra or {}),
        }
        req = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(body).encode(),
            headers=headers,
            method=method,
        )
        with self._open(req, WRITE_TIMEOUT) as resp:
            resp.read()

    def post_items(self, library: str, items: list[dict[str, Any]], key: str) -> None:
        self._write("POST", f"/api/{library}/items", items, key)

    def patch_item(
        self, library: str, item_key: str, version: int, data: dict[str, Any], key: str
    ) -> None:
        self._write(
            "PATCH",
            f"/api/{library}/items/{item_key}",
            data,
            key,
            {"If-Unmodified-Since-Version": str(version)},
        )

    def children(self, paper: Paper) -> list[dict[str, Any]]:
        path = f"/api/{library_path(paper)}/items/{paper.item_key}/children"
        result = self.get(path)
        if not isinstance(result, list):
            raise ZoteroError(f"unexpected children response for {paper.item_key}")
        return [c for c in result if isinstance(c, dict)]

    def pdf_key(self, paper: Paper) -> str | None:
        """Key of the item's PDF attachment, or None unless exactly one exists."""
        return pdf_key_of(self.children(paper))


def pdf_key_of(children: list[dict[str, Any]]) -> str | None:
    keys = [
        c.get("key")
        for c in children
        if (c.get("data") or {}).get("contentType") == "application/pdf"
        and (c.get("data") or {}).get("linkMode") in _FILE_MODES
    ]
    return keys[0] if len(keys) == 1 and keys[0] else None
