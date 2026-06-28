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

@sync:
    uv sync
