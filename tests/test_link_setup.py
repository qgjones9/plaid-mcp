"""Host Plaid Link page."""

import io
import json
import threading
from http.client import HTTPConnection

import pytest

from plaid_mcp.errors import PlaidMcpError
from plaid_mcp.items import ItemStore
from plaid_mcp.link_setup import (
    LinkSession,
    _handle_get,
    _handle_post,
    _read_json,
    bind_link_server,
    link_listen_settings,
    main,
    serve_until_linked,
)
from tests.fakes import FakeGateway


class _Headers:
    def __init__(self, values: dict) -> None:
        self._values = values

    def get(self, name: str):
        return self._values.get(name)


class _Handler:
    def __init__(
        self,
        path: str,
        body: bytes = b"",
        headers: dict | None = None,
        session=None,
    ) -> None:
        self.path = path
        self.headers = _Headers({} if headers is None else headers)
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.status = None
        self.sent_headers: list[tuple[str, str]] = []
        self.server = _ServerBox(session)

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, key: str, value: str) -> None:
        self.sent_headers.append((key, value))

    def end_headers(self) -> None:
        return


class _ServerBox:
    def __init__(self, session) -> None:
        self.session = session
        self.link_complete = False


def test_html_page_escapes_the_link_token(tmp_path):
    session = LinkSession(FakeGateway(), ItemStore(tmp_path / "items.json"), 'link-"<token>"')
    page = session.html_page()
    assert "link-&quot;&lt;token&gt;&quot;" in page
    assert "link-initialize.js" in page


def test_exchange_saves_an_item(tmp_path):
    gateway = FakeGateway()
    store = ItemStore(tmp_path / "items.json")
    session = LinkSession(gateway, store, "link-token")
    item = session.exchange(" public-sandbox ", " First Platypus Bank ")
    assert item.item_id == "item-1"
    assert item.institution_name == "First Platypus Bank"
    assert store.resolve(None).access_token == "access-sandbox"
    assert gateway.calls == [("exchange_public_token", "public-sandbox")]


def test_exchange_allows_a_missing_institution_name(tmp_path):
    session = LinkSession(FakeGateway(), ItemStore(tmp_path / "items.json"), "link-token")
    item = session.exchange("public-sandbox", None)
    assert item.institution_name == ""
    with pytest.raises(PlaidMcpError, match="public_token is required"):
        session.exchange("  ", None)
    with pytest.raises(PlaidMcpError, match="institution_name must be a string"):
        session.exchange("public-sandbox", 1)


def test_read_json_rejects_a_bad_body():
    missing = _Handler("/exchange")
    with pytest.raises(PlaidMcpError, match="Content-Length is required"):
        _read_json(missing)
    letters = _Handler("/exchange", headers={"Content-Length": "abc"})
    with pytest.raises(PlaidMcpError, match="Content-Length must be a number"):
        _read_json(letters)
    broken = _Handler("/exchange", b"{", {"Content-Length": "1"})
    with pytest.raises(PlaidMcpError, match="Request body must be JSON"):
        _read_json(broken)
    binary = _Handler("/exchange", b"\xff", {"Content-Length": "1"})
    with pytest.raises(PlaidMcpError, match="Request body must be JSON"):
        _read_json(binary)
    array = _Handler("/exchange", b"[1]", {"Content-Length": "3"})
    with pytest.raises(PlaidMcpError, match="Request body must be a JSON object"):
        _read_json(array)


def test_handlers_cover_not_found_and_errors(tmp_path):
    session = LinkSession(FakeGateway(), ItemStore(tmp_path / "items.json"), "link-token")
    missing_page = _Handler("/nope", session=session)
    _handle_get(missing_page)
    assert missing_page.status == 404

    page = _Handler("/?next=1", session=session)
    _handle_get(page)
    assert page.status == 200
    assert b"link-token" in page.wfile.getvalue()

    missing_post = _Handler("/nope", session=session)
    _handle_post(missing_post)
    assert missing_post.status == 404

    body = b"{}"
    rejected = _Handler("/exchange", body, {"Content-Length": str(len(body))}, session)
    _handle_post(rejected)
    assert rejected.status == 400
    assert rejected.server.link_complete is False


