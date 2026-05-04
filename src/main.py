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

import typer

app = typer.Typer(invoke_without_command=True)
launch_app = typer.Typer(
    help="Launch an LLM coding tool with GLM settings.",
    invoke_without_command=True,
)
app.add_typer(launch_app, name="launch")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()


@launch_app.callback(invoke_without_command=True)
def launch_main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()


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
    install_hint = f"Install it or ensure it is on your PATH."
    raise SystemExit(f"{name!r} not found. {install_hint}")


# ---------------------------------------------------------------------------
# launch claude
# ---------------------------------------------------------------------------


@launch_app.command(
    "claude",
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False},
)
def launch_claude(
    ctx: typer.Context,
    model: str = typer.Option("glm-4.7", "--model", "-m", help="Model name to pass to claude"),
    base_url: str = typer.Option(
        "https://api.z.ai/api/anthropic",
        "--base-url",
        envvar="GLM_BASE_URL",
        help="Base URL for the API endpoint",
    ),
    api_key: str = typer.Option(
        "",
        "--api-key",
        envvar="GLM_API_KEY",
        help="API key",
    ),
    auth_token: str = typer.Option(
        ...,
        "--auth-token",
        envvar="GLM_AUTH_TOKEN",
        help="Auth token",
    ),
    api_timeout_ms: str = typer.Option(
        "3000000",
        "--api-timeout-ms",
        envvar="API_TIMEOUT_MS",
        help="API request timeout in milliseconds",
    ),
    default_haiku_model: str = typer.Option(
        "glm-4.5-air",
        "--default-haiku-model",
        envvar="ANTHROPIC_DEFAULT_HAIKU_MODEL",
        help="Default model for Haiku-tier requests",
    ),
    default_sonnet_model: str = typer.Option(
        "glm-4.7",
        "--default-sonnet-model",
        envvar="ANTHROPIC_DEFAULT_SONNET_MODEL",
        help="Default model for Sonnet-tier requests",
    ),
    default_opus_model: str = typer.Option(
        "glm-4.7",
        "--default-opus-model",
        envvar="ANTHROPIC_DEFAULT_OPUS_MODEL",
        help="Default model for Opus-tier requests",
    ),
    subagent_model: str = typer.Option(
        "glm-4.5-air",
        "--subagent-model",
        envvar="CLAUDE_CODE_SUBAGENT_MODEL",
        help="Model used for spawned subagents",
    ),
    effort_level: str = typer.Option(
        "max",
        "--effort-level",
        envvar="CLAUDE_CODE_EFFORT_LEVEL",
        help="Effort level (e.g. max)",
    ),
) -> None:
    """Launch claude with GLM environment settings."""
    binary = _find_binary("claude", "~/.claude/local/claude")

    env = os.environ.copy()
    env["ANTHROPIC_BASE_URL"] = base_url
    env["ANTHROPIC_API_KEY"] = api_key
    env["ANTHROPIC_AUTH_TOKEN"] = auth_token
    env["API_TIMEOUT_MS"] = api_timeout_ms
    env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = default_haiku_model
    env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = default_sonnet_model
    env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = default_opus_model
    env["CLAUDE_CODE_SUBAGENT_MODEL"] = subagent_model
    env["CLAUDE_CODE_EFFORT_LEVEL"] = effort_level

    cmd_args = [binary]
    if model:
        cmd_args.extend(["--model", model])
    cmd_args.extend(ctx.args)

    os.execvpe(binary, cmd_args, env)


# ---------------------------------------------------------------------------
# launch codex
# ---------------------------------------------------------------------------


@launch_app.command(
    "codex",
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False},
)
def launch_codex(
    ctx: typer.Context,
    model: str = typer.Option(None, "--model", "-m", help="Model name to pass to codex"),
) -> None:
    """Launch codex with --oss flag for local Ollama usage."""
    binary = _find_binary("codex")

    cmd_args = [binary, "--oss"]
    if model:
        cmd_args.extend(["-m", model])
    cmd_args.extend(ctx.args)

    os.execvpe(binary, cmd_args, os.environ)


# ---------------------------------------------------------------------------
# launch opencode
# ---------------------------------------------------------------------------


