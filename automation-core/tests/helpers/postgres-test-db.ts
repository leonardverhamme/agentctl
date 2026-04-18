import postgres from "postgres";

const DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:58322/postgres";

export async function createIsolatedDatabase(prefix: string): Promise<{
  databaseName: string;
  databaseUrl: string;
  dispose: () => Promise<void>;
}> {
  const databaseName = `${prefix}_${crypto.randomUUID().replace(/-/g, "").slice(0, 24)}`;
  const adminUrl = buildAdminUrl();
  const targetUrl = new URL(adminUrl.toString());
  targetUrl.pathname = `/${databaseName}`;

  const admin = postgres(adminUrl.toString(), {
    prepare: false,
    max: 1,
    idle_timeout: 1,
    connect_timeout: 30,
  });

  try {
    await admin.unsafe(`create database "${databaseName}" template template0`);
  } finally {
    await admin.end();
  }

  return {
    databaseName,
    databaseUrl: targetUrl.toString(),
    async dispose() {
      const dropAdmin = postgres(adminUrl.toString(), {
        prepare: false,
        max: 1,
        idle_timeout: 1,
        connect_timeout: 30,
      });
      try {
        await dropAdmin.unsafe(`drop database if exists "${databaseName}"`);
      } finally {
        await dropAdmin.end();
      }
    },
  };
}

function buildAdminUrl(): URL {
  const raw = process.env.TEST_ADMIN_DATABASE_URL ?? process.env.DATABASE_URL ?? DEFAULT_DATABASE_URL;
  const url = new URL(raw);
  url.pathname = "/postgres";
  return url;
}
