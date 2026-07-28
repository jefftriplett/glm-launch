# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "typer",
# ]
# ///

from __future__ import annotations

import json
import os
import shutil
from importlib import metadata

import typer

try:
    __version__ = metadata.version("glm-launch")
except metadata.PackageNotFoundError:  # running as a standalone script
    __version__ = "2026.7.4"

app = typer.Typer(invoke_without_command=True)
launch_app = typer.Typer(
    help="Launch an LLM coding tool with GLM settings.",
    invoke_without_command=True,
)
app.add_typer(launch_app, name="launch")


def _version_callback(value: bool) -> None:
    if value:
        print(__version__)
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()


@launch_app.callback(invoke_without_command=True)
def launch_main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()


# ---------------------------------------------------------------------------
# Z.ai model registry
# ---------------------------------------------------------------------------

# Current Z.ai GLM models (API IDs are lowercase). Each entry is
# (model_id, context_window_tokens, description). The `[1m]` suffix enables
# the 1M context tier (billed separately); plain glm-5.2 serves the standard
# window. Kept here so `models`, the auto context defaults, and the help text
# stay in one place. See https://z.ai/model-api and
# https://docs.z.ai/devpack/latest-model
ZAI_MODELS: list[tuple[str, int, str]] = [
    ("glm-5.2[1m]", 1_000_000, "Flagship with the 1M context tier enabled"),
    ("glm-5.2", 200_000, "Flagship — frontier reasoning, coding, agentic tasks"),
    ("glm-5.1", 200_000, "Long-horizon agentic flagship"),
    ("glm-5", 200_000, "GLM-5 flagship"),
    ("glm-5-turbo", 200_000, "Speed-optimized GLM-5 variant"),
    ("glm-5v-turbo", 200_000, "Vision-capable GLM-5-Turbo variant"),
    ("glm-4.7", 200_000, "Balanced cost/performance coding model"),
    ("glm-4.6", 200_000, "Strong coding model"),
    ("glm-4.6v", 128_000, "Vision model (backs Z.ai's Vision MCP server)"),
    ("glm-4.5", 128_000, "Previous-gen general model"),
    ("glm-4.5-air", 128_000, "Lightweight, low-cost (good for subagents/haiku tier)"),
]

# Conservative fallback for model IDs not in the registry.
DEFAULT_CONTEXT_WINDOW = 200_000


def _context_window_for(model: str) -> int:
    """Resolve a model ID to its context window in tokens."""
    for model_id, window, _ in ZAI_MODELS:
        if model_id == model:
            return window
    if model.endswith("[1m]"):
        return 1_000_000
    return DEFAULT_CONTEXT_WINDOW


def _warn_unknown_model(model: str) -> None:
    """Warn when a model ID is not in the registry (Z.ai will 400 on typos)."""
    if model and model not in {model_id for model_id, _, _ in ZAI_MODELS}:
        typer.echo(
            f"warning: {model!r} is not a known Z.ai model (run `glm-launch models` "
            "to list them); launching anyway",
            err=True,
        )


def _fmt_window(window: int) -> str:
    """Format a token count compactly (1000000 -> 1M, 200000 -> 200K)."""
    if window >= 1_000_000 and window % 1_000_000 == 0:
        return f"{window // 1_000_000}M"
    return f"{window // 1_000}K"


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

_SECRET_VARS = {
    "GLM_API_KEY",
    "GLM_AUTH_TOKEN",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
}


def _mask(value: str) -> str:
    """Show only the first few chars, mask the rest."""
    if len(value) <= 10:
        return value[:2] + "***"
    return value[:4] + "***"


def _display_value(key: str, value: str) -> str:
    if not value:
        return "(empty)"
    return _mask(value) if key in _SECRET_VARS else value


def _print_dry_run(
    *,
    binary: str,
    cmd_args: list[str],
    env: dict[str, str] | None = None,
    config_changes: list[str] | None = None,
) -> None:
    """Print the launch plan without exec'ing the target binary."""
    print("Dry run:")
    print(f"  binary: {binary}")
    print(f"  argv: {cmd_args!r}")

    if env:
        print("  env:")
        for key in sorted(env):
            print(f"    {key}={_display_value(key, env[key])}")

    if config_changes:
        print("  config:")
        for change in config_changes:
            print(f"    {change}")


# ---------------------------------------------------------------------------
# Binary resolution helpers
# ---------------------------------------------------------------------------


