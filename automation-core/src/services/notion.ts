import { Client } from "@notionhq/client";

import {
  AppConfig,
  BUSINESS_PROPERTY_NAMES,
  TECHNICAL_DATA_SOURCE_TITLES,
} from "../config";
import { stableHash } from "../lib/hash";
import { compactText } from "../lib/text";
import { addDays, nowIso, toDateOnlyIso } from "../lib/time";
import { CalendarEventSnapshot, DecisionProposal, EmailThreadSnapshot } from "../types";

type NotionPage = {
  id: string;
  url?: string;
  last_edited_time?: string;
  properties?: Record<string, unknown>;
};

type QueryResult = {
  results: NotionPage[];
};

type DatabaseCreateResponse = {
  id: string;
  title?: unknown[];
  data_sources?: Array<{ id: string }>;
};

const EMAIL_THREADS_KEY = "Gmail thread ID";
const CALENDAR_EVENT_KEY = "Calendar event ID";
const DECISION_KEY = "Decision ID";
const MEETING_EVENT_KEY = "Calendar event ID";

const TECHNICAL_SCHEMA: Record<string, Record<string, unknown>> = {
  [TECHNICAL_DATA_SOURCE_TITLES.emailThreads]: {
    Name: { title: {} },
    [EMAIL_THREADS_KEY]: { rich_text: {} },
    Provider: { rich_text: {} },
    Subject: { rich_text: {} },
    "Sender email": { email: {} },
    Participants: { rich_text: {} },
    Summary: { rich_text: {} },
    "Latest excerpt": { rich_text: {} },
    "Gmail URL": { url: {} },
    "Last message at": { date: {} },
    Unread: { checkbox: {} },
    Labels: { rich_text: {} },
    "Approval state": {
      select: {
        options: [
          { name: "pending" },
          { name: "approved" },
          { name: "rejected" },
          { name: "snoozed" },
          { name: "stale" },
        ],
      },
    },
    "Decision status": {
      select: {
        options: [
          { name: "pending" },
          { name: "approved" },
          { name: "rejected" },
          { name: "snoozed" },
          { name: "stale" },
        ],
      },
    },
    Confidence: { number: { format: "number" } },
    "Review reason": { rich_text: {} },
    "User read required": { checkbox: {} },
    "User read confirmed": { checkbox: {} },
    "Linked account ID": { rich_text: {} },
    "Linked contact ID": { rich_text: {} },
    "Linked opportunity ID": { rich_text: {} },
    "Linked follow-up ID": { rich_text: {} },
    "Linked meeting note ID": { rich_text: {} },
    "Last synced at": { date: {} },
    "Sync status": {
      select: { options: [{ name: "ok" }, { name: "warning" }, { name: "error" }] },
    },
    "Sync hash": { rich_text: {} },
    "Last seen history ID": { rich_text: {} },
  },
  [TECHNICAL_DATA_SOURCE_TITLES.calendarEvents]: {
    Name: { title: {} },
    [CALENDAR_EVENT_KEY]: { rich_text: {} },
    Provider: { rich_text: {} },
    Summary: { rich_text: {} },
    Description: { rich_text: {} },
    "Organizer email": { email: {} },
    Attendees: { rich_text: {} },
    Status: {
      select: {
        options: [{ name: "confirmed" }, { name: "tentative" }, { name: "cancelled" }],
      },
    },
    "Start at": { date: {} },
    "End at": { date: {} },
    "Calendar URL": { url: {} },
    "Last synced at": { date: {} },
    "Sync status": {
      select: { options: [{ name: "ok" }, { name: "warning" }, { name: "error" }] },
    },
    "Sync hash": { rich_text: {} },
    "Linked meeting note ID": { rich_text: {} },
    "Linked follow-up ID": { rich_text: {} },
  },
  [TECHNICAL_DATA_SOURCE_TITLES.automationDecisions]: {
    Name: { title: {} },
    [DECISION_KEY]: { rich_text: {} },
    "Source type": {
      select: { options: [{ name: "email" }, { name: "meeting" }, { name: "brief" }] },
    },
    "Source external ID": { rich_text: {} },
    "Decision status": {
      select: {
        options: [
          { name: "pending" },
          { name: "approved" },
          { name: "rejected" },
          { name: "snoozed" },
          { name: "stale" },
        ],
      },
    },
    "Proposed state": {
      select: {
        options: [
          { name: "triage/new" },
          { name: "triage/pending-review" },
          { name: "state/action" },
          { name: "state/waiting" },
          { name: "state/scheduled" },
          { name: "state/reference" },
          { name: "state/ignored" },
        ],
      },
    },
    Confidence: { number: { format: "number" } },
    "Review reason": { rich_text: {} },
    "Summary": { rich_text: {} },
    "Gmail URL": { url: {} },
    "Source notion URL": { url: {} },
    "Read gate blocked": { checkbox: {} },
    "Snoozed until": { date: {} },
    "Approved by": { rich_text: {} },
    "Approved at": { date: {} },
    "Decision note": { rich_text: {} },
    "Proposal payload": { rich_text: {} },
    "Linked account ID": { rich_text: {} },
    "Linked contact ID": { rich_text: {} },
    "Linked opportunity ID": { rich_text: {} },
    "Linked follow-up ID": { rich_text: {} },
    "Linked meeting note ID": { rich_text: {} },
  },
  [TECHNICAL_DATA_SOURCE_TITLES.meetingNotes]: {
    Name: { title: {} },
    [MEETING_EVENT_KEY]: { rich_text: {} },
    "Calendar URL": { url: {} },
    Status: {
      select: {
        options: [{ name: "scheduled" }, { name: "completed" }, { name: "cancelled" }],
      },
    },
    "Meeting summary": { rich_text: {} },
    Outcomes: { rich_text: {} },
    "Next-action rationale": { rich_text: {} },
    "Linked account ID": { rich_text: {} },
    "Linked contact ID": { rich_text: {} },
    "Linked opportunity ID": { rich_text: {} },
    "Linked follow-up ID": { rich_text: {} },
    "Last synced at": { date: {} },
  },
};

