# Authentication

Plaid keys stay outside this repository.

Create a developer account in the Plaid Dashboard and copy the sandbox secret. The values below are placeholders, not real keys.

```json
{
  "client_id": "YOUR_CLIENT_ID",
  "secret": "YOUR_SECRET",
  "environment": "sandbox"
}
```

Save that object as `~/.config/plaid-mcp/credentials.json`.

These environment variables override the file when they are set and not blank:

| Variable | Purpose |
| --- | --- |
| `PLAID_CLIENT_ID` | Plaid client id |
| `PLAID_SECRET` | Plaid secret for the selected environment |
| `PLAID_ENV` | `sandbox` (default) or `production` |
| `PLAID_MCP_CONFIG_DIR` | Config directory. Default `~/.config/plaid-mcp` |

`PLAID_ENV=production` uses the production secret and the production host. Do not put the production secret in this repository.

## Link

`plaid-mcp-link` reads those credentials, opens `http://127.0.0.1:8096/`, and waits for Plaid Link. The page loads Plaid Link from the Plaid CDN. On success it exchanges the public token and appends an item to `items.json`.

`items.json` holds `default_item_id` and a list of `item_id`, `access_token`, and `institution_name`. The file mode is `0600`. Do not commit it.

Sandbox sign-in on that page is user `user_good` and password `pass_good`.

Override the page address with `PLAID_MCP_LINK_HOST` and `PLAID_MCP_LINK_PORT`. The defaults are `127.0.0.1` and `8096`.

The link token requests the `transactions` and `liabilities` products for country `US`. Link again if you need liabilities on an item that was linked without that product.
