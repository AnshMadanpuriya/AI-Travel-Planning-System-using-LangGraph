# Security policy

## API keys and local configuration

- Keep all real credentials in `.env`; the file is ignored by Git.
- Commit only `.env.example` with placeholder values.
- Never paste API keys into issues, screenshots, logs, or travel-plan downloads.
- Use separate development keys with provider-side usage limits whenever possible.

## Previously committed credentials

This repository previously tracked an `.env` file. Removing it from the current branch does not
remove its old contents from Git history. Treat every credential that appeared there as exposed:

1. Revoke each old API key and database password in the relevant provider dashboard.
2. Generate fresh credentials.
3. Store the replacements only in your local `.env` file.
4. Review provider usage logs for unexpected activity.

Key rotation is required even if the repository is later made private or its history is rewritten.

## Reporting a vulnerability

Do not open a public issue containing secrets or exploitable details. Contact the repository owner
privately with a concise description, affected component, reproduction steps, and suggested fix.

