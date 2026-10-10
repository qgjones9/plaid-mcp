# Plaid MCP: initial server

**Target release:** 0.0.1  
**Created:** 2026-10-10

## Checklist

- [x] `PlaidFinance` tools: `get_accounts`, `get_transactions`, `get_liabilities`
- [x] Item store at `{config_dir}/items.json` (outside the git tree)
- [x] Host-only `plaid-mcp-link` (Link token, local page, public token exchange)
- [x] MCP server on stdio, or HTTP on port 8006
- [x] Tests at 100% line and branch coverage
- [x] CHANGELOG, `pyproject.toml`, `AGENTS.md`, Docker, and CI

## Goal

A public Python MCP server that reads Plaid balances, transactions, and liabilities. Secrets and access tokens stay in `~/.config/plaid-mcp/` or in the environment. The agent surface is read-only. Linking a bank is a one-time host command, not an MCP tool.

Sandbox is the default environment. Production is selected with `PLAID_ENV=production`.

## Out of scope

Webhooks, investments, assets, income, transfers, item remove, and any product beyond transactions and liabilities.

## Tool contract

### `get_accounts`

| Parameter | Purpose |
| --- | --- |
| `item_id` | Optional. Omit it to use the default linked item. |

Calls `/accounts/get`.

```json
{
  "itemId": "item-id",
  "accounts": [
    {
      "accountId": "account-id",
      "name": "Plaid Checking",
      "officialName": "Plaid Gold Standard 0% Interest Checking",
      "type": "depository",
      "subtype": "checking",
      "mask": "0000",
      "balances": {
        "current": 110,
        "available": 100,
        "limit": null,
        "isoCurrencyCode": "USD"
      }
    }
  ]
}
```

Errors: no linked items, unknown `item_id`, blank `item_id`, missing credentials.

### `get_transactions`

| Parameter | Purpose |
| --- | --- |
| `start_date` | Required `YYYY-MM-DD` |
| `end_date` | Required `YYYY-MM-DD` |
| `count` | Default 100, from 1 to 500 |
| `offset` | Default 0, zero or greater |
| `item_id` | Optional. Omit it to use the default linked item. |

Calls `/transactions/get`. `start_date` must be on or before `end_date`.

```json
{
  "itemId": "item-id",
  "accounts": [],
  "transactions": [
    {
      "transactionId": "transaction-id",
      "accountId": "account-id",
      "date": "2026-10-01",
      "name": "Uber",
      "merchantName": "Uber",
      "amount": 5.4,
      "pending": false,
      "category": ["Travel", "Taxi"],
      "paymentChannel": "in store"
    }
  ],
  "totalTransactions": 1
}
```

### `get_liabilities`

| Parameter | Purpose |
| --- | --- |
| `item_id` | Optional. Omit it to use the default linked item. |

Calls `/liabilities/get`. The result always includes `itemId`. `credit`, `mortgage`, and `student` are included only when that list is non-empty.

## Link command

`plaid-mcp-link` is not an MCP tool.

1. Read credentials from the environment or `credentials.json`.
2. Call `/link/token/create` with products `transactions` and `liabilities`, country `US`.
3. Serve a local page on `127.0.0.1:8096` (override with `PLAID_MCP_LINK_HOST` and `PLAID_MCP_LINK_PORT`).
4. `POST /exchange` with `public_token` and `institution_name`.
5. Call `/item/public_token/exchange` and append the item to `items.json`.
6. The first item becomes `default_item_id`.

Sandbox sign-in is user `user_good` and password `pass_good`.

## Configuration

| Input | Purpose |
| --- | --- |
| `PLAID_CLIENT_ID` | Plaid client id. Overrides the file when set. |
| `PLAID_SECRET` | Plaid secret. Overrides the file when set. |
| `PLAID_ENV` | `sandbox` (default) or `production` |
| `PLAID_MCP_CONFIG_DIR` | Config directory. Default `~/.config/plaid-mcp` |
| `PLAID_MCP_TRANSPORT` | `stdio` (default) or `http` |
| `PLAID_MCP_HOST` | HTTP bind address. Default `127.0.0.1` |
| `PLAID_MCP_PORT` | HTTP port. Default `8006` |

`credentials.json` shape (values shown are placeholders):

```json
{
  "client_id": "YOUR_CLIENT_ID",
  "secret": "YOUR_SECRET",
  "environment": "sandbox"
}
```

## Quality gate

```bash
.venv/bin/python -m coverage run --branch -m pytest
.venv/bin/python -m coverage report --fail-under=100
```

## Ship checklist

- [x] `CHANGELOG.md` heading `0.0.1`
- [x] `pyproject.toml` version `0.0.1`
- [x] `plaid_mcp/__init__.py` `__version__` matches
- [x] `AGENTS.md` tool list
- [x] `compose.yaml` image tag `0.0.1` and port `8006`
- [x] Cursor reload note in `docs/docker.md`
