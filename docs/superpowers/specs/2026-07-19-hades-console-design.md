# Hades Console Design

## Context

At design start, the repository was clean at local commit `5c0a1a6`, one
commit ahead of `origin/main` (`25c622e`) after a fresh fetch on 2026-07-19.
That local commit contained a deterministic decision harness, a stdlib HTTP
server, and the CSS for a read-only console. The HTML and JavaScript
application files were missing. The baseline test run had 49 tests: 46 passed,
two failed because the static shell was missing, and one socket test was
blocked by the execution sandbox.

This design adds a general software-operations control plane. It does not make
biological decisions, generate or optimize molecules, design synthesis routes,
write experimental protocols, or make clinical judgments.

## Design Goal

Build a compact Paperclip-inspired console that lets the project team inspect
and manage projects, tasks, AI agents, execution records, costs, approval
states, and an append-only activity trail without replacing the existing
scientific decision core or adding runtime dependencies.

## Constraints

- Preserve the current `registry`, `state_machine`, `replay`, and
  `eval_runner` behavior.
- Use Python standard library and static HTML/CSS/JavaScript only.
- Store management state durably and atomically in a JSON file under the
  ignored `artifacts/` directory by default.
- Seed the console only from repository summaries, existing agent-role
  definitions, existing fixed replay/eval cases, and clearly labeled demo
  operations data.
- Do not expose hidden chain-of-thought. Execution records contain concise
  events, results, errors, and next actions.
- High-risk operational actions remain durable approval records.
- All mutation endpoints validate input, enforce state transitions, and append
  an activity event.

## Approaches Considered

### A. Finish the static read-only console

Add the missing `index.html` and `app.js`, render the existing `/api/*`
responses, and stop there.

- Advantages: smallest change; closes the two known static-file failures.
- Disadvantages: does not manage projects, tasks, agents, costs, runs, or
  approvals; fails the core request.

### B. Add an in-memory management plane

Extend `server.py` with seeded dictionaries and mutation endpoints.

- Advantages: simple; no persistence format.
- Disadvantages: all user actions disappear on restart; audit history is not
  durable; server responsibilities become tangled.

### C. Add a JSON-backed management plane

Create a focused `HadesConsoleStore`, keep it separate from the scientific
registry, expose a small REST-like API through the existing server, and add a
static single-page UI.

- Advantages: durable, dependency-free, testable, reversible, and consistent
  with the repository's snapshot-first/atomic-write operating invariants.
- Disadvantages: single-process storage only; not a production multi-user
  database.

Approach C is selected. It delivers the requested management surface while
keeping scope and dependency risk low.

## Paperclip Patterns Adapted

Paperclip's official implementation separates projects, issues, agents,
heartbeat runs, cost events, approvals, and activity records. The Hades Console
adapts the following patterns:

- `Project` provides the work boundary.
- `Task` is the user-facing unit of work.
- `Run` is separate from `Task` so retries and execution history remain
  auditable.
- Task checkout is atomic and returns a conflict when another active agent owns
  the task.
- `CostEvent` attributes usage to an agent, task, project, and run.
- Per-agent budget utilization is visible; 80% is a warning and 100% is a
  blocked/paused condition.
- `Approval` has a durable lifecycle:
  `pending -> approved | rejected | revision_requested`.
- `ActivityEvent` is append-only and records the actor, action, entity, time,
  and concise details.

The full Paperclip company/org-chart/plugin system is intentionally not copied.
This repository needs one project workspace and a small operational control
plane, not a multi-tenant business platform.

## Architecture

```text
static/index.html + static/app.js
              |
              v
        src/h2l/server.py
        /api/console/*
              |
              v
   src/h2l/console_store.py
              |
              v
 artifacts/hades-console.json

Existing read-only decision APIs
        /api/status, /api/decision, /api/eval, ...
              |
              v
 registry.py / replay.py / eval_runner.py
```

The management plane and scientific plane share the HTTP process but not
mutable state. Console actions cannot change evidence snapshots, target
decisions, molecule eligibility, or evaluation outputs.

## Data Model

### Project

Fields: `id`, `name`, `description`, `status`, `goal`, `target_date`,
`lead_agent_id`, `color`, `created_at`, `updated_at`.

Valid status values: `planned`, `active`, `paused`, `completed`, `cancelled`.

### Task

Fields: `id`, `project_id`, `title`, `description`, `status`, `priority`,
`assignee_agent_id`, `checkout_run_id`, `labels`, `created_at`, `updated_at`,
`started_at`, `completed_at`.

Lifecycle:

```text
backlog -> todo -> in_progress -> in_review -> done
                    |              |
                 blocked       in_progress
```

`in_progress` requires an assigned agent. Checkout accepts expected statuses
and atomically assigns the task. A checkout conflict returns HTTP 409.

### Agent

Fields: `id`, `name`, `role`, `title`, `status`, `capabilities`,
`reports_to`, `budget_monthly_cents`, `spent_monthly_cents`,
`last_heartbeat_at`, `pause_reason`, `created_at`, `updated_at`.

Valid status values: `idle`, `running`, `paused`, `error`, `terminated`.
The UI supports reversible pause/resume actions; termination is outside this
MVP.

### Run

