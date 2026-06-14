-- Return context columns (cwd/project/hostname) from semantic search so the API
-- can rank by how local a command is to the user's current context and show it.
-- Return type changes, so drop before recreate.
drop function if exists match_commands(uuid, vector, int);

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
  similarity float,
  cwd text,
  project text,
  hostname text
)
language sql stable
as $$
  select
    c.id, c.command, c.intent, c.explanation, c.complexity, c.skills,
    1 - (c.embedding <=> query_embedding) as similarity,
    c.cwd, c.project, c.hostname
  from commands c
  where c.user_id = p_user_id and c.embedding is not null
  order by c.embedding <=> query_embedding
  limit match_count;
$$;
