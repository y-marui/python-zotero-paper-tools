"""paper-note: create a slide-style discussion note for a Zotero paper."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .config import ConfigError, Vault, resolve_vault
from .zotero import Paper, ZoteroError, resolve_citekey

NOTE_DIR = Path("private") / "knowledge"
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


def create_note(paper: Paper, vault: Vault) -> Path:
    if not _SAFE_CITEKEY.match(paper.citekey):
        raise ValueError(f"citekey is not usable as a file name: {paper.citekey!r}")
    note_dir = vault.root / NOTE_DIR
    path = note_dir / f"{paper.citekey}.md"
    if path.exists():
        raise FileExistsError(f"note already exists: {path}")
    note_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(build_deck(paper), encoding="utf-8")
    return path


def obsidian_uri(vault: Vault, path: Path) -> str:
    from urllib.parse import quote

    rel = path.relative_to(vault.root).as_posix()
    return f"obsidian://open?vault={quote(vault.name)}&file={quote(rel)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="paper-note",
        description="Create a slide-style discussion note for a Zotero paper.",
    )
    parser.add_argument("citekey", help="Better BibTeX citekey")
    parser.add_argument("--vault", help="vault root (overrides env and config)")
    args = parser.parse_args(argv)

    try:
        vault = resolve_vault(args.vault)
        paper = resolve_citekey(args.citekey)
        path = create_note(paper, vault)
    except (ConfigError, ZoteroError, ValueError, FileExistsError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(path)
    print(obsidian_uri(vault, path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