def _write_opencode_config(model: str | None, base_url: str) -> None:
    """Write (or update) ~/.config/opencode/opencode.json and state file."""
    config_dir = os.path.expanduser("~/.config/opencode")
    config_path = os.path.join(config_dir, "opencode.json")

    # Load existing config or start fresh
    config: dict = {}
    if os.path.isfile(config_path):
        try:
            with open(config_path) as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    config.setdefault("$schema", "https://opencode.ai/config.json")
    providers = config.setdefault("provider", {})
    ollama = providers.setdefault("ollama", {})
    ollama["npm"] = "@ai-sdk/openai-compatible"
    ollama["name"] = "Ollama (local)"
    ollama.setdefault("options", {})["baseURL"] = base_url
    models = ollama.setdefault("models", {})

    if model:
        models[model] = {"name": model, "_launch": True}

    os.makedirs(config_dir, mode=0o755, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    # Update state/model.json with recent model
    if model:
        state_dir = os.path.expanduser("~/.local/state/opencode")
        state_path = os.path.join(state_dir, "model.json")

        state: dict = {}
        if os.path.isfile(state_path):
            try:
                with open(state_path) as f:
                    state = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        recent: list = state.setdefault("recent", [])
        state.setdefault("favorite", [])
        state.setdefault("variant", {})

        entry = {"providerID": "ollama", "modelID": model}
        recent = [r for r in recent if r.get("modelID") != model]
        recent.insert(0, entry)
        state["recent"] = recent[:10]

        os.makedirs(state_dir, mode=0o755, exist_ok=True)
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
            f.write("\n")


@launch_app.command(
    "opencode",
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False},
)
def launch_opencode(
    ctx: typer.Context,
    model: str = typer.Option(None, "--model", "-m", help="Model name for opencode"),
    base_url: str = typer.Option(
        ...,
        "--base-url",
        envvar="GLM_BASE_URL",
        help="Base URL for the API endpoint",
    ),
) -> None:
    """Launch opencode after writing provider config."""
    binary = _find_binary("opencode")

    _write_opencode_config(model, base_url)

    cmd_args = [binary]
    cmd_args.extend(ctx.args)

    os.execvpe(binary, cmd_args, os.environ)


# ---------------------------------------------------------------------------
# bench
# ---------------------------------------------------------------------------


@app.command()
def bench(
    model: str = typer.Option("glm-4.7", "--model", "-m", help="Model to benchmark"),
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
    import json
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
# doctor
# ---------------------------------------------------------------------------

_CLAUDE_ENV_VARS = [
    "GLM_BASE_URL",
    "GLM_API_KEY",
    "GLM_AUTH_TOKEN",
    "API_TIMEOUT_MS",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
    "CLAUDE_CODE_EFFORT_LEVEL",
]

_BINARIES = [
    ("claude", "~/.claude/local/claude"),
    ("codex", None),
    ("opencode", None),
]

_SECRET_VARS = {"GLM_API_KEY", "GLM_AUTH_TOKEN"}


def _mask(value: str) -> str:
    """Show first 4 and last 4 chars, mask the rest."""
    if len(value) <= 10:
        return value[:2] + "***"
    return value[:4] + "***" + value[-4:]


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
        if found:
            print(f"  {name}: {found}")
        elif fallback:
            expanded = os.path.expanduser(fallback)
            if os.path.isfile(expanded) and os.access(expanded, os.X_OK):
                print(f"  {name}: {expanded} (fallback)")
            else:
                print(f"  {name}: NOT FOUND")
                ok = False
        else:
            print(f"  {name}: NOT FOUND")
            ok = False

    print()
    print("Config files:")
    opencode_config = os.path.expanduser("~/.config/opencode/opencode.json")
    if os.path.isfile(opencode_config):
        print(f"  {opencode_config}: exists")
    else:
        print(f"  {opencode_config}: not found")

    opencode_state = os.path.expanduser("~/.local/state/opencode/model.json")
    if os.path.isfile(opencode_state):
        print(f"  {opencode_state}: exists")
    else:
        print(f"  {opencode_state}: not found")

    print()
    if ok:
        print("All checks passed.")
    else:
        print("Some checks failed. See above for details.")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
