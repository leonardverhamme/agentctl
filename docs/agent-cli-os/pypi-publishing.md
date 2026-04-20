# Agent CLI OS PyPI Publishing

Use this when GitHub releases are healthy but `pipx install agent-cli-os` is still not live.

## What Must Be True

- the GitHub repo is `leonardverhamme/agent-cli-os`
- the release workflow file is `.github/workflows/release.yml`
- the GitHub Actions environment is `pypi`
- `pyproject.toml` still declares the package name `agent-cli-os`

## Preferred Path: Trusted Publishing

PyPI trusted publishing is the preferred release path.

In PyPI:

1. Open the `agent-cli-os` project.
2. Go to `Settings` -> `Publishing`.
3. Add or update the GitHub Actions trusted publisher with:
   - Owner: `leonardverhamme`
   - Repository name: `agent-cli-os`
   - Workflow filename: `release.yml`
   - Environment name: `pypi`

If the project does not exist yet, create a pending publisher for the same values from the PyPI publishing setup page, then rerun the GitHub release workflow.

## Fallback Path: API Token Secret

If trusted publishing is temporarily unavailable, add a repository or environment secret named `PYPI_API_TOKEN`.

Requirements:

- the token belongs to the `agent-cli-os` PyPI project
- the token still has upload permission
- the GitHub release workflow can access the secret

The release workflow will now:

- prefer trusted publishing when no token is configured
- fall back to `PYPI_API_TOKEN` when the secret exists
- wait until the new version appears on PyPI before treating the upload as complete

## How To Verify

After the PyPI-side configuration is fixed, rerun the release workflow for the target tag or cut a new tag.

Then verify:

```powershell
python -m pip index versions agent-cli-os
pipx install agent-cli-os
agentcli version
```

The release workflow also verifies live PyPI visibility with:

```powershell
python scripts/check_pypi_release.py --package agent-cli-os --version <version>
```

## Failure Modes

- `invalid-publisher`: the PyPI trusted publisher entry does not match the repo/workflow/environment claim
- `No matching distribution found for agent-cli-os`: the release is not live on PyPI yet
- token-based upload failure: the `PYPI_API_TOKEN` secret is missing, expired, scoped to the wrong project, or blocked by environment configuration
