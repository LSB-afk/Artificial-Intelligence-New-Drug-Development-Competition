# Hades Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a durable Paperclip-inspired operations console for projects, tasks, AI agents, runs, costs, approvals, and activity without changing the scientific decision core.

**Architecture:** A new atomic JSON `HadesConsoleStore` owns general operations data. The existing stdlib HTTP server exposes read and mutation endpoints, while a vanilla static SPA renders the control plane. Existing decision/eval endpoints remain isolated and backward compatible.

**Tech Stack:** Python 3.10+ standard library, `pytest`, semantic HTML, CSS, vanilla JavaScript.

## Global Constraints

- Preserve `registry.py`, `state_machine.py`, `replay.py`, and `eval_runner.py` behavior.
- Add no runtime dependencies.
- Use only repository summaries, existing agent-role definitions, fixed test cases, and clearly labeled demo operations data.
- Do not perform biological judgment, molecule generation/optimization, synthesis design, experimental protocol creation, or clinical judgment.
- Do not store or display hidden chain-of-thought.
- Every mutation validates state, writes atomically, and appends an activity event.

---

## File Structure

- Create `src/h2l/console_store.py` — management entities, validation, atomic persistence, derived summaries, and mutations.
- Modify `src/h2l/server.py` — management API routing and JSON request handling.
- Create `tests/test_console_store.py` — unit coverage for store invariants.
- Modify `tests/test_server.py` — management API and HTTP mutation coverage.
- Create `static/index.html` — semantic Hades Console shell and action dialog.
- Create `static/app.js` — data loading, view rendering, mutation actions, escaping, and feedback.
- Modify `static/styles.css` — console-specific layout, operations pulse, tables, dialogs, and responsive behavior.
- Modify `README.md` — console run instructions and scope.
- Modify `harness.yaml` — register the management module and implementation decision.
- Create `docs/superpowers/specs/2026-07-19-hades-console-design.md` — approved design record.

### Task 1: Atomic management store

**Files:**

- Create: `tests/test_console_store.py`
- Create: `src/h2l/console_store.py`

**Interfaces:**

- Produces: `ConsoleError`, `seed_console_data()`, and
  `HadesConsoleStore(path: Path)`.
- Produces store methods:
  `snapshot()`, `list_entities(kind)`, `create_project(payload, actor)`,
  `update_project(id, payload, actor)`, `create_task(payload, actor)`,
  `update_task(id, payload, actor)`, `checkout_task(id, agent_id,
  expected_statuses, run_id, actor)`, `release_task(id, actor)`,
  `set_agent_status(id, status, reason, actor)`,
  `retry_run(id, actor)`, `decide_approval(id, action, note, actor)`,
  and `cost_summary()`.
- Consumes: only `json`, `threading`, `uuid`, `datetime`, `pathlib`,
  `tempfile`, and `os` from the standard library.

- [ ] **Step 1: Write the failing seed and persistence tests**

```python
def test_store_seeds_and_persists(tmp_path):
    path = tmp_path / "console.json"
    store = HadesConsoleStore(path)
    first = store.snapshot()
    assert first["overview"]["project_count"] >= 1
    created = store.create_task(
        {
            "project_id": first["projects"][0]["id"],
            "title": "정적 앱 셸 검증",
            "status": "todo",
            "priority": "high",
        },
        actor="test-user",
    )
    reloaded = HadesConsoleStore(path).snapshot()
    assert any(task["id"] == created["id"] for task in reloaded["tasks"])
```

- [ ] **Step 2: Run the new tests and verify RED**

Run: `pytest tests/test_console_store.py -q`

Expected: collection fails because `h2l.console_store` does not exist.

- [ ] **Step 3: Write checkout, approval, agent, retry, and cost tests**

