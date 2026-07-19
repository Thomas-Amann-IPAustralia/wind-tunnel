"""The LLM seam — role→model resolution, a mockable transport, and a call budget.

Every governance agent talks to Gemini through one narrow interface so the whole
pipeline is testable without a live key: the *transport* is injectable. Tests pass
a :class:`ScriptedTransport` (canned responses); Actions passes
:class:`GeminiTransport` (the live REST call). Nothing above this module knows
which is in use.

Three responsibilities live here and nowhere else:

  1. **Role → model id.** Resolved from ``config/models.yml`` (the one owner of that
     fact, CLAUDE.md §6), never hardcoded in an agent.
  2. **The call budget.** ``config/budgets.yml`` sets a hard per-run ceiling
     (``run_max_calls``); a runaway agent trips the guard rather than silently
     burning tokens (TECH_SPEC §13).
  3. **JSON discipline.** Governance agents emit structured JSON (consequence +
     likelihood + rationale — never a rating, §10). ``complete_json`` asks the
     transport for ``application/json`` and parses loudly: a non-JSON answer is an
     :class:`LLMError`, not a silent empty dict.

**Transient failure is the norm, not the exception**, and the seam absorbs it in
two bounded layers — the first three live governance runs each died here, in three
different ways (a 503 "high demand", a malformed JSON answer, a valid answer with
trailing text), every one recoverable:

  * :class:`GeminiTransport` retries transient HTTP errors (429/5xx, network
    blips, timeouts) with a short backoff. Permanent errors (bad key, bad
    request) still fail immediately.
  * ``complete_json`` first parses tolerantly-but-losslessly (a code fence, a
    prose preamble, trailing text after the object, a raw control character in a
    string — none of these changes the content the model produced), and when the
    answer is genuinely malformed it **re-asks the model** with a corrective note,
    up to ``JSON_REASKS`` times, each attempt charged to the run budget. Content
    is never guessed or repaired — a re-ask is a fresh model answer. Only after
    the re-asks are exhausted does the loud :class:`LLMError` propagate.

This module never assembles a prompt or wraps untrusted content — that is the
agent layer's job (``agents/prompting.py``, TECH_SPEC §9.2). It only carries a
finished (system, user) pair to a model and returns the text back.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable, Protocol

# Live-call defaults (overridable per call). Low temperature keeps governance
# drafting reproducible enough to audit; it is not a determinism guarantee.
_DEFAULT_TIMEOUT_S = 120
_GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# How many times complete_json re-asks the model after a malformed JSON answer
# (so 1 + JSON_REASKS total attempts). Each re-ask is a real, budget-charged call.
JSON_REASKS = 2

# Transient HTTP statuses the live transport retries (rate limit + server side).
# Anything else — 400 bad request, 401/403 bad key, 404 bad model — is permanent
# and fails immediately.
RETRYABLE_HTTP = frozenset({429, 500, 502, 503, 504})


class LLMError(RuntimeError):
    """Any failure in the LLM seam: an unknown role, an exhausted budget, a
    transport/HTTP error, or an unparseable JSON answer. A loud failure — the
    pipeline's top level (run.py §5.6) turns it into a calm, resumable run
    failure rather than a silent wrong result."""


class LLMTruncated(LLMError):
    """The model's answer was cut off at the output-token limit
    (``finishReason=MAX_TOKENS``). Distinct from :class:`LLMError` because a
    truncated answer *looks* like malformed JSON but has a different cause and a
    different fix — ``complete_json`` re-asks once more (a fresh roll may come in
    shorter), and the final error names the real cause instead of a bewildering
    parse position."""


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "config" / "models.yml").is_file():
            return parent
    raise LLMError(f"Could not locate the repo root (with config/models.yml) above {here}.")


@lru_cache(maxsize=1)
def _model_roles() -> dict[str, str]:
    """The role→model-id map from config/models.yml (TECH_SPEC §13)."""
    import yaml

    with (_repo_root() / "config" / "models.yml").open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    roles = data.get("roles")
    if not isinstance(roles, dict) or not roles:
        raise LLMError("config/models.yml has no non-empty 'roles' map.")
    return {str(k): str(v) for k, v in roles.items()}


def resolve_model(role: str) -> str:
    """The Gemini model id for a role (e.g. ``threshold_reconciler`` → the pro id).

    Raises on an unknown role rather than guessing a model — a typo in a role name
    must not silently route to the wrong tier."""
    roles = _model_roles()
    if role not in roles:
        raise LLMError(f"Unknown model role: {role!r}. Known roles: {sorted(roles)}.")
    return roles[role]


@lru_cache(maxsize=1)
def _run_max_calls() -> int:
    """The hard per-run call ceiling from config/budgets.yml (TECH_SPEC §13)."""
    import yaml

    with (_repo_root() / "config" / "budgets.yml").open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return int(data.get("run_max_calls", 0)) or 10_000


@dataclass
class LLMResponse:
    """One model turn's result: the raw text, plus provenance the caller records
    (which role/model produced it — TECH_SPEC §13)."""

    text: str
    role: str
    model: str


class Transport(Protocol):
    """The one seam every agent depends on. ``generate`` takes a finished system +
    user prompt and returns the model's raw text. ``response_json`` asks the model
    to answer as JSON (Gemini ``responseMimeType``); an implementation that cannot
    enforce it must still return text the caller will try to parse."""

    def generate(self, *, model: str, system: str, user: str, response_json: bool) -> str: ...


@dataclass
class CallBudget:
    """Counts model calls against the per-run ceiling (TECH_SPEC §13). Shared across
    every agent in a run so the whole run — not each stage — is bounded.

    Charging is atomic: the §5.4 fan-out has several specialists drafting on worker
    threads against this one budget, so the check-and-increment must not race — a
    torn pair could admit calls past the ceiling the guard exists to enforce."""

    max_calls: int = field(default_factory=_run_max_calls)
    used: int = 0
    _lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False, init=False
    )

    def charge(self) -> None:
        with self._lock:
            if self.used >= self.max_calls:
                raise LLMError(
                    f"Run call budget exhausted ({self.used}/{self.max_calls}, "
                    "config/budgets.yml run_max_calls). Refusing further LLM calls (§13)."
                )
            self.used += 1


@dataclass
class LLMClient:
    """The agent-facing client. Resolves the role's model, charges the budget, and
    delegates the actual call to the injected transport. Records every call for
    run provenance (role, model — TECH_SPEC §13)."""

    transport: Transport
    budget: CallBudget = field(default_factory=CallBudget)
    calls: list[dict] = field(default_factory=list)

    def complete_text(self, role: str, system: str, user: str) -> LLMResponse:
        """A free-text completion (no JSON contract)."""
        return self._call(role, system, user, response_json=False)

    def complete_json(self, role: str, system: str, user: str) -> tuple[dict, LLMResponse]:
        """A structured completion. Returns ``(parsed_dict, response)``.

        The answer is parsed tolerantly but losslessly (:func:`_parse_json_object`);
        a genuinely malformed or truncated answer triggers up to ``JSON_REASKS``
        corrective re-asks — a fresh model answer each time, charged to the budget,
        never a content repair. If every attempt fails, raises :class:`LLMError`:
        governance agents have a strict output schema and a persistently malformed
        answer must fail loudly (TECH_SPEC §9.3), never degrade to an empty result."""
        problem: str | None = None
        last_error: Exception | None = None
        last_text = ""
        model = resolve_model(role)
        attempts = 1 + JSON_REASKS
        for attempt in range(attempts):
            ask = user if problem is None else f"{user}\n\n{_corrective_note(problem)}"
            try:
                resp = self._call(role, system, ask, response_json=True)
            except LLMTruncated as exc:
                # Truncation reads as malformed JSON downstream; re-ask for a
                # tighter answer rather than failing on the first cut-off roll.
                problem = (
                    "your previous answer was cut off at the output-token limit — "
                    "answer again more concisely so the whole JSON object fits"
                )
                last_error, last_text = exc, ""
                continue
            try:
                parsed = _parse_json_object(resp.text)
            except json.JSONDecodeError as exc:
                problem = f"your previous answer was not valid JSON (parser: {exc})"
                last_error, last_text = exc, resp.text
                continue
            if not isinstance(parsed, dict):
                problem = (
                    "your previous answer was a JSON "
                    f"{type(parsed).__name__}, not the required single JSON object"
                )
                last_error, last_text = None, resp.text
                continue
            return parsed, resp
        detail = f" First 200 chars: {last_text[:200]!r}" if last_text else ""
        raise LLMError(
            f"{role!r} ({model}) did not return valid JSON after {attempts} attempts: "
            f"{last_error or problem}.{detail}"
        ) from last_error

    def _call(self, role: str, system: str, user: str, *, response_json: bool) -> LLMResponse:
        model = resolve_model(role)
        self.budget.charge()
        text = self.transport.generate(
            model=model, system=system, user=user, response_json=response_json
        )
        # list.append of a fresh dict is atomic under the GIL — safe for the §5.4
        # fan-out, where concurrent specialists share this client's provenance list.
        self.calls.append({"role": role, "model": model})
        return LLMResponse(text=text, role=role, model=model)


def _strip_code_fence(text: str) -> str:
    """Tolerate a ```json … ``` fence around an otherwise-valid JSON answer — some
    models wrap JSON even when asked not to. Purely defensive trimming; the parse
    still fails loudly if what is inside is not JSON."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1] if "\n" in stripped else stripped[3:]
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]
    return stripped.strip()


