"""Read accounts, transactions, and liabilities for one linked item."""

from plaid_mcp.errors import PlaidMcpError
from plaid_mcp.items import ItemStore
from plaid_mcp.validate import bounded_int, iso_date


class PlaidFinance:
    """Finance reads on an injected Plaid gateway and item store."""

    def __init__(self, gateway: object, items: ItemStore) -> None:
        self._gateway = gateway
        self._items = items

    def get_accounts(self, item_id: str | None = None) -> dict:
        """Return balances for each account on the item."""
        item = self._items.resolve(item_id)
        payload = self._gateway.accounts_get(item.access_token)
        accounts = _account_rows(payload.get("accounts"))
        return {"itemId": item.item_id, "accounts": accounts}

    def get_transactions(
        self,
        start_date: str,
        end_date: str,
        count: int = 100,
        offset: int = 0,
        item_id: str | None = None,
    ) -> dict:
        """Return transactions in the inclusive date range."""
        start = iso_date(start_date, "start_date")
        end = iso_date(end_date, "end_date")
        if start > end:
            raise PlaidMcpError("start_date must be on or before end_date")
        page_count = bounded_int(count, "count", 1, 500)
        page_offset = bounded_int(offset, "offset", 0, None)
        item = self._items.resolve(item_id)
        payload = self._gateway.transactions_get(
            item.access_token,
            start,
            end,
            page_count,
            page_offset,
        )
        accounts = _account_rows(payload.get("accounts"))
        transactions = _transaction_rows(payload.get("transactions"))
        return {
            "itemId": item.item_id,
            "accounts": accounts,
            "transactions": transactions,
            "totalTransactions": _total(payload.get("total_transactions"), transactions),
        }

    def get_liabilities(self, item_id: str | None = None) -> dict:
        """Return credit, mortgage, and student liabilities that Plaid sent."""
        item = self._items.resolve(item_id)
        payload = self._gateway.liabilities_get(item.access_token)
        result = {"itemId": item.item_id}
        liabilities = _optional_object(payload.get("liabilities"), "liabilities")
        if liabilities is None:
            return result
        _put_rows(result, "credit", _credit_rows(liabilities.get("credit")))
        _put_rows(result, "mortgage", _mortgage_rows(liabilities.get("mortgage")))
        _put_rows(result, "student", _student_rows(liabilities.get("student")))
        return result


def _account_rows(value: object) -> list:
    rows = []
    for row in _row_list(value, "accounts"):
        account = _object(row, "accounts")
        rows.append(_account_view(account))
    return rows


def _account_view(account: dict) -> dict:
    balances = _optional_object(account.get("balances"), "balances")
    if balances is None:
        balances = {}
    return {
        "accountId": account.get("account_id"),
        "name": account.get("name"),
        "officialName": account.get("official_name"),
        "type": account.get("type"),
        "subtype": account.get("subtype"),
        "mask": account.get("mask"),
        "balances": {
            "current": balances.get("current"),
            "available": balances.get("available"),
            "limit": balances.get("limit"),
            "isoCurrencyCode": balances.get("iso_currency_code"),
        },
    }


def _transaction_rows(value: object) -> list:
    rows = []
    for row in _row_list(value, "transactions"):
        transaction = _object(row, "transactions")
        rows.append(_transaction_view(transaction))
    return rows


def _transaction_view(transaction: dict) -> dict:
    return {
        "transactionId": transaction.get("transaction_id"),
        "accountId": transaction.get("account_id"),
        "date": transaction.get("date"),
        "name": transaction.get("name"),
        "merchantName": transaction.get("merchant_name"),
        "amount": transaction.get("amount"),
        "pending": transaction.get("pending"),
        "category": _row_list(transaction.get("category"), "category"),
        "paymentChannel": transaction.get("payment_channel"),
    }


def _total(value: object, transactions: list) -> int:
    if value is None:
        return len(transactions)
    if isinstance(value, bool) or not isinstance(value, int):
        raise PlaidMcpError("total_transactions must be a whole number")
    return value


def _credit_rows(value: object) -> list:
    rows = []
    for row in _row_list(value, "credit"):
        credit = _object(row, "credit")
        rows.append(_credit_view(credit))
    return rows


