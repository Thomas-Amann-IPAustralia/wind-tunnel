"""The interview transcript — ``runs/<id>/brainstorm/transcript.jsonl`` (TECH_SPEC §4, §7).

One JSON object per line, in turn order: ``{"role": "user"|"assistant", "text", "ts"}``.
The transcript is the durable conversation history the stateless backend re-reads every turn
(a cold Render instance has no memory, CLAUDE.md §3). Append-only; the whole file is
re-committed on each turn (it is small, and the Git Data API writes whole blobs anyway, §14).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

_ROLES = ("user", "assistant")


@dataclass
class Turn:
    role: str
    text: str
    ts: str = ""

    def to_dict(self) -> dict:
        return {"role": self.role, "text": self.text, "ts": self.ts}


@dataclass
class Transcript:
    """The parsed interview transcript. ``render()`` produces the jsonl bytes to commit;
    ``as_dialogue()`` produces the readable form the interviewer prompt is shown."""

    turns: list[Turn] = field(default_factory=list)

    @classmethod
    def parse(cls, text: str | bytes | None) -> "Transcript":
        """Parse the committed jsonl (or an empty/absent file → an empty transcript). A
        malformed line is skipped rather than failing the whole turn — the transcript is a
        convenience record, not authoritative run state (that is ``run.json``, §4)."""
        if text is None:
            return cls()
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        turns: list[Turn] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            role = str(obj.get("role", ""))
            if role in _ROLES:
                turns.append(
                    Turn(role=role, text=str(obj.get("text", "")), ts=str(obj.get("ts", "")))
                )
        return cls(turns=turns)

    def append(self, role: str, text: str, ts: str) -> None:
        if role not in _ROLES:
            raise ValueError(f"unknown transcript role {role!r}.")
        self.turns.append(Turn(role=role, text=text, ts=ts))

    def render(self) -> bytes:
        return (
            "".join(json.dumps(t.to_dict(), ensure_ascii=False) + "\n" for t in self.turns)
        ).encode("utf-8")

    def as_dialogue(self) -> str:
        """The conversation as plain text for the interviewer prompt. Empty string for a
        fresh conversation (the interviewer opens the exchange)."""
        speaker = {"user": "User", "assistant": "You (interviewer)"}
        return "\n\n".join(f"{speaker[t.role]}: {t.text}" for t in self.turns)
