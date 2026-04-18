import { AppConfig } from "../config";
import { addDays, addHours, nowIso } from "../lib/time";
import type { LocalStore } from "../store";
import { CalendarEventSnapshot, DecisionActionInput, DecisionProposal, EmailThreadSnapshot, QueueSnapshot } from "../types";
import { GmailService } from "./gmail";
import { NotionService } from "./notion";

export class ReconcileService {
  constructor(
    private readonly config: AppConfig,
    private readonly store: LocalStore,
    private readonly gmail: GmailService,
    private readonly notion: NotionService,
  ) {}

  async refreshEmailProposals(threads: EmailThreadSnapshot[]): Promise<DecisionProposal[]> {
    const proposals: DecisionProposal[] = [];

    for (const thread of threads) {
      if (await this.store.hasSuppressionHint(`thread:${thread.threadId}`)) {
        continue;
      }

      const senderDomain = thread.senderEmail.includes("@") ? thread.senderEmail.split("@")[1] : "";
      const proposal = await this.buildEmailProposal(thread, senderDomain);
      proposals.push(proposal);

      let notionPageId: string | null = null;
      let notionUrl: string | null = null;
      if (this.notion.isConfigured()) {
        const page = await this.notion.upsertDecision(proposal);
        notionPageId = page.id;
        notionUrl = page.url ?? null;
      }

      await this.store.upsertDecision({
        decisionId: proposal.decisionId,
        notionPageId,
        sourceType: proposal.sourceType,
        sourceExternalId: proposal.sourceExternalId,
        status: "pending",
        title: proposal.title,
        gmailUrl: proposal.gmailUrl ?? null,
        notionUrl,
        readGateBlocked: proposal.readGateBlocked,
        payload: proposal,
      });
    }

    return proposals;
  }

  async refreshMeetingProposals(events: CalendarEventSnapshot[]): Promise<DecisionProposal[]> {
    const proposals: DecisionProposal[] = [];
    const now = Date.now();

    for (const event of events) {
      const endAt = new Date(event.endAt).getTime();
      if (endAt > now || event.status === "cancelled") {
        continue;
      }

      const decisionId = `meeting-${event.eventId}`;
      const proposal: DecisionProposal = {
        decisionId,
        sourceType: "meeting",
        sourceExternalId: event.eventId,
        title: `Meeting wrap — ${event.summary}`,
        reviewReason: "Recently ended meeting requires next-step capture.",
        confidence: 0.72,
        proposedState: "state/action",
        dueAt: addDays(1),
        gmailUrl: undefined,
        notionUrl: event.htmlLink,
        readGateBlocked: false,
        diff: [
          { field: "Meeting status", from: "scheduled", to: "completed" },
          { field: "Next action", from: null, to: `Review outcomes from ${event.summary}` },
        ],
        target: {},
        summary: `${event.summary} ended recently and should be converted into follow-up actions.`,
        createdAt: nowIso(),
      };

      let notionPageId: string | null = null;
      let notionUrl: string | null = null;
      if (this.notion.isConfigured()) {
        const page = await this.notion.upsertDecision(proposal);
        notionPageId = page.id;
        notionUrl = page.url ?? null;
      }

      await this.store.upsertDecision({
        decisionId,
        notionPageId,
        sourceType: proposal.sourceType,
        sourceExternalId: proposal.sourceExternalId,
        status: "pending",
        title: proposal.title,
        gmailUrl: null,
        notionUrl,
        readGateBlocked: false,
        payload: proposal,
      });

      proposals.push(proposal);
    }

    return proposals;
  }

  async applyDecision(decisionId: string, action: "approve" | "reject" | "snooze", input: DecisionActionInput = {}) {
    const existing = await this.store.getDecision(decisionId);
    if (!existing) {
      throw new Error(`Decision ${decisionId} was not found.`);
    }

    const proposal = existing.payload;
    if (action === "approve") {
      if (proposal.readGateBlocked && !input.overrideReadGate) {
        throw new Error("This thread is blocked by the human-read gate. Read it first or approve with override.");
      }

      if (proposal.target.followUpId && (await this.notion.staleIfBusinessMoved(proposal.target.followUpId, proposal.createdAt))) {
        proposal.readGateBlocked = false;
        await this.store.updateDecisionStatus(decisionId, "stale", proposal, existing.notionUrl);
        if (this.notion.isConfigured()) {
          await this.notion.recordDecisionOutcome(
            decisionId,
            proposal,
            "stale",
            "Business record changed after the proposal was created.",
            this.config.localApproverName,
          );
        }
        throw new Error("The linked Notion record changed after this proposal was created. Refresh the queue first.");
      }

      if (this.notion.isConfigured()) {
        const interaction = await this.notion.ensureInteractionFromDecision(
          proposal,
          proposal.sourceType === "email"
            ? await this.store.getSourceCache<EmailThreadSnapshot>("gmail", "thread", proposal.sourceExternalId)
            : null,
        );
        const followUp = await this.notion.ensureFollowUpFromDecision(proposal, interaction.id);
        proposal.target.followUpId = followUp.id;
        proposal.readGateBlocked = false;
        await this.notion.recordDecisionOutcome(
          decisionId,
          proposal,
          "approved",
          input.note ?? "Approved from local automation UI.",
          this.config.localApproverName,
        );
      }

      if (proposal.sourceType === "email") {
        await this.gmail.applyApprovedState(proposal.sourceExternalId, proposal.proposedState);
      }

      await this.store.updateDecisionStatus(decisionId, "approved", proposal, existing.notionUrl);
      return this.store.getDecision(decisionId);
    }

    if (action === "reject") {
      if (input.note) {
        await this.store.addSuppressionHint(`thread:${proposal.sourceExternalId}`, input.note);
      }
      if (this.notion.isConfigured()) {
        await this.notion.recordDecisionOutcome(
          decisionId,
          proposal,
          "rejected",
          input.note ?? "Rejected from local automation UI.",
          this.config.localApproverName,
        );
      }
      await this.store.updateDecisionStatus(decisionId, "rejected", proposal, existing.notionUrl);
      return this.store.getDecision(decisionId);
    }

    proposal.snoozedUntil = input.snoozedUntil ?? addHours(24);
    if (this.notion.isConfigured()) {
      await this.notion.recordDecisionOutcome(
        decisionId,
        proposal,
        "snoozed",
        input.note ?? "Snoozed from local automation UI.",
        this.config.localApproverName,
      );
    }
    await this.store.updateDecisionStatus(decisionId, "snoozed", proposal, existing.notionUrl);
    return this.store.getDecision(decisionId);
  }

