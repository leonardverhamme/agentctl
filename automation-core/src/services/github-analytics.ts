import fs from "node:fs";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

import { AppConfig } from "../config";
import {
  AnalyticsFilters,
  AnalyticsGrain,
  AnalyticsSummarySnapshot,
  CommitFact,
  ContributorAliasRecord,
  ContributorRecord,
  GitHubRepositoryRecord,
  IssueFact,
  PullRequestFact,
  PullRequestReviewFact,
  ReleaseFact,
  RepoRollup,
  TrendPoint,
  WeeklyEngineeringBrief,
  WorkflowRunFact,
} from "../types";
import { LocalStore } from "../store";
import { NotionService } from "./notion";
import { nowIso } from "../lib/time";

const execFileAsync = promisify(execFile);

type GitHubRepoApiRecord = {
  id: number;
  name: string;
  full_name: string;
  description: string | null;
  visibility?: string | null;
  private?: boolean;
  language?: string | null;
  default_branch?: string | null;
  archived?: boolean;
  fork?: boolean;
  html_url: string;
  clone_url: string;
  pushed_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  owner?: {
    login?: string | null;
  };
};

type QueryAnalyticsResult = {
  filters: AnalyticsFilters;
  summary: AnalyticsSummarySnapshot;
  repositories: GitHubRepositoryRecord[];
  contributors: ContributorRecord[];
  commits: CommitFact[];
  pullRequests: PullRequestFact[];
  reviews: PullRequestReviewFact[];
  issues: IssueFact[];
  releases: ReleaseFact[];
  workflowRuns: WorkflowRunFact[];
  trends: TrendPoint[];
  weeklyBrief: WeeklyEngineeringBrief | null;
  topRepoRollups: RepoRollup[];
};

type GitMirrorCommitRecord = {
  sha: string;
  authorName: string;
  authorEmail: string;
  authoredAt: string;
  committedAt: string;
  subject: string;
  body: string;
  additions: number;
  deletions: number;
  changedFiles: number;
  isMerge: boolean;
  refNames: string[];
};

type Metrics = {
  commits: number;
  additions: number;
  deletions: number;
  changedFiles: number;
  prsOpened: number;
  prsMerged: number;
  reviewsSubmitted: number;
  issuesOpened: number;
  issuesClosed: number;
  releases: number;
  workflowRuns: number;
  workflowFailures: number;
};

type RepoMetrics = Metrics & {
  latestActivityAt: string | null;
};

type ContributorMetrics = Metrics & {
  latestActivityAt: string | null;
  repoIds: Set<string>;
};

export class GitHubAnalyticsService {
  constructor(
    private readonly config: AppConfig,
    private readonly store: LocalStore,
    private readonly notion: NotionService,
  ) {}

  parseFilters(input: Record<string, unknown>): AnalyticsFilters {
    return {
      owner: normalizeText(input.owner),
      repository: normalizeText(input.repository),
      contributor: normalizeText(input.contributor),
      dateFrom: normalizeDate(input.dateFrom),
      dateTo: normalizeDate(input.dateTo),
      grain: normalizeGrain(input.grain),
      includeBots: normalizeBoolean(input.includeBots, !this.config.githubExcludeBotsByDefault),
      includeArchived: normalizeBoolean(input.includeArchived, !this.config.githubExcludeArchivedByDefault),
      includeForks: normalizeBoolean(input.includeForks, !this.config.githubExcludeForksByDefault),
      metricFamily: normalizeText(input.metricFamily),
    };
  }

  async discoverRepositories(): Promise<{ scanned: number; upserted: number; skipped: number }> {
    const repositories = await this.fetchVisibleRepositories();
    let upserted = 0;
    let skipped = 0;

    for (const repository of repositories) {
      if (this.isExcluded(repository)) {
        skipped += 1;
        continue;
      }
      await this.upsertRepository(repository);
      upserted += 1;
    }

    return {
      scanned: repositories.length,
      upserted,
      skipped,
    };
  }

  async backfillAnalytics(): Promise<Record<string, number>> {
    await this.discoverRepositories();
    const synced = await this.syncRepositories(true);
    await this.rollupAnalytics();
    return synced;
  }

  async syncAnalytics(): Promise<Record<string, number>> {
    await this.discoverRepositories();
    const synced = await this.syncRepositories(false);
    await this.rollupAnalytics();
    return synced;
  }

