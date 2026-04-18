# automation-core

`automation-core` is the local Gmail + Google Calendar + Notion bridge that backs the Codex automation stack.

It provides:

- a local approval UI at `http://127.0.0.1:4313` when running through Docker
- a CLI for sync, reconcile, brief, and hygiene jobs
- a Docker runtime for workstation-local operation
- a local SQLite state store for OAuth tokens, sync cursors, decision cache, and job history

## Architecture

- `src/app.ts` exposes the local HTTP API and approval UI shell.
- `src/server.ts` starts the app and runs the startup catch-up pipeline.
- `src/jobs/index.ts` owns the sequential job contract used by Codex automations and the CLI.
- `src/services/gmail.ts` and `src/services/calendar.ts` perform incremental polling and mirror state into the local cache.
- `src/services/notion.ts` owns technical data-source bootstrap plus business-record writes.
- `src/services/reconcile.ts` converts synced evidence into approval proposals and approved business actions.
- `src/store.ts` keeps operational state only:
  - OAuth tokens
  - sync cursors
  - decision cache
  - suppression hints
  - job history

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

1. Copy `.env.example` to `.env` and fill in:
   - Google OAuth credentials
   - Notion integration token
   - your Notion data source IDs
2. Install dependencies:

```powershell
npm install
```

3. Bootstrap the Notion-side technical databases and additive fields:

```powershell
npm run cli -- schema-bootstrap
```

4. Start the local UI directly:

```powershell
npm run dev
```

5. Connect Gmail + Calendar by opening:

```text
http://localhost:3010/auth/google/start
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
npm run cli -- queue
npm run cli -- decision approve <decision-id> --override-read-gate
npm run cli -- decision reject <decision-id> --note "reason"
npm run cli -- decision snooze <decision-id> --snoozed-until 2026-04-19T09:00:00Z
```

## Codex automation mapping

These are the expected paused automations layered on top of the CLI:

- `Inbox Pipeline`
  - runs Gmail sync, Calendar sync, reconcile, and meeting-wrap sequentially
- `Morning Brief`
- `Weekly Plan`
- `Weekly Review`
- `Hygiene Sweep`

The current implementation intentionally keeps them paused until `.env`, Notion IDs, and Google OAuth are configured.

## Docker

```powershell
docker compose -f compose.yaml up --build
```

The app stores its SQLite database in `automation-core/.data/`.

The container definition is now hardened for local operation:

- `.dockerignore` trims the build context
- the image exposes a real `/health` healthcheck
- Compose runs with `restart: unless-stopped`
- Compose uses `init: true` so signal handling and shutdown are cleaner

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

- The current implementation uses Node 24's built-in `node:sqlite` runtime. On current Node releases that emits an experimental warning, but it avoids native-addon install failures on Windows and keeps local + Docker behavior aligned.
- Gmail labels are mirrored only after approval.
- Nothing auto-sends and nothing auto-archives in v1.
- The queue UI is intentionally approval-first and keeps unread inbound mail behind the soft read gate until a human reads or explicitly overrides it.
