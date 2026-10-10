"""Finance tool results."""

from datetime import date

import pytest

from plaid_mcp.errors import PlaidMcpError
from plaid_mcp.finance import PlaidFinance
from plaid_mcp.items import ItemStore, LinkedItem
from tests.fakes import FakeGateway


def _finance(tmp_path, gateway: FakeGateway | None = None) -> tuple[PlaidFinance, FakeGateway]:
    store = ItemStore(tmp_path / "items.json")
    store.add(LinkedItem("item-1", "access-1", "Bank"))
    store.add(LinkedItem("item-2", "access-2", "Other"))
    client = gateway or FakeGateway()
    return PlaidFinance(client, store), client


def test_get_accounts(tmp_path):
    finance, gateway = _finance(tmp_path)
    gateway.accounts_result = {
        "accounts": [
            {
                "account_id": "acc-1",
                "name": "Plaid Checking",
                "official_name": "Plaid Gold",
                "type": "depository",
                "subtype": "checking",
                "mask": "0000",
                "balances": {
                    "current": 110,
                    "available": 100,
                    "limit": None,
                    "iso_currency_code": "USD",
                },
            },
            {"account_id": "acc-2", "name": "No balances"},
        ]
    }
    result = finance.get_accounts()
    assert result["itemId"] == "item-1"
    assert result["accounts"][0]["balances"]["current"] == 110
    assert result["accounts"][0]["officialName"] == "Plaid Gold"
    assert result["accounts"][1]["balances"]["current"] is None
    assert gateway.calls == [("accounts_get", "access-1")]
    assert finance.get_accounts("item-2")["itemId"] == "item-2"


def test_get_accounts_rejects_a_bad_payload(tmp_path):
    finance, gateway = _finance(tmp_path)
    gateway.accounts_result = {"accounts": "nope"}
    with pytest.raises(PlaidMcpError, match="accounts must be a list"):
        finance.get_accounts()
    gateway.accounts_result = {"accounts": ["nope"]}
    with pytest.raises(PlaidMcpError, match="accounts must be an object"):
        finance.get_accounts()
    gateway.accounts_result = {"accounts": [{"balances": "nope"}]}
    with pytest.raises(PlaidMcpError, match="balances must be an object"):
        finance.get_accounts()


def test_get_transactions(tmp_path):
    finance, gateway = _finance(tmp_path)
    gateway.transactions_result = {
        "accounts": [{"account_id": "acc-1", "name": "Checking"}],
        "transactions": [
            {
                "transaction_id": "tx-1",
                "account_id": "acc-1",
                "date": "2026-10-01",
                "name": "Uber",
                "merchant_name": "Uber",
                "amount": 5.4,
                "pending": False,
                "category": ["Travel", "Taxi"],
                "payment_channel": "in store",
            }
        ],
        "total_transactions": 8,
    }
    result = finance.get_transactions(" 2026-10-01 ", "2026-10-03", count=500, offset=20)
    assert result["itemId"] == "item-1"
    assert result["totalTransactions"] == 8
    assert result["transactions"][0]["merchantName"] == "Uber"
    assert result["transactions"][0]["category"] == ["Travel", "Taxi"]
    assert result["accounts"][0]["accountId"] == "acc-1"
    call = gateway.calls[0]
    assert call[1] == "access-1"
    assert call[2] == date(2026, 10, 1)
    assert call[3] == date(2026, 10, 3)
    assert call[4] == 500
    assert call[5] == 20


def test_get_transactions_fills_a_missing_total(tmp_path):
    finance, gateway = _finance(tmp_path)
    gateway.transactions_result = {"transactions": [{"transaction_id": "tx-1"}]}
    result = finance.get_transactions("2026-10-01", "2026-10-01", item_id="item-2")
    assert result["itemId"] == "item-2"
    assert result["totalTransactions"] == 1
    assert result["transactions"][0]["category"] == []


