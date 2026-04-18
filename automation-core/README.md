# automation-core

`automation-core` is the local Gmail + Google Calendar + Notion bridge and GitHub analytics workspace that runs inside this repo.

It provides:

- a local approval console at `http://127.0.0.1:4313` when running through Docker
- a CLI for sync, reconcile, brief, hygiene, and GitHub analytics jobs
- a Docker runtime for workstation-local operation
- a local Supabase/Postgres runtime at `127.0.0.1:58322`
- a Notion reporting mirror for CRM and GitHub weekly snapshots
- GitHub repo intelligence ingest backed by `gh api` plus local git mirrors

## Architecture

- `src/app.ts` exposes the local HTTP API and approval console shell.
- `src/server.ts` starts the app and runs the startup catch-up pipeline.
- `src/jobs/index.ts` owns the sequential job contract used by Codex automations and the CLI.
- `src/services/gmail.ts` and `src/services/calendar.ts` perform incremental polling and mirror state into the local cache.
- `src/services/github-analytics.ts` discovers repositories, maintains git mirrors, computes rollups, and syncs curated GitHub reporting into Notion when configured.
- `src/services/notion.ts` owns technical data-source bootstrap plus business-record and reporting writes.
- `src/store.ts` persists operational state and the GitHub analytics tables in the local Postgres database.
- `supabase/migrations/` defines the local schema for bridge state, job history, and `github_*` analytics tables.

The current web UI is still the operator console. GitHub analytics is exposed through jobs, the local Postgres tables, and optional Notion reporting until the dedicated dashboard views are wired in.

## HTTP API

- `GET /health`
- `GET /queue`
- `GET /auth/google/start`
- `GET /auth/google/callback`
- `POST /jobs/:jobName`
- `POST /decisions/:decisionId/approve`
- `POST /decisions/:decisionId/reject`
- `POST /decisions/:decisionId/snooze`
- `POST /schema/bootstrap`

## Quick start

1. Start the local Supabase stack if it is not already running:

```powershell
supabase start
```

2. Install dependencies:

```powershell
npm install
```

3. Copy `.env.example` to `.env` and fill in:

- Google OAuth credentials
- Notion integration token and data source IDs
- any GitHub mirror filters or optional Notion GitHub reporting IDs

4. Bootstrap the Notion-side technical databases and additive CRM fields:

```powershell
npm run cli -- schema-bootstrap
```

5. Start the local UI directly:

```powershell
npm run dev
```

6. Connect Gmail + Calendar by opening:

```text
http://localhost:3010/auth/google/start
```

7. Run the first sync and GitHub analytics pass:

```powershell
npm run cli -- job gmail-sync
npm run cli -- job calendar-sync
npm run cli -- job reconcile
npm run cli -- job github-discover
npm run cli -- job github-backfill
npm run cli -- job github-sync
```

## Core commands

```powershell
npm run cli -- health
npm run cli -- job gmail-sync
npm run cli -- job calendar-sync
npm run cli -- job reconcile
npm run cli -- job meeting-wrap
npm run cli -- job morning-brief
npm run cli -- job weekly-plan
npm run cli -- job weekly-review
npm run cli -- job hygiene-sweep
npm run cli -- job github-discover
npm run cli -- job github-backfill
npm run cli -- job github-sync
npm run cli -- job github-rollup
npm run cli -- job github-notion-sync
npm run cli -- job github-weekly-brief
npm run cli -- queue
npm run cli -- decision approve <decision-id> --override-read-gate
npm run cli -- decision reject <decision-id> --note "reason"
npm run cli -- decision snooze <decision-id> --snoozed-until 2026-04-19T09:00:00Z
```

## GitHub analytics flow

- Discover visible repositories with `gh api`.
- Mirror repository history under `automation-core/.data/github-mirrors/<owner>/<repo>.git`.
- Compute repo and contributor rollups in local Postgres from git history plus GitHub API facts.
- Mirror curated repo/contributor snapshots and weekly reports into Notion only when the Notion GitHub data sources are configured.

## Docker

```powershell
docker compose -f compose.yaml up --build
```

The app stores its data in the local Postgres database that Supabase exposes on `127.0.0.1:58322`.

The Docker route binds the container's internal `3010` port to host port `4313` by default.

If you want a different host-side port, override it:

```powershell
$env:HOST_PORT = "4410"
docker compose -f compose.yaml up --build
```

## Availability posture

Today `automation-core` is an always-on local containerized backend that also serves its operator UI.

That means:

- it is a good fit for Docker on your workstation, a mini PC, or a VPS
- it is not a good fit for Vercel Functions as-is because the app keeps local state, runs startup catch-up logic, and is designed as a long-lived process

If you want a stronger architecture, the best split is:

- Vercel-hosted frontend for the polished operator shell
- always-on container host for `automation-core`
- HTTPS reverse proxy in front of the container host
- the frontend talking to the backend through a stable public API origin

Running the frontend on Vercel while the backend stays only on your laptop is not truly stable or generally available. For that setup to work reliably, the backend needs to live on an always-on reachable host or behind a durable tunnel/private network.

## Windows startup

To make `automation-core` come up automatically whenever your computer starts and you log in, install the bundled startup launcher:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\scripts\install-startup.ps1
```

That writes a launcher into your Windows Startup folder so the Docker container is brought up automatically on login. The launcher:

- waits for Docker to become ready
- runs `docker compose up -d`
- polls `/health` until the backend is ready
- writes startup logs to `output/startup/automation-core-startup.log`

The paired scripts are:

- `scripts/start-automation-core.ps1`
- `scripts/install-startup.ps1`
- `scripts/remove-startup.ps1`

Once installed, the standard Docker-backed local URL is:

```text
http://127.0.0.1:4313/
```

## Notes

- The current implementation uses the local Supabase/Postgres stack as the persistence layer.
- Gmail labels are mirrored only after approval.
- Nothing auto-sends and nothing auto-archives in v1.
- The queue UI is intentionally approval-first and keeps unread inbound mail behind the soft read gate until a human reads or explicitly overrides it.
