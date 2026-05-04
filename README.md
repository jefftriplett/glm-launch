# glm-cli-git

A Python CLI tool that wraps LLM coding tools (`claude`, `codex`, `opencode`) with [GLM](https://docs.z.ai/) settings. Instead of running a local proxy, it configures environment variables and config files, then exec's the underlying binary directly.

Requires Python 3.13+.

## Installation

```bash
uv sync
```

## Quick start

```bash
# Set your Z.AI auth token (required for claude)
export GLM_AUTH_TOKEN="your-zai-api-key"

# Launch Claude Code with GLM defaults
uv run src/main.py launch claude
```

## Commands

### `launch claude`

Launch [Claude Code](https://docs.anthropic.com/en/docs/claude-code) with GLM environment settings. Sets Anthropic env vars to route requests through Z.AI's Anthropic-compatible endpoint, then exec's the `claude` binary.

```bash
uv run src/main.py launch claude
```

**Options:**

| Flag | Env var | Default | Description |
|------|---------|---------|-------------|
| `--model` / `-m` | — | `glm-4.7` | Model name passed to `claude --model` |
| `--base-url` | `GLM_BASE_URL` | `https://api.z.ai/api/anthropic` | API endpoint |
| `--api-key` | `GLM_API_KEY` | `""` | API key |
| `--auth-token` | `GLM_AUTH_TOKEN` | **(required)** | Z.AI auth token |
| `--api-timeout-ms` | `API_TIMEOUT_MS` | `3000000` | Request timeout in milliseconds |
| `--default-haiku-model` | `ANTHROPIC_DEFAULT_HAIKU_MODEL` | `glm-4.5-air` | Model for Haiku-tier requests |
| `--default-sonnet-model` | `ANTHROPIC_DEFAULT_SONNET_MODEL` | `glm-4.7` | Model for Sonnet-tier requests |
| `--default-opus-model` | `ANTHROPIC_DEFAULT_OPUS_MODEL` | `glm-4.7` | Model for Opus-tier requests |
| `--subagent-model` | `CLAUDE_CODE_SUBAGENT_MODEL` | `glm-4.5-air` | Model used for spawned subagents |
| `--effort-level` | `CLAUDE_CODE_EFFORT_LEVEL` | `max` | Effort level for the agent loop |

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

**Examples:**

```bash
# Use defaults (glm-4.7, Z.AI endpoint)
uv run src/main.py launch claude

# Override the model
uv run src/main.py launch claude --model "glm-4.5-air"

# Pass extra args through to claude
uv run src/main.py launch claude -- --verbose

# Override via env vars
GLM_AUTH_TOKEN="my-token" uv run src/main.py launch claude
```

If `claude` is not on your PATH, the tool falls back to `~/.claude/local/claude`.

### `launch codex`

Launch [Codex](https://github.com/openai/codex) with the `--oss` flag for local Ollama usage.

```bash
uv run src/main.py launch codex
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--model` / `-m` | — | Model name passed to `codex -m` |

**Examples:**

```bash
# Launch with default settings
uv run src/main.py launch codex

# Specify a model
uv run src/main.py launch codex --model "some-model"

# Pass extra args through to codex
uv run src/main.py launch codex -- --some-flag
```

### `launch opencode`

Launch [opencode](https://opencode.ai/) after writing provider config. Writes an Ollama-compatible provider to `~/.config/opencode/opencode.json` and updates the recent model state at `~/.local/state/opencode/model.json`, then exec's the `opencode` binary.

```bash
uv run src/main.py launch opencode --model "some-model"
```

**Options:**

| Flag | Env var | Default | Description |
|------|---------|---------|-------------|
| `--model` / `-m` | — | — | Model name to configure in opencode |
| `--base-url` | `GLM_BASE_URL` | **(required)** | Base URL for the API endpoint |

**Examples:**

```bash
# Launch with a model
GLM_BASE_URL="http://localhost:11434/v1" uv run src/main.py launch opencode --model "llama3"

# Pass extra args through to opencode
uv run src/main.py launch opencode --model "llama3" -- --some-flag
```

### `bench`

Time a single `/v1/messages` round-trip against the configured GLM endpoint. Useful as a sanity check that your auth token, base URL, and chosen model are reachable.

```bash
uv run src/main.py bench
```

**Options:**

| Flag | Env var | Default | Description |
|------|---------|---------|-------------|
| `--model` / `-m` | — | `glm-4.7` | Model to benchmark |
| `--base-url` | `GLM_BASE_URL` | `https://api.z.ai/api/anthropic` | API endpoint |
| `--auth-token` | `GLM_AUTH_TOKEN` | **(required)** | Auth token for the endpoint |
| `--timeout` | — | `30.0` | Request timeout in seconds |

Sends a minimal 32-token request and prints the round-trip time. Exits non-zero on HTTP error or timeout.

**Example output:**

```
  glm-4.7 via https://api.z.ai/api/anthropic
  OK (200) in 412ms
```

### `doctor`

Check your environment for correct setup. Reports on environment variables, binary availability, and config files.

```bash
uv run src/main.py doctor
```

**Checks performed:**

- **Environment variables** — Whether `GLM_BASE_URL`, `GLM_API_KEY`, `GLM_AUTH_TOKEN`, `API_TIMEOUT_MS`, and the `ANTHROPIC_DEFAULT_*_MODEL` vars are set. Secrets are masked in output.
- **Binaries** — Whether `claude`, `codex`, and `opencode` are found on PATH (with fallback to `~/.claude/local/claude` for claude).
- **Config files** — Whether `~/.config/opencode/opencode.json` and `~/.local/state/opencode/model.json` exist.

Exits with code 1 if any binary is missing, 0 otherwise.

**Example output:**

```
Environment variables:
  GLM_BASE_URL: (not set)
  GLM_API_KEY: (not set)
  GLM_AUTH_TOKEN: (not set)
  API_TIMEOUT_MS: (not set)
  ANTHROPIC_DEFAULT_HAIKU_MODEL: (not set)
  ANTHROPIC_DEFAULT_SONNET_MODEL: (not set)
  ANTHROPIC_DEFAULT_OPUS_MODEL: (not set)

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
| `GLM_BASE_URL` | `launch claude`, `launch opencode` | API base URL |
| `GLM_API_KEY` | `launch claude` | API key |
| `GLM_AUTH_TOKEN` | `launch claude` | Z.AI auth token (required) |
| `API_TIMEOUT_MS` | `launch claude` | Request timeout in milliseconds |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | `launch claude` | Model for Haiku-tier requests |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | `launch claude` | Model for Sonnet-tier requests |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | `launch claude` | Model for Opus-tier requests |
| `CLAUDE_CODE_SUBAGENT_MODEL` | `launch claude` | Model used for spawned subagents |
| `CLAUDE_CODE_EFFORT_LEVEL` | `launch claude` | Effort level for the agent loop |

## How it works

Each provider follows the same pattern:

1. Resolve the binary on PATH (with optional fallback path)
2. Set up configuration (env vars for claude, config files for opencode, flags for codex)
3. `os.execvpe()` the binary — fully replacing the glm process with the underlying tool for direct stdio passthrough

For Claude specifically, Z.AI exposes an Anthropic-compatible endpoint at `https://api.z.ai/api/anthropic`, so no local proxy is needed. The CLI sets the standard `ANTHROPIC_*` env vars and Claude Code talks directly to Z.AI.
