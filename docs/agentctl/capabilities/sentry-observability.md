<!-- agentctl:auto-generated -->
# Sentry observability

- Key: `sentry-observability`
- Group: `integrations`
- Status: `missing`
- Front door: `$sentry-capability`

## Summary

Use for production error inspection, event review, and Sentry-backed observability checks.

## Navigation Skills

- `sentry-capability`

## Entry Points

- `$sentry-capability`
- `agentctl capability sentry-observability`
- `$sentry:sentry`

## Routing Notes

- Use the Sentry capability when the task starts from a production issue or error event.

## Backing Interfaces

- `skill` `sentry-capability` [ok]
- `plugin` `sentry@openai-curated` [missing] (enabled=false)

## Overlap Policy

- Expose Sentry as one observability capability instead of a transport-specific tool entry.
