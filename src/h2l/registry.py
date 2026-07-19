"""Versioned evidence registry.

Ported behavioural contract from the JB reference repository's
``RegulationRegistry``:

- content-addressed versions (SHA-256 over canonical JSON),
- a detected version is ``pending`` and does not change ``current``,
- approval promotes one version to ``current`` and supersedes the previous one,
- every mutation appends a structured audit event,
- persistence uses an atomic temp-file + rename write.

Version status values: ``pending``, ``current``, ``superseded``, ``rejected``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional


def canonical_json(value: Any) -> str:
    """Deterministic JSON used for hashing and on-disk state."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(payload: dict) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


class SnapshotRegistry:
    def __init__(self, path: Path):
        self.path = Path(path)
        if self.path.exists():
            self._state = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self._state = {"versions": [], "events": []}
            self._flush()

    # ---- reads ---------------------------------------------------------
    def versions(self, hypothesis_id: Optional[str] = None, *, include_history: bool = False) -> list[dict]:
        versions = self._state["versions"]
        if hypothesis_id is not None:
            versions = [v for v in versions if v["hypothesis_id"] == hypothesis_id]
        if not include_history:
            versions = [v for v in versions if v["status"] in ("pending", "current")]
        return [dict(v) for v in versions]

    def current(self, hypothesis_id: str) -> Optional[dict]:
        for version in self._state["versions"]:
            if version["hypothesis_id"] == hypothesis_id and version["status"] == "current":
                return dict(version)
        return None

    def events(self) -> list[dict]:
        return [dict(e) for e in self._state["events"]]

    # ---- mutations -----------------------------------------------------
    def detect(self, hypothesis_id: str, payload: dict, *, observed_at: str, actor: str = "evidence_scout") -> dict:
        digest = content_hash(payload)
        version_id = f"{hypothesis_id}@{digest[:12]}"
        existing = self._find(version_id)
        if existing is not None:
            return dict(existing)

        version = {
            "version_id": version_id,
            "hypothesis_id": hypothesis_id,
            "status": "pending",
            "content_hash": digest,
            "observed_at": observed_at,
            "payload": payload,
            "reason": None,
        }
        self._state["versions"].append(version)
        self._record_event(
            occurred_at=observed_at,
            actor=actor,
            event_type="EvidenceVersionDetected",
            target_id=version_id,
            summary=f"detected evidence version for {hypothesis_id}",
        )
        self._flush()
        return dict(version)

    def approve(self, version_id: str, *, actor: str, approved_at: str) -> dict:
        version = self._require(version_id)
        # Supersede the previous current version for the same hypothesis.
        for other in self._state["versions"]:
            if (
                other["hypothesis_id"] == version["hypothesis_id"]
                and other["status"] == "current"
                and other["version_id"] != version_id
            ):
                other["status"] = "superseded"
                self._record_event(
                    occurred_at=approved_at,
                    actor=actor,
                    event_type="EvidenceVersionSuperseded",
                    target_id=other["version_id"],
                    summary=f"superseded by {version_id}",
                )
        version["status"] = "current"
        self._record_event(
            occurred_at=approved_at,
            actor=actor,
            event_type="EvidenceVersionApproved",
            target_id=version_id,
            summary=f"approved evidence version for {version['hypothesis_id']}",
        )
        self._flush()
        return dict(version)

    def reject(self, version_id: str, *, actor: str, reason: str) -> dict:
        version = self._require(version_id)
        version["status"] = "rejected"
        version["reason"] = reason
        self._record_event(
            occurred_at=version["observed_at"],
            actor=actor,
            event_type="EvidenceVersionRejected",
            target_id=version_id,
            summary=reason,
        )
        self._flush()
        return dict(version)

    # ---- internals -----------------------------------------------------
    def _find(self, version_id: str) -> Optional[dict]:
        for version in self._state["versions"]:
            if version["version_id"] == version_id:
                return version
        return None

    def _require(self, version_id: str) -> dict:
        version = self._find(version_id)
        if version is None:
            raise KeyError(f"unknown version_id: {version_id}")
        return version

    def _record_event(self, *, occurred_at: str, actor: str, event_type: str, target_id: str, summary: str) -> None:
        event = {
            "event_id": f"EVT-{len(self._state['events']) + 1:04d}",
            "occurred_at": occurred_at,
            "actor": actor,
            "event_type": event_type,
            "target_id": target_id,
            "summary": summary,
        }
        self._state["events"].append(event)

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)
