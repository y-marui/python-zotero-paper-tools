import json

from conftest import ENTRIES

from zotero_paper_tools import find, note
from zotero_paper_tools.config import Vault
from zotero_paper_tools.zotero import parse_entry


def test_find_text(bbt_server, capsys):
    assert find.main(["probabilistic"]) == 0
    out = capsys.readouterr().out.strip().split("\t")
    assert out == ["xu_probabilistic_2025", "2025", "Xu", "Probabilistic computing"]


def test_find_json_and_empty(bbt_server, capsys):
    assert find.main(["--json", "probabilistic"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["zotero_key"] == "ABCD1234"
    assert find.main(["zzzz-none"]) == 1


def test_deck_structure():
    paper = parse_entry(ENTRIES[0])
    text = note.build_deck(paper)
    head, *slides = text.split("\n---\n")
    assert head.startswith("---\n") is False or "citekey" in text
    assert 'citekey: "xu_probabilistic_2025"' in text
    assert 'zotero-key: "ABCD1234"' in text
    assert 'doi: "10.1103/dvxz-w9ts"' in text
    assert "zotero://select/library/items/ABCD1234" in text
    assert len(slides) >= 5


def test_deck_has_no_broken_image_links():
    import re

    text = note.build_deck(parse_entry(ENTRIES[0]))
    uncommented = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    assert not re.search(r"!\[[^\]]*\]\([^)]*\)", uncommented)


def test_note_creation(bbt_server, tmp_path, capsys):
    assert note.main(["--vault", str(tmp_path), "xu_probabilistic_2025"]) == 0
    path = tmp_path / "private/knowledge/xu_probabilistic_2025.md"
    assert path.is_file()
    assert not (tmp_path / "private/knowledge/xu_probabilistic_2025-img").exists()
    out = capsys.readouterr().out
    assert f"obsidian://open?vault={tmp_path.name}" in out
    # a second run must not overwrite
    path.write_text("edited")
    assert note.main(["--vault", str(tmp_path), "xu_probabilistic_2025"]) == 2
    assert path.read_text() == "edited"


def test_note_stops_without_vault(bbt_server, monkeypatch, tmp_path):
    monkeypatch.delenv("OBSIDIAN_VAULT_ROOT", raising=False)
    monkeypatch.setenv("ZOTERO_PAPER_TOOLS_CONFIG", str(tmp_path / "none.toml"))
    assert note.main(["xu_probabilistic_2025"]) == 2


def test_unsafe_citekey_rejected(tmp_path):
    import dataclasses

    paper = dataclasses.replace(parse_entry(ENTRIES[0]), citekey="../evil")
    try:
        note.create_note(paper, Vault(tmp_path, "v"))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
