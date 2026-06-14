-- Migration: signature-based grouping + count-based scoring.
-- Run in the Supabase SQL editor (safe to re-run). Apply after auth.sql.
--
-- Commands are now grouped by a normalized *signature* (program + subcommand +
-- flags, argument values dropped) instead of the exact string. Scoring is a
-- plain count of uses, so the points machinery is retired.

-- 1. signature column. Existing rows have no CLI-computed signature, so backfill
--    with the literal command (good enough; future logs carry real signatures).
alter table commands add column if not exists signature text;
update commands set signature = command where signature is null;
alter table commands alter column signature set not null;

-- 2. Dedup existing rows that now collide on (user_id, signature): keep the
--    oldest row per group, repoint its command_uses, delete the duplicates.
with ranked as (
  select id, user_id, signature,
         first_value(id) over (
           partition by user_id, signature order by created_at, id
         ) as keep_id
  from commands
)
update command_uses u
set command_id = r.keep_id
from ranked r
where u.command_id = r.id and r.id <> r.keep_id;

with ranked as (
  select id,
         row_number() over (
           partition by user_id, signature order by created_at, id
         ) as rn
  from commands
)
delete from commands where id in (select id from ranked where rn > 1);

-- 3. Re-key uniqueness from (user, command) to (user, signature).
alter table commands drop constraint if exists commands_user_id_command_key;
alter table commands
  add constraint commands_user_id_signature_key unique (user_id, signature);

create index if not exists commands_signature_idx on commands(user_id, signature);

-- 4. Trigram index to make substring (ILIKE) search fast for /api/search.
create extension if not exists pg_trgm;
create index if not exists commands_command_trgm_idx
  on commands using gin (command gin_trgm_ops);

-- 5. Count-based scoring: uses per skill (replaces skill_scores/points).
create or replace function skill_counts(p_user_id uuid)
returns table (skill text, uses bigint)
language sql stable
as $$
  select s.skill, count(*) as uses
  from commands c
  join command_uses u on u.command_id = c.id
  cross join lateral unnest(coalesce(c.skills, '{}')) as s(skill)
  where c.user_id = p_user_id
  group by s.skill
  order by uses desc;
$$;

drop function if exists skill_scores(uuid);
