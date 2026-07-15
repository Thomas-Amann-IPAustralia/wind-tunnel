"""Backend settings — the one place deployment identity lives (CLAUDE.md §6).

The repo owner/name, default branch, and CORS origins the SPA is served from
are facts a JS/TS frontend cannot import from Python, so this is the *Python*
owner of them (CLAUDE.md §6: "belongs in a committed frontend/ config ... and a
pipeline constant, not hardcoded across files"). When ``frontend/config.ts``
lands it mirrors the values below by hand; this module stays the source of
truth to copy from. Nothing here is secret — secrets (``GEMINI_API_KEY``,
``WINDTUNNEL_PAT``) are read from the environment only where used
(``github_io.py``, ``dispatch.py``), never stored on a Settings instance, so
they are never accidentally logged or serialised.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# The GitHub repo this deployment commits run state to and dispatches
# governance runs against (TECH_SPEC §1, §14).
_DEFAULT_OWNER = "Thomas-Amann-IPAustralia"
_DEFAULT_REPO = "wind-tunnel"
_DEFAULT_BRANCH = "main"

# The GitHub Pages project-site origin the SPA is served from (CLAUDE.md §9:
# "path-aware... served from /<repo>/"). Origins carry no path, so this is just
# the Pages host. Local dev origins are included so `vite dev` works against a
# locally run backend without extra config.
_DEFAULT_CORS_ORIGINS = (
    f"https://{_DEFAULT_OWNER.lower()}.github.io",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

GOVERNANCE_WORKFLOW = "governance.yml"
GITHUB_TOKEN_ENV = "WINDTUNNEL_PAT"  # noqa: S105 — an env var *name*, not a secret


@dataclass(frozen=True)
class Settings:
    github_owner: str = _DEFAULT_OWNER
    github_repo: str = _DEFAULT_REPO
    github_branch: str = _DEFAULT_BRANCH
    governance_workflow: str = GOVERNANCE_WORKFLOW
    cors_origins: tuple[str, ...] = field(default_factory=lambda: _DEFAULT_CORS_ORIGINS)


def load_settings() -> Settings:
    """Settings from the environment, falling back to the pinned defaults above.
    Overrides exist for local dev / a fork's own Render deployment, not for
    day-to-day operation — the defaults are correct for this project."""
    cors_raw = os.environ.get("WINDTUNNEL_CORS_ORIGINS")
    cors = (
        tuple(o.strip() for o in cors_raw.split(",") if o.strip())
        if cors_raw
        else _DEFAULT_CORS_ORIGINS
    )
    return Settings(
        github_owner=os.environ.get("WINDTUNNEL_GITHUB_OWNER", _DEFAULT_OWNER),
        github_repo=os.environ.get("WINDTUNNEL_GITHUB_REPO", _DEFAULT_REPO),
        github_branch=os.environ.get("WINDTUNNEL_GITHUB_BRANCH", _DEFAULT_BRANCH),
        cors_origins=cors,
    )
