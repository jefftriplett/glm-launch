@_default:
    just --list

@bootstrap:
    python -m pip install --upgrade pip uv
    just sync

@build:
    uv build

@bump *ARGS:
    uv tool run bumpver update --allow-dirty {{ ARGS }}

@bump-dry *ARGS:
    just bump --dry {{ ARGS }}

@demo:
    uv run glm-launch models

@fmt:
    just --fmt --unstable

@lint *ARGS="--all-files":
    uv tool run prek run {{ ARGS }}

@lock:
    uv lock

# Bump the CalVer version, relock, and push the tag (CI publishes to PyPI)
release *ARGS:
    #!/usr/bin/env bash
    set -euo pipefail
    just bump {{ ARGS }}
    just lock
    version="$(grep -m1 '^current_version' pyproject.toml | cut -d'"' -f2)"
    git add uv.lock
    git commit --amend --no-edit
    git tag -d "$version"
    git tag -a "$version" -m "$version"
    git push --follow-tags

@sync:
    uv sync
