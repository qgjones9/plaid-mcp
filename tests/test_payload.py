"""Plain Plaid payloads."""

from datetime import date

import pytest

from plaid_mcp.errors import PlaidMcpError
from plaid_mcp.payload import payload_dict


class _Model:
    def __init__(self, payload) -> None:
        self._payload = payload

    def to_dict(self):
        return self._payload


class _Kind:
    def __init__(self, value) -> None:
        self.value = value


def test_payload_dict_accepts_a_dict():
    assert payload_dict({"accounts": []}) == {"accounts": []}


def test_payload_dict_accepts_to_dict():
    assert payload_dict(_Model({"ok": True})) == {"ok": True}


def test_payload_flattens_nested_values():
    payload = payload_dict(
        {
            "empty": {},
            "none": None,
            "flag": True,
            "count": 2,
            "amount": 1.5,
            "name": "checking",
            "when": date(2026, 10, 1),
            "items": [],
            "pair": ("a", "b"),
            "nested": [_Model({"kind": _Kind("depository")})],
        }
    )
    assert payload["empty"] == {}
    assert payload["none"] is None
    assert payload["flag"] is True
    assert payload["count"] == 2
    assert payload["amount"] == 1.5
    assert payload["when"] == "2026-10-01"
    assert payload["items"] == []
    assert payload["pair"] == ["a", "b"]
    assert payload["nested"] == [{"kind": "depository"}]


def test_payload_rejects_a_non_dict_response():
    with pytest.raises(PlaidMcpError, match="unexpected response"):
        payload_dict(object())
    with pytest.raises(PlaidMcpError, match="unexpected response"):
        payload_dict(_Model(["nope"]))


def test_payload_rejects_an_unknown_value():
    with pytest.raises(PlaidMcpError, match="unexpected value"):
        payload_dict({"bad": object()})
