create table if not exists oauth_tokens (
  provider text primary key,
  token_json text not null,
  email text,
  updated_at text not null
);

create table if not exists sync_state (
  provider text not null,
  state_key text not null,
  state_value text not null,
  updated_at text not null,
  primary key (provider, state_key)
);

create table if not exists source_cache (
  provider text not null,
  record_type text not null,
  external_id text not null,
  hash text not null,
  payload_json jsonb not null,
  updated_at text not null,
  primary key (provider, record_type, external_id)
);

create table if not exists decisions_cache (
  decision_id text primary key,
  notion_page_id text,
  source_type text not null,
  source_external_id text not null,
  status text not null,
  title text not null,
  gmail_url text,
  notion_url text,
  read_gate_blocked boolean not null default false,
  payload_json jsonb not null,
  created_at text not null,
  updated_at text not null
);

create table if not exists job_runs (
  id text primary key,
  job_name text not null,
  status text not null,
  details_json jsonb not null,
  started_at text not null,
  finished_at text
);

create table if not exists suppression_hints (
  suppression_key text primary key,
  reason text not null,
  created_at text not null
);

create table if not exists github_repositories (
  repo_id text primary key,
  owner text not null,
  name text not null,
  full_name text not null unique,
  description text not null default '',
  visibility text not null default 'private',
  language text not null default '',
  default_branch text not null default 'main',
  is_archived boolean not null default false,
  is_fork boolean not null default false,
  html_url text not null,
  clone_url text not null,
  pushed_at text,
  created_at text,
  updated_at text,
  first_synced_at text,
  last_synced_at text,
  mirror_path text not null,
  commit_count integer not null default 0,
  additions integer not null default 0,
  deletions integer not null default 0,
  changed_files integer not null default 0,
  open_prs integer not null default 0,
  merged_prs integer not null default 0,
  open_issues integer not null default 0,
  releases integer not null default 0,
  workflow_failures integer not null default 0,
  latest_activity_at text
);

create table if not exists github_repo_sync_state (
  repo_id text primary key,
  last_discovered_at text,
  last_backfill_at text,
  last_synced_at text,
  last_rollup_at text,
  pull_cursor text,
  issue_cursor text,
  release_cursor text,
  workflow_cursor text,
  last_error text
);

create table if not exists github_contributors (
  contributor_id text primary key,
  canonical_login text unique,
  display_name text not null,
  avatar_url text,
  first_seen_at text,
  last_active_at text,
  repo_count integer not null default 0,
  commit_count integer not null default 0,
  additions integer not null default 0,
  deletions integer not null default 0,
  changed_files integer not null default 0,
  prs_opened integer not null default 0,
  prs_merged integer not null default 0,
  reviews_submitted integer not null default 0,
  issues_opened integer not null default 0,
  workflow_runs integer not null default 0,
  latest_activity_at text
);

create table if not exists github_contributor_aliases (
  alias_key text primary key,
  contributor_id text not null,
  login text,
  name text,
  email text,
  last_seen_at text not null
);

create table if not exists github_commits (
  repo_id text not null,
  sha text not null,
  author_contributor_id text,
  author_login text,
  author_name text not null,
  author_email text not null,
  authored_at text not null,
  committed_at text not null,
  subject text not null,
  body text not null,
  additions integer not null default 0,
  deletions integer not null default 0,
  changed_files integer not null default 0,
  is_merge boolean not null default false,
  html_url text not null,
  ref_names_json jsonb not null default '[]'::jsonb,
  primary key (repo_id, sha)
);

create table if not exists github_pull_requests (
  pull_request_id text primary key,
  repo_id text not null,
  number integer not null,
  author_contributor_id text,
  author_login text,
  title text not null,
  state text not null,
  created_at text not null,
  updated_at text not null,
  merged_at text,
  closed_at text,
  additions integer not null default 0,
  deletions integer not null default 0,
  changed_files integer not null default 0,
  commits_count integer not null default 0,
  review_comments integer not null default 0,
  comments integer not null default 0,
  html_url text not null
);

create table if not exists github_pull_request_reviews (
  review_id text primary key,
  repo_id text not null,
  pull_request_id text not null,
  reviewer_contributor_id text,
  reviewer_login text,
  state text not null,
  submitted_at text,
  html_url text not null
);

