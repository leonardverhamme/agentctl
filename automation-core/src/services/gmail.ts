import { gmail_v1, google } from "googleapis";

import { AppConfig, MANAGED_GMAIL_LABELS } from "../config";
import { stableHash } from "../lib/hash";
import { compactText, parseDisplayName, unique } from "../lib/text";
import { nowIso } from "../lib/time";
import type { LocalStore } from "../store";
import { EmailThreadSnapshot, ManagedThreadState } from "../types";
import { GoogleAuthService } from "./google-auth";

const MANAGED_STATE_LABELS = MANAGED_GMAIL_LABELS.filter((label) => label.startsWith("triage/") || label.startsWith("state/"));

export class GmailService {
  constructor(
    private readonly config: AppConfig,
    private readonly store: LocalStore,
    private readonly auth: GoogleAuthService,
  ) {}

  async syncMailbox(): Promise<{ mode: "full" | "incremental"; threads: EmailThreadSnapshot[]; fallbackUsed: boolean }> {
    const client = await this.auth.getAuthorizedClient();
    const gmail = google.gmail({ version: "v1", auth: client });
    const profile = await gmail.users.getProfile({ userId: "me" });
    const localEmail = (this.config.googleAccountEmail || profile.data.emailAddress || "").toLowerCase();
    const labelMap = await this.ensureManagedLabels(gmail);

    const previousHistoryId = this.store.getSyncState("gmail", "historyId");
    const threadIds = new Set<string>();
    let fallbackUsed = false;
    let mode: "full" | "incremental" = previousHistoryId ? "incremental" : "full";
    let nextHistoryId = previousHistoryId ?? "0";

    if (previousHistoryId) {
      try {
        let pageToken: string | undefined;
        do {
          const response = await gmail.users.history.list({
            userId: this.config.googleGmailUser,
            startHistoryId: previousHistoryId,
            pageToken,
            maxResults: 500,
          });

          for (const historyItem of response.data.history ?? []) {
            const candidates = [
              ...(historyItem.messages ?? []),
              ...(historyItem.messagesAdded?.map((entry) => entry.message) ?? []),
              ...(historyItem.labelsAdded?.map((entry) => entry.message) ?? []),
              ...(historyItem.labelsRemoved?.map((entry) => entry.message) ?? []),
            ];

            for (const message of candidates) {
              if (message?.threadId) {
                threadIds.add(message.threadId);
              }
            }
          }

          if (response.data.historyId) {
            nextHistoryId = response.data.historyId;
          }

          pageToken = response.data.nextPageToken ?? undefined;
        } while (pageToken);
      } catch (error) {
        const httpStatus = (error as { code?: number }).code;
        if (httpStatus !== 404) {
          throw error;
        }
        fallbackUsed = true;
        mode = "full";
        threadIds.clear();
      }
    }

    if (mode === "full") {
      const listTargets = ["INBOX", ...Object.values(labelMap)];
      for (const labelId of unique(listTargets)) {
        let pageToken: string | undefined;
        do {
          const response = await gmail.users.threads.list({
            userId: this.config.googleGmailUser,
            labelIds: [labelId],
            maxResults: this.config.googleGmailFullSyncLimit,
            pageToken,
          });
          for (const thread of response.data.threads ?? []) {
            if (thread.id) {
              threadIds.add(thread.id);
            }
          }
          pageToken = response.data.nextPageToken ?? undefined;
        } while (pageToken);
      }
    }

    const threads: EmailThreadSnapshot[] = [];
    for (const threadId of threadIds) {
      const response = await gmail.users.threads.get({
        userId: this.config.googleGmailUser,
        id: threadId,
        format: "full",
      });
      const snapshot = this.toThreadSnapshot(response.data, localEmail, labelMap);
      if (!snapshot) {
        continue;
      }
      nextHistoryId = response.data.historyId ?? nextHistoryId;
      threads.push(snapshot);
      this.store.upsertSourceCache("gmail", "thread", snapshot.threadId, stableHash(snapshot), snapshot);
    }

    if (nextHistoryId !== "0") {
      this.store.setSyncState("gmail", "historyId", nextHistoryId);
      this.store.setSyncState("gmail", "lastSyncAt", nowIso());
    }

    return { mode, threads, fallbackUsed };
  }

