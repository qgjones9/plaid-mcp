"""Linked Plaid items stored outside the repository."""

import json
from dataclasses import dataclass
from pathlib import Path

from plaid_mcp.errors import PlaidMcpError
from plaid_mcp.validate import required_text


@dataclass(frozen=True)
class LinkedItem:
    """One Plaid Item and the access token that reads it."""

    item_id: str
    access_token: str
    institution_name: str


@dataclass(frozen=True)
class _Catalog:
    default_item_id: str | None
    items: list[LinkedItem]


class ItemStore:
    """Load and save linked items in items.json."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def resolve(self, item_id: str | None) -> LinkedItem:
        """Return the requested item, or the default when item_id is omitted."""
        catalog = self._load()
        if item_id is not None:
            return _require_item(catalog, required_text(item_id, "item_id"))
        return _default_item(catalog)

    def add(self, item: LinkedItem) -> None:
        """Insert or replace an item. The first saved item becomes the default."""
        catalog = self._load()
        items = _without(catalog.items, item.item_id)
        items.append(item)
        default_id = _next_default(catalog.default_item_id, items, item.item_id)
        self._write(default_id, items)

    def _load(self) -> _Catalog:
        if not self._path.is_file():
            return _Catalog(default_item_id=None, items=[])
        try:
            payload = json.loads(self._path.read_text())
        except json.JSONDecodeError as error:
            raise PlaidMcpError(f"items.json is not valid JSON: {self._path}") from error
        return _catalog_from_payload(payload, self._path)

    def _write(self, default_id: str, items: list[LinkedItem]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "default_item_id": default_id,
            "items": _item_rows(items),
        }
        text = json.dumps(payload, indent=2) + "\n"
        self._path.write_text(text)
        self._path.chmod(0o600)


def _require_item(catalog: _Catalog, item_id: str) -> LinkedItem:
    found = _find(catalog.items, item_id)
    if found is None:
        raise PlaidMcpError(f"Unknown item_id: {item_id}")
    return found


def _default_item(catalog: _Catalog) -> LinkedItem:
    if not catalog.items:
        raise PlaidMcpError("No linked items. Run plaid-mcp-link first.")
    if catalog.default_item_id is None:
        raise PlaidMcpError("No default item. Pass item_id.")
    found = _find(catalog.items, catalog.default_item_id)
    if found is None:
        raise PlaidMcpError("No default item. Pass item_id.")
    return found


def _find(items: list[LinkedItem], item_id: str) -> LinkedItem | None:
    for item in items:
        if item.item_id == item_id:
            return item
    return None


def _without(items: list[LinkedItem], item_id: str) -> list[LinkedItem]:
    kept = []
    for item in items:
        if item.item_id != item_id:
            kept.append(item)
    return kept


def _next_default(current: str | None, items: list[LinkedItem], new_id: str) -> str:
    if current is None:
        return new_id
    if _find(items, current) is None:
        return new_id
    return current


def _item_rows(items: list[LinkedItem]) -> list[dict]:
    rows = []
    for item in items:
        rows.append(
            {
                "item_id": item.item_id,
                "access_token": item.access_token,
                "institution_name": item.institution_name,
            }
        )
    return rows


def _catalog_from_payload(payload: object, path: Path) -> _Catalog:
    if not isinstance(payload, dict):
        raise PlaidMcpError(f"items.json must be an object: {path}")
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise PlaidMcpError(f"items.json items must be a list: {path}")
    items = []
    seen: set[str] = set()
    for raw in raw_items:
        item = _item_from_payload(raw, path)
        if item.item_id in seen:
            raise PlaidMcpError(f"Duplicate item_id in items.json: {item.item_id}")
        seen.add(item.item_id)
        items.append(item)
    default_id = _stored_default(payload.get("default_item_id"), path)
    return _Catalog(default_item_id=default_id, items=items)


def _item_from_payload(raw: object, path: Path) -> LinkedItem:
    if not isinstance(raw, dict):
        raise PlaidMcpError(f"items.json item must be an object: {path}")
    institution = raw.get("institution_name", "")
    if not isinstance(institution, str):
        raise PlaidMcpError(f"institution_name must be a string: {path}")
    return LinkedItem(
        item_id=required_text(raw.get("item_id"), "item_id"),
        access_token=required_text(raw.get("access_token"), "access_token"),
        institution_name=institution.strip(),
    )


def _stored_default(value: object, path: Path) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PlaidMcpError(f"default_item_id must be a string: {path}")
    cleaned = value.strip()
    if cleaned == "":
        return None
    return cleaned
