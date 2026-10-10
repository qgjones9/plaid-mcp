# Overview

This server lets an agent read Plaid data. It does not link a bank by itself, and it does not move money.

The tools are `get_accounts`, `get_transactions`, and `get_liabilities`. They call `/accounts/get`, `/transactions/get`, and `/liabilities/get`.

Link a bank with `plaid-mcp-link` on the host. That command writes `items.json` next to `credentials.json`. The first linked item is the default. Pass `item_id` when you want a different one.

Sandbox is the default Plaid environment. Set `PLAID_ENV=production` for live data. Build and test in sandbox first. The sandbox sign-in is user `user_good` and password `pass_good`.

Google Drive, Gmail, Google Docs, Google Calendar, Google Tasks, and Google Sheets are separate repositories and separate processes. Drive listens on port 8000. Gmail listens on port 8001. Docs listens on port 8002. Calendar listens on port 8003. Tasks listens on port 8004. Sheets listens on port 8005. This server listens on port 8006 so all of them can stay up.
