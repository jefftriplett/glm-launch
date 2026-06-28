# glm-launch

A Python CLI tool that wraps LLM coding tools (`claude`, `codex`, `opencode`) with [GLM](https://docs.z.ai/) settings. Instead of running a local proxy, it configures environment variables and config files, then exec's the underlying binary directly.

It works with [Z.AI](https://z.ai/) and their GLM series of models. You'll need a Z.AI API key — grab one with a [Z.AI Coding Plan subscription](https://z.ai/subscribe?ic=GLMN4NLXLV). Using that referral link gives you 10% off and gets me 10% off too. Prefer not to? Here's a [non-affiliate link](https://z.ai/subscribe).

Requires Python 3.13+.

## Usage

```bash
# 1. Set your Z.AI auth token
export GLM_AUTH_TOKEN="your-zai-api-key"

# 2. Launch Claude Code routed through Z.AI (defaults to glm-5.2)
uv run glm-launch              # bare command defaults to `claude`
uv run glm-launch claude       # same thing, explicit

# Pick a different model
uv run glm-launch claude --model glm-5.1        # long-horizon flagship
uv run glm-launch claude --model glm-5-turbo    # fast
uv run glm-launch claude --model glm-4.5-air    # cheap

# Bootstrap your current shell so a plain `claude` uses Z.AI
eval "$(uv run glm-launch shell)"
claude

# See available models (built-in list, or --remote for the live API list)
uv run glm-launch models
uv run glm-launch models --remote

# Sanity-check connectivity / latency
uv run glm-launch bench
```

> Examples use the installed `glm-launch` entrypoint. Before `uv sync` you can run
> the script directly with `uv run src/main.py …` — the two are interchangeable.

## Installation

```bash
uv sync
```

This installs a `glm-launch` entrypoint. Run commands via `uv run glm-launch <command>`, or `uv tool install .` to get `glm-launch` on your PATH directly. You can also run the script without installing via `uv run src/main.py <command>`.

### Run without cloning (`uvx`)

[`glm-launch` is on PyPI](https://pypi.org/project/glm-launch/), so you can run it directly with [`uvx`](https://docs.astral.sh/uv/guides/tools/) (`uv tool run`) — no clone or manual install needed.

```bash
# From PyPI
uvx glm-launch launch claude

# Or straight from GitHub
uvx --from git+https://github.com/jefftriplett/glm-launch glm-launch launch claude

# Pin to a tag/branch/commit
uvx --from git+https://github.com/jefftriplett/glm-launch@main glm-launch models
```

## Commands

### `launch claude`

Launch [Claude Code](https://docs.anthropic.com/en/docs/claude-code) with GLM environment settings. Sets Anthropic env vars to route requests through Z.AI's Anthropic-compatible endpoint, then exec's the `claude` binary.

> The `launch` prefix is optional: `glm-launch claude` is equivalent to `glm-launch launch claude`, and a bare `glm-launch` defaults to `claude`. The same applies to `codex` and `opencode`.

```bash
uv run glm-launch launch claude
```

**Options:**

| Flag | Env var | Default | Description |
|------|---------|---------|-------------|
| `--model` / `-m` | — | `glm-5.2` | Model name passed to `claude --model` |
| `--base-url` | `GLM_BASE_URL` | `https://api.z.ai/api/anthropic` | API endpoint |
| `--api-key` | `GLM_API_KEY` | `""` | API key |
| `--auth-token` | `GLM_AUTH_TOKEN` | **(required)** | Z.AI auth token |
| `--api-timeout-ms` | `API_TIMEOUT_MS` | `3000000` | Request timeout in milliseconds |
| `--default-haiku-model` | `ANTHROPIC_DEFAULT_HAIKU_MODEL` | `glm-4.5-air` | Model for Haiku-tier requests |
| `--default-sonnet-model` | `ANTHROPIC_DEFAULT_SONNET_MODEL` | `glm-5.2` | Model for Sonnet-tier requests |
| `--default-opus-model` | `ANTHROPIC_DEFAULT_OPUS_MODEL` | `glm-5.2` | Model for Opus-tier requests |
| `--subagent-model` | `CLAUDE_CODE_SUBAGENT_MODEL` | `glm-4.5-air` | Model used for spawned subagents |
| `--effort-level` | `CLAUDE_CODE_EFFORT_LEVEL` | `max` | Effort level for the agent loop |
| `--attribution-header` | `CLAUDE_CODE_ATTRIBUTION_HEADER` | `0` | Attribution header toggle (`0` disables it) |
| `--auto-compact-window` | `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | `200000` | Auto-compact context window in tokens (empty to leave unset) |
| `--dry-run` | — | `false` | Print the resolved command and masked GLM environment without launching |

The following env vars are set before exec'ing `claude`:

- `ANTHROPIC_BASE_URL` — from `--base-url` / `GLM_BASE_URL`
- `ANTHROPIC_API_KEY` — from `--api-key` / `GLM_API_KEY`
- `ANTHROPIC_AUTH_TOKEN` — from `--auth-token` / `GLM_AUTH_TOKEN`
- `API_TIMEOUT_MS` — from `--api-timeout-ms` / `API_TIMEOUT_MS`
- `ANTHROPIC_DEFAULT_HAIKU_MODEL` — from `--default-haiku-model`
- `ANTHROPIC_DEFAULT_SONNET_MODEL` — from `--default-sonnet-model`
- `ANTHROPIC_DEFAULT_OPUS_MODEL` — from `--default-opus-model`
- `CLAUDE_CODE_SUBAGENT_MODEL` — from `--subagent-model`
- `CLAUDE_CODE_EFFORT_LEVEL` — from `--effort-level`
- `CLAUDE_CODE_ATTRIBUTION_HEADER` — from `--attribution-header`
- `CLAUDE_CODE_AUTO_COMPACT_WINDOW` — from `--auto-compact-window` (only when non-empty)

**Examples:**

```bash
# Use defaults (glm-5.2, Z.AI endpoint)
uv run glm-launch launch claude

# Flagship reasoning/coding model (the default)
uv run glm-launch launch claude --model glm-5.2

# Long-horizon agentic flagship
uv run glm-launch launch claude --model glm-5.1

# Fast, speed-optimized GLM-5 variant
uv run glm-launch launch claude --model glm-5-turbo

# Lightweight, low-cost model for cheaper runs
uv run glm-launch launch claude --model glm-4.5-air

# Tune the model tiers independently (e.g. cheap subagents, flagship main)
uv run glm-launch launch claude \
  --model glm-5.2 \
  --subagent-model glm-4.5-air \
  --default-haiku-model glm-4.5-air

# Pass extra args through to claude
uv run glm-launch launch claude -- --verbose

# Inspect the command/env without launching claude
uv run glm-launch launch claude --dry-run

# Override via env vars
GLM_AUTH_TOKEN="my-token" uv run glm-launch launch claude
```

Run `uv run glm-launch models` to see all valid model names (or `--remote` for the live list).

If `claude` is not on your PATH, the tool falls back to `~/.claude/local/claude`.

### `launch codex`

Launch [Codex](https://github.com/openai/codex) with the `--oss` flag for local Ollama usage.

```bash
uv run glm-launch launch codex
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--model` / `-m` | — | Model name passed to `codex -m` |
| `--dry-run` | `false` | Print the resolved command without launching |

**Examples:**

```bash
# Launch with default settings
uv run glm-launch launch codex

# Specify a model
uv run glm-launch launch codex --model "some-model"

# Pass extra args through to codex
uv run glm-launch launch codex -- --some-flag

# Inspect the command without launching codex
uv run glm-launch launch codex --dry-run
```

### `launch opencode`

Launch [opencode](https://opencode.ai/) after writing provider config. Writes an OpenAI-compatible `glm` provider to `~/.config/opencode/opencode.json` and updates the recent model state at `~/.local/state/opencode/model.json`, then exec's the `opencode` binary.

```bash
uv run glm-launch launch opencode --model "some-model"
```

**Options:**

| Flag | Env var | Default | Description |
|------|---------|---------|-------------|
| `--model` / `-m` | — | — | Model name to configure in opencode |
| `--base-url` | `GLM_BASE_URL` | **(required)** | Base URL for the API endpoint |
| `--dry-run` | — | `false` | Print the resolved command and config changes without launching or writing files |

**Examples:**

```bash
# Launch with a model
GLM_BASE_URL="http://localhost:11434/v1" uv run glm-launch launch opencode --model "llama3"

# Pass extra args through to opencode
uv run glm-launch launch opencode --model "llama3" -- --some-flag

# Inspect config changes without writing files or launching opencode
uv run glm-launch launch opencode --model "llama3" --dry-run
```

### `shell`

Print `export` lines that bootstrap your current shell with the GLM env vars — without launching anything. Eval the output and a plain `claude` (or any Anthropic SDK tool) will talk to Z.AI.

```bash
eval "$(uv run glm-launch shell)"
claude
```

Accepts the same model/auth options as `launch claude` (`--model`, `--auth-token`, `--default-*-model`, etc.). Secrets are shell-quoted; empty values are skipped. Sets `ANTHROPIC_MODEL` plus all the `ANTHROPIC_*` / `CLAUDE_CODE_*` vars listed under `launch claude`.

```bash
# Inspect what would be exported
uv run glm-launch shell

# Bootstrap with a specific model
eval "$(uv run glm-launch shell --model glm-5.1)"
```

### `models`

List Z.AI GLM models. By default prints a built-in, annotated list; `--remote` fetches the live list from the Z.AI PaaS endpoint.

```bash
# Built-in list (no token needed)
uv run glm-launch models

# Live list from the API (needs GLM_AUTH_TOKEN)
uv run glm-launch models --remote
```

**Options:**

| Flag | Env var | Default | Description |
|------|---------|---------|-------------|
| `--remote` / `-r` | — | `false` | Fetch the live list from the Z.AI API |
| `--models-url` | `GLM_MODELS_URL` | `https://api.z.ai/api/paas/v4/models` | PaaS models endpoint (used with `--remote`) |
| `--auth-token` | `GLM_AUTH_TOKEN` | — | Auth token (required with `--remote`) |
| `--timeout` | — | `30.0` | Request timeout in seconds |

The live endpoint is the OpenAI-compatible PaaS base (`/api/paas/v4/models`) and uses `Authorization: Bearer <token>` — distinct from the Anthropic-style chat base (`/api/anthropic`) used by `launch claude` and `bench`.

### `bench`

Time a single `/v1/messages` round-trip against the configured GLM endpoint. Useful as a sanity check that your auth token, base URL, and chosen model are reachable.

```bash
uv run glm-launch bench
```

**Options:**

| Flag | Env var | Default | Description |
|------|---------|---------|-------------|
| `--model` / `-m` | — | `glm-5.2` | Model to benchmark |
| `--base-url` | `GLM_BASE_URL` | `https://api.z.ai/api/anthropic` | API endpoint |
| `--auth-token` | `GLM_AUTH_TOKEN` | **(required)** | Auth token for the endpoint |
| `--timeout` | — | `30.0` | Request timeout in seconds |

Sends a minimal 32-token request and prints the round-trip time. Exits non-zero on HTTP error or timeout.

**Example output:**

```
  glm-5.2 via https://api.z.ai/api/anthropic
  OK (200) in 412ms
```

### `doctor`

Check your environment for correct setup. Reports on environment variables, binary availability, and config files.

```bash
uv run glm-launch doctor
```

**Checks performed:**

- **Environment variables** — Whether the GLM, Anthropic default-model, and Claude Code env vars used by the launch commands are set. Secrets are masked in output.
- **Binaries** — Whether `claude`, `codex`, and `opencode` are found on PATH (with fallback to `~/.claude/local/claude` for claude).
- **Config files** — Whether `~/.config/opencode/opencode.json` and `~/.local/state/opencode/model.json` exist.

Exits with code 1 if any binary is missing, 0 otherwise.

**Example output:**

```
Environment variables:
  GLM_BASE_URL: (not set)
  GLM_API_KEY: (not set)
  GLM_AUTH_TOKEN: (not set)
  GLM_MODELS_URL: (not set)
  API_TIMEOUT_MS: (not set)
  ANTHROPIC_DEFAULT_HAIKU_MODEL: (not set)
  ANTHROPIC_DEFAULT_SONNET_MODEL: (not set)
  ANTHROPIC_DEFAULT_OPUS_MODEL: (not set)
  CLAUDE_CODE_SUBAGENT_MODEL: (not set)
  CLAUDE_CODE_EFFORT_LEVEL: (not set)
  CLAUDE_CODE_ATTRIBUTION_HEADER: (not set)
  CLAUDE_CODE_AUTO_COMPACT_WINDOW: (not set)

Binaries:
  claude: /usr/local/bin/claude
  codex: /usr/local/bin/codex
  opencode: /usr/local/bin/opencode

Config files:
  /home/user/.config/opencode/opencode.json: exists
  /home/user/.local/state/opencode/model.json: not found

All checks passed.
```

## Environment variables

| Variable | Used by | Description |
|----------|---------|-------------|
| `GLM_BASE_URL` | `launch claude`, `launch opencode`, `shell` | API base URL |
| `GLM_API_KEY` | `launch claude`, `shell` | API key |
| `GLM_AUTH_TOKEN` | `launch claude`, `shell`, `bench`, `models --remote` | Z.AI auth token (required) |
| `GLM_MODELS_URL` | `models --remote` | PaaS models endpoint |
| `API_TIMEOUT_MS` | `launch claude`, `shell` | Request timeout in milliseconds |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | `launch claude`, `shell` | Model for Haiku-tier requests |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | `launch claude`, `shell` | Model for Sonnet-tier requests |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | `launch claude`, `shell` | Model for Opus-tier requests |
| `CLAUDE_CODE_SUBAGENT_MODEL` | `launch claude`, `shell` | Model used for spawned subagents |
| `CLAUDE_CODE_EFFORT_LEVEL` | `launch claude`, `shell` | Effort level for the agent loop |
| `CLAUDE_CODE_ATTRIBUTION_HEADER` | `launch claude`, `shell` | Attribution header toggle (`0` disables it) |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | `launch claude`, `shell` | Auto-compact context window in tokens |

## How it works

Each provider follows the same pattern:

1. Resolve the binary on PATH (with optional fallback path)
2. Set up configuration (env vars for claude, config files for opencode, flags for codex)
3. `os.execvpe()` the binary — fully replacing the glm process with the underlying tool for direct stdio passthrough

For Claude specifically, Z.AI exposes an Anthropic-compatible endpoint at `https://api.z.ai/api/anthropic`, so no local proxy is needed. The CLI sets the standard `ANTHROPIC_*` env vars and Claude Code talks directly to Z.AI.

## Development

Common tasks are wrapped in a [`justfile`](https://github.com/casey/just). Run `just` with no arguments to list them.

| Recipe | Description |
|--------|-------------|
| `just bootstrap` | Upgrade `pip`/`uv`, then `uv sync` |
| `just sync` | `uv sync` the project dependencies |
| `just lock` | `uv lock` the dependency versions |
| `just build` | `uv build` the wheel and sdist |
| `just bump *ARGS` | Bump the CalVer version with `bumpver` (e.g. `just bump`) |
| `just bump-dry *ARGS` | Preview a version bump without writing changes |
| `just release *ARGS` | Bump, relock, and push the tag — CI then publishes to PyPI |
| `just lint *ARGS` | Run the [prek](https://github.com/j178/prek) hooks (defaults to `--all-files`) |
| `just fmt` | Format the `justfile` itself |
| `just demo` | Smoke-test the CLI by listing models |

Versioning follows [CalVer](https://calver.org/) (`YYYY.MM.INC1`), and lint hooks (ruff, pyupgrade, validate-pyproject) are configured in `.pre-commit-config.yaml` and run with `prek`.

Releases are automated. Run `just release` to bump the CalVer version, relock, and push the tag in one step. Pushing a `YYYY.MM.INC1` tag triggers the GitHub Actions release workflow, which builds and publishes to PyPI via [trusted publishing](https://docs.pypi.org/trusted-publishers/) (OIDC, no API token). A plain `git push` never publishes — only the tag does.
