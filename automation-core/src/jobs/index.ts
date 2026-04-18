import { AppContext } from "../context";
import { addDays, nowIso } from "../lib/time";
import { EmailThreadSnapshot, JobName, JobResult } from "../types";

export async function runJob(jobName: JobName, context: AppContext): Promise<JobResult> {
  const runId = context.store.startJobRun(jobName);
  const startedAt = nowIso();

  try {
    const result = await execute(jobName, context, startedAt);
    context.store.finishJobRun(runId, result);
    return result;
  } catch (error) {
    const failedAt = nowIso();
    const result: JobResult = {
      jobName,
      status: "error",
      startedAt,
      finishedAt: failedAt,
      notes: [(error as Error).message],
      stats: {},
    };
    context.store.finishJobRun(runId, result);
    throw error;
  }
}

async function execute(jobName: JobName, context: AppContext, startedAt: string): Promise<JobResult> {
  switch (jobName) {
    case "gmail-sync":
      return gmailSyncJob(context, startedAt);
    case "calendar-sync":
      return calendarSyncJob(context, startedAt);
    case "reconcile":
      return reconcileJob(context, startedAt);
    case "meeting-wrap":
      return meetingWrapJob(context, startedAt);
    case "morning-brief":
      return morningBriefJob(context, startedAt);
    case "weekly-plan":
      return weeklyPlanJob(context, startedAt);
    case "weekly-review":
      return weeklyReviewJob(context, startedAt);
    case "hygiene-sweep":
      return hygieneSweepJob(context, startedAt);
    default: {
      const exhaustive: never = jobName;
      throw new Error(`Unsupported job ${exhaustive}`);
    }
  }
}

async function gmailSyncJob(context: AppContext, startedAt: string): Promise<JobResult> {
  const sync = await context.gmail.syncMailbox();
  if (context.notion.isConfigured()) {
    for (const thread of sync.threads) {
      await context.notion.upsertEmailThread(thread);
    }
  }

  return {
    jobName: "gmail-sync",
    status: sync.fallbackUsed ? "warning" : "success",
    startedAt,
    finishedAt: nowIso(),
    notes: sync.fallbackUsed ? ["Gmail history cursor expired; fell back to a bounded full sync."] : [],
    stats: {
      mode: sync.mode,
      threads: sync.threads.length,
      fallbackUsed: sync.fallbackUsed,
    },
  };
}

async function calendarSyncJob(context: AppContext, startedAt: string): Promise<JobResult> {
  const sync = await context.calendar.syncCalendar();
  if (context.notion.isConfigured()) {
    for (const event of sync.events) {
      await context.notion.upsertCalendarEvent(event);
      await context.notion.createMeetingNote(event);
    }
  }

  return {
    jobName: "calendar-sync",
    status: sync.fallbackUsed ? "warning" : "success",
    startedAt,
    finishedAt: nowIso(),
    notes: sync.fallbackUsed ? ["Calendar sync token expired; fell back to a bounded full sync."] : [],
    stats: {
      mode: sync.mode,
      events: sync.events.length,
      fallbackUsed: sync.fallbackUsed,
    },
  };
}

async function reconcileJob(context: AppContext, startedAt: string): Promise<JobResult> {
  const threads = context.store.listSourceCache<EmailThreadSnapshot>("gmail", "thread");
  const proposals = await context.reconcile.refreshEmailProposals(threads);
  return {
    jobName: "reconcile",
    status: "success",
    startedAt,
    finishedAt: nowIso(),
    notes: [],
    stats: {
      proposals: proposals.length,
      pendingQueue: context.store.listPendingDecisions().length,
    },
  };
}

async function meetingWrapJob(context: AppContext, startedAt: string): Promise<JobResult> {
  const events = context.store.listSourceCache<any>("calendar", "event");
  const proposals = await context.reconcile.refreshMeetingProposals(events);
  return {
    jobName: "meeting-wrap",
    status: "success",
    startedAt,
    finishedAt: nowIso(),
    notes: [],
    stats: {
      proposals: proposals.length,
    },
  };
}

