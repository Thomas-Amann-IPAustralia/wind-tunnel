"""The LLM seam's failure-absorption layers (llm.py; TECH_SPEC §13, §15).

The first three live governance runs each died at this seam in a different way:
a malformed JSON answer mid-document (WT-H5M2-2Y), a valid object followed by
trailing text (WT-TR4C-DC), and a transient Gemini 503 (WT-PX5H-3D). These tests
pin the behaviours that make each recoverable — tolerant-but-lossless parsing,
the bounded corrective re-ask, and the transport's transient-HTTP retry — all
LLM-free (§15).
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pytest

from llm import (
    JSON_REASKS,
    CallBudget,
    GeminiTransport,
    LLMClient,
    LLMError,
    LLMTruncated,
    ScriptedTransport,
    _extract_text,
    _parse_json_object,
    resolve_model,
)

_ROLE = "threshold_generalist"
_MODEL = resolve_model(_ROLE)

_GOOD = json.dumps({"sections": {"1": "ok"}})
# The WT-H5M2-2Y shape: a syntax slip inside the document (missing comma).
_MALFORMED = '{\n  "sections": {\n    "1": "a"\n    "2": "b"\n  }\n}'


def _client(entry: object) -> LLMClient:
    return LLMClient(transport=ScriptedTransport(responses={_MODEL: entry}))


# -- tolerant, lossless parsing ------------------------------------------------


def test_parse_tolerates_trailing_text_after_object():
    # The WT-TR4C-DC failure: a complete object, then the model kept typing.
    text = _GOOD + "\n\nI hope this reconciliation is helpful!"
    assert _parse_json_object(text) == {"sections": {"1": "ok"}}


def test_parse_tolerates_prose_preamble():
    assert _parse_json_object("Here is the JSON:\n" + _GOOD) == {"sections": {"1": "ok"}}


def test_parse_tolerates_raw_control_characters_in_strings():
    # A raw newline inside a string — invalid strict JSON, unambiguous content.
    parsed = _parse_json_object('{"sections": {"1": "line one\nline two"}}')
    assert parsed == {"sections": {"1": "line one\nline two"}}


def test_parse_still_raises_on_genuinely_malformed_json():
    with pytest.raises(json.JSONDecodeError):
        _parse_json_object(_MALFORMED)


def test_complete_json_accepts_fenced_answer_unchanged():
    parsed, resp = _client(f"```json\n{_GOOD}\n```").complete_json(_ROLE, "s", "u")
    assert parsed == {"sections": {"1": "ok"}}
    assert resp.model == _MODEL


# -- the corrective re-ask loop ------------------------------------------------


def test_reasks_once_on_malformed_json_then_succeeds():
    transport = ScriptedTransport(responses={_MODEL: [_MALFORMED, _GOOD]})
    client = LLMClient(transport=transport)
    parsed, _ = client.complete_json(_ROLE, "sys", "the original ask")
    assert parsed == {"sections": {"1": "ok"}}
    assert client.budget.used == 2  # the re-ask is a real, budget-charged call
    retry_user = transport.seen[1]["user"]
    assert "the original ask" in retry_user  # full context is re-sent
    assert "## Output correction" in retry_user
    assert "was not valid JSON" in retry_user


def test_reasks_on_truncated_answer_with_concision_note():
    calls = {"n": 0}

    def handler(*, model, system, user, response_json):
        calls["n"] += 1
        if calls["n"] == 1:
            raise LLMTruncated("cut off at the output-token limit")
        return _GOOD

    client = LLMClient(transport=ScriptedTransport(handler=handler))
    parsed, _ = client.complete_json(_ROLE, "sys", "ask")
    assert parsed == {"sections": {"1": "ok"}}
    assert calls["n"] == 2


def test_raises_loudly_after_exhausting_reasks():
    attempts = 1 + JSON_REASKS
    transport = ScriptedTransport(responses={_MODEL: [_MALFORMED] * attempts})
    client = LLMClient(transport=transport)
    with pytest.raises(LLMError) as exc_info:
        client.complete_json(_ROLE, "sys", "ask")
    message = str(exc_info.value)
    assert f"after {attempts} attempts" in message
    assert _ROLE in message
    assert client.budget.used == attempts  # every attempt was charged


def test_reask_rejects_non_object_json_answers():
    transport = ScriptedTransport(responses={_MODEL: ['["a", "list"]'] * (1 + JSON_REASKS)})
    with pytest.raises(LLMError, match="did not return valid JSON"):
        LLMClient(transport=transport).complete_json(_ROLE, "sys", "ask")


def test_reasks_still_respect_the_run_budget():
    transport = ScriptedTransport(responses={_MODEL: [_MALFORMED] * 3})
    client = LLMClient(transport=transport, budget=CallBudget(max_calls=2))
    with pytest.raises(LLMError, match="budget exhausted"):
        client.complete_json(_ROLE, "sys", "ask")


# -- response extraction -------------------------------------------------------


def _payload(parts: list[dict], finish: str = "STOP") -> dict:
    return {"candidates": [{"content": {"parts": parts}, "finishReason": finish}]}


def test_extract_text_skips_thought_parts():
    payload = _payload([{"text": "thinking…", "thought": True}, {"text": _GOOD}])
    assert _extract_text(payload, _MODEL) == _GOOD


def test_extract_text_raises_truncated_on_max_tokens():
    with pytest.raises(LLMTruncated, match="output-token limit"):
        _extract_text(_payload([{"text": '{"sections": {"1": "cut'}], "MAX_TOKENS"), _MODEL)


def test_extract_text_still_raises_on_empty_answer():
    with pytest.raises(LLMError, match="empty answer"):
        _extract_text(_payload([{"text": "  "}], "SAFETY"), _MODEL)


# -- the live transport's transient-HTTP retry ---------------------------------


def _http_error(code: int, body: bytes = b"upstream detail") -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x", code, "err", None, io.BytesIO(body))


def _ok_response(text: str = _GOOD):
    class _Resp:
        def read(self):
            return json.dumps(
                {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]}
            ).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    return _Resp()


def _transport(**kwargs) -> tuple[GeminiTransport, list[float]]:
    slept: list[float] = []
    transport = GeminiTransport(api_key="k", sleep=slept.append, **kwargs)
    return transport, slept


def test_transport_retries_transient_503_then_succeeds(monkeypatch):
    # The WT-PX5H-3D failure: "high demand … try again later", fatal on attempt 1.
    outcomes = [_http_error(503), _http_error(503), _ok_response()]

    def fake_urlopen(req, timeout=None):
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    transport, slept = _transport(retry_delays_s=(0.01, 0.02))
    text = transport.generate(model=_MODEL, system="s", user="u", response_json=True)
    assert text == _GOOD
    assert slept == [0.01, 0.02]


def test_transport_does_not_retry_permanent_errors(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        raise _http_error(400, b"bad request")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    transport, slept = _transport()
    with pytest.raises(LLMError, match="HTTP 400"):
        transport.generate(model=_MODEL, system="s", user="u", response_json=False)
    assert calls["n"] == 1
    assert slept == []


def test_transport_gives_up_after_exhausting_retries(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        raise _http_error(503)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    transport, slept = _transport(retry_delays_s=(0.01, 0.02))
    with pytest.raises(LLMError, match=r"HTTP 503.*attempt 3/3"):
        transport.generate(model=_MODEL, system="s", user="u", response_json=True)
    assert calls["n"] == 3
    assert slept == [0.01, 0.02]


def test_transport_retries_network_blips(monkeypatch):
    outcomes: list[object] = [urllib.error.URLError("connection reset"), _ok_response()]

    def fake_urlopen(req, timeout=None):
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    transport, slept = _transport(retry_delays_s=(0.01,))
    text = transport.generate(model=_MODEL, system="s", user="u", response_json=True)
    assert text == _GOOD
    assert slept == [0.01]
