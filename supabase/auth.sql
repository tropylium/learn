-- Migration: add auth + RLS to an EXISTING learn database.
-- Run this in the Supabase SQL editor after schema.sql. Safe to re-run.
--
-- The vertical slice used a hardcoded dev user with no FK to auth. This wires
-- user_id to auth.users and enables row-level security. Existing dev-user rows
-- are deleted because they reference a user that doesn't exist in auth.users.

-- 1. Clear vertical-slice test data (dev user is not a real auth user).
delete from command_uses where user_id = '00000000-0000-0000-0000-000000000001';
delete from commands     where user_id = '00000000-0000-0000-0000-000000000001';

-- 2. Foreign keys to auth.users (cascade so deleting an account clears its data).
alter table commands
  drop constraint if exists commands_user_id_fkey;
alter table commands
  add constraint commands_user_id_fkey
  foreign key (user_id) references auth.users(id) on delete cascade;

alter table command_uses
  drop constraint if exists command_uses_user_id_fkey_auth;
alter table command_uses
  add constraint command_uses_user_id_fkey_auth
  foreign key (user_id) references auth.users(id) on delete cascade;

-- 3. Row-level security. The API uses the service role (which bypasses RLS) and
--    scopes every query by the JWT-verified user_id; these policies are defense
--    in depth, blocking any direct access with the public anon key.
alter table commands     enable row level security;
alter table command_uses enable row level security;

drop policy if exists "own commands" on commands;
create policy "own commands" on commands
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "own command_uses" on command_uses;
create policy "own command_uses" on command_uses
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
