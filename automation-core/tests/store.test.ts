import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { LocalStore } from "../src/store";
import { createIsolatedDatabase } from "./helpers/postgres-test-db";

const describePostgres = process.env.RUN_POSTGRES_TESTS === "1" ? describe : describe.skip;

describePostgres("LocalStore", () => {
  let databaseUrl = "";
  let cleanupDatabase = async () => {};

  void beforeAll(async () => {
    const isolated = await createIsolatedDatabase("automation_core_store");
    databaseUrl = isolated.databaseUrl;
    cleanupDatabase = isolated.dispose;
  });

  void afterAll(async () => {
    await cleanupDatabase();
  });

  it("applies the GitHub analytics migrations to the Supabase-backed Postgres store", async () => {
    const store = await LocalStore.create(databaseUrl);
    const repoTable = await store.get<{ exists: boolean }>(
      "select to_regclass('public.github_repositories') is not null as exists",
    );
    const contributorTable = await store.get<{ exists: boolean }>(
      "select to_regclass('public.github_contributors') is not null as exists",
    );
    const weeklyBriefTable = await store.get<{ exists: boolean }>(
      "select to_regclass('public.github_weekly_briefs') is not null as exists",
    );

    expect(repoTable?.exists).toBe(true);
    expect(contributorTable?.exists).toBe(true);
    expect(weeklyBriefTable?.exists).toBe(true);

    await store.close();
  });

  it("round-trips GitHub analytics records through the Postgres store", async () => {
    const store = await LocalStore.create(databaseUrl);
    const repoId = `repo-${crypto.randomUUID()}`;

    await store.run(
      `
        insert into github_weekly_briefs (week_start, generated_at, headline, summary, payload_json, notion_url)
        values ($1, $2, $3, $4, $5::jsonb, $6)
        on conflict (week_start) do update set
          generated_at = excluded.generated_at,
          headline = excluded.headline,
          summary = excluded.summary,
          payload_json = excluded.payload_json,
          notion_url = excluded.notion_url
      `,
      "2026-04-13",
      "2026-04-18T08:00:00.000Z",
      "Engineering stayed steady",
      "Weekly brief for test coverage",
      JSON.stringify({
        weekStart: "2026-04-13",
        topRepositories: [{ fullName: "acme/dashboard", commits: 7, netLoc: 75 }],
      }),
      "https://www.notion.so/brief-1",
    );

    const weeklyBrief = await store.get<{
      week_start: string;
      headline: string;
      notion_url: string | null;
    }>(
      `
        select week_start, headline, notion_url
        from github_weekly_briefs
        where week_start = $1
      `,
      "2026-04-13",
    );

    expect(weeklyBrief).toEqual({
      week_start: "2026-04-13",
      headline: "Engineering stayed steady",
      notion_url: "https://www.notion.so/brief-1",
    });

    await store.run("delete from github_weekly_briefs where week_start = $1", "2026-04-13");
    await store.run("delete from github_repositories where repo_id = $1", repoId);
    await store.close();
  });
});
