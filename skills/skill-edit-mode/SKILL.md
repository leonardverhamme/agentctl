---
name: skill-edit-mode
description: Safe skill creation and skill maintenance workflow for Codex-managed skills. Use only when the user explicitly asks to create, update, move, rename, or otherwise change skill files and has explicitly confirmed that skill edit mode should open for the named skill or skills.
---

# Skill Edit Mode

Use this skill only for intentional work on the skill system itself.

## Entry Gate

- Do not use this skill just because a task touches tools, docs, or prompts.
- Only use this skill when the user explicitly asks to change a skill or create a new skill.
- Even then, require explicit confirmation that `skill-edit-mode` should open for the named skill or skills before editing any files under `skills/` or `plugins/*/skills/`.

If the user has not confirmed, stop and ask for confirmation instead of editing.

## What This Skill Covers

- Creating a new managed skill in a stable way
- Updating an existing managed skill after confirmation
- Renaming or reorganizing a managed skill after confirmation
- Regenerating or correcting companion `agents/openai.yaml`
- Validating a changed skill with the local validation path

## Safe Workflow

1. Confirm exactly which skill or skills may change.
2. Confirm whether this is a new skill, an update, a rename, or a packaging move.
3. Keep the change set as small as possible and avoid unrelated skill edits.
4. Update the skill files, companion references, and `agents/openai.yaml` only for the confirmed scope.
5. Run `quick_validate.py` for every changed skill before stopping.
6. If the skill is mirrored into a public bundle or plugin, sync that copy as part of the same change.
7. Summarize what changed and which skills were intentionally touched.

## Stability Rules

- Do not opportunistically clean up other skills while you are here.
- Do not widen the scope from one confirmed skill to many without a fresh confirmation.
- Do not edit curated third-party plugin skills unless the user explicitly asks for that and confirms the exact target.
- Do not leave a changed skill unvalidated.

## References

- Use the built-in `skill-creator` guidance when you need help designing or validating a skill structure.
- Follow the local `AGENTS.md` rules first when they are stricter than generic skill-creation guidance.
