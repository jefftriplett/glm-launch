# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

glm-cli-git is a Python CLI tool that wraps LLM coding tools (`claude`, `codex`, `opencode`) with GLM settings. It requires Python 3.13+ and uses Typer for CLI handling. Configuration is driven by environment variables (`GLM_BASE_URL`, `GLM_API_KEY`, `GLM_AUTH_TOKEN`).

## Commands

```bash
# Show top-level help
uv run src/main.py --help

# Show available providers
uv run src/main.py launch --help

# Launch claude (requires GLM_BASE_URL env var)
uv run src/main.py launch claude

# Launch claude with a specific model
uv run src/main.py launch claude --model "some-model"

# Launch codex (always passes --oss)
uv run src/main.py launch codex --model "some-model"

# Launch opencode (writes config JSON, then runs)
uv run src/main.py launch opencode --model "some-model"

# Pass extra args through to the underlying tool
uv run src/main.py launch claude -- --verbose

# Time a request against the configured GLM endpoint
uv run src/main.py bench

# List known Z.ai GLM models (built-in list)
uv run src/main.py models

# Fetch the live model list from the Z.ai API (needs GLM_AUTH_TOKEN)
uv run src/main.py models --remote

# Bootstrap the current shell with GLM env vars (so a plain `claude` uses Z.ai)
eval "$(uv run src/main.py shell)"
```

## Architecture

Single-module project with entry point at `src/main.py` (the installed `glm-launch` console script calls `cli()`, which defaults to the `claude` provider when no command is given). Uses Typer with a two-level command structure: `glm launch <provider>`. Providers are also registered at the top level so `glm-launch <provider>` works without the `launch` prefix. Each provider gets its own `@launch_app.command()` with provider-specific setup logic:

- **claude** — Sets `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_DEFAULT_*_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_EFFORT_LEVEL`, `CLAUDE_CODE_ATTRIBUTION_HEADER`, and `CLAUDE_CODE_AUTO_COMPACT_WINDOW` env vars from GLM settings, passes `--model` flag. Falls back to `~/.claude/local/claude` if not on PATH.
- **codex** — Always passes `--oss` flag, passes `-m` for model. No env vars or config files.
- **opencode** — Writes provider config to `~/.config/opencode/opencode.json` and recent model state to `~/.local/state/opencode/model.json`, then execs the binary. No env vars.

All providers exec the underlying binary via `os.execvpe()` for full stdio passthrough.
