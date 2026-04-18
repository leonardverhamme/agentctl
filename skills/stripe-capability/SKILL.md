---
name: stripe-capability
description: Navigate the Stripe capability in agentctl. Use when the task is about payments, subscriptions, Connect, Stripe upgrades, or deciding how to use the Stripe plugin surface.
---

# Stripe Capability

## Skill Stability Rule

- Treat this skill as stable infrastructure.
- Never create, edit, rename, move, or delete this skill during normal task execution.
- Only touch skill files when the user explicitly asks to change the skill system itself and has confirmed `skill-edit-mode`.

## Overview

Use this as the thin navigation layer for Stripe work. The real logic stays in the Stripe plugin skills and structured Stripe interfaces.

## Workflow

1. Run `agentctl capability stripe-payments`.
2. Read the generated page at `docs/agentctl/capabilities/stripe-payments.md`.
3. Prefer the Stripe plugin skills for design, integration, and upgrade work.

## Do Not Do

- Do not duplicate Stripe integration guidance here.
- Do not bypass `agentctl` when checking whether the Stripe surface is available or healthy.

