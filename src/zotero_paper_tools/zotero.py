"""Read-only access to Zotero via Better BibTeX JSON-RPC (local only)."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

BASE_URL = "http://localhost:23119"
RPC_PATH = "/better-bibtex/json-rpc"
TIMEOUT = 10.0

_ITEM_ID = re.compile(
    r"/(?P<scope>users|groups)/(?P<lib>\d+)/items/(?P<key>[A-Z0-9]+)$"
)


class ZoteroError(Exception):
    """Raised when Zotero or Better BibTeX cannot answer."""


@dataclass(frozen=True)
class Paper:
    citekey: str
    item_key: str
    title: str
    authors: list[str]
    year: str
    doi: str
    library: str  # "library" for the user library, else "groups/<id>"

    @property
    def select_uri(self) -> str:
        return f"zotero://select/{self.library}/items/{self.item_key}"

    @property
    def first_author(self) -> str:
        return self.authors[0] if self.authors else ""


def rpc(method: str, params: list[object], base_url: str | None = None) -> object:
    base_url = base_url or BASE_URL
    body = json.dumps(
        {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    ).encode()
    req = urllib.request.Request(
        base_url + RPC_PATH, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            payload = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise ZoteroError(
            f"cannot reach Zotero/Better BibTeX at {base_url} (is Zotero running?): {e}"
        ) from e
    if "error" in payload:
        raise ZoteroError(f"{method} failed: {payload['error']}")
    return payload["result"]


def _year(entry: dict[str, object]) -> str:
    issued = entry.get("issued")
    if isinstance(issued, dict):
        parts = issued.get("date-parts")
        if isinstance(parts, list) and parts and parts[0]:
            return str(parts[0][0])
    return ""


def _authors(entry: dict[str, object]) -> list[str]:
    names = []
    for a in entry.get("author") or []:  # type: ignore[attr-defined]
        if not isinstance(a, dict):
            continue
        name = a.get("family") or a.get("literal") or ""
        if name:
            names.append(str(name))
    return names


def parse_entry(entry: dict[str, object]) -> Paper | None:
    """Convert one CSL-JSON entry from ``item.search`` into a Paper."""
    citekey = entry.get("citation-key")
    m = _ITEM_ID.search(str(entry.get("id", "")))
    if not citekey or not m:
        return None
    library = "library" if m["scope"] == "users" else f"groups/{m['lib']}"
    return Paper(
        citekey=str(citekey),
        item_key=m["key"],
        title=str(entry.get("title", "")),
        authors=_authors(entry),
        year=_year(entry),
        doi=str(entry.get("DOI", "")),
        library=library,
    )


def search(query: str, base_url: str | None = None) -> list[Paper]:
    result = rpc("item.search", [query], base_url)
    if not isinstance(result, list):
        raise ZoteroError(f"unexpected item.search result: {result!r}")
    papers = (parse_entry(e) for e in result if isinstance(e, dict))
    return [p for p in papers if p is not None]


def resolve_citekey(citekey: str, base_url: str | None = None) -> Paper:
    """Resolve a citekey to exactly one item (no direct BBT method exists)."""
    matches = [p for p in search(citekey, base_url) if p.citekey == citekey]
    if not matches:
        raise ZoteroError(f"citekey not found in Zotero: {citekey}")
    if len(matches) > 1:
        raise ZoteroError(f"citekey is ambiguous in Zotero: {citekey}")
    return matches[0]
