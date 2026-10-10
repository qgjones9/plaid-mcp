"""One-time Plaid Link on the host. This is not an MCP tool."""

import json
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer

from plaid_mcp.client import build_gateway
from plaid_mcp.config import (
    default_config_dir,
    environment_port,
    environment_text,
    load_credentials,
)
from plaid_mcp.errors import PlaidMcpError
from plaid_mcp.items import ItemStore, LinkedItem
from plaid_mcp.validate import optional_text, required_text

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Plaid Link</title>
</head>
<body>
  <p id="status">Opening Plaid Link.</p>
  <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
  <script>
    var handler = Plaid.create({
      token: "LINK_TOKEN",
      onSuccess: function (publicToken, metadata) {
        var institution = metadata.institution || {};
        var body = JSON.stringify({
          public_token: publicToken,
          institution_name: institution.name || ""
        });
        fetch("/exchange", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: body
        }).then(function (response) {
          return response.json();
        }).then(function (payload) {
          var status = document.getElementById("status");
          if (payload.itemId) {
            status.textContent = "Linked item " + payload.itemId;
            return;
          }
          status.textContent = payload.error || "Link failed";
        });
      }
    });
    handler.open();
  </script>
</body>
</html>
"""


class LinkSession:
    """Exchange one public token and render the Link page."""

    def __init__(self, gateway: object, items: ItemStore, link_token: str) -> None:
        self._gateway = gateway
        self._items = items
        self._link_token = link_token

    def html_page(self) -> str:
        """Return the local page that opens Plaid Link."""
        token = escape(self._link_token, quote=True)
        return _PAGE.replace("LINK_TOKEN", token)

    def exchange(self, public_token: object, institution_name: object) -> LinkedItem:
        """Turn a public token into a stored item."""
        token = required_text(public_token, "public_token")
        name = optional_text(institution_name, "institution_name")
        access_token, item_id = self._gateway.exchange_public_token(token)
        item = LinkedItem(
            item_id=item_id,
            access_token=access_token,
            institution_name=name,
        )
        self._items.add(item)
        return item


class LinkHTTPServer(HTTPServer):
    """Local server that stops after one successful exchange."""

    def __init__(self, address: tuple[str, int], handler: type, session: LinkSession) -> None:
        self.session = session
        self.link_complete = False
        super().__init__(address, handler)


def link_listen_settings() -> tuple[str, int]:
    """Read the Link page host and port. The default is 127.0.0.1:8096."""
    host = environment_text("PLAID_MCP_LINK_HOST", "127.0.0.1")
    port = environment_port("PLAID_MCP_LINK_PORT", 8096)
    return host, port


def bind_link_server(session: LinkSession, host: str, port: int) -> LinkHTTPServer:
    """Bind the Link page. Use port 0 in tests to let the OS pick a port."""
    return LinkHTTPServer((host, port), _handler_class(), session)


def serve_until_linked(server: LinkHTTPServer) -> None:
    """Handle requests until a public token has been saved."""
    try:
        while not server.link_complete:
            server.handle_request()
    finally:
        server.server_close()


def main() -> None:
    """Open Plaid Link and save the access token outside the repository."""
    directory = default_config_dir()
    credentials = load_credentials(directory)
    gateway = build_gateway(credentials)
    items = ItemStore(directory / "items.json")
    session = LinkSession(gateway, items, gateway.create_link_token())
    host, port = link_listen_settings()
    server = bind_link_server(session, host, port)
    print(f"Open http://{host}:{port}/")
    print("Sandbox sign-in is user_good / pass_good.")
    serve_until_linked(server)
    print("Saved the linked item.")


def _handler_class() -> type:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            _handle_get(self)

        def do_POST(self) -> None:
            _handle_post(self)

        def log_message(self, message_format: str, *args) -> None:
            return

    return Handler


def _handle_get(handler: BaseHTTPRequestHandler) -> None:
    if _route(handler) != "/":
        _send_text(handler, 404, "Not found")
        return
    page = handler.server.session.html_page()
    _send_bytes(handler, 200, page.encode("utf-8"), "text/html; charset=utf-8")


def _handle_post(handler: BaseHTTPRequestHandler) -> None:
    if _route(handler) != "/exchange":
        _send_text(handler, 404, "Not found")
        return
    try:
        body = _read_json(handler)
        item = handler.server.session.exchange(
            body.get("public_token"),
            body.get("institution_name"),
        )
    except PlaidMcpError as error:
        _send_json(handler, 400, {"error": str(error)})
        return
    handler.server.link_complete = True
    _send_json(handler, 200, {"itemId": item.item_id})


def _route(handler: BaseHTTPRequestHandler) -> str:
    return handler.path.split("?", 1)[0]


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length_text = handler.headers.get("Content-Length")
    if length_text is None:
        raise PlaidMcpError("Content-Length is required")
    if not str(length_text).isdigit():
        raise PlaidMcpError("Content-Length must be a number")
    raw = handler.rfile.read(int(length_text))
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PlaidMcpError("Request body must be JSON") from error
    if not isinstance(payload, dict):
        raise PlaidMcpError("Request body must be a JSON object")
    return payload


def _send_text(handler: BaseHTTPRequestHandler, status: int, message: str) -> None:
    _send_bytes(handler, status, message.encode("utf-8"), "text/plain; charset=utf-8")


def _send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = (json.dumps(payload) + "\n").encode("utf-8")
    _send_bytes(handler, status, body, "application/json")


def _send_bytes(
    handler: BaseHTTPRequestHandler,
    status: int,
    body: bytes,
    content_type: str,
) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
