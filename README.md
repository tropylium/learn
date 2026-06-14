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

## Deploy (backend on Vercel)

The backend (`web/`) deploys to Vercel, wired to GitHub for **commit-based
auto-deploy**: every push to `main` ships a new deployment.

One-time setup in the Vercel dashboard:

1. **Add New → Project → Import** `tropylium/learn`.
2. **⚠️ Set Root Directory = `web`.** The Next.js app lives in `web/`, not the
   repo root — without this the build fails. (Expand *Root Directory* → Edit → `web`.)
3. Framework preset auto-detects **Next.js**; leave build/output defaults.
4. Add the same env vars as `web/.env.local` (copy the values):
   `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`.
   Set them for **Production** (and Preview if you want PR deploys to work).
5. **Deploy.** From then on, `git push` to `main` auto-deploys.

Notes:
- The build succeeds even if an env var is missing — env access is lazy/runtime,
  so a misconfigured key surfaces as a request-time error, not a failed build.
- Normal dev loop stays local: run `npm run dev` and point the CLI at
  `http://localhost:3000`. Only push to `main` when you want the deployed
  backend to update.
- To test the CLI against the deployed backend:
  `learn config --api-url https://<your-deployment>.vercel.app`
  (switch back with `--api-url http://localhost:3000`).

## Next milestones

- **Auth + per-user rows** (next): email-OTP CLI login (`learn login`) +
  Supabase RLS so each user only sees their own commands.
- Installer hosting: serve `dist/install.sh` from the web app (`curl … | sh`).
- Shell hook (`eval "$(learn shell-init)"`) for auto-logging + contextual reminders.
- Stripe Pro tier.
- (Deprioritized) Frontend dashboard — the CLI is the product.