Fields: `id`, `task_id`, `project_id`, `agent_id`, `status`,
`invocation_source`, `started_at`, `finished_at`, `duration_ms`, `result`,
`error`, `next_action`, `usage`, `cost_cents`, `log`.

Valid status values: `queued`, `running`, `succeeded`, `failed`, `cancelled`.
Run logs contain concise operational events, never hidden reasoning.

### CostEvent

Fields: `id`, `agent_id`, `task_id`, `project_id`, `run_id`, `provider`,
`model`, `input_tokens`, `cached_input_tokens`, `output_tokens`,
`cost_cents`, `occurred_at`.

The API returns overall utilization plus breakdowns by agent and project.

### Approval

Fields: `id`, `type`, `title`, `status`, `requested_by`, `payload`,
`decision_note`, `decided_by`, `decided_at`, `created_at`, `updated_at`.

Only pending approvals accept approve, reject, or request-revision actions.
The initial demo approvals cover deployment, budget, and agent scheduling, not
scientific progression.

### ActivityEvent

Fields: `id`, `actor_type`, `actor_id`, `action`, `entity_type`, `entity_id`,
`run_id`, `details`, `created_at`.

Events are appended for project/task mutations, checkout/release, agent
pause/resume, approval decisions, and run retry creation.

## HTTP API

Read endpoints:

- `GET /api/console` — complete management snapshot and derived overview.
- `GET /api/projects`
- `GET /api/tasks`
- `GET /api/agents`
- `GET /api/runs`
- `GET /api/costs`
- `GET /api/approvals`
- `GET /api/activity`

Mutation endpoints:

- `POST /api/projects`
- `PATCH /api/projects/{project_id}`
- `POST /api/tasks`
- `PATCH /api/tasks/{task_id}`
- `POST /api/tasks/{task_id}/checkout`
- `POST /api/tasks/{task_id}/release`
- `POST /api/agents/{agent_id}/pause`
- `POST /api/agents/{agent_id}/resume`
- `POST /api/runs/{run_id}/retry`
- `POST /api/approvals/{approval_id}/approve`
- `POST /api/approvals/{approval_id}/reject`
- `POST /api/approvals/{approval_id}/request-revision`

Responses use structured JSON errors with `error`, `message`, and optional
`details`. Invalid JSON returns 400, missing records return 404, illegal state
transitions return 409, and unsupported methods return 405.

## User Interface

The application keeps the existing light operational palette and Korean UI
copy. It uses the existing system sans face for readable Korean text and a
monospace utility face for identifiers, timestamps, and spend.

The visual signature is an **operations pulse**: a linked horizontal strip
showing project, task, agent, run, cost, and approval state as one control
sequence. It is structural rather than decorative and helps reviewers follow
how work becomes execution, spend, and a governed decision.

Primary views:

- Dashboard — operations pulse, attention queue, current runs, and recent
  activity.
- Projects — project goal, status, dates, lead, and status controls.
- Tasks — filterable queue, assignee, priority, lifecycle controls, and task
  creation.
- Agents — role, current status, last heartbeat, budget utilization, and
  pause/resume.
- Runs — execution status, task/agent, timestamps, usage, cost, concise log,
  and retry action for failed runs.
- Costs — total utilization, spend by agent/project, and event ledger.
- Approvals — pending/recent operational approvals with decision notes.
- Activity — append-only event timeline.

The UI has visible keyboard focus, mobile layouts, reduced-motion support,
clear empty/error states, and a reload action. Demo data is labeled throughout.

## Persistence and Concurrency

The store holds a process-local reentrant lock. Every mutation:

1. Reloads the current JSON document.
2. Validates the requested transition.
3. Mutates the entity and appends one activity event.
4. Writes to a sibling temporary file.
5. Atomically replaces the state file.

This protects a single server process from concurrent request races and avoids
partially written files. Multi-process locking and user authentication are
future production work.

## Testing

- Store tests cover seeding, persistence, atomic task checkout conflict,
  status validation, agent pause/resume, approval lifecycle, run retry, cost
  aggregation, and append-only activity.
- Server tests cover read endpoints, mutation endpoints, structured errors,
  JSON request parsing, and backward compatibility with existing decision APIs.
- Static tests verify the required application shell and JavaScript asset.
- JavaScript syntax is checked with `node --check`.
- Python sources are compiled with `python3 -m compileall`.
- The full pytest suite and a real HTTP smoke test are run after implementation.

## Non-Goals

- No production authentication or multi-tenant isolation.
- No background worker scheduler or real provider invocation.
- No model/provider secret management.
- No scientific approval decisions.
- No molecule generation, optimization, synthesis, experiment, or clinical
  workflow.
- No changes to existing scientific decision outcomes.

## Acceptance Criteria

- A user can create and update projects and tasks.
- A user can atomically check out/release a task and see ownership conflicts.
- A user can pause/resume an agent and inspect its budget use.
- A user can inspect run history and create a queued retry record.
- A user can inspect cost totals and attribution.
- A user can approve, reject, or request revision for an operational approval.
- Every mutation appears in the activity trail and survives store reload.
- The existing scientific read-only endpoints keep their current behavior.
- All repository tests pass in an environment that permits local sockets; all
  non-socket tests pass in the managed sandbox.
