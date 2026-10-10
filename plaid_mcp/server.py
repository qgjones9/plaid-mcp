"""MCP tools for Plaid."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from plaid_mcp.client import build_gateway
from plaid_mcp.config import (
    ServerSettings,
    default_config_dir,
    environment_port,
    environment_text,
    load_credentials,
)
from plaid_mcp.errors import PlaidMcpError
from plaid_mcp.finance import PlaidFinance
from plaid_mcp.items import ItemStore


def make_tools(finance: PlaidFinance) -> dict:
    """Return the Plaid tools an agent can call."""

    def get_accounts(item_id: str | None = None) -> dict:
        """Fetch balances with /accounts/get.

        item_id is optional. Omit it to use the default linked item.
        """
        return finance.get_accounts(item_id)

    def get_balances(
        item_id: str | None = None,
        account_ids: list[str] | None = None,
    ) -> dict:
        """Fetch live balances with /accounts/balance/get.

        item_id is optional. Omit it to use the default linked item.
        account_ids is optional. Omit it to refresh every account on the item.
        """
        return finance.get_balances(item_id, account_ids)

    def get_transactions(
        start_date: str,
        end_date: str,
        count: int = 100,
        offset: int = 0,
        item_id: str | None = None,
    ) -> dict:
        """Fetch transactions with /transactions/get.

        start_date and end_date are YYYY-MM-DD. count is from 1 to 500 and
        defaults to 100. offset defaults to 0. item_id is optional. Omit
        item_id to use the default linked item.
        """
        return finance.get_transactions(
            start_date=start_date,
            end_date=end_date,
            count=count,
            offset=offset,
            item_id=item_id,
        )

    def get_liabilities(item_id: str | None = None) -> dict:
        """Fetch credit, mortgage, and student liabilities with /liabilities/get.

        item_id is optional. Omit it to use the default linked item. Empty
        liability groups are omitted.
        """
        return finance.get_liabilities(item_id)

    return {
        "get_accounts": get_accounts,
        "get_balances": get_balances,
        "get_transactions": get_transactions,
        "get_liabilities": get_liabilities,
    }


def server_settings() -> ServerSettings:
    """Read the listen mode from the environment.

    PLAID_MCP_TRANSPORT=stdio keeps the process on stdin.
    PLAID_MCP_TRANSPORT=http listens for Cursor on HTTP.
    The default HTTP port is 8006 so this server can run beside Drive on 8000,
    Gmail on 8001, Docs on 8002, Calendar on 8003, Tasks on 8004, and Sheets
    on 8005.
    """
    raw_transport = environment_text("PLAID_MCP_TRANSPORT", "stdio").lower()
    if raw_transport == "stdio":
        transport = "stdio"
    elif raw_transport == "http":
        transport = "http"
    else:
        raise PlaidMcpError(f"Unknown PLAID_MCP_TRANSPORT: {raw_transport}")
    host = environment_text("PLAID_MCP_HOST", "127.0.0.1")
    port = environment_port("PLAID_MCP_PORT", 8006)
    return ServerSettings(transport=transport, host=host, port=port)


def build_finance(config_dir: Path | None = None) -> PlaidFinance:
    """Build a finance reader from the config directory."""
    directory = config_dir or default_config_dir()
    credentials = load_credentials(directory)
    gateway = build_gateway(credentials)
    return PlaidFinance(gateway, ItemStore(directory / "items.json"))


def build_server(
    finance: PlaidFinance,
    *,
    host: str = "127.0.0.1",
    port: int = 8006,
) -> FastMCP:
    """Register Plaid tools. host and port apply only to HTTP mode."""
    mcp = FastMCP("plaid-mcp", host=host, port=port)
    for tool in make_tools(finance).values():
        mcp.tool()(tool)
    return mcp


def main() -> None:
    """Start the Plaid MCP server on stdio, or on HTTP when configured."""
    settings = server_settings()
    server = build_server(
        build_finance(),
        host=settings.host,
        port=settings.port,
    )
    if settings.transport == "http":
        server.run(transport="streamable-http")
    else:
        server.run()
