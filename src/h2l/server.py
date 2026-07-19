"""HTTP verification and management console (stdlib only, no dependencies).

Architecture mirrors the JB reference: a static single-page frontend under
``static/`` plus a ``/api/*`` JSON surface. The scientific API renders decision
traces, the evidence registry, audit events, and the ablation evaluation as a
read-only surface. The management plane is mutable and persists operational
project, task, agent, run, approval, cost, and activity state through the
console store. It never mutates scientific state from a request.

    python -m h2l.server --host 127.0.0.1 --port 8765

REJECTION_DEMO surface: the seeded packets are illustrative fixtures, not
verified clinical snapshots, and no therapeutic efficacy is claimed.
"""
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from h2l import RULESET_VERSION
from h2l.console_store import ConsoleError, HadesConsoleStore
from h2l.eval_runner import load_cases, run_evaluation
from h2l.registry import SnapshotRegistry
from h2l.replay import ClinicalContradictionCritic, DrugDiscoveryHarness, SnapshotEvidenceAdapter

BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "static"
DEMO_EVIDENCE = BASE_DIR / "tests" / "fixtures" / "tyk2_ibd" / "normalized_evidence.json"
DECISION_CASES = BASE_DIR / "evals" / "decision_cases.json"
DEFAULT_CONSOLE_STATE = BASE_DIR / "artifacts" / "hades-console.json"
BUDGET = {"max_tool_calls": 5, "max_attempts": 2}
MAX_JSON_BODY = 1024 * 1024

STATIC_TYPES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".html": "text/html; charset=utf-8"}
_STATE: dict = {}
_CONSOLE_STORE: HadesConsoleStore | None = None


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
def configure_console_store(path: str | os.PathLike) -> HadesConsoleStore:
    global _CONSOLE_STORE
    _CONSOLE_STORE = HadesConsoleStore(Path(path))
    return _CONSOLE_STORE


def _console_store() -> HadesConsoleStore:
    global _CONSOLE_STORE
    if _CONSOLE_STORE is None:
        _CONSOLE_STORE = HadesConsoleStore(Path(os.environ.get("H2L_CONSOLE_STATE_PATH", DEFAULT_CONSOLE_STATE)))
    return _CONSOLE_STORE


def route(method: str, path: str, body=None) -> tuple[int, str, str]:
    parts = urlsplit(path)
    clean = parts.path
    query = parse_qs(parts.query)
    method = method.upper()

    try:
        if clean.startswith("/api/"):
            response = _route_console(method, clean, body)
            if response is not None:
                return response
    except ConsoleError as error:
        return _console_error(error)

    if clean == "/" or clean == "/index.html":
        if method != "GET":
            return _method_not_allowed()
        return _serve_static("index.html")
    if clean.startswith("/static/"):
        if method != "GET":
            return _method_not_allowed()
        return _serve_static(clean[len("/static/"):])

    if method != "GET":
        return _method_not_allowed()

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

    return _json_response(404, {"error": "not_found", "message": f"Route not found: {clean}", "details": {"path": clean}})


def _route_console(method: str, clean: str, body) -> tuple[int, str, str] | None:
    collections = {
        "/api/projects": "projects",
        "/api/tasks": "tasks",
        "/api/agents": "agents",
        "/api/runs": "runs",
        "/api/approvals": "approvals",
        "/api/activity": "activity",
    }
    is_management_path = clean in {"/api/console", "/api/costs"} or clean in collections or any(
        clean.startswith(path + "/") for path in collections
    )
    if not is_management_path:
        return None

    store = _console_store()

    if method == "GET":
        if clean == "/api/console":
            return _ok(store.snapshot())
        if clean in collections:
            return _json_response(200, store.list_entities(collections[clean]))
        if clean == "/api/costs":
            return _ok(store.cost_summary())
        raise ConsoleError("not_found", f"Management route not found: {clean}", 404, {"path": clean})

    if method not in {"POST", "PATCH"}:
        raise ConsoleError("method_not_allowed", f"Method {method} is not allowed for {clean}", 405, {"method": method})
    if _is_known_management_wrong_method(method, clean):
        raise ConsoleError("method_not_allowed", f"Method {method} is not allowed for {clean}", 405, {"method": method})
    payload = _payload_object(body)
    actor = _pop_actor(payload)
    return _mutate_console(store, method, clean, payload, actor)


def _is_known_management_wrong_method(method: str, clean: str) -> bool:
    segments = [segment for segment in clean.split("/") if segment]
    if clean in {"/api/console", "/api/costs"}:
        return True
    if clean in {"/api/projects", "/api/tasks"}:
        return method != "POST"
    if clean in {"/api/agents", "/api/runs", "/api/approvals", "/api/activity"}:
        return True
    if len(segments) == 3 and segments[:2] in (["api", "projects"], ["api", "tasks"]):
        return method != "PATCH"
    action_routes = {
        ("api", "tasks", "checkout"),
        ("api", "tasks", "release"),
        ("api", "agents", "pause"),
        ("api", "agents", "resume"),
        ("api", "runs", "retry"),
        ("api", "approvals", "approve"),
        ("api", "approvals", "reject"),
        ("api", "approvals", "request-revision"),
    }
    if len(segments) == 4 and (segments[0], segments[1], segments[3]) in action_routes:
        return method != "POST"
    return False