const BUSINESS_PATCHES: Array<{ dataSourceId: keyof AppConfig; properties: Record<string, unknown> }> = [
  {
    dataSourceId: "notionAccountsDataSourceId",
    properties: {
      [BUSINESS_PROPERTY_NAMES.accounts.domains]: { rich_text: {} },
    },
  },
  {
    dataSourceId: "notionContactsDataSourceId",
    properties: {
      [BUSINESS_PROPERTY_NAMES.contacts.primaryEmail]: { email: {} },
    },
  },
  {
    dataSourceId: "notionInteractionsDataSourceId",
    properties: {
      [BUSINESS_PROPERTY_NAMES.interactions.sourceExternalId]: { rich_text: {} },
      [BUSINESS_PROPERTY_NAMES.interactions.sourceProvider]: { rich_text: {} },
    },
  },
  {
    dataSourceId: "notionFollowupsDataSourceId",
    properties: {
      [BUSINESS_PROPERTY_NAMES.followups.sourceExternalId]: { rich_text: {} },
      [BUSINESS_PROPERTY_NAMES.followups.sourceProvider]: { rich_text: {} },
    },
  },
];

export class NotionService {
  private readonly client: Client | null;

  constructor(private readonly config: AppConfig) {
    this.client = config.notionToken
      ? new Client({
          auth: config.notionToken,
          notionVersion: config.notionVersion,
        })
      : null;
  }

  isConfigured(): boolean {
    return Boolean(this.client);
  }

  async bootstrapSchema(): Promise<Record<string, string>> {
    this.getClient();

    const created: Record<string, string> = {};
    for (const patch of BUSINESS_PATCHES) {
      const target = this.config[patch.dataSourceId];
      if (!target) {
        continue;
      }
      await this.request(`data_sources/${target}`, "patch", {
        properties: patch.properties,
      });
    }

    if (!this.config.notionParentPageId) {
      return created;
    }

    const technicalTargets: Array<{
      configKey:
        | "notionEmailThreadsDataSourceId"
        | "notionCalendarEventsDataSourceId"
        | "notionAutomationDecisionsDataSourceId"
        | "notionMeetingNotesDataSourceId";
      title: string;
    }> = [
      { configKey: "notionEmailThreadsDataSourceId", title: TECHNICAL_DATA_SOURCE_TITLES.emailThreads },
      { configKey: "notionCalendarEventsDataSourceId", title: TECHNICAL_DATA_SOURCE_TITLES.calendarEvents },
      { configKey: "notionAutomationDecisionsDataSourceId", title: TECHNICAL_DATA_SOURCE_TITLES.automationDecisions },
      { configKey: "notionMeetingNotesDataSourceId", title: TECHNICAL_DATA_SOURCE_TITLES.meetingNotes },
    ];

    for (const target of technicalTargets) {
      if (this.config[target.configKey]) {
        continue;
      }
      const response = await this.request<DatabaseCreateResponse>("databases", "post", {
        parent: { page_id: this.config.notionParentPageId },
        title: [{ type: "text", text: { content: target.title } }],
        properties: TECHNICAL_SCHEMA[target.title],
      });
      const dataSourceId = response.data_sources?.[0]?.id;
      if (dataSourceId) {
        created[target.title] = dataSourceId;
      }
    }

    return created;
  }

