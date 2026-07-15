"""The sufficiency rubric (TECH_SPEC §7.1; PROJECT_BRIEF §4).

Two halves, per §7.1:

  * a **deterministic gate** — every registry section resolved (computed from ``resolved``,
    never judged); and
  * **judged checks** (Flash-Lite, ``prompts/sufficiency.v1.md``) — no internal
    contradictions between resolved sections, and the happy path narratable end-to-end.

``missing`` lists unresolved sections first (reason ``"unresolved"``), then judged failures,
each ``{section_id, reason}``. ``ready`` is true only when ``missing`` is empty. The judged
call is skipped when nothing is resolved yet (no sections to contradict) — a pure saving; the
result is identical because the deterministic gate already makes ``ready`` false.
"""

from __future__ import annotations

from agents.prompting import load_prompt, wrap_untrusted
from llm import LLMClient

from outline import SECTION_IDS, Outline


def assess_sufficiency(outline: Outline, outline_md: str, client: LLMClient) -> dict:
    """Return ``{ready, missing:[{section_id, reason}]}`` for ``outline`` (§7.1).

    ``outline_md`` is the rendered outline text handed to the judge; ``client`` runs the
    Flash-Lite judged check. Unresolved sections are surfaced deterministically; the judge
    adds contradiction / happy-path failures for the resolved sections only."""
    resolved = set(outline.resolved)
    missing: list[dict] = [
        {"section_id": sid, "reason": "unresolved"} for sid in SECTION_IDS if sid not in resolved
    ]

    if resolved:
        for issue in _run_judge(outline_md, client):
            # Only keep judged failures against resolved sections; an issue naming an
            # unresolved section is already covered by the deterministic list above.
            if issue["section_id"] in resolved:
                missing.append(issue)

    return {"ready": not missing, "missing": missing}


def _run_judge(outline_md: str, client: LLMClient) -> list[dict]:
    prompt = load_prompt("sufficiency")
    user = "\n\n".join(
        [
            wrap_untrusted(outline_md, label="## The outline to judge"),
            "## Your task\n\nReturn the single JSON object your instructions describe: an "
            "`issues` list of `{section_id, reason}` for any contradiction or happy-path gap "
            "among the resolved sections (an empty list if there are none).",
        ]
    )
    data, _ = client.complete_json(prompt.model_role, prompt.system, user)
    raw = data.get("issues")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("section_id", ""))
        reason = str(item.get("reason", "")).strip()
        if sid in SECTION_IDS and reason:
            out.append({"section_id": sid, "reason": reason})
    return out
