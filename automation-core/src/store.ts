import fs from "node:fs";
import path from "node:path";

import postgres, { Sql } from "postgres";

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

const DEFAULT_MIGRATIONS_DIR = path.resolve(process.cwd(), "supabase", "migrations");

type RowValue = string | number | boolean | null | Record<string, unknown> | unknown[];

interface DatabaseRow extends Record<string, RowValue> {}

export class LocalStore {
  private constructor(
    private readonly sql: Sql,
    private readonly migrationsDir: string,
  ) {}

  static async create(databaseUrl: string, migrationsDir = DEFAULT_MIGRATIONS_DIR): Promise<LocalStore> {
    const sql = postgres(databaseUrl, {
      prepare: false,
      max: 10,
      idle_timeout: 5,
      connect_timeout: 30,
    });
    const store = new LocalStore(sql, migrationsDir);
    await store.migrate();
    return store;
  }

  private async migrate(): Promise<void> {
    await this.sql`
      create table if not exists automation_core_schema_migrations (
        filename text primary key,
        applied_at text not null
      )
    `;

    if (!fs.existsSync(this.migrationsDir)) {
      return;
    }

    const files = fs
      .readdirSync(this.migrationsDir, { withFileTypes: true })
      .filter((entry) => entry.isFile() && entry.name.endsWith(".sql"))
      .map((entry) => entry.name)
      .sort();

    for (const filename of files) {
      const applied = await this.sql<{ filename: string }[]>`
        select filename
        from automation_core_schema_migrations
        where filename = ${filename}
        limit 1
      `;
      if (applied.length > 0) {
        continue;
      }

      const migrationSql = fs.readFileSync(path.join(this.migrationsDir, filename), "utf8");
      await this.sql.begin(async (transaction) => {
        await transaction.unsafe(migrationSql);
        await transaction`
          insert into automation_core_schema_migrations (filename, applied_at)
          values (${filename}, ${nowIso()})
        `;
      });
    }
  }

  async close(): Promise<void> {
    await this.sql.end({ timeout: 5 });
  }

  async execute(sqlText: string, values: unknown[] = []): Promise<void> {
    await this.sql.unsafe(sqlText, values as never[]);
  }

  async run(sqlText: string, ...values: unknown[]): Promise<void> {
    await this.execute(sqlText, values);
  }

  async get<T>(sqlText: string, ...values: unknown[]): Promise<T | null> {
    const rows = (await this.sql.unsafe(sqlText, values as never[])) as T[];
    return rows[0] ?? null;
  }

  async all<T>(sqlText: string, ...values: unknown[]): Promise<T[]> {
    return (await this.sql.unsafe(sqlText, values as never[])) as T[];
  }

  async getOAuthToken(provider: string): Promise<OAuthTokenRecord | null> {
    const row = await this.get<DatabaseRow>(
      `
        select provider, token_json, email, updated_at
        from oauth_tokens
        where provider = $1
      `,
      provider,
    );

    if (!row) {
      return null;
    }

    return {
      provider: String(row.provider),
      tokenJson: String(row.token_json),
      email: normalizeNullableText(row.email),
      updatedAt: String(row.updated_at),
    };
  }

  async setOAuthToken(provider: string, tokenJson: string, email: string | null): Promise<void> {
    await this.sql`
      insert into oauth_tokens (provider, token_json, email, updated_at)
      values (${provider}, ${tokenJson}, ${email}, ${nowIso()})
      on conflict (provider) do update set
        token_json = excluded.token_json,
        email = excluded.email,
        updated_at = excluded.updated_at
    `;
  }

  async getSyncState(provider: string, key: string): Promise<string | null> {
    const row = await this.get<DatabaseRow>(
      `
        select state_value
        from sync_state
        where provider = $1 and state_key = $2
      `,
      provider,
      key,
    );
    return row ? String(row.state_value) : null;
  }

