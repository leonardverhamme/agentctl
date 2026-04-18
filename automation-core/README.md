# automation-core

`automation-core` is the local Gmail + Google Calendar + Notion bridge that backs the Codex automation stack.

It provides:

- a local approval UI at `http://localhost:3010`
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

4. Start the local UI:

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

## Notes

- The current implementation uses Node 24's built-in `node:sqlite` runtime. On current Node releases that emits an experimental warning, but it avoids native-addon install failures on Windows and keeps local + Docker behavior aligned.
- Gmail labels are mirrored only after approval.
- Nothing auto-sends and nothing auto-archives in v1.
- The queue UI is intentionally approval-first and keeps unread inbound mail behind the soft read gate until a human reads or explicitly overrides it.
