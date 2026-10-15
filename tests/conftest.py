import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

ENTRIES = [
    {
        "id": "http://zotero.org/users/123/items/ABCD1234",
        "citation-key": "xu_probabilistic_2025",
        "title": "Probabilistic computing",
        "DOI": "10.1103/dvxz-w9ts",
        "issued": {"date-parts": [[2025, 3]]},
        "author": [{"family": "Xu", "given": "Haijie"}, {"literal": "Team"}],
    },
    {
        "id": "http://zotero.org/groups/9/items/WXYZ9999",
        "citation-key": "other_2020",
        "title": "Other",
    },
    {"id": "http://zotero.org/users/123/items/NOKEY000", "title": "No citekey"},
]


@pytest.fixture
def bbt_server(monkeypatch):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            term = req["params"][0]
            hits = [e for e in ENTRIES if term.lower() in json.dumps(e).lower()]
            body = json.dumps({"jsonrpc": "2.0", "result": hits, "id": req["id"]})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body.encode())

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}"
    monkeypatch.setattr("zotero_paper_tools.zotero.BASE_URL", url)
    yield url
    server.shutdown()