  async upsertEmailThread(snapshot: EmailThreadSnapshot): Promise<{ id: string; url: string | undefined }> {
    const dataSourceId = this.requireId("notionEmailThreadsDataSourceId", "Email Threads");
    return this.upsertPage(dataSourceId, EMAIL_THREADS_KEY, snapshot.threadId, snapshot.subject, {
      Provider: richText("gmail"),
      Subject: richText(snapshot.subject),
      "Sender email": emailValue(snapshot.senderEmail),
      Participants: richText(snapshot.participants.join(", ")),
      Summary: richText(snapshot.summary),
      "Latest excerpt": richText(snapshot.excerpt),
      "Gmail URL": urlValue(snapshot.gmailUrl),
      "Last message at": dateValue(snapshot.lastMessageAt),
      Unread: checkboxValue(snapshot.unread),
      Labels: richText(snapshot.labels.join(", ")),
      "Approval state": selectValue("pending"),
      "Decision status": selectValue("pending"),
      Confidence: numberValue(snapshot.userReadRequired ? 0.45 : 0.75),
      "Review reason": richText(snapshot.userReadRequired ? "Unread inbound mail requires operator review." : "Thread synced."),
      "User read required": checkboxValue(snapshot.userReadRequired),
      "User read confirmed": checkboxValue(snapshot.userReadConfirmed),
      "Last synced at": dateValue(nowIso()),
      "Sync status": selectValue("ok"),
      "Sync hash": richText(stableHash(snapshot)),
      "Last seen history ID": richText(snapshot.historyId),
    });
  }

  async upsertCalendarEvent(snapshot: CalendarEventSnapshot): Promise<{ id: string; url: string | undefined }> {
    const dataSourceId = this.requireId("notionCalendarEventsDataSourceId", "Calendar Events");
    return this.upsertPage(dataSourceId, CALENDAR_EVENT_KEY, snapshot.eventId, snapshot.summary, {
      Provider: richText("google-calendar"),
      Summary: richText(snapshot.summary),
      Description: richText(snapshot.description),
      "Organizer email": emailValue(snapshot.organizerEmail),
      Attendees: richText(snapshot.attendees.join(", ")),
      Status: selectValue(normalizeCalendarStatus(snapshot.status)),
      "Start at": dateValue(snapshot.startAt),
      "End at": dateValue(snapshot.endAt),
      "Calendar URL": urlValue(snapshot.htmlLink),
      "Last synced at": dateValue(nowIso()),
      "Sync status": selectValue("ok"),
      "Sync hash": richText(stableHash(snapshot)),
    });
  }

  async upsertDecision(proposal: DecisionProposal, status = "pending"): Promise<{ id: string; url: string | undefined }> {
    const dataSourceId = this.requireId("notionAutomationDecisionsDataSourceId", "Automation Decisions");
    return this.upsertPage(dataSourceId, DECISION_KEY, proposal.decisionId, proposal.title, {
      "Source type": selectValue(proposal.sourceType),
      "Source external ID": richText(proposal.sourceExternalId),
      "Decision status": selectValue(status),
      "Proposed state": selectValue(proposal.proposedState),
      Confidence: numberValue(Number(proposal.confidence.toFixed(2))),
      "Review reason": richText(proposal.reviewReason),
      Summary: richText(proposal.summary),
      "Gmail URL": urlValue(proposal.gmailUrl ?? ""),
      "Source notion URL": urlValue(proposal.notionUrl ?? ""),
      "Read gate blocked": checkboxValue(proposal.readGateBlocked),
      "Snoozed until": dateValue(proposal.snoozedUntil ?? null),
      "Proposal payload": richText(compactText(JSON.stringify(proposal), 1800)),
      "Linked account ID": richText(proposal.target.accountId ?? ""),
      "Linked contact ID": richText(proposal.target.contactId ?? ""),
      "Linked opportunity ID": richText(proposal.target.opportunityId ?? ""),
      "Linked follow-up ID": richText(proposal.target.followUpId ?? ""),
      "Linked meeting note ID": richText(proposal.target.meetingNoteId ?? ""),
    });
  }