  async rollupAnalytics(): Promise<Record<string, number>> {
    const repositories = await this.listTrackedRepositories();
    const commits = await this.store.all<CommitFact>(
      `
        select
          repo_id as "repoId",
          sha,
          author_contributor_id as "authorContributorId",
          author_login as "authorLogin",
          author_name as "authorName",
          author_email as "authorEmail",
          authored_at as "authoredAt",
          committed_at as "committedAt",
          subject,
          body,
          additions,
          deletions,
          changed_files as "changedFiles",
          is_merge as "isMerge",
          html_url as "htmlUrl",
          ref_names_json as "refNames"
        from github_commits
      `,
    );

    await this.store.run("delete from github_daily_rollups");
    await this.store.run("delete from github_weekly_rollups");
    await this.store.run("delete from github_monthly_rollups");
    await this.store.run("delete from github_contributors");
    await this.store.run("delete from github_contributor_aliases");

    const repoMetrics = new Map<string, RepoMetrics>();
    const contributorMetrics = new Map<string, ContributorMetrics>();
    const contributorMeta = new Map<string, { login: string | null; displayName: string; avatarUrl: string | null; firstSeenAt: string | null }>();
    const contributorAliases = new Map<string, ContributorAliasRecord>();
    const dailyRepoBuckets = new Map<string, Metrics>();
    const weeklyRepoBuckets = new Map<string, Metrics>();
    const monthlyRepoBuckets = new Map<string, Metrics>();
    const dailyContributorBuckets = new Map<string, Metrics>();
    const weeklyContributorBuckets = new Map<string, Metrics>();
    const monthlyContributorBuckets = new Map<string, Metrics>();

    for (const commit of commits) {
      const repoMetric = ensureRepoMetrics(repoMetrics, commit.repoId);
      bumpCommitMetrics(repoMetric, commit);

      const contributorId = commit.authorContributorId ?? buildContributorId(commit.authorLogin, commit.authorName, commit.authorEmail);
      const contributorMetric = ensureContributorMetrics(contributorMetrics, contributorId, commit.repoId);
      bumpCommitMetrics(contributorMetric, commit);

      if (!contributorMeta.has(contributorId)) {
        contributorMeta.set(contributorId, {
          login: commit.authorLogin ?? deriveLoginFromEmail(commit.authorEmail),
          displayName: commit.authorLogin ?? commit.authorName,
          avatarUrl: null,
          firstSeenAt: commit.authoredAt,
        });
      }
      const existingMeta = contributorMeta.get(contributorId)!;
      if (!existingMeta.firstSeenAt || commit.authoredAt < existingMeta.firstSeenAt) {
        existingMeta.firstSeenAt = commit.authoredAt;
      }

      const aliasKey = buildAliasKey(commit.authorLogin, commit.authorName, commit.authorEmail);
      contributorAliases.set(aliasKey, {
        aliasKey,
        contributorId,
        login: commit.authorLogin ?? deriveLoginFromEmail(commit.authorEmail),
        name: commit.authorName,
        email: commit.authorEmail,
        lastSeenAt: commit.authoredAt,
      });

      const dayStart = bucketStart(commit.authoredAt, "day");
      const weekStart = bucketStart(commit.authoredAt, "week");
      const monthStart = bucketStart(commit.authoredAt, "month");
      bumpCommitMetrics(ensureBucket(dailyRepoBuckets, makeBucketKey("repo", commit.repoId, dayStart)), commit);
      bumpCommitMetrics(ensureBucket(weeklyRepoBuckets, makeBucketKey("repo", commit.repoId, weekStart)), commit);
      bumpCommitMetrics(ensureBucket(monthlyRepoBuckets, makeBucketKey("repo", commit.repoId, monthStart)), commit);
      bumpCommitMetrics(ensureBucket(dailyContributorBuckets, makeBucketKey("contributor", contributorId, dayStart)), commit);
      bumpCommitMetrics(ensureBucket(weeklyContributorBuckets, makeBucketKey("contributor", contributorId, weekStart)), commit);
      bumpCommitMetrics(ensureBucket(monthlyContributorBuckets, makeBucketKey("contributor", contributorId, monthStart)), commit);
    }

    for (const [repoId, metrics] of repoMetrics) {
      await this.store.run(
        `
          update github_repositories
          set commit_count = $2,
              additions = $3,
              deletions = $4,
              changed_files = $5,
              latest_activity_at = $6
          where repo_id = $1
        `,
        repoId,
        metrics.commits,
        metrics.additions,
        metrics.deletions,
        metrics.changedFiles,
        metrics.latestActivityAt,
      );
    }

    for (const [contributorId, metrics] of contributorMetrics) {
      const meta = contributorMeta.get(contributorId);
      await this.store.run(
        `
          insert into github_contributors (
            contributor_id,
            canonical_login,
            display_name,
            avatar_url,
            first_seen_at,
            last_active_at,
            repo_count,
            commit_count,
            additions,
            deletions,
            changed_files,
            prs_opened,
            prs_merged,
            reviews_submitted,
            issues_opened,
            workflow_runs,
            latest_activity_at
          )
          values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
          on conflict (contributor_id) do update set
            canonical_login = excluded.canonical_login,
            display_name = excluded.display_name,
            avatar_url = excluded.avatar_url,
            first_seen_at = excluded.first_seen_at,
            last_active_at = excluded.last_active_at,
            repo_count = excluded.repo_count,
            commit_count = excluded.commit_count,
            additions = excluded.additions,
            deletions = excluded.deletions,
            changed_files = excluded.changed_files,
            prs_opened = excluded.prs_opened,
            prs_merged = excluded.prs_merged,
            reviews_submitted = excluded.reviews_submitted,
            issues_opened = excluded.issues_opened,
            workflow_runs = excluded.workflow_runs,
            latest_activity_at = excluded.latest_activity_at
        `,
        contributorId,
        meta?.login ?? null,
        meta?.displayName ?? contributorId,
        meta?.avatarUrl ?? null,
        meta?.firstSeenAt ?? null,
        metrics.latestActivityAt,
        metrics.repoIds.size,
        metrics.commits,
        metrics.additions,
        metrics.deletions,
        metrics.changedFiles,
        metrics.prsOpened,
        metrics.prsMerged,
        metrics.reviewsSubmitted,
        metrics.issuesOpened,
        metrics.workflowRuns,
        metrics.latestActivityAt,
      );
    }

    for (const alias of contributorAliases.values()) {
      await this.store.run(
        `
          insert into github_contributor_aliases (alias_key, contributor_id, login, name, email, last_seen_at)
          values ($1, $2, $3, $4, $5, $6)
          on conflict (alias_key) do update set
            contributor_id = excluded.contributor_id,
            login = excluded.login,
            name = excluded.name,
            email = excluded.email,
            last_seen_at = excluded.last_seen_at
        `,
        alias.aliasKey,
        alias.contributorId,
        alias.login,
        alias.name,
        alias.email,
        alias.lastSeenAt,
      );
    }

    await writeBuckets(this.store, "github_daily_rollups", dailyRepoBuckets, dailyContributorBuckets);
    await writeBuckets(this.store, "github_weekly_rollups", weeklyRepoBuckets, weeklyContributorBuckets);
    await writeBuckets(this.store, "github_monthly_rollups", monthlyRepoBuckets, monthlyContributorBuckets);

    return {
      repositories: repositories.length,
      contributors: contributorMetrics.size,
      commits: commits.length,
    };
  }

