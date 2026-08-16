-- Public-safe schema snapshot of the current ESC semantic-search backend.
--
-- This is intentionally a schema snapshot rather than a fabricated migration:
-- the live project has no migration-history entries. It contains no data,
-- project references, private links, API keys, or deployment identifiers.

create schema if not exists extensions;
create extension if not exists vector with schema extensions;

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create table if not exists public.esc_projects (
  id bigint generated always as identity primary key,
  programme text not null,
  action text,
  funding_year smallint,
  project_identifier text not null unique,
  project_title text,
  project_summary text,
  results_platform_project_card text,
  coordinating_organisation_name text,
  coordinator_country text,
  participating_countries text,
  funding_amount numeric,
  search_text text not null default '',
  search_fts tsvector generated always as (
    to_tsvector('simple'::regconfig, search_text)
  ) stored,
  embedding extensions.vector(384),
  embedding_model text,
  embedding_updated_at timestamptz,
  source_name text not null default 'Google Drive: European Solidarity Corps Germany Projects — Enriched',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint esc_projects_funding_year_check
    check (funding_year is null or funding_year between 2000 and 2100),
  constraint esc_projects_funding_amount_check
    check (funding_amount is null or funding_amount >= 0)
);

comment on table public.esc_projects is
  'European Solidarity Corps projects imported idempotently from the private enriched source.';
comment on column public.esc_projects.embedding is
  'Normalized 384-dimensional gte-small embedding of search_text.';

create or replace function private.prepare_esc_project()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  next_search_text text;
begin
  next_search_text := concat_ws(E'\n',
    nullif(new.project_title, ''),
    nullif(new.action, ''),
    nullif(new.coordinating_organisation_name, ''),
    nullif(new.coordinator_country, ''),
    nullif(new.participating_countries, ''),
    nullif(new.project_summary, '')
  );

  if tg_op = 'UPDATE' and next_search_text is distinct from old.search_text then
    new.embedding := null;
    new.embedding_model := null;
    new.embedding_updated_at := null;
  end if;

  new.search_text := next_search_text;
  new.updated_at := now();
  return new;
end;
$$;

revoke all on function private.prepare_esc_project() from public, anon, authenticated, service_role;
grant execute on function private.prepare_esc_project() to postgres;

drop trigger if exists esc_projects_prepare on public.esc_projects;
create trigger esc_projects_prepare
before insert or update of
  project_title,
  action,
  coordinating_organisation_name,
  coordinator_country,
  participating_countries,
  project_summary
on public.esc_projects
for each row
execute function private.prepare_esc_project();

create index if not exists esc_projects_embedding_hnsw_idx
  on public.esc_projects
  using hnsw (embedding extensions.vector_ip_ops);

create index if not exists esc_projects_filters_idx
  on public.esc_projects (coordinator_country, action, funding_year);

create index if not exists esc_projects_funding_year_idx
  on public.esc_projects (funding_year);

create index if not exists esc_projects_search_fts_idx
  on public.esc_projects
  using gin (search_fts);

create or replace function public.search_esc_projects(
  query_embedding extensions.vector,
  match_count integer default 10,
  filter_country text default null,
  filter_action text default null,
  filter_funding_year smallint default null
)
returns table (
  project_identifier text,
  project_title text,
  project_summary text,
  results_platform_project_card text,
  action text,
  coordinator_country text,
  funding_year smallint,
  funding_amount numeric,
  similarity double precision
)
language sql
stable
set search_path = ''
as $$
  select
    p.project_identifier,
    p.project_title,
    p.project_summary,
    p.results_platform_project_card,
    p.action,
    p.coordinator_country,
    p.funding_year,
    p.funding_amount,
    -(p.embedding operator(extensions.<#>) query_embedding) as similarity
  from public.esc_projects as p
  where p.embedding is not null
    and (filter_country is null or p.coordinator_country = upper(filter_country))
    and (filter_action is null or p.action = filter_action)
    and (filter_funding_year is null or p.funding_year = filter_funding_year)
  order by p.embedding operator(extensions.<#>) query_embedding
  limit least(greatest(match_count, 1), 100);
$$;

revoke all on function public.search_esc_projects(
  extensions.vector, integer, text, text, smallint
) from public, anon, authenticated;
grant execute on function public.search_esc_projects(
  extensions.vector, integer, text, text, smallint
) to postgres, service_role;

alter table public.esc_projects enable row level security;
drop policy if exists esc_projects_no_direct_client_access on public.esc_projects;
create policy esc_projects_no_direct_client_access
  on public.esc_projects
  for all
  to anon, authenticated
  using (false)
  with check (false);

revoke all on table public.esc_projects from public, anon, authenticated;
grant all on table public.esc_projects to postgres, service_role;

do $$
declare
  identity_sequence text;
begin
  select pg_get_serial_sequence('public.esc_projects', 'id')
    into identity_sequence;

  if identity_sequence is not null then
    execute format(
      'revoke all on sequence %s from public, anon, authenticated',
      identity_sequence
    );
    execute format(
      'grant all on sequence %s to postgres, service_role',
      identity_sequence
    );
  end if;
end;
$$;