def _mutate_console(store: HadesConsoleStore, method: str, clean: str, payload: dict, actor: str) -> tuple[int, str, str]:
    segments = [segment for segment in clean.split("/") if segment]

    if method == "POST" and segments == ["api", "projects"]:
        return _json_response(201, store.create_project(payload, actor))
    if method == "PATCH" and len(segments) == 3 and segments[:2] == ["api", "projects"]:
        return _ok(store.update_project(segments[2], payload, actor))

    if method == "POST" and segments == ["api", "tasks"]:
        return _json_response(201, store.create_task(payload, actor))
    if method == "PATCH" and len(segments) == 3 and segments[:2] == ["api", "tasks"]:
        return _ok(store.update_task(segments[2], payload, actor))
    if method == "POST" and len(segments) == 4 and segments[:2] == ["api", "tasks"] and segments[3] == "checkout":
        task = store.checkout_task(
            segments[2],
            _required_payload(payload, "agent_id"),
            _expected_statuses(payload),
            _required_payload(payload, "run_id"),
            actor,
        )
        return _ok(task)
    if method == "POST" and len(segments) == 4 and segments[:2] == ["api", "tasks"] and segments[3] == "release":
        return _ok(store.release_task(segments[2], actor))

    if method == "POST" and len(segments) == 4 and segments[:2] == ["api", "agents"] and segments[3] == "pause":
        return _ok(store.set_agent_status(segments[2], "paused", payload.get("reason"), actor))
    if method == "POST" and len(segments) == 4 and segments[:2] == ["api", "agents"] and segments[3] == "resume":
        return _ok(store.set_agent_status(segments[2], "idle", None, actor))

    if method == "POST" and len(segments) == 4 and segments[:2] == ["api", "runs"] and segments[3] == "retry":
        return _json_response(201, store.retry_run(segments[2], actor))

    if method == "POST" and len(segments) == 4 and segments[:2] == ["api", "approvals"]:
        return _ok(store.decide_approval(segments[2], segments[3], payload.get("note", payload.get("decision_note")), actor))

    if method in {"POST", "PATCH"}:
        raise ConsoleError("not_found", f"Management route not found: {clean}", 404, {"path": clean})
    raise ConsoleError("method_not_allowed", f"Method {method} is not allowed for {clean}", 405, {"method": method})


def _payload_object(body) -> dict:
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise ConsoleError("invalid_payload", "JSON body must be an object.", 400)
    return dict(body)


def _pop_actor(payload: dict) -> str:
    return payload.pop("actor", payload.pop("operator", "operator"))


def _required_payload(payload: dict, key: str):
    value = payload.get(key)
    if value in (None, ""):
        raise ConsoleError("missing_field", f"Missing required field: {key}", 400, {"field": key})
    return value


def _expected_statuses(payload: dict) -> list[str]:
    statuses = payload.get("expected_statuses", ["todo"])
    if not isinstance(statuses, list) or not statuses or any(not isinstance(item, str) or not item for item in statuses):
        raise ConsoleError(
            "invalid_expected_statuses",
            "expected_statuses must be a non-empty list of strings.",
            400,
            {"field": "expected_statuses"},
        )
    return statuses


def _ok(payload: dict) -> tuple[int, str, str]:
    return _json_response(200, payload)


def _json_response(status: int, payload) -> tuple[int, str, str]:
    return status, "application/json; charset=utf-8", json.dumps(payload, ensure_ascii=False, indent=2)


def _console_error(error: ConsoleError) -> tuple[int, str, str]:
    return _json_response(
        error.status,
        {"error": error.code, "message": error.message, "details": error.details},
    )


def _method_not_allowed() -> tuple[int, str, str]:
    return _json_response(
        405,
        {"error": "method_not_allowed", "message": "HTTP method is not allowed.", "details": {}},
    )


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
        self._dispatch("GET")

    def do_POST(self):  # noqa: N802 (stdlib naming)
        self._dispatch("POST")

    def do_PATCH(self):  # noqa: N802 (stdlib naming)
        self._dispatch("PATCH")

    def do_DELETE(self):  # noqa: N802 (stdlib naming)
        self._dispatch("DELETE")

    def do_PUT(self):  # noqa: N802 (stdlib naming)
        self._dispatch("PUT")

    def do_HEAD(self):  # noqa: N802 (stdlib naming)
        self._dispatch("HEAD")

    def _dispatch(self, method: str):
        try:
            body = self._read_json() if method in {"POST", "PATCH"} else None
            status, ctype, body = route(method, self.path, body)
        except ConsoleError as error:
            status, ctype, body = _console_error(error)
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ConsoleError("invalid_content_length", "Content-Length must be an integer.", 400) from exc
        if length < 0:
            raise ConsoleError("invalid_content_length", "Content-Length cannot be negative.", 400)
        if length > MAX_JSON_BODY:
            raise ConsoleError("payload_too_large", "JSON body exceeds 1 MiB.", 413)
        if length == 0:
            return {}
        try:
            value = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as exc:
            raise ConsoleError("invalid_json", "Request body is not valid JSON.", 400) from exc
        if not isinstance(value, dict):
            raise ConsoleError("invalid_payload", "JSON body must be an object.", 400)
        return value

    def log_message(self, *args):  # keep the console quiet
        return


def make_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _Handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="h2l-server",
        description="H2L-Forge verification console with read-only scientific APIs and a mutable management plane.",
    )
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
