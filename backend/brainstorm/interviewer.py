"""The co-design interviewer (TECH_SPEC §7, §7.1; PROJECT_BRIEF §4).

One Flash-Lite call per user turn: given the conversation so far and the current outline, it
replies with the next question and writes whatever outline sections the conversation now
supports. The wrapper here assembles the (untrusted-wrapped) context, calls the model, and
validates the output shape; the outline document machinery (applying the updates, computing
the delta, maintaining ``resolved``) lives in ``backend/outline.py``.

Write-scope note: the interviewer may only write the nine registry section ids (§7.1). An
output naming an id outside the registry is **dropped**, not failed — the Brainstorm surface
is conversational and fully user-revisable, so a stray id costs a re-prompt, not a lost run;
the one hard requirement is a non-empty ``assistant_message`` to show the user.
"""

from __future__ import annotations

from dataclasses import dataclass

from agents.prompting import load_prompt, wrap_untrusted
from llm import LLMClient

from outline import SECTION_IDS


class BrainstormError(RuntimeError):
    """An interviewer answer with no usable content (no ``assistant_message``). Loud so the
    endpoint returns a clean error rather than showing the user an empty reply."""


@dataclass
class InterviewerResult:
    """One interview turn's output. ``section_updates`` is already filtered to registry ids;
    ``title``/``summary`` are ``None`` unless the model set them this turn."""

    assistant_message: str
    section_updates: dict[str, str]
    title: str | None
    summary: str | None
    model: str = ""
    prompt_version: str = ""


def run_interviewer(
    client: LLMClient, *, outline_md: str, dialogue: str, user_message: str
) -> InterviewerResult:
    """Run one interview turn (§7.1). ``dialogue`` is the readable transcript so far (empty on
    the first turn); ``user_message`` is what the user just said; ``outline_md`` is the current
    outline. All three are user-derived and wrapped as untrusted content (§9.2)."""
    prompt = load_prompt("interviewer")
    parts = [
        wrap_untrusted(
            outline_md, label="## The outline so far (what you have written; update it)"
        ),
    ]
    if dialogue.strip():
        parts.append(wrap_untrusted(dialogue, label="## The conversation so far (oldest first)"))
    parts.append(wrap_untrusted(user_message, label="## What the person just said (reply to this)"))
    parts.append(
        "## Your turn\n\nReturn the single JSON object your instructions describe: your reply "
        "and next question in `assistant_message`, any sections you can now write in "
        "`section_updates`, and `title`/`summary` if you are setting them."
    )
    data, resp = client.complete_json(prompt.model_role, prompt.system, "\n\n".join(parts))
    return _parse(data, resp, prompt)


def _parse(data: dict, resp, prompt) -> InterviewerResult:
    assistant_message = str(data.get("assistant_message", "")).strip()
    if not assistant_message:
        raise BrainstormError("interviewer returned no 'assistant_message'.")

    raw_updates = data.get("section_updates") or {}
    section_updates: dict[str, str] = {}
    if isinstance(raw_updates, dict):
        for sid, body in raw_updates.items():
            if sid in SECTION_IDS and isinstance(body, str) and body.strip():
                section_updates[sid] = body.strip()

    title = data.get("title")
    summary = data.get("summary")
    return InterviewerResult(
        assistant_message=assistant_message,
        section_updates=section_updates,
        title=str(title).strip() if isinstance(title, str) and title.strip() else None,
        summary=str(summary).strip() if isinstance(summary, str) and summary.strip() else None,
        model=resp.model,
        prompt_version=prompt.version,
    )
