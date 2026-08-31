"""Live checks that every registry model ID actually resolves at Z.ai.

These are opt-in: they need a real `GLM_AUTH_TOKEN` and hit the network, so
they are skipped unless `GLM_LIVE_TESTS=1` is set. Run them with:

    GLM_LIVE_TESTS=1 uv run pytest -m live -v

The offline suite can only prove the registry's arithmetic is self-consistent.
It cannot prove an ID is real: Z.ai answers an unknown *or unentitled* model
with HTTP 400 `modelCode: does not exist`, so a `[1m]` tier the plan does not
cover looks identical to a typo until something calls it.
"""

from __future__ import annotations

import os

import pytest

import main

BASE_URL = os.environ.get("GLM_BASE_URL", "https://api.z.ai/api/anthropic")
TIMEOUT = float(os.environ.get("GLM_LIVE_TIMEOUT", "30"))

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("GLM_LIVE_TESTS") != "1",
        reason="live API tests are opt-in; set GLM_LIVE_TESTS=1",
    ),
    pytest.mark.skipif(
        not os.environ.get("GLM_AUTH_TOKEN"),
        reason="live API tests need GLM_AUTH_TOKEN",
    ),
]

ALL_MODELS = [model_id for model_id, _, _ in main.ZAI_MODELS]
ONE_M_MODELS = [m for m in ALL_MODELS if m.endswith("[1m]")]


_CACHE: dict[str, main.ProbeResult] = {}


def _probe(model: str) -> main.ProbeResult:
    """Probe a model once per session; several tests assert on the same call."""
    if model not in _CACHE:
        _CACHE[model] = main._probe_model(
            model, BASE_URL, os.environ["GLM_AUTH_TOKEN"], TIMEOUT
        )
    return _CACHE[model]


@pytest.mark.parametrize("model", ALL_MODELS)
def test_registry_model_resolves(model: str) -> None:
    """Every advertised model ID must be callable, not just well-formed."""
    result = _probe(model)
    if result.throttled:
        pytest.skip(f"{model} is rate limited / out of quota right now")
    assert result.ok, (
        f"{model} did not resolve ({result.status}): {result.body[:200]}\n"
        "If this is a `[1m]` ID, Z.ai did not accept the suffix for this key."
    )


@pytest.mark.parametrize("model", ONE_M_MODELS)
def test_one_m_models_are_not_silently_missing(model: str) -> None:
    """A `[1m]` ID must not 400 with `does not exist`.

    This is the failure that shipped in 2026.8.3: the registry promised a 1M
    window for an ID the API rejected outright.
    """
    result = _probe(model)
    if result.throttled:
        pytest.skip(f"{model} is rate limited / out of quota right now")
    assert not result.unknown_model, (
        f"{model} is advertised in ZAI_MODELS but Z.ai rejects it as unknown. "
        "Either the 1M tier is not enabled for this key or the ID should go."
    )


@pytest.mark.parametrize("model", ONE_M_MODELS)
def test_one_m_models_claim_a_1m_window(model: str) -> None:
    """A `[1m]` ID that resolves should also be registered as 1M."""
    assert main._context_window_for(model) == 1_000_000
