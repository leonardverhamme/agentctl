import path from "node:path";

import { z } from "zod";

function envBoolean(defaultValue: boolean) {
  return z
    .string()
    .optional()
    .transform((value) => {
      if (value === undefined || value === "") {
        return defaultValue;
      }
      return ["1", "true", "yes", "on"].includes(value.toLowerCase());
    });
}

const configSchema = z.object({
  appHost: z.string().default("127.0.0.1"),
  appPort: z.coerce.number().int().positive().default(3010),
  appBaseUrl: z.string().url().default("http://localhost:3010"),
  databaseUrl: z
    .string()
    .default("postgresql://postgres:postgres@127.0.0.1:58322/postgres"),
  databaseMigrationsDir: z
    .string()
    .default(path.resolve(process.cwd(), "supabase", "migrations")),
  localApproverName: z.string().default("Local operator"),
  googleClientId: z.string().default(""),
  googleClientSecret: z.string().default(""),
  googleRedirectUri: z.string().url().default("http://localhost:3010/auth/google/callback"),
  googleGmailUser: z.string().default("me"),
  googleAccountEmail: z.string().optional().transform((value) => value ?? ""),
  googleCalendarId: z.string().default("primary"),
  googleGmailFullSyncLimit: z.coerce.number().int().positive().default(150),
  googleCalendarLookbackDays: z.coerce.number().int().positive().default(30),
  googleCalendarLookaheadDays: z.coerce.number().int().positive().default(120),
  githubMirrorRoot: z.string().default(path.resolve(process.cwd(), ".data", "github-mirrors")),
  githubBackfillMonths: z.coerce.number().int().positive().default(12),
  githubOwnerFilters: z.string().optional().transform((value) => value ?? ""),
  githubRepoExcludePatterns: z.string().optional().transform((value) => value ?? ""),
  githubExcludeArchivedByDefault: envBoolean(true),
  githubExcludeForksByDefault: envBoolean(true),
  githubExcludeBotsByDefault: envBoolean(true),
  notionToken: z.string().default(""),
  notionVersion: z.string().default("2026-03-11"),
  notionParentPageId: z.string().optional().transform((value) => value ?? ""),
  notionAccountsDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionContactsDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionOpportunitiesDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionInteractionsDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionFollowupsDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionAiBriefsDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionEmailThreadsDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionCalendarEventsDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionAutomationDecisionsDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionMeetingNotesDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionMeetingNotesTemplateId: z.string().optional().transform((value) => value ?? ""),
  notionGithubRepositoriesDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionGithubContributorsDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionGithubWeeklyRepoSnapshotsDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionGithubWeeklyContributorSnapshotsDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionGithubMonthlyRepoSnapshotsDataSourceId: z.string().optional().transform((value) => value ?? ""),
  notionGithubEngineeringBriefsDataSourceId: z.string().optional().transform((value) => value ?? ""),
});

export type AppConfig = ReturnType<typeof loadConfig>;