def _find_binary(name: str, fallback_path: str | None = None) -> str:
    """Locate *name* on PATH, optionally falling back to *fallback_path*."""
    found = shutil.which(name)
    if found:
        return found
    if fallback_path:
        expanded = os.path.expanduser(fallback_path)
        if os.path.isfile(expanded) and os.access(expanded, os.X_OK):
            return expanded
    install_hint = "Install it or ensure it is on your PATH."
    raise SystemExit(f"{name!r} not found. {install_hint}")


# ---------------------------------------------------------------------------
# Claude / GLM environment
# ---------------------------------------------------------------------------

# Shared option declarations for `launch claude` and `shell`, so each
# flag/envvar/default/help lives in exactly one place.
MODEL_OPTION = typer.Option(
    "glm-5.2[1m]",
    "--model",
    "-m",
    help="Model name (ANTHROPIC_MODEL, passed to claude --model); "
    "the [1m] suffix enables the 1M context tier",
)
BASE_URL_OPTION = typer.Option(
    "https://api.z.ai/api/anthropic",
    "--base-url",
    envvar="GLM_BASE_URL",
    help="Base URL for the API endpoint",
)
API_KEY_OPTION = typer.Option("", "--api-key", envvar="GLM_API_KEY", help="API key")
AUTH_TOKEN_OPTION = typer.Option(
    ..., "--auth-token", envvar="GLM_AUTH_TOKEN", help="Auth token"
)
API_TIMEOUT_MS_OPTION = typer.Option(
    "3000000",
    "--api-timeout-ms",
    envvar="API_TIMEOUT_MS",
    help="API request timeout in milliseconds",
)
DEFAULT_HAIKU_MODEL_OPTION = typer.Option(
    "glm-4.5-air",
    "--default-haiku-model",
    envvar="ANTHROPIC_DEFAULT_HAIKU_MODEL",
    help="Default model for Haiku-tier requests",
)
DEFAULT_SONNET_MODEL_OPTION = typer.Option(
    "glm-5.2[1m]",
    "--default-sonnet-model",
    envvar="ANTHROPIC_DEFAULT_SONNET_MODEL",
    help="Default model for Sonnet-tier requests",
)
DEFAULT_OPUS_MODEL_OPTION = typer.Option(
    "glm-5.2[1m]",
    "--default-opus-model",
    envvar="ANTHROPIC_DEFAULT_OPUS_MODEL",
    help="Default model for Opus-tier requests",
)
DEFAULT_FABLE_MODEL_OPTION = typer.Option(
    "glm-5.2[1m]",
    "--default-fable-model",
    envvar="ANTHROPIC_DEFAULT_FABLE_MODEL",
    help="Default model for Fable-tier requests",
)
SUBAGENT_MODEL_OPTION = typer.Option(
    "glm-4.5-air",
    "--subagent-model",
    envvar="CLAUDE_CODE_SUBAGENT_MODEL",
    help="Model used for spawned subagents",
)
# GLM-5.2 collapses Claude Code's effort ladder into two effective tiers:
# low/medium/high -> high, xhigh/max/ultracode -> max. Z.ai recommends max
# for coding. See https://docs.z.ai/devpack/latest-model
EFFORT_LEVEL_OPTION = typer.Option(
    "max",
    "--effort-level",
    envvar="CLAUDE_CODE_EFFORT_LEVEL",
    help="Effort level; GLM-5.2 only distinguishes high (faster) vs max (deeper) — "
    "low/medium/high map to high, xhigh/max map to max",
)
ATTRIBUTION_HEADER_OPTION = typer.Option(
    "0",
    "--attribution-header",
    envvar="CLAUDE_CODE_ATTRIBUTION_HEADER",
    help="Attribution header toggle (0 disables it)",
)
AUTO_COMPACT_WINDOW_OPTION = typer.Option(
    "auto",
    "--auto-compact-window",
    envvar="CLAUDE_CODE_AUTO_COMPACT_WINDOW",
    help="Auto-compact context window (token count); "
    "'auto' sizes it to the model's context window, empty to leave unset",
)
MAX_CONTEXT_TOKENS_OPTION = typer.Option(
    "auto",
    "--max-context-tokens",
    envvar="CLAUDE_CODE_MAX_CONTEXT_TOKENS",
    help="Maximum context token budget; "
    "'auto' sizes it to the model's context window, empty to leave unset",
)


