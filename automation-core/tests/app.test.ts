import { describe, expect, it } from "vitest";

import { createApp } from "../src/app";

describe("createApp", () => {
  it("serves the operator console, health, and queue routes", async () => {
    const snapshot = {
      decisions: [
        {
          decisionId: "dec-1",
          notionPageId: "page-1",
          sourceType: "email",
          sourceExternalId: "thread-1",
          status: "pending",
          title: "Follow up on pilot rollout timeline",
          gmailUrl: "https://mail.google.com/mail/u/0/#inbox/thread-1",
          notionUrl: "https://www.notion.so/page-1",
          readGateBlocked: true,
          payload: {
            decisionId: "dec-1",
            sourceType: "email",
            sourceExternalId: "thread-1",
            title: "Follow up on pilot rollout timeline",
            reviewReason: "Unread inbound mail from an active opportunity.",
            confidence: 0.58,
            proposedState: "state/action",
            dueAt: "2026-04-18T09:00:00.000Z",
            gmailUrl: "https://mail.google.com/mail/u/0/#inbox/thread-1",
            notionUrl: "https://www.notion.so/page-1",
            readGateBlocked: true,
            diff: [
              { field: "follow_up.status", from: "Waiting", to: "Needs action" },
              { field: "follow_up.due_at", from: "2026-04-20T09:00:00.000Z", to: "2026-04-18T09:00:00.000Z" },
            ],
            target: {
              accountId: "acct-1",
              accountName: "Acme",
              followUpId: "follow-1",
              followUpName: "Pilot rollout",
            },
            summary: "Customer replied with a new dependency and asked for a shorter turnaround.",
            createdAt: "2026-04-18T08:15:00.000Z",
          },
          createdAt: "2026-04-18T08:15:00.000Z",
          updatedAt: "2026-04-18T08:15:00.000Z",
        },
      ],
      latestRuns: [
        {
          id: "run-1",
          jobName: "reconcile",
          status: "success",
          detailsJson: "{}",
          startedAt: "2026-04-18T08:00:00.000Z",
          finishedAt: "2026-04-18T08:02:00.000Z",
        },
      ],
    };

    const analytics = {
      filters: {
        owner: null,
        repository: null,
        contributor: null,
        dateFrom: null,
        dateTo: null,
        grain: "day",
        includeBots: false,
        includeArchived: false,
        includeForks: false,
        metricFamily: null,
      },
      summary: {
        generatedAt: "2026-04-18T08:00:00.000Z",
        filters: {
          grain: "day",
          includeBots: false,
          includeArchived: false,
          includeForks: false,
        },
        totals: {
          activeRepos: 2,
          activeContributors: 1,
          commits: 14,
          additions: 320,
          deletions: 80,
          netLoc: 240,
          prsOpened: 3,
          prsMerged: 2,
          reviewsSubmitted: 5,
          issuesOpened: 1,
          issuesClosed: 1,
          releases: 1,
          workflowRuns: 4,
          workflowFailures: 1,
        },
        biggestRepos: [{ fullName: "acme/portal", commits: 9, netLoc: 180, mergedPrs: 2 }],
        biggestContributors: [{ contributor: "Leonard Verhamme", commits: 14, netLoc: 240, prsMerged: 2 }],
        trendHighlights: [
          { label: "Active repos", value: "2" },
          { label: "Commits", value: "14" },
          { label: "Net LOC", value: "+240" },
        ],
      },
      repositories: [
        {
          repoId: "repo-1",
          owner: "acme",
          name: "portal",
          fullName: "acme/portal",
          description: "Customer portal",
          visibility: "private",
          language: "TypeScript",
          defaultBranch: "main",
          isArchived: false,
          isFork: false,
          htmlUrl: "https://github.com/acme/portal",
          cloneUrl: "git@github.com:acme/portal.git",
          pushedAt: "2026-04-18T07:45:00.000Z",
          createdAt: "2025-01-01T00:00:00.000Z",
          updatedAt: "2026-04-18T07:45:00.000Z",
          firstSyncedAt: "2026-04-18T07:00:00.000Z",
          lastSyncedAt: "2026-04-18T08:00:00.000Z",
          mirrorPath: "C:/repo.git",
          commitCount: 9,
          additions: 250,
          deletions: 70,
          changedFiles: 18,
          openPrs: 1,
          mergedPrs: 2,
          openIssues: 1,
          releases: 1,
          workflowFailures: 1,
          latestActivityAt: "2026-04-18T07:45:00.000Z",
        },
      ],
      contributors: [
        {
          contributorId: "contrib-1",
          canonicalLogin: "leonard",
          displayName: "Leonard Verhamme",
          avatarUrl: null,
          firstSeenAt: "2025-01-01T00:00:00.000Z",
          lastActiveAt: "2026-04-18T07:45:00.000Z",
          repoCount: 1,
          commitCount: 14,
          additions: 320,
          deletions: 80,
          changedFiles: 18,
          prsOpened: 3,
          prsMerged: 2,
          reviewsSubmitted: 5,
          issuesOpened: 1,
          workflowRuns: 4,
          latestActivityAt: "2026-04-18T07:45:00.000Z",
        },
      ],
      commits: [
        {
          repoId: "acme/portal",
          sha: "abcdef1234567890",
          authorContributorId: "contrib-1",
          authorLogin: "leonard",
          authorName: "Leonard Verhamme",
          authorEmail: "leonard@example.com",
          authoredAt: "2026-04-18T07:30:00.000Z",
          committedAt: "2026-04-18T07:30:00.000Z",
          subject: "Tighten dashboard density",
          body: "",
          additions: 50,
          deletions: 10,
          changedFiles: 4,
          isMerge: false,
          htmlUrl: "https://github.com/acme/portal/commit/abcdef1234567890",
          refNames: ["main"],
        },
      ],
      pullRequests: [],
      reviews: [],
      issues: [],
      releases: [],
      workflowRuns: [],
      trends: [
        {
          bucketStart: "2026-04-12",
          commits: 6,
          additions: 120,
          deletions: 30,
          netLoc: 90,
          prsOpened: 1,
          prsMerged: 1,
          reviewsSubmitted: 2,
          issuesOpened: 0,
          issuesClosed: 0,
          releases: 0,
          workflowRuns: 1,
          workflowFailures: 0,
        },
        {
          bucketStart: "2026-04-18",
          commits: 8,
          additions: 200,
          deletions: 50,
          netLoc: 150,
          prsOpened: 2,
          prsMerged: 1,
          reviewsSubmitted: 3,
          issuesOpened: 1,
          issuesClosed: 1,
          releases: 1,
          workflowRuns: 3,
          workflowFailures: 1,
        },
      ],
      weeklyBrief: {
        weekStart: "2026-04-12",
        generatedAt: "2026-04-18T08:00:00.000Z",
        headline: "Working set overview",
        summary: "Review the active repos and contributors.",
        topRepositories: [{ fullName: "acme/portal", commits: 9, netLoc: 180 }],
        topContributors: [{ contributor: "Leonard Verhamme", commits: 14, netLoc: 240 }],
        workflowAlerts: [{ fullName: "acme/portal", failures: 1 }],
        notionUrl: null,
      },
      topRepoRollups: [],
    };

    const context = {
      notion: { isConfigured: () => false, bootstrapSchema: async () => ({}) },
      googleAuth: { isConfigured: () => false, getAuthorizationUrl: () => "https://example.com", exchangeCodeForToken: async () => "me@example.com" },
      reconcile: {
        queue: async () => snapshot,
        applyDecision: async () => null,
      },
      githubAnalytics: {
        parseFilters: () => analytics.filters,
        queryAnalytics: async () => analytics,
      },
    } as any;

    const app = createApp(context);

    const dashboard = await app.inject({ method: "GET", url: "/" });
    expect(dashboard.statusCode).toBe(200);
    expect(dashboard.headers["content-type"]).toContain("text/html");
    expect(dashboard.body).toContain("Operator console");
    expect(dashboard.body).toContain("Queue overview");
    expect(dashboard.body).toContain("Trend overview");
    expect(dashboard.body).toContain("Queue mix");
    expect(dashboard.body).toContain("Decision overview");
    expect(dashboard.body).toContain("Proposed changes");
    expect(dashboard.body).toContain("Read gate");
    expect(dashboard.body).toContain("Open Gmail");
    expect(dashboard.body).toContain("follow_up.status");
    expect(dashboard.body).toContain('rel="icon" href="/favicon.ico"');

    const favicon = await app.inject({ method: "GET", url: "/favicon.ico" });
    expect(favicon.statusCode).toBe(200);
    expect(favicon.headers["content-type"]).toContain("image/svg+xml");
    expect(favicon.body).toContain("<svg");

    const health = await app.inject({ method: "GET", url: "/health" });
    expect(health.statusCode).toBe(200);
    expect(health.json()).toMatchObject({
      status: "ok",
      notionConfigured: false,
      googleConfigured: false,
      queueSize: 1,
    });

    const queue = await app.inject({ method: "GET", url: "/queue" });
    expect(queue.statusCode).toBe(200);
    expect(queue.json()).toEqual(snapshot);

    const analyticsPage = await app.inject({ method: "GET", url: "/analytics" });
    expect(analyticsPage.statusCode).toBe(200);
    expect(analyticsPage.body).toContain("GitHub analytics");
    expect(analyticsPage.body).toContain("Operator dashboard");
    expect(analyticsPage.body).toContain("Trend");
    expect(analyticsPage.body).toContain("Repo table");
    expect(analyticsPage.body).toContain("People table");
    expect(analyticsPage.body).toContain("Raw fact explorer");
    expect(analyticsPage.body).toContain("Working set overview");

    const analyticsSummary = await app.inject({ method: "GET", url: "/analytics/summary" });
    expect(analyticsSummary.statusCode).toBe(200);
    expect(analyticsSummary.json()).toMatchObject({
      totals: {
        activeRepos: 2,
        commits: 14,
      },
    });

    await app.close();
  });
});
