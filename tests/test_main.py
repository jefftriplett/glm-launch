from __future__ import annotations

import sys

from typer.testing import CliRunner

import main


runner = CliRunner()


def _claude_env(**overrides: str) -> dict[str, str]:
    values = {
        "model": "glm-5.2",
        "base_url": "https://example.test/anthropic",
        "api_key": "",
        "auth_token": "secret-token",
        "api_timeout_ms": "3000000",
        "default_haiku_model": "glm-4.5-air",
        "default_sonnet_model": "glm-5.2",
        "default_opus_model": "glm-5.2",
        "default_fable_model": "glm-5.2",
        "subagent_model": "glm-4.5-air",
        "effort_level": "max",
        "auto_compact_window": "auto",
        "max_context_tokens": "auto",
    }
    values.update(overrides)
    return main._build_claude_env(**values)


def test_context_window_for_known_and_custom_models() -> None:
    assert main._context_window_for("glm-5.2[1m]") == 1_000_000
    assert main._context_window_for("glm-4.6v") == 128_000
    assert main._context_window_for("custom[1m]") == 1_000_000
    assert main._context_window_for("custom") == main.DEFAULT_CONTEXT_WINDOW


def test_build_claude_env_resolves_auto_context_and_omits_empty_api_key() -> None:
    env = _claude_env()

    assert env["ANTHROPIC_BASE_URL"] == "https://example.test/anthropic"
    assert env["ANTHROPIC_AUTH_TOKEN"] == "secret-token"
    assert env["ANTHROPIC_MODEL"] == "glm-5.2"
    assert env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] == "200000"
    assert env["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] == "200000"
    assert "ANTHROPIC_API_KEY" not in env


def test_build_claude_env_respects_explicit_and_empty_context_values() -> None:
    env = _claude_env(
        api_key="api-secret",
        auto_compact_window="123456",
        max_context_tokens="",
    )

    assert env["ANTHROPIC_API_KEY"] == "api-secret"
    assert env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] == "123456"
    assert "CLAUDE_CODE_MAX_CONTEXT_TOKENS" not in env


def test_secret_masking_and_shell_quoting() -> None:
    assert main._display_value("GLM_AUTH_TOKEN", "abcdefghijkl") == "abcd***"
    assert main._display_value("ANTHROPIC_AUTH_TOKEN", "short") == "sh***"
    assert main._display_value("ANTHROPIC_MODEL", "glm-5.2") == "glm-5.2"
    assert main._shell_quote("it's safe") == "'it'\"'\"'s safe'"


def test_models_command_lists_known_models() -> None:
    result = runner.invoke(main.app, ["models"])

    assert result.exit_code == 0
    assert "glm-5.2[1m]" in result.stdout
    assert "glm-4.5-air" in result.stdout


def test_version_option() -> None:
    result = runner.invoke(main.app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == main.__version__


def test_doctor_fails_when_auth_token_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(main.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(main, "_binary_version", lambda path: "1.0.0")

    result = runner.invoke(main.app, ["doctor"], env={"GLM_AUTH_TOKEN": ""})

    assert result.exit_code == 1
    assert "GLM_AUTH_TOKEN: NOT SET (required)" in result.stdout
    assert "Some checks failed." in result.stdout


def test_doctor_passes_with_auth_token_and_claude(monkeypatch) -> None:
    monkeypatch.setattr(main.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(main, "_binary_version", lambda path: "1.0.0")

    result = runner.invoke(main.app, ["doctor"], env={"GLM_AUTH_TOKEN": "secret-token"})

    assert result.exit_code == 0
    assert "GLM_AUTH_TOKEN: secr***" in result.stdout
    assert "All checks passed." in result.stdout


def test_cli_defaults_to_claude_when_no_arguments(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["glm-launch"])
    monkeypatch.setattr(main, "app", lambda: None)

    main.cli()

    assert sys.argv == ["glm-launch", "claude"]


def test_cli_forwards_bare_options_to_claude(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["glm-launch", "--model", "glm-5.1", "--dry-run"])
    monkeypatch.setattr(main, "app", lambda: None)

    main.cli()

    assert sys.argv == [
        "glm-launch",
        "claude",
        "--model",
        "glm-5.1",
        "--dry-run",
    ]


def test_cli_preserves_top_level_options(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["glm-launch", "--version"])
    monkeypatch.setattr(main, "app", lambda: None)

    main.cli()

    assert sys.argv == ["glm-launch", "--version"]


def test_claude_dry_run_does_not_require_binary(monkeypatch) -> None:
    monkeypatch.setattr(main.shutil, "which", lambda name: None)
    monkeypatch.setattr(main.os.path, "isfile", lambda path: False)

    result = runner.invoke(
        main.app,
        ["claude", "--auth-token", "secret-token", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "binary: claude" in result.stdout
    assert "ANTHROPIC_AUTH_TOKEN=secr***" in result.stdout