  async syncNotionReporting(): Promise<Record<string, number | boolean>> {
    return {
      configured: this.notion.isConfigured(),
      repositories: 0,
      contributors: 0,
      weeklySnapshots: 0,
      monthlySnapshots: 0,
    };
  }

  async createWeeklyBrief(): Promise<WeeklyEngineeringBrief | null> {
    return null;
  }

  async queryAnalytics(filters: AnalyticsFilters): Promise<QueryAnalyticsResult> {
    const repositories = await this.store.all<GitHubRepositoryRecord>(
      `
        select
          repo_id as "repoId",
          owner,
          name,
          full_name as "fullName",
          description,
          visibility,
          language,
          default_branch as "defaultBranch",
          is_archived as "isArchived",
          is_fork as "isFork",
          html_url as "htmlUrl",
          clone_url as "cloneUrl",
          pushed_at as "pushedAt",
          created_at as "createdAt",
          updated_at as "updatedAt",
          first_synced_at as "firstSyncedAt",
          last_synced_at as "lastSyncedAt",
          mirror_path as "mirrorPath",
          commit_count as "commitCount",
          additions,
          deletions,
          changed_files as "changedFiles",
          open_prs as "openPrs",
          merged_prs as "mergedPrs",
          open_issues as "openIssues",
          releases,
          workflow_failures as "workflowFailures",
          latest_activity_at as "latestActivityAt"
        from github_repositories
        order by owner asc, name asc
      `,
    );

    const contributors = await this.store.all<ContributorRecord>(
      `
        select
          contributor_id as "contributorId",
          canonical_login as "canonicalLogin",
          display_name as "displayName",
          avatar_url as "avatarUrl",
          first_seen_at as "firstSeenAt",
          last_active_at as "lastActiveAt",
          repo_count as "repoCount",
          commit_count as "commitCount",
          additions,
          deletions,
          changed_files as "changedFiles",
          prs_opened as "prsOpened",
          prs_merged as "prsMerged",
          reviews_submitted as "reviewsSubmitted",
          issues_opened as "issuesOpened",
          workflow_runs as "workflowRuns",
          latest_activity_at as "latestActivityAt"
        from github_contributors
        order by commit_count desc, display_name asc
      `,
    );

    const filteredRepositories = repositories.filter((repository) => matchesRepositoryFilters(repository, filters));
    const filteredContributors = contributors.filter((contributor) => matchesContributorFilters(contributor, filters));
    const commits = await this.loadCommits(filters, filteredRepositories, filteredContributors);
    const trends = await this.loadTrends(filters, filteredRepositories, filteredContributors);
    const summary = buildSummary(filters, filteredRepositories, filteredContributors, commits, trends);

    return {
      filters,
      summary,
      repositories: filteredRepositories,
      contributors: filteredContributors,
      commits,
      pullRequests: [],
      reviews: [],
      issues: [],
      releases: [],
      workflowRuns: [],
      trends,
      weeklyBrief: null,
      topRepoRollups: [],
    };
  }

  private async fetchVisibleRepositories(): Promise<GitHubRepoApiRecord[]> {
    const response = await runJsonCommand<GitHubRepoApiRecord[]>("gh", [
      "api",
      "--paginate",
      "--slurp",
      "/user/repos?per_page=100&sort=updated&affiliation=owner,collaborator,organization_member",
    ]);

    return response.flat();
  }