  async setSyncState(provider: string, key: string, value: string): Promise<void> {
    await this.sql`
      insert into sync_state (provider, state_key, state_value, updated_at)
      values (${provider}, ${key}, ${value}, ${nowIso()})
      on conflict (provider, state_key) do update set
        state_value = excluded.state_value,
        updated_at = excluded.updated_at
    `;
  }

  async upsertSourceCache(
    provider: string,
    recordType: string,
    externalId: string,
    hash: string,
    payload: unknown,
  ): Promise<void> {
    await this.sql`
      insert into source_cache (provider, record_type, external_id, hash, payload_json, updated_at)
      values (${provider}, ${recordType}, ${externalId}, ${hash}, ${JSON.stringify(payload)}::jsonb, ${nowIso()})
      on conflict (provider, record_type, external_id) do update set
        hash = excluded.hash,
        payload_json = excluded.payload_json,
        updated_at = excluded.updated_at
    `;
  }

  async getSourceCache<T>(provider: string, recordType: string, externalId: string): Promise<T | null> {
    const row = await this.get<DatabaseRow>(
      `
        select payload_json
        from source_cache
        where provider = $1 and record_type = $2 and external_id = $3
      `,
      provider,
      recordType,
      externalId,
    );
    if (!row) {
      return null;
    }
    return parseJsonValue<T>(row.payload_json);
  }

  async listSourceCache<T>(provider: string, recordType: string): Promise<T[]> {
    const rows = await this.all<DatabaseRow>(
      `
        select payload_json
        from source_cache
        where provider = $1 and record_type = $2
        order by updated_at desc
      `,
      provider,
      recordType,
    );
    return rows.map((row) => parseJsonValue<T>(row.payload_json));
  }

  async startJobRun(jobName: JobName): Promise<string> {
    const id = cryptoRandomId();
    await this.sql`
      insert into job_runs (id, job_name, status, details_json, started_at, finished_at)
      values (${id}, ${jobName}, 'running', ${"{}"}::jsonb, ${nowIso()}, null)
    `;
    return id;
  }

  async finishJobRun(id: string, result: JobResult): Promise<void> {
    await this.sql`
      update job_runs
      set status = ${result.status},
          details_json = ${JSON.stringify(result)}::jsonb,
          finished_at = ${result.finishedAt}
      where id = ${id}
    `;
  }

  async listRecentJobRuns(limit = 12): Promise<JobRunRecord[]> {
    const rows = await this.all<DatabaseRow>(
      `
        select
          id,
          job_name as "jobName",
          status,
          details_json as "detailsJson",
          started_at as "startedAt",
          finished_at as "finishedAt"
        from job_runs
        order by started_at desc
        limit $1
      `,
      limit,
    );

    return rows.map((row) => ({
      id: String(row.id),
      jobName: row.jobName as JobName,
      status: String(row.status) as JobRunRecord["status"],
      detailsJson: stringifyJsonValue(row.detailsJson),
      startedAt: String(row.startedAt),
      finishedAt: normalizeNullableText(row.finishedAt),
    }));
  }

  async upsertDecision(entry: {
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
  }): Promise<void> {
    const timestamp = nowIso();
    await this.sql`
      insert into decisions_cache (
        decision_id,
        notion_page_id,
        source_type,
        source_external_id,
        status,
        title,
        gmail_url,
        notion_url,
        read_gate_blocked,
        payload_json,
        created_at,
        updated_at
      )
      values (
        ${entry.decisionId},
        ${entry.notionPageId ?? null},
        ${entry.sourceType},
        ${entry.sourceExternalId},
        ${entry.status},
        ${entry.title},
        ${entry.gmailUrl ?? null},
        ${entry.notionUrl ?? null},
        ${entry.readGateBlocked},
        ${JSON.stringify(entry.payload)}::jsonb,
        ${timestamp},
        ${timestamp}
      )
      on conflict (decision_id) do update set
        notion_page_id = excluded.notion_page_id,
        status = excluded.status,
        title = excluded.title,
        gmail_url = excluded.gmail_url,
        notion_url = excluded.notion_url,
        read_gate_blocked = excluded.read_gate_blocked,
        payload_json = excluded.payload_json,
        updated_at = excluded.updated_at
    `;
  }