  async recordDecisionOutcome(
    decisionId: string,
    proposal: DecisionProposal,
    status: "approved" | "rejected" | "snoozed" | "stale",
    note: string,
    approvedBy: string,
  ): Promise<void> {
    const dataSourceId = this.requireId("notionAutomationDecisionsDataSourceId", "Automation Decisions");
    const existing = await this.findPageByRichText(dataSourceId, DECISION_KEY, decisionId);
    if (!existing) {
      return;
    }
    await this.updatePage(existing.id, {
      "Decision status": selectValue(status),
      "Read gate blocked": checkboxValue(proposal.readGateBlocked),
      "Decision note": richText(note),
      "Approved by": richText(approvedBy),
      "Approved at": dateValue(nowIso()),
      "Snoozed until": dateValue(proposal.snoozedUntil ?? null),
      "Proposal payload": richText(compactText(JSON.stringify(proposal), 1800)),
    });
  }

  async createMeetingNote(snapshot: CalendarEventSnapshot): Promise<{ id: string; url: string | undefined }> {
    const dataSourceId = this.requireId("notionMeetingNotesDataSourceId", "Meeting Notes");
    const title = `${snapshot.summary} — ${toDateOnlyIso(snapshot.startAt)}`;
    return this.upsertPage(dataSourceId, MEETING_EVENT_KEY, snapshot.eventId, title, {
      "Calendar URL": urlValue(snapshot.htmlLink),
      Status: selectValue(snapshot.status === "cancelled" ? "cancelled" : "scheduled"),
      "Meeting summary": richText(snapshot.summary),
      Outcomes: richText(snapshot.description),
      "Next-action rationale": richText("Meeting wrap job will turn outcomes into follow-up proposals."),
      "Last synced at": dateValue(nowIso()),
    });
  }

  async findContactByEmail(email: string): Promise<{ id: string; title: string; url?: string } | null> {
    const dataSourceId = this.requireId("notionContactsDataSourceId", "Contacts");
    const page = await this.findPageByEmail(dataSourceId, BUSINESS_PROPERTY_NAMES.contacts.primaryEmail, email);
    if (!page) {
      return null;
    }
    return { id: page.id, title: extractTitle(page, BUSINESS_PROPERTY_NAMES.contacts.title), url: page.url };
  }

  async findAccountByDomain(domain: string): Promise<{ id: string; title: string; url?: string } | null> {
    const dataSourceId = this.requireId("notionAccountsDataSourceId", "Accounts");
    const page = await this.findPageByRichTextContains(dataSourceId, BUSINESS_PROPERTY_NAMES.accounts.domains, domain);
    if (!page) {
      return null;
    }
    return { id: page.id, title: extractTitle(page, BUSINESS_PROPERTY_NAMES.accounts.title), url: page.url };
  }

  async findSingleOpenOpportunity(accountId: string): Promise<{ id: string; title: string; url?: string } | null> {
    const dataSourceId = this.requireId("notionOpportunitiesDataSourceId", "Opportunities");
    const response = await this.queryDataSource(dataSourceId, {
      filter: {
        and: [
          {
            property: BUSINESS_PROPERTY_NAMES.opportunities.accountRelation,
            relation: { contains: accountId },
          },
          {
            property: BUSINESS_PROPERTY_NAMES.opportunities.stage,
            status: { does_not_equal: "Closed won" },
          },
          {
            property: BUSINESS_PROPERTY_NAMES.opportunities.stage,
            status: { does_not_equal: "Closed lost" },
          },
        ],
      },
      page_size: 5,
    });
    if (response.results.length !== 1) {
      return null;
    }
    const page = response.results[0];
    return { id: page.id, title: extractTitle(page, BUSINESS_PROPERTY_NAMES.opportunities.title), url: page.url };
  }

