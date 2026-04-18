---
name: macos-development-capability
description: Navigate the macOS development capability in agentctl. Use when the task is about macOS builds, packaging, desktop debugging, or SwiftUI/AppKit work.
---

# macOS Development Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for macOS work. The actual implementation and debugging flows stay in the Build macOS Apps plugin skills.

## Workflow

1. Run `agentctl capability macos-development`.
2. Read the generated page at `docs/agentctl/capabilities/macos-development.md`.
3. Route into the specific Build macOS Apps plugin skill that fits the task, such as `$build-macos-apps:build-run-debug` or `$build-macos-apps:swiftui-patterns`.

## Do Not Do

- Do not duplicate macOS build, packaging, or AppKit guidance in this skill.
- Do not skip the capability page when choosing between the available macOS plugin skills.
