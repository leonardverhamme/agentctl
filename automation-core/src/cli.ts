import { Command } from "commander";

import { createContext } from "./context";
import { JOB_NAMES } from "./types";
import { runJob } from "./jobs";

async function main() {
  const program = new Command();
  program.name("automation-core");

  program
    .command("health")
    .description("Print the local bridge health payload.")
    .action(async () => {
      const context = createContext();
      try {
        console.log(
          JSON.stringify(
            {
              status: "ok",
              notionConfigured: context.notion.isConfigured(),
              googleConfigured: context.googleAuth.isConfigured(),
              queueSize: context.reconcile.queue().decisions.length,
            },
            null,
            2,
          ),
        );
      } finally {
        context.close();
      }
    });

  program
    .command("schema-bootstrap")
    .description("Create the hidden Notion technical data sources and additive CRM fields.")
    .action(async () => {
      const context = createContext();
      try {
        const result = await context.notion.bootstrapSchema();
        console.log(JSON.stringify(result, null, 2));
      } finally {
        context.close();
      }
    });

  program
    .command("job")
    .description("Run one bridge job.")
    .argument("<name>", `One of: ${JOB_NAMES.join(", ")}`)
    .action(async (name: string) => {
      if (!JOB_NAMES.includes(name as any)) {
        throw new Error(`Unknown job ${name}`);
      }
      const context = createContext();
      try {
        const result = await runJob(name as any, context);
        console.log(JSON.stringify(result, null, 2));
      } finally {
        context.close();
      }
    });

  program
    .command("queue")
    .description("Print the current approval queue.")
    .action(async () => {
      const context = createContext();
      try {
        console.log(JSON.stringify(context.reconcile.queue(), null, 2));
      } finally {
        context.close();
      }
    });

  program
    .command("decision")
    .description("Apply an approve/reject/snooze action to a decision.")
    .argument("<action>", "approve | reject | snooze")
    .argument("<decisionId>", "Decision identifier")
    .option("--note <note>", "Optional operator note")
    .option("--override-read-gate", "Override the human-read gate when approving")
    .option("--snoozed-until <iso>", "Optional ISO timestamp for snooze")
    .action(async (action: string, decisionId: string, options: Record<string, string | boolean>) => {
      if (!["approve", "reject", "snooze"].includes(action)) {
        throw new Error(`Unknown decision action ${action}`);
      }
      const context = createContext();
      try {
        const result = await context.reconcile.applyDecision(decisionId, action as any, {
          note: typeof options.note === "string" ? options.note : undefined,
          overrideReadGate: Boolean(options.overrideReadGate),
          snoozedUntil: typeof options.snoozedUntil === "string" ? options.snoozedUntil : undefined,
        });
        console.log(JSON.stringify(result, null, 2));
      } finally {
        context.close();
      }
    });

  await program.parseAsync(process.argv);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
