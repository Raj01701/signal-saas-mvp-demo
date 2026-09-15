-- Signal schema: one workspace per signed-up user, seeded with demo data on sign-up.
-- Browsers never query these tables directly. RLS is on with no policies, so the public
-- anon/authenticated keys are denied; every read and write goes through /api, which
-- verifies the caller's Supabase session and enforces workspace roles with the service role.

create table public.workspaces (
  id         uuid primary key default gen_random_uuid(),
  name       text not null,
  created_at timestamptz not null default now()
);

create table public.members (
  id           bigint generated always as identity primary key,
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  user_id      uuid references auth.users(id) on delete set null,
  name         text not null check (length(btrim(name)) between 1 and 80),
  email        text check (length(email) <= 254),
  role         text not null default 'Member' check (role in ('Owner', 'Admin', 'Member', 'Viewer')),
  active       boolean not null default true,
  created_at   timestamptz not null default now(),
  unique (workspace_id, email)
);
create unique index members_user_id_key on public.members (user_id) where user_id is not null;
create index members_workspace_idx on public.members (workspace_id);

create table public.submissions (
  id           bigint generated always as identity primary key,
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  title        text not null check (length(btrim(title)) between 1 and 200),
  requester    text not null check (length(btrim(requester)) between 1 and 80),
  votes        integer not null default 1 check (votes >= 0),
  status       text not null default 'open' check (status in ('open', 'prog', 'shipped', 'closed')),
  created_by   uuid references auth.users(id) on delete set null,
  created_at   timestamptz not null default now()
);
create index submissions_workspace_idx on public.submissions (workspace_id, created_at desc);

alter table public.workspaces  enable row level security;
alter table public.members     enable row level security;
alter table public.submissions enable row level security;
revoke all on public.workspaces, public.members, public.submissions from anon, authenticated;

-- Atomic increment, so concurrent upvotes never overwrite each other.
create function public.upvote_submission(p_workspace uuid, p_id bigint)
returns setof public.submissions
language sql
set search_path = ''
as $$
  update public.submissions
     set votes = votes + 1
   where id = p_id and workspace_id = p_workspace
  returning *;
$$;

create function public.seed_workspace(p_workspace uuid)
returns void
language sql
set search_path = ''
as $$
  insert into public.submissions (workspace_id, title, requester, votes, status, created_at) values
    (p_workspace, 'Slack notifications for new feedback', 'Priya (Acme)',       42, 'prog',    now() - interval '1 day'),
    (p_workspace, 'Export requests to CSV',               'Daniel M.',          28, 'open',    now() - interval '3 days'),
    (p_workspace, 'Dark mode for the dashboard',          'Lucia R.',           19, 'shipped', now() - interval '6 days'),
    (p_workspace, 'Public roadmap page',                  'Tomás (Beta)',       37, 'open',    now() - interval '9 days'),
    (p_workspace, 'Merge duplicate requests',             'Priya (Acme)',       15, 'prog',    now() - interval '12 days'),
    (p_workspace, 'Weekly digest email',                  'Sofia K.',           23, 'open',    now() - interval '16 days'),
    (p_workspace, 'SSO / Google login',                   'Marco (Enterprise)', 31, 'closed',  now() - interval '24 days'),
    (p_workspace, 'Tag & categorise submissions',         'Daniel M.',          12, 'shipped', now() - interval '33 days'),
    (p_workspace, 'Mobile push notifications',            'Aisha N.',           26, 'open',    now() - interval '2 days'),
    (p_workspace, 'Bulk status updates',                  'Marco (Enterprise)',  9, 'prog',    now() - interval '19 days');

  insert into public.members (workspace_id, name, email, role, active) values
    (p_workspace, 'Priya Nair',    'priya@acme.io',      'Admin',  true),
    (p_workspace, 'Daniel Moreno', 'daniel@startup.com', 'Member', true),
    (p_workspace, 'Lucia Rossi',   'lucia@beta.co',      'Viewer', false),
    (p_workspace, 'Sofia Kaur',    'sofia@startup.com',  'Member', true);
$$;

-- Every new auth user (email or anonymous guest) gets a fresh workspace they own.
create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_email     text := nullif(btrim(new.email), '');
  v_name      text := coalesce(nullif(btrim(new.raw_user_meta_data ->> 'name'), ''), split_part(v_email, '@', 1), 'Guest');
  v_workspace uuid;
begin
  insert into public.workspaces (name) values (left(v_name, 60) || '''s workspace')
  returning id into v_workspace;

  insert into public.members (workspace_id, user_id, name, email, role)
  values (v_workspace, new.id, left(v_name, 80), v_email, 'Owner');

  perform public.seed_workspace(v_workspace);
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

revoke execute on function public.upvote_submission(uuid, bigint) from public, anon, authenticated;
revoke execute on function public.seed_workspace(uuid)             from public, anon, authenticated;
revoke execute on function public.handle_new_user()                from public, anon, authenticated;
