"""The commit helper — Contents/Git-Data API, serialise-per-run (TECH_SPEC §14).

Render's disk is ephemeral, so the backend never treats a working copy as
durable; every read and write goes through the GitHub HTTP API instead of
``git`` (CLAUDE.md §9). Two operations live here:

  * **Reads** (``get_file``) go through the Contents API with conditional
    ``If-None-Match`` support, because the status proxy (TECH_SPEC §7) needs a
    cheap ``304`` on steady-state polling rather than the CDN-cached
    ``raw.githubusercontent.com`` path.
  * **Writes** (``commit_files``) go through the Git Data API (tree + commit +
    ref update) so a run's multi-file skeleton or checkpoint lands as one
    atomic commit, not a sequence of partial Contents-API PUTs. A non-fast-
    forward ref update — another writer's commit landed first — is absorbed by
    re-reading the tip and retrying (§14); because every writer touches only
    its own disjoint ``runs/<run-id>/...`` path, the retry always succeeds.

Two independent kinds of failure are absorbed, at two layers — the same
belt-and-suspenders shape ``pipeline/llm.py`` uses for the Gemini seam:

  * **Transient upstream failure** — a 429/5xx or a network blip — is retried at
    the *transport* level (``_request``) with a short backoff. GitHub's Git Data
    API intermittently returns ``503 "No server is currently available to
    service your request"``; with no retry a single such blip anywhere in the
    tree→commit→ref sequence killed the whole commit (the reported bug). This
    covers reads too, so the status proxy's steady-state polling rides over a
    momentary GitHub hiccup instead of surfacing it to the SPA.
  * **Non-fast-forward** — a genuine write race on the ref — is retried at the
    *commit* level (``commit_files``), which re-reads the tip and rebuilds. It is
    a business-level conflict, not a transport failure, so it stays its own loop.

Following ``pipeline/llm.py``'s pattern: one injectable ``GitHubClient``
Protocol, a real implementation over stdlib ``urllib`` (no new HTTP-client
dependency), and an in-memory fake for tests — nothing above this module knows
which is in use.
"""

from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass, field
from typing import Literal, Protocol

_API_ROOT = "https://api.github.com"
_DEFAULT_TIMEOUT_S = 20

# Transient HTTP statuses the client retries (rate limit + GitHub server-side).
# The live ``503 "No server is currently available to service your request"``
# that killed a commit is exactly this class. Everything else is permanent here
# and returns to the caller unretried: 401/403 (bad token), 404 (missing file —
# a legitimate ``get_file`` outcome), and 409/422 (a non-fast-forward ref update,
# which has its own re-read-and-retry loop in ``commit_files``). Mirrors
# ``llm.RETRYABLE_HTTP`` so the two seams treat upstream failure identically.
RETRYABLE_HTTP = frozenset({429, 500, 502, 503, 504})


class GitHubError(RuntimeError):
    """Any failure in the commit helper: a missing token, an HTTP error, or a
    commit that could not land after retrying. Loud — a silent failure here
    would mean a checkpoint the SPA can never see (TECH_SPEC §7)."""


GetStatus = Literal["ok", "not_modified", "missing"]


@dataclass
class GetFileResult:
    """The outcome of one ``get_file`` call. ``content``/``sha`` are set only
    when ``status == "ok"``; ``etag`` is set whenever the file exists."""

    status: GetStatus
    content: bytes | None = None
    sha: str | None = None
    etag: str | None = None


class GitHubClient(Protocol):
    """The seam every endpoint depends on (§7, §14)."""

    def get_file(self, path: str, *, if_none_match: str | None = None) -> GetFileResult: ...

    def commit_files(self, files: dict[str, bytes], message: str) -> str: ...


