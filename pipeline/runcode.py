"""Run codes — the run id *is* the run code (TECH_SPEC §3).

A run code like ``WT-7K3D-Q2`` normalises directly to the directory
``runs/WT-7K3D-Q2/``: resume is a path lookup and the public audit trail stays
human-navigable. There is no separate UUID.

The alphabet, format and normalisation live HERE — this module is the single
Python owner of the run-code fact (CLAUDE.md §6; the frontend keeps the one
unavoidable second copy, in TypeScript, because it validates the resume input
client-side). Nothing here does I/O: collision handling (§3) is expressed as a
pure helper that takes an existence predicate, so the backend can plug its
GitHub Contents API check in without this module ever importing it.

Codes are *locators, not secrets* (§3): the whole repo is world-readable, so a
code only needs to be unique and legible, never unguessable.
"""

from __future__ import annotations

import re
import secrets
from collections.abc import Callable

# 29 unambiguous symbols (design §7.5 / TECH_SPEC §3). Deliberately excluded:
# letters I L O U V and digits 0 1 — the pairs that get misread aloud or in print.
ALPHABET = "ABCDEFGHJKMNPQRSTWXYZ23456789"

PREFIX = "WT"
_GROUP1_LEN = 4
_GROUP2_LEN = 2

# ^WT-XXXX-XX over the alphabet. Anchored; uppercase only (codes are stored and
# displayed uppercase, §3). Callers normalise() before matching user input.
RUN_CODE_RE = re.compile(rf"^{PREFIX}-[{ALPHABET}]{{{_GROUP1_LEN}}}-[{ALPHABET}]{{{_GROUP2_LEN}}}$")


class RunCodeError(ValueError):
    """Raised when a string is not a valid run code. A loud failure — an unknown
    code surfaces as a plain error, never a silent fallback (TECH_SPEC §3, §7)."""


def generate() -> str:
    """Draw a fresh run code from a CSPRNG (TECH_SPEC §3).

    ~5.9 × 10⁸ codes over the 29-symbol alphabet — far more than a demo needs,
    short enough to read aloud. Uniqueness against existing runs is the caller's
    concern; see :func:`generate_unique`.
    """
    group1 = "".join(secrets.choice(ALPHABET) for _ in range(_GROUP1_LEN))
    group2 = "".join(secrets.choice(ALPHABET) for _ in range(_GROUP2_LEN))
    return f"{PREFIX}-{group1}-{group2}"


def normalize(raw: str) -> str:
    """Uppercase and trim a candidate code (TECH_SPEC §3 resume input).

    Does not validate — :func:`is_valid` / :func:`validate` do. Kept separate so
    the resume path can normalise first, then report an invalid *normalised* code.
    """
    return raw.strip().upper()


def is_valid(code: str) -> bool:
    """True iff ``code`` is exactly a normalised, well-formed run code.

    Strict: does not normalise first. Validate untrusted input with
    ``is_valid(normalize(raw))`` or :func:`validate`.
    """
    return bool(RUN_CODE_RE.match(code))


def validate(raw: str) -> str:
    """Normalise ``raw`` and return it if valid, else raise RunCodeError.

    The one call the resume path needs: it uppercases/trims, checks the format,
    and hands back the canonical code to look up ``runs/<code>/``.
    """
    code = normalize(raw)
    if not is_valid(code):
        raise RunCodeError(
            f"Not a valid run code: {raw!r} (normalised {code!r}). "
            f"Expected the form WT-XXXX-XX over the alphabet {ALPHABET}."
        )
    return code


def generate_unique(exists: Callable[[str], bool], attempts: int = 5) -> str:
    """Draw a run code that ``exists`` reports as free, up to ``attempts`` tries.

    ``exists(code)`` returns True iff ``runs/<code>/`` is already present — the
    backend supplies a GitHub Contents API ``GET`` (treating 404 as free, §3).
    This helper stays I/O-free and testable. On the rare exhaustion it raises,
    surfacing as the plain error §3 describes rather than a duplicate run.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    for _ in range(attempts):
        code = generate()
        if not exists(code):
            return code
    raise RunCodeError(
        f"Could not draw a free run code in {attempts} attempts. "
        "Retry the request (TECH_SPEC §3 collision handling)."
    )
