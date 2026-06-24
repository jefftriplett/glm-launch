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
# Z.ai model registry
# ---------------------------------------------------------------------------

# Current Z.ai GLM models (API IDs are lowercase). Kept here so `models` and
# the help text stay in one place. See https://z.ai/model-api
ZAI_MODELS: list[tuple[str, str]] = [
    ("glm-5.2", "Flagship — frontier reasoning, coding, and agentic tasks"),
    ("glm-5.1", "Long-horizon agentic flagship (200K context)"),
    ("glm-5", "GLM-5 flagship"),
    ("glm-5-turbo", "Speed-optimized GLM-5 variant"),
    ("glm-4.7", "Balanced cost/performance coding model"),
    ("glm-4.6", "Strong coding model, 200K context"),
    ("glm-4.5", "Previous-gen general model"),
    ("glm-4.5-air", "Lightweight, low-cost (good for subagents/haiku tier)"),
]


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
    subagent_model: str,
    effort_level: str,
    attribution_header: str = "0",
    auto_compact_window: str = "",
) -> dict[str, str]:
    """Build the GLM env vars claude needs to talk to Z.ai."""
    env = {
        "ANTHROPIC_BASE_URL": base_url,
        "ANTHROPIC_API_KEY": api_key,
        "ANTHROPIC_AUTH_TOKEN": auth_token,
        "API_TIMEOUT_MS": api_timeout_ms,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": default_haiku_model,
        "ANTHROPIC_DEFAULT_SONNET_MODEL": default_sonnet_model,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": default_opus_model,
        "CLAUDE_CODE_SUBAGENT_MODEL": subagent_model,
        "CLAUDE_CODE_EFFORT_LEVEL": effort_level,
        "CLAUDE_CODE_ATTRIBUTION_HEADER": attribution_header,
    }
    if model:
        env["ANTHROPIC_MODEL"] = model
    if auto_compact_window:
        env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] = auto_compact_window
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
    model: str = typer.Option(
        "glm-5.2", "--model", "-m", help="Model name to pass to claude"
    ),
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
        "glm-5.2",
        "--default-sonnet-model",
        envvar="ANTHROPIC_DEFAULT_SONNET_MODEL",
        help="Default model for Sonnet-tier requests",
    ),
    default_opus_model: str = typer.Option(
        "glm-5.2",
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
    attribution_header: str = typer.Option(
        "0",
        "--attribution-header",
        envvar="CLAUDE_CODE_ATTRIBUTION_HEADER",
        help="Attribution header toggle (0 disables it)",
    ),
    auto_compact_window: str = typer.Option(
        "200000",
        "--auto-compact-window",
        envvar="CLAUDE_CODE_AUTO_COMPACT_WINDOW",
        help="Auto-compact context window (token count); empty to leave unset",
    ),
) -> None:
    """Launch claude with GLM environment settings."""
    binary = _find_binary("claude", "~/.claude/local/claude")

    env = os.environ.copy()
    env.update(
        _build_claude_env(
            model=model,
            base_url=base_url,
            api_key=api_key,
            auth_token=auth_token,
            api_timeout_ms=api_timeout_ms,
            default_haiku_model=default_haiku_model,
            default_sonnet_model=default_sonnet_model,
            default_opus_model=default_opus_model,
            subagent_model=subagent_model,
            effort_level=effort_level,
            attribution_header=attribution_header,
            auto_compact_window=auto_compact_window,
        )
    )

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
    model: str = typer.Option(
        None, "--model", "-m", help="Model name to pass to codex"
    ),
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
# shell
# ---------------------------------------------------------------------------


def _shell_quote(value: str) -> str:
    """Single-quote a value safely for POSIX shell eval."""
    return "'" + value.replace("'", "'\"'\"'") + "'"


@app.command()
def shell(
    model: str = typer.Option(
        "glm-5.2", "--model", "-m", help="Top-level model (ANTHROPIC_MODEL)"
    ),
    base_url: str = typer.Option(
        "https://api.z.ai/api/anthropic",
        "--base-url",
        envvar="GLM_BASE_URL",
        help="Base URL for the API endpoint",
    ),
    api_key: str = typer.Option("", "--api-key", envvar="GLM_API_KEY", help="API key"),
    auth_token: str = typer.Option(
        ..., "--auth-token", envvar="GLM_AUTH_TOKEN", help="Auth token"
    ),
    api_timeout_ms: str = typer.Option(
        "3000000", "--api-timeout-ms", envvar="API_TIMEOUT_MS"
    ),
    default_haiku_model: str = typer.Option(
        "glm-4.5-air", "--default-haiku-model", envvar="ANTHROPIC_DEFAULT_HAIKU_MODEL"
    ),
    default_sonnet_model: str = typer.Option(
        "glm-5.2", "--default-sonnet-model", envvar="ANTHROPIC_DEFAULT_SONNET_MODEL"
    ),
    default_opus_model: str = typer.Option(
        "glm-5.2", "--default-opus-model", envvar="ANTHROPIC_DEFAULT_OPUS_MODEL"
    ),
    subagent_model: str = typer.Option(
        "glm-4.5-air", "--subagent-model", envvar="CLAUDE_CODE_SUBAGENT_MODEL"
    ),
    effort_level: str = typer.Option(
        "max", "--effort-level", envvar="CLAUDE_CODE_EFFORT_LEVEL"
    ),
    attribution_header: str = typer.Option(
        "0", "--attribution-header", envvar="CLAUDE_CODE_ATTRIBUTION_HEADER"
    ),
    auto_compact_window: str = typer.Option(
        "200000", "--auto-compact-window", envvar="CLAUDE_CODE_AUTO_COMPACT_WINDOW"
    ),
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
        subagent_model=subagent_model,
        effort_level=effort_level,
        attribution_header=attribution_header,
        auto_compact_window=auto_compact_window,
    )
    for key, value in env.items():
        if value:
            print(f"export {key}={_shell_quote(value)}")


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------


def _fetch_remote_models(models_url: str, auth_token: str, timeout: float) -> list[str]:
    """Fetch the live model ID list from the Z.ai PaaS /models endpoint."""
    import json
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
        "https://api.z.ai/api/paas/v4/models",
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
        known = dict(ZAI_MODELS)
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
    width = max(len(model_id) for model_id, _ in ZAI_MODELS)
    for model_id, desc in ZAI_MODELS:
        print(f"  {model_id.ljust(width)}  {desc}")


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
