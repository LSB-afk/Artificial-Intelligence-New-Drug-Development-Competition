# Import / Export Rules

## Import Groups

1. Python standard library,
2. framework/runtime,
3. third-party chemistry/model packages,
4. internal public package APIs,
5. relative module imports.

## Planned Package Boundaries

```text
h2l_forge.domain        # entities, enums, transitions; no network/model imports
h2l_forge.sources       # Open Targets/ChEMBL/clinical/literature adapters
h2l_forge.chemistry     # RDKit, ADMET, activity, synthesis verification
h2l_forge.agents        # typed role orchestration; depends on domain/public ports
h2l_forge.audit         # event/artifact/report rendering
h2l_forge.evals         # read-only runners and failure injection
```

## Boundary Rules

- Domain/state code must not import LLM, UI, network, or chemistry implementations.
- Source adapters return normalized typed records; raw provider payloads do not leak into agents.
- LLM code cannot call RDKit/model internals directly; it uses typed tool ports.
- Evaluation code is read-only and cannot import mutation/approval commands.
- Report rendering cannot create new scientific claims; it reads committed records.
- No hidden network or filesystem side effect on import.
- Export only public ports/types through package `__init__` files.
- No circular dependency between agents and evaluation.

## Completion Gate

A feature is incomplete if it crosses a boundary through an internal import, bypasses the state engine, or makes a network/model call without a tool event.
