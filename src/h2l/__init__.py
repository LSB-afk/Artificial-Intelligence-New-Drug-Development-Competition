"""H2L-Forge: evidence-critical drug-discovery decision harness.

Operating invariants are ported from the JB reference repository
(``LSB-afk/Search-for-AI-based-internal-regulations``):

- a versioned registry where a pending version never changes the current answer,
- an explicit approval gate between judgment and downstream action,
- snapshot-first offline replay so a tool outage reproduces the same decision,
- a read-only evaluation plane that can never mutate scientific state.

This package implements the decision plane only. Molecule scoring
(RDKit / ADMET-AI / RAscore) is deliberately out of scope until a target is
``MOLECULE_ELIGIBLE`` and the tools are version-pinned and smoke-tested.
"""

__all__ = [
    "registry",
    "state_machine",
    "replay",
    "eval_runner",
]

RULESET_VERSION = "v1"