  async queue(): Promise<QueueSnapshot> {
    return this.store.queueSnapshot();
  }

  private async buildEmailProposal(thread: EmailThreadSnapshot, senderDomain: string): Promise<DecisionProposal> {
    const decisionId = `email-${thread.threadId}`;
    let contactId: string | undefined;
    let contactName: string | undefined;
    let accountId: string | undefined;
    let accountName: string | undefined;
    let opportunityId: string | undefined;
    let opportunityName: string | undefined;

    if (this.notion.isConfigured()) {
      const contact = await this.notion.findContactByEmail(thread.senderEmail);
      contactId = contact?.id;
      contactName = contact?.title;

      if (!contact && senderDomain) {
        const account = await this.notion.findAccountByDomain(senderDomain);
        accountId = account?.id;
        accountName = account?.title;
      }

      if (accountId) {
        const opportunity = await this.notion.findSingleOpenOpportunity(accountId);
        opportunityId = opportunity?.id;
        opportunityName = opportunity?.title;
      }
    }

    const proposedState = deriveThreadState(thread);
    const confidence = scoreConfidence(thread, Boolean(contactId), Boolean(accountId));
    const dueAt = proposedState === "state/waiting" ? addDays(3) : addDays(thread.userReadRequired ? 1 : 2);
    const reviewReason = buildReviewReason(thread, Boolean(contactId), Boolean(accountId), proposedState);

    return {
      decisionId,
      sourceType: "email",
      sourceExternalId: thread.threadId,
      title: `Inbox triage — ${thread.subject}`,
      reviewReason,
      confidence,
      proposedState,
      waitingOn: proposedState === "state/waiting" ? thread.senderEmail : undefined,
      dueAt,
      gmailUrl: thread.gmailUrl,
      notionUrl: undefined,
      readGateBlocked: thread.userReadRequired,
      diff: [
        { field: "Linked contact", from: null, to: contactName ?? null },
        { field: "Linked account", from: null, to: accountName ?? null },
        { field: "Linked opportunity", from: null, to: opportunityName ?? null },
        {
          field: "Follow-up state",
          from: null,
          to: proposedState,
        },
        {
          field: "Next action",
          from: null,
          to: nextActionForState(proposedState, thread.senderName || thread.senderEmail),
        },
      ],
      target: {
        accountId,
        accountName,
        contactId,
        contactName,
        opportunityId,
        opportunityName,
      },
      summary: `${thread.subject}: ${thread.excerpt}`,
      createdAt: nowIso(),
    };
  }
}

function deriveThreadState(thread: EmailThreadSnapshot): DecisionProposal["proposedState"] {
  if (thread.unread) {
    return "triage/pending-review";
  }
  if (thread.labels.includes("state/waiting")) {
    return "state/action";
  }
  if (thread.labels.includes("state/reference")) {
    return "state/reference";
  }
  if (thread.outboundCount > 0 && thread.inboundCount === 0) {
    return "state/waiting";
  }
  return "state/action";
}

function scoreConfidence(thread: EmailThreadSnapshot, hasContact: boolean, hasAccount: boolean): number {
  let confidence = thread.userReadRequired ? 0.45 : 0.65;
  if (hasContact) {
    confidence += 0.2;
  } else if (hasAccount) {
    confidence += 0.1;
  }
  return Math.min(0.95, Number(confidence.toFixed(2)));
}

function buildReviewReason(
  thread: EmailThreadSnapshot,
  hasContact: boolean,
  hasAccount: boolean,
  proposedState: DecisionProposal["proposedState"],
): string {
  const reasons = [];
  if (thread.userReadRequired) {
    reasons.push("Unread inbound thread must stay behind the human-read gate.");
  }
  if (hasContact) {
    reasons.push("Matched sender to an existing contact.");
  } else if (hasAccount) {
    reasons.push("Matched sender domain to an existing account.");
  } else {
    reasons.push("Sender is not yet linked to a contact or account.");
  }
  reasons.push(`Proposed Gmail state: ${proposedState}.`);
  return reasons.join(" ");
}

function nextActionForState(state: DecisionProposal["proposedState"], party: string): string {
  switch (state) {
    case "state/waiting":
      return `Wait for ${party} and revisit if no reply arrives.`;
    case "state/reference":
      return `Store the thread as reference material.`;
    case "triage/pending-review":
      return `Read the email and approve the suggested routing.`;
    default:
      return `Review ${party}'s thread and decide the next move.`;
  }
}
