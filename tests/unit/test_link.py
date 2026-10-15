import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from conftest import ENTRIES

from zotero_paper_tools import keystore, link, localapi
from zotero_paper_tools.config import Vault
from zotero_paper_tools.zotero import ZoteroError, parse_entry

PAPER = parse_entry(ENTRIES[0])
VAULT = Vault("/x", "v")
URL = "obsidian://open?vault=v&file=knowledge/research/papers/k"


class State:
    children: list[dict]
    authorize_calls: int
    hang_on_write: bool
    valid_keys: set
    remember: bool


@pytest.fixture
def vault_keys(monkeypatch):
    store = {}
    monkeypatch.setattr(keystore, "load", lambda: store.get("k"))
    monkeypatch.setattr(keystore, "save", lambda k: store.__setitem__("k", k))
    monkeypatch.setattr(keystore, "forget", lambda: store.pop("k", None) is not None)
    return store


@pytest.fixture
def local_api(monkeypatch, vault_keys):
    state = State()
    state.children, state.authorize_calls, state.hang_on_write = [], 0, False
    state.valid_keys, state.remember = {"K"}, True

    class Handler(BaseHTTPRequestHandler):
        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Zotero-Server-ID", "srv1")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self._json(state.children if self.path.endswith("/children") else [])

        def _authorized(self):
            assert self.headers["Zotero-Server-ID"] == "srv1"
            if self.headers["Zotero-API-Key"] not in state.valid_keys:
                self._json({}, 401)
                return False
            return True

        def _length_body(self):
            return json.loads(self.rfile.read(int(self.headers["Content-Length"])))

        def do_POST(self):
            body = self._length_body()
            if self.path == "/api/local/authorize":
                assert self.headers["Zotero-Server-ID"] == "srv1"
                state.authorize_calls += 1
                return self._json({"key": "K", "remember": state.remember})
            assert self.path == "/api/users/0/items"
            if not self._authorized():
                return
            state.children.append({"key": "NEWATT01", "version": 5, "data": body[0]})
            self._finish()

        def do_PATCH(self):
            body = self._length_body()
            if not self._authorized():
                return
            att = next(c for c in state.children if self.path.endswith(c["key"]))
            assert self.headers["If-Unmodified-Since-Version"] == str(att["version"])
            att["data"].update(body)
            self._finish()

        def _finish(self):
            if state.hang_on_write:
                time.sleep(1.0)
                return
            self._json({"successful": {"0": {}}})

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(localapi, "WRITE_TIMEOUT", 0.2)
    monkeypatch.setattr(link, "VERIFY_INTERVAL", 0)
    api = localapi.LocalApi(f"http://127.0.0.1:{server.server_port}")
    yield api, state
    server.shutdown()


def test_deck_uri_has_no_extension_and_is_encoded():
    uri = link.deck_uri(Vault("/x", "my vault"), "knowledge/research/papers/a_b-1")
    assert uri == (
        "obsidian://open?vault=my%20vault&file=knowledge/research/papers/a_b-1"
    )


def test_locate_deck(tmp_path):
    vault = Vault(tmp_path, "v")
    with pytest.raises(link.DeckError, match="not found"):
        link.locate_deck(vault, "k")
    private = tmp_path / "private/knowledge/research/papers"
    private.mkdir(parents=True)
    (private / "k.md").write_text("x")
    assert link.locate_deck(vault, "k") == "private/knowledge/research/papers/k"
    normal = tmp_path / "knowledge/research/papers"
    normal.mkdir(parents=True)
    (normal / "k.md").write_text("x")
    with pytest.raises(link.DeckError, match="both"):
        link.locate_deck(vault, "k")


def test_create_then_idempotent(local_api):
    api, state = local_api
    assert link.link_paper(api, PAPER, VAULT, URL)[0] == "created"
    data = state.children[0]["data"]
    assert (data["itemType"], data["linkMode"], data["parentItem"]) == (
        "attachment",
        "linked_url",
        "ABCD1234",
    )
    assert data["url"] == URL and data["title"] == "Obsidian deck"
    assert link.link_paper(api, PAPER, VAULT, URL)[0] == "exists"
    assert len(state.children) == 1
    assert state.authorize_calls == 1  # no authorization needed when it exists


@pytest.mark.parametrize(
    "data",
    [
        {"title": "Obsidian deck", "url": "obsidian://open?vault=other&file=x"},
        {"title": "renamed", "url": "obsidian://open?vault=v&file=private/old"},
    ],
)
def test_changed_url_updates_existing_attachment(local_api, data):
    api, state = local_api
    state.children.append(
        {"key": "OLDATT01", "version": 3, "data": {"linkMode": "linked_url", **data}}
    )
    status, att, _ = link.link_paper(api, PAPER, VAULT, URL)
    assert status == "updated" and att["key"] == "OLDATT01"
    assert len(state.children) == 1 and state.children[0]["data"]["url"] == URL


