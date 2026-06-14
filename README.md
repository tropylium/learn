# `learn`

Teach yourself the terminal by reinforcing the commands you've actually used.
AI annotates each command, scores your learning, and lets you recall commands
semantically (`learn find "how do I pull a file from an old commit"`).

The core loop (log → annotate → embed → score → semantic-recall) works
end-to-end, with **email-OTP auth** and per-user rows behind Supabase RLS. See
`CLAUDE.md` for the full design.

## Layout

```
web/             Next.js app + API routes (AI proxy, auth, Supabase writer)
                 web/public/install.sh — the served `curl | sh` installer
cli/             Python CLI (login, log, find, here, score)
supabase/        schema.sql (fresh DB) · auth.sql (migrate an existing DB)
```

## Install (end users)

```sh
curl -LsSf https://learn-one-lac.vercel.app/install.sh | sh
```

The installer is a short, readable script ([web/public/install.sh](web/public/install.sh)):
it ensures `uv`, then `uv tool install`s the CLI from this public repo and writes
`~/.config/learn/config.json`. No bundled blobs — audit it before piping to `sh`.

## Setup

1. **Supabase schema**: create a project → SQL editor → run `supabase/schema.sql`
   (a fresh DB). It enables `pgvector`, creates the tables (`user_id` → `auth.users`),
   the `match_commands` / `skill_scores` RPCs, and RLS policies.
   - Migrating an existing vertical-slice DB instead? Run `supabase/auth.sql`.
2. **Email login (SMTP + template)** — required for `learn login` to send a code:
   - Configure **custom SMTP** (Supabase → Authentication → SMTP Settings).
     Supabase gates template editing behind custom SMTP, and the built-in sender
     is rate-limited. **Resend** free tier is quickest: create an API key, then in
     Supabase set Host `smtp.resend.com`, Port `465`, Username `resend`, Password
     `re_…`, Sender `onboarding@resend.dev`.
   - Edit **Authentication → Email Templates → Magic Link** to send a *code*, not
     a link — the body must include `{{ .Token }}` (default uses `{{ .ConfirmationURL }}`).
3. **Web env**: `cp web/.env.example web/.env.local` and fill in `SUPABASE_URL`,
   `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `ANTHROPIC_API_KEY`,
   `OPENAI_API_KEY`.
4. **Run the web app**: `cd web && npm run dev` (http://localhost:3000).
5. **Run the CLI**: `cd cli && uv sync`, then:
   ```
   uv run learn login            # email -> paste 6-digit code
   uv run learn log "grep -rEn 'TODO' --include='*.py' ."
   uv run learn find "search python files for a pattern with line numbers"
   uv run learn score
   ```
   The CLI talks to `http://localhost:3000` by default (override with
   `LEARN_API_URL` or `uv run learn config --api-url ...`). Tokens are stored in
   `~/.config/learn/auth.json`.

## Deploy (backend on Vercel)

The backend (`web/`) deploys to Vercel, wired to GitHub for **commit-based
auto-deploy**: every push to `main` ships a new deployment.

One-time setup in the Vercel dashboard:

1. **Add New → Project → Import** `tropylium/learn`.
2. **⚠️ Set Root Directory = `web`.** The Next.js app lives in `web/`, not the
   repo root — without this the build fails. (Expand *Root Directory* → Edit → `web`.)
3. Framework preset auto-detects **Next.js**; leave build/output defaults.
4. Add the same env vars as `web/.env.local` (copy the values): `SUPABASE_URL`,
   `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `ANTHROPIC_API_KEY`,
   `OPENAI_API_KEY`. Set them for **Production** (and Preview for PR deploys).
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

- Shell hook (`eval "$(learn shell-init)"`) for auto-logging + contextual reminders.
- Stripe Pro tier.
- (Deprioritized) Frontend dashboard — the CLI is the product.

Done: core log/find/here/score loop · Vercel deploy · email-OTP auth + RLS ·
hosted `curl | sh` installer + landing page.
