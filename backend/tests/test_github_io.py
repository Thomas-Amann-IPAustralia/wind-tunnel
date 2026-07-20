"""The commit helper's failure absorption (github_io.py; TECH_SPEC §14, §15).

A live governance commit died on a GitHub Git Data API ``503 "No server is
currently available to service your request"`` raised while creating the tree,
with no retry to ride over it. These tests pin the two independent layers that
now make such a blip survivable — the transport-level transient retry
(429/5xx, a network blip) and the commit-level non-fast-forward retry — all
without network or git (§15), mirroring ``pipeline/tests/test_llm.py``'s
transport tests.
"""

from __future__ import annotations

import base64
import io
import json
import urllib.error
import urllib.request

import pytest

from github_io import GitHubError, RestGitHubClient

_URL = "https://api.github.com/x"


def _client(**kwargs) -> tuple[RestGitHubClient, list[float]]:
    """A real client with a fast, recorded backoff so tests assert delays without
    waiting. The token is set so ``commit_files`` does not short-circuit."""
    slept: list[float] = []
    client = RestGitHubClient(
        owner="o",
        repo="r",
        token="t",
        sleep=slept.append,
        transient_retry_delays_s=(0.01, 0.02),
        **kwargs,
    )
    return client, slept


def _http_error(code: int, body: bytes = b'{"message": "upstream"}') -> urllib.error.HTTPError:
    return urllib.error.HTTPError(_URL, code, "err", None, io.BytesIO(body))


class _Resp:
    """A minimal urlopen return value: a context manager exposing status/read/headers."""

    def __init__(self, status: int = 200, body: bytes = b"{}", headers: dict | None = None):
        self.status = status
        self._body = body
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *args) -> bool:
        return False


def _drive(monkeypatch, outcomes: list) -> dict:
    """Point ``urlopen`` at a FIFO of outcomes (each an exception to raise or a
    ``_Resp`` to return) and record how many times it was called."""
    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return calls


# -- the transport layer's transient retry (_request) --------------------------


def test_request_retries_transient_503_then_succeeds(monkeypatch):
    # The reported failure: GitHub's "No server is currently available" 503.
    calls = _drive(monkeypatch, [_http_error(503), _http_error(503), _Resp(200, b'{"ok": 1}')])
    client, slept = _client()
    status, payload, _headers = client._request("GET", _URL, headers={})
    assert status == 200
    assert json.loads(payload) == {"ok": 1}
    assert calls["n"] == 3  # two failures ridden over, third succeeded
    assert slept == [0.01, 0.02]


def test_request_retries_network_blip_then_succeeds(monkeypatch):
    calls = _drive(monkeypatch, [urllib.error.URLError("connection reset"), _Resp(200)])
    client, slept = _client()
    status, _payload, _headers = client._request("POST", _URL, headers={}, body={"x": 1})
    assert status == 200
    assert calls["n"] == 2
    assert slept == [0.01]


def test_request_does_not_retry_permanent_404(monkeypatch):
    # 404 is a legitimate get_file "missing" — it must return, not retry or raise.
    calls = _drive(monkeypatch, [_http_error(404, b'{"message": "Not Found"}')])
    client, slept = _client()
    status, _payload, _headers = client._request("GET", _URL, headers={})
    assert status == 404
    assert calls["n"] == 1
    assert slept == []


def test_request_does_not_retry_non_fast_forward_422(monkeypatch):
    # 422 on the ref PATCH is a non-fast-forward — returned so _commit_once can
    # raise _NonFastForward; retrying it at the transport layer would be wrong.
    calls = _drive(monkeypatch, [_http_error(422, b'{"message": "not fast forward"}')])
    client, slept = _client()
    status, _payload, _headers = client._request("PATCH", _URL, headers={})
    assert status == 422
    assert calls["n"] == 1
    assert slept == []


def test_request_gives_up_loudly_after_exhausting_retries(monkeypatch):
    calls = _drive(monkeypatch, [_http_error(503) for _ in range(3)])
    client, slept = _client()
    with pytest.raises(GitHubError, match="after 3 attempts"):
        client._request("POST", _URL, headers={})
    assert calls["n"] == 3
    assert slept == [0.01, 0.02]


def test_get_file_retries_transient_500(monkeypatch):
    # Reads are covered too: the status proxy's polling rides over a momentary
    # GitHub 5xx instead of surfacing it to the SPA.
    content = base64.b64encode(b"hello").decode()
    body = json.dumps({"content": content, "sha": "abc"}).encode("utf-8")
    calls = _drive(monkeypatch, [_http_error(500), _Resp(200, body, {"ETag": '"e1"'})])
    client, slept = _client()
    result = client.get_file("runs/WT-X/status.json")
    assert result.status == "ok"
    assert result.content == b"hello"
    assert result.etag == '"e1"'
    assert calls["n"] == 2
    assert slept == [0.01]


