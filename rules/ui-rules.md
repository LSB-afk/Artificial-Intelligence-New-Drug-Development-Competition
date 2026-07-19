# UI Rules

## Decision Transparency

Every target or molecule judgment must show:

- current state and run mode,
- evidence IDs/links and snapshot date,
- supporting, contradicting, and missing evidence,
- rule or gate applied,
- uncertainty/limitation,
- recommended next action,
- reviewer/approval state,
- audit/replay status.

Display a concise decision trace. Never request, store, or reveal hidden chain-of-thought.

## Scientific Language

- Always label molecule evidence as `Measured`, `Predicted`, `Proxy`, or `Unknown`.
- Show the current indication beside drug approval/trial evidence.
- Show “Open Targets association score is not confidence” wherever that score drives ranking.
- `REJECT` is a valid scientific outcome, not a red system-error screen.
- `METHOD_ONLY` screens must show a persistent “no therapeutic claim” banner.

## States

- Empty states explain missing source, permission, snapshot, or positive target.
- Error states show whether retry, cache fallback, hold, or reviewer action is available.
- Stale snapshots show observation date and refresh status.
- High-risk actions use an explicit approval state and cannot look like ordinary one-click actions.
- A `HOLD`/`REJECT` target must not expose an enabled molecule-optimization action.

## Required Demo Panels

- Run manifest/budget
- Claim/evidence ledger
- Decision card
- Tool/fallback timeline
- Candidate/failure table when eligible
- Approval and safety state
- Eval case result
