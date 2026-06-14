-- Cache for `learn practice`: per-token explanations of a command.
-- Stored as {"tokens": [...], "parts": [...]} so a command is explained by the
-- LLM only once, then reused (and reusable across users via the command text).
alter table commands add column if not exists breakdown jsonb;
