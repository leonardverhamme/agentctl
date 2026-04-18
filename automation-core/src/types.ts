export const JOB_NAMES = [
  "gmail-sync",
  "calendar-sync",
  "reconcile",
  "meeting-wrap",
  "morning-brief",
  "weekly-plan",
  "weekly-review",
  "hygiene-sweep",
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
