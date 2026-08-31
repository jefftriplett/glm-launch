from __future__ import annotations

import io
import re
import sys
import urllib.request

import pytest
from typer.testing import CliRunner

import main


runner = CliRunner()
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


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
    assert main._context_window_for("glm-5.3") == 1_000_000
    assert main._context_window_for("glm-5.2[1m]") == 1_000_000
    assert main._context_window_for("glm-5.2") == 200_000
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
    assert "glm-5.3" in result.stdout
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


def _capture_execvpe(monkeypatch) -> dict:
    captured: dict = {}

    def fake_execvpe(binary, args, env):
        captured.update(binary=binary, args=args, env=env)

    monkeypatch.setattr(main.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(main.os, "execvpe", fake_execvpe)
    return captured


def test_glm_env_vars_flow_through_to_exec_env(monkeypatch) -> None:
    captured = _capture_execvpe(monkeypatch)
    monkeypatch.setenv("GLM_BASE_URL", "https://example.test/anthropic")
    monkeypatch.setenv("GLM_AUTH_TOKEN", "secret-token")
    monkeypatch.setenv("GLM_API_KEY", "api-secret")

    result = runner.invoke(main.app, ["claude", "--model", "glm-5.2"])

    assert result.exit_code == 0
    assert captured["binary"] == "/usr/bin/claude"
    assert captured["args"] == ["/usr/bin/claude", "--model", "glm-5.2"]
    assert captured["env"]["ANTHROPIC_BASE_URL"] == "https://example.test/anthropic"
    assert captured["env"]["ANTHROPIC_AUTH_TOKEN"] == "secret-token"
    assert captured["env"]["ANTHROPIC_API_KEY"] == "api-secret"
    assert captured["env"]["ANTHROPIC_MODEL"] == "glm-5.2"


def test_exec_env_drops_inherited_anthropic_api_key(monkeypatch) -> None:
    captured = _capture_execvpe(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "inherited-key")
    monkeypatch.setenv("GLM_AUTH_TOKEN", "secret-token")
    monkeypatch.delenv("GLM_API_KEY", raising=False)

    result = runner.invoke(main.app, ["claude"])

    assert result.exit_code == 0
    assert "ANTHROPIC_API_KEY" not in captured["env"]
    assert captured["env"]["ANTHROPIC_AUTH_TOKEN"] == "secret-token"


def test_default_launch_uses_glm53_with_1m_context(monkeypatch) -> None:
    captured = _capture_execvpe(monkeypatch)
    monkeypatch.setenv("GLM_AUTH_TOKEN", "secret-token")

    result = runner.invoke(main.app, ["claude"])

    assert result.exit_code == 0
    assert captured["env"]["ANTHROPIC_MODEL"] == "glm-5.3"
    assert captured["env"]["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] == "1000000"
    assert captured["env"]["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] == "1000000"
    assert captured["env"]["CLAUDE_CODE_EFFORT_LEVEL"] == "max"


def test_older_models_still_launch_with_their_context_windows(monkeypatch) -> None:
    captured = _capture_execvpe(monkeypatch)
    monkeypatch.setenv("GLM_AUTH_TOKEN", "secret-token")

    for model, window in [("glm-5.2[1m]", "1000000"), ("glm-5.2", "200000")]:
        result = runner.invoke(main.app, ["claude", "--model", model])

        assert result.exit_code == 0
        assert result.stderr == ""  # known models launch without a warning
        assert captured["env"]["ANTHROPIC_MODEL"] == model
        assert captured["env"]["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] == window


def test_exec_env_preserves_unrelated_environment(monkeypatch) -> None:
    captured = _capture_execvpe(monkeypatch)
    monkeypatch.setenv("GLM_AUTH_TOKEN", "secret-token")
    monkeypatch.setenv("UNRELATED_VAR", "keep-me")

    result = runner.invoke(main.app, ["claude"])

    assert result.exit_code == 0
    assert captured["env"]["UNRELATED_VAR"] == "keep-me"


def test_extra_args_pass_through_to_claude(monkeypatch) -> None:
    captured = _capture_execvpe(monkeypatch)
    monkeypatch.setenv("GLM_AUTH_TOKEN", "secret-token")

    result = runner.invoke(
        main.app,
        ["claude", "--model", "glm-5.2", "--", "--verbose", "-p", "hi"],
    )

    assert result.exit_code == 0
    assert captured["args"] == [
        "/usr/bin/claude",
        "--model",
        "glm-5.2",
        "--verbose",
        "-p",
        "hi",
    ]


@pytest.mark.parametrize(
    ("option", "value", "message"),
    [
        ("--api-timeout-ms", "later", "must be a positive integer"),
        ("--api-timeout-ms", "0", "must be a positive integer"),
        ("--auto-compact-window", "-1", "must be a positive integer"),
        ("--max-context-tokens", "lots", "must be a positive integer"),
        ("--effort-level", "extreme", "must be one of"),
        ("--attribution-header", "yes", "must be 0 or 1"),
    ],
)
def test_claude_rejects_invalid_settings(option: str, value: str, message: str) -> None:
    result = runner.invoke(
        main.app,
        ["claude", "--auth-token", "secret-token", option, value, "--dry-run"],
        terminal_width=200,
    )

    assert result.exit_code == 2
    plain_output = ANSI_ESCAPE_RE.sub("", result.output)
    normalized_output = " ".join(plain_output.replace("│", " ").split())
    assert message in normalized_output


def test_remote_models_reports_invalid_json(monkeypatch) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request, timeout: io.BytesIO(b"not-json"),
    )

    with pytest.raises(SystemExit, match="invalid JSON response"):
        main._fetch_remote_models("https://example.test/models", "secret-token", 1.0)


def test_remote_models_reports_timeout(monkeypatch) -> None:
    def raise_timeout(request, timeout):
        raise TimeoutError

    monkeypatch.setattr(urllib.request, "urlopen", raise_timeout)

    with pytest.raises(SystemExit, match="timed out after 1s"):
        main._fetch_remote_models("https://example.test/models", "secret-token", 1.0)


def test_remote_models_reports_invalid_url() -> None:
    with pytest.raises(SystemExit, match="invalid URL"):
        main._fetch_remote_models("not-a-url", "secret-token", 1.0)


def test_bench_reports_timeout(monkeypatch) -> None:
    def raise_timeout(request, timeout):
        raise TimeoutError

    monkeypatch.setattr(urllib.request, "urlopen", raise_timeout)

    result = runner.invoke(
        main.app,
        ["bench", "--auth-token", "secret-token", "--timeout", "0.5"],
    )

    assert result.exit_code == 1
    assert "FAIL (timed out after 0.5s)" in result.stdout


def _fake_http_error(code: int, body: bytes):
    import urllib.error

    return urllib.error.HTTPError(
        url="https://api.z.ai/api/anthropic/v1/messages",
        code=code,
        msg="error",
        hdrs=None,
        fp=io.BytesIO(body),
    )


def test_probe_model_reports_unknown_model_code(monkeypatch) -> None:
    """A `[1m]` ID Z.ai rejects must surface as a failure, not a 1M promise."""
    body = b'{"error":{"code":"1214","message":"modelCode: does not exist"}}'

    def fake_urlopen(*args, **kwargs):
        raise _fake_http_error(400, body)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = main._probe_model(
        "glm-5.2[1m]", "https://api.z.ai/api/anthropic", "t", 5.0
    )

    assert result.ok is False
    assert result.status == "400"
    assert "does not exist" in result.body


def test_probe_model_reports_success(monkeypatch) -> None:
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: FakeResponse())
    result = main._probe_model("glm-5.3", "https://api.z.ai/api/anthropic", "t", 5.0)

    assert result.ok is True
    assert result.status == "200"


def test_bench_all_probes_every_registry_model_and_exits_nonzero(monkeypatch) -> None:
    """`bench --all` must check the whole registry and fail if any ID is bad."""
    probed: list[str] = []

    def fake_probe(model, base_url, auth_token, timeout):
        probed.append(model)
        ok = not model.endswith("[1m]")
        return main.ProbeResult(
            model, ok, "200" if ok else "400", 10, "" if ok else "x"
        )

    monkeypatch.setattr(main, "_probe_model", fake_probe)
    result = runner.invoke(main.app, ["bench", "--all", "--auth-token", "t"])

    assert result.exit_code == 1
    assert probed == [model_id for model_id, _, _ in main.ZAI_MODELS]
    assert "failed to resolve" in result.stdout


def test_probe_result_classifies_throttling_and_unknown_models() -> None:
    """A 429 means the ID exists; only `does not exist` means it does not."""
    throttled = main.ProbeResult("glm-5v-turbo", False, "429", 10, "rate limited")
    unknown = main.ProbeResult(
        "glm-5.2[1m]", False, "400", 10, '{"message":"modelCode: does not exist"}'
    )

    assert throttled.throttled and not throttled.unknown_model
    assert unknown.unknown_model and not unknown.throttled


def test_bench_all_does_not_fail_on_rate_limited_models(monkeypatch) -> None:
    """A 429 is a quota problem, not evidence the model ID is bad."""

    def fake_probe(model, base_url, auth_token, timeout):
        if model == "glm-5v-turbo":
            return main.ProbeResult(model, False, "429", 10, "rate limited")
        return main.ProbeResult(model, True, "200", 10)

    monkeypatch.setattr(main, "_probe_model", fake_probe)
    result = runner.invoke(main.app, ["bench", "--all", "--auth-token", "t"])

    assert result.exit_code == 0
    assert "SKIP" in result.stdout
    assert "rate limited and not verified" in result.stdout


def test_bench_all_only_blames_model_code_when_the_api_said_so(monkeypatch) -> None:
    """The `does not exist` hint must key off the body, not the model name."""

    def fake_probe(model, base_url, auth_token, timeout):
        if model == "glm-5.2[1m]":
            return main.ProbeResult(model, False, "500", 10, "internal error")
        return main.ProbeResult(model, True, "200", 10)

    monkeypatch.setattr(main, "_probe_model", fake_probe)
    result = runner.invoke(main.app, ["bench", "--all", "--auth-token", "t"])

    assert result.exit_code == 1
    assert "does not exist" not in result.stdout


def test_probe_model_returns_result_for_invalid_url() -> None:
    """A bad URL must not abort a whole --all sweep."""
    result = main._probe_model("glm-5.3", "not a url", "t", 5.0)

    assert result.ok is False
    assert "invalid URL" in result.status
