import fs from "node:fs";
import path from "node:path";

import { DatabaseSync } from "node:sqlite";

import {
  DecisionCacheEntry,
  DecisionProposal,
  JobName,
  JobResult,
  JobRunRecord,
  OAuthTokenRecord,
  QueueSnapshot,
  SourceType,
} from "./types";
import { nowIso } from "./lib/time";

export class LocalStore {
  private readonly db: DatabaseSync;

  constructor(sqlitePath: string) {
    fs.mkdirSync(path.dirname(sqlitePath), { recursive: true });
    this.db = new DatabaseSync(sqlitePath);
    this.db.exec("PRAGMA journal_mode = WAL;");
    this.db.exec("PRAGMA busy_timeout = 5000;");
    this.migrate();
  }

  private migrate(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS oauth_tokens (
        provider TEXT PRIMARY KEY,
        token_json TEXT NOT NULL,
        email TEXT,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS sync_state (
        provider TEXT NOT NULL,
        state_key TEXT NOT NULL,
        state_value TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (provider, state_key)
      );

      CREATE TABLE IF NOT EXISTS source_cache (
        provider TEXT NOT NULL,
        record_type TEXT NOT NULL,
        external_id TEXT NOT NULL,
        hash TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (provider, record_type, external_id)
      );

      CREATE TABLE IF NOT EXISTS decisions_cache (
        decision_id TEXT PRIMARY KEY,
        notion_page_id TEXT,
        source_type TEXT NOT NULL,
        source_external_id TEXT NOT NULL,
        status TEXT NOT NULL,
        title TEXT NOT NULL,
        gmail_url TEXT,
        notion_url TEXT,
        read_gate_blocked INTEGER NOT NULL DEFAULT 0,
        payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS job_runs (
        id TEXT PRIMARY KEY,
        job_name TEXT NOT NULL,
        status TEXT NOT NULL,
        details_json TEXT NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT
      );

      CREATE TABLE IF NOT EXISTS suppression_hints (
        suppression_key TEXT PRIMARY KEY,
        reason TEXT NOT NULL,
        created_at TEXT NOT NULL
      );
    `);
  }

  close(): void {
    this.db.close();
  }

  getOAuthToken(provider: string): OAuthTokenRecord | null {
    const row = this.db
      .prepare("SELECT provider, token_json, email, updated_at FROM oauth_tokens WHERE provider = ?")
      .get(provider) as OAuthTokenRecord | undefined;
    return row ?? null;
  }

  setOAuthToken(provider: string, tokenJson: string, email: string | null): void {
    const timestamp = nowIso();
    this.db
      .prepare(
        `
          INSERT INTO oauth_tokens (provider, token_json, email, updated_at)
          VALUES (@provider, @token_json, @email, @updated_at)
          ON CONFLICT(provider) DO UPDATE SET
            token_json = excluded.token_json,
            email = excluded.email,
            updated_at = excluded.updated_at
        `,
      )
      .run({
        provider,
        token_json: tokenJson,
        email,
        updated_at: timestamp,
      });
  }

  getSyncState(provider: string, key: string): string | null {
    const row = this.db
      .prepare("SELECT state_value FROM sync_state WHERE provider = ? AND state_key = ?")
      .get(provider, key) as { state_value: string } | undefined;
    return row?.state_value ?? null;
  }

  setSyncState(provider: string, key: string, value: string): void {
    this.db
      .prepare(
        `
          INSERT INTO sync_state (provider, state_key, state_value, updated_at)
          VALUES (@provider, @state_key, @state_value, @updated_at)
          ON CONFLICT(provider, state_key) DO UPDATE SET
            state_value = excluded.state_value,
            updated_at = excluded.updated_at
        `,
      )
      .run({
        provider,
        state_key: key,
        state_value: value,
        updated_at: nowIso(),
      });
  }

  upsertSourceCache(provider: string, recordType: string, externalId: string, hash: string, payload: unknown): void {
    this.db
      .prepare(
        `
          INSERT INTO source_cache (provider, record_type, external_id, hash, payload_json, updated_at)
          VALUES (@provider, @record_type, @external_id, @hash, @payload_json, @updated_at)
          ON CONFLICT(provider, record_type, external_id) DO UPDATE SET
            hash = excluded.hash,
            payload_json = excluded.payload_json,
            updated_at = excluded.updated_at
        `,
      )
      .run({
        provider,
        record_type: recordType,
        external_id: externalId,
        hash,
        payload_json: JSON.stringify(payload),
        updated_at: nowIso(),
      });
  }

  getSourceCache<T>(provider: string, recordType: string, externalId: string): T | null {
    const row = this.db
      .prepare(
        "SELECT payload_json FROM source_cache WHERE provider = ? AND record_type = ? AND external_id = ?",
      )
      .get(provider, recordType, externalId) as { payload_json: string } | undefined;
    return row ? (JSON.parse(row.payload_json) as T) : null;
  }

  listSourceCache<T>(provider: string, recordType: string): T[] {
    const rows = this.db
      .prepare(
        `
          SELECT payload_json
          FROM source_cache
          WHERE provider = ? AND record_type = ?
          ORDER BY updated_at DESC
        `,
      )
      .all(provider, recordType) as Array<{ payload_json: string }>;
    return rows.map((row) => JSON.parse(row.payload_json) as T);
  }

  startJobRun(jobName: JobName): string {
    const id = cryptoRandomId();
    this.db
      .prepare(
        `
          INSERT INTO job_runs (id, job_name, status, details_json, started_at, finished_at)
          VALUES (?, ?, 'running', '{}', ?, NULL)
        `,
      )
      .run(id, jobName, nowIso());
    return id;
  }

  finishJobRun(id: string, result: JobResult): void {
    this.db
      .prepare(
        `
          UPDATE job_runs
          SET status = @status,
              details_json = @details_json,
              finished_at = @finished_at
          WHERE id = @id
        `,
      )
      .run({
        id,
        status: result.status,
        details_json: JSON.stringify(result),
        finished_at: result.finishedAt,
      });
  }

  listRecentJobRuns(limit = 12): JobRunRecord[] {
    return this.db
      .prepare(
        `
          SELECT id, job_name as jobName, status, details_json as detailsJson, started_at as startedAt, finished_at as finishedAt
          FROM job_runs
          ORDER BY started_at DESC
          LIMIT ?
        `,
      )
      .all(limit) as unknown as JobRunRecord[];
  }

  upsertDecision(entry: {
    decisionId: string;
    notionPageId?: string | null;
    sourceType: SourceType;
    sourceExternalId: string;
    status: string;
    title: string;
    gmailUrl?: string | null;
    notionUrl?: string | null;
    readGateBlocked: boolean;
    payload: DecisionProposal;
  }): void {
    const timestamp = nowIso();
    this.db
      .prepare(
        `
          INSERT INTO decisions_cache (
            decision_id, notion_page_id, source_type, source_external_id, status, title, gmail_url,
            notion_url, read_gate_blocked, payload_json, created_at, updated_at
          )
          VALUES (
            @decision_id, @notion_page_id, @source_type, @source_external_id, @status, @title, @gmail_url,
            @notion_url, @read_gate_blocked, @payload_json, @created_at, @updated_at
          )
          ON CONFLICT(decision_id) DO UPDATE SET
            notion_page_id = excluded.notion_page_id,
            status = excluded.status,
            title = excluded.title,
            gmail_url = excluded.gmail_url,
            notion_url = excluded.notion_url,
            read_gate_blocked = excluded.read_gate_blocked,
            payload_json = excluded.payload_json,
            updated_at = excluded.updated_at
        `,
      )
      .run({
        decision_id: entry.decisionId,
        notion_page_id: entry.notionPageId ?? null,
        source_type: entry.sourceType,
        source_external_id: entry.sourceExternalId,
        status: entry.status,
        title: entry.title,
        gmail_url: entry.gmailUrl ?? null,
        notion_url: entry.notionUrl ?? null,
        read_gate_blocked: entry.readGateBlocked ? 1 : 0,
        payload_json: JSON.stringify(entry.payload),
        created_at: timestamp,
        updated_at: timestamp,
      });
  }

  getDecision(decisionId: string): DecisionCacheEntry | null {
    const row = this.db
      .prepare(
        `
          SELECT
            decision_id as decisionId,
            notion_page_id as notionPageId,
            source_type as sourceType,
            source_external_id as sourceExternalId,
            status,
            title,
            gmail_url as gmailUrl,
            notion_url as notionUrl,
            read_gate_blocked as readGateBlocked,
            payload_json,
            created_at as createdAt,
            updated_at as updatedAt
          FROM decisions_cache
          WHERE decision_id = ?
        `,
      )
      .get(decisionId) as
      | (Omit<DecisionCacheEntry, "payload" | "readGateBlocked"> & {
          readGateBlocked: number;
          payload_json: string;
        })
      | undefined;

    if (!row) {
      return null;
    }

    return {
      ...row,
      payload: JSON.parse(row.payload_json) as DecisionProposal,
      readGateBlocked: row.readGateBlocked === 1,
    };
  }

  listPendingDecisions(): DecisionCacheEntry[] {
    const rows = this.db
      .prepare(
        `
          SELECT
            decision_id as decisionId,
            notion_page_id as notionPageId,
            source_type as sourceType,
            source_external_id as sourceExternalId,
            status,
            title,
            gmail_url as gmailUrl,
            notion_url as notionUrl,
            read_gate_blocked as readGateBlocked,
            payload_json,
            created_at as createdAt,
            updated_at as updatedAt
          FROM decisions_cache
          WHERE status IN ('pending', 'snoozed')
          ORDER BY updated_at DESC
        `,
      )
      .all() as Array<
      Omit<DecisionCacheEntry, "payload" | "readGateBlocked"> & {
        readGateBlocked: number;
        payload_json: string;
      }
    >;

    return rows.map((row) => ({
      ...row,
      payload: JSON.parse(row.payload_json) as DecisionProposal,
      readGateBlocked: row.readGateBlocked === 1,
    }));
  }

  updateDecisionStatus(decisionId: string, status: string, payload: DecisionProposal, notionUrl?: string | null): void {
    this.db
      .prepare(
        `
          UPDATE decisions_cache
          SET status = @status,
              payload_json = @payload_json,
              notion_url = COALESCE(@notion_url, notion_url),
              read_gate_blocked = @read_gate_blocked,
              updated_at = @updated_at
          WHERE decision_id = @decision_id
        `,
      )
      .run({
        decision_id: decisionId,
        status,
        payload_json: JSON.stringify(payload),
        notion_url: notionUrl ?? null,
        read_gate_blocked: payload.readGateBlocked ? 1 : 0,
        updated_at: nowIso(),
      });
  }

  addSuppressionHint(key: string, reason: string): void {
    this.db
      .prepare(
        `
          INSERT OR REPLACE INTO suppression_hints (suppression_key, reason, created_at)
          VALUES (?, ?, ?)
        `,
      )
      .run(key, reason, nowIso());
  }

  hasSuppressionHint(key: string): boolean {
    const row = this.db
      .prepare("SELECT suppression_key FROM suppression_hints WHERE suppression_key = ?")
      .get(key) as { suppression_key: string } | undefined;
    return Boolean(row);
  }

  queueSnapshot(): QueueSnapshot {
    return {
      decisions: this.listPendingDecisions(),
      latestRuns: this.listRecentJobRuns(),
    };
  }
}

function cryptoRandomId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