# -- the commit layer, end to end ----------------------------------------------


class _FakeGitHubAPI:
    """Serves the Git Data API sequence ``commit_files`` drives — read ref, read
    base commit, create tree, create commit, update ref — and can inject a queue
    of exceptions per ``(method, url-fragment)`` before the normal response, so a
    test can fail one specific endpoint transiently or permanently."""

    def __init__(self) -> None:
        self.head = "basecommit"
        self.base_tree = "basetree"
        self._n = 0
        self.calls: list[tuple[str, str]] = []
        self.inject: dict[tuple[str, str], list] = {}

    def __call__(self, req, timeout=None) -> _Resp:
        method = req.get_method()
        url = req.full_url
        self.calls.append((method, url))
        for (m, fragment), queue in self.inject.items():
            if m == method and fragment in url and queue:
                raise queue.pop(0)
        return self._serve(method, url)

    def _serve(self, method: str, url: str) -> _Resp:
        if method == "GET" and "/git/refs/heads/" in url:
            return _Resp(200, json.dumps({"object": {"sha": self.head}}).encode("utf-8"))
        if method == "GET" and "/git/commits/" in url:
            return _Resp(200, json.dumps({"tree": {"sha": self.base_tree}}).encode("utf-8"))
        if method == "POST" and url.endswith("/git/trees"):
            self._n += 1
            return _Resp(201, json.dumps({"sha": f"newtree{self._n}"}).encode("utf-8"))
        if method == "POST" and url.endswith("/git/commits"):
            return _Resp(201, json.dumps({"sha": f"newcommit{self._n}"}).encode("utf-8"))
        if method == "PATCH" and "/git/refs/heads/" in url:
            self.head = f"newcommit{self._n}"
            return _Resp(200, b"{}")
        raise AssertionError(f"unexpected request {method} {url}")


def _commit_client(api: _FakeGitHubAPI, monkeypatch) -> tuple[RestGitHubClient, list[float]]:
    monkeypatch.setattr(urllib.request, "urlopen", api)
    return _client()


def _tree_posts(api: _FakeGitHubAPI) -> list[tuple[str, str]]:
    return [c for c in api.calls if c[0] == "POST" and c[1].endswith("/git/trees")]


def test_commit_files_survives_transient_tree_503(monkeypatch):
    # The reported bug, end to end: a 503 while creating the tree no longer kills
    # the commit — the transport retries and the whole sequence completes.
    api = _FakeGitHubAPI()
    api.inject[("POST", "/git/trees")] = [_http_error(503), _http_error(503)]
    client, slept = _commit_client(api, monkeypatch)
    sha = client.commit_files({"runs/WT-X/run.json": b"{}"}, "checkpoint")
    assert sha == "newcommit1"
    assert len(_tree_posts(api)) == 3  # two transient failures + one success
    assert slept == [0.01, 0.02]


def test_commit_files_still_raises_loudly_on_permanent_tree_error(monkeypatch):
    # A non-retryable tree error (422 validation) still fails loudly and fast —
    # the existing "Could not create tree" guard is unchanged for permanent errors.
    api = _FakeGitHubAPI()
    api.inject[("POST", "/git/trees")] = [_http_error(422, b'{"message": "bad tree"}')]
    client, slept = _commit_client(api, monkeypatch)
    with pytest.raises(GitHubError, match="Could not create tree: HTTP 422"):
        client.commit_files({"runs/WT-X/run.json": b"{}"}, "checkpoint")
    assert slept == []  # permanent — no backoff, no retry


def test_commit_files_retries_non_fast_forward_ref_race(monkeypatch):
    # The other retry layer still works: a 422 on the ref PATCH is a non-fast-
    # forward; commit_files re-reads the tip and retries the whole commit.
    api = _FakeGitHubAPI()
    api.inject[("PATCH", "/git/refs/heads/")] = [
        _http_error(422, b'{"message": "not fast forward"}')
    ]
    client, slept = _commit_client(api, monkeypatch)
    sha = client.commit_files({"runs/WT-X/run.json": b"{}"}, "checkpoint")
    assert sha == "newcommit2"  # succeeded on the second _commit_once
    ref_gets = [c for c in api.calls if c[0] == "GET" and "/git/refs/heads/" in c[1]]
    assert len(ref_gets) == 2  # the tip was re-read for the retry
    assert slept == [1.0]  # the non-fast-forward backoff, not the transient one
