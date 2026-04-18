import { describe, expect, it } from "vitest";

import { runJob } from "../src/jobs";

describe("runJob", () => {
  it("runs the morning brief job against a mocked Notion context", async () => {
    const jobRuns: Array<{ id: string; result?: unknown }> = [];
    const context = {
      notion: {
        isConfigured: () => true,
        listPendingDecisions: async () => [
          { title: "Inbox triage — Acme", summary: "Unread inbound mail", url: "https://notion.so/decision" },
        ],
        listOpenFollowUps: async () => [
          { title: "Follow-up — Acme", nextAction: "Reply tomorrow", url: "https://notion.so/followup" },
        ],
        createBrief: async (title: string, briefType: string, generatedBy: string, summary: string, paragraphs: string[]) => ({
          id: "brief-1",
          url: "https://notion.so/brief-1",
          title,
          briefType,
          generatedBy,
          summary,
          paragraphs,
        }),
      },
      store: {
        startJobRun: (name: string) => {
          const id = `run-${name}`;
          jobRuns.push({ id });
          return id;
        },
        finishJobRun: (id: string, result: unknown) => {
          const run = jobRuns.find((entry) => entry.id === id);
          if (run) {
            run.result = result;
          }
        },
      },
    } as any;

    const result = await runJob("morning-brief", context);
    expect(result.status).toBe("success");
    expect(result.stats).toMatchObject({ pending: 1, followUps: 1 });
    expect(jobRuns[0]?.result).toBeTruthy();
  });

  it("dispatches GitHub analytics jobs to the analytics service", async () => {
    const jobRuns: Array<{ id: string; result?: unknown }> = [];
    const githubAnalytics = {
      discoverRepositories: async () => ({ scanned: 3, upserted: 2, skipped: 1 }),
      backfillAnalytics: async () => ({ repositories: 2, commits: 8 }),
      syncAnalytics: async () => ({ repositories: 1, commits: 4 }),
      rollupAnalytics: async () => ({ repositories: 2, contributors: 1, commits: 12 }),
      syncNotionReporting: async () => ({ configured: false, repositories: 0, contributors: 0, weeklySnapshots: 0, monthlySnapshots: 0 }),
      createWeeklyBrief: async () => null,
    };
    const context = {
      notion: {
        isConfigured: () => false,
      },
      githubAnalytics,
      store: {
        startJobRun: (name: string) => {
          const id = `run-${name}`;
          jobRuns.push({ id });
          return id;
        },
        finishJobRun: (id: string, result: unknown) => {
          const run = jobRuns.find((entry) => entry.id === id);
          if (run) {
            run.result = result;
          }
        },
      },
    } as any;

    const discover = await runJob("github-discover", context);
    const backfill = await runJob("github-backfill", context);
    const sync = await runJob("github-sync", context);
    const rollup = await runJob("github-rollup", context);
    const notionSync = await runJob("github-notion-sync", context);
    const weeklyBrief = await runJob("github-weekly-brief", context);

    expect(discover).toMatchObject({ status: "success", stats: { scanned: 3, upserted: 2, skipped: 1 } });
    expect(backfill).toMatchObject({ status: "success", stats: { repositories: 2, commits: 8 } });
    expect(sync).toMatchObject({ status: "success", stats: { repositories: 1, commits: 4 } });
    expect(rollup).toMatchObject({ status: "success", stats: { repositories: 2, contributors: 1, commits: 12 } });
    expect(notionSync).toMatchObject({ status: "warning", stats: { configured: false } });
    expect(weeklyBrief).toMatchObject({ status: "warning", stats: { generated: false } });
    expect(jobRuns).toHaveLength(6);
  });
});
