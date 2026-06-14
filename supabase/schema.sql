-- learn — schema for the vertical slice (run in Supabase SQL editor).
-- No auth yet: a hardcoded dev user id is used by the CLI. RLS is added in the
-- auth milestone; for now the API uses the service-role key server-side only.

create extension if not exists vector;
create extension if not exists "pgcrypto";

-- One row per distinct (user, command). Re-running a logged command adds a
-- command_uses row rather than a new commands row.
create table if not exists commands (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null,
  command       text not null,
  intent        text,                 -- AI: "Restore a file from a previous commit"
  explanation   text,                 -- AI: longer explanation
  complexity    int,                  -- AI: 1-5
  skills        text[] default '{}',  -- AI: ['git','history-surgery']
  embedding     vector(1536),         -- of intent (+command)
  hostname      text,
  project       text,
  cwd           text,
  first_used_at timestamptz default now(),
  created_at    timestamptz default now(),
  unique (user_id, command)
);

create table if not exists command_uses (
  id             uuid primary key default gen_random_uuid(),
  command_id     uuid not null references commands(id) on delete cascade,
  user_id        uuid not null,
  used_at        timestamptz default now(),
  exit_code      int,
  points_awarded numeric default 0
);

create index if not exists commands_user_idx on commands(user_id);
create index if not exists commands_project_idx on commands(user_id, project);
create index if not exists uses_command_idx on command_uses(command_id);

-- Vector similarity index (cosine). ivfflat needs ANALYZE after data loads; for
-- demo-scale data a plain index is fine and lists can stay small.
create index if not exists commands_embedding_idx
  on commands using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- Semantic recall: nearest commands for a query embedding, scoped to one user.
create or replace function match_commands(
  p_user_id uuid,
  query_embedding vector(1536),
  match_count int default 5
)
returns table (
  id uuid,
  command text,
  intent text,
  explanation text,
  complexity int,
  skills text[],
  similarity float
)
language sql stable
as $$
  select
    c.id, c.command, c.intent, c.explanation, c.complexity, c.skills,
    1 - (c.embedding <=> query_embedding) as similarity
  from commands c
  where c.user_id = p_user_id and c.embedding is not null
  order by c.embedding <=> query_embedding
  limit match_count;
$$;

-- XP per skill: explode skills[] and sum points across all uses.
create or replace function skill_scores(p_user_id uuid)
returns table (skill text, xp numeric)
language sql stable
as $$
  select s.skill, sum(u.points_awarded) as xp
  from commands c
  join command_uses u on u.command_id = c.id
  cross join lateral unnest(coalesce(c.skills, '{}')) as s(skill)
  where c.user_id = p_user_id
  group by s.skill
  order by xp desc;
$$;
