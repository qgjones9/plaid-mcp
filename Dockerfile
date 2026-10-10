FROM python:3.12-slim

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin mcp

WORKDIR /app

COPY pyproject.toml README.md ./
COPY plaid_mcp ./plaid_mcp

RUN pip install --no-cache-dir .

USER mcp

ENV PLAID_MCP_CONFIG_DIR=/config
ENV PLAID_MCP_TRANSPORT=http
ENV PLAID_MCP_HOST=0.0.0.0
ENV PLAID_MCP_PORT=8006

EXPOSE 8006

ENTRYPOINT ["python", "-m", "plaid_mcp"]
