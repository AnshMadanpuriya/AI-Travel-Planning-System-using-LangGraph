# Security policy

## Never commit credentials

Use `.env.example` only for variable names. Store real values in a local ignored `.env` file or the deployment provider's encrypted secret manager.

The five source repositories audited for this integration included committed `.env` files. Removing those files in a new commit does **not** remove their earlier contents from Git history. Treat every key that ever appeared there as compromised:

1. Revoke the old Groq, Tavily, AviationStack, OpenWeather, and database credentials in their provider dashboards.
2. Generate replacement credentials.
3. Store replacements only in local/deployment secret stores.
4. Consider cleaning old history with `git filter-repo` after coordinating with every collaborator; history rewriting is intentionally not performed by this integration PR.
5. Enable GitHub secret scanning and push protection where available.

## Application safeguards

- Server-side provider calls; keys are never sent to the browser.
- Input length, date, traveler, budget, and prompt-extraction guardrails.
- Provider timeouts and non-sensitive error messages.
- External research is explicitly treated as untrusted data.
- No booking, payment, email, or account action is performed automatically.
- Human approval is required before a plan is treated as final.
- Approved plans are owner-scoped with a one-way SHA-256 identity key; email addresses are not written to the plan table.
- SQL operations use prepared statements, and database constraints independently enforce traveler, budget, currency, mode, and revision invariants.
- Full plan snapshots pass cross-field server validation before storage and again when restored.

Report a vulnerability privately to the repository owner. Do not open a public issue containing a key, exploit payload, or personal travel data.