async function morningBriefJob(context: AppContext, startedAt: string): Promise<JobResult> {
  ensureNotionForBriefs(context);
  const pending = await context.notion.listPendingDecisions(12);
  const followUps = await context.notion.listOpenFollowUps(12);
  const summary = `Pending approvals: ${pending.length}. Open follow-ups: ${followUps.length}.`;
  const paragraphs = [
    "Top priorities",
    ...pending.slice(0, 5).map((item, index) => `${index + 1}. ${item.title} — ${item.summary}`),
    "Open follow-ups",
    ...followUps.slice(0, 5).map((item, index) => `${index + 1}. ${item.title} — ${item.nextAction}`),
  ];
  const page = await context.notion.createBrief(
    `Morning brief — ${startedAt.slice(0, 10)}`,
    "Morning Brief",
    "automation-core",
    summary,
    paragraphs,
  );
  return {
    jobName: "morning-brief",
    status: "success",
    startedAt,
    finishedAt: nowIso(),
    notes: page?.url ? [`Created Notion brief ${page.url}`] : [],
    stats: {
      pending: pending.length,
      followUps: followUps.length,
    },
  };
}

async function weeklyPlanJob(context: AppContext, startedAt: string): Promise<JobResult> {
  ensureNotionForBriefs(context);
  const pending = await context.notion.listPendingDecisions(20);
  const followUps = await context.notion.listOpenFollowUps(20);
  const page = await context.notion.createBrief(
    `Weekly plan — ${startedAt.slice(0, 10)}`,
    "Weekly Plan",
    "automation-core",
    `Weekly plan based on ${followUps.length} open follow-ups and ${pending.length} pending approvals.`,
    [
      "This week",
      ...followUps.slice(0, 8).map((item, index) => `${index + 1}. ${item.title} — ${item.nextAction}`),
      "Needs operator review",
      ...pending.slice(0, 8).map((item, index) => `${index + 1}. ${item.title} — ${item.summary}`),
    ],
  );
  return {
    jobName: "weekly-plan",
    status: "success",
    startedAt,
    finishedAt: nowIso(),
    notes: page?.url ? [`Created Notion plan ${page.url}`] : [],
    stats: {
      pending: pending.length,
      followUps: followUps.length,
    },
  };
}

async function weeklyReviewJob(context: AppContext, startedAt: string): Promise<JobResult> {
  ensureNotionForBriefs(context);
  const pending = await context.notion.listPendingDecisions(20);
  const followUps = await context.notion.listOpenFollowUps(20);
  const recentRuns = context.store.listRecentJobRuns(8);
  const page = await context.notion.createBrief(
    `Weekly review — ${startedAt.slice(0, 10)}`,
    "Weekly Review",
    "automation-core",
    `Weekly review generated from current Notion state and recent automation health.`,
    [
      "Automation health",
      ...recentRuns.map((run) => `${run.jobName}: ${run.status}`),
      "Carry-over follow-ups",
      ...followUps.slice(0, 6).map((item, index) => `${index + 1}. ${item.title} — ${item.nextAction}`),
      "Still pending approval",
      ...pending.slice(0, 6).map((item, index) => `${index + 1}. ${item.title} — ${item.summary}`),
    ],
  );
  return {
    jobName: "weekly-review",
    status: "success",
    startedAt,
    finishedAt: nowIso(),
    notes: page?.url ? [`Created Notion review ${page.url}`] : [],
    stats: {
      recentRuns: recentRuns.length,
      pending: pending.length,
      carryOver: followUps.length,
    },
  };
}

async function hygieneSweepJob(context: AppContext, startedAt: string): Promise<JobResult> {
  ensureNotionForBriefs(context);
  const pending = await context.notion.listPendingDecisions(25);
  const followUps = await context.notion.listOpenFollowUps(25);
  const events = await context.notion.listStaleCalendarEvents(12);
  const page = await context.notion.createBrief(
    `Deep audit — ${startedAt.slice(0, 10)}`,
    "Deep Audit",
    "automation-core",
    `Hygiene sweep covering pending approvals, stale follow-ups, and recent meetings.`,
    [
      "Pending approvals",
      ...pending.slice(0, 8).map((item, index) => `${index + 1}. ${item.title} — ${item.summary}`),
      "Open follow-ups",
      ...followUps.slice(0, 8).map((item, index) => `${index + 1}. ${item.title} — ${item.nextAction}`),
      "Recent calendar events",
      ...events.slice(0, 8).map((item, index) => `${index + 1}. ${item.title} — ${item.summary}`),
    ],
  );
  return {
    jobName: "hygiene-sweep",
    status: "success",
    startedAt,
    finishedAt: nowIso(),
    notes: page?.url ? [`Created Notion audit ${page.url}`] : [],
    stats: {
      pending: pending.length,
      followUps: followUps.length,
      events: events.length,
      suggestedReviewBy: addDays(7),
    },
  };
}

function ensureNotionForBriefs(context: AppContext) {
  if (!context.notion.isConfigured()) {
    throw new Error("Notion must be configured for brief-generation jobs.");
  }
}
