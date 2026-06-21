# RFC-0002 Slice 17: Implementation Proof And Live Validation

Status: Planned

## Outcome

Prove the complete supported opportunity journey end to end.

## Required Work

1. Run repo-native checks and affected cross-repo gates.
2. Run canonical live validation through source APIs, `lotus-idea`, Gateway,
   Workbench, downstream conversion, report/render/archive where claimed, and
   AI fallback/provider paths.
3. Capture proof under non-git-tracked `output/` and summarize evidence in this
   slice file.
4. Critically review returned figures, statuses, reason codes, source refs,
   lineage refs, score, review state, AI posture, conversion outcome, and
   screenshots.

## Acceptance Gate

1. All proof gaps are fixed inside RFC-0002 or the supported claim is narrowed.
2. Evidence includes success, unsupported, degraded, denied, stale, duplicate,
   AI unavailable, and downstream failure paths.
3. GitHub checks and local gates are recorded with commit SHAs.
