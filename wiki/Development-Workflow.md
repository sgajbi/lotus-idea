# Development Workflow

`lotus-idea` follows the Lotus rebase-only delivery model.

Required workflow:

1. start from current `main`,
2. run stranded-truth reconciliation for RFC, docs, wiki, context, contract, supported-feature, or
   CI workflow changes,
3. keep commits small, meaningful, and truthful,
4. update code, tests, endpoint certification, supported features, README, wiki, RFC evidence, and
   repository context in the same slice when implementation truth changes,
5. use rebase-only PR completion,
6. do not squash RFC or implementation commits,
7. publish wiki source after merge when wiki truth changes,
8. delete completed local and remote feature branches after merge.

RFC-0002 implementation slices must record branch, PR, commit, CI, proof directory, wiki decision,
and branch-cleanup evidence before closure. No supported product claim may depend on a side branch,
WTBD ledger, or unpublished wiki change.
