"""HTTP verification server: a read-only, JB-style console over the tested core.

Architecture mirrors JB: a static single-page frontend plus ``/api/*`` JSON.
The server seeds a demo registry (approved current + a pending version that must
not change the answer) so the registry and audit views have real content. It
never mutates scientific state from a request.
"""
import json
import threading
import urllib.request
from contextlib import closing

from h2l.server import make_server, route


def _json(path):
    status, ctype, body = route("GET", path)
    return status, ctype, json.loads(body)


def test_health_route():
    status, _, payload = _json("/api/health")
    assert status == 200 and payload["status"] == "ok"


def test_index_is_the_static_shell():
    status, ctype, body = route("GET", "/")
    assert status == 200
    assert "text/html" in ctype
    # JB-style app shell markers, rendered client-side.
    assert "H2L-Forge" in body
    assert "sync-rail" in body
    assert "primary-nav" in body
    assert 'src="static/app.js"' in body


def test_static_css_and_js_are_served():
    css_status, css_ctype, css_body = route("GET", "/static/styles.css")
    assert css_status == 200
    assert "text/css" in css_ctype
    assert "--corporate-green" in css_body  # JB design tokens reused verbatim

    js_status, js_ctype, js_body = route("GET", "/static/app.js")
    assert js_status == 200
    assert "javascript" in js_ctype


def test_status_rail_reports_pending_and_approved():
    status, _, payload = _json("/api/status")
    assert status == 200
    assert payload["approved_count"] >= 1
    assert payload["pending_count"] >= 1  # a detected-but-unapproved version exists
    assert payload["ruleset"]


def test_decision_default_rejects_tyk2_ibd():
    status, _, payload = _json("/api/decision?hypothesis=IBD:TYK2")
    assert status == 200
    assert payload["decision"] == "REJECT"
    assert payload["molecule_eligible"] is False


def test_decision_positive_branch_awaits_approval():
    status, _, payload = _json("/api/decision?hypothesis=IBD:DEMO-POS")
    assert status == 200
    assert payload["decision"] == "ADVANCE"
    assert payload["state"] == "AWAITING_APPROVAL"
    assert payload["molecule_eligible"] is False  # advance never auto-grants eligibility


def test_registry_shows_pending_not_changing_current():
    status, _, payload = _json("/api/registry")
    assert status == 200
    tyk2 = [g for g in payload["groups"] if g["hypothesis_id"] == "IBD:TYK2"][0]
    statuses = [v["status"] for v in tyk2["versions"]]
    assert "current" in statuses
    assert "pending" in statuses
    assert sum(s == "current" for s in statuses) == 1


def test_events_are_present():
    status, _, payload = _json("/api/events")
    assert status == 200
    assert len(payload["events"]) >= 1
    assert {"event_type", "occurred_at", "target_id"}.issubset(payload["events"][0])


def test_eval_route_reports_candidate_ready():
    status, _, payload = _json("/api/eval")
    assert status == 200
    assert payload["candidate"]["readiness"] is True
    assert payload["baseline"]["readiness"] is False


def test_unknown_route_is_404():
    status, _, _ = route("GET", "/does-not-exist")
    assert status == 404


def test_server_serves_over_a_real_socket():
    server = make_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        with closing(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=5)) as resp:
            assert resp.status == 200
            assert json.loads(resp.read())["status"] == "ok"
    finally:
        server.shutdown()
        thread.join(timeout=5)