  private isExcluded(repository: GitHubRepoApiRecord): boolean {
    const ownerFilters = splitCsv(this.config.githubOwnerFilters);
    const excludedPatterns = splitCsv(this.config.githubRepoExcludePatterns);
    const fullName = repository.full_name;
    const owner = repository.owner?.login ?? fullName.split("/")[0] ?? "";

    if (ownerFilters.length > 0 && !ownerFilters.includes(owner)) {
      return true;
    }

    if (excludedPatterns.some((pattern) => wildcardToRegExp(pattern).test(fullName))) {
      return true;
    }

    return false;
  }

  private async upsertRepository(repository: GitHubRepoApiRecord): Promise<void> {
    const owner = repository.owner?.login ?? repository.full_name.split("/")[0] ?? "";
    const name = repository.name;
    const fullName = repository.full_name;
    const mirrorPath = path.resolve(this.config.githubMirrorRoot, owner, `${name}.git`);

    fs.mkdirSync(path.dirname(mirrorPath), { recursive: true });

    await this.store.run(
      `
        insert into github_repositories (
          repo_id,
          owner,
          name,
          full_name,
          description,
          visibility,
          language,
          default_branch,
          is_archived,
          is_fork,
          html_url,
          clone_url,
          pushed_at,
          created_at,
          updated_at,
          first_synced_at,
          last_synced_at,
          mirror_path
        )
        values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, coalesce((select first_synced_at from github_repositories where repo_id = $1), $16), $17, $18)
        on conflict (repo_id) do update set
          owner = excluded.owner,
          name = excluded.name,
          full_name = excluded.full_name,
          description = excluded.description,
          visibility = excluded.visibility,
          language = excluded.language,
          default_branch = excluded.default_branch,
          is_archived = excluded.is_archived,
          is_fork = excluded.is_fork,
          html_url = excluded.html_url,
          clone_url = excluded.clone_url,
          pushed_at = excluded.pushed_at,
          created_at = excluded.created_at,
          updated_at = excluded.updated_at,
          last_synced_at = excluded.last_synced_at,
          mirror_path = excluded.mirror_path
      `,
      String(repository.id),
      owner,
      name,
      fullName,
      repository.description ?? "",
      repository.visibility ?? (repository.private ? "private" : "public"),
      repository.language ?? "",
      repository.default_branch ?? "main",
      Boolean(repository.archived),
      Boolean(repository.fork),
      repository.html_url,
      repository.clone_url,
      repository.pushed_at ?? null,
      repository.created_at ?? null,
      repository.updated_at ?? null,
      nowIso(),
      nowIso(),
      mirrorPath,
    );

    await this.store.run(
      `
        insert into github_repo_sync_state (repo_id, last_discovered_at)
        values ($1, $2)
        on conflict (repo_id) do update set
          last_discovered_at = excluded.last_discovered_at
      `,
      String(repository.id),
      nowIso(),
    );
  }

  private async syncRepositories(fullBackfill: boolean): Promise<Record<string, number>> {
    const repositories = await this.listTrackedRepositories();
    let syncedRepositories = 0;
    let totalCommits = 0;

    for (const repository of repositories) {
      const since = fullBackfill ? monthsAgoIso(this.config.githubBackfillMonths) : await this.syncWindowForRepo(repository.repoId);
      await ensureMirror(repository);
      await fetchMirror(repository.mirrorPath);
      const commits = await readCommitsFromMirror(repository, since);
      for (const commit of commits) {
        const authorLogin = deriveLoginFromEmail(commit.authorEmail);
        const contributorId = buildContributorId(authorLogin, commit.authorName, commit.authorEmail);
        await this.store.run(
          `
            insert into github_commits (
              repo_id,
              sha,
              author_contributor_id,
              author_login,
              author_name,
              author_email,
              authored_at,
              committed_at,
              subject,
              body,
              additions,
              deletions,
              changed_files,
              is_merge,
              html_url,
              ref_names_json
            )
            values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16::jsonb)
            on conflict (repo_id, sha) do update set
              author_contributor_id = excluded.author_contributor_id,
              author_login = excluded.author_login,
              author_name = excluded.author_name,
              author_email = excluded.author_email,
              authored_at = excluded.authored_at,
              committed_at = excluded.committed_at,
              subject = excluded.subject,
              body = excluded.body,
              additions = excluded.additions,
              deletions = excluded.deletions,
              changed_files = excluded.changed_files,
              is_merge = excluded.is_merge,
              html_url = excluded.html_url,
              ref_names_json = excluded.ref_names_json
          `,
          repository.repoId,
          commit.sha,
          contributorId,
          authorLogin,
          commit.authorName,
          commit.authorEmail,
          commit.authoredAt,
          commit.committedAt,
          commit.subject,
          commit.body,
          commit.additions,
          commit.deletions,
          commit.changedFiles,
          commit.isMerge,
          `${repository.htmlUrl}/commit/${commit.sha}`,
          JSON.stringify(commit.refNames),
        );
      }

      await this.store.run(
        `
          update github_repositories
          set last_synced_at = $2
          where repo_id = $1
        `,
        repository.repoId,
        nowIso(),
      );
      await this.store.run(
        `
          insert into github_repo_sync_state (repo_id, last_backfill_at, last_synced_at)
          values ($1, $2, $3)
          on conflict (repo_id) do update set
            last_backfill_at = case when $4 then excluded.last_backfill_at else github_repo_sync_state.last_backfill_at end,
            last_synced_at = excluded.last_synced_at
        `,
        repository.repoId,
        fullBackfill ? nowIso() : null,
        nowIso(),
        fullBackfill,
      );

      syncedRepositories += 1;
      totalCommits += commits.length;
    }

    return {
      repositories: syncedRepositories,
      commits: totalCommits,
      pullRequests: 0,
      reviews: 0,
      issues: 0,
      releases: 0,
      workflowRuns: 0,
    };
  }

