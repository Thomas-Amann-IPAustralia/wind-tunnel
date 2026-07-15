"""The specialist agent: retrieval tool loop + owned-section draft (TECH_SPEC
§5.1 FULL_DRAFTING, §8.1, §9.3).

Each of the six specialists drives its own KB through a bounded fetch/search
loop (§8.1): the model sees its KB index and, each round, returns either a tool
call or a final draft. The wrapper resolves `fetch`/`search` against the KB
(``pipeline/retrieval/``, LLM-free) and feeds the results back; after
``config/retrieval.yml`` `fetch.max_rounds` tool rounds (or the fetched-token
cap), the wrapper demands a final draft from whatever was retrieved rather than
looping forever.

Write-scope is enforced here at the agent boundary (§9.3): a specialist's draft
may only touch its own owned section ids (`agents.prompting.specialist_owned_sections`)
— any other key, in `sections`, `citations`, or `gaps`, is rejected, not ignored.
Every owned section must be either drafted or flagged as a gap with a reason; a
specialist never asserts a risk rating (it does not own §3, so this never arises,
but the JSON schema below has no rating field to begin with).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from agents.prompting import (
    load_prompt,
    response_type_of,
    specialist_instrument_context,
    specialist_owned_sections,
    specialist_seed_terms,
    wrap_untrusted,
)
from llm import LLMClient
from retrieval.retrieve import KB, RetrievedChunk
from retrieval.tokens import estimate_tokens

MAX_QUESTIONS_PER_SPECIALIST = 3  # CLAUDE.md §3 "specialist questions ≤3 each"
_YES_NO_NA = ("yes", "no", "not applicable")


class AgentError(RuntimeError):
    """A specialist's answer violated the output contract — an out-of-scope
    section, a section neither drafted nor flagged as a gap, too many questions,
    or a malformed tool call. Loud: the pipeline surfaces it as a calm, resumable
    failure (§5.6) rather than assembling a bad draft."""


@dataclass
class SpecialistDraft:
    """One specialist's full-assessment draft (§4 `full/specialists/<id>.json`).
    ``sections``/``citations``/``gaps`` are keyed by owned subsection id only —
    the structural write-scope guarantee (§9.3)."""

    specialist: str
    sections: dict[str, str]
    citations: dict[str, list[dict]]
    questions_why: str
    questions: list[dict]
    gaps: list[dict]
    model: str = ""
    prompt_version: str = ""

    def to_dict(self) -> dict:
        return {
            "specialist": self.specialist,
            "sections": self.sections,
            "citations": self.citations,
            "questions": {"why": self.questions_why, "items": self.questions},
            "gaps": self.gaps,
            "provenance": {"model": self.model, "prompt_version": self.prompt_version},
        }


@lru_cache(maxsize=1)
def _retrieval_config() -> dict:
    import yaml

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "config" / "retrieval.yml"
        if candidate.is_file():
            with candidate.open(encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
    raise AgentError(f"Could not locate config/retrieval.yml above {here}.")


def run_specialist(
    client: LLMClient,
    specialist_id: str,
    outline_md: str,
    threshold_md: str,
    kb: KB,
    index_text: str,
    *,
    status: object | None = None,  # status.StatusModel — typed loosely to stay import-light
    node_id: str | None = None,
    max_rounds: int | None = None,
    search_top_k: int | None = None,
    seed_top_k: int | None = None,
    max_total_tokens: int | None = None,
) -> SpecialistDraft:
    """Run one specialist's bounded retrieval + draft loop (§8.1, §9.3).

    ``status``/``node_id`` are optional so this stays testable without a status
    model; when given, every fetch/search emits a `retrieval` event (§6.3)."""
    cfg = _retrieval_config()
    max_rounds = max_rounds if max_rounds is not None else cfg["fetch"]["max_rounds"]
    search_top_k = search_top_k if search_top_k is not None else cfg["search"]["top_k"]
    seed_top_k = seed_top_k if seed_top_k is not None else cfg["search"]["seed_top_k"]
    max_total_tokens = (
        max_total_tokens if max_total_tokens is not None else cfg["fetch"]["max_total_tokens"]
    )

    prompt = load_prompt("specialist")
    owned = specialist_owned_sections(specialist_id)
    context = specialist_instrument_context(specialist_id)

    history: list[str] = []
    fetched_tokens = 0
    seed = kb.search(specialist_seed_terms(specialist_id), k=seed_top_k)
    if seed:
        _narrate(status, node_id, seed)
        history.append(_render_chunks("Seed context (pre-fetched)", seed))
        fetched_tokens += sum(estimate_tokens(c.text) for c in seed)

    for round_no in range(1, max_rounds + 1):
        user = _build_user(
            context, index_text, outline_md, threshold_md, history, round_no, max_rounds
        )
        data, resp = client.complete_json("specialist", prompt.system, user)
        action = data.get("action")
        if action == "draft":
            return _parse_draft(data, specialist_id, owned, resp, prompt)
        if action not in ("fetch", "search"):
            raise AgentError(
                f"{specialist_id}: unknown action {action!r} (expected fetch/search/draft)."
            )
        chunks = _run_tool(kb, action, data, specialist_id, search_top_k)
        _narrate(status, node_id, chunks)
        history.append(_render_chunks(f"{action}() result", chunks))
        fetched_tokens += sum(estimate_tokens(c.text) for c in chunks)
        if fetched_tokens >= max_total_tokens:
            break  # hit the per-call fetch cap (§8.1) — force the final round below

    # Forced final round (§8.1: "on cap, the wrapper demands the final draft from
    # what has been fetched") — no more tool calls permitted.
    user = _build_user(
        context, index_text, outline_md, threshold_md, history, max_rounds, max_rounds, final=True
    )
    data, resp = client.complete_json("specialist", prompt.system, user)
    if data.get("action") != "draft":
        raise AgentError(f"{specialist_id}: did not return a draft on the forced final round.")
    return _parse_draft(data, specialist_id, owned, resp, prompt)


def _run_tool(
    kb: KB, action: str, data: dict, specialist_id: str, search_top_k: int
) -> list[RetrievedChunk]:
    if action == "fetch":
        refs = data.get("refs")
        if not isinstance(refs, list) or not refs:
            raise AgentError(f"{specialist_id}: fetch requires a non-empty 'refs' list.")
        return kb.fetch([str(r) for r in refs])
    query = data.get("query")
    if not isinstance(query, str) or not query.strip():
        raise AgentError(f"{specialist_id}: search requires a non-empty 'query' string.")
    k = data.get("k", search_top_k)
    try:
        k = min(int(k), search_top_k)
    except (TypeError, ValueError):
        k = search_top_k
    return kb.search(query, k=max(1, k))


def _narrate(status: object | None, node_id: str | None, chunks: list[RetrievedChunk]) -> None:
    if status is None or node_id is None:
        return
    for c in chunks:
        status.retrieval(node_id, f"reading {c.short_name}", doc=c.short_name, locator=c.locator)


def _render_chunks(label: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return f"{label}: none found."
    lines = [f"{label}:"]
    for c in chunks:
        lines.append(
            f"- chunk_id={c.chunk_id!r} citation={c.citation} "
            f"section={c.section_path or '(root)'}\n  {c.text}"
        )
    return "\n".join(lines)


def _build_user(
    context: str,
    index_text: str,
    outline_md: str,
    threshold_md: str,
    history: list[str],
    round_no: int,
    max_rounds: int,
    *,
    final: bool = False,
) -> str:
    parts = [
        context,
        f"## Your knowledge base index\n\n{index_text}",
        wrap_untrusted(outline_md, label="## Use-case outline (the concept under assessment)"),
        wrap_untrusted(
            threshold_md,
            label="## Threshold assessment (already completed — sections 1–4 and the "
            "computed inherent risk ratings)",
        ),
    ]
    if history:
        parts.append("## Retrieval so far\n\n" + "\n\n".join(history))
    if final:
        parts.append(
            "## Final round — no more tool calls\n\n"
            'Return your final `{"action": "draft", ...}` answer now, using only what '
            "you have already fetched or searched above. If a section still cannot be "
            "determined from what you have, record it in `gaps` with a reason rather than "
            "inventing detail."
        )
    else:
        parts.append(
            f"## This turn (round {round_no} of {max_rounds})\n\n"
            "Return exactly one JSON object: either a tool call "
            '(`{"action":"fetch","refs":[...]}` or `{"action":"search","query":"...","k":8}`) '
            'or your final answer (`{"action":"draft", ...}`) if you already have enough to '
            "draft every owned section. Do not repeat a fetch/search already shown above."
        )
    return "\n\n".join(parts)


# -- validation (§9.3 structural write-scope, §9.4 citation shape) -------------


def _parse_draft(
    data: dict, specialist_id: str, owned: tuple[str, ...], resp, prompt
) -> SpecialistDraft:
    sections_in = data.get("sections")
    if not isinstance(sections_in, dict):
        raise AgentError(f"{specialist_id}: 'sections' must be an object.")
    out_of_scope = set(sections_in) - set(owned)
    if out_of_scope:
        raise AgentError(
            f"{specialist_id}: sections contain out-of-scope keys {sorted(out_of_scope)} "
            "(§9.3 structural write-scope)."
        )

    gaps_out = _require_gaps(data.get("gaps"), specialist_id, owned)
    gap_ids = {g["section"] for g in gaps_out}

    sections_out: dict[str, str] = {}
    for sid in owned:
        value = sections_in.get(sid)
        has_text = isinstance(value, str) and bool(value.strip())
        if sid in gap_ids:
            if has_text:
                raise AgentError(
                    f"{specialist_id}: {sid!r} is both drafted and flagged as a gap — pick one."
                )
            continue
        if not has_text:
            raise AgentError(
                f"{specialist_id}: {sid!r} is neither drafted nor flagged as a gap "
                "(every owned section must be one or the other)."
            )
        text = value.strip()
        if response_type_of(sid) == "yes_no_na" and not text.lower().startswith(_YES_NO_NA):
            raise AgentError(
                f"{specialist_id}: {sid!r} is a yes/no/N-A question and must open with "
                f"'Yes', 'No', or 'Not applicable' — got {text[:40]!r}."
            )
        sections_out[sid] = text

    citations_out = _require_citations(data.get("citations"), specialist_id, owned)
    questions_why, questions_out = _require_questions(data.get("questions"), specialist_id)

    return SpecialistDraft(
        specialist=specialist_id,
        sections=sections_out,
        citations=citations_out,
        questions_why=questions_why,
        questions=questions_out,
        gaps=gaps_out,
        model=resp.model,
        prompt_version=prompt.version,
    )


def _require_gaps(raw: object, specialist_id: str, owned: tuple[str, ...]) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise AgentError(f"{specialist_id}: 'gaps' must be a list if present.")
    out: list[dict] = []
    seen: set[str] = set()
    for g in raw:
        if not isinstance(g, dict) or not g.get("section") or not g.get("reason"):
            raise AgentError(f"{specialist_id}: each gap needs 'section' and 'reason'.")
        sid = str(g["section"])
        if sid not in owned:
            raise AgentError(f"{specialist_id}: gap for out-of-scope section {sid!r}.")
        if sid in seen:
            raise AgentError(f"{specialist_id}: duplicate gap for section {sid!r}.")
        seen.add(sid)
        out.append({"section": sid, "reason": str(g["reason"]).strip()})
    return out


def _require_citations(raw: object, specialist_id: str, owned: tuple[str, ...]) -> dict[str, list]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise AgentError(f"{specialist_id}: 'citations' must be an object if present.")
    out: dict[str, list[dict]] = {}
    for sid, entries in raw.items():
        if sid not in owned:
            raise AgentError(f"{specialist_id}: citations for out-of-scope section {sid!r}.")
        if not isinstance(entries, list):
            raise AgentError(f"{specialist_id}: citations[{sid!r}] must be a list.")
        clean = []
        for e in entries:
            if not isinstance(e, dict) or not e.get("short_name") or not e.get("locator"):
                raise AgentError(
                    f"{specialist_id}: citations[{sid!r}] entries need 'short_name' and 'locator'."
                )
            clean.append({"short_name": str(e["short_name"]), "locator": str(e["locator"])})
        out[sid] = clean
    return out


def _require_questions(raw: object, specialist_id: str) -> tuple[str, list[dict]]:
    if raw is None:
        return "", []
    if not isinstance(raw, dict):
        raise AgentError(f"{specialist_id}: 'questions' must be an object if present.")
    items_in = raw.get("items") or []
    if not isinstance(items_in, list):
        raise AgentError(f"{specialist_id}: 'questions.items' must be a list.")
    if len(items_in) > MAX_QUESTIONS_PER_SPECIALIST:
        raise AgentError(
            f"{specialist_id}: {len(items_in)} questions exceeds the cap of "
            f"{MAX_QUESTIONS_PER_SPECIALIST} (CLAUDE.md §3)."
        )
    items_out: list[dict] = []
    seen: set[str] = set()
    for item in items_in:
        if not isinstance(item, dict) or not item.get("question_id") or not item.get("text"):
            raise AgentError(f"{specialist_id}: each question needs 'question_id' and 'text'.")
        qid = str(item["question_id"])
        if qid in seen:
            raise AgentError(f"{specialist_id}: duplicate question_id {qid!r}.")
        seen.add(qid)
        options = item.get("options")
        if options is not None and not (
            isinstance(options, list) and all(isinstance(o, str) for o in options)
        ):
            raise AgentError(
                f"{specialist_id}: question {qid!r} 'options' must be a list of strings."
            )
        items_out.append(
            {
                "question_id": qid,
                "text": str(item["text"]).strip(),
                "options": options,
                "allow_free_text": bool(item.get("allow_free_text", True)),
            }
        )
    why = str(raw.get("why", "")).strip()
    if items_out and not why:
        raise AgentError(f"{specialist_id}: questions raised without a 'why'.")
    return why, items_out