def _build_claude_env(
    *,
    model: str,
    base_url: str,
    api_key: str,
    auth_token: str,
    api_timeout_ms: str,
    default_haiku_model: str,
    default_sonnet_model: str,
    default_opus_model: str,
    default_fable_model: str,
    subagent_model: str,
    effort_level: str,
    attribution_header: str = "0",
    auto_compact_window: str = "",
    max_context_tokens: str = "",
) -> dict[str, str]:
    """Build the GLM env vars claude needs to talk to Z.ai."""
    if auto_compact_window == "auto":
        auto_compact_window = str(_context_window_for(model))
    if max_context_tokens == "auto":
        max_context_tokens = str(_context_window_for(model))
    env = {
        "ANTHROPIC_BASE_URL": base_url,
        "ANTHROPIC_AUTH_TOKEN": auth_token,
        "API_TIMEOUT_MS": api_timeout_ms,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": default_haiku_model,
        "ANTHROPIC_DEFAULT_SONNET_MODEL": default_sonnet_model,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": default_opus_model,
        "ANTHROPIC_DEFAULT_FABLE_MODEL": default_fable_model,
        "CLAUDE_CODE_SUBAGENT_MODEL": subagent_model,
        "CLAUDE_CODE_EFFORT_LEVEL": effort_level,
        "CLAUDE_CODE_ATTRIBUTION_HEADER": attribution_header,
    }
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    if model:
        env["ANTHROPIC_MODEL"] = model
    if auto_compact_window:
        env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] = auto_compact_window
    if max_context_tokens:
        env["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] = max_context_tokens
    return env


# ---------------------------------------------------------------------------
# launch claude
# ---------------------------------------------------------------------------


@launch_app.command(
    "claude",
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False},
)
def launch_claude(
    ctx: typer.Context,
    model: str = MODEL_OPTION,
    base_url: str = BASE_URL_OPTION,
    api_key: str = API_KEY_OPTION,
    auth_token: str = AUTH_TOKEN_OPTION,
    api_timeout_ms: str = API_TIMEOUT_MS_OPTION,
    default_haiku_model: str = DEFAULT_HAIKU_MODEL_OPTION,
    default_sonnet_model: str = DEFAULT_SONNET_MODEL_OPTION,
    default_opus_model: str = DEFAULT_OPUS_MODEL_OPTION,
    default_fable_model: str = DEFAULT_FABLE_MODEL_OPTION,
    subagent_model: str = SUBAGENT_MODEL_OPTION,
    effort_level: str = EFFORT_LEVEL_OPTION,
    attribution_header: str = ATTRIBUTION_HEADER_OPTION,
    auto_compact_window: str = AUTO_COMPACT_WINDOW_OPTION,
    max_context_tokens: str = MAX_CONTEXT_TOKENS_OPTION,
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print the resolved command and GLM environment without launching claude",
    ),
) -> None:
    """Launch claude with GLM environment settings."""
    _warn_unknown_model(model)
    binary = _find_binary("claude", "~/.claude/local/claude")

    glm_env = _build_claude_env(
        model=model,
        base_url=base_url,
        api_key=api_key,
        auth_token=auth_token,
        api_timeout_ms=api_timeout_ms,
        default_haiku_model=default_haiku_model,
        default_sonnet_model=default_sonnet_model,
        default_opus_model=default_opus_model,
        default_fable_model=default_fable_model,
        subagent_model=subagent_model,
        effort_level=effort_level,
        attribution_header=attribution_header,
        auto_compact_window=auto_compact_window,
        max_context_tokens=max_context_tokens,
    )
    env = os.environ.copy()
    if not api_key:
        # Without a GLM api key, drop any inherited ANTHROPIC_API_KEY -- claude
        # may prefer an api key over the auth token and route away from Z.ai.
        env.pop("ANTHROPIC_API_KEY", None)
    env.update(glm_env)

    cmd_args = [binary]
    if model:
        cmd_args.extend(["--model", model])
    cmd_args.extend(ctx.args)

    if dry_run:
        _print_dry_run(binary=binary, cmd_args=cmd_args, env=glm_env)
        return

    os.execvpe(binary, cmd_args, env)


# ---------------------------------------------------------------------------
# launch codex
# ---------------------------------------------------------------------------


# codex is intentionally disabled. codex only speaks the OpenAI Responses API
# (it removed wire_api="chat"), but Z.ai's GLM endpoints are Anthropic Messages
# and OpenAI Chat Completions only -- there is no /responses endpoint, so codex
# requests 404. Use the claude provider instead.
@launch_app.command(
    "codex",
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False},
)
def launch_codex(ctx: typer.Context) -> None:
    """Disabled: Z.ai does not support codex (no OpenAI Responses API)."""
    typer.echo(
        "codex is not supported by glm-launch.\n"
        "codex requires the OpenAI Responses API, but Z.ai's GLM only exposes "
        "Anthropic Messages and OpenAI Chat Completions (no /responses endpoint), "
        "so codex requests 404.\n"
        "Use `glm-launch launch claude` instead.",
        err=True,
    )
    raise typer.Exit(1)


