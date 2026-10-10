# Plaid MCP

Public Python MCP server for Plaid. An agent can read account balances, transactions, and liabilities for items you have linked.

Tools:

- `get_accounts`
- `get_transactions`
- `get_liabilities`

Details are in `docs/finance.md`. Linking a bank is a separate host command, `plaid-mcp-link`. It is not an MCP tool. The server is Python only.

## Run

Install this repository, then put your Plaid keys in `~/.config/plaid-mcp/credentials.json` or in `PLAID_CLIENT_ID` and `PLAID_SECRET`. That directory is outside the repository. See `docs/authentication.md`.

```bash
plaid-mcp-link
python -m plaid_mcp
```

`plaid-mcp` is the same server entry point. Cursor starts it as a local stdio server:

```json
{
  "mcpServers": {
    "plaid": {
      "command": "python",
      "args": ["-m", "plaid_mcp"]
    }
  }
}
```

Use the `python` from the environment where this package is installed.

To run that same server in a container, see `docs/docker.md`. `compose.yaml` publishes `127.0.0.1:8006` and starts `ghcr.io/qgjones9/plaid-mcp:0.0.1`. Point Cursor at `http://127.0.0.1:8006/mcp`. Credentials stay on the host and are mounted in. Plaid Link stays on the host. The browser page cannot finish inside Docker.

## Coverage

Application code is done only when tests reach 100% line and branch coverage. The check is:

```bash
python -m coverage run --branch -m pytest
python -m coverage report --fail-under=100
```

Install the package and the check with `python -m pip install -e ".[dev]"`. Configuration is in `pyproject.toml`. It measures the `plaid_mcp` package.

## Public repository

Never commit Plaid secrets, access tokens, `credentials.json`, `items.json`, `.env` files, or personal account data. Do not copy anything from the user home directory into this repo. `YOUR_CLIENT_ID` in the docs is a placeholder, not a real client id.