def _parse_json_object(text: str) -> object:
    """Parse the JSON value out of a model answer, tolerating only what does not
    change the content the model produced:

      * a ```json``` fence around the answer (``_strip_code_fence``);
      * a prose preamble before the object ("Here is the JSON: {…}");
      * trailing text after a complete object — the live failure of run WT-TR4C-DC,
        whose reconciler emitted a valid object then kept typing ("Extra data");
      * a raw newline/tab inside a string (``strict=False``) — the character the
        model plainly intended, which the strict parser rejects.

    Anything else — the mid-document syntax slip of run WT-H5M2-2Y, a truncated
    document — raises ``json.JSONDecodeError`` for the caller's re-ask loop.
    Nothing is ever inserted, deleted, or guessed."""
    stripped = _strip_code_fence(text)
    start = stripped.find("{")
    if start == -1:
        # No object anywhere: parse from 0 purely to raise the standard error.
        return json.loads(stripped, strict=False)
    value, _end = json.JSONDecoder(strict=False).raw_decode(stripped, start)
    return value


def _corrective_note(problem: str) -> str:
    """The trusted re-ask suffix appended to the user prompt after a bad answer."""
    return (
        "## Output correction\n"
        f"Note: {problem}. Reply again, in full, with your complete answer as ONE "
        "valid JSON object and nothing else — no prose before or after it, no code "
        'fence, every string value correctly JSON-escaped (\\" for a double quote, '
        "\\n for a newline) and a comma between every pair of entries."
    )


