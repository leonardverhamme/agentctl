import { describe, expect, it } from "vitest";

import { createApp } from "../src/app";

describe("createApp", () => {
  it("serves health and queue routes", async () => {
    const context = {
      notion: { isConfigured: () => false, bootstrapSchema: async () => ({}) },
      googleAuth: { isConfigured: () => false, getAuthorizationUrl: () => "https://example.com", exchangeCodeForToken: async () => "me@example.com" },
      reconcile: {
        queue: () => ({
          decisions: [],
          latestRuns: [],
        }),
        applyDecision: async () => null,
      },
    } as any;

    const app = createApp(context);

    const health = await app.inject({ method: "GET", url: "/health" });
    expect(health.statusCode).toBe(200);
    expect(health.json()).toMatchObject({
      status: "ok",
      notionConfigured: false,
      googleConfigured: false,
      queueSize: 0,
    });

    const queue = await app.inject({ method: "GET", url: "/queue" });
    expect(queue.statusCode).toBe(200);
    expect(queue.json()).toEqual({ decisions: [], latestRuns: [] });

    await app.close();
  });
});