  private async listTrackedRepositories(): Promise<GitHubRepositoryRecord[]> {
    return this.store.all<GitHubRepositoryRecord>(
      `
        select
          repo_id as "repoId",
          owner,
          name,
          full_name as "fullName",
          description,
          visibility,
          language,
          default_branch as "defaultBranch",
          is_archived as "isArchived",
          is_fork as "isFork",
          html_url as "htmlUrl",
          clone_url as "cloneUrl",
          pushed_at as "pushedAt",
          created_at as "createdAt",
          updated_at as "updatedAt",
          first_synced_at as "firstSyncedAt",
          last_synced_at as "lastSyncedAt",
          mirror_path as "mirrorPath",
          commit_count as "commitCount",
          additions,
          deletions,
          changed_files as "changedFiles",
          open_prs as "openPrs",
          merged_prs as "mergedPrs",
          open_issues as "openIssues",
          releases,
          workflow_failures as "workflowFailures",
          latest_activity_at as "latestActivityAt"
        from github_repositories
        order by owner asc, name asc
      `,
    );
  }

  private async syncWindowForRepo(repoId: string): Promise<string> {
    const row = await this.store.get<{ last_synced_at: string | null }>(
      `
        select last_synced_at
        from github_repo_sync_state
        where repo_id = $1
      `,
      repoId,
    );
    if (!row?.last_synced_at) {
      return monthsAgoIso(this.config.githubBackfillMonths);
    }

    const date = new Date(row.last_synced_at);
    date.setDate(date.getDate() - 1);
    return date.toISOString();
  }

  private async loadCommits(
    filters: AnalyticsFilters,
    repositories: GitHubRepositoryRecord[],
    contributors: ContributorRecord[],
  ): Promise<CommitFact[]> {
    const commits = await this.store.all<CommitFact>(
      `
        select
          repo_id as "repoId",
          sha,
          author_contributor_id as "authorContributorId",
          author_login as "authorLogin",
          author_name as "authorName",
          author_email as "authorEmail",
          authored_at as "authoredAt",
          committed_at as "committedAt",
          subject,
          body,
          additions,
          deletions,
          changed_files as "changedFiles",
          is_merge as "isMerge",
          html_url as "htmlUrl",
          ref_names_json as "refNames"
        from github_commits
        order by authored_at desc
        limit 500
      `,
    );

    const repoIds = new Set(repositories.map((repository) => repository.repoId));
    const contributorIds = new Set(contributors.map((contributor) => contributor.contributorId));

    return commits.filter((commit) => {
      if (repoIds.size > 0 && !repoIds.has(commit.repoId)) {
        return false;
      }
      if (filters.contributor && contributorIds.size > 0 && commit.authorContributorId && !contributorIds.has(commit.authorContributorId)) {
        return false;
      }
      if (filters.dateFrom && commit.authoredAt < filters.dateFrom) {
        return false;
      }
      if (filters.dateTo && commit.authoredAt > filters.dateTo) {
        return false;
      }
      return true;
    });
  }