```python
def test_checkout_is_atomic(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    task = next(item for item in store.snapshot()["tasks"] if item["status"] == "todo")
    agent = store.snapshot()["agents"][0]
    claimed = store.checkout_task(task["id"], agent["id"], ["todo"], "run-test", "operator")
    assert claimed["status"] == "in_progress"
    with pytest.raises(ConsoleError) as error:
        store.checkout_task(task["id"], "other-agent", ["todo"], "run-other", "operator")
    assert error.value.status == 409


def test_approval_decision_is_terminal(tmp_path):
    store = HadesConsoleStore(tmp_path / "console.json")
    approval = next(item for item in store.snapshot()["approvals"] if item["status"] == "pending")
    decided = store.decide_approval(approval["id"], "approve", "운영 범위 확인", "reviewer")
    assert decided["status"] == "approved"
    with pytest.raises(ConsoleError) as error:
        store.decide_approval(approval["id"], "reject", "late", "reviewer")
    assert error.value.status == 409
```

- [ ] **Step 4: Implement the minimal store**

```python
class ConsoleError(ValueError):
    def __init__(self, code: str, message: str, status: int = 400, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


class HadesConsoleStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        if not self.path.exists():
            self._write(seed_console_data())

    def snapshot(self) -> dict:
        with self._lock:
            state = self._read()
            state["costs"] = self._cost_summary(state)
            state["overview"] = self._overview(state)
            return copy.deepcopy(state)
```

Use a sibling temporary file plus `os.replace()` in `_write`. Validate enum
fields and references before mutation. Use fixed repository-derived demo
timestamps and label all seeded records `demo`.

- [ ] **Step 5: Run store tests and verify GREEN**

Run: `pytest tests/test_console_store.py -q`

Expected: all store tests pass.

- [ ] **Step 6: Commit the store slice**

```bash
git add src/h2l/console_store.py tests/test_console_store.py
git commit -m "Make console operations durable and auditable

Constraint: Preserve the deterministic scientific core and add no runtime dependency
Rejected: In-memory state | restart would erase task ownership and approvals
Confidence: high
Scope-risk: moderate
Directive: Keep scientific evidence and decisions outside HadesConsoleStore
Tested: pytest tests/test_console_store.py -q
Not-tested: Multi-process file locking"
```

### Task 2: Management HTTP API

**Files:**

- Modify: `tests/test_server.py`
- Modify: `src/h2l/server.py`

**Interfaces:**

- Consumes: `HadesConsoleStore` and `ConsoleError`.
- Produces: `route(method, path, body=None)` for unit tests.
- Produces: GET collection routes and validated POST/PATCH mutation routes.
- Preserves: all existing `/api/status`, `/api/decision`, `/api/registry`,
  `/api/events`, `/api/eval`, and `/api/demo` responses.

- [ ] **Step 1: Write failing API tests**

```python
def test_console_snapshot_exposes_management_entities(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    status, _, payload = _json("/api/console")
    assert status == 200
    assert {"projects", "tasks", "agents", "runs", "approvals", "activity", "costs"}.issubset(payload)


def test_task_create_and_checkout_routes(tmp_path):
    configure_console_store(tmp_path / "hades.json")
    snapshot = _json("/api/console")[2]
    status, _, body = route(
        "POST",
        "/api/tasks",
        {
            "project_id": snapshot["projects"][0]["id"],
            "title": "회귀 테스트 실행",
            "status": "todo",
            "priority": "high",
        },
    )
    task = json.loads(body)
    assert status == 201
    status, _, body = route(
        "POST",
        f"/api/tasks/{task['id']}/checkout",
        {
            "agent_id": snapshot["agents"][0]["id"],
            "expected_statuses": ["todo"],
            "run_id": "run-http-test",
        },
    )
    assert status == 200
    assert json.loads(body)["status"] == "in_progress"
```

- [ ] **Step 2: Run server tests and verify RED**

Run: `pytest tests/test_server.py -q -k "console or task_create or approval_action"`

Expected: failures because management routes and store configuration do not
exist.

- [ ] **Step 3: Add API routes and structured errors**

```python
def _json_response(status: int, payload: dict) -> tuple[int, str, str]:
    return status, "application/json; charset=utf-8", json.dumps(
        payload, ensure_ascii=False, indent=2
    )


def _console_error(error: ConsoleError) -> tuple[int, str, str]:
    return _json_response(
        error.status,
        {"error": error.code, "message": error.message, "details": error.details},
    )
```

