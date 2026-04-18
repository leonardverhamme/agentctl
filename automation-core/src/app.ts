import Fastify from "fastify";

import { JOB_NAMES, JobName } from "./types";
import { AppContext } from "./context";
import { runJob } from "./jobs";
import { renderGitHubAnalytics } from "./web/github-dashboard";
import { renderDashboard } from "./web/render";

const FAVICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#1f4f43"/>
  <path d="M20 23h24v18H20z" fill="none" stroke="#f3f2ed" stroke-width="4" stroke-linejoin="round"/>
  <path d="M24 23v-4a8 8 0 0 1 16 0v4" fill="none" stroke="#f3f2ed" stroke-width="4" stroke-linecap="round"/>
  <circle cx="32" cy="32" r="3" fill="#f3f2ed"/>
</svg>`;

export function createApp(context: AppContext) {
  const app = Fastify({ logger: false });

  app.get("/", async (_request, reply) => {
    reply.header("content-type", "text/html; charset=utf-8");
    return renderDashboard(await context.reconcile.queue());
  });

  app.get("/favicon.ico", async (_request, reply) => {
    reply.header("cache-control", "public, max-age=604800, immutable");
    reply.type("image/svg+xml; charset=utf-8");
    return FAVICON_SVG;
  });

  app.get("/health", async () => ({
    status: "ok",
    notionConfigured: context.notion.isConfigured(),
    googleConfigured: context.googleAuth.isConfigured(),
    queueSize: (await context.reconcile.queue()).decisions.length,
  }));

  app.get("/queue", async () => context.reconcile.queue());

  app.get("/analytics", async (request, reply) => {
    reply.header("content-type", "text/html; charset=utf-8");
    const data = await context.githubAnalytics.queryAnalytics(context.githubAnalytics.parseFilters(request.query as Record<string, unknown>));
    return renderGitHubAnalytics(data);
  });

  app.get("/analytics/summary", async (request) =>
    (await context.githubAnalytics.queryAnalytics(context.githubAnalytics.parseFilters(request.query as Record<string, unknown>))).summary,
  );

  app.get("/analytics/repos", async (request) =>
    (await context.githubAnalytics.queryAnalytics(context.githubAnalytics.parseFilters(request.query as Record<string, unknown>))).repositories,
  );

  app.get("/analytics/contributors", async (request) =>
    (await context.githubAnalytics.queryAnalytics(context.githubAnalytics.parseFilters(request.query as Record<string, unknown>))).contributors,
  );

  app.get("/analytics/commits", async (request) =>
    (await context.githubAnalytics.queryAnalytics(context.githubAnalytics.parseFilters(request.query as Record<string, unknown>))).commits,
  );

  app.get("/analytics/trends", async (request) =>
    (await context.githubAnalytics.queryAnalytics(context.githubAnalytics.parseFilters(request.query as Record<string, unknown>))).trends,
  );

  app.get("/analytics/weekly", async (request) =>
    (await context.githubAnalytics.queryAnalytics(context.githubAnalytics.parseFilters(request.query as Record<string, unknown>))).weeklyBrief,
  );

  app.get("/auth/google/start", async (_request, reply) => {
    const url = context.googleAuth.getAuthorizationUrl();
    return reply.redirect(url);
  });

  app.get<{ Querystring: { code?: string } }>("/auth/google/callback", async (request, reply) => {
    if (!request.query.code) {
      reply.status(400);
      return { error: "Missing OAuth code." };
    }
    const email = await context.googleAuth.exchangeCodeForToken(request.query.code);
    return reply.redirect(`/?connected=${encodeURIComponent(email ?? "google")}`);
  });

  app.post<{ Params: { jobName: JobName } }>("/jobs/:jobName", async (request, reply) => {
    if (!JOB_NAMES.includes(request.params.jobName)) {
      reply.status(404);
      return { error: `Unknown job ${request.params.jobName}` };
    }

    const result = await runJob(request.params.jobName, context);
    return result;
  });

  app.post<{ Params: { decisionId: string } }>("/decisions/:decisionId/approve", async (request, reply) => {
    try {
      const result = await context.reconcile.applyDecision(request.params.decisionId, "approve", request.body as any);
      return result;
    } catch (error) {
      reply.status(409);
      return { error: (error as Error).message };
    }
  });

  app.post<{ Params: { decisionId: string } }>("/decisions/:decisionId/reject", async (request) => {
    return context.reconcile.applyDecision(request.params.decisionId, "reject", request.body as any);
  });

  app.post<{ Params: { decisionId: string } }>("/decisions/:decisionId/snooze", async (request) => {
    return context.reconcile.applyDecision(request.params.decisionId, "snooze", request.body as any);
  });

  app.post("/schema/bootstrap", async () => {
    return context.notion.bootstrapSchema();
  });

  return app;
}
