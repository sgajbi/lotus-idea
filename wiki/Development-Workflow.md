# Development Workflow

`lotus-idea` follows the Lotus rebase-only delivery model.

Required workflow:

1. start from current `main`,
2. run stranded-truth reconciliation for RFC, docs, wiki, context, contract, supported-feature, or
   CI workflow changes,
3. keep commits small, meaningful, and truthful,
4. update code, tests, endpoint certification, supported features, README, wiki, RFC evidence, and
   repository context in the same slice when implementation truth changes,
5. keep durable docs passing `make documentation-contract-gate` so required
   README, repository context, quality, evidence, and wiki surfaces remain
   substantive,
6. keep the bank-buyable control matrix passing `make quality-scorecard-gate`
   so scorecard evidence, gaps, and next slices match current implementation,
7. keep current-state docs passing `make implementation-truth-gate` so demo or production claims
   never outrun supported-feature evidence,
8. use rebase-only PR completion,
9. do not squash RFC or implementation commits,
10. publish wiki source after merge when wiki truth changes,
11. delete completed local and remote feature branches after merge.

RFC-0002 implementation slices must record branch, PR, commit, CI, proof directory, wiki decision,
and branch-cleanup evidence before closure. No supported product claim may depend on a side branch,
WTBD ledger, or unpublished wiki change.

For partial RFC PRs, link GitHub issues without auto-close keywords. The PR and
issue comment should say `Keep #<issue> open` and name the remaining evidence
class until exact-main validation and QA-backed closure are ready. Run
`make rfc0002-github-issue-execution-ledger-gate` when updating RFC-0002
issue-tracking truth.
