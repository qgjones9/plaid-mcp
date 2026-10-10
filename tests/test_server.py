"""MCP registration for Plaid tools."""

import importlib
import sys
import tomllib
from pathlib import Path

import pytest

import plaid_mcp
from plaid_mcp.config import PlaidCredentials
from plaid_mcp.errors import PlaidMcpError
from plaid_mcp.finance import PlaidFinance
from plaid_mcp.items import ItemStore, LinkedItem
from plaid_mcp.server import build_finance, build_server, main, make_tools
from tests.fakes import FakeGateway


def _finance(tmp_path) -> tuple[PlaidFinance, FakeGateway]:
    gateway = FakeGateway()
    store = ItemStore(tmp_path / "items.json")
    store.add(LinkedItem("item-1", "access-1", "Bank"))
    return PlaidFinance(gateway, store), gateway


def test_version_matches_pyproject():
    project = tomllib.loads(Path("pyproject.toml").read_text())
    assert plaid_mcp.__version__ == project["project"]["version"]
    assert plaid_mcp.__version__ == "0.0.1"


def test_tools_delegate_to_finance(tmp_path):
    finance, gateway = _finance(tmp_path)
    gateway.accounts_result = {"accounts": [{"account_id": "acc-1", "name": "Checking"}]}
    gateway.transactions_result = {
        "transactions": [{"transaction_id": "tx-1", "amount": 5}],
        "total_transactions": 1,
    }
    gateway.liabilities_result = {"liabilities": {"credit": [{"account_id": "card-1"}]}}
    tools = make_tools(finance)

    accounts = tools["get_accounts"]()
    transactions = tools["get_transactions"]("2026-10-01", "2026-10-02", 10, 1, "item-1")
    liabilities = tools["get_liabilities"]("item-1")

    assert accounts["accounts"][0]["accountId"] == "acc-1"
    assert transactions["transactions"][0]["amount"] == 5
    assert liabilities["credit"][0]["accountId"] == "card-1"
    assert gateway.calls[1][4] == 10
    assert gateway.calls[1][5] == 1


def test_server_registers_each_plaid_tool(tmp_path):
    finance, _gateway = _finance(tmp_path)
    server = build_server(finance, host="0.0.0.0", port=8016)
    names = {tool.name for tool in server._tool_manager.list_tools()}
    assert names == {"get_accounts", "get_transactions", "get_liabilities"}
    assert server.settings.host == "0.0.0.0"
    assert server.settings.port == 8016


def test_server_settings(monkeypatch):
    import plaid_mcp.server as server

    monkeypatch.delenv("PLAID_MCP_TRANSPORT", raising=False)
    monkeypatch.delenv("PLAID_MCP_HOST", raising=False)
    monkeypatch.delenv("PLAID_MCP_PORT", raising=False)
    defaults = server.server_settings()
    assert defaults.transport == "stdio"
    assert defaults.host == "127.0.0.1"
    assert defaults.port == 8006

    monkeypatch.setenv("PLAID_MCP_TRANSPORT", "  ")
    monkeypatch.setenv("PLAID_MCP_HOST", "  ")
    monkeypatch.setenv("PLAID_MCP_PORT", "  ")
    blank = server.server_settings()
    assert blank.transport == "stdio"
    assert blank.host == "127.0.0.1"
    assert blank.port == 8006

    monkeypatch.setenv("PLAID_MCP_TRANSPORT", "stdio")
    assert server.server_settings().transport == "stdio"

    monkeypatch.setenv("PLAID_MCP_TRANSPORT", "HTTP")
    monkeypatch.setenv("PLAID_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("PLAID_MCP_PORT", "9000")
    http = server.server_settings()
    assert http.transport == "http"
    assert http.host == "0.0.0.0"
    assert http.port == 9000

    monkeypatch.setenv("PLAID_MCP_TRANSPORT", "sse")
    with pytest.raises(PlaidMcpError, match="Unknown PLAID_MCP_TRANSPORT"):
        server.server_settings()


def test_build_finance_reads_the_config_directory(monkeypatch, tmp_path):
    import plaid_mcp.server as server

    monkeypatch.setattr(
        server,
        "load_credentials",
        lambda directory: PlaidCredentials("client", "secret", "sandbox"),
    )
    monkeypatch.setattr(server, "build_gateway", lambda credentials: FakeGateway())
    finance = build_finance(tmp_path)
    with pytest.raises(PlaidMcpError, match="plaid-mcp-link"):
        finance.get_accounts()

    monkeypatch.setattr(server, "default_config_dir", lambda: tmp_path)
    built = build_finance()
    with pytest.raises(PlaidMcpError, match="plaid-mcp-link"):
        built.get_accounts()


def test_main_starts_stdio_server(monkeypatch):
    import plaid_mcp.server as server

    started = {}

    class _Server:
        def run(self, transport="stdio"):
            started["transport"] = transport

    monkeypatch.delenv("PLAID_MCP_TRANSPORT", raising=False)
    monkeypatch.setattr(server, "build_finance", lambda: object())
    monkeypatch.setattr(server, "build_server", lambda finance, host, port: _Server())
    main()
    assert started["transport"] == "stdio"


def test_main_starts_http_server(monkeypatch):
    import plaid_mcp.server as server

    started = {}

    class _Server:
        def run(self, transport="stdio"):
            started["transport"] = transport

    monkeypatch.setenv("PLAID_MCP_TRANSPORT", "http")
    monkeypatch.setenv("PLAID_MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("PLAID_MCP_PORT", "8006")
    monkeypatch.setattr(server, "build_finance", lambda: object())

    def build(finance, host, port):
        started["host"] = host
        started["port"] = port
        return _Server()

    monkeypatch.setattr(server, "build_server", build)
    main()
    assert started == {"host": "0.0.0.0", "port": 8006, "transport": "streamable-http"}


def test_module_entry_point_calls_main(monkeypatch):
    import plaid_mcp.server as server

    called = {}
    monkeypatch.setattr(server, "main", lambda: called.setdefault("yes", True))
    sys.modules.pop("plaid_mcp.__main__", None)
    importlib.import_module("plaid_mcp.__main__")
    assert called["yes"] is True