def test_link_page_exchanges_a_public_token(tmp_path):
    gateway = FakeGateway()
    store = ItemStore(tmp_path / "items.json")
    session = LinkSession(gateway, store, "link-sandbox-token")
    server = bind_link_server(session, "127.0.0.1", 0)
    port = server.server_address[1]
    thread = threading.Thread(target=serve_until_linked, args=(server,), daemon=True)
    thread.start()
    try:
        missing_status, missing_body = _request(port, "GET", "/missing")
        assert missing_status == 404
        assert missing_body == b"Not found"
        home_status, home_body = _request(port, "GET", "/")
        assert home_status == 200
        assert b"link-sandbox-token" in home_body
        other_status, _other_body = _request(port, "POST", "/other")
        assert other_status == 404
        exchange_body = json.dumps(
            {"public_token": "public-sandbox", "institution_name": "First Platypus Bank"}
        ).encode()
        exchange_status, exchange_payload = _request(port, "POST", "/exchange", exchange_body)
        assert exchange_status == 200
        assert json.loads(exchange_payload.decode())["itemId"] == "item-1"
    finally:
        thread.join(timeout=5)
    assert store.resolve(None).institution_name == "First Platypus Bank"


def test_serve_closes_when_a_request_fails(tmp_path):
    session = LinkSession(FakeGateway(), ItemStore(tmp_path / "items.json"), "link-token")
    server = bind_link_server(session, "127.0.0.1", 0)

    def boom() -> None:
        raise RuntimeError("boom")

    server.handle_request = boom
    with pytest.raises(RuntimeError, match="boom"):
        serve_until_linked(server)


def test_link_listen_settings(monkeypatch):
    monkeypatch.delenv("PLAID_MCP_LINK_HOST", raising=False)
    monkeypatch.delenv("PLAID_MCP_LINK_PORT", raising=False)
    assert link_listen_settings() == ("127.0.0.1", 8096)
    monkeypatch.setenv("PLAID_MCP_LINK_HOST", "0.0.0.0")
    monkeypatch.setenv("PLAID_MCP_LINK_PORT", "9001")
    assert link_listen_settings() == ("0.0.0.0", 9001)


def test_link_main_prints_the_local_page(monkeypatch, tmp_path, capsys):
    import plaid_mcp.link_setup as link

    gateway = FakeGateway()
    monkeypatch.setattr(link, "default_config_dir", lambda: tmp_path)
    monkeypatch.setattr(link, "load_credentials", lambda directory: "creds")
    monkeypatch.setattr(link, "build_gateway", lambda credentials: gateway)
    captured = {}
    monkeypatch.setattr(
        link,
        "bind_link_server",
        lambda session, host, port: captured.setdefault("server", object()),
    )
    monkeypatch.setattr(
        link,
        "serve_until_linked",
        lambda server: captured.setdefault("served", server),
    )
    monkeypatch.delenv("PLAID_MCP_LINK_HOST", raising=False)
    monkeypatch.delenv("PLAID_MCP_LINK_PORT", raising=False)

    main()

    text = capsys.readouterr().out
    assert "http://127.0.0.1:8096/" in text
    assert "user_good / pass_good" in text
    assert "Saved the linked item." in text
    assert captured["served"] is captured["server"]
    assert gateway.calls == [("create_link_token",)]


def _request(port: int, method: str, path: str, body: bytes | None = None) -> tuple[int, bytes]:
    connection = HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request(method, path, body=body)
    response = connection.getresponse()
    payload = response.read()
    status = response.status
    connection.close()
    return status, payload
