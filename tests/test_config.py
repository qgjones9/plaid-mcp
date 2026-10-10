"""Credentials and listen settings."""

import json
from pathlib import Path

import pytest

from plaid_mcp.config import (
    SANDBOX,
    default_config_dir,
    environment_port,
    environment_text,
    load_credentials,
)
from plaid_mcp.errors import PlaidMcpError


def _clear_env(monkeypatch) -> None:
    monkeypatch.delenv("PLAID_CLIENT_ID", raising=False)
    monkeypatch.delenv("PLAID_SECRET", raising=False)
    monkeypatch.delenv("PLAID_ENV", raising=False)
    monkeypatch.delenv("PLAID_MCP_CONFIG_DIR", raising=False)


def test_default_config_dir_uses_home(monkeypatch):
    _clear_env(monkeypatch)
    assert default_config_dir() == Path.home() / ".config" / "plaid-mcp"


def test_default_config_dir_blank_override_uses_home(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("PLAID_MCP_CONFIG_DIR", "  ")
    assert default_config_dir() == Path.home() / ".config" / "plaid-mcp"


def test_default_config_dir_override(monkeypatch, tmp_path):
    monkeypatch.setenv("PLAID_MCP_CONFIG_DIR", str(tmp_path))
    assert default_config_dir() == tmp_path


def test_environment_credentials_default_to_sandbox(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("PLAID_CLIENT_ID", " client ")
    monkeypatch.setenv("PLAID_SECRET", " secret ")
    loaded = load_credentials(tmp_path)
    assert loaded.client_id == "client"
    assert loaded.secret == "secret"
    assert loaded.environment == SANDBOX


def test_load_credentials_uses_default_directory(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("PLAID_MCP_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("PLAID_CLIENT_ID", "client")
    monkeypatch.setenv("PLAID_SECRET", "secret")
    loaded = load_credentials()
    assert loaded.client_id == "client"


def test_file_credentials(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    _write_credentials(
        tmp_path,
        {"client_id": "from-file", "secret": "file-secret", "environment": "Production"},
    )
    loaded = load_credentials(tmp_path)
    assert loaded.client_id == "from-file"
    assert loaded.secret == "file-secret"
    assert loaded.environment == "production"


def test_environment_wins_over_file(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    _write_credentials(
        tmp_path,
        {"client_id": "from-file", "secret": "file-secret", "environment": "production"},
    )
    monkeypatch.setenv("PLAID_CLIENT_ID", "from-env")
    monkeypatch.setenv("PLAID_SECRET", "env-secret")
    monkeypatch.setenv("PLAID_ENV", "sandbox")
    loaded = load_credentials(tmp_path)
    assert loaded.client_id == "from-env"
    assert loaded.secret == "env-secret"
    assert loaded.environment == "sandbox"


def test_blank_environment_variables_fall_back_to_file(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    _write_credentials(
        tmp_path,
        {"client_id": "from-file", "secret": "file-secret", "environment": "production"},
    )
    monkeypatch.setenv("PLAID_CLIENT_ID", "  ")
    monkeypatch.setenv("PLAID_SECRET", "   ")
    monkeypatch.setenv("PLAID_ENV", " ")
    loaded = load_credentials(tmp_path)
    assert loaded.client_id == "from-file"
    assert loaded.environment == "production"


def test_blank_file_values_are_missing(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    _write_credentials(tmp_path, {"client_id": "  ", "secret": "", "environment": "  "})
    with pytest.raises(PlaidMcpError, match="credentials are missing"):
        load_credentials(tmp_path)


def test_missing_secret(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("PLAID_CLIENT_ID", "client")
    with pytest.raises(PlaidMcpError, match="credentials are missing"):
        load_credentials(tmp_path)


def test_credentials_file_must_be_json(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    path = tmp_path / "credentials.json"
    path.write_text("{")
    with pytest.raises(PlaidMcpError, match="not valid JSON"):
        load_credentials(tmp_path)


def test_credentials_file_must_be_an_object(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    _write_credentials(tmp_path, ["nope"])
    with pytest.raises(PlaidMcpError, match="must be an object"):
        load_credentials(tmp_path)


def test_file_field_must_be_a_string(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    _write_credentials(tmp_path, {"client_id": 12, "secret": "secret"})
    with pytest.raises(PlaidMcpError, match="client_id in credentials.json must be a string"):
        load_credentials(tmp_path)


def test_unknown_environment(monkeypatch, tmp_path):
    _clear_env(monkeypatch)
    monkeypatch.setenv("PLAID_CLIENT_ID", "client")
    monkeypatch.setenv("PLAID_SECRET", "secret")
    monkeypatch.setenv("PLAID_ENV", "development")
    with pytest.raises(PlaidMcpError, match="sandbox or production"):
        load_credentials(tmp_path)


def test_environment_text_and_port(monkeypatch):
    monkeypatch.delenv("PLAID_MCP_PORT", raising=False)
    assert environment_text("PLAID_MCP_PORT", "8006") == "8006"
    monkeypatch.setenv("PLAID_MCP_PORT", "  ")
    assert environment_text("PLAID_MCP_PORT", "8006") == "8006"
    monkeypatch.setenv("PLAID_MCP_PORT", " 9000 ")
    assert environment_port("PLAID_MCP_PORT", 8006) == 9000


def test_port_must_be_numeric(monkeypatch):
    monkeypatch.setenv("PLAID_MCP_PORT", "nope")
    with pytest.raises(PlaidMcpError, match="must be a number"):
        environment_port("PLAID_MCP_PORT", 8006)


def test_port_must_be_in_range(monkeypatch):
    monkeypatch.setenv("PLAID_MCP_PORT", "0")
    with pytest.raises(PlaidMcpError, match="1 to 65535"):
        environment_port("PLAID_MCP_PORT", 8006)
    monkeypatch.setenv("PLAID_MCP_PORT", "70000")
    with pytest.raises(PlaidMcpError, match="1 to 65535"):
        environment_port("PLAID_MCP_PORT", 8006)


def _write_credentials(directory: Path, payload: object) -> None:
    path = directory / "credentials.json"
    path.write_text(json.dumps(payload))
