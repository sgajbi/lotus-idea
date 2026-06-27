# Lotus Idea Outbox Event Contract

This folder contains the repo-owned internal outbox event publication contract for
`lotus-idea`.

The contract is intentionally not a supported feature declaration. It defines the
source-owned event envelope, event families, payload safety rules, and remaining
certification blockers required before `lotus-idea` can claim platform mesh event
publication.

Validate it with:

```powershell
make outbox-event-contract-gate
```

