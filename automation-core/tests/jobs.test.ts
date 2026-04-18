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
});