# ---------------------------------------------------------------------------
# shell
# ---------------------------------------------------------------------------


def _shell_quote(value: str) -> str:
    """Single-quote a value safely for POSIX shell eval."""
    return "'" + value.replace("'", "'\"'\"'") + "'"


@app.command()
def shell(
    model: str = MODEL_OPTION,
    base_url: str = BASE_URL_OPTION,
    api_key: str = API_KEY_OPTION,
    auth_token: str = AUTH_TOKEN_OPTION,
    api_timeout_ms: str = API_TIMEOUT_MS_OPTION,
    default_haiku_model: str = DEFAULT_HAIKU_MODEL_OPTION,
    default_sonnet_model: str = DEFAULT_SONNET_MODEL_OPTION,
    default_opus_model: str = DEFAULT_OPUS_MODEL_OPTION,
    default_fable_model: str = DEFAULT_FABLE_MODEL_OPTION,
    subagent_model: str = SUBAGENT_MODEL_OPTION,
    effort_level: str = EFFORT_LEVEL_OPTION,
    attribution_header: str = ATTRIBUTION_HEADER_OPTION,
    auto_compact_window: str = AUTO_COMPACT_WINDOW_OPTION,
    max_context_tokens: str = MAX_CONTEXT_TOKENS_OPTION,
) -> None:
    """Print `export` lines to bootstrap the current shell for Z.ai.

    Eval the output to configure your shell so a plain `claude` uses Z.ai:

        eval "$(uv run src/main.py shell)"
    """
    env = _build_claude_env(
        model=model,
        base_url=base_url,
        api_key=api_key,
        auth_token=auth_token,
        api_timeout_ms=api_timeout_ms,
        default_haiku_model=default_haiku_model,
        default_sonnet_model=default_sonnet_model,
        default_opus_model=default_opus_model,
        default_fable_model=default_fable_model,
        subagent_model=subagent_model,
        effort_level=effort_level,
        attribution_header=attribution_header,
        auto_compact_window=auto_compact_window,
        max_context_tokens=max_context_tokens,
    )
    for key, value in env.items():
        if value:
            print(f"export {key}={_shell_quote(value)}")


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------