# -- transports ----------------------------------------------------------------


@dataclass
class ScriptedTransport:
    """A test/offline transport. Either a mapping ``role → response text`` (or a
    list of texts consumed in order per role) or a callable
    ``(model, system, user, response_json) → text``. Lets the whole governance
    path run deterministically with no key (TECH_SPEC §15 — the pipeline is
    unit-tested LLM-free)."""

    responses: dict[str, object] | None = None
    handler: object | None = None
    seen: list[dict] = field(default_factory=list)

    def generate(self, *, model: str, system: str, user: str, response_json: bool) -> str:
        self.seen.append({"model": model, "system": system, "user": user})
        if self.handler is not None:
            return self.handler(model=model, system=system, user=user, response_json=response_json)
        if self.responses is None:
            raise LLMError("ScriptedTransport has neither a handler nor a responses map.")
        # Roles are not passed to the transport, so scripted responses key on model
        # id (or a queue keyed by model). Callers that need role-keyed scripting use
        # a handler. Default: single response per model, or FIFO if a list is given.
        entry = self.responses.get(model)
        if entry is None:
            raise LLMError(f"ScriptedTransport has no response for model {model!r}.")
        if isinstance(entry, list):
            if not entry:
                raise LLMError(f"ScriptedTransport queue for model {model!r} is empty.")
            return entry.pop(0)
        return str(entry)