  async getDecision(decisionId: string): Promise<DecisionCacheEntry | null> {
    const row = await this.get<DatabaseRow>(
      `
        select
          decision_id as "decisionId",
          notion_page_id as "notionPageId",
          source_type as "sourceType",
          source_external_id as "sourceExternalId",
          status,
          title,
          gmail_url as "gmailUrl",
          notion_url as "notionUrl",
          read_gate_blocked as "readGateBlocked",
          payload_json as payload,
          created_at as "createdAt",
          updated_at as "updatedAt"
        from decisions_cache
        where decision_id = $1
      `,
      decisionId,
    );

    return row ? mapDecisionRow(row) : null;
  }

  async listPendingDecisions(): Promise<DecisionCacheEntry[]> {
    const rows = await this.all<DatabaseRow>(
      `
        select
          decision_id as "decisionId",
          notion_page_id as "notionPageId",
          source_type as "sourceType",
          source_external_id as "sourceExternalId",
          status,
          title,
          gmail_url as "gmailUrl",
          notion_url as "notionUrl",
          read_gate_blocked as "readGateBlocked",
          payload_json as payload,
          created_at as "createdAt",
          updated_at as "updatedAt"
        from decisions_cache
        where status in ('pending', 'snoozed')
        order by updated_at desc
      `,
    );

    return rows.map((row) => mapDecisionRow(row));
  }

  async updateDecisionStatus(
    decisionId: string,
    status: string,
    payload: DecisionProposal,
    notionUrl?: string | null,
  ): Promise<void> {
    await this.sql`
      update decisions_cache
      set status = ${status},
          payload_json = ${JSON.stringify(payload)}::jsonb,
          notion_url = coalesce(${notionUrl ?? null}, notion_url),
          read_gate_blocked = ${payload.readGateBlocked},
          updated_at = ${nowIso()}
      where decision_id = ${decisionId}
    `;
  }

  async addSuppressionHint(key: string, reason: string): Promise<void> {
    await this.sql`
      insert into suppression_hints (suppression_key, reason, created_at)
      values (${key}, ${reason}, ${nowIso()})
      on conflict (suppression_key) do update set
        reason = excluded.reason,
        created_at = excluded.created_at
    `;
  }

  async hasSuppressionHint(key: string): Promise<boolean> {
    const row = await this.get<DatabaseRow>(
      `
        select suppression_key
        from suppression_hints
        where suppression_key = $1
      `,
      key,
    );
    return Boolean(row);
  }

  async queueSnapshot(): Promise<QueueSnapshot> {
    const [decisions, latestRuns] = await Promise.all([this.listPendingDecisions(), this.listRecentJobRuns()]);
    return {
      decisions,
      latestRuns,
    };
  }
}

function mapDecisionRow(row: DatabaseRow): DecisionCacheEntry {
  return {
    decisionId: String(row.decisionId),
    notionPageId: normalizeNullableText(row.notionPageId),
    sourceType: String(row.sourceType) as SourceType,
    sourceExternalId: String(row.sourceExternalId),
    status: String(row.status) as DecisionCacheEntry["status"],
    title: String(row.title),
    gmailUrl: normalizeNullableText(row.gmailUrl),
    notionUrl: normalizeNullableText(row.notionUrl),
    readGateBlocked: Boolean(row.readGateBlocked),
    payload: parseJsonValue<DecisionProposal>(row.payload),
    createdAt: String(row.createdAt),
    updatedAt: String(row.updatedAt),
  };
}

function normalizeNullableText(value: RowValue | undefined): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  return String(value);
}

function parseJsonValue<T>(value: RowValue | undefined): T {
  if (typeof value === "string") {
    return JSON.parse(value) as T;
  }
  return value as T;
}

function stringifyJsonValue(value: RowValue | undefined): string {
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value ?? {});
}

function cryptoRandomId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