  async ensureManagedLabels(gmail?: gmail_v1.Gmail): Promise<Record<string, string>> {
    const client = gmail ?? google.gmail({ version: "v1", auth: await this.auth.getAuthorizedClient() });
    const response = await client.users.labels.list({ userId: this.config.googleGmailUser });
    const labelMap = new Map<string, string>();
    for (const label of response.data.labels ?? []) {
      if (label.name && label.id) {
        labelMap.set(label.name, label.id);
      }
    }

    for (const managedLabel of MANAGED_GMAIL_LABELS) {
      if (labelMap.has(managedLabel)) {
        continue;
      }
      const created = await client.users.labels.create({
        userId: this.config.googleGmailUser,
        requestBody: {
          name: managedLabel,
          labelListVisibility: "labelShow",
          messageListVisibility: "show",
        },
      });
      if (created.data.id) {
        labelMap.set(managedLabel, created.data.id);
      }
    }

    const result: Record<string, string> = {};
    for (const managedLabel of MANAGED_GMAIL_LABELS) {
      const id = labelMap.get(managedLabel);
      if (!id) {
        throw new Error(`Managed Gmail label ${managedLabel} was not created.`);
      }
      result[managedLabel] = id;
    }

    return result;
  }

  async applyApprovedState(threadId: string, state: ManagedThreadState): Promise<void> {
    const client = await this.auth.getAuthorizedClient();
    const gmail = google.gmail({ version: "v1", auth: client });
    const labelMap = await this.ensureManagedLabels(gmail);

    const addLabelIds = [labelMap[state], labelMap["system/linked"]];
    const removeLabelIds = MANAGED_STATE_LABELS.filter((label) => label !== state).map((label) => labelMap[label]);

    await gmail.users.threads.modify({
      userId: this.config.googleGmailUser,
      id: threadId,
      requestBody: {
        addLabelIds,
        removeLabelIds,
      },
    });
  }

  getThreadUrl(threadId: string): string {
    return `https://mail.google.com/mail/u/0/#all/${threadId}`;
  }

  private toThreadSnapshot(
    thread: gmail_v1.Schema$Thread,
    localEmail: string,
    labelMap: Record<string, string>,
  ): EmailThreadSnapshot | null {
    const messages = thread.messages ?? [];
    if (!thread.id || !thread.historyId || messages.length === 0) {
      return null;
    }

    const participants: string[] = [];
    let senderEmail = "";
    let senderName = "";
    let subject = "";
    let latestSnippet = thread.snippet ?? "";
    let lastMessageAt = new Date(0).toISOString();
    let unread = false;
    let inboundCount = 0;
    let outboundCount = 0;
    let unreadExternal = false;

    for (const message of messages) {
      const headers = message.payload?.headers ?? [];
      const fromHeader = headers.find((header) => header.name?.toLowerCase() === "from")?.value ?? "";
      const subjectHeader = headers.find((header) => header.name?.toLowerCase() === "subject")?.value ?? "";
      const { email, name } = parseDisplayName(fromHeader);
      const snippet = message.snippet ?? "";
      const messageDate = message.internalDate ? new Date(Number(message.internalDate)).toISOString() : new Date(0).toISOString();

      if (messageDate > lastMessageAt) {
        lastMessageAt = messageDate;
        latestSnippet = snippet || latestSnippet;
      }

      if (subjectHeader) {
        subject = subjectHeader;
      }
      if (email) {
        participants.push(email);
      }
      if (!senderEmail) {
        senderEmail = email;
        senderName = name;
      }

      const isLocal = Boolean(localEmail && email === localEmail);
      if (isLocal) {
        outboundCount += 1;
      } else {
        inboundCount += 1;
      }

      const isUnread = (message.labelIds ?? []).includes("UNREAD");
      unread = unread || isUnread;
      if (!isLocal && isUnread) {
        unreadExternal = true;
      }
    }

    const managedNames = Object.entries(labelMap)
      .filter(([, id]) => thread.messages?.some((message) => (message.labelIds ?? []).includes(id)))
      .map(([name]) => name);

    return {
      threadId: thread.id,
      historyId: thread.historyId,
      subject: subject || "Untitled thread",
      participants: unique(participants),
      senderEmail,
      senderName,
      snippet: compactText(latestSnippet, 160),
      excerpt: compactText(latestSnippet, 280),
      summary: compactText(`${subject || "Untitled thread"} — ${latestSnippet}`),
      labels: unique(managedNames),
      unread,
      lastMessageAt,
      inboundCount,
      outboundCount,
      userReadRequired: unreadExternal,
      userReadConfirmed: !unreadExternal,
      gmailUrl: this.getThreadUrl(thread.id),
    };
  }
}