create table if not exists github_issues (
  issue_id text primary key,
  repo_id text not null,
  number integer not null,
  author_contributor_id text,
  author_login text,
  title text not null,
  state text not null,
  created_at text not null,
  updated_at text not null,
  closed_at text,
  comments integer not null default 0,
  html_url text not null
);

create table if not exists github_releases (
  release_id text primary key,
  repo_id text not null,
  tag_name text not null,
  name text not null,
  is_draft boolean not null default false,
  is_prerelease boolean not null default false,
  published_at text,
  created_at text not null,
  html_url text not null
);

create table if not exists github_workflow_runs (
  run_id text primary key,
  repo_id text not null,
  workflow_name text not null,
  status text not null,
  conclusion text,
  event text not null,
  branch text,
  actor_contributor_id text,
  actor_login text,
  created_at text not null,
  updated_at text not null,
  html_url text not null
);

create table if not exists github_daily_rollups (
  entity_type text not null,
  entity_id text not null,
  bucket_start text not null,
  commits integer not null default 0,
  additions integer not null default 0,
  deletions integer not null default 0,
  changed_files integer not null default 0,
  prs_opened integer not null default 0,
  prs_merged integer not null default 0,
  reviews_submitted integer not null default 0,
  issues_opened integer not null default 0,
  issues_closed integer not null default 0,
  releases integer not null default 0,
  workflow_runs integer not null default 0,
  workflow_failures integer not null default 0,
  primary key (entity_type, entity_id, bucket_start)
);

create table if not exists github_weekly_rollups (
  entity_type text not null,
  entity_id text not null,
  bucket_start text not null,
  commits integer not null default 0,
  additions integer not null default 0,
  deletions integer not null default 0,
  changed_files integer not null default 0,
  prs_opened integer not null default 0,
  prs_merged integer not null default 0,
  reviews_submitted integer not null default 0,
  issues_opened integer not null default 0,
  issues_closed integer not null default 0,
  releases integer not null default 0,
  workflow_runs integer not null default 0,
  workflow_failures integer not null default 0,
  primary key (entity_type, entity_id, bucket_start)
);

create table if not exists github_monthly_rollups (
  entity_type text not null,
  entity_id text not null,
  bucket_start text not null,
  commits integer not null default 0,
  additions integer not null default 0,
  deletions integer not null default 0,
  changed_files integer not null default 0,
  prs_opened integer not null default 0,
  prs_merged integer not null default 0,
  reviews_submitted integer not null default 0,
  issues_opened integer not null default 0,
  issues_closed integer not null default 0,
  releases integer not null default 0,
  workflow_runs integer not null default 0,
  workflow_failures integer not null default 0,
  primary key (entity_type, entity_id, bucket_start)
);

create table if not exists github_weekly_briefs (
  week_start text primary key,
  generated_at text not null,
  headline text not null,
  summary text not null,
  payload_json jsonb not null,
  notion_url text
);

create index if not exists idx_source_cache_lookup on source_cache (provider, record_type, updated_at desc);
create index if not exists idx_decisions_cache_status on decisions_cache (status, updated_at desc);
create index if not exists idx_job_runs_started_at on job_runs (started_at desc);
create index if not exists idx_github_repositories_owner on github_repositories (owner, name);
create index if not exists idx_github_commits_authored on github_commits (authored_at desc);
create index if not exists idx_github_commits_author on github_commits (author_contributor_id, authored_at desc);
create index if not exists idx_github_pull_requests_repo on github_pull_requests (repo_id, updated_at desc);
create index if not exists idx_github_pull_request_reviews_repo on github_pull_request_reviews (repo_id, submitted_at desc);
create index if not exists idx_github_issues_repo on github_issues (repo_id, updated_at desc);
create index if not exists idx_github_releases_repo on github_releases (repo_id, published_at desc);
create index if not exists idx_github_workflow_runs_repo on github_workflow_runs (repo_id, updated_at desc);
create index if not exists idx_github_daily_rollups_bucket on github_daily_rollups (entity_type, bucket_start desc);
create index if not exists idx_github_weekly_rollups_bucket on github_weekly_rollups (entity_type, bucket_start desc);
create index if not exists idx_github_monthly_rollups_bucket on github_monthly_rollups (entity_type, bucket_start desc);
