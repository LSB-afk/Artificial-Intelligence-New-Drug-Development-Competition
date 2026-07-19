# Data Rules

## Classification Before Use

| Data Type | Examples | Allowed Use | External Transfer | Redaction/Tokenization | Retention |
|---|---|---|---|---|---|
| Public identifiers | MONDO, ChEMBL, DOI, trial IDs | Retrieval, report, eval | Allowed to allowlisted services | None | Versioned |
| Public source payload | API response/publication metadata | Evidence normalization and lawful fixtures | Only as permitted by source terms | Remove irrelevant fields | Per source terms |
| Molecular structure | Public/reference/generated SMILES | Local chemistry and allowed model/tool inference | Allowlisted tools only | Suppress unsafe route detail | Run/audit window |
| Model/tool telemetry | Prompt version, tool input hash, latency, response hash | Reproducibility and budget | Minimized provider data | Remove keys, tokens, local paths | Run/audit window |
| Human review record | Reviewer label, decision, rationale | Approval/audit | No external transfer by default | Use project pseudonym if public | Submission/audit window |
| Secrets/private data | API keys, unpublished compounds, PII | Not part of competition MVP | Blocked | Never log | None |

## Evidence Record Requirements

Each evidence record must include:

- source/service and record ID or URL,
- disease/indication context,
- query or request hash,
- observation/retrieval timestamp,
- response/content hash where lawful,
- release/model/tool version when available,
- stance toward a claim,
- cache/live/manual mode,
- validation status and uncertainty.

## Snapshot Policy

- Use pinned snapshots for deterministic demos and optional live refresh for freshness.
- Never describe cached data as a successful live call.
- If neither a valid live result nor an allowed snapshot exists, fail closed.
- Review source terms before committing raw snapshots. Prefer minimal lawful fixtures plus manifests/hashes.
- Broad ignored `data/raw` or `artifacts` paths do not count as versioned reproducibility evidence.

## Scientific Data Rules

- Open Targets association score is a ranking feature, not confidence.
- ChEMBL activity must retain assay, relation, type, unit, and target metadata.
- Separate measured, predicted, proxy, and unknown values at schema level.
- Do not impute unavailable ADMET/synthesis values in final reports.
- Generated candidates require canonical structure, parent lineage, tool version, and failure reason.

## Default Rules

- Do not send unpublished structures, PII, or secrets to an external model/API.
- Log source and transformation, not hidden model reasoning.
- Unknown permission, license, or redistribution status is blocked pending review.
- A source update never silently mutates a pinned run; create a new snapshot/version.
