export const JOB_NAMES = [
  "gmail-sync",
  "calendar-sync",
  "reconcile",
  "meeting-wrap",
  "morning-brief",
  "weekly-plan",
  "weekly-review",
  "hygiene-sweep",
  "github-discover",
  "github-backfill",
  "github-sync",
  "github-rollup",
  "github-notion-sync",
  "github-weekly-brief",
] as const;

export type JobName = (typeof JOB_NAMES)[number];

export type JobStatus = "success" | "warning" | "error";

export type DecisionStatus = "pending" | "approved" | "rejected" | "snoozed" | "stale";

export type SourceType = "email" | "meeting" | "brief";

export type ManagedThreadState =
  | "triage/new"
  | "triage/pending-review"
  | "state/action"
  | "state/waiting"
  | "state/scheduled"
  | "state/reference"
  | "state/ignored";

export interface JobResult {
  jobName: JobName;
  status: JobStatus;
  startedAt: string;
  finishedAt: string;
  notes: string[];
  stats: Record<string, number | string | boolean | null>;
}

export interface EmailThreadSnapshot {
  threadId: string;
  historyId: string;
  subject: string;
  participants: string[];
  senderEmail: string;
  senderName: string;
  snippet: string;
  summary: string;
  excerpt: string;
  labels: string[];
  unread: boolean;
  lastMessageAt: string;
  inboundCount: number;
  outboundCount: number;
  userReadRequired: boolean;
  userReadConfirmed: boolean;
  gmailUrl: string;
}

export interface CalendarEventSnapshot {
  eventId: string;
  summary: string;
  description: string;
  organizerEmail: string;
  attendees: string[];
  status: string;
  startAt: string;
  endAt: string;
  updatedAt: string;
  htmlLink: string;
}

export interface DecisionDiff {
  field: string;
  from: string | null;
  to: string | null;
}

export interface ProposalTarget {
  accountId?: string;
  accountName?: string;
  contactId?: string;
  contactName?: string;
  opportunityId?: string;
  opportunityName?: string;
  followUpId?: string;
  followUpName?: string;
  meetingNoteId?: string;
}

export interface DecisionProposal {
  decisionId: string;
  sourceType: SourceType;
  sourceExternalId: string;
  title: string;
  reviewReason: string;
  confidence: number;
  proposedState: ManagedThreadState;
  waitingOn?: string;
  dueAt?: string;
  gmailUrl?: string;
  notionUrl?: string;
  readGateBlocked: boolean;
  diff: DecisionDiff[];
  target: ProposalTarget;
  summary: string;
  createdAt: string;
  snoozedUntil?: string | null;
}

export interface DecisionCacheEntry {
  decisionId: string;
  notionPageId: string | null;
  sourceType: SourceType;
  sourceExternalId: string;
  status: DecisionStatus;
  title: string;
  gmailUrl: string | null;
  notionUrl: string | null;
  readGateBlocked: boolean;
  payload: DecisionProposal;
  createdAt: string;
  updatedAt: string;
}

export interface OAuthTokenRecord {
  provider: string;
  tokenJson: string;
  email: string | null;
  updatedAt: string;
}

export interface QueueSnapshot {
  decisions: DecisionCacheEntry[];
  latestRuns: JobRunRecord[];
}

export interface JobRunRecord {
  id: string;
  jobName: JobName;
  status: JobStatus | "running";
  detailsJson: string;
  startedAt: string;
  finishedAt: string | null;
}

export interface DecisionActionInput {
  note?: string;
  snoozedUntil?: string;
  overrideReadGate?: boolean;
}

export type AnalyticsGrain = "day" | "week" | "month";

export interface AnalyticsFilters {
  owner?: string | null;
  repository?: string | null;
  contributor?: string | null;
  dateFrom?: string | null;
  dateTo?: string | null;
  grain?: AnalyticsGrain | null;
  includeBots?: boolean;
  includeArchived?: boolean;
  includeForks?: boolean;
  metricFamily?: string | null;
}

export interface GitHubRepositoryRecord {
  repoId: string;
  owner: string;
  name: string;
  fullName: string;
  description: string;
  visibility: string;
  language: string;
  defaultBranch: string;
  isArchived: boolean;
  isFork: boolean;
  htmlUrl: string;
  cloneUrl: string;
  pushedAt: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  firstSyncedAt: string | null;
  lastSyncedAt: string | null;
  mirrorPath: string;
  commitCount: number;
  additions: number;
  deletions: number;
  changedFiles: number;
  openPrs: number;
  mergedPrs: number;
  openIssues: number;
  releases: number;
  workflowFailures: number;
  latestActivityAt: string | null;
}