@dataclass
class RestGitHubClient:
    """The real client: GitHub REST (Contents API reads, Git Data API writes)
    over stdlib ``urllib``. Holds the fine-grained PAT — the sole holder,
    alongside ``dispatch.py`` (CLAUDE.md §6); it never reaches the SPA.

    The token is read lazily (a field default, not a constructor requirement)
    so constructing a client at import time never fails even when the env is
    unconfigured — the same pattern ``llm.GeminiTransport`` uses; the loud
    error surfaces only when a call is actually made without one.

    Two retry knobs, one per failure kind: ``transient_retry_delays_s`` is the
    transport-level backoff for a 429/5xx/network blip (so ``1 + len`` attempts
    per HTTP call), ``commit_retries`` is the commit-level count for a
    non-fast-forward ref race. Both drive the injectable ``sleep``, so tests
    assert the backoff without waiting."""

    owner: str
    repo: str
    branch: str = "main"
    token: str = field(default_factory=lambda: os.environ.get("WINDTUNNEL_PAT", ""))
    timeout_s: int = _DEFAULT_TIMEOUT_S
    commit_retries: int = 4
    transient_retry_delays_s: tuple[float, ...] = (2.0, 5.0, 12.0)
    sleep: object = field(default=time.sleep)

    def get_file(self, path: str, *, if_none_match: str | None = None) -> GetFileResult:
        headers = self._headers()
        if if_none_match:
            headers["If-None-Match"] = if_none_match
        url = (
            f"{_API_ROOT}/repos/{self.owner}/{self.repo}/contents/{_quote(path)}?ref={self.branch}"
        )
        status, payload, resp_headers = self._request("GET", url, headers=headers)
        if status == 304:
            return GetFileResult(status="not_modified", etag=if_none_match)
        if status == 404:
            return GetFileResult(status="missing")
        if status != 200:
            raise GitHubError(f"GET {path} failed: HTTP {status}: {payload!r}")
        data = json.loads(payload)
        content = base64.b64decode(data["content"])
        return GetFileResult(
            status="ok",
            content=content,
            sha=data["sha"],
            etag=resp_headers.get("etag") or resp_headers.get("ETag"),
        )

    def commit_files(self, files: dict[str, bytes], message: str) -> str:
        if not self.token:
            raise GitHubError(
                "WINDTUNNEL_PAT is not set — the commit helper needs the fine-grained "
                "PAT to write to the repo (CLAUDE.md §6)."
            )
        delay = 1.0
        last_error: str | None = None
        for attempt in range(1, self.commit_retries + 1):
            try:
                return self._commit_once(files, message)
            except _NonFastForward as exc:
                last_error = str(exc)
                if attempt == self.commit_retries:
                    break
                self.sleep(delay)
                delay *= 2
        raise GitHubError(f"commit_files failed after {self.commit_retries} attempts: {last_error}")

    def _commit_once(self, files: dict[str, bytes], message: str) -> str:
        base = f"{_API_ROOT}/repos/{self.owner}/{self.repo}"
        ref_status, ref_payload, _ = self._request(
            "GET", f"{base}/git/refs/heads/{self.branch}", headers=self._headers()
        )
        if ref_status != 200:
            raise GitHubError(f"Could not read ref heads/{self.branch}: HTTP {ref_status}")
        base_sha = json.loads(ref_payload)["object"]["sha"]

        commit_status, commit_payload, _ = self._request(
            "GET", f"{base}/git/commits/{base_sha}", headers=self._headers()
        )
        if commit_status != 200:
            raise GitHubError(f"Could not read base commit {base_sha}: HTTP {commit_status}")
        base_tree_sha = json.loads(commit_payload)["tree"]["sha"]

        tree = [
            {"path": path, "mode": "100644", "type": "blob", "content": content.decode("utf-8")}
            for path, content in files.items()
        ]
        tree_status, tree_payload, _ = self._request(
            "POST",
            f"{base}/git/trees",
            headers=self._headers(),
            body={"base_tree": base_tree_sha, "tree": tree},
        )
        if tree_status not in (200, 201):
            raise GitHubError(f"Could not create tree: HTTP {tree_status}: {tree_payload!r}")
        new_tree_sha = json.loads(tree_payload)["sha"]

        commit_status, commit_payload, _ = self._request(
            "POST",
            f"{base}/git/commits",
            headers=self._headers(),
            body={"message": message, "tree": new_tree_sha, "parents": [base_sha]},
        )
        if commit_status not in (200, 201):
            raise GitHubError(f"Could not create commit: HTTP {commit_status}: {commit_payload!r}")
        new_commit_sha = json.loads(commit_payload)["sha"]

        patch_status, patch_payload, _ = self._request(
            "PATCH",
            f"{base}/git/refs/heads/{self.branch}",
            headers=self._headers(),
            body={"sha": new_commit_sha, "force": False},
        )
        if patch_status in (422, 409):
            raise _NonFastForward(f"HTTP {patch_status}: {patch_payload!r}")
        if patch_status != 200:
            raise GitHubError(f"Could not update ref: HTTP {patch_status}: {patch_payload!r}")
        return new_commit_sha

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(
        self, method: str, url: str, *, headers: dict[str, str], body: dict | None = None
    ) -> tuple[int, bytes, dict[str, str]]:
        """One HTTP call, retrying transient upstream failure (429/5xx, a network
        blip, a timeout) with a short backoff before giving up loudly — the
        hardening the live ``503 "No server is currently available"`` needed.
        Permanent statuses (a 2xx/3xx success, or a 4xx the caller must branch on
        such as 404-missing or 422-non-fast-forward) return unretried."""
        attempts = 1 + len(self.transient_retry_delays_s)
        last: _TransientHTTP | None = None
        for attempt in range(attempts):
            try:
                return self._request_once(method, url, headers=headers, body=body)
            except _TransientHTTP as exc:
                last = exc
                if attempt < attempts - 1:
                    self.sleep(self.transient_retry_delays_s[attempt])
        assert last is not None  # the loop only leaves early via a successful return
        raise GitHubError(
            f"{method} {url} failed after {attempts} attempts: {last}"
        ) from last.__cause__

    def _request_once(
        self, method: str, url: str, *, headers: dict[str, str], body: dict | None = None
    ) -> tuple[int, bytes, dict[str, str]]:
        """The raw call. Raises ``_TransientHTTP`` on a retryable status or a
        network error (for ``_request`` to absorb); returns any other status to
        the caller. Retrying a POST (create tree/commit) is safe — git objects are
        content-addressed, so a repeat yields the same tree sha or an unreferenced
        orphan commit; retrying the ref PATCH re-sends the same target sha, which
        GitHub treats as a no-op when the ref already moved there."""
        import urllib.error
        import urllib.request

        data = json.dumps(body).encode("utf-8") if body is not None else None
        if data is not None:
            headers = {**headers, "Content-Type": "application/json"}
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return resp.status, resp.read(), dict(resp.headers)
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            if exc.code in RETRYABLE_HTTP:
                raise _TransientHTTP(
                    f"{method} {url} → HTTP {exc.code}: {payload[:200]!r}"
                ) from exc
            return exc.code, payload, dict(exc.headers or {})
        except (urllib.error.URLError, TimeoutError) as exc:
            reason = getattr(exc, "reason", exc)
            raise _TransientHTTP(f"{method} {url} failed: {reason}") from exc


