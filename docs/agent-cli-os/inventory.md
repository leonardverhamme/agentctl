<!-- agent-cli-os:auto-generated -->
# Agent CLI OS Inventory

The raw app-aware inventory is stored at `agentctl/state/inventory.json`.

## App-Aware Coverage

- Machine CLIs and runtime tools.
- Local repo skills and globally installed skills.
- Plugin-provided skills plus configured plugins.
- Configured MCP servers and app connectors discovered from local `.app.json` metadata in the Codex plugin cache.

## Why This Exists

- Detect what is actually present on the machine and in Codex.
- Keep raw installed surface separate from the curated capability menu.
- Let `capabilities` stay compact while `inventory` remains the debugging, inspection, and health layer.

## Commands

- `agentcli inventory refresh`
- `agentcli inventory show --kind all --scope all`
- `agentcli inventory item <kind>:<name>`

## Health Model

- `ok`: the source refreshed cleanly and the surface is usable for routing.
- `degraded`: the source partially refreshed or a backing runtime is missing.
- `error`: the source could not be refreshed cleanly or the record is not trustworthy.
- App connector health comes from the enabled plugin/config state plus the local `.app.json` connector metadata.

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
- App-aware inventory stays raw and separate from the curated capability menu.

## Current Summary

```json
{
  "bucket_count": 8,
  "hidden_count": 21,
  "kind_counts": {
    "app": 5,
    "plugin": 1,
    "skill": 77,
    "tool": 20
  },
  "max_bucket_size": 25,
  "status": "ok",
  "total_items": 103
}
```

## Detection Sources

- `tools`: `ok`
  - 20 detected tools
- `skills-global`: `ok`
- `skills-project`: `ok`
  - 36 project skills
- `apps-temp`: `ok`
  - 100 manifests, 100 mapped connectors
- `apps-active`: `ok`
  - 5 active connectors, 6 helper connectors ignored, 1 cache files
