"""Process configuration. Secrets stay outside the repository."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from plaid_mcp.errors import PlaidMcpError

SANDBOX = "sandbox"
PRODUCTION = "production"
_ENVIRONMENTS = {SANDBOX, PRODUCTION}


@dataclass(frozen=True)
class PlaidCredentials:
    """Plaid client id, secret, and environment name."""

    client_id: str
    secret: str
    environment: str


@dataclass(frozen=True)
class ServerSettings:
    """How this process should listen."""

    transport: str
    host: str
    port: int


def default_config_dir() -> Path:
    """Directory for credentials.json and items.json.

    PLAID_MCP_CONFIG_DIR overrides the location so a container can mount
    the host config directory without copying it into the image.
    """
    override = os.environ.get("PLAID_MCP_CONFIG_DIR", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".config" / "plaid-mcp"


def load_credentials(config_dir: Path | None = None) -> PlaidCredentials:
    """Read the client id and secret. Environment variables win over the file."""
    directory = config_dir or default_config_dir()
    from_file = _read_credentials_file(directory / "credentials.json")
    client_id = _prefer_env("PLAID_CLIENT_ID", "client_id", from_file.get("client_id"))
    secret = _prefer_env("PLAID_SECRET", "secret", from_file.get("secret"))
    environment = _prefer_env("PLAID_ENV", "environment", from_file.get("environment"))
    if environment is None:
        environment = SANDBOX
    if client_id is None or secret is None:
        raise PlaidMcpError(
            "Plaid credentials are missing. Set PLAID_CLIENT_ID and PLAID_SECRET, "
            f"or place credentials.json in {directory}. "
            "Do not put that file in the repository."
        )
    return PlaidCredentials(
        client_id=client_id,
        secret=secret,
        environment=environment_name(environment),
    )


def environment_name(value: str) -> str:
    """Return sandbox or production."""
    cleaned = value.strip().lower()
    if cleaned not in _ENVIRONMENTS:
        raise PlaidMcpError("PLAID_ENV must be sandbox or production")
    return cleaned


def environment_text(name: str, default: str) -> str:
    """Return a trimmed environment variable, or default when it is missing or blank."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    cleaned = raw.strip()
    if cleaned == "":
        return default
    return cleaned


def environment_port(name: str, default: int) -> int:
    """Return a TCP port from the environment."""
    text = environment_text(name, str(default))
    if not text.isdigit():
        raise PlaidMcpError(f"{name} must be a number: {text}")
    port = int(text)
    if port < 1 or port > 65535:
        raise PlaidMcpError(f"{name} must be from 1 to 65535: {port}")
    return port


def _prefer_env(env_name: str, file_label: str, from_file: object) -> str | None:
    raw = os.environ.get(env_name)
    if raw is not None and raw.strip():
        return raw.strip()
    return _file_text(from_file, file_label)


def _file_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PlaidMcpError(f"{label} in credentials.json must be a string")
    cleaned = value.strip()
    if cleaned == "":
        return None
    return cleaned


def _read_credentials_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise PlaidMcpError(f"credentials.json is not valid JSON: {path}") from error
    if not isinstance(payload, dict):
        raise PlaidMcpError(f"credentials.json must be an object: {path}")
    return payload
