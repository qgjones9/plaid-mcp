"""Turn Plaid SDK responses into plain dicts, lists, and scalars."""

from plaid_mcp.errors import PlaidMcpError


def payload_dict(response: object) -> dict:
    """Return a JSON-like dict from a Plaid model or a dict."""
    payload = _unwrap(response)
    if not isinstance(payload, dict):
        raise PlaidMcpError("Plaid returned an unexpected response")
    return _plain_dict(payload)


def _unwrap(response: object) -> object:
    if isinstance(response, dict):
        return response
    to_dict = getattr(response, "to_dict", None)
    if to_dict is None:
        raise PlaidMcpError("Plaid returned an unexpected response")
    return to_dict()


def _plain(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return _plain_dict(value)
    if isinstance(value, (list, tuple)):
        return _plain_list(value)
    to_dict = getattr(value, "to_dict", None)
    if to_dict is not None:
        return _plain(to_dict())
    if hasattr(value, "isoformat"):
        return value.isoformat()
    enum_value = getattr(value, "value", None)
    if enum_value is not None:
        return _plain(enum_value)
    raise PlaidMcpError("Plaid returned an unexpected value")


def _plain_dict(value: dict) -> dict:
    result = {}
    for key, item in value.items():
        result[str(key)] = _plain(item)
    return result


def _plain_list(value: list | tuple) -> list:
    result = []
    for item in value:
        result.append(_plain(item))
    return result
