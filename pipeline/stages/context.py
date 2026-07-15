"""StageContext — the handle every stage handler is given (TECH_SPEC §5).

It bundles the run directory, the authoritative ``run.json`` model, the derived
``status.json`` projection, the LLM client, and a clock. Handlers read/write
artefacts through it and narrate progress on ``status``; committing and stage
advancement are the driver's job (run.py), not the handler's — a handler only does
its state's work and leaves the outputs on disk for the driver to checkpoint (§5.3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from statefile import RunState, utc_now_iso
from status import StatusModel

# The outline lands here at run creation (TECH_SPEC §7.1); the threshold generalists
# read it as their sole use-case input.
OUTLINE_RELPATH = "brainstorm/outline.md"


@dataclass
class StageContext:
    run_dir: Path
    run: RunState
    status: StatusModel
    llm: object  # llm.LLMClient — typed loosely to keep stages import-light
    now: Callable[[], str] = utc_now_iso

    def path(self, *parts: str) -> Path:
        return self.run_dir.joinpath(*parts)

    def read_text(self, relpath: str) -> str:
        return self.path(relpath).read_text(encoding="utf-8")

    def read_json(self, relpath: str) -> dict:
        with self.path(relpath).open(encoding="utf-8") as fh:
            return json.load(fh)

    def write_text(self, relpath: str, text: str) -> Path:
        target = self.path(relpath)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def write_json(self, relpath: str, obj: object) -> Path:
        target = self.path(relpath)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        return target

    def outline(self) -> str:
        """The use-case outline (§7.1). Raises a clear error if it is missing — a
        threshold run cannot start without it."""
        path = self.path(OUTLINE_RELPATH)
        if not path.is_file():
            raise FileNotFoundError(
                f"No outline at {path} — the threshold stage needs {OUTLINE_RELPATH} "
                "(written at run creation, §7.1)."
            )
        return path.read_text(encoding="utf-8")
