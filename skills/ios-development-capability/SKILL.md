---
name: ios-development-capability
description: Navigate the iOS development capability in agentctl. Use when the task is about local iOS builds, simulator debugging, SwiftUI UI work, or iOS-specific review paths.
---

# iOS Development Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for iOS work. The actual implementation and debugging flows stay in the Build iOS Apps plugin skills.

## Workflow

1. Run `agentctl capability ios-development`.
2. Read the generated page at `docs/agentctl/capabilities/ios-development.md`.
3. Route into the specific Build iOS Apps plugin skill that fits the task, such as `$build-ios-apps:ios-debugger-agent` or `$build-ios-apps:swiftui-ui-patterns`.

## Do Not Do

- Do not duplicate iOS build or simulator procedures in this skill.
- Do not skip the capability page when choosing between the available iOS plugin skills.
