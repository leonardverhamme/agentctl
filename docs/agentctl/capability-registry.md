<!-- agentctl:auto-generated -->
# Agentctl Capability Registry

The machine-readable registry lives at `agentctl/state/capabilities.json`.

## How To Use This Registry

- Treat `front_door` as the default interface an agent should choose first.
- Treat `backing_interfaces` as implementation detail and health metadata.
- Only care about raw CLI/MCP/plugin distinctions if a capability is degraded or missing.
- Use `overlap_policy` to understand why multiple interfaces collapse into one capability.

## Capability Menu

### Control Plane

- `autonomous-deep-runs` uses `$autonomous-deep-runs-capability` and is currently `ok`.
  - Overlap policy: The outer execute-until-done loop must use a real worker command, not chat memory. Prefer Codex runtime when it is callable or explicitly templated.
  - Advisory: Default Codex runtime is not callable in this environment. Use `--worker-command` or configure `AGENTCTL_CODEX_WORKER_TEMPLATE` for unattended deep runs.
  - Page: `docs/agentctl/capabilities/autonomous-deep-runs.md`
- `skills-management` uses `$skills-management-capability` and is currently `ok`.
  - Overlap policy: Wrap official skills tooling rather than reimplementing it.
  - Page: `docs/agentctl/capabilities/skills-management.md`
- `agentctl-maintenance` uses `$agentctl-maintenance-engineer` and is currently `ok`.
  - Overlap policy: Keep maintenance as one capability surface for docs, packaging, registry health, and platform drift.
  - Page: `docs/agentctl/capabilities/agentctl-maintenance.md`

### Workflow Skills

- `context-workflows` uses `$context-skill` and is currently `ok`.
  - Overlap policy: Prefer the lightweight context skill and durable repo docs over deeper automation.
  - Page: `docs/agentctl/capabilities/context-workflows.md`
- `ui-workflows` uses `$ui-skill / $ui-deep-audit` and is currently `ok`.
  - Overlap policy: Surface the UI skills first; plugin support stays a backing capability, not a separate menu.
  - Page: `docs/agentctl/capabilities/ui-workflows.md`
- `test-workflows` uses `$test-skill / $test-deep-audit` and is currently `ok`.
  - Overlap policy: Collapse testing transports behind one testing surface; use repo-native CLIs and Playwright first.
  - Page: `docs/agentctl/capabilities/test-workflows.md`
- `docs-workflows` uses `$docs-skill / $docs-deep-audit` and is currently `ok`.
  - Overlap policy: Keep docs work in the docs skills and hide transport details entirely.
  - Page: `docs/agentctl/capabilities/docs-workflows.md`
- `refactor-workflows` uses `$refactor-skill / $refactor-deep-audit` and is currently `ok`.
  - Overlap policy: Use the local refactor skills as the capability surface; do not split by underlying tooling.
  - Page: `docs/agentctl/capabilities/refactor-workflows.md`
- `cicd-workflows` uses `$cicd-skill / $cicd-deep-audit` and is currently `ok`.
  - Overlap policy: Surface CI/CD by workflow, not by whether GitHub or Vercel provides the underlying route.
  - Page: `docs/agentctl/capabilities/cicd-workflows.md`

### Research And Verification

- `research` uses `$research-capability` and is currently `ok`.
  - Overlap policy: Hide web, GitHub, and browser transport choices behind one research surface and one evidence contract.
  - Page: `docs/agentctl/capabilities/research.md`
- `browser-automation` uses `$browser-capability` and is currently `ok`.
  - Overlap policy: Treat Playwright CLI and MCP as peer browser backends behind one browser capability.
  - Page: `docs/agentctl/capabilities/browser-automation.md`

### Integrations

- `github-workflows` uses `$github-capability` and is currently `ok`.
  - Overlap policy: Collapse GitHub plugin skills and gh into one capability entry instead of separate transport menus.
  - Page: `docs/agentctl/capabilities/github-workflows.md`
- `github-advanced-security` uses `$github-security-capability` and is currently `ok`.
  - Overlap policy: Use `gh api` and `gh codeql` as the authoritative GitHub security routes, with `ghas-cli` as the rollout-at-scale helper when it is healthy. Do not assume generic GitHub plugin skills cover GHAS-specific work.
  - Page: `docs/agentctl/capabilities/github-advanced-security.md`
- `vercel-platform` uses `$vercel-capability` and is currently `ok`.
  - Overlap policy: Keep one Vercel capability entry; plugin and CLI are primary, MCP stays background metadata.
  - Page: `docs/agentctl/capabilities/vercel-platform.md`
- `supabase-data` uses `$supabase-capability` and is currently `ok`.
  - Overlap policy: Prefer the Supabase CLI for local stack, schema, migrations, and CI/CD. Use MCP when structured project access adds value beyond the CLI.
  - Page: `docs/agentctl/capabilities/supabase-data.md`