Route management paths before the legacy read-only API branch. Treat a missing
body as `{}`. Return 201 for creation, 200 for updates, 400 for malformed
payloads, 404 for missing IDs, and 409 for transition or checkout conflicts.

- [ ] **Step 4: Add HTTP JSON body handling**

```python
def _read_json(self) -> dict:
    length = int(self.headers.get("Content-Length", "0"))
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
```

Implement `do_POST` and `do_PATCH` through one `_dispatch` method. Add focused
real-socket coverage for a POST request when the environment allows sockets.

- [ ] **Step 5: Run API tests and verify GREEN**

Run: `pytest tests/test_server.py -q -k "not real_socket"`

Expected: all selected tests pass.

- [ ] **Step 6: Verify legacy server behavior**

Run: `pytest tests/test_server.py -q -k "health or decision or registry or events or eval"`

Expected: all legacy endpoint tests pass unchanged.

### Task 3: Static Hades Console application

**Files:**

- Create: `static/index.html`
- Create: `static/app.js`
- Modify: `static/styles.css`
- Modify: `tests/test_server.py`

**Interfaces:**

- Consumes: `GET /api/console` and the management mutation endpoints.
- Produces: eight navigable views and an accessible action dialog.
- Preserves: `sync-rail`, `primary-nav`, `--corporate-green`, and all existing
  static-shell test markers.

- [ ] **Step 1: Extend the failing static contract**

```python
def test_index_is_the_hades_console_shell():
    status, ctype, body = route("GET", "/")
    assert status == 200
    assert "하데스 콘솔" in body
    assert 'id="ops-pulse"' in body
    assert 'id="action-dialog"' in body
    assert 'src="static/app.js"' in body


def test_app_js_declares_all_management_views():
    status, _, body = route("GET", "/static/app.js")
    assert status == 200
    for view in ("dashboard", "projects", "tasks", "agents", "runs", "costs", "approvals", "activity"):
        assert view in body
```

- [ ] **Step 2: Run the static tests and verify RED**

Run: `pytest tests/test_server.py -q -k "index or static or app_js"`

Expected: 404 for `index.html` and `app.js`.

- [ ] **Step 3: Create the semantic application shell**

```html
<div class="app-shell">
  <header class="app-header">
    <div class="brand-block">
      <span class="network-mark">H2L-FORGE / OPS</span>
      <h1>하데스 콘솔</h1>
      <p class="brand-subtitle">프로젝트와 에이전트 실행을 한 곳에서 통제합니다.</p>
    </div>
  </header>
  <section class="sync-rail" aria-label="운영 상태"></section>
  <nav class="primary-nav" aria-label="콘솔 보기"></nav>
  <main id="view-root" class="view-root" tabindex="-1"></main>
  <dialog id="action-dialog"></dialog>
  <div id="toast" class="toast" role="status" aria-live="polite"></div>
</div>
```

Include a visible “repository summaries + demo operations data” notice.

- [ ] **Step 4: Implement rendering and mutation actions**

```javascript
const views = {
  dashboard: renderDashboard,
  projects: renderProjects,
  tasks: renderTasks,
  agents: renderAgents,
  runs: renderRuns,
  costs: renderCosts,
  approvals: renderApprovals,
  activity: renderActivity,
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.message || payload.error || "요청에 실패했습니다.");
  return payload;
}
```

Escape all stored text before inserting HTML. Use event delegation for
`data-action` controls. Reload `/api/console` after every successful mutation
and preserve the active view.

- [ ] **Step 5: Add the operations-pulse design and responsive rules**

```css
.ops-pulse {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  border: 1px solid var(--line);
  background: var(--ink);
}

.pulse-step {
  position: relative;
  min-width: 0;
  padding: 14px;
  color: #f7faf8;
}

.pulse-step + .pulse-step::before {
  content: "";
  position: absolute;
  inset: 12px auto 12px 0;
  width: 1px;
  background: rgba(255, 255, 255, 0.22);
}
```

Add tables/cards/dialog styles, visible disabled controls, `prefers-reduced-motion`,
and mobile breakpoints that collapse the pulse and data grids.