def test_get_transactions_rejects_bad_input(tmp_path):
    finance, gateway = _finance(tmp_path)
    with pytest.raises(PlaidMcpError, match="start_date must be YYYY-MM-DD"):
        finance.get_transactions(1, "2026-10-01")
    with pytest.raises(PlaidMcpError, match="end_date must be YYYY-MM-DD"):
        finance.get_transactions("2026-10-01", "10/01/2026")
    with pytest.raises(PlaidMcpError, match="end_date must be YYYY-MM-DD"):
        finance.get_transactions("2026-10-01", "2026-02-31")
    with pytest.raises(PlaidMcpError, match="on or before"):
        finance.get_transactions("2026-10-03", "2026-10-01")
    with pytest.raises(PlaidMcpError, match="count must be a whole number"):
        finance.get_transactions("2026-10-01", "2026-10-01", count=True)
    with pytest.raises(PlaidMcpError, match="count must be a whole number"):
        finance.get_transactions("2026-10-01", "2026-10-01", count=1.5)
    with pytest.raises(PlaidMcpError, match="count must be at least 1"):
        finance.get_transactions("2026-10-01", "2026-10-01", count=0)
    with pytest.raises(PlaidMcpError, match="count must be at most 500"):
        finance.get_transactions("2026-10-01", "2026-10-01", count=501)
    with pytest.raises(PlaidMcpError, match="offset must be a whole number"):
        finance.get_transactions("2026-10-01", "2026-10-01", offset=False)
    with pytest.raises(PlaidMcpError, match="offset must be at least 0"):
        finance.get_transactions("2026-10-01", "2026-10-01", offset=-1)
    gateway.transactions_result = {"transactions": "nope"}
    with pytest.raises(PlaidMcpError, match="transactions must be a list"):
        finance.get_transactions("2026-10-01", "2026-10-01")
    gateway.transactions_result = {"transactions": ["nope"]}
    with pytest.raises(PlaidMcpError, match="transactions must be an object"):
        finance.get_transactions("2026-10-01", "2026-10-01")
    gateway.transactions_result = {"transactions": [{"category": "Travel"}]}
    with pytest.raises(PlaidMcpError, match="category must be a list"):
        finance.get_transactions("2026-10-01", "2026-10-01")
    gateway.transactions_result = {"transactions": [], "total_transactions": True}
    with pytest.raises(PlaidMcpError, match="total_transactions must be a whole number"):
        finance.get_transactions("2026-10-01", "2026-10-01")
    gateway.transactions_result = {"transactions": [], "total_transactions": "1"}
    with pytest.raises(PlaidMcpError, match="total_transactions must be a whole number"):
        finance.get_transactions("2026-10-01", "2026-10-01")


def test_get_liabilities(tmp_path):
    finance, gateway = _finance(tmp_path)
    gateway.liabilities_result = {
        "liabilities": {
            "credit": [
                {
                    "account_id": "card-1",
                    "is_overdue": False,
                    "last_payment_amount": 25,
                    "last_payment_date": "2026-09-01",
                    "last_statement_balance": 400,
                    "minimum_payment_amount": 25,
                    "next_payment_due_date": "2026-10-20",
                    "aprs": [
                        {
                            "apr_percentage": 15.99,
                            "apr_type": "purchase_apr",
                            "balance_subject_to_apr": 400,
                            "interest_charge_amount": 4,
                        }
                    ],
                }
            ],
            "mortgage": [
                {
                    "account_id": "home-1",
                    "interest_rate": {"percentage": 3.5, "type": "fixed"},
                    "loan_type_description": "conventional",
                    "next_monthly_payment": 1200,
                    "next_payment_due_date": "2026-11-01",
                    "origination_principal_amount": 200000,
                    "past_due_amount": 0,
                    "ytd_interest_paid": 3000,
                    "ytd_principal_paid": 4000,
                    "property_address": {
                        "street": "1 Main",
                        "city": "Town",
                        "region": "VA",
                        "postal_code": "20120",
                        "country": "US",
                    },
                }
            ],
            "student": [
                {
                    "account_id": "loan-1",
                    "loan_name": "Student",
                    "interest_rate_percentage": 4.5,
                    "is_overdue": False,
                    "minimum_payment_amount": 50,
                    "next_payment_due_date": "2026-11-01",
                    "origination_principal_amount": 10000,
                    "outstanding_interest_amount": 12,
                    "expected_payoff_date": "2030-01-01",
                    "ytd_interest_paid": 100,
                    "ytd_principal_paid": 200,
                    "loan_status": {"type": "repayment", "end_date": None},
                    "repayment_plan": {"type": "standard", "description": "Standard"},
                }
            ],
        }
    }
    result = finance.get_liabilities("item-1")
    assert result["credit"][0]["aprs"][0]["aprType"] == "purchase_apr"
    assert result["mortgage"][0]["propertyAddress"]["postalCode"] == "20120"
    assert result["mortgage"][0]["interestRate"]["percentage"] == 3.5
    assert result["student"][0]["loanStatus"]["type"] == "repayment"
    assert result["student"][0]["repaymentPlan"]["description"] == "Standard"


