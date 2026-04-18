import { describe, expect, it, vi } from "vitest";

import { ReconcileService } from "../src/services/reconcile";
import { DecisionProposal } from "../src/types";

describe("ReconcileService", () => {
  it("blocks approval when the human-read gate is active", async () => {
    const payload: DecisionProposal = {
      decisionId: "email-123",
      sourceType: "email",
      sourceExternalId: "123",
      title: "Inbox triage — Test",
      reviewReason: "Unread mail",
      confidence: 0.5,
      proposedState: "triage/pending-review",
      gmailUrl: "https://mail.google.com",
      notionUrl: undefined,
      readGateBlocked: true,
      diff: [],
      target: {},
      summary: "Example summary",
      createdAt: new Date().toISOString(),
    };

    let status = "pending";
    const store = {
      getDecision: vi.fn().mockImplementation(() => ({
        decisionId: payload.decisionId,
        notionPageId: null,
        sourceType: payload.sourceType,
        sourceExternalId: payload.sourceExternalId,
        status,
        title: payload.title,
        gmailUrl: payload.gmailUrl ?? null,
        notionUrl: null,
        readGateBlocked: true,
        payload,
        createdAt: payload.createdAt,
        updatedAt: payload.createdAt,
      })),
      updateDecisionStatus: vi.fn().mockImplementation((_decisionId, nextStatus) => {
        status = nextStatus;
      }),
      addSuppressionHint: vi.fn(),
    };

    const gmail = { applyApprovedState: vi.fn() };
    const notion = {
      isConfigured: () => false,
      staleIfBusinessMoved: async () => false,
    };

    const reconcile = new ReconcileService(
      { localApproverName: "Local operator" } as any,
      store,
      gmail as any,
      notion as any,
    );

    await expect(reconcile.applyDecision("email-123", "approve")).rejects.toThrow("human-read gate");
    expect(gmail.applyApprovedState).not.toHaveBeenCalled();

    await reconcile.applyDecision("email-123", "approve", { overrideReadGate: true });
    expect(gmail.applyApprovedState).toHaveBeenCalledOnce();
    expect(status).toBe("approved");
  });

  it("builds proposals for synced email threads and stores them as pending decisions", async () => {
    const saved: Array<{ decisionId: string; payload: DecisionProposal }> = [];
    const store = {
      hasSuppressionHint: vi.fn().mockReturnValue(false),
      upsertDecision: vi.fn().mockImplementation((entry) => {
        saved.push({ decisionId: entry.decisionId, payload: entry.payload });
      }),
    };

    const notion = {
      isConfigured: () => true,
      findContactByEmail: async () => ({ id: "contact-1", title: "Jane Doe", url: "https://notion.so/contact-1" }),
      findSingleOpenOpportunity: async () => ({ id: "opp-1", title: "Pilot", url: "https://notion.so/opp-1" }),
      upsertDecision: async () => ({ id: "decision-1", url: "https://notion.so/decision-1" }),
    };

    const reconcile = new ReconcileService(
      { localApproverName: "Local operator" } as any,
      store as any,
      {} as any,
      notion as any,
    );

    const proposals = await reconcile.refreshEmailProposals([
      {
        threadId: "thread-1",
        historyId: "10",
        subject: "Pilot follow-up",
        participants: ["jane@example.com"],
        senderEmail: "jane@example.com",
        senderName: "Jane Doe",
        snippet: "Could we continue next week?",
        summary: "Pilot follow-up — Could we continue next week?",
        excerpt: "Could we continue next week?",
        labels: [],
        unread: false,
        lastMessageAt: new Date().toISOString(),
        inboundCount: 1,
        outboundCount: 0,
        userReadRequired: false,
        userReadConfirmed: true,
        gmailUrl: "https://mail.google.com/thread-1",
      },
    ]);

    expect(proposals).toHaveLength(1);
    expect(proposals[0]?.target.contactId).toBe("contact-1");
    expect(saved).toHaveLength(1);
    expect(saved[0]?.payload.proposedState).toBe("state/action");
  });
});
