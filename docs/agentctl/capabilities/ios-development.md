<!-- agentctl:auto-generated -->
# iOS development

- Key: `ios-development`
- Group: `integrations`
- Status: `missing`
- Front door: `$ios-development-capability`

## Summary

Use for local iOS builds, simulator debugging, SwiftUI UI work, and iOS-specific review paths.

## Navigation Skills

- `ios-development-capability`

## Entry Points

- `$ios-development-capability`
- `agentctl capability ios-development`
- `$build-ios-apps:ios-debugger-agent`
- `$build-ios-apps:swiftui-ui-patterns`

## Routing Notes

- Start with the capability skill, then route into the specific Build iOS Apps plugin skill that best matches the task.

## Backing Interfaces

- `skill` `ios-development-capability` [ok]
- `plugin` `build-ios-apps@openai-curated` [missing] (enabled=false)

## Overlap Policy

- Expose iOS build, UI, and debugging workflows as one capability backed by the iOS plugin.
