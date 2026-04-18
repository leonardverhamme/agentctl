---
name: android-testing-capability
description: Navigate the Android testing capability in agentctl. Use when the task is about Android emulator QA, reproduction, screenshots, or log-driven debugging.
---

# Android Testing Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for Android QA. The actual runbook remains the Test Android Apps plugin skill.

## Workflow

1. Run `agentctl capability android-testing`.
2. Read the generated page at `docs/agentctl/capabilities/android-testing.md`.
3. Route into `$test-android-apps:android-emulator-qa` for the actual emulator workflow.

## Do Not Do

- Do not duplicate Android emulator procedures in this skill.
- Do not skip the capability page when auth, environment, or overlap is unclear.
