"""Model clients for the cross-model eval matrix (design doc §10.3).

Every call takes a system prompt and a user prompt and returns the model's
raw text response. There is no shared SDK dependency here on purpose --
each provider's wire format is small enough that a stdlib `urllib` request
is less to maintain than an extra pinned dependency per provider, and it
keeps every HTTP call inspectable in one place when a run needs debugging.
Transient failures (timeouts, 429/5xx) are retried with backoff in
_post_json so one slow generation doesn't silently shrink a paid run.

Which model plays which of the three matrix slots (Claude / GPT / Qwen) is
a repo decision, not a per-run flag -- see MODEL_MATRIX below and design
doc §10.3 / §14.3.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

REQUEST_TIMEOUT_SECS = 120

# A run is paid work: a transient 429/503 or a slow generation that trips the
# timeout should cost a few retries, not a silently dropped cell and a
# shrunken sample. Non-transient failures (auth, a 400 on a bad parameter)
# still fail on the first try -- retrying them just wastes minutes.
MAX_ATTEMPTS = 4
RETRY_BACKOFF_SECS = 4
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class ModelCallError(RuntimeError):
    """Raised when a provider call can't be made or fails outright."""


class _TransientCallError(Exception):
    """Internal: a failure worth retrying. Never escapes this module -- once
    the attempts are spent it is re-raised as a ModelCallError."""

    def __init__(self, message: str, retry_after: str | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


# Every provider signals "I hit the token cap mid-answer" with one of these
# in its finish/stop-reason field. A truncated completion is a syntactically
# broken partial file; scoring or judging it as a finished answer skews
# M1/M2/M3, so callers reject it instead of writing it.
TRUNCATION_REASONS = frozenset({"length", "max_tokens", "MAX_TOKENS"})


def _reject_if_truncated(label: str, finish_reason: str | None, sampler: SamplerSettings) -> None:
    if finish_reason in TRUNCATION_REASONS:
        raise ModelCallError(
            f"{label}: completion truncated at max_tokens={sampler.max_tokens} "
            f"(finish_reason={finish_reason!r}) -- raise max_tokens or shorten the "
            f"task; a cut-off completion must not be scored as a finished answer"
        )


@dataclass(frozen=True)
class SamplerSettings:
    """Recorded verbatim in RESULTS.md per design doc §10.3 -- reproducibility
    for a hosted model lives in the sampler settings, not the model name."""

    temperature: float
    top_p: float
    max_tokens: int


# Code generation wants low-variance sampling: two runs of the same
# scenario/model/condition should be comparable, not a coin flip on style.
DEFAULT_SAMPLER = SamplerSettings(temperature=0.2, top_p=1.0, max_tokens=2000)


@dataclass(frozen=True)
class ModelSpec:
    """One slot in the three-model matrix.

    `skill_artifact` names which generated artifact stands in for "skill
    condition" for this model, matching the distribution mechanism that
    model's harness would actually use in practice (PRD R3.2):
      - "skill_md"     Claude runs skills natively -- use the full skill.
      - "agent_block"  GPT via an AGENTS.md-reading harness (e.g. Codex CLI)
                       -- use the managed block, not the raw skill.
      - "system_prompt" Open-weights models have no skill runtime at all --
                       use the portable fallback prompt, which is the exact
                       thing this matrix slot exists to validate (§14.3).
    """

    slot: str
    provider: str
    model_id: str
    api_key_env: str
    skill_artifact: str
    base_url: str = ""


# Pinned per design doc §10.3 / §14.3. `model_id` for the "qwen" slot must be
# the exact string the chosen host (Together / Fireworks / OpenRouter) uses
# for Qwen3.6-27B -- confirm it against that host's model list before a run
# and record whatever you used in RESULTS.md, since the host-specific string
# is part of what makes the run reproducible.
MODEL_MATRIX = [
    ModelSpec(
        slot="claude",
        provider="anthropic",
        model_id="claude-opus-5",
        api_key_env="ANTHROPIC_API_KEY",
        skill_artifact="skill_md",
    ),
    ModelSpec(
        slot="gpt",
        provider="openai",
        model_id="gpt-5.1",
        api_key_env="OPENAI_API_KEY",
        skill_artifact="agent_block",
    ),
    ModelSpec(
        slot="qwen",
        provider="openai-compatible",
        model_id="qwen3.6-27b-instruct",
        api_key_env="OPENROUTER_API_KEY",
        skill_artifact="system_prompt",
        base_url="https://openrouter.ai/api/v1",
    ),
]


def _require_api_key(spec: ModelSpec) -> str:
    api_key = os.environ.get(spec.api_key_env)
    if not api_key:
        raise ModelCallError(
            f"{spec.slot}: set {spec.api_key_env} to call {spec.provider} "
            f"model {spec.model_id!r}"
        )
    return api_key


def _retry_delay_secs(attempt: int, retry_after: str | None) -> float:
    """Exponential backoff (4s, 8s, 16s ...), overridden upward by a
    server-supplied Retry-After when the 429/503 carried a parseable one."""
    backoff = RETRY_BACKOFF_SECS * (2 ** (attempt - 1))
    if retry_after:
        try:
            return max(backoff, float(retry_after))
        except ValueError:
            pass
    return backoff


def _read_response_once(request: urllib.request.Request, url: str) -> bytes:
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECS) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        if error.code in RETRYABLE_STATUS:
            raise _TransientCallError(
                f"HTTP {error.code} from {url}: {detail}",
                retry_after=error.headers.get("Retry-After"),
            ) from error
        raise ModelCallError(f"HTTP {error.code} from {url}: {detail}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        # A bare urlopen timeout raises TimeoutError, not a URLError, so both
        # are caught here; a DNS or connection-refused failure is a URLError.
        reason = getattr(error, "reason", error)
        raise _TransientCallError(f"could not reach {url}: {reason}") from error


def _post_json(url: str, headers: dict[str, str], payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")

    raw_body = b""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw_body = _read_response_once(request, url)
            break
        except _TransientCallError as error:
            if attempt == MAX_ATTEMPTS:
                raise ModelCallError(f"{error} (gave up after {MAX_ATTEMPTS} attempts)") from error
            time.sleep(_retry_delay_secs(attempt, error.retry_after))

    # A 200 status doesn't guarantee a well-formed body -- a proxy in front
    # of the real provider can return an HTML error page or a truncated
    # response while still setting a success status.
    try:
        return json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        detail = raw_body[:200].decode("utf-8", errors="replace")
        raise ModelCallError(f"unparseable response body from {url}: {detail!r}") from error

def call_anthropic(spec: ModelSpec, system: str, user: str, sampler: SamplerSettings) -> str:
    api_key = _require_api_key(spec)
    response = _post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        {
            "model": spec.model_id,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": sampler.max_tokens,
            "temperature": sampler.temperature,
            "top_p": sampler.top_p,
        },
    )
    _reject_if_truncated(spec.slot, response.get("stop_reason"), sampler)
    text = "".join(block.get("text", "") for block in response.get("content", []))
    if not text:
        raise ModelCallError(
            f"{spec.slot}: empty content from api.anthropic.com/v1/messages "
            f"(likely content-filtered or a stop_reason with no text): {response!r}"
        )
    return text


def _token_limit_field(provider: str) -> str:
    """OpenAI's own API rejects `max_tokens` on its current models and wants
    `max_completion_tokens`; the OpenAI-compatible hosts (OpenRouter,
    Together, Fireworks) that serve the open-weights slot still take the
    older `max_tokens`. Same Chat Completions wire format otherwise."""
    return "max_completion_tokens" if provider == "openai" else "max_tokens"


def call_openai_chat(spec: ModelSpec, system: str, user: str, sampler: SamplerSettings) -> str:
    """Chat Completions call, used for both OpenAI itself and any
    OpenAI-compatible hosted endpoint (OpenRouter, Together, Fireworks)."""
    api_key = _require_api_key(spec)
    base_url = spec.base_url or "https://api.openai.com/v1"
    response = _post_json(
        f"{base_url}/chat/completions",
        {"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
        {
            "model": spec.model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            _token_limit_field(spec.provider): sampler.max_tokens,
            "temperature": sampler.temperature,
            "top_p": sampler.top_p,
        },
    )
    try:
        choice = response["choices"][0]
        content = choice["message"]["content"]
    except (KeyError, IndexError) as error:
        raise ModelCallError(
            f"{spec.slot}: unexpected response shape from {base_url}/chat/completions "
            f"(no completion choices -- may be content-filtered): {response!r}"
        ) from error
    _reject_if_truncated(spec.slot, choice.get("finish_reason"), sampler)
    if content is None:
        raise ModelCallError(
            f"{spec.slot}: null message content from {base_url}/chat/completions "
            f"(likely content-filtered): {response!r}"
        )
    return content


def call_ollama(model_id: str, system: str, user: str, sampler: SamplerSettings) -> str:
    """Local Ollama call for the unpublished mini-prompt smoke test
    (design doc §14.3) -- no API key, no network beyond localhost."""
    response = _post_json(
        "http://localhost:11434/api/chat",
        {"content-type": "application/json"},
        {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {
                "temperature": sampler.temperature,
                "top_p": sampler.top_p,
                "num_predict": sampler.max_tokens,
            },
        },
    )
    try:
        content = response["message"]["content"]
    except KeyError as error:
        raise ModelCallError(
            f"ollama {model_id}: unexpected response shape: {response!r}"
        ) from error
    _reject_if_truncated(f"ollama {model_id}", response.get("done_reason"), sampler)
    if not content:
        raise ModelCallError(
            f"ollama {model_id}: empty content -- the model returned no text "
            f"(check `ollama pull {model_id}` succeeded and the prompt fits its "
            f"context window): {response!r}"
        )
    return content


PROVIDER_CALLERS = {
    "anthropic": call_anthropic,
    "openai": call_openai_chat,
    "openai-compatible": call_openai_chat,
}


def generate(
    spec: ModelSpec, system: str, user: str, sampler: SamplerSettings = DEFAULT_SAMPLER
) -> str:
    caller = PROVIDER_CALLERS.get(spec.provider)
    if caller is None:
        raise ModelCallError(f"{spec.slot}: unknown provider {spec.provider!r}")
    return caller(spec, system, user, sampler)
