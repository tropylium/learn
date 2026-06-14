# `learn`

Teach yourself the terminal by reinforcing the commands you've actually used.
AI annotates each command, scores your learning, and lets you recall commands
semantically (`learn find "how do I pull a file from an old commit"`).

This repo currently implements the **vertical slice**: the core
log → annotate → embed → score → semantic-recall loop, with a hardcoded dev
user (no auth yet). See `CLAUDE.md` for the full design.

## Layout

```
web/        Next.js app + API routes (the AI proxy + Supabase writer)
cli/        Python CLI (`learn log`, `learn find`, `learn here`, `learn score`)
supabase/   schema.sql — run in the Supabase SQL editor
```

## Setup (vertical slice)

1. **Supabase**: create a project, open the SQL editor, run `supabase/schema.sql`
   (enables `pgvector`, creates tables + the `match_commands` / `skill_scores` RPCs).
2. **Web env**: `cp web/.env.example web/.env.local` and fill in Supabase URL +
   service-role key, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`.
3. **Seed the dev user**: in the SQL editor, the dev user_id is
   `00000000-0000-0000-0000-000000000001` — no row needed (no FK to auth in v1).
4. **Run the web app**: `cd web && npm run dev` (http://localhost:3000).
5. **Run the CLI**: `cd cli && uv sync`, then:
   ```
   uv run learn log "grep -rEn 'TODO' --include='*.py' ."
   uv run learn find "search python files for a pattern with line numbers"
   uv run learn score
   uv run learn here
   ```
   The CLI talks to `http://localhost:3000` by default (override with
   `LEARN_API_URL` or `uv run learn config --api-url ...`).

## Next milestones

- Real auth (Supabase OAuth + CLI `learn login`)
- Frontend dashboard (XP bars, recent commands, leaderboard)
- Shell hook (`eval "$(learn shell-init)"`) for contextual reminders
- Stripe Pro tier