  async ensureInteractionFromDecision(
    proposal: DecisionProposal,
    thread: EmailThreadSnapshot | null,
  ): Promise<{ id: string; url: string | undefined }> {
    const dataSourceId = this.requireId("notionInteractionsDataSourceId", "Interactions");
    return this.upsertPage(
      dataSourceId,
      BUSINESS_PROPERTY_NAMES.interactions.sourceExternalId,
      proposal.sourceExternalId,
      proposal.title,
      {
        [BUSINESS_PROPERTY_NAMES.interactions.sourceProvider]: richText(proposal.sourceType === "email" ? "gmail" : "google-calendar"),
        [BUSINESS_PROPERTY_NAMES.interactions.summary]: richText(proposal.summary),
        [BUSINESS_PROPERTY_NAMES.interactions.explicitNextStep]: richText(proposal.diff.map((entry) => `${entry.field}: ${entry.to ?? ""}`).join(" | ")),
        [BUSINESS_PROPERTY_NAMES.interactions.followUpNeeded]: checkboxValue(true),
        [BUSINESS_PROPERTY_NAMES.interactions.interactionDate]: dateValue(thread?.lastMessageAt ?? proposal.createdAt),
        [BUSINESS_PROPERTY_NAMES.interactions.type]: selectValue(proposal.sourceType === "email" ? "Email received" : "Calendar event"),
        ...(proposal.target.accountId
          ? { [BUSINESS_PROPERTY_NAMES.interactions.accountRelation]: relationValue([proposal.target.accountId]) }
          : {}),
        ...(proposal.target.contactId
          ? { [BUSINESS_PROPERTY_NAMES.interactions.contactRelation]: relationValue([proposal.target.contactId]) }
          : {}),
        ...(proposal.target.opportunityId
          ? { [BUSINESS_PROPERTY_NAMES.interactions.opportunityRelation]: relationValue([proposal.target.opportunityId]) }
          : {}),
      },
    );
  }

  async ensureFollowUpFromDecision(
    proposal: DecisionProposal,
    interactionId: string,
  ): Promise<{ id: string; url: string | undefined }> {
    const dataSourceId = this.requireId("notionFollowupsDataSourceId", "Follow-ups");
    const nextAction = proposal.diff.find((entry) => entry.field === "Next action")?.to ?? proposal.summary;
    return this.upsertPage(
      dataSourceId,
      BUSINESS_PROPERTY_NAMES.followups.sourceExternalId,
      proposal.sourceExternalId,
      proposal.title,
      {
        [BUSINESS_PROPERTY_NAMES.followups.sourceProvider]: richText(proposal.sourceType === "email" ? "gmail" : "google-calendar"),
        [BUSINESS_PROPERTY_NAMES.followups.nextAction]: richText(nextAction),
        [BUSINESS_PROPERTY_NAMES.followups.nextActionDue]: dateValue(proposal.dueAt ?? addDays(1)),
        [BUSINESS_PROPERTY_NAMES.followups.waitingOn]: richText(proposal.waitingOn ?? ""),
        [BUSINESS_PROPERTY_NAMES.followups.status]: selectValue(mapManagedStateToFollowUpStatus(proposal.proposedState)),
        ...(proposal.target.accountId
          ? { [BUSINESS_PROPERTY_NAMES.followups.accountRelation]: relationValue([proposal.target.accountId]) }
          : {}),
        ...(proposal.target.contactId
          ? { [BUSINESS_PROPERTY_NAMES.followups.contactRelation]: relationValue([proposal.target.contactId]) }
          : {}),
        ...(proposal.target.opportunityId
          ? { [BUSINESS_PROPERTY_NAMES.followups.opportunityRelation]: relationValue([proposal.target.opportunityId]) }
          : {}),
      },
    );
  }

  async createBrief(
    title: string,
    briefType: "Morning Brief" | "Weekly Plan" | "Weekly Review" | "Deep Audit",
    generatedBy: string,
    summary: string,
    bodyParagraphs: string[],
  ): Promise<{ id: string; url: string | undefined } | null> {
    if (!this.config.notionAiBriefsDataSourceId) {
      return null;
    }

    return this.createPage(this.config.notionAiBriefsDataSourceId, title, {
      [BUSINESS_PROPERTY_NAMES.aiBriefs.briefType]: selectValue(briefType),
      [BUSINESS_PROPERTY_NAMES.aiBriefs.briefDate]: dateValue(nowIso()),
      [BUSINESS_PROPERTY_NAMES.aiBriefs.generatedBy]: selectValue(generatedBy),
      [BUSINESS_PROPERTY_NAMES.aiBriefs.scope]: richText("automation-core"),
      [BUSINESS_PROPERTY_NAMES.aiBriefs.summary]: richText(summary),
    }, bodyParagraphs.map(paragraphBlock));
  }

