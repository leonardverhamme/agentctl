<!-- agentctl:auto-generated -->
# macOS development

- Key: `macos-development`
- Group: `integrations`
- Status: `missing`
- Front door: `$macos-development-capability`

## Summary

Use for local macOS build, run, packaging, signing, and desktop-specific SwiftUI/AppKit work.

## Navigation Skills

- `macos-development-capability`

## Entry Points

- `$macos-development-capability`
- `agentctl capability macos-development`
- `$build-macos-apps:build-run-debug`
- `$build-macos-apps:swiftui-patterns`

## Routing Notes

- Start with the capability skill, then route into the specific Build macOS Apps plugin skill that fits the current task.

## Backing Interfaces

- `skill` `macos-development-capability` [ok]
- `plugin` `build-macos-apps@openai-curated` [missing] (enabled=false)

## Overlap Policy

- Expose macOS build, packaging, and desktop debugging as one capability backed by the macOS plugin.
