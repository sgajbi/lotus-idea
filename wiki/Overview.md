# Overview

`lotus-idea` turns governed Lotus evidence into reviewable private-banking
opportunity ideas.

The target operating model is:

1. consume source-owned facts from Lotus domain services,
2. generate deterministic opportunity candidates,
3. attach source refs, freshness, reason codes, score, and evidence,
4. route candidates through human review,
5. convert approved ideas into advisory, portfolio-management, report, or
   Workbench workflows,
6. use AI only for bounded explanation assistance through `lotus-ai`.

Current posture: opportunity intelligence foundation implementation is in
progress. Current support:

1. repository scaffold,
2. service boundary ADRs,
3. full RFC-0002 implementation program,
4. source wiki,
5. planned supported-feature registry,
6. certified internal high-cash signal evaluation API foundation over
   caller-supplied, source-owned Core evidence,
7. certified internal candidate lifecycle, AI explanation evaluator, advisor
   explanation readiness, advisor queue, review-action, and feedback API foundations over persisted
   candidates,
8. bounded read-only Gateway publication for advisor queue and candidate
   detail,
9. certified internal aggregate implementation-proof readiness diagnostic for
   RFC-0002 blocker visibility.

No external business feature is supported yet. The high-cash, advisor queue,
lifecycle, AI explanation, AI explanation readiness, review-action, and
feedback API foundations are certified for internal contract evolution and
operator supportability diagnostics, and the first Gateway publication is
read-only integration foundation. The implementation-proof readiness diagnostic
reports blockers; it is not Workbench proof, data-product certification, AI
runtime proof, live implementation proof, or a client-demo feature claim.
