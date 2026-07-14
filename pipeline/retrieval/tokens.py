"""Dependency-free token estimation for chunk sizing (TECH_SPEC §8.6 step 3).

The chunker targets 400–900 tokens (config/retrieval.yml). We deliberately avoid
pulling a model tokenizer into the runners — the targets are structural caps, not
quality dials (§8.8), so a stable word/punctuation count is a good-enough proxy
and keeps ingestion dependency-light. Consistency matters more than absolute
accuracy: the same estimator is used everywhere sizes are compared.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"\w+|[^\w\s]")


def estimate_tokens(text: str) -> int:
    """Approximate token count: word runs plus standalone punctuation marks."""
    return len(_TOKEN_RE.findall(text))
