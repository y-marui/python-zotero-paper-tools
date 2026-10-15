"""paper-note: create a slide-style discussion note for a Zotero paper."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .config import ConfigError, Vault, resolve_vault
from .zotero import Paper, ZoteroError, resolve_citekey

NOTE_DIR = Path("knowledge") / "research" / "papers"
PRIVATE_NOTE_DIR = Path("private") / NOTE_DIR
_SAFE_CITEKEY = re.compile(r"^[A-Za-z0-9_.:-]+$")


def _yaml(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_deck(paper: Paper) -> str:
    """Return the note text. Slides are separated by ``---`` lines."""
    label = " ".join(x for x in (paper.first_author, paper.year) if x)
    desc = f"{label or paper.citekey} の論文議論のまとめ"
    lines = [
        "---",
        "type: knowledge",
        f"description: {_yaml(desc)}",
        f"citekey: {_yaml(paper.citekey)}",
        f"zotero-key: {_yaml(paper.item_key)}",
        f"doi: {_yaml(paper.doi)}",
        "review_status: pending",
        "sources: []",
        "marp: true",
        "paginate: true",
        "style: |",
        "  section { font-size: 22px; }",
        "  section img { max-height: 380px; }",
        "---",
        "",
        f"# {paper.title}",
        "",
        f"- Zotero: [{paper.citekey}]({paper.select_uri})",
        "",
        "---",
        "",
        "## 目的と主張",
        "",
        "---",
        "",
        "## 方法",
        "",
        "---",
        "",
        "## 結果",
        "",
        f"<!-- 図は {paper.citekey}-img/ に置き、"
        f"![図の説明]({paper.citekey}-img/ファイル名.png) で埋め込む -->",
        "",
        "---",
        "",
        "## 議論（原文 / AIの推論 / 自分の着想）",
        "",
        "- 原文:",
        "- AIの推論:",
        "- 自分の着想:",
        "",
        "---",
        "",
        "## 次にやること",
        "",
    ]
    return "\n".join(lines)


def find_decks(vault: Vault, citekey: str) -> list[Path]:
    """Existing decks for the citekey in the normal and private areas."""
    paths = (vault.root / d / f"{citekey}.md" for d in (NOTE_DIR, PRIVATE_NOTE_DIR))
    return [p for p in paths if p.exists()]


def create_note(paper: Paper, vault: Vault, private: bool = False) -> Path:
    if not _SAFE_CITEKEY.match(paper.citekey):
        raise ValueError(f"citekey is not usable as a file name: {paper.citekey!r}")
    existing = find_decks(vault, paper.citekey)
    if existing:
        raise FileExistsError(f"note already exists: {existing[0]}")
    note_dir = vault.root / (PRIVATE_NOTE_DIR if private else NOTE_DIR)
    path = note_dir / f"{paper.citekey}.md"
    note_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(build_deck(paper), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="paper-note",
        description="Create a slide-style discussion note for a Zotero paper.",
    )
    parser.add_argument("citekey", help="Better BibTeX citekey")
    parser.add_argument("--vault", help="vault root (overrides env and config)")
    parser.add_argument(
        "--vault-name",
        help="vault name registered in Obsidian (overrides env and config)",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="create the deck under private/ instead of the normal area",
    )
    args = parser.parse_args(argv)

    try:
        vault = resolve_vault(args.vault, cli_name=args.vault_name)
        paper = resolve_citekey(args.citekey)
        path = create_note(paper, vault, args.private)
    except (ConfigError, ZoteroError, ValueError, FileExistsError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(path)
    print(paper.select_uri)
    return 0


if __name__ == "__main__":
    sys.exit(main())
