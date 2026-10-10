# Changelog

## 0.0.2

- Add `get_balances` for live balances from `/accounts/balance/get`. Optional `account_ids` limits which accounts refresh. Responses may include `lastUpdatedDatetime`.

## 0.0.1

- Read balances, transactions, and liabilities with `get_accounts`, `get_transactions`, and `get_liabilities`.
- Link a bank on the host with `plaid-mcp-link`. Access tokens stay in `items.json` outside the repository.
- Listen on HTTP when `PLAID_MCP_TRANSPORT=http`. The default port is 8006.
- Run the server from a container.
- Publish that image to GitHub Container Registry with an immutable version tag.