- [ ] **Step 6: Verify frontend assets**

Run: `node --check static/app.js`

Expected: exit 0.

Run: `pytest tests/test_server.py -q -k "index or static or app_js"`

Expected: all static tests pass.

### Task 4: Documentation and repository integration

**Files:**

- Modify: `README.md`
- Modify: `harness.yaml`

**Interfaces:**

- Documents: server command, persisted state path, management capabilities,
  demo-data boundary, and validation commands.
- Registers: `console_store` as a management-plane module separate from the
  scientific runtime modules.

- [ ] **Step 1: Update README commands and scope**

Add:

```bash
# 하데스 콘솔 (기본 상태: artifacts/hades-console.json)
PYTHONPATH=src python3 -m h2l.server --host 127.0.0.1 --port 8765
```

Document project/task/agent/run/cost/approval/activity views and explicitly
state that the management plane does not perform scientific decisions.

- [ ] **Step 2: Update harness metadata**

Add:

```yaml
implementation:
  modules:
    console_store: "src/h2l/console_store.py"
    server: "src/h2l/server.py"
  console:
    static_shell: "static/index.html"
    client: "static/app.js"
    state_path: "artifacts/hades-console.json"
```

Record a decision that Paperclip patterns are adapted only for software
operations and remain isolated from scientific authority.

- [ ] **Step 3: Check documentation consistency**

Run:

```bash
rg -n "Hades|하데스|console_store|hades-console" README.md harness.yaml docs/superpowers
```

Expected: the design, plan, module, run command, and state path are present.

### Task 5: Full verification and review

**Files:**

- Review all modified files.

**Interfaces:**

- Proves: tests, syntax, compilation, legacy behavior, management behavior,
  visual rendering, and scope boundaries.

- [ ] **Step 1: Run focused store and server tests**

Run: `pytest tests/test_console_store.py tests/test_server.py -q -k "not real_socket"`

Expected: all selected tests pass.

- [ ] **Step 2: Run the full Python suite**

Run: `pytest -q`

Expected: all tests pass when local sockets are permitted. If the managed
sandbox denies `bind()`, rerun the same command with the approved elevated
socket permission and record both results.

- [ ] **Step 3: Run static and build checks**

Run: `node --check static/app.js`

Expected: exit 0.

Run: `python3 -m compileall -q src tests`

Expected: exit 0.

- [ ] **Step 4: Run CLI regression checks**

Run:

```bash
PYTHONPATH=src python3 -m h2l.cli run --evidence tests/fixtures/tyk2_ibd/normalized_evidence.json
```

Expected: the fixed replay still reports `REJECT` and
`molecule_eligible=false`.

Run:

```bash
PYTHONPATH=src python3 -m h2l.cli eval --cases evals/decision_cases.json --out artifacts/eval_report.json
```

Expected: command exits 0 and writes a deterministic evaluation report.

- [ ] **Step 5: Run browser smoke verification**

Start:

```bash
PYTHONPATH=src python3 -m h2l.server --host 127.0.0.1 --port 8765
```

Verify at 1440px and 390px widths:

- all eight navigation views render,
- the operations pulse remains readable,
- project/task/agent/approval actions update and persist,
- no horizontal page overflow at mobile width,
- focus is visible and the action dialog is keyboard operable,
- the demo-data notice remains visible.

- [ ] **Step 6: Review the diff and scope**

Run:

```bash
git diff --check
git status --short
git diff --stat
```

Confirm that no scientific decision module changed and no generated artifact is
tracked.

- [ ] **Step 7: Commit the integrated console**

```bash
git add README.md harness.yaml src/h2l/server.py static tests docs/superpowers
git commit -m "Give operators one durable console for agent work

Constraint: General software operations only; scientific authority remains unchanged
Rejected: Static-only dashboard | it could not manage ownership, spend, or approvals
Confidence: high
Scope-risk: moderate
Directive: Keep production auth and multi-process persistence out of this dependency-free MVP
Tested: pytest -q; node --check static/app.js; python3 -m compileall -q src tests
Not-tested: Production multi-user concurrency"
```
