import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from conftest import ENTRIES

from zotero_paper_tools import keystore, link
from zotero_paper_tools.config import Vault
from zotero_paper_tools.zotero import ZoteroError, parse_entry

PAPER = parse_entry(ENTRIES[0])


class State:
    children: list[dict]
    authorize_calls: int
    hang_on_post: bool
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
    state.children, state.authorize_calls, state.hang_on_post = [], 0, False
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
            if self.path.endswith("/children"):
                self._json(state.children)
            else:
                self._json([])

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path == "/api/local/authorize":
                assert self.headers["Zotero-Server-ID"] == "srv1"
                state.authorize_calls += 1
                return self._json({"key": "K", "remember": state.remember})
            assert self.path == "/api/users/0/items"
            if self.headers["Zotero-API-Key"] not in state.valid_keys:
                return self._json({}, 401)
            assert self.headers["Zotero-Server-ID"] == "srv1"
            state.children.append({"key": "NEWATT01", "data": body[0]})
            if state.hang_on_post:
                time.sleep(1.0)
                return
            self._json({"successful": {"0": {}}})

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(link, "WRITE_TIMEOUT", 0.2)
    monkeypatch.setattr(link, "VERIFY_INTERVAL", 0)
    api = link.LocalApi(f"http://127.0.0.1:{server.server_port}")
    yield api, state
    server.shutdown()


def test_deck_uri_has_no_extension_and_is_encoded():
    uri = link.deck_uri(Vault("/x", "my vault"), "a_b-1")
    assert uri == "obsidian://open?vault=my%20vault&file=private/knowledge/a_b-1"


def test_create_then_idempotent(local_api):
    api, state = local_api
    url = "obsidian://open?vault=v&file=private/knowledge/k"
    assert link.link_paper(api, PAPER, url)[0] == "created"
    data = state.children[0]["data"]
    assert (data["itemType"], data["linkMode"], data["parentItem"]) == (
        "attachment",
        "linked_url",
        "ABCD1234",
    )
    assert data["url"] == url
    assert link.link_paper(api, PAPER, url)[0] == "exists"
    assert len(state.children) == 1
    assert state.authorize_calls == 1  # no authorization needed when it exists


def test_write_timeout_is_verified_by_reading(local_api):
    api, state = local_api
    state.hang_on_post = True
    status, att = link.link_paper(api, PAPER, "obsidian://x")
    assert status == "created" and att["key"] == "NEWATT01"


def test_failure_when_attachment_never_appears(local_api, monkeypatch):
    api, state = local_api
    monkeypatch.setattr(
        api, "post_items", lambda *a: (_ for _ in ()).throw(ZoteroError("boom"))
    )
    with pytest.raises(ZoteroError, match="not found after writing.*boom"):
        link.link_paper(api, PAPER, "obsidian://x", sleep=lambda s: None)


def test_main(local_api, bbt_server, tmp_path, monkeypatch, capsys):
    api, state = local_api
    monkeypatch.setattr(link, "LocalApi", lambda: api)
    argv = ["--vault", str(tmp_path), "xu_probabilistic_2025"]
    assert link.main(argv) == 2  # deck missing
    deck = tmp_path / "private/knowledge/xu_probabilistic_2025.md"
    deck.parent.mkdir(parents=True)
    deck.write_text("x")
    capsys.readouterr()
    assert link.main(argv) == 0
    assert capsys.readouterr().out.startswith("created: NEWATT01")
    assert link.main(argv) == 0
    assert capsys.readouterr().out.startswith("exists:")


def test_stored_key_is_saved_and_reused(local_api, vault_keys):
    api, state = local_api
    link.link_paper(api, PAPER, "obsidian://a")
    assert vault_keys == {"k": "K"} and state.authorize_calls == 1
    link.link_paper(api, PAPER, "obsidian://b")
    assert state.authorize_calls == 1  # reused without asking again


def test_rejected_key_triggers_reauthorization(local_api, vault_keys):
    api, state = local_api
    vault_keys["k"] = "STALE"
    assert link.link_paper(api, PAPER, "obsidian://a")[0] == "created"
    assert state.authorize_calls == 1 and vault_keys["k"] == "K"


def test_single_use_key_is_not_stored(local_api, vault_keys):
    api, state = local_api
    state.remember = False
    warnings = []
    link.link_paper(api, PAPER, "obsidian://a", warn=warnings.append)
    assert vault_keys == {} and "single-use" in warnings[0]


def test_forget_key(vault_keys, capsys):
    vault_keys["k"] = "K"
    assert link.main(["--forget-key"]) == 0
    assert "key removed" in capsys.readouterr().out and vault_keys == {}
    assert link.main(["--forget-key"]) == 0
    assert "no stored key" in capsys.readouterr().out
