"""Item store."""

import json

import pytest

from plaid_mcp.errors import PlaidMcpError
from plaid_mcp.items import ItemStore, LinkedItem


def _item(item_id: str = "item-1", token: str = "access-1", name: str = "Bank") -> LinkedItem:
    return LinkedItem(item_id=item_id, access_token=token, institution_name=name)


def test_missing_file_has_no_items(tmp_path):
    store = ItemStore(tmp_path / "items.json")
    with pytest.raises(PlaidMcpError, match="plaid-mcp-link"):
        store.resolve(None)


def test_add_first_item_becomes_default_and_is_private(tmp_path):
    path = tmp_path / "nested" / "items.json"
    store = ItemStore(path)
    store.add(_item())
    resolved = store.resolve(None)
    assert resolved.access_token == "access-1"
    assert resolved.institution_name == "Bank"
    mode = path.stat().st_mode & 0o777
    assert mode == 0o600
    saved = json.loads(path.read_text())
    assert saved["default_item_id"] == "item-1"


def test_second_item_keeps_the_default(tmp_path):
    store = ItemStore(tmp_path / "items.json")
    store.add(_item())
    store.add(_item("item-2", "access-2", "Other"))
    assert store.resolve(None).item_id == "item-1"
    assert store.resolve("item-2").access_token == "access-2"


def test_add_replaces_the_same_item(tmp_path):
    store = ItemStore(tmp_path / "items.json")
    store.add(_item())
    store.add(_item(token="access-new", name="Renamed"))
    resolved = store.resolve(" item-1 ")
    assert resolved.access_token == "access-new"
    assert resolved.institution_name == "Renamed"
    saved = json.loads((tmp_path / "items.json").read_text())
    assert len(saved["items"]) == 1


def test_add_replaces_a_dangling_default(tmp_path):
    path = tmp_path / "items.json"
    path.write_text(
        json.dumps(
            {
                "default_item_id": "gone",
                "items": [
                    {
                        "item_id": "item-1",
                        "access_token": "access-1",
                        "institution_name": "Bank",
                    }
                ],
            }
        )
    )
    store = ItemStore(path)
    store.add(_item("item-2", "access-2", "Other"))
    assert store.resolve(None).item_id == "item-2"


def test_unknown_item(tmp_path):
    store = ItemStore(tmp_path / "items.json")
    store.add(_item())
    with pytest.raises(PlaidMcpError, match="Unknown item_id"):
        store.resolve("missing")


def test_blank_item_id(tmp_path):
    store = ItemStore(tmp_path / "items.json")
    store.add(_item())
    with pytest.raises(PlaidMcpError, match="item_id is required"):
        store.resolve("  ")
    with pytest.raises(PlaidMcpError, match="item_id is required"):
        store.resolve(1)


def test_no_default_item(tmp_path):
    path = tmp_path / "items.json"
    path.write_text(
        json.dumps(
            {
                "default_item_id": None,
                "items": [
                    {
                        "item_id": "item-1",
                        "access_token": "access-1",
                        "institution_name": "Bank",
                    }
                ],
            }
        )
    )
    store = ItemStore(path)
    with pytest.raises(PlaidMcpError, match="No default item"):
        store.resolve(None)
    assert store.resolve("item-1").item_id == "item-1"


def test_default_item_does_not_match(tmp_path):
    path = tmp_path / "items.json"
    path.write_text(
        json.dumps(
            {
                "default_item_id": "gone",
                "items": [
                    {
                        "item_id": "item-1",
                        "access_token": "access-1",
                        "institution_name": "Bank",
                    }
                ],
            }
        )
    )
    with pytest.raises(PlaidMcpError, match="No default item"):
        ItemStore(path).resolve(None)


def test_empty_catalog_file(tmp_path):
    path = tmp_path / "items.json"
    path.write_text(json.dumps({"default_item_id": None, "items": []}))
    with pytest.raises(PlaidMcpError, match="plaid-mcp-link"):
        ItemStore(path).resolve(None)


