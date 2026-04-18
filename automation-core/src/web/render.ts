import {
  AnalyticsFilters,
  AnalyticsSummarySnapshot,
  CommitFact,
  ContributorRecord,
  GitHubRepositoryRecord,
  IssueFact,
  PullRequestFact,
  PullRequestReviewFact,
  ReleaseFact,
  RepoRollup,
  TrendPoint,
  WeeklyEngineeringBrief,
  WorkflowRunFact,
  QueueSnapshot,
} from "../types";

type Tone = "ok" | "pending" | "warn" | "danger";

interface MetricSegment {
  label: string;
  value: number;
  tone: Tone;
}

export function renderDashboard(queue: QueueSnapshot): string {
  const decisions = queue.decisions;
  const inboxItems = decisions.filter((item) => item.sourceType === "email");
  const waitingItems = decisions.filter((item) => item.payload.proposedState === "state/waiting");
  const meetingItems = decisions.filter((item) => item.sourceType === "meeting");
  const blockedItems = decisions.filter((item) => item.readGateBlocked || item.payload.confidence < 0.6);
  const actionItems = decisions.filter((item) => item.payload.proposedState === "state/action");

  const queueSegments: MetricSegment[] = [
    { label: "Action", value: actionItems.length, tone: "pending" },
    { label: "Inbox", value: inboxItems.length, tone: "warn" },
    { label: "Waiting", value: waitingItems.length, tone: "ok" },
    { label: "Meetings", value: meetingItems.length, tone: "pending" },
    { label: "Blocked", value: blockedItems.length, tone: "danger" },
  ];
  const runSegments = summarizeRuns(queue.latestRuns);
  const confidenceSegments = summarizeConfidence(decisions);
  const dueSegments = summarizeDue(decisions);
  const avgConfidence = decisions.length
    ? (decisions.reduce((sum, item) => sum + item.payload.confidence, 0) / decisions.length).toFixed(2)
    : "0.00";
  const successfulRuns = runSegments.find((segment) => segment.label === "OK")?.value ?? 0;
  const runSuccessRate = queue.latestRuns.length ? Math.round((successfulRuns / queue.latestRuns.length) * 100) : 0;

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="icon" href="/favicon.ico" sizes="any" />
    <title>automation-core</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f7faff;
        --surface: #ffffff;
        --surface-subtle: #fbfdff;
        --surface-muted: #eef5ff;
        --surface-strong: #e4eeff;
        --ink: #0f172a;
        --muted: #5e6d8a;
        --line: #d9e5f4;
        --accent: #2563eb;
        --accent-strong: #1d4ed8;
        --accent-soft: #e7f0ff;
        --focus: #1d4ed8;
        --warn: #8a6112;
        --warn-soft: #fff3da;
        --danger: #8f3531;
        --danger-soft: #fdeceb;
        --ok: #1d4ed8;
        --ok-soft: #ebf3ff;
        --mono: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
      }

      * { box-sizing: border-box; }

      body {
        margin: 0;
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        background:
          linear-gradient(180deg, rgba(37, 99, 235, 0.06), transparent 140px),
          linear-gradient(135deg, rgba(228, 238, 255, 0.38), transparent 58%),
          var(--bg);
        color: var(--ink);
      }

      a { color: inherit; }

      button,
      a {
        transition: background-color 120ms ease, border-color 120ms ease, color 120ms ease;
      }

      :focus-visible {
        outline: 2px solid var(--focus);
        outline-offset: 2px;
      }

      .shell {
        max-width: 1520px;
        margin: 0 auto;
        padding: 12px;
      }

      .panel {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
      }

      .topbar {
        display: grid;
        grid-template-columns: minmax(0, 1.5fr) minmax(260px, 0.8fr);
        gap: 10px;
        padding: 10px 12px;
        margin-bottom: 10px;
      }

      .brand {
        display: grid;
        gap: 3px;
      }

      .eyebrow,
      .section-label,
      .chart-label,
      .item-kicker,
      .field-name {
        color: var(--muted);
        font-size: 9px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
      }

      h1 {
        margin: 0;
        font-size: 20px;
        line-height: 1.1;
      }

      h2 {
        margin: 0;
        font-size: 13px;
        line-height: 1.2;
      }

      .headline,
      .queue-description,
      .meta,
      .empty,
      .chart-note {
        color: var(--muted);
        font-size: 11px;
        line-height: 1.4;
      }

      .topbar-status,
      .queue-heading,
      .workspace,
      .metric,
      .field-list,
      .queue-item,
      .trend-card,
      .trend-heading,
      .trend-stat,
      .row-title {
        display: grid;
      }

      .topbar-status {
        gap: 8px;
        justify-items: end;
        align-content: center;
      }

      .app-nav {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        align-items: center;
      }

      .app-link {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 7px;
        border: 1px solid var(--line);
        border-radius: 999px;
        font-size: 10px;
        line-height: 1;
        text-decoration: none;
        background: var(--surface-subtle);
      }

      .app-link.active {
        color: var(--accent);
        background: #fff;
        border-color: rgba(29, 78, 216, 0.24);
      }

      .status-rail,
      .meta-rail,
      .badge-row,
      .inline-links,
      .compact-actions,
      .trend-stats,
      .sparkline {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        align-items: center;
      }

      .status-pill,
      .badge,
      .inline-link,
      .trend-stat {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        border: 1px solid var(--line);
        border-radius: 999px;
        white-space: nowrap;
      }

      .status-pill,
      .badge {
        padding: 3px 7px;
        font-size: 10px;
        line-height: 1;
        background: var(--surface-muted);
      }

      .status-pill::before,
      .badge::before {
        content: "";
        width: 6px;
        height: 6px;
        border-radius: 999px;
        background: currentColor;
        opacity: 0.75;
      }

      .status-pill.ok,
      .badge.ok {
        color: var(--ok);
        background: var(--ok-soft);
      }

      .status-pill.pending,
      .badge.pending {
        color: var(--accent);
        background: var(--accent-soft);
      }

      .status-pill.warn,
      .badge.warn {
        color: var(--warn);
        background: var(--warn-soft);
      }

      .status-pill.danger,
      .badge.danger {
        color: var(--danger);
        background: var(--danger-soft);
      }

      .mono {
        font-family: var(--mono);
      }

      .workspace {
        gap: 10px;
      }

      .summary {
        padding: 10px;
      }

      .summary-grid {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 6px;
      }

      .metric {
        gap: 4px;
        padding: 8px;
        border: 1px solid var(--line);
        border-radius: 6px;
        background: linear-gradient(180deg, var(--surface), var(--surface-subtle));
      }

      .metric strong {
        font-size: 22px;
        line-height: 1;
        letter-spacing: -0.03em;
      }

      .metric .meta {
        font-size: 10px;
      }

      .section {
        padding: 10px 12px;
      }

      .queue-heading {
        gap: 1px;
        margin-bottom: 8px;
      }

      .trend-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 8px;
      }

      .trend-card {
        gap: 8px;
        padding: 10px;
        border: 1px solid var(--line);
        border-radius: 6px;
        background: linear-gradient(180deg, var(--surface), var(--surface-subtle));
      }

      .trend-heading {
        gap: 2px;
      }

      .chart-value {
        font-size: 20px;
        font-weight: 700;
        letter-spacing: -0.03em;
      }

      .stack {
        display: grid;
        grid-auto-flow: column;
        gap: 3px;
        width: 100%;
        min-height: 16px;
        padding: 3px;
        border: 1px solid var(--line);
        border-radius: 999px;
        background: var(--surface-muted);
      }

      .stack.is-empty {
        min-height: 16px;
      }

      .stack-segment {
        min-width: 6px;
        border-radius: 999px;
      }

      .trend-stats {
        gap: 5px;
      }

      .trend-stat {
        padding: 3px 6px;
        font-size: 10px;
        line-height: 1;
        background: var(--surface);
      }

      .trend-stat strong {
        font-size: 10px;
      }

      .sparkline {
        flex-wrap: nowrap;
        align-items: end;
        min-height: 58px;
        padding: 4px;
        border: 1px solid var(--line);
        border-radius: 6px;
        background: var(--surface-muted);
      }

      .spark-bar {
        flex: 1 1 0;
        min-width: 8px;
        border-radius: 3px 3px 2px 2px;
        border: 1px solid transparent;
      }

      .stack-segment.ok,
      .spark-bar.ok {
        color: var(--ok);
        background: var(--ok-soft);
      }

      .stack-segment.pending,
      .spark-bar.pending {
        color: var(--accent);
        background: var(--accent-soft);
      }

      .stack-segment.warn,
      .spark-bar.warn {
        color: var(--warn);
        background: var(--warn-soft);
      }

      .stack-segment.danger,
      .spark-bar.danger {
        color: var(--danger);
        background: var(--danger-soft);
      }

      .spark-bar.ok { border-color: rgba(37, 99, 235, 0.15); }
      .spark-bar.pending { border-color: rgba(29, 78, 216, 0.18); }
      .spark-bar.warn { border-color: rgba(138, 97, 18, 0.18); }
      .spark-bar.danger { border-color: rgba(143, 53, 49, 0.18); }

      .table-wrap {
        overflow-x: auto;
        border: 1px solid var(--line);
        border-radius: 6px;
        background: var(--surface-subtle);
      }

      .data-table,
      .queue-table,
      .runs-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        font-size: 11px;
      }

      .data-table { min-width: 980px; }

      .data-table th,
      .data-table td,
      .queue-table th,
      .queue-table td,
      .runs-table th,
      .runs-table td {
        padding: 7px 8px;
        text-align: left;
        vertical-align: top;
        border-top: 1px solid var(--line);
      }

      .data-table thead th,
      .queue-table thead th,
      .runs-table thead th {
        border-top: 0;
        background: var(--surface-strong);
        color: var(--muted);
        font-size: 9px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      .data-table tbody tr:nth-child(even),
      .queue-table tbody tr:nth-child(even),
      .runs-table tbody tr:nth-child(even) {
        background: rgba(239, 245, 255, 0.45);
      }

      .row-title,
      .queue-item {
        gap: 2px;
      }

      .row-title strong,
      .queue-item strong {
        font-size: 12px;
        line-height: 1.35;
      }

      .field-list {
        gap: 3px;
      }

      .field-row {
        display: grid;
        gap: 2px;
      }

      .field-change {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
        align-items: center;
      }

      .from,
      .arrow {
        color: var(--muted);
      }

      .to {
        color: var(--accent);
        font-weight: 600;
      }

      .inline-link {
        padding: 3px 6px;
        font-size: 10px;
        text-decoration: none;
        background: var(--surface);
      }

      .inline-link:hover {
        background: var(--surface-muted);
      }

      .board {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
      }

      .queue {
        overflow: hidden;
      }

      .queue-header {
        display: flex;
        justify-content: space-between;
        align-items: start;
        gap: 10px;
        padding: 10px 12px;
        border-bottom: 1px solid var(--line);
        background: linear-gradient(180deg, var(--surface-subtle), var(--surface-muted));
      }

      .queue-count {
        min-width: 32px;
        padding: 4px 6px;
        border: 1px solid var(--line);
        border-radius: 6px;
        background: var(--surface);
        font-size: 11px;
        font-weight: 600;
        text-align: center;
      }

      .button,
      button {
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 6px 8px;
        font: inherit;
        font-size: 11px;
        line-height: 1.1;
        cursor: pointer;
        background: var(--accent);
        color: #ffffff;
        text-decoration: none;
      }

      button:hover,
      .button:hover {
        background: var(--accent-strong);
      }

      button.reject {
        background: var(--danger);
      }

      button.warn {
        background: var(--warn);
      }

      .runs {
        padding: 10px 12px;
      }

      .runs-layout {
        display: grid;
        grid-template-columns: minmax(300px, 0.8fr) minmax(0, 1.2fr);
        gap: 10px;
      }

      .runs-card {
        display: grid;
        gap: 8px;
        padding: 10px;
        border: 1px solid var(--line);
        border-radius: 6px;
        background: linear-gradient(180deg, var(--surface), var(--surface-subtle));
      }

      .runs-table td:first-child,
      .data-table td:first-child {
        font-family: var(--mono);
      }

      .empty {
        margin: 10px 12px 12px;
        padding: 12px;
        border: 1px dashed var(--line);
        border-radius: 6px;
      }

      @media (max-width: 1180px) {
        .topbar,
        .board {
          grid-template-columns: 1fr;
        }

        .topbar-status {
          justify-items: start;
        }
      }

      @media (max-width: 1240px) {
        .summary-grid,
        .trend-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .runs-layout {
          grid-template-columns: 1fr;
        }
      }

      @media (max-width: 720px) {
        .shell {
          padding: 10px;
        }

        .summary-grid,
        .trend-grid {
          grid-template-columns: 1fr;
        }

        .actions {
          width: 100%;
        }

        .actions > * {
          flex: 1 1 96px;
          text-align: center;
          justify-content: center;
        }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <header class="panel topbar">
        <div class="brand">
          <div class="eyebrow">automation-core</div>
          <h1>Operator console</h1>
          <p class="headline">Notion authoritative. Manual review.</p>
          <div class="app-nav" aria-label="Surfaces">
            <a class="app-link active" href="/">Operator</a>
            <a class="app-link" href="/analytics">GitHub analytics</a>
          </div>
        </div>
        <div class="topbar-status">
          <div class="status-rail" aria-label="System posture">
            <span class="status-pill ok">Notion</span>
            <span class="status-pill pending">Approval</span>
            <span class="status-pill warn">No send</span>
          </div>
          <div class="meta-rail">
            <span class="mono">queue:${decisions.length}</span>
            <span class="mono">avg:${avgConfidence}</span>
            <span class="mono">ok:${runSuccessRate}%</span>
          </div>
        </div>
      </header>

      <main class="workspace">
        <section class="panel summary" aria-label="Queue overview">
          <div class="summary-grid">
            ${renderMetric("Pending", decisions.length, `${actionItems.length} action`)}
            ${renderMetric("Inbox", inboxItems.length, `${blockedItems.filter((item) => item.sourceType === "email").length} gated`)}
            ${renderMetric("Waiting", waitingItems.length, `${decisions.length ? Math.round((waitingItems.length / decisions.length) * 100) : 0}% mix`)}
            ${renderMetric("Meetings", meetingItems.length, `${meetingItems.filter((item) => item.payload.dueAt).length} due`)}
            ${renderMetric("Blocked", blockedItems.length, `${confidenceSegments.find((segment) => segment.label === "Low")?.value ?? 0} low conf`)}
            ${renderMetric("Runs", queue.latestRuns.length, `${successfulRuns} ok`)}
          </div>
        </section>

        <section class="panel section" aria-labelledby="trend-overview">
          <div class="queue-heading">
            <div class="eyebrow">Dashboard</div>
            <h2 id="trend-overview">Trend overview</h2>
            <div class="queue-description">Live queue and run signal.</div>
          </div>
          <div class="trend-grid">
            ${renderTrendCard(
              "Queue mix",
              `${decisions.length}`,
              renderStackBar(queueSegments, "Queue mix"),
              renderTrendStats(queueSegments),
              "pending items",
            )}
            ${renderTrendCard(
              "Confidence",
              avgConfidence,
              renderStackBar(confidenceSegments, "Decision confidence"),
              renderTrendStats(confidenceSegments),
              "avg score",
            )}
            ${renderTrendCard(
              "Due pressure",
              `${dueSegments.find((segment) => segment.label === "Now")?.value ?? 0}`,
              renderStackBar(dueSegments, "Due pressure"),
              renderTrendStats(dueSegments),
              "need action now",
            )}
            ${renderTrendCard(
              "Run trend",
              `${runSuccessRate}%`,
              renderRunSpark(queue.latestRuns),
              renderTrendStats(runSegments),
              "success rate",
            )}
          </div>
        </section>

        <section class="panel section" aria-labelledby="decision-overview">
          <div class="queue-heading">
            <div class="eyebrow">Queue</div>
            <h2 id="decision-overview">Decision overview</h2>
            <div class="queue-description">Primary table.</div>
          </div>
          ${renderDecisionOverviewTable(queue)}
        </section>

        <section class="board" aria-label="Decision queues">
          ${renderQueue("Inbox", "Unread inbound", inboxItems)}
          ${renderQueue("Waiting", "Awaiting reply", waitingItems)}
          ${renderQueue("Meetings", "Post-meeting", meetingItems)}
          ${renderQueue("Blocked", "Read gate or low confidence", blockedItems)}
        </section>

        <section class="panel runs" aria-labelledby="daily-overview">
          <div class="queue-heading">
            <div class="eyebrow">Operations</div>
            <h2 id="daily-overview">Daily overview</h2>
            <div class="queue-description">Latest runs.</div>
          </div>
          ${renderRuns(queue)}
        </section>
      </main>
    </div>
    <script>
      async function postJson(url, body) {
        const response = await fetch(url, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(body || {}),
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => ({ error: response.statusText }));
          throw new Error(payload.error || "Request failed");
        }
        return response.json();
      }

      async function handleAction(decisionId, action) {
        try {
          const note = action === "reject" ? window.prompt("Optional rejection note") || "" : "";
          const overrideReadGate = action === "approve" && window.confirm("Override the human-read gate if needed?");
          await postJson(\`/decisions/\${decisionId}/\${action}\`, {
            note,
            overrideReadGate,
          });
          window.location.reload();
        } catch (error) {
          window.alert(error.message);
        }
      }

      document.querySelectorAll("[data-action]").forEach((button) => {
        button.addEventListener("click", () => {
          handleAction(button.dataset.decisionId, button.dataset.action);
        });
      });
    </script>
  </body>
</html>`;
}

function renderMetric(label: string, value: number, meta?: string): string {
  return `
    <article class="metric">
      <span class="eyebrow">${escapeHtml(label)}</span>
      <strong>${value}</strong>
      ${meta ? `<span class="meta">${escapeHtml(meta)}</span>` : ""}
    </article>
  `;
}

function renderTrendCard(title: string, value: string, chart: string, footer: string, note: string): string {
  return `
    <article class="trend-card">
      <div class="trend-heading">
        <span class="chart-label">${escapeHtml(title)}</span>
        <span class="chart-value">${escapeHtml(value)}</span>
        <span class="chart-note">${escapeHtml(note)}</span>
      </div>
      ${chart}
      ${footer}
    </article>
  `;
}

function renderStackBar(segments: MetricSegment[], ariaLabel: string): string {
  const total = segments.reduce((sum, segment) => sum + segment.value, 0);
  if (total === 0) {
    return `<div class="stack is-empty" role="img" aria-label="${escapeHtml(ariaLabel)}"></div>`;
  }

  return `
    <div class="stack" role="img" aria-label="${escapeHtml(ariaLabel)}">
      ${segments
        .filter((segment) => segment.value > 0)
        .map((segment) => {
          const basis = Math.max(6, Math.round((segment.value / total) * 100));
          return `<span class="stack-segment ${segment.tone}" style="flex:${basis} 1 0%" title="${escapeHtml(`${segment.label}: ${segment.value}`)}"></span>`;
        })
        .join("")}
    </div>
  `;
}

function renderTrendStats(segments: MetricSegment[]): string {
  return `
    <div class="trend-stats">
      ${segments
        .map(
          (segment) => `
            <span class="trend-stat">
              <span>${escapeHtml(segment.label)}</span>
              <strong>${segment.value}</strong>
            </span>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderRunSpark(runs: QueueSnapshot["latestRuns"]): string {
  if (runs.length === 0) {
    return `<div class="sparkline" role="img" aria-label="No job runs"></div>`;
  }

  return `
    <div class="sparkline" role="img" aria-label="Recent job runs">
      ${[...runs]
        .reverse()
        .map((run) => {
          const tone = badgeTone(run.status);
          const height = sparkHeightForStatus(run.status);
          return `<span class="spark-bar ${tone}" style="height:${height}px" title="${escapeHtml(`${run.jobName} ${run.status}`)}"></span>`;
        })
        .join("")}
    </div>
  `;
}

function renderDecisionOverviewTable(queue: QueueSnapshot): string {
  if (queue.decisions.length === 0) {
    return `<div class="empty">No approval items.</div>`;
  }

  return `
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Item</th>
            <th>State</th>
            <th>Reason</th>
            <th>Proposed changes</th>
            <th>Due</th>
            <th>Links</th>
          </tr>
        </thead>
        <tbody>
          ${queue.decisions
            .map(
              (item) => `
                <tr>
                  <td>
                    <div class="row-title">
                      <span class="item-kicker">${escapeHtml(item.sourceType)}</span>
                      <strong>${escapeHtml(item.title)}</strong>
                      <span class="meta mono">${escapeHtml(item.decisionId)}</span>
                    </div>
                  </td>
                  <td>
                    <div class="field-list">
                      <span class="badge ${item.readGateBlocked ? "warn" : badgeTone(item.payload.proposedState)}">${escapeHtml(item.readGateBlocked ? "Read gate" : item.payload.proposedState)}</span>
                      <span class="meta">c:${item.payload.confidence.toFixed(2)}</span>
                    </div>
                  </td>
                  <td>
                    <div class="field-list">
                      <span>${escapeHtml(item.payload.reviewReason)}</span>
                      ${item.payload.waitingOn ? `<span class="meta">${escapeHtml(item.payload.waitingOn)}</span>` : ""}
                    </div>
                  </td>
                  <td>${renderInlineDiffList(item.payload.diff)}</td>
                  <td class="mono">${escapeHtml(item.payload.dueAt ? formatTimestamp(item.payload.dueAt) : "Not set")}</td>
                  <td>
                    <div class="inline-links">
                      ${item.gmailUrl ? `<a class="inline-link" href="${item.gmailUrl}" target="_blank" rel="noreferrer">Open Gmail</a>` : ""}
                      ${item.notionUrl ? `<a class="inline-link" href="${item.notionUrl}" target="_blank" rel="noreferrer">Open Notion</a>` : ""}
                    </div>
                  </td>
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderQueue(title: string, description: string, items: QueueSnapshot["decisions"]): string {
  if (items.length === 0) {
    return `
      <section class="panel queue">
        <div class="queue-header">
          <div class="queue-heading">
            <h2>${escapeHtml(title)}</h2>
            <div class="queue-description">${escapeHtml(description)}</div>
          </div>
          <div class="queue-count">0</div>
        </div>
        <div class="empty">No items.</div>
      </section>
    `;
  }

  return `
    <section class="panel queue">
      <div class="queue-header">
        <div class="queue-heading">
          <h2>${escapeHtml(title)}</h2>
          <div class="queue-description">${escapeHtml(description)}</div>
        </div>
        <div class="queue-count">${items.length}</div>
      </div>
      <table class="queue-table">
        <thead>
          <tr>
            <th>Item</th>
            <th>State</th>
            <th>Due</th>
            <th>Links</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${items.map((item) => renderQueueRow(item)).join("")}
        </tbody>
      </table>
    </section>
  `;
}

function renderQueueRow(item: QueueSnapshot["decisions"][number]): string {
  const proposedTone = badgeTone(item.payload.proposedState);
  const readGateBadge = item.readGateBlocked ? `<span class="badge warn">Read gate</span>` : "";
  const snoozeBadge = item.payload.snoozedUntil ? `<span class="badge ok">Snoozed</span>` : "";

  return `
    <tr>
      <td>
        <div class="queue-item">
          <div class="item-kicker">${escapeHtml(item.sourceType)}</div>
          <strong>${escapeHtml(item.title)}</strong>
          <div class="meta">${escapeHtml(item.payload.reviewReason)}</div>
        </div>
      </td>
      <td>
        <div class="badge-row">
          ${readGateBadge}
          <span class="badge ${proposedTone}">${escapeHtml(item.payload.proposedState)}</span>
          ${snoozeBadge}
        </div>
      </td>
      <td class="mono">${escapeHtml(item.payload.dueAt ? formatTimestamp(item.payload.dueAt) : "Not set")}</td>
      <td>
        <div class="inline-links">
          ${item.gmailUrl ? `<a class="inline-link" href="${item.gmailUrl}" target="_blank" rel="noreferrer">Open Gmail</a>` : ""}
          ${item.notionUrl ? `<a class="inline-link" href="${item.notionUrl}" target="_blank" rel="noreferrer">Open Notion</a>` : ""}
        </div>
      </td>
      <td>
        <div class="compact-actions">
          <button type="button" data-decision-id="${item.decisionId}" data-action="approve">Approve</button>
          <button class="reject" type="button" data-decision-id="${item.decisionId}" data-action="reject">Reject</button>
          <button class="warn" type="button" data-decision-id="${item.decisionId}" data-action="snooze">Snooze</button>
        </div>
      </td>
    </tr>
  `;
}

function renderInlineDiffList(diff: QueueSnapshot["decisions"][number]["payload"]["diff"]): string {
  if (diff.length === 0) {
    return `<span class="meta">No structured delta.</span>`;
  }

  const visible = diff.slice(0, 2);
  const overflow = diff.length - visible.length;

  return `
    <div class="field-list">
      ${visible
        .map(
          (change) => `
            <div class="field-row">
              <span class="field-name">${escapeHtml(change.field)}</span>
              <div class="field-change">
                <span class="from">${escapeHtml(change.from ?? "Empty")}</span>
                <span class="arrow">-&gt;</span>
                <span class="to">${escapeHtml(change.to ?? "Empty")}</span>
              </div>
            </div>
          `,
        )
        .join("")}
      ${overflow > 0 ? `<span class="meta">+${overflow} more</span>` : ""}
    </div>
  `;
}

function renderRuns(queue: QueueSnapshot): string {
  if (queue.latestRuns.length === 0) {
    return `<div class="empty">No job runs.</div>`;
  }

  return `
    <div class="runs-layout">
      <article class="runs-card">
        <div class="trend-heading">
          <span class="chart-label">Recent cadence</span>
          <span class="chart-value">${queue.latestRuns.length}</span>
          <span class="chart-note">logged runs</span>
        </div>
        ${renderRunSpark(queue.latestRuns)}
        ${renderTrendStats(summarizeRuns(queue.latestRuns))}
      </article>
      <div class="table-wrap">
        <table class="runs-table">
          <thead>
            <tr>
              <th>Job</th>
              <th>Status</th>
              <th>Started</th>
              <th>Finished</th>
            </tr>
          </thead>
          <tbody>
            ${queue.latestRuns
              .map(
                (run) => `
                  <tr>
                    <td>${escapeHtml(run.jobName)}</td>
                    <td><span class="badge ${badgeTone(run.status)}">${escapeHtml(run.status)}</span></td>
                    <td>${escapeHtml(formatTimestamp(run.startedAt))}</td>
                    <td>${escapeHtml(run.finishedAt ? formatTimestamp(run.finishedAt) : "running")}</td>
                  </tr>
                `,
              )
              .join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function summarizeRuns(runs: QueueSnapshot["latestRuns"]): MetricSegment[] {
  return [
    { label: "OK", value: runs.filter((run) => run.status === "success").length, tone: "ok" },
    { label: "Warn", value: runs.filter((run) => run.status === "warning").length, tone: "warn" },
    { label: "Err", value: runs.filter((run) => run.status === "error").length, tone: "danger" },
    { label: "Run", value: runs.filter((run) => run.status === "running").length, tone: "pending" },
  ];
}

function summarizeConfidence(decisions: QueueSnapshot["decisions"]): MetricSegment[] {
  return [
    { label: "High", value: decisions.filter((item) => item.payload.confidence >= 0.8).length, tone: "ok" },
    {
      label: "Mid",
      value: decisions.filter((item) => item.payload.confidence >= 0.6 && item.payload.confidence < 0.8).length,
      tone: "pending",
    },
    { label: "Low", value: decisions.filter((item) => item.payload.confidence < 0.6).length, tone: "danger" },
  ];
}

function summarizeDue(decisions: QueueSnapshot["decisions"]): MetricSegment[] {
  const now = Date.now();
  const oneDay = 24 * 60 * 60 * 1000;
  const threeDays = 3 * oneDay;

  let nowCount = 0;
  let soonCount = 0;
  let laterCount = 0;
  let unsetCount = 0;

  for (const decision of decisions) {
    if (!decision.payload.dueAt) {
      unsetCount += 1;
      continue;
    }

    const dueAt = new Date(decision.payload.dueAt).getTime();
    if (Number.isNaN(dueAt) || dueAt <= now + oneDay) {
      nowCount += 1;
      continue;
    }
    if (dueAt <= now + threeDays) {
      soonCount += 1;
      continue;
    }
    laterCount += 1;
  }

  return [
    { label: "Now", value: nowCount, tone: "danger" },
    { label: "Soon", value: soonCount, tone: "warn" },
    { label: "Later", value: laterCount, tone: "ok" },
    { label: "Unset", value: unsetCount, tone: "pending" },
  ];
}

function sparkHeightForStatus(status: QueueSnapshot["latestRuns"][number]["status"]): number {
  if (status === "success") {
    return 30;
  }
  if (status === "warning") {
    return 22;
  }
  if (status === "error") {
    return 46;
  }
  return 38;
}

function badgeTone(value: string): Tone {
  if (value === "success" || value === "approved" || value === "state/reference") {
    return "ok";
  }
  if (
    value === "warning" ||
    value === "state/waiting" ||
    value === "triage/new" ||
    value === "triage/pending-review"
  ) {
    return "warn";
  }
  if (value === "error" || value === "rejected" || value === "state/ignored") {
    return "danger";
  }
  return "pending";
}

function formatTimestamp(value: string): string {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.valueOf())) {
    return value;
  }

  return timestamp.toLocaleString("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