def test_get_liabilities_omits_empty_groups(tmp_path):
    finance, gateway = _finance(tmp_path)
    gateway.liabilities_result = {}
    assert finance.get_liabilities() == {"itemId": "item-1"}
    gateway.liabilities_result = {"liabilities": {"credit": [], "mortgage": None, "student": []}}
    result = finance.get_liabilities()
    assert result == {"itemId": "item-1"}
    gateway.liabilities_result = {
        "liabilities": {
            "mortgage": [{"account_id": "home-1"}],
            "student": [{"account_id": "loan-1"}],
        }
    }
    sparse = finance.get_liabilities()
    assert "credit" not in sparse
    assert sparse["mortgage"][0]["interestRate"] is None
    assert sparse["mortgage"][0]["propertyAddress"] is None
    assert sparse["student"][0]["loanStatus"] is None
    assert sparse["student"][0]["repaymentPlan"] is None


def test_get_liabilities_rejects_bad_rows(tmp_path):
    finance, gateway = _finance(tmp_path)
    gateway.liabilities_result = {"liabilities": []}
    with pytest.raises(PlaidMcpError, match="liabilities must be an object"):
        finance.get_liabilities()
    gateway.liabilities_result = {"liabilities": {"credit": "nope"}}
    with pytest.raises(PlaidMcpError, match="credit must be a list"):
        finance.get_liabilities()
    gateway.liabilities_result = {"liabilities": {"credit": ["nope"]}}
    with pytest.raises(PlaidMcpError, match="credit must be an object"):
        finance.get_liabilities()
    gateway.liabilities_result = {"liabilities": {"credit": [{"aprs": ["nope"]}]}}
    with pytest.raises(PlaidMcpError, match="aprs must be an object"):
        finance.get_liabilities()
    gateway.liabilities_result = {"liabilities": {"mortgage": ["nope"]}}
    with pytest.raises(PlaidMcpError, match="mortgage must be an object"):
        finance.get_liabilities()
    gateway.liabilities_result = {"liabilities": {"mortgage": [{"interest_rate": "nope"}]}}
    with pytest.raises(PlaidMcpError, match="interest_rate must be an object"):
        finance.get_liabilities()
    gateway.liabilities_result = {"liabilities": {"mortgage": [{"property_address": "nope"}]}}
    with pytest.raises(PlaidMcpError, match="property_address must be an object"):
        finance.get_liabilities()
    gateway.liabilities_result = {"liabilities": {"student": ["nope"]}}
    with pytest.raises(PlaidMcpError, match="student must be an object"):
        finance.get_liabilities()
    gateway.liabilities_result = {"liabilities": {"student": [{"loan_status": "nope"}]}}
    with pytest.raises(PlaidMcpError, match="loan_status must be an object"):
        finance.get_liabilities()
    gateway.liabilities_result = {"liabilities": {"student": [{"repayment_plan": "nope"}]}}
    with pytest.raises(PlaidMcpError, match="repayment_plan must be an object"):
        finance.get_liabilities()
