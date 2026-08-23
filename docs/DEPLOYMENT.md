# Deployment runbook

The project has two supported deployment shapes.

## 1. Hosted edge web app

The root application is the production web experience. It contains its own LangGraph workflow and API routes:

Current production deployment: [AI Travel Agent System](https://ai-travel-agent-ansh.anshmadanpuriya16.chatgpt.site)

- `POST /api/plan`
- `POST /api/revise`
- `GET /api/health`
- `GET|POST /api/plans`
- `GET|DELETE /api/plans/:id`

Approved plans are stored in the platform-managed D1 database bound as `DB`. The generated migration under `drizzle/` creates constrained plan records and owner-scoped indexes. The hosting manifest declares only the logical binding; the deployment platform owns the physical database.

Set runtime environment variables in the hosting provider's secret manager. Never upload a local `.env` file.

Minimum live-AI configuration:

```text
GROQ_API_KEY=...
TRAVEL_AGENT_DEMO_MODE=false
```

Optional provider research:

```text
TAVILY_API_KEY=...
AVIATION_STACK_API_KEY=...
GROQ_MODEL=llama-3.3-70b-versatile
```

Without those values the deployed app deliberately remains useful in **safe preview mode**. It produces a deterministic budget and itinerary but clearly labels the result as non-live.

Open-Meteo's free endpoint is used for near-date forecasts in the hosted app. Its free service is for non-commercial use, requires attribution, and is limited to 10,000 calls/day. Use a customer plan or another licensed provider for commercial deployment: [Open-Meteo pricing](https://open-meteo.com/en/pricing).

## 2. Dockerized Python LangGraph app

Prerequisites: Docker Engine and Docker Compose v2.

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:8501`. Docker Compose starts:

- Streamlit + Python LangGraph + local FastMCP servers
- PostgreSQL 16 for resumable human-review checkpoints

For a live provider run, set `TRAVEL_AGENT_DEMO_MODE=false` and add keys to `.env` before starting the containers.

For a VPS, place the repository under `/opt/ai-travel-agent`, restrict `.env` to the service account, run the Compose stack behind Nginx or Caddy, and terminate HTTPS at the reverse proxy. Do not expose PostgreSQL publicly.

## Post-deployment verification

1. Open `/api/health`; expect HTTP 200 and `status: ok`.
2. Confirm `persistence.database` is `true`.
3. Create a 3–7 day trip and confirm all six workflow stages are displayed.
4. Confirm preview/live mode is visibly labeled.
5. Request a revision and verify the new draft reflects the feedback.
6. Approve the draft, refresh the page, and restore it from Saved trips.
7. Delete the saved draft and confirm it disappears from the history.
8. Test an invalid date range and a prompt/credential extraction request; both should return a safe validation error.
9. Confirm no API key appears in browser source, network response bodies, logs, or the repository.

## Rollback

- Hosted app: redeploy the previous immutable release.
- Docker: deploy the previous Git tag and run `docker compose up -d --build`.
- PostgreSQL data is kept in the `postgres_data` volume. Back it up before schema or infrastructure changes.
