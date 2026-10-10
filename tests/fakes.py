"""In-memory Plaid stand-ins for tests."""

from datetime import date


class FakeGateway:
    """Records finance calls and returns plain dicts."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.accounts_result: dict = {"accounts": []}
        self.balances_result: dict = {"accounts": []}
        self.transactions_result: dict = {
            "accounts": [],
            "transactions": [],
            "total_transactions": 0,
        }
        self.liabilities_result: dict = {}
        self.link_token = "link-sandbox-token"
        self.exchanged = ("access-sandbox", "item-1")

    def accounts_get(self, access_token: str) -> dict:
        self.calls.append(("accounts_get", access_token))
        return self.accounts_result

    def accounts_balance_get(self, access_token: str, account_ids: list[str] | None) -> dict:
        self.calls.append(("accounts_balance_get", access_token, account_ids))
        return self.balances_result

    def transactions_get(
        self,
        access_token: str,
        start_date: date,
        end_date: date,
        count: int,
        offset: int,
    ) -> dict:
        self.calls.append(("transactions_get", access_token, start_date, end_date, count, offset))
        return self.transactions_result

    def liabilities_get(self, access_token: str) -> dict:
        self.calls.append(("liabilities_get", access_token))
        return self.liabilities_result

    def create_link_token(self) -> str:
        self.calls.append(("create_link_token",))
        return self.link_token

    def exchange_public_token(self, public_token: str) -> tuple[str, str]:
        self.calls.append(("exchange_public_token", public_token))
        return self.exchanged


class ResponseBody:
    """SDK-shaped response with to_dict."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def to_dict(self) -> dict:
        return self._payload


class FakePlaidApi:
    """Records SDK requests and returns ResponseBody objects."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.accounts_response: object = ResponseBody({"accounts": []})
        self.balances_response: object = ResponseBody({"accounts": []})
        self.transactions_response: object = ResponseBody(
            {"accounts": [], "transactions": [], "total_transactions": 0}
        )
        self.liabilities_response: object = ResponseBody({"liabilities": {}})
        self.link_response: object = ResponseBody({"link_token": "link-sandbox-token"})
        self.exchange_response: object = ResponseBody(
            {"access_token": "access-sandbox", "item_id": "item-1"}
        )

    def accounts_get(self, request: object) -> object:
        self.calls.append(("accounts_get", request))
        return self.accounts_response

    def accounts_balance_get(self, request: object) -> object:
        self.calls.append(("accounts_balance_get", request))
        return self.balances_response

    def transactions_get(self, request: object) -> object:
        self.calls.append(("transactions_get", request))
        return self.transactions_response

    def liabilities_get(self, request: object) -> object:
        self.calls.append(("liabilities_get", request))
        return self.liabilities_response

    def link_token_create(self, request: object) -> object:
        self.calls.append(("link_token_create", request))
        return self.link_response

    def item_public_token_exchange(self, request: object) -> object:
        self.calls.append(("item_public_token_exchange", request))
        return self.exchange_response
