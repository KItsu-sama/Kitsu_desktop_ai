# TODO.md

## Task: “how are you” (direct style) should return the whole system state

- [x] Create early-match handler module subscribed to `INPUT_RECEIVED` for phrases.
- [x] Intercept only when emotion/style is `direct`.
- [x] Emit `RESPONSE_READY` with a formatted snapshot of orchestrator/emotion/resources.
- [ ] (Optional) Update snapshot to include more precise budget/resource fields if available.


