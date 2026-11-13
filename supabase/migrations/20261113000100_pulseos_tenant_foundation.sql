-- PulseOS tenant foundation (additive; does not cut over the existing SQLite app).
-- Apply in Supabase SQL Editor only after reviewing the release notes in this PR.

create extension if not exists pgcrypto;

create table if not exists public.pulseos_workspaces (
    user_id uuid primary key references auth.users(id) on delete cascade,
    display_name text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.pulseos_datasets (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    dataset_type text not null check (dataset_type in ('events', 'reviews', 'documents')),
    original_filename text not null,
    object_path text not null,
    row_count bigint not null default 0 check (row_count >= 0),
    content_type text,
    uploaded_at timestamptz not null default now(),
    unique (owner_id, id, dataset_type),
    unique (object_path)
);

create index if not exists pulseos_datasets_owner_uploaded_idx
    on public.pulseos_datasets (owner_id, uploaded_at desc);
create index if not exists pulseos_datasets_owner_type_idx
    on public.pulseos_datasets (owner_id, dataset_type);

create table if not exists public.pulseos_active_datasets (
    owner_id uuid not null references auth.users(id) on delete cascade,
    dataset_type text not null check (dataset_type in ('events', 'reviews', 'documents')),
    dataset_id uuid,
    updated_at timestamptz not null default now(),
    primary key (owner_id, dataset_type),
    constraint pulseos_active_dataset_owned_fk
      foreign key (owner_id, dataset_id, dataset_type)
      references public.pulseos_datasets (owner_id, id, dataset_type)
      on delete set null (dataset_id)
);

alter table public.pulseos_workspaces enable row level security;
alter table public.pulseos_datasets enable row level security;
alter table public.pulseos_active_datasets enable row level security;

drop policy if exists "workspace owner can read" on public.pulseos_workspaces;
create policy "workspace owner can read" on public.pulseos_workspaces
  for select to authenticated using (user_id = (select auth.uid()));
drop policy if exists "workspace owner can create" on public.pulseos_workspaces;
create policy "workspace owner can create" on public.pulseos_workspaces
  for insert to authenticated with check (user_id = (select auth.uid()));
drop policy if exists "workspace owner can update" on public.pulseos_workspaces;
create policy "workspace owner can update" on public.pulseos_workspaces
  for update to authenticated using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

drop policy if exists "dataset owner access" on public.pulseos_datasets;
create policy "dataset owner access" on public.pulseos_datasets
  for all to authenticated using (owner_id = (select auth.uid()))
  with check (owner_id = (select auth.uid()));

drop policy if exists "active dataset owner access" on public.pulseos_active_datasets;
create policy "active dataset owner access" on public.pulseos_active_datasets
  for all to authenticated using (owner_id = (select auth.uid()))
  with check (
    owner_id = (select auth.uid())
    and (
      dataset_id is null
      or exists (
        select 1 from public.pulseos_datasets d
        where d.id = dataset_id
          and d.owner_id = (select auth.uid())
          and d.dataset_type = pulseos_active_datasets.dataset_type
      )
    )
  );

-- The private bucket stores objects under <auth.uid()>/<dataset-uuid>/<filename>.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'pulseos-private',
  'pulseos-private',
  false,
  20971520,
  array[
    'text/csv',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain'
  ]
)
on conflict (id) do update
set public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "PulseOS users read own objects" on storage.objects;
create policy "PulseOS users read own objects" on storage.objects
  for select to authenticated
  using (
    bucket_id = 'pulseos-private'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

drop policy if exists "PulseOS users upload own objects" on storage.objects;
create policy "PulseOS users upload own objects" on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'pulseos-private'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

drop policy if exists "PulseOS users update own objects" on storage.objects;
create policy "PulseOS users update own objects" on storage.objects
  for update to authenticated
  using (
    bucket_id = 'pulseos-private'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  )
  with check (
    bucket_id = 'pulseos-private'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

drop policy if exists "PulseOS users delete own objects" on storage.objects;
create policy "PulseOS users delete own objects" on storage.objects
  for delete to authenticated
  using (
    bucket_id = 'pulseos-private'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

-- Create a workspace row automatically for new Supabase Auth users.
create or replace function public.pulseos_create_workspace_for_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.pulseos_workspaces (user_id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'full_name', new.email))
  on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists pulseos_auth_user_workspace on auth.users;
create trigger pulseos_auth_user_workspace
  after insert on auth.users
  for each row execute procedure public.pulseos_create_workspace_for_user();

-- Backfill existing auth users once, without assigning any legacy SQLite data.
insert into public.pulseos_workspaces (user_id, display_name)
select id, coalesce(raw_user_meta_data ->> 'full_name', email)
from auth.users
on conflict (user_id) do nothing;
