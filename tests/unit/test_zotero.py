import pytest
from conftest import ENTRIES

from zotero_paper_tools.zotero import (
    ZoteroError,
    parse_entry,
    resolve_citekey,
    search,
)


def test_parse_entry():
    p = parse_entry(ENTRIES[0])
    assert p is not None
    assert (p.citekey, p.item_key, p.year, p.doi) == (
        "xu_probabilistic_2025",
        "ABCD1234",
        "2025",
        "10.1103/dvxz-w9ts",
    )
    assert p.authors == ["Xu", "Team"]
    assert p.select_uri == "zotero://select/library/items/ABCD1234"


def test_parse_group_and_skip_without_citekey():
    assert parse_entry(ENTRIES[1]).library == "groups/9"
    assert parse_entry(ENTRIES[2]) is None


def test_search_and_resolve(bbt_server):
    assert [p.citekey for p in search("probabilistic")] == ["xu_probabilistic_2025"]
    assert resolve_citekey("other_2020").item_key == "WXYZ9999"


def test_resolve_requires_exact_match(bbt_server):
    with pytest.raises(ZoteroError):
        resolve_citekey("xu_probabilistic")


def test_unreachable():
    from zotero_paper_tools.zotero import rpc

    with pytest.raises(ZoteroError):
        rpc("item.search", ["x"], "http://127.0.0.1:1")
