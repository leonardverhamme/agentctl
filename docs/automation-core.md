# automation-core Operator Guide

`automation-core` is the local, Postgres-backed automation surface under [`automation-core/README.md`](../automation-core/README.md). It combines the CRM bridge, the GitHub analytics jobs, and the approval console that the Codex automations run against.

For the system map, read [docs/automation-core-architecture.md](automation-core-architecture.md) first.

## What It Does

- polls Gmail with history-based incremental sync
- polls Google Calendar with sync tokens
- discovers GitHub repositories with `gh api`
- mirrors Git history under `automation-core/.data/github-mirrors/`
- writes CRM technical memory into Notion:
  - `Email Threads`
  - `Calendar Events`
  - `Automation Decisions`
  - `Meeting Notes`
- writes GitHub reporting into Notion when the GitHub data sources are configured:
  - `GitHub Repositories`
  - `GitHub Contributors`
  - weekly and monthly GitHub snapshots
  - `GitHub Engineering Briefs`
- keeps Postgres as the local system of record for bridge state and GitHub analytics tables
- exposes a local approval console and CLI for Codex automations

## System Boundaries

- Notion is the business system of record for CRM data and the reporting mirror for the curated GitHub summaries.
- Gmail and Calendar remain the external evidence sources.
- Local Supabase/Postgres stores operational bridge state, GitHub analytics facts, and rollups.
- `gh api` plus local git mirrors are the source of truth for GitHub analytics facts.
- Gmail labels are mirrors of approved state, not the primary authority.
- No auto-send and no auto-archive in v1.

## Required Configuration

Fill `automation-core/.env` with:

- `DATABASE_URL` pointing at the local Supabase/Postgres stack, which defaults to `postgresql://postgres:postgres@127.0.0.1:58322/postgres`
- Google OAuth credentials
- the Notion integration token
- the existing CRM data source IDs:
  - Accounts
  - Contacts
  - Opportunities
  - Interactions
  - Follow-ups
  - AI Briefs
- the hidden technical Notion data source IDs:
  - Email Threads
  - Calendar Events
  - Automation Decisions
  - Meeting Notes
- the GitHub reporting Notion data source IDs if you want the weekly mirror:
  - GitHub Repositories
  - GitHub Contributors
  - GitHub Weekly Repo Snapshots
  - GitHub Weekly Contributor Snapshots
  - GitHub Monthly Repo Snapshots
  - GitHub Engineering Briefs
- optional GitHub mirror filters:
  - `GITHUB_OWNER_FILTERS`
  - `GITHUB_REPO_EXCLUDE_PATTERNS`
- optional mirror path overrides:
  - `GITHUB_MIRROR_ROOT`

## Bootstrap Flow

1. Start the local Supabase/Postgres stack:

```powershell
supabase start
```

2. Install dependencies in `automation-core`.
3. Copy `.env.example` to `.env`.
4. Run the Notion schema bootstrap:

```powershell
npm run cli -- schema-bootstrap
```

5. Start the server with `npm run dev` or `docker compose -f compose.yaml up --build`.
6. Open `/auth/google/start` once to connect Gmail and Calendar.
7. Run the first sync pass:
   - `npm run cli -- job gmail-sync`
   - `npm run cli -- job calendar-sync`
   - `npm run cli -- job reconcile`
8. Run the GitHub ingest jobs:
   - `npm run cli -- job github-discover`
   - `npm run cli -- job github-backfill`
   - `npm run cli -- job github-sync`
   - `npm run cli -- job github-rollup`
   - `npm run cli -- job github-notion-sync`
   - `npm run cli -- job github-weekly-brief`

## Local UI

- The current web UI is the approval console at the root route.
- It shows the inbox, waiting, meeting, and blocked queues plus recent job runs.
- GitHub analytics currently runs through jobs and Postgres tables; the dedicated analytics dashboard views are still being wired in the app layer.

## Notion Data Sources

Existing business-facing sources remain in place:

- Accounts
- Contacts
- Opportunities
- Interactions
- Follow-ups
- AI Briefs

The bridge adds or expects hidden technical sources:

- Email Threads
- Calendar Events
- Automation Decisions
- Meeting Notes

The GitHub reporting mirror uses separate Notion data sources and only receives curated repo/contributor snapshots and weekly/monthly summaries.

## Codex Automation Entry Points

The Codex automations should call these CLI entrypoints from this repo:

- `npm --prefix automation-core run cli -- job gmail-sync`
- `npm --prefix automation-core run cli -- job calendar-sync`
- `npm --prefix automation-core run cli -- job reconcile`
- `npm --prefix automation-core run cli -- job meeting-wrap`
- `npm --prefix automation-core run cli -- job morning-brief`
- `npm --prefix automation-core run cli -- job weekly-plan`
- `npm --prefix automation-core run cli -- job weekly-review`
- `npm --prefix automation-core run cli -- job hygiene-sweep`
- `npm --prefix automation-core run cli -- job github-discover`
- `npm --prefix automation-core run cli -- job github-backfill`
- `npm --prefix automation-core run cli -- job github-sync`
- `npm --prefix automation-core run cli -- job github-rollup`
- `npm --prefix automation-core run cli -- job github-notion-sync`
- `npm --prefix automation-core run cli -- job github-weekly-brief`

## Current Scope Limits

- One Gmail account
- One primary Google Calendar
- Local/workstation runtime only
- No auto-send
- No auto-archive
- No public webhooks
- No separate analytics dashboard route yet in the web app

## Troubleshooting

- If Google auth is not connected yet, `/health` reports `googleConfigured: false` and sync jobs will fail until `/auth/google/start` is completed.
- If Notion is not configured, `/health` reports `notionConfigured: false`; schema bootstrap and brief-generation jobs will fail until the token and data source IDs are supplied.
- If the local Postgres stack is not running, the app will fail to connect to the default `DATABASE_URL` on `127.0.0.1:58322`.
- If Gmail history IDs or Calendar sync tokens expire, the bridge falls back to a bounded full sync and records that fallback in the job result.
