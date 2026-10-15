"""paper-find: search Zotero and print citekeys."""

from __future__ import annotations

import argparse
import json
import sys

from .localapi import LocalApi
from .zotero import ZoteroError, search


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="paper-find", description="Search Zotero and print matching citekeys."
    )
    parser.add_argument("query", help="search terms (title, author, citekey, ...)")
    parser.add_argument("--json", action="store_true", help="output JSON")
    parser.add_argument(
        "--limit", type=int, default=20, help="max results (default 20)"
    )
    args = parser.parse_args(argv)

    try:
        papers = search(args.query)[: args.limit]
    except ZoteroError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if not papers:
        print(f"no results for: {args.query}", file=sys.stderr)
        return 1

    if args.json:
        api = LocalApi()

        def pdf_key(p):
            try:
                return api.pdf_key(p)
            except ZoteroError:
                return None

        rows = [
            {
                "citekey": p.citekey,
                "zotero_key": p.item_key,
                "pdf_key": pdf_key(p),
                "title": p.title,
                "authors": p.authors,
                "year": p.year,
                "doi": p.doi,
            }
            for p in papers
        ]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for p in papers:
            print(f"{p.citekey}\t{p.year}\t{p.first_author}\t{p.title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