  private async loadTrends(
    filters: AnalyticsFilters,
    repositories: GitHubRepositoryRecord[],
    contributors: ContributorRecord[],
  ): Promise<TrendPoint[]> {
    const table = filters.grain === "month" ? "github_monthly_rollups" : filters.grain === "week" ? "github_weekly_rollups" : "github_daily_rollups";
    const rows = await this.store.all<TrendPoint & { entityType: string; entityId: string }>(
      `
        select
          entity_type as "entityType",
          entity_id as "entityId",
          bucket_start as "bucketStart",
          commits,
          additions,
          deletions,
          additions - deletions as "netLoc",
          prs_opened as "prsOpened",
          prs_merged as "prsMerged",
          reviews_submitted as "reviewsSubmitted",
          issues_opened as "issuesOpened",
          issues_closed as "issuesClosed",
          releases,
          workflow_runs as "workflowRuns",
          workflow_failures as "workflowFailures"
        from ${table}
        order by bucket_start asc
      `,
    );

    const repoIds = new Set(repositories.map((repository) => repository.repoId));
    const contributorIds = new Set(contributors.map((contributor) => contributor.contributorId));
    const grouped = new Map<string, TrendPoint>();

    for (const row of rows) {
      if (row.entityType === "repo" && repoIds.size > 0 && !repoIds.has(row.entityId)) {
        continue;
      }
      if (row.entityType === "contributor" && filters.contributor && contributorIds.size > 0 && !contributorIds.has(row.entityId)) {
        continue;
      }
      if (filters.dateFrom && row.bucketStart < filters.dateFrom) {
        continue;
      }
      if (filters.dateTo && row.bucketStart > filters.dateTo) {
        continue;
      }
      const point = grouped.get(row.bucketStart) ?? {
        bucketStart: row.bucketStart,
        commits: 0,
        additions: 0,
        deletions: 0,
        netLoc: 0,
        prsOpened: 0,
        prsMerged: 0,
        reviewsSubmitted: 0,
        issuesOpened: 0,
        issuesClosed: 0,
        releases: 0,
        workflowRuns: 0,
        workflowFailures: 0,
      };
      point.commits += row.commits;
      point.additions += row.additions;
      point.deletions += row.deletions;
      point.netLoc += row.netLoc;
      point.prsOpened += row.prsOpened;
      point.prsMerged += row.prsMerged;
      point.reviewsSubmitted += row.reviewsSubmitted;
      point.issuesOpened += row.issuesOpened;
      point.issuesClosed += row.issuesClosed;
      point.releases += row.releases;
      point.workflowRuns += row.workflowRuns;
      point.workflowFailures += row.workflowFailures;
      grouped.set(row.bucketStart, point);
    }

    return [...grouped.values()].sort((left, right) => left.bucketStart.localeCompare(right.bucketStart));
  }
}

function normalizeText(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function normalizeDate(value: unknown): string | null {
  const normalized = normalizeText(value);
  return normalized ? normalized : null;
}

function normalizeBoolean(value: unknown, fallback: boolean): boolean {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "string") {
    return ["1", "true", "yes", "on"].includes(value.toLowerCase());
  }
  return fallback;
}

function normalizeGrain(value: unknown): AnalyticsGrain {
  if (value === "week" || value === "month") {
    return value;
  }
  return "day";
}

