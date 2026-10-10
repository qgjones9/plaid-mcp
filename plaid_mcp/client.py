"""Plaid API client. Credentials stay outside the repository."""

import plaid
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.liabilities_get_request import LiabilitiesGetRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

from plaid_mcp.config import PRODUCTION, SANDBOX, PlaidCredentials
from plaid_mcp.errors import PlaidMcpError
from plaid_mcp.payload import payload_dict
from plaid_mcp.validate import required_text

_CLIENT_NAME = "Plaid MCP"
_CLIENT_USER_ID = "plaid-mcp"
_LINK_PRODUCTS = ("transactions", "liabilities")


class PlaidGateway:
    """Plaid calls used by the finance tools and the link command."""

    def __init__(self, api: object) -> None:
        self._api = api

    def accounts_get(self, access_token: str) -> dict:
        """Call /accounts/get."""
        request = AccountsGetRequest(access_token=access_token)
        return payload_dict(self._api.accounts_get(request))

    def transactions_get(
        self,
        access_token: str,
        start_date: object,
        end_date: object,
        count: int,
        offset: int,
    ) -> dict:
        """Call /transactions/get."""
        options = TransactionsGetRequestOptions(count=count, offset=offset)
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=options,
        )
        return payload_dict(self._api.transactions_get(request))

    def liabilities_get(self, access_token: str) -> dict:
        """Call /liabilities/get."""
        request = LiabilitiesGetRequest(access_token=access_token)
        return payload_dict(self._api.liabilities_get(request))

    def create_link_token(self) -> str:
        """Call /link/token/create for transactions and liabilities."""
        request = LinkTokenCreateRequest(
            products=_products(),
            client_name=_CLIENT_NAME,
            country_codes=[CountryCode("US")],
            language="en",
            user=LinkTokenCreateRequestUser(client_user_id=_CLIENT_USER_ID),
        )
        payload = payload_dict(self._api.link_token_create(request))
        return required_text(payload.get("link_token"), "link token")

    def exchange_public_token(self, public_token: str) -> tuple[str, str]:
        """Call /item/public_token/exchange. Returns access token and item id."""
        request = ItemPublicTokenExchangeRequest(public_token=public_token)
        payload = payload_dict(self._api.item_public_token_exchange(request))
        access_token = required_text(payload.get("access_token"), "access token")
        item_id = required_text(payload.get("item_id"), "item id")
        return access_token, item_id


def build_gateway(credentials: PlaidCredentials) -> PlaidGateway:
    """Build a Plaid client from a client id, secret, and environment name."""
    configuration = plaid.Configuration(
        host=plaid_host(credentials.environment),
        api_key={
            "clientId": credentials.client_id,
            "secret": credentials.secret,
        },
    )
    api_client = plaid.ApiClient(configuration)
    return PlaidGateway(plaid_api.PlaidApi(api_client))


def plaid_host(environment: str):
    """Return the Plaid host for sandbox or production."""
    if environment == SANDBOX:
        return plaid.Environment.Sandbox
    if environment == PRODUCTION:
        return plaid.Environment.Production
    raise PlaidMcpError("PLAID_ENV must be sandbox or production")


def _products() -> list:
    products = []
    for name in _LINK_PRODUCTS:
        products.append(Products(name))
    return products