export function loadConfig() {
  return configSchema.parse({
    appHost: process.env.APP_HOST,
    appPort: process.env.APP_PORT,
    appBaseUrl: process.env.APP_BASE_URL,
    databaseUrl: process.env.DATABASE_URL,
    databaseMigrationsDir: process.env.DATABASE_MIGRATIONS_DIR,
    localApproverName: process.env.LOCAL_APPROVER_NAME,
    googleClientId: process.env.GOOGLE_CLIENT_ID,
    googleClientSecret: process.env.GOOGLE_CLIENT_SECRET,
    googleRedirectUri: process.env.GOOGLE_REDIRECT_URI,
    googleGmailUser: process.env.GOOGLE_GMAIL_USER,
    googleAccountEmail: process.env.GOOGLE_ACCOUNT_EMAIL,
    googleCalendarId: process.env.GOOGLE_CALENDAR_ID,
    googleGmailFullSyncLimit: process.env.GOOGLE_GMAIL_FULL_SYNC_LIMIT,
    googleCalendarLookbackDays: process.env.GOOGLE_CALENDAR_LOOKBACK_DAYS,
    googleCalendarLookaheadDays: process.env.GOOGLE_CALENDAR_LOOKAHEAD_DAYS,
    githubMirrorRoot: process.env.GITHUB_MIRROR_ROOT,
    githubBackfillMonths: process.env.GITHUB_BACKFILL_MONTHS,
    githubOwnerFilters: process.env.GITHUB_OWNER_FILTERS,
    githubRepoExcludePatterns: process.env.GITHUB_REPO_EXCLUDE_PATTERNS,
    githubExcludeArchivedByDefault: process.env.GITHUB_EXCLUDE_ARCHIVED_BY_DEFAULT,
    githubExcludeForksByDefault: process.env.GITHUB_EXCLUDE_FORKS_BY_DEFAULT,
    githubExcludeBotsByDefault: process.env.GITHUB_EXCLUDE_BOTS_BY_DEFAULT,
    notionToken: process.env.NOTION_TOKEN,
    notionVersion: process.env.NOTION_VERSION,
    notionParentPageId: process.env.NOTION_PARENT_PAGE_ID,
    notionAccountsDataSourceId: process.env.NOTION_ACCOUNTS_DATA_SOURCE_ID,
    notionContactsDataSourceId: process.env.NOTION_CONTACTS_DATA_SOURCE_ID,
    notionOpportunitiesDataSourceId: process.env.NOTION_OPPORTUNITIES_DATA_SOURCE_ID,
    notionInteractionsDataSourceId: process.env.NOTION_INTERACTIONS_DATA_SOURCE_ID,
    notionFollowupsDataSourceId: process.env.NOTION_FOLLOWUPS_DATA_SOURCE_ID,
    notionAiBriefsDataSourceId: process.env.NOTION_AI_BRIEFS_DATA_SOURCE_ID,
    notionEmailThreadsDataSourceId: process.env.NOTION_EMAIL_THREADS_DATA_SOURCE_ID,
    notionCalendarEventsDataSourceId: process.env.NOTION_CALENDAR_EVENTS_DATA_SOURCE_ID,
    notionAutomationDecisionsDataSourceId: process.env.NOTION_AUTOMATION_DECISIONS_DATA_SOURCE_ID,
    notionMeetingNotesDataSourceId: process.env.NOTION_MEETING_NOTES_DATA_SOURCE_ID,
    notionMeetingNotesTemplateId: process.env.NOTION_MEETING_NOTES_TEMPLATE_ID,
    notionGithubRepositoriesDataSourceId: process.env.NOTION_GITHUB_REPOSITORIES_DATA_SOURCE_ID,
    notionGithubContributorsDataSourceId: process.env.NOTION_GITHUB_CONTRIBUTORS_DATA_SOURCE_ID,
    notionGithubWeeklyRepoSnapshotsDataSourceId: process.env.NOTION_GITHUB_WEEKLY_REPO_SNAPSHOTS_DATA_SOURCE_ID,
    notionGithubWeeklyContributorSnapshotsDataSourceId: process.env.NOTION_GITHUB_WEEKLY_CONTRIBUTOR_SNAPSHOTS_DATA_SOURCE_ID,
    notionGithubMonthlyRepoSnapshotsDataSourceId: process.env.NOTION_GITHUB_MONTHLY_REPO_SNAPSHOTS_DATA_SOURCE_ID,
    notionGithubEngineeringBriefsDataSourceId: process.env.NOTION_GITHUB_ENGINEERING_BRIEFS_DATA_SOURCE_ID,
  });
}

export const MANAGED_GMAIL_LABELS = [
  "triage/new",
  "triage/pending-review",
  "state/action",
  "state/waiting",
  "state/scheduled",
  "state/reference",
  "state/ignored",
  "system/linked",
] as const;

export const BUSINESS_PROPERTY_NAMES = {
  accounts: {
    title: "Account",
    domains: "Known domains",
  },
  contacts: {
    title: "Full name",
    primaryEmail: "Primary email",
  },
  opportunities: {
    title: "Opportunity",
    stage: "Stage",
    accountRelation: "Account",
  },
  interactions: {
    title: "Interaction",
    sourceExternalId: "Source external ID",
    sourceProvider: "Source provider",
    summary: "Summary",
    explicitNextStep: "Explicit next step",
    followUpNeeded: "Follow-up needed",
    accountRelation: "Account",
    contactRelation: "Contact",
    opportunityRelation: "Opportunity",
    interactionDate: "Interaction date",
    type: "Interaction Type",
  },
  followups: {
    title: "Follow-up",
    sourceExternalId: "Source external ID",
    sourceProvider: "Source provider",
    nextAction: "Next action",
    nextActionDue: "Next action due",
    waitingOn: "Waiting on",
    status: "Status",
    accountRelation: "Account",
    contactRelation: "Contact",
    opportunityRelation: "Opportunity",
  },
  aiBriefs: {
    title: "Brief",
    briefType: "Brief Type",
    briefDate: "Brief date",
    periodStart: "Period start",
    periodEnd: "Period end",
    generatedBy: "Generated by",
    scope: "Scope",
    summary: "Brief summary",
  },
} as const;

export const TECHNICAL_DATA_SOURCE_TITLES = {
  emailThreads: "Email Threads",
  calendarEvents: "Calendar Events",
  automationDecisions: "Automation Decisions",
  meetingNotes: "Meeting Notes",
  githubRepositories: "GitHub Repositories",
  githubContributors: "GitHub Contributors",
  githubWeeklyRepoSnapshots: "GitHub Weekly Repo Snapshots",
  githubWeeklyContributorSnapshots: "GitHub Weekly Contributor Snapshots",
  githubMonthlyRepoSnapshots: "GitHub Monthly Repo Snapshots",
  githubEngineeringBriefs: "GitHub Engineering Briefs",
} as const;