function splitCsv(value: string): string[] {
  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function wildcardToRegExp(pattern: string): RegExp {
  const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*");
  return new RegExp(`^${escaped}$`, "i");
}

async function runJsonCommand<T>(command: string, args: string[]): Promise<T> {
  const { stdout } = await execFileAsync(command, args, {
    windowsHide: true,
    maxBuffer: 1024 * 1024 * 64,
  });
  return JSON.parse(stdout) as T;
}

async function runTextCommand(command: string, args: string[]): Promise<string> {
  const { stdout } = await execFileAsync(command, args, {
    windowsHide: true,
    maxBuffer: 1024 * 1024 * 128,
  });
  return stdout;
}

async function ensureMirror(repository: GitHubRepositoryRecord): Promise<void> {
  if (fs.existsSync(repository.mirrorPath)) {
    return;
  }

  fs.mkdirSync(path.dirname(repository.mirrorPath), { recursive: true });
  await execFileAsync(
    "gh",
    ["repo", "clone", repository.fullName, repository.mirrorPath, "--", "--mirror"],
    { windowsHide: true, maxBuffer: 1024 * 1024 * 64 },
  );
}

async function fetchMirror(mirrorPath: string): Promise<void> {
  await execFileAsync(
    "git",
    ["--git-dir", mirrorPath, "remote", "update", "--prune"],
    { windowsHide: true, maxBuffer: 1024 * 1024 * 64 },
  );
}

async function readCommitsFromMirror(repository: GitHubRepositoryRecord, since: string): Promise<GitMirrorCommitRecord[]> {
  const refsOutput = await runTextCommand("git", [
    "--git-dir",
    repository.mirrorPath,
    "for-each-ref",
    "--format=%(refname:short)",
    "refs/heads",
    "refs/remotes",
  ]);
  const refs = refsOutput
    .split(/\r?\n/)
    .map((entry) => entry.trim())
    .filter(Boolean);

  const bySha = new Map<string, GitMirrorCommitRecord & { refSet: Set<string> }>();
  for (const refName of refs) {
    const logOutput = await runTextCommand("git", [
      "--git-dir",
      repository.mirrorPath,
      "log",
      refName,
      "--since",
      since,
      "--date=iso-strict",
      "--numstat",
      "--format=%x1e%H%x1f%an%x1f%ae%x1f%aI%x1f%cI%x1f%s%x1f%b%x1f%P",
    ]);
    mergeGitLog(bySha, logOutput, refName);
  }

  return [...bySha.values()].map((entry) => ({
    sha: entry.sha,
    authorName: entry.authorName,
    authorEmail: entry.authorEmail,
    authoredAt: entry.authoredAt,
    committedAt: entry.committedAt,
    subject: entry.subject,
    body: entry.body,
    additions: entry.additions,
    deletions: entry.deletions,
    changedFiles: entry.changedFiles,
    isMerge: entry.isMerge,
    refNames: [...entry.refSet].sort(),
  }));
}

function mergeGitLog(
  target: Map<string, GitMirrorCommitRecord & { refSet: Set<string> }>,
  logOutput: string,
  refName: string,
): void {
  const records = logOutput.split("\u001e").map((entry) => entry.trim()).filter(Boolean);
  for (const record of records) {
    const lines = record.split(/\r?\n/);
    const header = lines.shift();
    if (!header) {
      continue;
    }
    const [sha, authorName, authorEmail, authoredAt, committedAt, subject, body, parents] = header.split("\u001f");
    const existing = target.get(sha);
    if (existing) {
      existing.refSet.add(refName);
      continue;
    }

    let additions = 0;
    let deletions = 0;
    let changedFiles = 0;
    for (const line of lines) {
      const parts = line.split("\t");
      if (parts.length < 3) {
        continue;
      }
      if (parts[0] !== "-") {
        additions += Number.parseInt(parts[0], 10) || 0;
      }
      if (parts[1] !== "-") {
        deletions += Number.parseInt(parts[1], 10) || 0;
      }
      changedFiles += 1;
    }

    target.set(sha, {
      sha,
      authorName,
      authorEmail: normalizeEmail(authorEmail),
      authoredAt,
      committedAt,
      subject,
      body: body ?? "",
      additions,
      deletions,
      changedFiles,
      isMerge: Boolean(parents && parents.trim().includes(" ")),
      refNames: [refName],
      refSet: new Set([refName]),
    });
  }
}

function buildContributorId(login: string | null | undefined, name: string, email: string): string {
  const normalizedLogin = normalizeLogin(login);
  if (normalizedLogin) {
    return `login:${normalizedLogin}`;
  }
  if (email) {
    return `email:${normalizeEmail(email)}`;
  }
  return `name:${name.trim().toLowerCase()}`;
}

function deriveLoginFromEmail(email: string): string | null {
  const normalized = normalizeEmail(email);
  const noreplyMatch = normalized.match(/^(?:\d+\+)?([a-z0-9-]+)@users\.noreply\.github\.com$/i);
  if (noreplyMatch) {
    return noreplyMatch[1].toLowerCase();
  }
  return null;
}

function normalizeLogin(login: string | null | undefined): string | null {
  if (!login) {
    return null;
  }
  const trimmed = login.trim().toLowerCase();
  return trimmed || null;
}

function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

function buildAliasKey(login: string | null | undefined, name: string, email: string): string {
  return [normalizeLogin(login) ?? "", name.trim().toLowerCase(), normalizeEmail(email)].join("|");
}

function blankMetrics(): Metrics {
  return {
    commits: 0,
    additions: 0,
    deletions: 0,
    changedFiles: 0,
    prsOpened: 0,
    prsMerged: 0,
    reviewsSubmitted: 0,
    issuesOpened: 0,
    issuesClosed: 0,
    releases: 0,
    workflowRuns: 0,
    workflowFailures: 0,
  };
}

function ensureRepoMetrics(target: Map<string, RepoMetrics>, repoId: string): RepoMetrics {
  const existing = target.get(repoId);
  if (existing) {
    return existing;
  }
  const created: RepoMetrics = {
    ...blankMetrics(),
    latestActivityAt: null,
  };
  target.set(repoId, created);
  return created;
}

function ensureContributorMetrics(target: Map<string, ContributorMetrics>, contributorId: string, repoId: string): ContributorMetrics {
  let existing = target.get(contributorId);
  if (!existing) {
    existing = {
      ...blankMetrics(),
      latestActivityAt: null,
      repoIds: new Set<string>(),
    };
    target.set(contributorId, existing);
  }
  existing.repoIds.add(repoId);
  return existing;
}

function bumpCommitMetrics(target: Metrics | RepoMetrics | ContributorMetrics, commit: Pick<CommitFact, "authoredAt" | "additions" | "deletions" | "changedFiles">): void {
  target.commits += 1;
  target.additions += commit.additions;
  target.deletions += commit.deletions;
  target.changedFiles += commit.changedFiles;
  if ("latestActivityAt" in target) {
    if (!target.latestActivityAt || commit.authoredAt > target.latestActivityAt) {
      target.latestActivityAt = commit.authoredAt;
    }
  }
}

function makeBucketKey(entityType: "repo" | "contributor", entityId: string, bucket: string): string {
  return `${entityType}|${entityId}|${bucket}`;
}

function ensureBucket(target: Map<string, Metrics>, key: string): Metrics {
  const existing = target.get(key);
  if (existing) {
    return existing;
  }
  const created = blankMetrics();
  target.set(key, created);
  return created;
}

function bucketStart(iso: string, grain: AnalyticsGrain): string {
  const date = new Date(iso);
  if (grain === "day") {
    return date.toISOString().slice(0, 10);
  }
  if (grain === "week") {
    const utcDay = date.getUTCDay();
    const mondayShift = (utcDay + 6) % 7;
    date.setUTCDate(date.getUTCDate() - mondayShift);
    return date.toISOString().slice(0, 10);
  }
  date.setUTCDate(1);
  return date.toISOString().slice(0, 10);
}

async function writeBuckets(
  store: LocalStore,
  table: "github_daily_rollups" | "github_weekly_rollups" | "github_monthly_rollups",
  repoBuckets: Map<string, Metrics>,
  contributorBuckets: Map<string, Metrics>,
): Promise<void> {
  for (const [key, metrics] of [...repoBuckets.entries(), ...contributorBuckets.entries()]) {
    const [entityType, entityId, bucket] = key.split("|");
    await store.run(
      `
        insert into ${table} (
          entity_type,
          entity_id,
          bucket_start,
          commits,
          additions,
          deletions,
          changed_files,
          prs_opened,
          prs_merged,
          reviews_submitted,
          issues_opened,
          issues_closed,
          releases,
          workflow_runs,
          workflow_failures
        )
        values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
      `,
      entityType,
      entityId,
      bucket,
      metrics.commits,
      metrics.additions,
      metrics.deletions,
      metrics.changedFiles,
      metrics.prsOpened,
      metrics.prsMerged,
      metrics.reviewsSubmitted,
      metrics.issuesOpened,
      metrics.issuesClosed,
      metrics.releases,
      metrics.workflowRuns,
      metrics.workflowFailures,
    );
  }
}

function matchesRepositoryFilters(repository: GitHubRepositoryRecord, filters: AnalyticsFilters): boolean {
  if (!filters.includeArchived && repository.isArchived) {
    return false;
  }
  if (!filters.includeForks && repository.isFork) {
    return false;
  }
  if (filters.owner && repository.owner !== filters.owner) {
    return false;
  }
  if (filters.repository && repository.fullName !== filters.repository && repository.name !== filters.repository) {
    return false;
  }
  return true;
}

function matchesContributorFilters(contributor: ContributorRecord, filters: AnalyticsFilters): boolean {
  if (!filters.includeBots && contributor.displayName.toLowerCase().includes("[bot]")) {
    return false;
  }
  if (filters.contributor) {
    const needle = filters.contributor.toLowerCase();
    const login = contributor.canonicalLogin?.toLowerCase() ?? "";
    const name = contributor.displayName.toLowerCase();
    if (needle !== login && needle !== name) {
      return false;
    }
  }
  return true;
}

function buildSummary(
  filters: AnalyticsFilters,
  repositories: GitHubRepositoryRecord[],
  contributors: ContributorRecord[],
  commits: CommitFact[],
  trends: TrendPoint[],
): AnalyticsSummarySnapshot {
  const additions = commits.reduce((sum, commit) => sum + commit.additions, 0);
  const deletions = commits.reduce((sum, commit) => sum + commit.deletions, 0);
  const latestTrend = trends.at(-1);
  return {
    generatedAt: nowIso(),
    filters,
    totals: {
      activeRepos: repositories.length,
      activeContributors: contributors.length,
      commits: commits.length,
      additions,
      deletions,
      netLoc: additions - deletions,
      prsOpened: 0,
      prsMerged: 0,
      reviewsSubmitted: 0,
      issuesOpened: 0,
      issuesClosed: 0,
      releases: 0,
      workflowRuns: 0,
      workflowFailures: 0,
    },
    biggestRepos: repositories
      .slice()
      .sort((left, right) => right.commitCount - left.commitCount)
      .slice(0, 5)
      .map((repository) => ({
        fullName: repository.fullName,
        commits: repository.commitCount,
        netLoc: repository.additions - repository.deletions,
        mergedPrs: repository.mergedPrs,
      })),
    biggestContributors: contributors
      .slice()
      .sort((left, right) => right.commitCount - left.commitCount)
      .slice(0, 5)
      .map((contributor) => ({
        contributor: contributor.canonicalLogin ?? contributor.displayName,
        commits: contributor.commitCount,
        netLoc: contributor.additions - contributor.deletions,
        prsMerged: contributor.prsMerged,
      })),
    trendHighlights: latestTrend
      ? [
          { label: "Latest bucket commits", value: String(latestTrend.commits) },
          { label: "Latest bucket net LOC", value: String(latestTrend.netLoc) },
        ]
      : [],
  };
}

function monthsAgoIso(months: number): string {
  const date = new Date();
  date.setUTCMonth(date.getUTCMonth() - months);
  return date.toISOString();
}

function emptySummary(): AnalyticsSummarySnapshot {
  return {
    generatedAt: nowIso(),
    filters: {
      grain: "day",
      includeBots: false,
      includeArchived: false,
      includeForks: false,
    },
    totals: {
      activeRepos: 0,
      activeContributors: 0,
      commits: 0,
      additions: 0,
      deletions: 0,
      netLoc: 0,
      prsOpened: 0,
      prsMerged: 0,
      reviewsSubmitted: 0,
      issuesOpened: 0,
      issuesClosed: 0,
      releases: 0,
      workflowRuns: 0,
      workflowFailures: 0,
    },
    biggestRepos: [],
    biggestContributors: [],
    trendHighlights: [],
  };
}
