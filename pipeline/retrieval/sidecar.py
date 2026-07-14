"""Sidecar metadata + the licence hard gate (TECH_SPEC §8.6 step 1).

Every corpus document carries a `<filename>.meta.yml` sidecar (corpus/README.md
template) with seven fields. The licence gate is the enforcement point: a document
is admitted only if `redistributable: true` AND `licence` is in the committed
allow-list (config/licences.yml). The repo is public and every chunk republishes
source text, so this is a gate, not a router (PROJECT_BRIEF §3, §10) — a failure
raises loudly and names the offending file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

REQUIRED_FIELDS = (
    "short_name",
    "title",
    "version",
    "publisher",
    "source_url",
    "licence",
    "redistributable",
)


class LicenceGateError(Exception):
    """A document failed the licence hard gate. Nothing downstream may run."""


class SidecarError(Exception):
    """A sidecar is missing or malformed."""


@dataclass
class Sidecar:
    short_name: str
    title: str
    version: str | None
    publisher: str | None
    source_url: str | None
    licence: str
    redistributable: bool
    path: Path

    @classmethod
    def load(cls, doc_path: Path) -> "Sidecar":
        meta_path = doc_path.with_name(doc_path.name + ".meta.yml")
        if not meta_path.is_file():
            raise SidecarError(f"No sidecar for {doc_path.name} (expected {meta_path.name}).")
        with meta_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        missing = [f for f in REQUIRED_FIELDS if f not in data]
        if missing:
            raise SidecarError(f"{meta_path.name} missing fields: {missing}")
        return cls(
            short_name=str(data["short_name"]).strip(),
            title=str(data["title"]).strip(),
            version=None if data["version"] is None else str(data["version"]).strip(),
            publisher=None if data["publisher"] is None else str(data["publisher"]).strip(),
            source_url=None if data["source_url"] is None else str(data["source_url"]).strip(),
            licence=str(data["licence"]).strip(),
            redistributable=bool(data["redistributable"]),
            path=meta_path,
        )


def load_licence_allow_list(config_dir: Path) -> set[str]:
    path = config_dir / "licences.yml"
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    allow = data.get("allow_list")
    if not allow:
        raise SidecarError(f"{path} has no allow_list.")
    return {str(x).strip() for x in allow}


def enforce_licence_gate(sidecar: Sidecar, allow_list: set[str], doc_path: Path) -> None:
    """Raise LicenceGateError unless the document is cleared for republication."""
    if sidecar.redistributable is not True:
        raise LicenceGateError(
            f"LICENCE GATE: {doc_path.name} has redistributable != true "
            f"(sidecar {sidecar.path.name}). Refusing to ingest into a public repo."
        )
    if sidecar.licence not in allow_list:
        raise LicenceGateError(
            f"LICENCE GATE: {doc_path.name} licence {sidecar.licence!r} is not in the "
            f"allow-list (config/licences.yml). Add it deliberately or exclude the "
            f"document — an inherited redistributable flag must not wave through an "
            f"unrecognised licence."
        )
