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

    const context = {
      notion: { isConfigured: () => false, bootstrapSchema: async () => ({}) },
      googleAuth: { isConfigured: () => false, getAuthorizationUrl: () => "https://example.com", exchangeCodeForToken: async () => "me@example.com" },
      reconcile: {
        queue: () => snapshot,
        applyDecision: async () => null,
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

    await app.close();
  });
});
