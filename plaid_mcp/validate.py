"""Small checks shared by the finance tools and the link command."""

from datetime import date

from plaid_mcp.errors import PlaidMcpError


def required_text(value: object, label: str) -> str:
    """Return a stripped string, or raise when the value is missing."""
    if not isinstance(value, str):
        raise PlaidMcpError(f"{label} is required")
    cleaned = value.strip()
    if cleaned == "":
        raise PlaidMcpError(f"{label} is required")
    return cleaned


def optional_text(value: object, label: str) -> str:
    """Return a stripped string. None becomes an empty string."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise PlaidMcpError(f"{label} must be a string")
    return value.strip()


def bounded_int(value: object, label: str, low: int, high: int | None) -> int:
    """Return an int inside the inclusive range. Reject bool."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise PlaidMcpError(f"{label} must be a whole number")
    if value < low:
        raise PlaidMcpError(f"{label} must be at least {low}")
    if high is not None and value > high:
        raise PlaidMcpError(f"{label} must be at most {high}")
    return value


def iso_date(value: object, label: str) -> date:
    """Return a calendar date from YYYY-MM-DD."""
    if not isinstance(value, str):
        raise PlaidMcpError(f"{label} must be YYYY-MM-DD")
    cleaned = value.strip()
    if len(cleaned) != 10 or cleaned[4] != "-" or cleaned[7] != "-":
        raise PlaidMcpError(f"{label} must be YYYY-MM-DD")
    try:
        return date.fromisoformat(cleaned)
    except ValueError as error:
        raise PlaidMcpError(f"{label} must be YYYY-MM-DD") from error