def _fetch_remote_models(models_url: str, auth_token: str, timeout: float) -> list[str]:
    """Fetch the live model ID list from the Z.ai PaaS /models endpoint."""
    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        models_url,
        headers={"Authorization": f"Bearer {auth_token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        msg = f"Failed to fetch models ({e.code})"
        if body:
            msg += f": {body[:200]}"
        raise SystemExit(msg)
    except urllib.error.URLError as e:
        raise SystemExit(f"Failed to fetch models: {e.reason}")

    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    ids = [m.get("id") for m in data if isinstance(m, dict) and m.get("id")]
    return sorted(ids)


@app.command()
def models(
    remote: bool = typer.Option(
        False, "--remote", "-r", help="Fetch the live list from the Z.ai API"
    ),
    models_url: str = typer.Option(
        # The coding PaaS base -- Coding Plan keys only work through the
        # coding endpoints, not the general /api/paas/v4 base.
        "https://api.z.ai/api/coding/paas/v4/models",
        "--models-url",
        envvar="GLM_MODELS_URL",
        help="PaaS models endpoint (used with --remote)",
    ),
    auth_token: str = typer.Option(
        "",
        "--auth-token",
        envvar="GLM_AUTH_TOKEN",
        help="Auth token (required with --remote)",
    ),
    timeout: float = typer.Option(30.0, "--timeout", help="Request timeout in seconds"),
) -> None:
    """List Z.ai GLM models (built-in list, or --remote for the live API list)."""
    if remote:
        if not auth_token:
            raise SystemExit(
                "--remote requires an auth token (--auth-token or GLM_AUTH_TOKEN)."
            )
        known = {model_id: desc for model_id, _, desc in ZAI_MODELS}
        ids = _fetch_remote_models(models_url, auth_token, timeout)
        if not ids:
            print(f"No models returned from {models_url}")
            return
        print(f"Z.ai models (live from {models_url}):")
        width = max(len(model_id) for model_id in ids)
        for model_id in ids:
            desc = known.get(model_id, "")
            print(f"  {model_id.ljust(width)}  {desc}".rstrip())
        return

    print("Z.ai GLM models (use the ID in --model):")
    width = max(len(model_id) for model_id, _, _ in ZAI_MODELS)
    for model_id, window, desc in ZAI_MODELS:
        print(f"  {model_id.ljust(width)}  {_fmt_window(window).rjust(4)}  {desc}")


# ---------------------------------------------------------------------------
# bench
# ---------------------------------------------------------------------------


@app.command()
def bench(
    model: str = typer.Option("glm-5.2", "--model", "-m", help="Model to benchmark"),
    base_url: str = typer.Option(
        "https://api.z.ai/api/anthropic",
        "--base-url",
        envvar="GLM_BASE_URL",
        help="Base URL for the API endpoint",
    ),
    auth_token: str = typer.Option(
        ...,
        "--auth-token",
        envvar="GLM_AUTH_TOKEN",
        help="Auth token for the endpoint",
    ),
    timeout: float = typer.Option(30.0, "--timeout", help="Request timeout in seconds"),
) -> None:
    """Time a single /v1/messages round-trip against the configured endpoint."""
    import time
    import urllib.error
    import urllib.request

    url = f"{base_url.rstrip('/')}/v1/messages"
    payload = json.dumps(
        {
            "model": model,
            "max_tokens": 32,
            "messages": [{"role": "user", "content": "Reply: ok"}],
        }
    ).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "x-api-key": auth_token,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    print(f"  {model} via {base_url}")
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            print(f"  OK ({resp.status}) in {elapsed_ms}ms")
    except urllib.error.HTTPError as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        body = e.read().decode("utf-8", errors="replace")
        print(f"  FAIL ({e.code}) in {elapsed_ms}ms")
        if body:
            print(f"  {body[:200]}")
        raise typer.Exit(code=1)
    except urllib.error.URLError as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        print(f"  FAIL ({e.reason}) in {elapsed_ms}ms")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# usage
# ---------------------------------------------------------------------------


@app.command()
def usage() -> None:
    """Open the Z.ai usage/quota dashboard (no API exists for quota data)."""
    import webbrowser

    url = "https://z.ai/manage-apikey/subscription"
    print(f"Opening {url}")
    print("Coding Plan quotas are tracked in 5-hour and weekly windows.")
    webbrowser.open(url)


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

_CLAUDE_ENV_VARS = [
    "GLM_BASE_URL",
    "GLM_API_KEY",
    "GLM_AUTH_TOKEN",
    "GLM_MODELS_URL",
    "API_TIMEOUT_MS",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_FABLE_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
    "CLAUDE_CODE_EFFORT_LEVEL",
    "CLAUDE_CODE_ATTRIBUTION_HEADER",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW",
    "CLAUDE_CODE_MAX_CONTEXT_TOKENS",
]

_BINARIES = [
    ("claude", "~/.claude/local/claude"),
]


def _binary_version(path: str) -> str | None:
    """Return `<binary> --version` output, or None if it can't be determined."""
    import subprocess

    try:
        result = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = (result.stdout or result.stderr).strip()
    return output or None


@app.command()
def doctor() -> None:
    """Check environment variables and binary availability."""
    ok = True

    print("Environment variables:")
    for var in _CLAUDE_ENV_VARS:
        value = os.environ.get(var)
        if value:
            display = _mask(value) if var in _SECRET_VARS else value
            print(f"  {var}: {display}")
        else:
            print(f"  {var}: (not set)")

    print()
    print("Binaries:")
    for name, fallback in _BINARIES:
        found = shutil.which(name)
        if not found and fallback:
            expanded = os.path.expanduser(fallback)
            if os.path.isfile(expanded) and os.access(expanded, os.X_OK):
                found = expanded
        if found:
            version = _binary_version(found)
            suffix = f" ({version})" if version else ""
            print(f"  {name}: {found}{suffix}")
        else:
            print(f"  {name}: NOT FOUND")
            ok = False

    print()
    print(
        "Note: the default model glm-5.2[1m] needs a recent Claude Code -- if "
        "claude reports the [1m] model does not exist, upgrade Claude Code."
    )

    print()
    if ok:
        print("All checks passed.")
    else:
        print("Some checks failed. See above for details.")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Top-level provider aliases
# ---------------------------------------------------------------------------

# Expose providers at the top level so `glm-launch claude` works the same as
# `glm-launch launch claude`. The `launch` group is kept for backwards compat.
_PROVIDER_CTX = {"allow_extra_args": True, "allow_interspersed_args": False}
app.command("claude", context_settings=_PROVIDER_CTX)(launch_claude)
app.command("codex", context_settings=_PROVIDER_CTX)(launch_codex)


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def cli() -> None:
    """Run the app, defaulting to the `claude` provider when no command is given."""
    import sys

    if len(sys.argv) == 1:
        sys.argv.append("claude")
    app()


if __name__ == "__main__":
    cli()
