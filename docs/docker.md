# Docker

The published container listens on HTTP and stays running. Cursor connects to that URL. It does not start the container.

The image does not contain a Plaid secret or an access token. Mount the host config directory when you start the container.

Link a bank on the host before the first container start. `plaid-mcp-link` opens a browser on localhost, and that page is not served from inside the container. After `items.json` exists, the container can read it through the mounted directory.

```bash
plaid-mcp-link
```

That writes `~/.config/plaid-mcp/items.json` next to `credentials.json`.

A push to `main` publishes an image when `plaid_mcp/`, `Dockerfile`, or `pyproject.toml` changed. The version tag matches `pyproject.toml` and `CHANGELOG.md`. A docs-only push does not publish an image.

```text
ghcr.io/qgjones9/plaid-mcp:0.0.2
```

The package page is [plaid-mcp](https://github.com/qgjones9/plaid-mcp/pkgs/container/plaid-mcp). The first publish is private. In the package settings on GitHub, set the package to public so it can be pulled without a token. A public package cannot be made private again.

When those paths change, the version tag must be new, and `latest` moves to that same image. The next feature has to bump the version, for example to `0.0.2`, and add a changelog heading. The workflow also creates git tag `v` plus that version on the commit that produced the image. Version tags are immutable.

Start the container from this repository after `items.json` exists. `compose.yaml` publishes the port only on this Mac and mounts `~/.config/plaid-mcp` at `/config`. Port 8006 leaves 8000 free for Drive, 8001 free for Gmail, 8002 free for Docs, 8003 free for Calendar, 8004 free for Tasks, and 8005 free for Sheets.

```bash
UID="$(id -u)" GID="$(id -g)" docker compose up -d --build
```

Stop it with `docker compose down`. The Plaid files stay on the Mac.

Inside the container the process binds to `0.0.0.0` so Docker can forward the port. On the Mac, `127.0.0.1:8006` is the only published address. The container config directory is `/config`.

Cursor configuration, in the user MCP file rather than this repository:

```json
{
  "mcpServers": {
    "plaid": {
      "url": "http://127.0.0.1:8006/mcp"
    }
  }
}
```

Reload the Cursor window after the server is running. Until you reload, Cursor keeps the old tool list and calls fail with "tool not found" even though this server is up.

`python -m plaid_mcp` without `PLAID_MCP_TRANSPORT` still uses stdin. That is the local command above. The image sets `PLAID_MCP_TRANSPORT=http`. Pin the semver tag when you want a fixed image. `latest` moves every time a new version is published.

You can pass `PLAID_CLIENT_ID`, `PLAID_SECRET`, and `PLAID_ENV` into the container instead of `credentials.json`. Do not write those values into `compose.yaml`.
