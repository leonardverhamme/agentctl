<!-- agentctl:auto-generated -->
# Android testing

- Key: `android-testing`
- Group: `integrations`
- Status: `missing`
- Front door: `$android-testing-capability`

## Summary

Use for Android emulator QA, reproduction, screenshots, and log-driven debugging.

## Navigation Skills

- `android-testing-capability`

## Entry Points

- `$android-testing-capability`
- `agentctl capability android-testing`
- `$test-android-apps:android-emulator-qa`

## Routing Notes

- Start with the capability skill, then route into the Android emulator QA plugin skill for the actual run.

## Backing Interfaces

- `skill` `android-testing-capability` [ok]
- `plugin` `test-android-apps@openai-curated` [missing] (enabled=false)

## Overlap Policy

- Expose Android emulator QA as one capability backed by the Android testing plugin.