export interface ContributorRecord {
  contributorId: string;
  canonicalLogin: string | null;
  displayName: string;
  avatarUrl: string | null;
  firstSeenAt: string | null;
  lastActiveAt: string | null;
  repoCount: number;
  commitCount: number;
  additions: number;
  deletions: number;
  changedFiles: number;
  prsOpened: number;
  prsMerged: number;
  reviewsSubmitted: number;
  issuesOpened: number;
  workflowRuns: number;
  latestActivityAt: string | null;
}

export interface ContributorAliasRecord {
  aliasKey: string;
  contributorId: string;
  login: string | null;
  name: string | null;
  email: string | null;
  lastSeenAt: string;
}

export interface CommitFact {
  repoId: string;
  sha: string;
  authorContributorId: string | null;
  authorLogin: string | null;
  authorName: string;
  authorEmail: string;
  authoredAt: string;
  committedAt: string;
  subject: string;
  body: string;
  additions: number;
  deletions: number;
  changedFiles: number;
  isMerge: boolean;
  htmlUrl: string;
  refNames: string[];
}

export interface PullRequestFact {
  pullRequestId: string;
  repoId: string;
  number: number;
  authorContributorId: string | null;
  authorLogin: string | null;
  title: string;
  state: string;
  createdAt: string;
  updatedAt: string;
  mergedAt: string | null;
  closedAt: string | null;
  additions: number;
  deletions: number;
  changedFiles: number;
  commitsCount: number;
  reviewComments: number;
  comments: number;
  htmlUrl: string;
}

export interface PullRequestReviewFact {
  reviewId: string;
  repoId: string;
  pullRequestId: string;
  reviewerContributorId: string | null;
  reviewerLogin: string | null;
  state: string;
  submittedAt: string | null;
  htmlUrl: string;
}

export interface IssueFact {
  issueId: string;
  repoId: string;
  number: number;
  authorContributorId: string | null;
  authorLogin: string | null;
  title: string;
  state: string;
  createdAt: string;
  updatedAt: string;
  closedAt: string | null;
  comments: number;
  htmlUrl: string;
}

export interface ReleaseFact {
  releaseId: string;
  repoId: string;
  tagName: string;
  name: string;
  isDraft: boolean;
  isPrerelease: boolean;
  publishedAt: string | null;
  createdAt: string;
  htmlUrl: string;
}

export interface WorkflowRunFact {
  runId: string;
  repoId: string;
  workflowName: string;
  status: string;
  conclusion: string | null;
  event: string;
  branch: string | null;
  actorContributorId: string | null;
  actorLogin: string | null;
  createdAt: string;
  updatedAt: string;
  htmlUrl: string;
}

export interface RepoRollup {
  entityType: "repo";
  entityId: string;
  bucketStart: string;
  commits: number;
  additions: number;
  deletions: number;
  changedFiles: number;
  prsOpened: number;
  prsMerged: number;
  reviewsSubmitted: number;
  issuesOpened: number;
  issuesClosed: number;
  releases: number;
  workflowRuns: number;
  workflowFailures: number;
}

export interface ContributorRollup {
  entityType: "contributor";
  entityId: string;
  bucketStart: string;
  commits: number;
  additions: number;
  deletions: number;
  changedFiles: number;
  prsOpened: number;
  prsMerged: number;
  reviewsSubmitted: number;
  issuesOpened: number;
  issuesClosed: number;
  releases: number;
  workflowRuns: number;
  workflowFailures: number;
}

export interface WeeklyEngineeringBrief {
  weekStart: string;
  generatedAt: string;
  headline: string;
  summary: string;
  topRepositories: Array<{ fullName: string; commits: number; netLoc: number }>;
  topContributors: Array<{ contributor: string; commits: number; netLoc: number }>;
  workflowAlerts: Array<{ fullName: string; failures: number }>;
  notionUrl?: string | null;
}

export interface AnalyticsSummarySnapshot {
  generatedAt: string;
  filters: AnalyticsFilters;
  totals: {
    activeRepos: number;
    activeContributors: number;
    commits: number;
    additions: number;
    deletions: number;
    netLoc: number;
    prsOpened: number;
    prsMerged: number;
    reviewsSubmitted: number;
    issuesOpened: number;
    issuesClosed: number;
    releases: number;
    workflowRuns: number;
    workflowFailures: number;
  };
  biggestRepos: Array<{ fullName: string; commits: number; netLoc: number; mergedPrs: number }>;
  biggestContributors: Array<{ contributor: string; commits: number; netLoc: number; prsMerged: number }>;
  trendHighlights: Array<{ label: string; value: string }>;
}

export interface TrendPoint {
  bucketStart: string;
  commits: number;
  additions: number;
  deletions: number;
  netLoc: number;
  prsOpened: number;
  prsMerged: number;
  reviewsSubmitted: number;
  issuesOpened: number;
  issuesClosed: number;
  releases: number;
  workflowRuns: number;
  workflowFailures: number;
}
