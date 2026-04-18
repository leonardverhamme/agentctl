# Agentctl Maintenance Workflow

Primary commands:

- `agentctl maintenance check`
- `agentctl maintenance audit`
- `agentctl maintenance fix-docs`
- `agentctl maintenance render-report`

Primary outputs:

- `C:\Users\leona\.codex\docs\agentctl\overview.md`
- `C:\Users\leona\.codex\docs\agentctl\command-map.md`
- `C:\Users\leona\.codex\docs\agentctl\state-schema.md`
- `C:\Users\leona\.codex\docs\agentctl\capability-registry.md`
- `C:\Users\leona\.codex\docs\agentctl\cloud-readiness.md`
- `C:\Users\leona\.codex\docs\agentctl\maintenance.md`
- `C:\Users\leona\.codex\docs\agentctl\maintenance-report.json`
- `C:\Users\leona\.codex\.codex-workflows\agentctl-maintenance\state.json`

Use `audit` when:

- command or adapter behavior changed
- plugin packaging changed
- config enablement changed
- the maintenance docs should be fully regenerated

Use `fix-docs` when:

- the machine state is correct and only the generated docs need to be refreshed

Use `render-report` when:

- the maintenance Markdown page and JSON report need a fast refresh without regenerating every doc
