# Agent instructions

This is a public repository. Refuse to add secrets or personal data. That includes Plaid client ids, secrets, access tokens, `credentials.json`, `items.json`, `.env` files, API keys, and personal account data.

Do not read or print `credentials.json` or `items.json`.

## Scope

Plaid only. Do not add Calendar, Gmail, Drive, Docs, Tasks, or Sheets tools. Those products belong in their own repositories and their own processes.

Python only. Do not add Node.js.

Implemented tools are `get_accounts`, `get_transactions`, and `get_liabilities`.

They call Plaid `/accounts/get`, `/transactions/get`, and `/liabilities/get`.

`get_accounts` returns balances for the default linked item unless `item_id` is set.

`get_transactions` requires `start_date` and `end_date` as `YYYY-MM-DD`. `count` is from 1 to 500 and defaults to 100. `offset` defaults to 0. `start_date` must be on or before `end_date`.

`get_liabilities` returns credit, mortgage, and student groups. Empty groups are omitted.

`item_id` is optional on every tool. Omit it to use the default linked item. A blank `item_id` is an error.

Do not add tools beyond this list.

`plaid-mcp-link` is a host command, not an MCP tool. It runs Plaid Link once and writes `items.json`. Do not register it on the MCP server.

## Secrets

Tokens and the Plaid secret are never written into this tree. Store them in `~/.config/plaid-mcp/credentials.json` and `items.json` on the machine, outside the git repo. `PLAID_CLIENT_ID` and `PLAID_SECRET` override the file when they are set. Docker images must not copy that directory or any credential file into the build context.

The default environment is sandbox. `PLAID_ENV=production` selects production. There is no other environment name.

Never commit Plaid secrets, access tokens, `credentials.json`, `items.json`, `.env` files, or personal account data.

Do not copy anything from the user home directory into this repo.

If a document needs to mention a client id, use the placeholder `YOUR_CLIENT_ID` and label it as a placeholder.

Do not edit `~/.cursor/mcp.json` or `~/.cursor/permissions.json`. The Cursor URL is documented in `docs/docker.md`.

## Git and docs

Do not commit unless the user asks. Do not push, and do not create a GitHub remote, unless the user asks.

The intended remote, when the user asks for it, is `https://github.com/qgjones9/plaid-mcp.git`.

A feature that changes this server is not done until `pyproject.toml` `version` is bumped and `CHANGELOG.md` has a heading for that version. A feature increments the patch number, for example `0.0.1` to `0.0.2`. The publish workflow does not choose the next number. Keep `plaid_mcp/__init__.py` `__version__` equal to the `pyproject.toml` version.

New documentation goes in `docs/`.

Before a new or changed MCP tool, add a plan in `docs/plans/<feature>.md`, update `docs/plans/README.md`, and get review before coding.

## Coverage

Every Python module in the application package must have 100% line and branch coverage from tests.

Do not merge or treat code as done until coverage is 100% line and branch.

Do not exclude real application code with `omit` or `pragma` to fake the number. Tests do not need to cover themselves.

Application code belongs in the `plaid_mcp` package. `pyproject.toml` turns branch coverage on and sets `fail_under` to 100 for that package. Do not add a dummy module so the report has something to measure.

The gate is:

```bash
python -m coverage run --branch -m pytest
python -m coverage report --fail-under=100
```