  async findPendingDecisionPage(decisionId: string): Promise<NotionPage | null> {
    const dataSourceId = this.requireId("notionAutomationDecisionsDataSourceId", "Automation Decisions");
    return this.findPageByRichText(dataSourceId, DECISION_KEY, decisionId);
  }

  async listPendingDecisions(limit = 25): Promise<Array<{ title: string; summary: string; url?: string }>> {
    const dataSourceId = this.requireId("notionAutomationDecisionsDataSourceId", "Automation Decisions");
    const response = await this.queryDataSource(dataSourceId, {
      filter: {
        property: "Decision status",
        select: { equals: "pending" },
      },
      page_size: limit,
      sorts: [{ property: "Confidence", direction: "ascending" }],
    });
    return response.results.map((page) => ({
      title: extractTitle(page, "Name"),
      summary: extractRichText(page, "Summary"),
      url: page.url,
    }));
  }

  async listOpenFollowUps(limit = 25): Promise<Array<{ title: string; nextAction: string; url?: string }>> {
    const dataSourceId = this.requireId("notionFollowupsDataSourceId", "Follow-ups");
    const response = await this.queryDataSource(dataSourceId, {
      filter: {
        and: [
          {
            property: BUSINESS_PROPERTY_NAMES.followups.status,
            status: { does_not_equal: "Done" },
          },
          {
            property: BUSINESS_PROPERTY_NAMES.followups.status,
            status: { does_not_equal: "Dropped" },
          },
        ],
      },
      page_size: limit,
    });
    return response.results.map((page) => ({
      title: extractTitle(page, BUSINESS_PROPERTY_NAMES.followups.title),
      nextAction: extractRichText(page, BUSINESS_PROPERTY_NAMES.followups.nextAction),
      url: page.url,
    }));
  }

  async listStaleCalendarEvents(limit = 25): Promise<Array<{ title: string; summary: string; url?: string }>> {
    const dataSourceId = this.requireId("notionCalendarEventsDataSourceId", "Calendar Events");
    const response = await this.queryDataSource(dataSourceId, {
      filter: {
        property: "Status",
        select: { equals: "confirmed" },
      },
      page_size: limit,
    });
    return response.results.map((page) => ({
      title: extractTitle(page, "Name"),
      summary: extractRichText(page, "Summary"),
      url: page.url,
    }));
  }

  async staleIfBusinessMoved(followUpId: string | undefined, decisionCreatedAt: string): Promise<boolean> {
    if (!followUpId) {
      return false;
    }
    const page = await this.retrievePage(followUpId);
    return Boolean(page?.last_edited_time && page.last_edited_time > decisionCreatedAt);
  }

  private requireId(
    key:
      | "notionAccountsDataSourceId"
      | "notionContactsDataSourceId"
      | "notionOpportunitiesDataSourceId"
      | "notionInteractionsDataSourceId"
      | "notionFollowupsDataSourceId"
      | "notionAiBriefsDataSourceId"
      | "notionEmailThreadsDataSourceId"
      | "notionCalendarEventsDataSourceId"
      | "notionAutomationDecisionsDataSourceId"
      | "notionMeetingNotesDataSourceId",
    label: string,
  ): string {
    const value = this.config[key];
    if (!value) {
      throw new Error(`${label} data source ID is not configured (${key}).`);
    }
    return value;
  }

  private async request<T extends object>(
    path: string,
    method: "get" | "post" | "patch",
    body?: Record<string, unknown>,
  ): Promise<T> {
    const client = this.getClient();
    return client.request<T>({
      path,
      method,
      body,
    });
  }

  private getClient(): Client {
    if (!this.client) {
      throw new Error("Notion integration is not configured. Set NOTION_TOKEN and data source IDs.");
    }
    return this.client;
  }

  private async queryDataSource(dataSourceId: string, body: Record<string, unknown>): Promise<QueryResult> {
    return this.request<QueryResult>(`data_sources/${dataSourceId}/query`, "post", body);
  }

  private async findPageByRichText(dataSourceId: string, property: string, value: string): Promise<NotionPage | null> {
    const response = await this.queryDataSource(dataSourceId, {
      filter: {
        property,
        rich_text: { equals: value },
      },
      page_size: 1,
    });
    return response.results[0] ?? null;
  }

