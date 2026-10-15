import json

from conftest import ENTRIES

from zotero_paper_tools import find, note
from zotero_paper_tools.config import Vault
from zotero_paper_tools.zotero import parse_entry


def test_find_text(bbt_server, capsys):
    assert find.main(["probabilistic"]) == 0
    out = capsys.readouterr().out.strip().split("\t")
    assert out == ["xu_probabilistic_2025", "2025", "Xu", "Probabilistic computing"]


def test_find_json_and_empty(bbt_server, monkeypatch, capsys):
    class FakeApi:
        def pdf_key(self, paper):
            return "PDF00001"

    monkeypatch.setattr(find, "LocalApi", FakeApi)
    assert find.main(["--json", "probabilistic"]) == 0
    row = json.loads(capsys.readouterr().out)[0]
    assert (row["zotero_key"], row["pdf_key"]) == ("ABCD1234", "PDF00001")
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
    front = text.split("\n---\n")[0]
    assert "marp: true" in front and "paginate: true" in front
    assert "style: |\n  section { font-size: 22px; }" in front
    assert "section img { max-height: 380px; }" in front


def test_deck_has_no_broken_image_links():
    import re

    text = note.build_deck(parse_entry(ENTRIES[0]))
    uncommented = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    assert not re.search(r"!\[[^\]]*\]\([^)]*\)", uncommented)


def test_note_creation(bbt_server, tmp_path, capsys):
    assert note.main(["--vault", str(tmp_path), "xu_probabilistic_2025"]) == 0
    path = tmp_path / "knowledge/research/papers/xu_probabilistic_2025.md"
    assert path.is_file()
    assert not path.with_name("xu_probabilistic_2025-img").exists()
    out = capsys.readouterr().out.splitlines()
    assert out == [str(path), "zotero://select/library/items/ABCD1234"]
    # a second run must not overwrite
    path.write_text("edited")
    assert note.main(["--vault", str(tmp_path), "xu_probabilistic_2025"]) == 2
    assert path.read_text() == "edited"


def test_note_private(bbt_server, tmp_path):
    args = ["--vault", str(tmp_path), "xu_probabilistic_2025"]
    assert note.main([*args, "--private"]) == 0
    private = tmp_path / "private/knowledge/research/papers/xu_probabilistic_2025.md"
    assert private.is_file()
    # a deck in either area blocks creating the other one
    assert note.main(args) == 2
    assert not (tmp_path / "knowledge/research/papers").exists()


def test_note_normal_blocks_private(bbt_server, tmp_path):
    args = ["--vault", str(tmp_path), "xu_probabilistic_2025"]
    assert note.main(args) == 0
    assert note.main([*args, "--private"]) == 2
    assert not (tmp_path / "private").exists()


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


def test_find_json_pdf_key_null_when_unavailable(bbt_server, monkeypatch, capsys):
    from zotero_paper_tools.zotero import ZoteroError

    class FakeApi:
        def pdf_key(self, paper):
            raise ZoteroError("down")

    monkeypatch.setattr(find, "LocalApi", FakeApi)
    assert find.main(["--json", "probabilistic"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["pdf_key"] is None


def test_note_and_link_use_overridden_vault_name(
    bbt_server, tmp_path, monkeypatch, capsys
):
    # Issue #1: config points at vault-a; --vault vault-b must not use its name
    from zotero_paper_tools import link

    a, b = tmp_path / "vault-a", tmp_path / "vault-b"
    a.mkdir()
    b.mkdir()
    conf = tmp_path / "c.toml"
    conf.write_text(f'vault_root = "{a}"\nvault_name = "Registered-A"\n')
    monkeypatch.setenv("ZOTERO_PAPER_TOOLS_CONFIG", str(conf))
    monkeypatch.delenv("OBSIDIAN_VAULT_ROOT", raising=False)
    monkeypatch.delenv("OBSIDIAN_VAULT_NAME", raising=False)
    assert note.main(["--vault", str(b), "xu_probabilistic_2025"]) == 0
    assert (b / "knowledge/research/papers/xu_probabilistic_2025.md").is_file()
    assert not (a / "knowledge").exists()
    # link resolves the deck in vault-b and builds the URI with vault-b's name
    vault = link.resolve_vault(str(b))
    rel = link.locate_deck(vault, "xu_probabilistic_2025")
    uri = link.deck_uri(vault, rel)
    assert uri.startswith("obsidian://open?vault=vault-b&file=knowledge/")
    assert "Registered-A" not in uri
    # with the name given explicitly
    vault = link.resolve_vault(str(b), cli_name="Registered-B")
    assert link.deck_uri(vault, rel).startswith("obsidian://open?vault=Registered-B&")