@dataclass
class GeminiTransport:
    """The live transport: Google Generative Language ``:generateContent`` over
    stdlib urllib (no extra dependency, TECH_SPEC §13). Holds the key — which only
    ever exists in the backend/Actions env, never the SPA (CLAUDE.md §6). This path
    is exercised only in Actions with a real key, not in unit tests.

    The ``generateContent`` request shape is stable and independent of the specific
    Gemini model id (Tom pins the ids in config/models.yml), so this stays correct
    as the tier ids change.

    Transient upstream failure — a 429/5xx (run WT-PX5H-3D died on a 503 "high
    demand" with no retry), a network blip, a timeout — is retried with a short
    backoff (``retry_delays_s``). Permanent errors fail immediately."""

    api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    timeout_s: int = _DEFAULT_TIMEOUT_S
    temperature: float = 0.2
    retry_delays_s: tuple[float, ...] = (2.0, 5.0, 12.0)
    sleep: Callable[[float], None] = field(default=time.sleep, repr=False)

    def generate(self, *, model: str, system: str, user: str, response_json: bool) -> str:
        if not self.api_key:
            raise LLMError("GEMINI_API_KEY is not set — the live transport needs the key (§6).")
        attempts = 1 + len(self.retry_delays_s)
        last: LLMError | None = None
        for attempt in range(attempts):
            try:
                return self._request_once(
                    model=model, system=system, user=user, response_json=response_json
                )
            except _TransientHTTP as exc:
                last = LLMError(f"{exc} (attempt {attempt + 1}/{attempts})")
                last.__cause__ = exc.__cause__
                if attempt < attempts - 1:
                    self.sleep(self.retry_delays_s[attempt])
        assert last is not None
        raise last

    def _request_once(self, *, model: str, system: str, user: str, response_json: bool) -> str:
        import urllib.error
        import urllib.request

        gen_config: dict = {"temperature": self.temperature}
        if response_json:
            gen_config["responseMimeType"] = "application/json"
        body = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": gen_config,
            }
        ).encode("utf-8")
        url = _GEMINI_ENDPOINT.format(model=model)
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            message = f"Gemini HTTP {exc.code} for model {model!r}: {detail}"
            if exc.code in RETRYABLE_HTTP:
                raise _TransientHTTP(message) from exc
            raise LLMError(message) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            reason = getattr(exc, "reason", exc)
            raise _TransientHTTP(f"Gemini request failed for model {model!r}: {reason}") from exc
        return _extract_text(payload, model)


class _TransientHTTP(RuntimeError):
    """Internal marker for a retryable transport failure (never leaves the seam)."""


def _extract_text(payload: dict, model: str) -> str:
    """Pull the answer text out of a generateContent response, failing loudly on a
    blocked/empty candidate (a safety block must not read as an empty draft).

    Parts flagged ``thought`` (a thinking model's summary, when the API returns
    one) are excluded — concatenating a thought into a JSON answer manufactures
    exactly the trailing-garbage parse failures the seam exists to prevent. A
    ``MAX_TOKENS`` finish is raised as :class:`LLMTruncated` so the cause is named
    instead of surfacing as a baffling parse error deep inside the cut-off JSON."""
    candidates = payload.get("candidates")
    if not candidates:
        feedback = payload.get("promptFeedback")
        raise LLMError(f"Gemini returned no candidates for {model!r} (promptFeedback={feedback}).")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    reason = candidates[0].get("finishReason")
    if not text.strip():
        raise LLMError(f"Gemini returned an empty answer for {model!r} (finishReason={reason}).")
    if reason == "MAX_TOKENS":
        raise LLMTruncated(
            f"Gemini's answer for {model!r} was cut off at the output-token limit "
            f"(finishReason=MAX_TOKENS, {len(text)} chars received)."
        )
    return text
