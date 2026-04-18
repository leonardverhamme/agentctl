import Fastify from "fastify";

import { JOB_NAMES, JobName } from "./types";
import { AppContext } from "./context";
import { runJob } from "./jobs";
import { renderDashboard } from "./web/render";

export function createApp(context: AppContext) {
  const app = Fastify({ logger: false });

  app.get("/", async (_request, reply) => {
    reply.header("content-type", "text/html; charset=utf-8");
    return renderDashboard(context.reconcile.queue());
  });

  app.get("/health", async () => ({
    status: "ok",
    notionConfigured: context.notion.isConfigured(),
    googleConfigured: context.googleAuth.isConfigured(),
    queueSize: context.reconcile.queue().decisions.length,
  }));

  app.get("/queue", async () => context.reconcile.queue());

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
