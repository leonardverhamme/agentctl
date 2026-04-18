# Agentctl Skill Governance

Use this guide when creating or changing skills in the `agentctl` bundle.

## Purpose

The goal is not "more skills." The goal is a capability-first surface that stays easy for agents to navigate, shows visible skill usage in chat, and does not waste context on duplicated logic.

## Core Rule

Every meaningful top-level capability may have one thin local skill front door.

That does **not** mean every raw CLI command, every MCP method, or every plugin subskill should become a new local wrapper skill.

Good:

- one skill for a capability such as GitHub, browser automation, Supabase, or research
- one workflow skill such as UI, test, docs, refactor, or CI/CD

Bad:

- one skill per single raw command
- one skill per tiny variant when `agentctl capability <key>` already explains the route
- multiple local skills that restate the same routing logic

## The Shape Of A Good Agentctl Skill

A local `agentctl` skill should usually be:

- thin
- navigation-first
- capability-first
- stable

Default pattern:

1. identify the capability
2. run `agentctl capability <key>`
3. read the generated capability page
4. switch to the healthiest authoritative path

Most local capability skills should be short wrappers, not large manuals.

## What Lives Where

Use the following split consistently:

- `agentctl` code owns routing, health, status, machine-readable state, and generated docs
- local capability skills own the visible front door and a small amount of navigation guidance
- vendor CLIs, Playwright, plugin skills, and MCP servers remain authoritative for real work
- detailed docs belong in `docs/agentctl/` or generated capability pages, not inside every skill

## Context Budget Rules

Treat context as scarce.

- Keep `SKILL.md` bodies short and procedural.
- Put only the minimum route-selection guidance in the skill itself.
- Prefer `agentctl capability <key>` and generated docs for details.
- Use `references/` only when there is real variant-specific material that should not sit in the main skill body.
- Do not duplicate long explanations across multiple skills.
- Do not add filler sections just because a skill exists.

## Required Files

Every managed local skill should have:

- `SKILL.md`
- `agents/openai.yaml`

Use `agents/openai.yaml` for the visible display name, short description, and default prompt that make the skill usable in Codex surfaces.

## Script Rules

If a skill needs deterministic helper code:

- reusable bundle-owned scripts may live in the bundle only when they are truly part of the control plane
- task-specific helper scripts created during user work must go in the target repo, not in `$CODEX_HOME`, not in `skills/`, and not in plugin skill folders

Do not turn every repeated task into a new bundle script automatically.

## Stability Rules

- Treat `skills/` and `plugins/*/skills/` as stable infrastructure.
- Do not change them during normal task execution.
- Use `$skill-edit-mode` for intentional skill work only after explicit user confirmation.
- Keep the change set narrow to the confirmed skills.

## Creation And Update Workflow

When adding or changing a managed local skill:

1. use `$skill-edit-mode`
2. use `$skill-creator` when you need structure or validation guidance
3. create or update `SKILL.md`
4. create or refresh `agents/openai.yaml`
5. if it is a capability-front-door skill, wire it into `agentctl/lib/capabilities.py`
6. regenerate docs with `agentctl maintenance audit`
7. validate every changed skill with `quick_validate.py`
8. run repo tests
9. sync the installed bundle if this repo mirrors the live `CODEX_HOME`

## What Must Be Updated When A Skill Changes

Depending on the change, update:

- `agentctl/lib/capabilities.py`
- `AGENTS.md`
- `docs/agentctl/overview.md` via maintenance audit
- generated capability pages via maintenance audit
- `README.md` when the public navigation story changes
- this guide when the skill-governance contract itself changes

## Decision Rule For New Skills

Before adding a new local skill, ask:

1. Is this a real top-level capability or workflow?
2. Would a purple skill chip materially improve navigation or user trust?
3. Is the skill a thin front door, not a duplicate runtime?
4. Can the same outcome be achieved by improving an existing capability skill instead?

If the answer to 4 is yes, prefer improving the existing skill instead of creating another one.

## The Desired End State

Agents should be able to:

- start from a small set of obvious skills
- drill down through `agentctl capability <key>`
- avoid transport-level reasoning unless a capability is degraded
- keep their context focused on the task, not on a giant skill catalog

That is the standard for new skill work in this repo.
