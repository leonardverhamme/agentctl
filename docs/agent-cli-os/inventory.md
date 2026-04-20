<!-- agent-cli-os:auto-generated -->
# Agent CLI OS Inventory

The raw autodetected inventory is stored at `agentctl/state/inventory.json`.

## Purpose

- Detect what is actually present on the machine and in Codex.
- Keep raw installed surface separate from the curated capability menu.
- Let `capabilities` stay compact while `inventory` remains the debugging and inspection layer.

## Commands

- `agentcli inventory refresh`
- `agentcli inventory show --kind all --scope all`
- `agentcli inventory item <kind>:<name>`

## Item Shape

- `id`
- `kind`
- `name`
- `source_scope`
- `status`
- `installed` or `configured`
- `version` when available
- `source_path` or `source_hint`
- `front_door_candidate`
- `menu_bucket`
- `hidden_reason`

## Menu Budget

- Raw inventory items per bucket: <= 25
- Raw buckets split deterministically when the item budget is exceeded.

## Current Summary

```json
{
  "bucket_count": 6,
  "hidden_count": 15,
  "kind_counts": {
    "plugin": 1,
    "skill": 42,
    "tool": 18
  },
  "max_bucket_size": 25,
  "status": "ok",
  "total_items": 61
}
```

## Detection Sources

- `tools`: `ok`
  - 18 detected tools
- `skills-global`: `ok`
- `skills-project`: `ok`
  - 3 project skills
