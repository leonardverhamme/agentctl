import { createContext } from "./context";
import { runJob } from "./jobs";
import { createApp } from "./app";

async function main() {
  const context = await createContext();
  const app = createApp(context);

  await app.listen({
    host: context.config.appHost,
    port: context.config.appPort,
  });

  void startupCatchUp(context);

  const shutdown = async () => {
    await app.close();
    await context.close();
    process.exit(0);
  };

  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

async function startupCatchUp(context: Awaited<ReturnType<typeof createContext>>) {
  if (!context.googleAuth.isConfigured()) {
    return;
  }

  const sequence = ["gmail-sync", "calendar-sync", "reconcile"] as const;
  for (const jobName of sequence) {
    try {
      await runJob(jobName, context);
    } catch (error) {
      console.error(`[startup] ${jobName} failed:`, (error as Error).message);
    }
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
