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
} from "../types";

export interface GitHubAnalyticsPageData {
  filters: AnalyticsFilters;
  summary: AnalyticsSummarySnapshot;
  repositories: GitHubRepositoryRecord[];
  contributors: ContributorRecord[];
  commits: CommitFact[];
  pullRequests: PullRequestFact[];
  reviews: PullRequestReviewFact[];
  issues: IssueFact[];
  releases: ReleaseFact[];
  workflowRuns: WorkflowRunFact[];
  trends: TrendPoint[];
  weeklyBrief: WeeklyEngineeringBrief | null;
  topRepoRollups: RepoRollup[];
}

type TrendMetric = "commits" | "netLoc" | "prsMerged" | "workflowFailures";

export function renderGitHubAnalytics(data: GitHubAnalyticsPageData): string {
  const summary = hydrateSummary(data);
  const weeklyBrief = data.weeklyBrief ?? buildFallbackWeeklyBrief(data, summary);
  const repositories = sortRepositories(data.repositories);
  const contributors = sortContributors(data.contributors);
  const commits = sortCommits(data.commits);
  const trends = data.trends.length > 0 ? data.trends : buildEmptyTrends(summary);

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="icon" href="/favicon.ico" sizes="any" />
    <title>GitHub analytics</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f5f8fc;
        --surface: #ffffff;
        --surface-2: #f8fbff;
        --surface-3: #eef5ff;
        --ink: #10223f;
        --muted: #5b6b82;
        --line: #d7e3f2;
        --accent: #1d4ed8;
        --accent-strong: #1e40af;
        --accent-soft: #e6efff;
        --ok: #1d4ed8;
        --warn: #8a6112;
        --danger: #9f2e2e;
        --ok-soft: #edf4ff;
        --warn-soft: #fff3d8;
        --danger-soft: #fde8e8;
        --mono: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
      }

      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        color: var(--ink);
        background:
          linear-gradient(180deg, rgba(29, 78, 216, 0.06), transparent 140px),
          linear-gradient(135deg, rgba(230, 239, 255, 0.68), transparent 58%),
          var(--bg);
      }
      a { color: inherit; }
      :focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

      .shell { max-width: 1580px; margin: 0 auto; padding: 12px; }
      .panel { border: 1px solid var(--line); border-radius: 8px; background: var(--surface); box-shadow: 0 1px 2px rgba(16, 34, 63, 0.04); }
      .header, .filters, .section { margin-bottom: 10px; }
      .header { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); gap: 10px; padding: 10px 12px; }
      .filters, .section { padding: 10px 12px; }
      .title-block { display: grid; gap: 4px; }
      .eyebrow, .section-kicker, .field-label, .metric-label, .table-kicker, .chart-label { color: var(--muted); font-size: 9px; letter-spacing: 0.1em; text-transform: uppercase; }
      h1, h2 { margin: 0; }
      h1 { font-size: 20px; line-height: 1.1; }
      h2 { font-size: 13px; line-height: 1.2; }
      .headline, .meta, .subtle, .empty, .chart-note { color: var(--muted); font-size: 11px; line-height: 1.35; }
      .app-nav, .pill-row, .chart-foot, .table-links, .check-row { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
      .nav-link, .pill, .chip, .stat-chip { display: inline-flex; align-items: center; gap: 5px; padding: 3px 7px; border: 1px solid var(--line); border-radius: 999px; background: var(--surface-2); white-space: nowrap; font-size: 10px; line-height: 1; text-decoration: none; }
      .nav-link.active { color: var(--accent); background: #fff; border-color: rgba(29, 78, 216, 0.24); }
      .pill.ok, .chip.ok { color: var(--ok); background: var(--ok-soft); }
      .pill.pending, .chip.pending { color: var(--accent); background: var(--accent-soft); }
      .pill.warn, .chip.warn { color: var(--warn); background: var(--warn-soft); }
      .pill.danger, .chip.danger { color: var(--danger); background: var(--danger-soft); }
      .topline { display: grid; justify-items: end; gap: 8px; align-content: center; }
      .kpi-grid, .trend-grid, .weekly-grid { display: grid; gap: 8px; }
      .kpi-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); }
      .trend-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .weekly-grid { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(280px, 0.9fr); }
      .kpi, .trend-card, .weekly-card { display: grid; gap: 8px; padding: 8px; border: 1px solid var(--line); border-radius: 6px; background: linear-gradient(180deg, var(--surface), var(--surface-2)); }
      .kpi strong, .trend-value { font-size: 20px; line-height: 1; letter-spacing: -0.03em; }
      .chart { display: grid; gap: 4px; min-height: 76px; padding: 4px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface-3); }
      .bars { display: grid; grid-auto-flow: column; gap: 3px; align-items: end; min-height: 56px; }
      .bar { min-width: 8px; border-radius: 3px 3px 2px 2px; background: var(--accent-soft); border: 1px solid rgba(29, 78, 216, 0.14); }
      .bar.warn { background: var(--warn-soft); border-color: rgba(138, 97, 18, 0.16); }
      .bar.danger { background: var(--danger-soft); border-color: rgba(159, 46, 46, 0.16); }
      .table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 6px; background: var(--surface-2); }
      table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 11px; }
      th, td { padding: 7px 8px; vertical-align: top; text-align: left; border-top: 1px solid var(--line); }
      thead th { border-top: 0; background: var(--surface-3); color: var(--muted); font-size: 9px; letter-spacing: 0.08em; text-transform: uppercase; }
      tbody tr:nth-child(even) { background: rgba(239, 245, 255, 0.5); }
      .mono { font-family: var(--mono); }
      .row-title { display: grid; gap: 2px; }
      .row-title strong { font-size: 12px; line-height: 1.35; }
      .filter-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; width: 100%; }
      .filter { display: grid; gap: 4px; }
      .filter input, .filter select { width: 100%; height: 32px; padding: 0 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); color: var(--ink); font: inherit; font-size: 11px; }
      .check { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; color: var(--ink); }
      .check input { width: 14px; height: 14px; margin: 0; }
      .actions { display: flex; gap: 6px; align-items: center; margin-left: auto; }
      .button { height: 32px; padding: 0 10px; border: 1px solid transparent; border-radius: 6px; background: var(--accent); color: #fff; font: inherit; font-size: 11px; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; }
      .button.secondary { background: #fff; color: var(--accent); border-color: rgba(29, 78, 216, 0.2); }
      .empty { padding: 12px; border: 1px dashed var(--line); border-radius: 6px; }
      .bullet-list { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; }
      .bullet-list li { display: flex; justify-content: space-between; gap: 10px; padding: 6px 8px; border: 1px solid var(--line); border-radius: 6px; background: #fff; }
      .bullet-list strong { font-size: 11px; }
      .bullet-list span { color: var(--muted); font-size: 11px; text-align: right; }

      @media (max-width: 1260px) {
        .header, .weekly-grid, .trend-grid, .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      }
      @media (max-width: 880px) {
        .header, .weekly-grid { grid-template-columns: 1fr; }
        .topline { justify-items: start; }
      }
      @media (max-width: 760px) {
        .shell { padding: 10px; }
        .filter-grid, .trend-grid, .kpi-grid { grid-template-columns: 1fr; }
        .actions { width: 100%; margin-left: 0; justify-content: flex-start; }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <header class="panel header">
        <div class="title-block">
          <div class="eyebrow">GitHub analytics</div>
          <h1>Operator dashboard</h1>
          <div class="app-nav" aria-label="Surfaces">
            <a class="nav-link" href="/">Operator console</a>
            <a class="nav-link active" href="/analytics">GitHub analytics</a>
          </div>
        </div>
        <div class="topline">
          <div class="pill-row">
            <span class="pill ok">${summary.totals.activeRepos} repos</span>
            <span class="pill pending">${summary.totals.activeContributors} contributors</span>
            <span class="pill warn">${summary.totals.workflowFailures} failures</span>
          </div>
          <div class="pill-row">
            <span class="stat-chip mono">${formatDate(summary.generatedAt)}</span>
            <span class="stat-chip mono">${summary.totals.commits} commits</span>
            <span class="stat-chip mono">${summary.totals.netLoc >= 0 ? "+" : ""}${summary.totals.netLoc} net LOC</span>
          </div>
        </div>
      </header>

      <form class="panel filters" method="get" action="/analytics">
        <div class="filter-grid" role="group" aria-label="Analytics filters">
          ${renderTextFilter("Owner", "owner", data.filters.owner)}
          ${renderTextFilter("Repo", "repository", data.filters.repository)}
          ${renderTextFilter("Contributor", "contributor", data.filters.contributor)}
          ${renderTextFilter("Metric", "metricFamily", data.filters.metricFamily)}
          ${renderDateFilter("From", "dateFrom", data.filters.dateFrom)}
          ${renderDateFilter("To", "dateTo", data.filters.dateTo)}
          ${renderGrainFilter("Grain", "grain", data.filters.grain ?? "day")}
          <div class="filter">
            <span class="field-label">Scope</span>
            <div class="check-row">
              <label class="check"><input type="checkbox" name="includeBots" value="true" ${checked(data.filters.includeBots)} /> bots</label>
              <label class="check"><input type="checkbox" name="includeArchived" value="true" ${checked(data.filters.includeArchived)} /> archived</label>
              <label class="check"><input type="checkbox" name="includeForks" value="true" ${checked(data.filters.includeForks)} /> forks</label>
            </div>
          </div>
        </div>
        <div class="actions">
          <a class="button secondary" href="/analytics">Reset</a>
          <button type="submit" class="button">Apply</button>
        </div>
      </form>

      <main>
        <section class="panel section">
          <div class="section-kicker">Overview</div>
          <h2>Overview</h2>
          <div class="kpi-grid">
            ${renderKpi("Repos", summary.totals.activeRepos, "active")}
            ${renderKpi("People", summary.totals.activeContributors, "active")}
            ${renderKpi("Commits", summary.totals.commits, "authored")}
            ${renderKpi("Net LOC", summary.totals.netLoc, "added - deleted")}
            ${renderKpi("PRs", summary.totals.prsMerged, "merged")}
            ${renderKpi("Health", summary.totals.workflowFailures, "failures")}
          </div>
          <div class="pill-row" style="margin-top:8px;">
            ${summary.trendHighlights
              .slice(0, 3)
              .map((item) => `<span class="chip pending">${escapeHtml(item.label)} ${escapeHtml(item.value)}</span>`)
              .join("")}
          </div>
        </section>

        <section class="panel section">
          <div class="section-kicker">Trends</div>
          <h2>Trend overview</h2>
          <div class="trend-grid">
            ${renderTrendCard("Commits", summary.totals.commits, trends, "commits", "bucketed activity")}
            ${renderTrendCard("Net LOC", summary.totals.netLoc, trends, "netLoc", "growth minus churn")}
          </div>
        </section>

        <section class="panel section">
          <div class="section-kicker">Repositories</div>
          <h2>Repo table</h2>
          ${renderRepositoryTable(repositories, summary)}
        </section>

        <section class="panel section">
          <div class="section-kicker">Contributors</div>
          <h2>People table</h2>
          ${renderContributorTable(contributors, summary)}
        </section>

        <section class="panel section">
          <div class="section-kicker">Commits</div>
          <h2>Raw fact explorer</h2>
          ${renderCommitTable(commits)}
        </section>

        <section class="panel section">
          <div class="section-kicker">Weekly</div>
          <h2>Weekly brief</h2>
          ${renderWeeklyBrief(weeklyBrief)}
        </section>
      </main>
    </div>
  </body>
</html>`;
}

function renderKpi(label: string, value: number, meta: string): string {
  return `
    <article class="kpi">
      <span class="metric-label">${escapeHtml(label)}</span>
      <strong>${formatInteger(value)}</strong>
      <span class="subtle">${escapeHtml(meta)}</span>
    </article>
  `;
}

function renderTrendCard(title: string, value: number, trends: TrendPoint[], metric: TrendMetric, note: string): string {
  const max = Math.max(...trends.map((trend) => Math.abs(trend[metric])), 1);
  const bars = trends
    .map((trend) => {
      const raw = trend[metric];
      const height = Math.max(6, Math.round((Math.abs(raw) / max) * 54));
      const tone = metric === "workflowFailures" ? "danger" : metric === "netLoc" && raw < 0 ? "warn" : "";
      return `<span class="bar ${tone}" style="height:${height}px" title="${escapeHtml(`${trend.bucketStart}: ${raw}`)}"></span>`;
    })
    .join("");

  const buckets = trends
    .slice(-6)
    .map((trend) => `<span class="chart-note">${escapeHtml(shortBucket(trend.bucketStart))}</span>`)
    .join("");

  return `
    <article class="trend-card">
      <div class="row-title">
        <span class="chart-label">${escapeHtml(title)}</span>
        <span class="trend-value">${formatInteger(value)}</span>
        <span class="chart-note">${escapeHtml(note)}</span>
      </div>
      <div class="chart" aria-label="${escapeHtml(title)} trend">
        <div class="bars">${bars}</div>
        <div class="chart-foot">${buckets}</div>
      </div>
    </article>
  `;
}

function renderRepositoryTable(rows: GitHubRepositoryRecord[], summary: AnalyticsSummarySnapshot): string {
  if (rows.length === 0) {
    return `<div class="empty">No repository snapshots yet.</div>`;
  }

  const highlight = new Map(summary.biggestRepos.map((item) => [item.fullName, item]));

  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Repo</th>
            <th>Owner</th>
            <th>Commits</th>
            <th>Net LOC</th>
            <th>PRs</th>
            <th>Issues</th>
            <th>Releases</th>
            <th>Health</th>
          </tr>
        </thead>
        <tbody>
          ${rows
            .map((row) => {
              const top = highlight.get(row.fullName);
              const netLoc = row.additions - row.deletions;
              return `
                <tr>
                  <td>
                    <div class="row-title">
                      <strong>${escapeHtml(row.fullName)}</strong>
                      <span class="meta">${escapeHtml(row.description || "No description")}</span>
                    </div>
                  </td>
                  <td>
                    <div class="row-title">
                      <strong>${escapeHtml(row.owner)}</strong>
                      <span class="meta">${escapeHtml(row.language || "Unknown")} · ${escapeHtml(row.visibility)}</span>
                    </div>
                  </td>
                  <td class="mono">${formatInteger(row.commitCount)}</td>
                  <td class="mono">${netLoc >= 0 ? "+" : ""}${formatInteger(netLoc)}</td>
                  <td class="mono">${formatInteger(row.openPrs)} / ${formatInteger(row.mergedPrs)}</td>
                  <td class="mono">${formatInteger(row.openIssues)}</td>
                  <td class="mono">${formatInteger(row.releases)}</td>
                  <td>
                    <div class="row-title">
                      <span class="chip ${row.workflowFailures > 0 ? "warn" : "ok"}">${formatInteger(row.workflowFailures)} failures</span>
                      <span class="meta">${top ? `top ${formatInteger(top.commits)} commits` : row.latestActivityAt ? formatDate(row.latestActivityAt) : "No activity"}</span>
                      <a class="nav-link" href="${escapeHtml(row.htmlUrl)}" target="_blank" rel="noreferrer">Open</a>
                    </div>
                  </td>
                </tr>
              `;
            })
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderContributorTable(rows: ContributorRecord[], summary: AnalyticsSummarySnapshot): string {
  if (rows.length === 0) {
    return `<div class="empty">No contributor snapshots yet.</div>`;
  }

  const highlight = new Map(summary.biggestContributors.map((item) => [item.contributor, item]));

  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Contributor</th>
            <th>Repos</th>
            <th>Commits</th>
            <th>Net LOC</th>
            <th>PRs</th>
            <th>Reviews</th>
            <th>Activity</th>
          </tr>
        </thead>
        <tbody>
          ${rows
            .map((row) => {
              const top = highlight.get(row.displayName);
              const netLoc = row.additions - row.deletions;
              return `
                <tr>
                  <td>
                    <div class="row-title">
                      <strong>${escapeHtml(row.displayName)}</strong>
                      <span class="meta mono">${escapeHtml(row.canonicalLogin || "unmapped")}</span>
                    </div>
                  </td>
                  <td class="mono">${formatInteger(row.repoCount)}</td>
                  <td class="mono">${formatInteger(row.commitCount)}</td>
                  <td class="mono">${netLoc >= 0 ? "+" : ""}${formatInteger(netLoc)}</td>
                  <td class="mono">${formatInteger(row.prsOpened)} / ${formatInteger(row.prsMerged)}</td>
                  <td class="mono">${formatInteger(row.reviewsSubmitted)}</td>
                  <td>
                    <div class="row-title">
                      <span class="chip ${row.workflowRuns > 0 ? "pending" : "ok"}">${formatInteger(row.workflowRuns)} runs</span>
                      <span class="meta">${top ? `top ${formatInteger(top.commits)} commits` : row.latestActivityAt ? formatDate(row.latestActivityAt) : "No activity"}</span>
                    </div>
                  </td>
                </tr>
              `;
            })
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderCommitTable(rows: CommitFact[]): string {
  if (rows.length === 0) {
    return `<div class="empty">No commit facts yet.</div>`;
  }

  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>SHA</th>
            <th>Repo</th>
            <th>Author</th>
            <th>Time</th>
            <th>Delta</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          ${rows
            .map(
              (row) => `
                <tr>
                  <td class="mono">
                    <div class="row-title">
                      <strong>${escapeHtml(row.sha.slice(0, 8))}</strong>
                      <span class="meta">${escapeHtml(row.isMerge ? "merge" : "commit")}</span>
                    </div>
                  </td>
                  <td>
                    <div class="row-title">
                      <strong>${escapeHtml(row.repoId)}</strong>
                      <span class="meta">${escapeHtml(row.refNames.slice(0, 2).join(", ") || "default")}</span>
                    </div>
                  </td>
                  <td>
                    <div class="row-title">
                      <strong>${escapeHtml(row.authorName || row.authorLogin || "Unknown")}</strong>
                      <span class="meta mono">${escapeHtml(row.authorEmail || "no email")}</span>
                    </div>
                  </td>
                  <td class="mono">${escapeHtml(formatDate(row.authoredAt))}</td>
                  <td class="mono">${row.additions >= 0 ? "+" : ""}${formatInteger(row.additions)} / -${formatInteger(row.deletions)} / ${formatInteger(row.changedFiles)} files</td>
                  <td>
                    <div class="row-title">
                      <span>${escapeHtml(row.subject)}</span>
                      <span class="table-links">
                        <span class="chip ${row.authorContributorId ? "ok" : "warn"}">${row.authorContributorId ? "linked" : "unmapped"}</span>
                        <a class="nav-link" href="${escapeHtml(row.htmlUrl)}" target="_blank" rel="noreferrer">Open</a>
                      </span>
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

function renderWeeklyBrief(weeklyBrief: WeeklyEngineeringBrief | null): string {
  if (!weeklyBrief) {
    return `<div class="empty">No weekly brief yet.</div>`;
  }

  return `
    <div class="weekly-grid">
      <article class="weekly-card">
        <div class="row-title">
          <span class="section-kicker">Headline</span>
          <strong>${escapeHtml(weeklyBrief.headline)}</strong>
          <span class="meta">${escapeHtml(weeklyBrief.summary)}</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>Repo</th>
              <th>Commits</th>
              <th>Net LOC</th>
            </tr>
          </thead>
          <tbody>
            ${weeklyBrief.topRepositories
              .map(
                (repo) => `
                  <tr>
                    <td>${escapeHtml(repo.fullName)}</td>
                    <td class="mono">${formatInteger(repo.commits)}</td>
                    <td class="mono">${repo.netLoc >= 0 ? "+" : ""}${formatInteger(repo.netLoc)}</td>
                  </tr>
                `,
              )
              .join("")}
          </tbody>
        </table>
      </article>

      <article class="weekly-card">
        <div class="table-kicker">Top contributors</div>
        <table>
          <thead>
            <tr>
              <th>Contributor</th>
              <th>Commits</th>
              <th>Net LOC</th>
            </tr>
          </thead>
          <tbody>
            ${weeklyBrief.topContributors
              .map(
                (contributor) => `
                  <tr>
                    <td>${escapeHtml(contributor.contributor)}</td>
                    <td class="mono">${formatInteger(contributor.commits)}</td>
                    <td class="mono">${contributor.netLoc >= 0 ? "+" : ""}${formatInteger(contributor.netLoc)}</td>
                  </tr>
                `,
              )
              .join("")}
          </tbody>
        </table>
      </article>

      <article class="weekly-card">
        <div class="table-kicker">Alerts</div>
        ${weeklyBrief.workflowAlerts.length === 0
          ? `<div class="empty">No workflow alerts.</div>`
          : `
            <ul class="bullet-list">
              ${weeklyBrief.workflowAlerts
                .map(
                  (alert) => `
                    <li>
                      <strong>${escapeHtml(alert.fullName)}</strong>
                      <span>${formatInteger(alert.failures)} failures</span>
                    </li>
                  `,
                )
                .join("")}
            </ul>
          `}
      </article>
    </div>
  `;
}

function renderTextFilter(label: string, name: string, value: string | null | undefined): string {
  return `
    <label class="filter">
      <span class="field-label">${escapeHtml(label)}</span>
      <input type="text" name="${name}" value="${escapeHtml(value ?? "")}" />
    </label>
  `;
}

function renderDateFilter(label: string, name: string, value: string | null | undefined): string {
  return `
    <label class="filter">
      <span class="field-label">${escapeHtml(label)}</span>
      <input type="date" name="${name}" value="${escapeHtml((value ?? "").slice(0, 10))}" />
    </label>
  `;
}

function renderGrainFilter(label: string, name: string, value: string): string {
  return `
    <label class="filter">
      <span class="field-label">${escapeHtml(label)}</span>
      <select name="${name}">
        <option value="day" ${value === "day" ? "selected" : ""}>day</option>
        <option value="week" ${value === "week" ? "selected" : ""}>week</option>
        <option value="month" ${value === "month" ? "selected" : ""}>month</option>
      </select>
    </label>
  `;
}

function hydrateSummary(data: GitHubAnalyticsPageData): AnalyticsSummarySnapshot {
  if (data.summary.totals.activeRepos > 0 || data.repositories.length === 0) {
    return data.summary;
  }

  const activeRepos = data.repositories.filter((repo) => !repo.isArchived && !repo.isFork).length;
  const activeContributors = data.contributors.length;
  const commits = data.repositories.reduce((sum, repo) => sum + repo.commitCount, 0);
  const additions = data.repositories.reduce((sum, repo) => sum + repo.additions, 0);
  const deletions = data.repositories.reduce((sum, repo) => sum + repo.deletions, 0);

  return {
    ...data.summary,
    generatedAt: data.summary.generatedAt || new Date().toISOString(),
    totals: {
      activeRepos,
      activeContributors,
      commits,
      additions,
      deletions,
      netLoc: additions - deletions,
      prsOpened: data.repositories.reduce((sum, repo) => sum + repo.openPrs, 0),
      prsMerged: data.repositories.reduce((sum, repo) => sum + repo.mergedPrs, 0),
      reviewsSubmitted: data.contributors.reduce((sum, contributor) => sum + contributor.reviewsSubmitted, 0),
      issuesOpened: data.repositories.reduce((sum, repo) => sum + repo.openIssues, 0),
      issuesClosed: 0,
      releases: data.repositories.reduce((sum, repo) => sum + repo.releases, 0),
      workflowRuns: data.contributors.reduce((sum, contributor) => sum + contributor.workflowRuns, 0),
      workflowFailures: data.repositories.reduce((sum, repo) => sum + repo.workflowFailures, 0),
    },
    biggestRepos:
      data.summary.biggestRepos.length > 0
        ? data.summary.biggestRepos
        : sortRepositories(data.repositories)
            .slice(0, 3)
            .map((repo) => ({
              fullName: repo.fullName,
              commits: repo.commitCount,
              netLoc: repo.additions - repo.deletions,
              mergedPrs: repo.mergedPrs,
            })),
    biggestContributors:
      data.summary.biggestContributors.length > 0
        ? data.summary.biggestContributors
        : sortContributors(data.contributors)
            .slice(0, 3)
            .map((contributor) => ({
              contributor: contributor.displayName,
              commits: contributor.commitCount,
              netLoc: contributor.additions - contributor.deletions,
              prsMerged: contributor.prsMerged,
            })),
    trendHighlights:
      data.summary.trendHighlights.length > 0
        ? data.summary.trendHighlights
        : [
            { label: "Active repos", value: formatInteger(activeRepos) },
            { label: "Commits", value: formatInteger(commits) },
            { label: "Net LOC", value: `${additions - deletions >= 0 ? "+" : ""}${formatInteger(additions - deletions)}` },
          ],
  };
}

function buildFallbackWeeklyBrief(
  data: GitHubAnalyticsPageData,
  summary: AnalyticsSummarySnapshot,
): WeeklyEngineeringBrief | null {
  if (data.repositories.length === 0 && data.contributors.length === 0) {
    return null;
  }

  return {
    weekStart: summary.generatedAt.slice(0, 10),
    generatedAt: summary.generatedAt,
    headline: "Working set overview",
    summary: `Review ${summary.totals.activeRepos} repos and ${summary.totals.activeContributors} contributors.`,
    topRepositories: sortRepositories(data.repositories)
      .slice(0, 3)
      .map((repo) => ({
        fullName: repo.fullName,
        commits: repo.commitCount,
        netLoc: repo.additions - repo.deletions,
      })),
    topContributors: sortContributors(data.contributors)
      .slice(0, 3)
      .map((contributor) => ({
        contributor: contributor.displayName,
        commits: contributor.commitCount,
        netLoc: contributor.additions - contributor.deletions,
      })),
    workflowAlerts: sortRepositories(data.repositories)
      .filter((repo) => repo.workflowFailures > 0)
      .slice(0, 3)
      .map((repo) => ({
        fullName: repo.fullName,
        failures: repo.workflowFailures,
      })),
    notionUrl: null,
  };
}

function sortRepositories(rows: GitHubRepositoryRecord[]): GitHubRepositoryRecord[] {
  return [...rows].sort((left, right) => right.commitCount - left.commitCount || left.fullName.localeCompare(right.fullName));
}

function sortContributors(rows: ContributorRecord[]): ContributorRecord[] {
  return [...rows].sort((left, right) => right.commitCount - left.commitCount || left.displayName.localeCompare(right.displayName));
}

function sortCommits(rows: CommitFact[]): CommitFact[] {
  return [...rows].sort((left, right) => right.authoredAt.localeCompare(left.authoredAt) || right.sha.localeCompare(left.sha));
}

function buildEmptyTrends(summary: AnalyticsSummarySnapshot): TrendPoint[] {
  return summary.totals.commits > 0
    ? [
        {
          bucketStart: summary.generatedAt.slice(0, 10),
          commits: summary.totals.commits,
          additions: summary.totals.additions,
          deletions: summary.totals.deletions,
          netLoc: summary.totals.netLoc,
          prsOpened: summary.totals.prsOpened,
          prsMerged: summary.totals.prsMerged,
          reviewsSubmitted: summary.totals.reviewsSubmitted,
          issuesOpened: summary.totals.issuesOpened,
          issuesClosed: summary.totals.issuesClosed,
          releases: summary.totals.releases,
          workflowRuns: summary.totals.workflowRuns,
          workflowFailures: summary.totals.workflowFailures,
        },
      ]
    : [{ bucketStart: "", commits: 0, additions: 0, deletions: 0, netLoc: 0, prsOpened: 0, prsMerged: 0, reviewsSubmitted: 0, issuesOpened: 0, issuesClosed: 0, releases: 0, workflowRuns: 0, workflowFailures: 0 }];
}

function formatInteger(value: number): string {
  return new Intl.NumberFormat("en-GB").format(value);
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) {
    return value;
  }

  return date.toLocaleString("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function shortBucket(value: string): string {
  if (!value) {
    return "now";
  }
  return value.slice(5, 10);
}

function checked(value: boolean | undefined): string {
  return value ? "checked" : "";
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
