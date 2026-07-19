"""Read-only HTTP verification console (stdlib only, no dependencies).

Architecture mirrors the JB reference: a static single-page frontend under
``static/`` plus a ``/api/*`` JSON surface. The server renders decision traces,
the evidence registry, audit events, and the ablation evaluation so a human can
inspect the harness in a browser. It never mutates scientific state from a
request.

    python -m h2l.server --host 127.0.0.1 --port 8765

REJECTION_DEMO surface: the seeded packets are illustrative fixtures, not
verified clinical snapshots, and no therapeutic efficacy is claimed.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from h2l import RULESET_VERSION
from h2l.eval_runner import load_cases, run_evaluation
from h2l.registry import SnapshotRegistry
from h2l.replay import ClinicalContradictionCritic, DrugDiscoveryHarness, SnapshotEvidenceAdapter

BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "static"
DEMO_EVIDENCE = BASE_DIR / "tests" / "fixtures" / "tyk2_ibd" / "normalized_evidence.json"
DECISION_CASES = BASE_DIR / "evals" / "decision_cases.json"
BUDGET = {"max_tool_calls": 5, "max_attempts": 2}

STATIC_TYPES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".html": "text/html; charset=utf-8"}
_STATE: dict = {}


# ---- demo state (built once, in memory) --------------------------------
def _positive_packet() -> dict:
    cases = load_cases(DECISION_CASES)["cases"]
    return next(c["evidence"] for c in cases if c["id"] == "IN-INDICATION-SUPPORT")


def _registry() -> SnapshotRegistry:
    """A seeded in-memory registry, built once per process.

    Seeds an approved TYK2/IBD snapshot, a *pending* newer TYK2/IBD version that
    must not change the current answer, and an approved positive-branch demo.
    """
    if "registry" in _STATE:
        return _STATE["registry"]

    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="h2l-demo-")
    reg = SnapshotRegistry(Path(tmpdir) / "registry.json")

    tyk2 = json.loads(DEMO_EVIDENCE.read_text(encoding="utf-8"))
    v1 = reg.detect("IBD:TYK2", tyk2, observed_at="2026-07-16T00:00:00Z")
    reg.approve(v1["version_id"], actor="domain_reviewer", approved_at="2026-07-16T01:00:00Z")
    # A newer detection that stays pending: proves it does not change `current`.
    newer = dict(tyk2, observed_at="2026-07-18T00:00:00Z")
    reg.detect("IBD:TYK2", newer, observed_at="2026-07-18T00:00:00Z")

    pos = _positive_packet()
    vp = reg.detect(pos["hypothesis_id"], pos, observed_at=pos["observed_at"])
    reg.approve(vp["version_id"], actor="domain_reviewer", approved_at="2026-07-16T02:00:00Z")

    _STATE["registry"] = reg
    return reg


def _decide(hypothesis_id: str) -> dict:
    harness = DrugDiscoveryHarness(SnapshotEvidenceAdapter(_registry()), ClinicalContradictionCritic())
    result = harness.run(hypothesis_id, budget=BUDGET).to_dict()
    current = _registry().current(hypothesis_id)
    result["packet"] = current["payload"] if current else None
    return result


def _hypotheses() -> list[dict]:
    reg = _registry()
    items = []
    for version in reg.versions(include_history=False):
        if version["status"] == "current":
            items.append({"hypothesis_id": version["hypothesis_id"], "target": version["payload"].get("target")})
    return sorted(items, key=lambda x: x["hypothesis_id"])


def _status() -> dict:
    reg = _registry()
    history = reg.versions(include_history=True)
    current = [v for v in history if v["status"] == "current"]
    pending = [v for v in history if v["status"] == "pending"]
    last_snapshot = max((v["observed_at"] for v in current), default="—")
    return {
        "status": "ok",
        "network": "offline-core",
        "ruleset": RULESET_VERSION,
        "approved_count": len(current),
        "pending_count": len(pending),
        "hypothesis_count": len(current),
        "last_snapshot": last_snapshot,
    }


def _registry_view() -> dict:
    reg = _registry()
    history = reg.versions(include_history=True)
    groups: dict[str, list] = {}
    for v in history:
        groups.setdefault(v["hypothesis_id"], []).append(
            {
                "version_id": v["version_id"],
                "status": v["status"],
                "content_hash": v["content_hash"][:16],
                "observed_at": v["observed_at"],
                "target": v["payload"].get("target"),
                "reason": v.get("reason"),
            }
        )
    order = {"current": 0, "pending": 1, "superseded": 2, "rejected": 3}
    ordered = [
        {"hypothesis_id": hid, "versions": sorted(vs, key=lambda x: (order.get(x["status"], 9), x["observed_at"]))}
        for hid, vs in sorted(groups.items())
    ]
    return {"groups": ordered}


def _events_view() -> dict:
    reg = _registry()
    events = [
        {
            "event_id": e["event_id"],
            "occurred_at": e["occurred_at"],
            "actor": e["actor"],
            "event_type": e["event_type"],
            "target_id": e["target_id"],
            "summary": e["summary"],
        }
        for e in reg.events()
    ]
    return {"events": events}


def _eval_view() -> dict:
    return run_evaluation(load_cases(DECISION_CASES))


# ---- routing -----------------------------------------------------------
def route(method: str, path: str) -> tuple[int, str, str]:
    parts = urlsplit(path)
    clean = parts.path
    query = parse_qs(parts.query)

    if method != "GET":
        return 405, "application/json", json.dumps({"error": "method_not_allowed"})

    if clean == "/" or clean == "/index.html":
        return _serve_static("index.html")
    if clean.startswith("/static/"):
        return _serve_static(clean[len("/static/"):])

    if clean == "/api/health":
        return _ok({"status": "ok", "ruleset": RULESET_VERSION})
    if clean == "/api/status":
        return _ok(_status())
    if clean == "/api/hypotheses":
        return _ok({"hypotheses": _hypotheses()})
    if clean == "/api/decision":
        hypothesis = (query.get("hypothesis") or ["IBD:TYK2"])[0]
        return _ok(_decide(hypothesis))
    if clean == "/api/registry":
        return _ok(_registry_view())
    if clean == "/api/events":
        return _ok(_events_view())
    if clean == "/api/eval":
        return _ok(_eval_view())
    if clean == "/api/demo":  # backward-compatible alias
        return _ok(_decide("IBD:TYK2"))

    return 404, "application/json", json.dumps({"error": "not_found", "path": clean})


def _ok(payload: dict) -> tuple[int, str, str]:
    return 200, "application/json; charset=utf-8", json.dumps(payload, ensure_ascii=False, indent=2)


def _serve_static(name: str) -> tuple[int, str, str]:
    target = (STATIC_DIR / name).resolve()
    if STATIC_DIR not in target.parents and target != STATIC_DIR / name:
        return 404, "application/json", json.dumps({"error": "forbidden"})
    if not target.is_file():
        return 404, "application/json", json.dumps({"error": "not_found", "path": name})
    ctype = STATIC_TYPES.get(target.suffix, "application/octet-stream")
    return 200, ctype, target.read_text(encoding="utf-8")


# ---- http plumbing -----------------------------------------------------
class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (stdlib naming)
        status, ctype, body = route("GET", self.path)
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # keep the console quiet
        return


def make_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _Handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="h2l-server", description="Read-only H2L-Forge verification console.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    server = make_server(args.host, args.port)
    print(f"H2L-Forge console on http://{args.host}:{args.port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping…")
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
