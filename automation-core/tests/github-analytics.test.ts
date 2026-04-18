import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import { loadConfig } from "../src/config";
import { LocalStore } from "../src/store";
import { GitHubAnalyticsService } from "../src/services/github-analytics";
import { createIsolatedDatabase } from "./helpers/postgres-test-db";
const describePostgres = process.env.RUN_POSTGRES_TESTS === "1" ? describe : describe.skip;

describePostgres("GitHub analytics service", () => {
  let databaseUrl = "";
  let cleanupDatabase = async () => {};

  void beforeAll(async () => {
    const isolated = await createIsolatedDatabase("automation_core_github");
    databaseUrl = isolated.databaseUrl;
    cleanupDatabase = isolated.dispose;
  });

  void afterAll(async () => {
    await cleanupDatabase();
  });

  it("parses analytics filters with config defaults", () => {
    const service = buildService({
      githubExcludeArchivedByDefault: true,
      githubExcludeForksByDefault: false,
      githubExcludeBotsByDefault: true,
    });

    expect(
      service.parseFilters({
        owner: "  acme ",
        repository: "  automation-core ",
        contributor: "  jane-doe ",
        dateFrom: " 2026-04-01 ",
        dateTo: " 2026-04-18 ",
        grain: "month",
        includeBots: "false",
        includeArchived: "true",
        includeForks: true,
        metricFamily: " throughput ",
      }),
    ).toEqual({
      owner: "acme",
      repository: "automation-core",
      contributor: "jane-doe",
      dateFrom: "2026-04-01",
      dateTo: "2026-04-18",
      grain: "month",
      includeBots: false,
      includeArchived: true,
      includeForks: true,
      metricFamily: "throughput",
    });
  });

  it("discovers visible repositories into Postgres and respects repo exclusions", async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "automation-core-github-"));
    const store = await LocalStore.create(databaseUrl);
    const service = buildService(
      {
        githubMirrorRoot: root,
        githubOwnerFilters: "acme",
        githubRepoExcludePatterns: "acme/ignore-*",
      },
      store,
    );

    Object.defineProperty(service as any, "fetchVisibleRepositories", {
      configurable: true,
      value: async () => [
        {
          id: 101,
          name: "active-repo",
        full_name: "acme/active-repo",
        description: "Main repository",
        visibility: "private",
        private: true,
        language: "TypeScript",
        default_branch: "main",
        archived: false,
        fork: false,
        html_url: "https://github.com/acme/active-repo",
        clone_url: "https://github.com/acme/active-repo.git",
        pushed_at: "2026-04-18T07:00:00Z",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-04-18T07:00:00Z",
        owner: { login: "acme" },
      },
      {
        id: 102,
        name: "ignored-repo",
        full_name: "other/ignored-repo",
        description: "Other team",
        visibility: "public",
        private: false,
        language: "TypeScript",
        default_branch: "main",
        archived: false,
        fork: false,
        html_url: "https://github.com/other/ignored-repo",
        clone_url: "https://github.com/other/ignored-repo.git",
        pushed_at: "2026-04-18T07:00:00Z",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-04-18T07:00:00Z",
        owner: { login: "other" },
      },
      {
        id: 103,
        name: "ignore-me",
        full_name: "acme/ignore-me",
        description: "Excluded by pattern",
        visibility: "public",
        private: false,
        language: "TypeScript",
        default_branch: "main",
        archived: false,
        fork: false,
        html_url: "https://github.com/acme/ignore-me",
        clone_url: "https://github.com/acme/ignore-me.git",
        pushed_at: "2026-04-18T07:00:00Z",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-04-18T07:00:00Z",
        owner: { login: "acme" },
      },
      ],
    });

    const result = await service.discoverRepositories();
    expect(result).toEqual({
      scanned: 3,
      upserted: 1,
      skipped: 2,
    });

    const savedRepository = await store.get<{
      repo_id: string;
      owner: string;
      full_name: string;
      mirror_path: string;
      description: string;
    }>(
      `
        select repo_id, owner, full_name, mirror_path, description
        from github_repositories
        where repo_id = $1
      `,
      "101",
    );
    expect(savedRepository).toMatchObject({
      repo_id: "101",
      owner: "acme",
      full_name: "acme/active-repo",
      description: "Main repository",
    });
    expect(savedRepository?.mirror_path).toBe(path.resolve(root, "acme", "active-repo.git"));

    const syncState = await store.get<{
      repo_id: string;
      last_discovered_at: string | null;
    }>(
      `
        select repo_id, last_discovered_at
        from github_repo_sync_state
        where repo_id = $1
      `,
      "101",
    );
    expect(syncState).toMatchObject({
      repo_id: "101",
    });
    expect(syncState?.last_discovered_at).toBeTruthy();

    await store.run("delete from github_repo_sync_state where repo_id in ('101', '102', '103')");
    await store.run("delete from github_repositories where repo_id in ('101', '102', '103')");
    await store.close();
  });

  it("loads persisted analytics snapshots from the Postgres store", async () => {
    const store = await LocalStore.create(databaseUrl);
    const service = buildService({}, store);
    const repoId = `repo-${crypto.randomUUID()}`;
    const contributorId = `contributor-${crypto.randomUUID()}`;

    await store.run(
      `
        insert into github_repositories (
          repo_id, owner, name, full_name, description, visibility, language, default_branch,
          is_archived, is_fork, html_url, clone_url, pushed_at, created_at, updated_at,
          first_synced_at, last_synced_at, mirror_path, commit_count, additions, deletions,
          changed_files, open_prs, merged_prs, open_issues, releases, workflow_failures,
          latest_activity_at
        )
        values (
          $1, 'acme', 'dashboard', 'acme/dashboard', 'Engineering dashboard', 'private', 'TypeScript', 'main',
          false, false, 'https://github.com/acme/dashboard', 'https://github.com/acme/dashboard.git', null, null, null,
          '2026-04-18T08:00:00.000Z', '2026-04-18T08:00:00.000Z', '/tmp/dashboard.git', 7, 120, 45,
          18, 2, 1, 5, 1, 0, '2026-04-18T08:00:00.000Z'
        )
      `,
      repoId,
    );
    await store.run(
      `
        insert into github_contributors (
          contributor_id, canonical_login, display_name, avatar_url, first_seen_at, last_active_at,
          repo_count, commit_count, additions, deletions, changed_files, prs_opened, prs_merged,
          reviews_submitted, issues_opened, workflow_runs, latest_activity_at
        )
        values (
          $1, 'jane', 'Jane Doe', null, '2026-04-18T08:00:00.000Z', '2026-04-18T08:00:00.000Z',
          1, 5, 120, 45, 18, 2, 1, 3, 1, 1, '2026-04-18T08:00:00.000Z'
        )
      `,
      contributorId,
    );

    const filters = service.parseFilters({ owner: "acme", includeArchived: true, includeForks: true });
    const result = await service.queryAnalytics(filters);
    expect(result.filters.owner).toBe("acme");
    expect(result.summary.filters.owner).toBe("acme");
    expect(result.summary.totals.activeRepos).toBe(1);
    expect(result.summary.totals.activeContributors).toBe(1);
    expect(result.repositories).toHaveLength(1);
    expect(result.repositories[0]?.fullName).toBe("acme/dashboard");
    expect(result.contributors).toHaveLength(1);
    expect(result.contributors[0]?.canonicalLogin).toBe("jane");

    await store.run(`delete from github_contributors where contributor_id = '${contributorId}'`);
    await store.run(`delete from github_repositories where repo_id = '${repoId}'`);
    await store.close();
  });
});

function buildService(
  overrides: Partial<ReturnType<typeof loadConfig>>,
  store?: LocalStore,
) {
  const config = {
    ...loadConfig(),
    githubMirrorRoot: path.join(os.tmpdir(), "automation-core-github-mirrors"),
    githubBackfillMonths: 12,
    githubOwnerFilters: "",
    githubRepoExcludePatterns: "",
    githubExcludeArchivedByDefault: true,
    githubExcludeForksByDefault: true,
    githubExcludeBotsByDefault: true,
    ...overrides,
  };
  const localStore = store ?? ({
    run: vi.fn(),
    all: vi.fn().mockResolvedValue([]),
    get: vi.fn().mockResolvedValue(null),
  } as unknown as LocalStore);
  const notion = { isConfigured: () => false } as any;
  return new GitHubAnalyticsService(config, localStore, notion);
}