- `stripe-payments` uses `$stripe-capability` and is currently `missing`.
  - Overlap policy: Prefer the Stripe plugin capability surface; keep MCP as backing metadata, not a separate menu.
  - Page: `docs/agentctl/capabilities/stripe-payments.md`
- `sentry-observability` uses `$sentry-capability` and is currently `missing`.
  - Overlap policy: Expose Sentry as one observability capability instead of a transport-specific tool entry.
  - Page: `docs/agentctl/capabilities/sentry-observability.md`
- `ios-development` uses `$ios-development-capability` and is currently `missing`.
  - Overlap policy: Expose iOS build, UI, and debugging workflows as one capability backed by the iOS plugin.
  - Page: `docs/agentctl/capabilities/ios-development.md`
- `macos-development` uses `$macos-development-capability` and is currently `missing`.
  - Overlap policy: Expose macOS build, packaging, and desktop debugging as one capability backed by the macOS plugin.
  - Page: `docs/agentctl/capabilities/macos-development.md`
- `android-testing` uses `$android-testing-capability` and is currently `missing`.
  - Overlap policy: Expose Android emulator QA as one capability backed by the Android testing plugin.
  - Page: `docs/agentctl/capabilities/android-testing.md`
- `figma-design` uses `$figma-capability` and is currently `missing`.
  - Overlap policy: No plugin overlap here, so MCP remains the single capability entry.
  - Page: `docs/agentctl/capabilities/figma-design.md`
- `nextjs-runtime` uses `$nextjs-runtime-capability` and is currently `missing`.
  - Overlap policy: Keep Next.js runtime tooling as one capability entry backed by Next DevTools MCP.
  - Page: `docs/agentctl/capabilities/nextjs-runtime.md`

## Registry Shape

- `schema_version`
- `generated_at`
- `summary`
- `installed_skills`
- `local_skills`
- `plugins`
- `mcp_servers`
- `tools`
- `capabilities`
- `overlap_analysis`
- `detect_only_tools`

## Current Summary

```json
{
  "configured_mcp_count": 0,
  "enabled_plugin_count": 1,
  "installed_skill_count": 33,
  "local_skill_count": 33,
  "optional_attention_count": 7,
  "optional_capability_count": 12,
  "required_capability_count": 10,
  "status": "ok"
}
```

## Overlap Decisions

- `autonomous-deep-runs`: The outer execute-until-done loop must use a real worker command, not chat memory. Prefer Codex runtime when it is callable or explicitly templated.
- `skills-management`: Wrap official skills tooling rather than reimplementing it.
- `agentctl-maintenance`: Keep maintenance as one capability surface for docs, packaging, registry health, and platform drift.
- `ui-workflows`: Surface the UI skills first; plugin support stays a backing capability, not a separate menu.
- `test-workflows`: Collapse testing transports behind one testing surface; use repo-native CLIs and Playwright first.
- `docs-workflows`: Keep docs work in the docs skills and hide transport details entirely.
- `refactor-workflows`: Use the local refactor skills as the capability surface; do not split by underlying tooling.
- `cicd-workflows`: Surface CI/CD by workflow, not by whether GitHub or Vercel provides the underlying route.
- `research`: Hide web, GitHub, and browser transport choices behind one research surface and one evidence contract.
- `github-workflows`: Collapse GitHub plugin skills and gh into one capability entry instead of separate transport menus.
- `github-advanced-security`: Use `gh api` and `gh codeql` as the authoritative GitHub security routes, with `ghas-cli` as the rollout-at-scale helper when it is healthy. Do not assume generic GitHub plugin skills cover GHAS-specific work.
- `browser-automation`: Treat Playwright CLI and MCP as peer browser backends behind one browser capability.
- `vercel-platform`: Keep one Vercel capability entry; plugin and CLI are primary, MCP stays background metadata.
- `supabase-data`: Prefer the Supabase CLI for local stack, schema, migrations, and CI/CD. Use MCP when structured project access adds value beyond the CLI.
- `stripe-payments`: Prefer the Stripe plugin capability surface; keep MCP as backing metadata, not a separate menu.
- `sentry-observability`: Expose Sentry as one observability capability instead of a transport-specific tool entry.
- `ios-development`: Expose iOS build, UI, and debugging workflows as one capability backed by the iOS plugin.
- `macos-development`: Expose macOS build, packaging, and desktop debugging as one capability backed by the macOS plugin.
- `android-testing`: Expose Android emulator QA as one capability backed by the Android testing plugin.
- `figma-design`: No plugin overlap here, so MCP remains the single capability entry.
- `nextjs-runtime`: Keep Next.js runtime tooling as one capability entry backed by Next DevTools MCP.