def test_vault_name_prefix_does_not_match_other_vault(local_api):
    """A link into vault "v2" must not be taken for a link into vault "v"."""
    api, state = local_api
    other = "obsidian://open?vault=v2&file=x"
    state.children.append(
        {
            "key": "V2ATT001",
            "version": 3,
            "data": {"linkMode": "linked_url", "title": "other", "url": other},
        }
    )
    status, _, _ = link.link_paper(api, PAPER, VAULT, URL)
    assert status == "created"
    assert len(state.children) == 2
    assert state.children[0]["data"]["url"] == other


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("obsidian://open?vault=v&file=a", True),
        ("obsidian://open?file=a&vault=v", True),
        ("obsidian://open?vault=v2&file=a", False),
        ("obsidian://open?vault=vv", False),
        ("obsidian://open?vault=v%20x&file=a", False),
        ("https://example.com/?vault=v", False),
        ("obsidian://search?vault=v", False),
    ],
)
def test_points_into_vault_is_exact(url, expected):
    assert link._points_into_vault(url, "v") is expected


def test_unrelated_link_attachment_is_left_alone(local_api):
    api, state = local_api
    state.children.append(
        {
            "key": "WEBATT01",
            "version": 1,
            "data": {"linkMode": "linked_url", "title": "Web", "url": "https://x.org"},
        }
    )
    assert link.link_paper(api, PAPER, VAULT, URL)[0] == "created"
    assert state.children[0]["data"]["url"] == "https://x.org"


def test_pdf_key_only_when_unique(local_api):
    api, state = local_api
    pdf = {
        "key": "PDF00001",
        "data": {"linkMode": "imported_file", "contentType": "application/pdf"},
    }
    state.children.append(pdf)
    assert link.link_paper(api, PAPER, VAULT, URL)[2] == "PDF00001"
    state.children.append({**pdf, "key": "PDF00002"})
    assert api.pdf_key(PAPER) is None


def test_write_timeout_is_verified_by_reading(local_api):
    api, state = local_api
    state.hang_on_write = True
    status, att, _ = link.link_paper(api, PAPER, VAULT, URL)
    assert status == "created" and att["key"] == "NEWATT01"


def test_failure_when_attachment_never_appears(local_api, monkeypatch):
    api, _ = local_api
    monkeypatch.setattr(
        api, "post_items", lambda *a: (_ for _ in ()).throw(ZoteroError("boom"))
    )
    with pytest.raises(ZoteroError, match="not found after writing.*boom"):
        link.link_paper(api, PAPER, VAULT, URL, sleep=lambda s: None)


def test_main_output(local_api, bbt_server, tmp_path, monkeypatch, capsys):
    api, state = local_api
    state.children.append(
        {
            "key": "PDF00001",
            "data": {"linkMode": "imported_file", "contentType": "application/pdf"},
        }
    )
    monkeypatch.setattr(link, "LocalApi", lambda: api)
    argv = ["--vault", str(tmp_path), "xu_probabilistic_2025"]
    assert link.main(argv) == 2  # deck missing
    deck = tmp_path / "knowledge/research/papers/xu_probabilistic_2025.md"
    deck.parent.mkdir(parents=True)
    deck.write_text("x")
    capsys.readouterr()
    assert link.main(argv) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "created: NEWATT01"
    assert "item: zotero://select/library/items/ABCD1234" in out
    assert "pdf: zotero://open-pdf/library/items/PDF00001?page=1" in out
    assert (
        f"deck: obsidian://open?vault={tmp_path.name}"
        "&file=knowledge/research/papers/xu_probabilistic_2025"
    ) in out
    assert link.main(argv) == 0
    assert capsys.readouterr().out.startswith("exists:")


def test_stored_key_is_saved_and_reused(local_api, vault_keys):
    api, state = local_api
    link.link_paper(api, PAPER, VAULT, "obsidian://open?vault=v&file=a")
    assert vault_keys == {"k": "K"} and state.authorize_calls == 1
    link.link_paper(api, PAPER, VAULT, "obsidian://open?vault=v&file=b")  # update
    assert state.authorize_calls == 1  # reused without asking again


def test_rejected_key_triggers_reauthorization(local_api, vault_keys):
    api, state = local_api
    vault_keys["k"] = "STALE"
    assert link.link_paper(api, PAPER, VAULT, URL)[0] == "created"
    assert state.authorize_calls == 1 and vault_keys["k"] == "K"


def test_single_use_key_is_not_stored(local_api, vault_keys):
    api, state = local_api
    state.remember = False
    warnings = []
    link.link_paper(api, PAPER, VAULT, URL, warn=warnings.append)
    assert vault_keys == {} and "single-use" in warnings[0]


def test_forget_key(vault_keys, capsys):
    vault_keys["k"] = "K"
    assert link.main(["--forget-key"]) == 0
    assert "key removed" in capsys.readouterr().out and vault_keys == {}
    assert link.main(["--forget-key"]) == 0
    assert "no stored key" in capsys.readouterr().out