def test_items_json_must_be_json(tmp_path):
    path = tmp_path / "items.json"
    path.write_text("{")
    with pytest.raises(PlaidMcpError, match="not valid JSON"):
        ItemStore(path).resolve(None)


def test_items_json_must_be_an_object(tmp_path):
    path = tmp_path / "items.json"
    path.write_text("[]")
    with pytest.raises(PlaidMcpError, match="must be an object"):
        ItemStore(path).resolve(None)


def test_items_must_be_a_list(tmp_path):
    path = tmp_path / "items.json"
    path.write_text(json.dumps({"items": {}}))
    with pytest.raises(PlaidMcpError, match="items must be a list"):
        ItemStore(path).resolve(None)


def test_item_must_be_an_object(tmp_path):
    path = tmp_path / "items.json"
    path.write_text(json.dumps({"items": ["nope"]}))
    with pytest.raises(PlaidMcpError, match="item must be an object"):
        ItemStore(path).resolve(None)


def test_institution_name_must_be_a_string(tmp_path):
    path = tmp_path / "items.json"
    path.write_text(
        json.dumps(
            {
                "items": [
                    {"item_id": "item-1", "access_token": "access-1", "institution_name": 1}
                ]
            }
        )
    )
    with pytest.raises(PlaidMcpError, match="institution_name must be a string"):
        ItemStore(path).resolve("item-1")


def test_missing_institution_name_is_blank(tmp_path):
    path = tmp_path / "items.json"
    path.write_text(
        json.dumps(
            {
                "default_item_id": "item-1",
                "items": [{"item_id": "item-1", "access_token": "access-1"}],
            }
        )
    )
    assert ItemStore(path).resolve(None).institution_name == ""


def test_institution_name_is_stripped(tmp_path):
    path = tmp_path / "items.json"
    path.write_text(
        json.dumps(
            {
                "default_item_id": "item-1",
                "items": [
                    {
                        "item_id": "item-1",
                        "access_token": " access-1 ",
                        "institution_name": " Bank ",
                    }
                ],
            }
        )
    )
    item = ItemStore(path).resolve(None)
    assert item.institution_name == "Bank"
    assert item.access_token == "access-1"


def test_duplicate_item_id(tmp_path):
    path = tmp_path / "items.json"
    row = {"item_id": "item-1", "access_token": "access-1", "institution_name": "Bank"}
    path.write_text(json.dumps({"items": [row, row]}))
    with pytest.raises(PlaidMcpError, match="Duplicate item_id"):
        ItemStore(path).resolve("item-1")


def test_item_fields_are_required(tmp_path):
    path = tmp_path / "items.json"
    path.write_text(json.dumps({"items": [{"access_token": "access-1"}]}))
    with pytest.raises(PlaidMcpError, match="item_id is required"):
        ItemStore(path).resolve(None)
    path.write_text(json.dumps({"items": [{"item_id": "item-1", "access_token": "  "}]}))
    with pytest.raises(PlaidMcpError, match="access_token is required"):
        ItemStore(path).resolve(None)


def test_default_item_id_must_be_a_string(tmp_path):
    path = tmp_path / "items.json"
    path.write_text(
        json.dumps(
            {
                "default_item_id": 1,
                "items": [{"item_id": "item-1", "access_token": "access-1"}],
            }
        )
    )
    with pytest.raises(PlaidMcpError, match="default_item_id must be a string"):
        ItemStore(path).resolve(None)


def test_blank_default_item_id_means_no_default(tmp_path):
    path = tmp_path / "items.json"
    path.write_text(
        json.dumps(
            {
                "default_item_id": "  ",
                "items": [{"item_id": "item-1", "access_token": "access-1"}],
            }
        )
    )
    with pytest.raises(PlaidMcpError, match="No default item"):
        ItemStore(path).resolve(None)