  private async findPageByRichTextContains(dataSourceId: string, property: string, value: string): Promise<NotionPage | null> {
    const response = await this.queryDataSource(dataSourceId, {
      filter: {
        property,
        rich_text: { contains: value },
      },
      page_size: 1,
    });
    return response.results[0] ?? null;
  }

  private async findPageByEmail(dataSourceId: string, property: string, value: string): Promise<NotionPage | null> {
    const response = await this.queryDataSource(dataSourceId, {
      filter: {
        property,
        email: { equals: value },
      },
      page_size: 1,
    });
    return response.results[0] ?? null;
  }

  private async retrievePage(pageId: string): Promise<NotionPage | null> {
    try {
      return await this.request<NotionPage>(`pages/${pageId}`, "get");
    } catch {
      return null;
    }
  }

  private async updatePage(pageId: string, properties: Record<string, unknown>): Promise<void> {
    await this.request(`pages/${pageId}`, "patch", {
      properties,
    });
  }

  private async createPage(
    dataSourceId: string,
    title: string,
    properties: Record<string, unknown>,
    children?: unknown[],
  ): Promise<{ id: string; url: string | undefined }> {
    const page = await this.request<NotionPage>("pages", "post", {
      parent: { data_source_id: dataSourceId },
      properties: {
        Name: titleValue(title),
        ...properties,
      },
      ...(children ? { children } : {}),
    });
    return { id: page.id, url: page.url };
  }

  private async upsertPage(
    dataSourceId: string,
    keyPropertyName: string,
    keyValue: string,
    title: string,
    properties: Record<string, unknown>,
  ): Promise<{ id: string; url: string | undefined }> {
    const existing = await this.findPageByRichText(dataSourceId, keyPropertyName, keyValue);
    const normalized = {
      [keyPropertyName]: richText(keyValue),
      ...properties,
    };

    if (existing) {
      await this.updatePage(existing.id, {
        Name: titleValue(title),
        ...normalized,
      });
      return { id: existing.id, url: existing.url };
    }

    return this.createPage(dataSourceId, title, normalized);
  }
}

function titleValue(value: string) {
  return {
    title: [
      {
        type: "text",
        text: { content: compactText(value, 200) || "Untitled" },
      },
    ],
  };
}

function richText(value: string) {
  return {
    rich_text: value
      ? [
          {
            type: "text",
            text: { content: compactText(value, 1900) },
          },
        ]
      : [],
  };
}

function paragraphBlock(value: string) {
  return {
    object: "block",
    type: "paragraph",
    paragraph: {
      rich_text: [
        {
          type: "text",
          text: { content: compactText(value, 1900) },
        },
      ],
    },
  };
}

function dateValue(value: string | null) {
  return value
    ? {
        date: {
          start: value,
        },
      }
    : { date: null };
}

function emailValue(value: string) {
  return { email: value || null };
}

function urlValue(value: string) {
  return { url: value || null };
}

function checkboxValue(value: boolean) {
  return { checkbox: value };
}

function numberValue(value: number) {
  return { number: value };
}

function selectValue(value: string) {
  return value ? { select: { name: value } } : { select: null };
}

function relationValue(pageIds: string[]) {
  return {
    relation: pageIds.map((id) => ({ id })),
  };
}

function extractTitle(page: NotionPage, property: string): string {
  const prop = page.properties?.[property] as
    | {
        title?: Array<{ plain_text?: string }>;
      }
    | undefined;
  return prop?.title?.map((item) => item.plain_text ?? "").join("").trim() || "Untitled";
}

function extractRichText(page: NotionPage, property: string): string {
  const prop = page.properties?.[property] as
    | {
        rich_text?: Array<{ plain_text?: string }>;
      }
    | undefined;
  return prop?.rich_text?.map((item) => item.plain_text ?? "").join("").trim() || "";
}

function normalizeCalendarStatus(status: string): string {
  if (status === "cancelled") {
    return "cancelled";
  }
  if (status === "tentative") {
    return "tentative";
  }
  return "confirmed";
}

function mapManagedStateToFollowUpStatus(state: DecisionProposal["proposedState"]): string {
  switch (state) {
    case "state/waiting":
      return "Waiting";
    case "state/reference":
    case "state/ignored":
      return "Done";
    case "state/scheduled":
      return "Planned";
    default:
      return "Needs action";
  }
}
