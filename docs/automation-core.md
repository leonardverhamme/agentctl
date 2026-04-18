# automation-core Operator Guide

This repo now contains a workstation-local automation stack under [`automation-core`](C:/Users/leona/Documents/Playground/agentctl/automation-core/README.md).

## What it does

- polls Gmail with history-based incremental sync
- polls Google Calendar with sync tokens
- writes technical memory into Notion:
  - `Email Threads`
  - `Calendar Events`
  - `Automation Decisions`
  - `Meeting Notes`
- keeps Notion as the business system of record
- exposes a local approval UI and CLI for Codex automations
- generates brief/review/audit pages into `AI Briefs`

## System boundaries

- Notion is the business system of record.
- Gmail and Calendar remain the external evidence sources.
- Local SQLite stores only operational bridge state and secrets.
- Gmail labels are mirrors of approved Notion state, not the primary authority.

## Required configuration

Fill `automation-core/.env` with:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`
- `NOTION_TOKEN`
- all existing CRM data source IDs:
  - Accounts
  - Contacts
  - Opportunities
  - Interactions
  - Follow-ups
  - AI Briefs
- a parent page ID for technical data sources if they do not exist yet

## Bootstrap flow

1. Run `npm install` in `automation-core`.
2. Copy `.env.example` to `.env`.
3. Run `npm run cli -- schema-bootstrap`.
4. Start the server with `npm run dev` or `docker compose -f compose.yaml up --build`.
5. Open `/auth/google/start` once to connect Gmail and Calendar.
6. Run the first sync pass:
   - `npm run cli -- job gmail-sync`
   - `npm run cli -- job calendar-sync`
   - `npm run cli -- job reconcile`

## Notion data sources

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

The schema bootstrap command also applies additive fields to the CRM-facing sources for deterministic external IDs and sync provenance.

## Approval model

- The local UI is the primary approval surface.
- Unread inbound mail stays behind a soft read gate.
- Approving a decision updates Notion first and only then mirrors Gmail labels.
- Rejecting a decision records the outcome and can add a local suppression hint.
- Snoozing a decision keeps it in the queue with a future timestamp.

## Local UI screens

- Inbox approval queue
- Waiting queue
- Meeting follow-up queue
- Stale / low-confidence queue
- Daily overview based on recent job runs

## Codex automation entrypoints

The Codex automations should call these CLI entrypoints from this repo:

- `npm --prefix automation-core run cli -- job gmail-sync`
- `npm --prefix automation-core run cli -- job calendar-sync`
- `npm --prefix automation-core run cli -- job reconcile`
- `npm --prefix automation-core run cli -- job meeting-wrap`
- `npm --prefix automation-core run cli -- job morning-brief`
- `npm --prefix automation-core run cli -- job weekly-plan`
- `npm --prefix automation-core run cli -- job weekly-review`
- `npm --prefix automation-core run cli -- job hygiene-sweep`

## Current scope limits

- One Gmail account
- One primary Google Calendar
- Local/workstation runtime only
- No auto-send
- No auto-archive
- No public webhooks

## Troubleshooting

- If Google auth is not connected yet, `/health` reports `googleConfigured: false` and sync jobs will fail until `/auth/google/start` is completed.
- If Notion is not configured, `/health` reports `notionConfigured: false`; schema bootstrap and brief-generation jobs will fail until the token and data source IDs are supplied.
- If Gmail history IDs or Calendar sync tokens expire, the bridge falls back to a bounded full sync and records that fallback in the job result.
