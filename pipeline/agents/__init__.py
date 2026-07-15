"""pipeline.agents — the LLM agent layer (TECH_SPEC §9).

Agents assemble a role's prompt (from prompts/, §9.1), wrap user text as untrusted
data (§9.2), give the agent its instrument context (§9.3), call the model through
the LLM seam (llm.py), and validate the structured answer — crucially rejecting any
attempt to assert a rating (§9.4, §10). Stages (pipeline/stages/) drive agents;
agents never touch run.json/status.json or commit.
"""

from agents.threshold import (
    AgentError,
    GeneralistDraft,
    ReconcilerResult,
    run_generalist,
    run_reconciler,
)

__all__ = [
    "AgentError",
    "GeneralistDraft",
    "ReconcilerResult",
    "run_generalist",
    "run_reconciler",
]