class _NonFastForward(RuntimeError):
    """Internal: the ref update lost a race. Caught by ``commit_files``' retry
    loop — never escapes this module."""


class _TransientHTTP(RuntimeError):
    """Internal: a retryable transport failure — a 429/5xx or a network blip.
    Caught by ``_request``'s retry loop; on exhaustion it becomes a loud
    ``GitHubError``. Never escapes this module (cf. ``llm._TransientHTTP``)."""


def _quote(path: str) -> str:
    from urllib.parse import quote

    return quote(path, safe="/")


# -- test double -----------------------------------------------------------


@dataclass
class FakeGitHubClient:
    """An in-memory stand-in for tests: no network, no git. Mirrors the real
    client's contract (missing/not_modified/ok, atomic multi-file commits)
    closely enough that endpoint tests exercise real request/response shapes."""

    files: dict[str, bytes] = field(default_factory=dict)
    commits: list[dict] = field(default_factory=list)

    def get_file(self, path: str, *, if_none_match: str | None = None) -> GetFileResult:
        if path not in self.files:
            return GetFileResult(status="missing")
        content = self.files[path]
        sha = _fake_sha(content)
        if if_none_match is not None and if_none_match == sha:
            return GetFileResult(status="not_modified", sha=sha, etag=sha)
        return GetFileResult(status="ok", content=content, sha=sha, etag=sha)

    def commit_files(self, files: dict[str, bytes], message: str) -> str:
        self.files.update(files)
        sha = f"fake{len(self.commits) + 1:04d}"
        self.commits.append({"sha": sha, "message": message, "paths": sorted(files)})
        return sha


def _fake_sha(content: bytes) -> str:
    import hashlib

    return hashlib.sha1(content).hexdigest()  # noqa: S324 — a fake content fingerprint, not crypto
