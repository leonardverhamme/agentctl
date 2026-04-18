import { QueueSnapshot } from "../types";

export function renderDashboard(queue: QueueSnapshot): string {
  const decisions = queue.decisions;
  const inboxItems = decisions.filter((item) => item.sourceType === "email");
  const waitingItems = decisions.filter((item) => item.payload.proposedState === "state/waiting");
  const meetingItems = decisions.filter((item) => item.sourceType === "meeting");
  const staleItems = decisions.filter((item) => item.readGateBlocked || item.payload.confidence < 0.6);

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>automation-core</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f3f5ef;
        --surface: rgba(255,255,255,0.82);
        --surface-strong: rgba(255,255,255,0.94);
        --ink: #1d251f;
        --muted: #607168;
        --line: rgba(29,37,31,0.12);
        --accent: #194f3f;
        --accent-soft: rgba(25,79,63,0.12);
        --warn: #9b5a13;
        --danger: #8b2f2b;
        --ok: #316146;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        background:
          radial-gradient(circle at top right, rgba(25,79,63,0.18), transparent 34%),
          linear-gradient(160deg, #f0f3eb 0%, #eef5f1 54%, #f8f7f3 100%);
        color: var(--ink);
      }
      a { color: inherit; }
      .shell {
        max-width: 1400px;
        margin: 0 auto;
        padding: 24px;
      }
      .hero {
        display: grid;
        grid-template-columns: 1.4fr 1fr;
        gap: 16px;
        margin-bottom: 16px;
      }
      .panel {
        background: var(--surface);
        backdrop-filter: blur(10px);
        border: 1px solid var(--line);
        border-radius: 18px;
        box-shadow: 0 20px 40px rgba(22,32,26,0.08);
      }
      .hero-card {
        padding: 20px;
        min-height: 180px;
      }
      .eyebrow {
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-size: 11px;
        color: var(--muted);
        margin-bottom: 12px;
      }
      h1 {
        margin: 0 0 8px 0;
        font-size: 34px;
        line-height: 1;
      }
      .hero p, .meta, .subtle {
        color: var(--muted);
        font-size: 14px;
        line-height: 1.5;
      }
      .metrics {
        display: grid;
        grid-template-columns: repeat(2, minmax(0,1fr));
        gap: 12px;
      }
      .metric {
        padding: 14px;
        border-radius: 14px;
        background: var(--surface-strong);
        border: 1px solid var(--line);
      }
      .metric strong {
        display: block;
        font-size: 26px;
        margin-bottom: 6px;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0,1fr));
        gap: 16px;
      }
      .queue {
        padding: 18px;
      }
      .queue h2 {
        margin: 0 0 12px 0;
        font-size: 18px;
      }
      .queue-list {
        display: grid;
        gap: 10px;
      }
      .item {
        padding: 12px;
        border-radius: 14px;
        border: 1px solid var(--line);
        background: rgba(255,255,255,0.82);
      }
      .item-title {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        align-items: start;
        margin-bottom: 6px;
      }
      .item-title strong {
        font-size: 14px;
        line-height: 1.35;
      }
      .badge {
        border-radius: 999px;
        padding: 3px 8px;
        font-size: 11px;
        line-height: 1;
        border: 1px solid transparent;
        white-space: nowrap;
      }
      .badge.warn { background: rgba(155,90,19,0.12); color: var(--warn); border-color: rgba(155,90,19,0.16); }
      .badge.ok { background: rgba(49,97,70,0.12); color: var(--ok); border-color: rgba(49,97,70,0.16); }
      .badge.pending { background: var(--accent-soft); color: var(--accent); border-color: rgba(25,79,63,0.16); }
      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
      }
      button, .link-button {
        border: 0;
        border-radius: 10px;
        padding: 8px 10px;
        font: inherit;
        font-size: 13px;
        cursor: pointer;
        background: #1b4137;
        color: white;
        text-decoration: none;
      }
      button.secondary, .link-button.secondary {
        background: rgba(29,37,31,0.07);
        color: var(--ink);
      }
      button.warn {
        background: #9b5a13;
      }
      button.reject {
        background: #8b2f2b;
      }
      .runs {
        margin-top: 16px;
        padding: 18px;
      }
      .runs table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
      }
      .runs th, .runs td {
        text-align: left;
        padding: 8px 0;
        border-bottom: 1px solid var(--line);
      }
      .empty {
        padding: 18px;
        border: 1px dashed var(--line);
        border-radius: 14px;
        color: var(--muted);
        font-size: 13px;
      }
      @media (max-width: 980px) {
        .hero, .grid {
          grid-template-columns: 1fr;
        }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <div class="hero">
        <section class="panel hero-card">
          <div class="eyebrow">Local control plane</div>
          <h1>automation-core</h1>
          <p>Gmail and Calendar feed the queue. Notion remains the system of record. Approve or reject proposals here before state moves anywhere else.</p>
          <p class="subtle">Unread inbound mail stays behind the human-read gate unless you explicitly override it.</p>
        </section>
        <section class="panel hero-card">
          <div class="metrics">
            <div class="metric">
              <span class="eyebrow">Pending</span>
              <strong>${decisions.length}</strong>
              <span class="meta">Approval items</span>
            </div>
            <div class="metric">
              <span class="eyebrow">Inbox</span>
              <strong>${inboxItems.length}</strong>
              <span class="meta">Email-driven proposals</span>
            </div>
            <div class="metric">
              <span class="eyebrow">Meetings</span>
              <strong>${meetingItems.length}</strong>
              <span class="meta">Post-meeting wrap items</span>
            </div>
            <div class="metric">
              <span class="eyebrow">Blocked</span>
              <strong>${staleItems.length}</strong>
              <span class="meta">Needs human attention</span>
            </div>
          </div>
        </section>
      </div>

      <div class="grid">
        ${renderQueue("Inbox approval queue", inboxItems)}
        ${renderQueue("Waiting queue", waitingItems)}
        ${renderQueue("Meeting follow-up queue", meetingItems)}
        ${renderQueue("Stale / low-confidence queue", staleItems)}
      </div>

      <section class="panel runs">
        <div class="eyebrow">Daily overview</div>
        <table>
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
                    <td>${run.jobName}</td>
                    <td>${run.status}</td>
                    <td>${run.startedAt}</td>
                    <td>${run.finishedAt ?? "running"}</td>
                  </tr>
                `,
              )
              .join("")}
          </tbody>
        </table>
      </section>
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

function renderQueue(title: string, items: QueueSnapshot["decisions"]): string {
  if (items.length === 0) {
    return `
      <section class="panel queue">
        <h2>${title}</h2>
        <div class="empty">Nothing queued here.</div>
      </section>
    `;
  }

  return `
    <section class="panel queue">
      <h2>${title}</h2>
      <div class="queue-list">
        ${items
          .map(
            (item) => `
              <article class="item">
                <div class="item-title">
                  <strong>${escapeHtml(item.title)}</strong>
                  <span class="badge ${item.readGateBlocked ? "warn" : "pending"}">${item.readGateBlocked ? "Read gate" : item.payload.proposedState}</span>
                </div>
                <div class="meta">${escapeHtml(item.payload.reviewReason)}</div>
                <div class="meta">Confidence: ${item.payload.confidence.toFixed(2)}</div>
                <div class="meta">Summary: ${escapeHtml(item.payload.summary)}</div>
                <div class="actions">
                  <button data-decision-id="${item.decisionId}" data-action="approve">Approve</button>
                  <button class="reject" data-decision-id="${item.decisionId}" data-action="reject">Reject</button>
                  <button class="warn" data-decision-id="${item.decisionId}" data-action="snooze">Snooze</button>
                  ${item.gmailUrl ? `<a class="link-button secondary" href="${item.gmailUrl}" target="_blank" rel="noreferrer">Open Gmail</a>` : ""}
                  ${item.notionUrl ? `<a class="link-button secondary" href="${item.notionUrl}" target="_blank" rel="noreferrer">Open Notion</a>` : ""}
                </div>
              </article>
            `,
          )
          .join("")}
      </div>
    </section>
  `;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
