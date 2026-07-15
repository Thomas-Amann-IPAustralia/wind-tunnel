"""The ``workflow_dispatch`` trigger (TECH_SPEC §5.7, §14).

``workflow_dispatch`` is fire-and-forget: the trigger call only needs to
succeed at the API level (HTTP 204), and the SPA learns the run actually
started by watching ``status.json`` advance, not by this call's return value
(§5.7). This module owns exactly that one call — trigger and return, never
wait — over stdlib ``urllib``, matching ``github_io.py`` and
``pipeline/llm.py``'s no-new-HTTP-dependency pattern.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Protocol

_API_ROOT = "https://api.github.com"
_DEFAULT_TIMEOUT_S = 15


class DispatchError(RuntimeError):
    """The dispatch call itself failed (bad token, unknown workflow file, GitHub
    API error). Distinct from anything about the *run* the workflow performs —
    this is purely "did the trigger succeed" (§5.7)."""


class Dispatcher(Protocol):
    def dispatch(self, workflow_file: str, *, ref: str, inputs: dict[str, str]) -> None: ...


@dataclass
class WorkflowDispatcher:
    """The real dispatcher: ``POST .../actions/workflows/{file}/dispatches``.
    Shares the fine-grained PAT with ``github_io.RestGitHubClient`` (CLAUDE.md
    §6 — the backend is the sole holder); read lazily so construction never
    fails on an unconfigured env (same rationale as ``llm.GeminiTransport``)."""

    owner: str
    repo: str
    token: str = field(default_factory=lambda: os.environ.get("WINDTUNNEL_PAT", ""))
    timeout_s: int = _DEFAULT_TIMEOUT_S

    def dispatch(self, workflow_file: str, *, ref: str, inputs: dict[str, str]) -> None:
        import urllib.error
        import urllib.request

        if not self.token:
            raise DispatchError(
                "WINDTUNNEL_PAT is not set — dispatching a governance run needs the "
                "fine-grained PAT (CLAUDE.md §6)."
            )
        url = f"{_API_ROOT}/repos/{self.owner}/{self.repo}/actions/workflows/{workflow_file}/dispatches"
        body = json.dumps({"ref": ref, "inputs": inputs}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                if resp.status != 204:
                    raise DispatchError(f"Unexpected dispatch status: HTTP {resp.status}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise DispatchError(
                f"Dispatch of {workflow_file!r} failed: HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise DispatchError(f"Dispatch of {workflow_file!r} failed: {exc.reason}") from exc


@dataclass
class FakeDispatcher:
    """Records calls for tests; never touches the network (TECH_SPEC §15)."""

    calls: list[dict] = field(default_factory=list)

    def dispatch(self, workflow_file: str, *, ref: str, inputs: dict[str, str]) -> None:
        self.calls.append({"workflow_file": workflow_file, "ref": ref, "inputs": inputs})