def _credit_view(credit: dict) -> dict:
    return {
        "accountId": credit.get("account_id"),
        "isOverdue": credit.get("is_overdue"),
        "lastPaymentAmount": credit.get("last_payment_amount"),
        "lastPaymentDate": credit.get("last_payment_date"),
        "lastStatementBalance": credit.get("last_statement_balance"),
        "minimumPaymentAmount": credit.get("minimum_payment_amount"),
        "nextPaymentDueDate": credit.get("next_payment_due_date"),
        "aprs": _apr_rows(credit.get("aprs")),
    }


def _apr_rows(value: object) -> list:
    rows = []
    for row in _row_list(value, "aprs"):
        apr = _object(row, "aprs")
        rows.append(
            {
                "aprPercentage": apr.get("apr_percentage"),
                "aprType": apr.get("apr_type"),
                "balanceSubjectToApr": apr.get("balance_subject_to_apr"),
                "interestChargeAmount": apr.get("interest_charge_amount"),
            }
        )
    return rows


def _mortgage_rows(value: object) -> list:
    rows = []
    for row in _row_list(value, "mortgage"):
        mortgage = _object(row, "mortgage")
        rows.append(_mortgage_view(mortgage))
    return rows


def _mortgage_view(mortgage: dict) -> dict:
    return {
        "accountId": mortgage.get("account_id"),
        "interestRate": _interest_rate(mortgage.get("interest_rate")),
        "loanTypeDescription": mortgage.get("loan_type_description"),
        "nextMonthlyPayment": mortgage.get("next_monthly_payment"),
        "nextPaymentDueDate": mortgage.get("next_payment_due_date"),
        "originationPrincipalAmount": mortgage.get("origination_principal_amount"),
        "pastDueAmount": mortgage.get("past_due_amount"),
        "ytdInterestPaid": mortgage.get("ytd_interest_paid"),
        "ytdPrincipalPaid": mortgage.get("ytd_principal_paid"),
        "propertyAddress": _address(mortgage.get("property_address")),
    }


def _interest_rate(value: object) -> dict | None:
    rate = _optional_object(value, "interest_rate")
    if rate is None:
        return None
    return {"percentage": rate.get("percentage"), "type": rate.get("type")}


def _address(value: object) -> dict | None:
    address = _optional_object(value, "property_address")
    if address is None:
        return None
    return {
        "street": address.get("street"),
        "city": address.get("city"),
        "region": address.get("region"),
        "postalCode": address.get("postal_code"),
        "country": address.get("country"),
    }


def _student_rows(value: object) -> list:
    rows = []
    for row in _row_list(value, "student"):
        student = _object(row, "student")
        rows.append(_student_view(student))
    return rows


def _student_view(student: dict) -> dict:
    return {
        "accountId": student.get("account_id"),
        "loanName": student.get("loan_name"),
        "interestRatePercentage": student.get("interest_rate_percentage"),
        "isOverdue": student.get("is_overdue"),
        "minimumPaymentAmount": student.get("minimum_payment_amount"),
        "nextPaymentDueDate": student.get("next_payment_due_date"),
        "originationPrincipalAmount": student.get("origination_principal_amount"),
        "outstandingInterestAmount": student.get("outstanding_interest_amount"),
        "expectedPayoffDate": student.get("expected_payoff_date"),
        "ytdInterestPaid": student.get("ytd_interest_paid"),
        "ytdPrincipalPaid": student.get("ytd_principal_paid"),
        "loanStatus": _loan_status(student.get("loan_status")),
        "repaymentPlan": _repayment_plan(student.get("repayment_plan")),
    }


def _loan_status(value: object) -> dict | None:
    status = _optional_object(value, "loan_status")
    if status is None:
        return None
    return {"type": status.get("type"), "endDate": status.get("end_date")}


def _repayment_plan(value: object) -> dict | None:
    plan = _optional_object(value, "repayment_plan")
    if plan is None:
        return None
    return {"type": plan.get("type"), "description": plan.get("description")}


def _put_rows(result: dict, name: str, rows: list) -> None:
    if rows:
        result[name] = rows


def _row_list(value: object, label: str) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    raise PlaidMcpError(f"{label} must be a list")


def _object(value: object, label: str) -> dict:
    if isinstance(value, dict):
        return value
    raise PlaidMcpError(f"{label} must be an object")


def _optional_object(value: object, label: str) -> dict | None:
    if value is None:
        return None
    return _object(value, label)
