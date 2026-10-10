"""Plaid SDK gateway."""

from datetime import date

import plaid
import pytest

from plaid_mcp.client import PlaidGateway, build_gateway, plaid_host
from plaid_mcp.config import PlaidCredentials
from plaid_mcp.errors import PlaidMcpError
from tests.fakes import FakePlaidApi


def test_gateway_calls_accounts_transactions_and_liabilities():
    api = FakePlaidApi()
    api.accounts_response = {"accounts": [{"account_id": "acc-1"}]}
    gateway = PlaidGateway(api)
    start = date(2026, 10, 1)
    end = date(2026, 10, 2)

    accounts = gateway.accounts_get("access-1")
    transactions = gateway.transactions_get("access-1", start, end, 25, 5)
    liabilities = gateway.liabilities_get("access-1")

    assert accounts == {"accounts": [{"account_id": "acc-1"}]}
    assert transactions["total_transactions"] == 0
    assert liabilities == {"liabilities": {}}
    assert api.calls[0][1].access_token == "access-1"
    assert api.calls[1][1].access_token == "access-1"
    assert api.calls[1][1].start_date == start
    assert api.calls[1][1].end_date == end
    assert api.calls[1][1].options.count == 25
    assert api.calls[1][1].options.offset == 5
    assert api.calls[2][1].access_token == "access-1"


def test_gateway_creates_and_exchanges_a_link_token():
    api = FakePlaidApi()
    gateway = PlaidGateway(api)
    assert gateway.create_link_token() == "link-sandbox-token"
    assert gateway.exchange_public_token("public-sandbox") == ("access-sandbox", "item-1")
    link_request = api.calls[0][1]
    assert link_request.client_name == "Plaid MCP"
    assert link_request.user.client_user_id == "plaid-mcp"
    assert api.calls[1][1].public_token == "public-sandbox"


def test_gateway_rejects_a_missing_link_token():
    api = FakePlaidApi()
    api.link_response = {"link_token": "  "}
    with pytest.raises(PlaidMcpError, match="link token is required"):
        PlaidGateway(api).create_link_token()
    api.link_response = {}
    with pytest.raises(PlaidMcpError, match="link token is required"):
        PlaidGateway(api).create_link_token()


def test_gateway_rejects_a_missing_exchange_field():
    api = FakePlaidApi()
    api.exchange_response = {"item_id": "item-1"}
    with pytest.raises(PlaidMcpError, match="access token is required"):
        PlaidGateway(api).exchange_public_token("public-sandbox")
    api.exchange_response = {"access_token": "access-sandbox", "item_id": ""}
    with pytest.raises(PlaidMcpError, match="item id is required"):
        PlaidGateway(api).exchange_public_token("public-sandbox")


def test_build_gateway_selects_the_plaid_host():
    sandbox = build_gateway(PlaidCredentials("client", "secret", "sandbox"))
    production = build_gateway(PlaidCredentials("client", "secret", "production"))
    assert sandbox._api.api_client.configuration.host == plaid.Environment.Sandbox
    assert production._api.api_client.configuration.host == plaid.Environment.Production
    assert sandbox._api.api_client.configuration.api_key["clientId"] == "client"
    assert sandbox._api.api_client.configuration.api_key["secret"] == "secret"
    assert plaid_host("sandbox") == plaid.Environment.Sandbox
    with pytest.raises(PlaidMcpError, match="sandbox or production"):
        plaid_host("development")
