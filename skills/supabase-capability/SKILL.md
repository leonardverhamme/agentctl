---
name: supabase-capability
description: Navigate the Supabase capability in agentctl. Use when the task is about local Supabase development, migrations, local stack management, CI/CD setup, or deciding between Supabase CLI and Supabase MCP.
---

# Supabase Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for Supabase work. Supabase is CLI-first here: prefer the Supabase CLI for local stacks, schema, migrations, and CI/CD, and use MCP when structured project access adds value beyond the CLI.

## Workflow

1. Run `agentctl capability supabase-data`.
2. Read the generated page at `docs/agentctl/capabilities/supabase-data.md`.
3. Prefer `supabase init` and `supabase start` for local development and stack bring-up.
4. Use Supabase MCP when the task needs structured project or platform access that the CLI path does not expose cleanly.

## Rules

- Do not recommend `npm install -g supabase`; it is not the supported global install path.
- Prefer Scoop, Homebrew, standalone binaries, or `npx supabase`.
- If using `npx supabase`, require Node.js 20 or later.
- Local Supabase development expects a Docker-compatible container runtime.

## Do Not Do

- Do not treat Supabase MCP as mandatory when the CLI already covers the task.
- Do not duplicate Supabase operational logic in this skill.

