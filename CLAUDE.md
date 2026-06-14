# `learn` — Hackathon Project Brief

A one-day hackathon project. A CLI tool that helps you actually *learn* terminal commands by logging what you run, annotating it with AI, scoring your progress, and surfacing commands semantically when you need them again.

**Status:** Pre-implementation. Brainstorming captured here; nothing is final. Continue the conversation freely — the decisions below are starting points, not constraints.

---

## The Motivation (in my own words)

I have years of programming experience but I'm not fluent in the terminal beyond basic commands, and even on basic commands I often don't know less common flags. When I use AI agents like Claude Code or Cursor, I see them invoke commands and flags I'd like to learn for myself — but without something actively reinforcing those, I have no incentive to actually internalize them. Existing AI shell tools do everything *for* you; I want one that nudges me toward doing it myself.

The pitch in one line: **an AI-powered tool that teaches you the terminal by reinforcing the commands you've used, scoped to the contexts where they matter.**

---

## Prior Art — What Exists, What Doesn't

We searched and found nothing that hits the full intersection. The closest neighbors:

- **ShellSage (Answer.AI)** — closest in spirit. Uses tmux capture-pane to "see" your terminal and teaches rather than tells. *Gap:* only knows current session context; doesn't accumulate knowledge across sessions or projects.
- **Shell History MCP Server (rajpdus)** — exposes shell history to MCP clients. *Gap:* it's a searchable history *for the AI*, not a learning loop for the user.
- **Atuin / McFly** — modern shell history with sync and search. *Gap:* not a learning tool; no annotation, no skill model, no reinforcement.
- **Clanki / Vinca / various Anki-style CLIs** — spaced repetition in the terminal. *Gap:* require manual card creation, don't read history, no AI.
- **GitHub Copilot CLI / ShellGPT / Warp AI** — generate commands from natural language. *Gap:* opposite philosophy — they replace learning rather than support it.

The novel combination we're aiming at: **history-aware + AI-annotated + context-scoped + gamified reinforcement.**

---

## Core Concepts / Vocabulary

These are the mental model atoms. Useful to share with anyone (including future Claude Code sessions) so terminology stays consistent.

- **Command** — a literal shell command string, e.g. `grep -rEn "pattern" .`
- **Intent / Goal** — what the user was trying to *do*. "Recursively search Python files for a pattern, with line numbers." The unit of knowledge is really `intent ↔ command`, not the command alone.
- **Skill** — a named cluster of related intents/commands. Examples: "Text processing (grep/awk/sed)", "Slurm job management", "Git history surgery", "Process inspection".
- **Context** — *where* and *why* a command was used. Two orthogonal axes:
  - *Location:* hostname + project (git root, or manually set) + cwd
  - *Intent:* what the user was trying to do (captured semantically via embeddings)
- **Annotation** — AI-generated metadata about a command: explanation, complexity score, skill tags, intent description.
- **XP / Score** — gamified measure of learning progress, computed per-skill and globally.

---

## Stack

Hackathon organizers recommend (all generous free tiers):

- **Vercel** — frontend deployment + API routes (the proxy for AI calls)
- **Supabase** — Postgres (with `pgvector`), auth, RLS
- **Stripe** — payments / monetization

Plus:

- **Frontend:** Next.js + Tailwind + shadcn/ui (judgment call — GitHub Pages works for pure static, but we want API routes for the AI proxy and auth flow)
- **CLI:** Python + `click` + `httpx`. Stores token in `~/.config/learn/`.
- **AI:** Claude Haiku for annotation (cheap, fast, good enough). Embeddings via OpenAI `text-embedding-3-small` or Voyage.

---

## Architecture Decisions (with the reasoning behind them)

Each of these was discussed and could be reopened.

### 1. What context do we capture, and how?

Considered:
- **Option 1 — Read history files** (`~/.bash_history`, `~/.zsh_history`). Trivially easy. Misses exit codes, output, cwd.
- **Option 2 — Shell hooks** (zsh `preexec`/`precmd`, bash `trap DEBUG`+`PROMPT_COMMAND`). Captures command, cwd, hostname, exit code, duration. ~30-50 lines of shell.
- **Option 3 — Full session capture** (tmux `capture-pane`, `script`, asciinema). Gets output too. Invasive, noisy.
- **Option 4 — Piggyback on Atuin.** Less work, but adds an install dependency.

**Decision for v1:** Option 1 as default (zero-setup), Option 2 as a stretch goal (`eval "$(learn shell-init)"`).

**Not capturing output** — for a learning tool, the command is the unit, not its output. Exception worth considering later: capture stderr when `exit_code != 0` (failures are the best learning opportunities).

**Gotcha:** zsh/bash don't flush history until shell exit by default. Either require `INC_APPEND_HISTORY` / `PROMPT_COMMAND='history -a'` in setup, or go straight to hooks for demo.

### 2. Who pays for AI calls?

Considered:
- **A — BYOK (user provides API key).** Simplest; zero infra cost; no risk. Adds friction.
- **B — We proxy through Vercel using our key.** Best UX; tiny cost at demo scale; need to rate-limit + spend-cap.
- **C — Hybrid.** Free tier on our key (e.g. 50 annotations/mo), Pro tier unlocks more, BYOK option for power users.

**Decision for hackathon:** Option B for the demo. Mention Option C in the pitch as the monetization story (gives Stripe a real reason to exist).

Notes for the proxy:
- Hard spend cap in Anthropic console (belt and suspenders)
- Per-user rate limit in Supabase (10 min to add)
- **Cache annotations by command string** — major argument for B over A. Annotating `git status` once and reusing across all users is both cheaper and faster. This is a real architectural advantage worth mentioning in the pitch.

### 3. Scoring / gamification design

The design principle: reward *learning*, not raw usage. Three forces in tension:

- **Novelty matters early, repetition mid-game.** First use of `grep -P` is worth a lot; tenth use is worth ~1 point.
- **Complexity matters.** Bare `grep foo file.txt` < `grep -rEn --include="*.py" "pattern" .`. AI provides a 1-5 complexity score at annotation time.
- **Spaced reuse beats burst reuse.** Using `sbatch --array` once a day for a week > 7 times in 10 minutes.

Formula sketch:
```
points = novelty_bonus × complexity_score × spacing_multiplier
```
where novelty decays from ~10 → ~1 over the first 10 uses, complexity is 1-5 from AI, spacing_multiplier is `min(1.0, hours_since_last_use / 24)` or similar.

**Skill trees:** AI tags each command with one or more skills at annotation time. XP accumulates per skill. Gives the dopamine loop a structure ("I'm level 4 in Slurm, level 1 in awk").

**Streaks / decay / challenges:** mentioned but not committed for v1.
- Daily streak for ≥1 non-trivial command logged
- Forgotten-skill decay (high-level skill not used in 30 days starts losing XP)
- AI-generated weekly challenge based on commands logged but not mastered

**Anti-gaming:** Soft cap (same exact command max 3x/day). Don't over-engineer — this is for the user themselves.

**Leaderboards:** Per-skill global leaderboard across users. Cheap given the stack. Strong demo moment ("look, I'm #2 globally in awk this week").

### 4. The intent / vector layer

Late addition to the design but probably the most important architectural insight.

**Reframe:** The atoms of learning aren't commands, they're `intent → command` mappings. "Restore a file from an old commit" is the *thing being learned*; `git checkout <commit> -- <file>` is just the syntax that realizes it.

Two things this unlocks:

1. **Semantic recall.** `learn find "how do I pull a file from an old commit"` returns the right command from the user's own history. This is *the* killer demo moment — the user types in plain English what they're trying to do, and gets back a command they themselves used before.

2. **Better novelty scoring.** At log time, embed the annotated intent. If close to an existing intent in the user's history, this is a reuse (not novelty). If far from everything, congratulations, you learned something new. The XP system gets a real signal instead of just "have I run this exact string."

Implementation: `pgvector` is built into Supabase. Add `embedding vector(1536)` to `commands`. Embedding call alongside annotation call. ~90 minutes of total additional work.

**Do not visualize the clusters in the UI** for the demo. The vector layer should be invisible infrastructure powering `learn find` and scoring.

### 5. Auth flow

Supabase Auth (GitHub/Google OAuth). For the CLI:

- `learn login` opens a browser to a Vercel-hosted page
- User signs in via Supabase Auth there
- Page either displays a token to paste back, *or* redirects to a localhost callback that the CLI is listening on (fancier; cleaner UX)
- CLI stores token in `~/.config/learn/`

If the localhost callback is too much yak-shaving for one day, the paste-back flow is ugly but ~20 min of work.

### 6. Frontend scope

Minimum viable for demo:
- Landing page with "Sign in with GitHub"
- Post-login dashboard: XP per skill, recent commands, leaderboard
- Token-display page for CLI login flow
- Pricing page + Stripe Checkout button (if including Stripe)

Next.js + Tailwind + shadcn/ui can produce something that looks legit in a few hours.

### 7. Stripe — include or skip?

Organizer recommendation says yes. Minimal-effort path: a Pro tier that unlocks something marginal — unlimited annotations, private leaderboards with friends, AI-generated weekly challenges. Stripe Checkout (hosted) + webhook to flip a `subscription_active` flag. ~1-2 hours if it goes well.

Honestly this is the most cuttable piece if time runs short. If we keep it, it should *back* the monetization story for Option C in §2.

---

## Schema Sketch

Not committed; iterate freely.

```
-- Managed by Supabase Auth
users (id, email, ...)

commands (
  id uuid primary key,
  user_id uuid references users,
  command text,
  intent text,                 -- AI-generated, e.g. "Restore a file from a previous commit"
  explanation text,            -- AI-generated longer explanation
  complexity int,              -- 1-5, AI-rated
  skills text[],               -- AI-tagged, e.g. ['git', 'history-surgery']
  embedding vector(1536),      -- of intent or intent+command
  hostname text,
  project text,                -- git root name or manual override
  cwd text,
  first_used_at timestamptz,
  created_at timestamptz default now()
)

command_uses (
  id uuid primary key,
  command_id uuid references commands,
  used_at timestamptz,
  exit_code int,               -- if hook-based
  points_awarded numeric
)

-- maybe later
skills_meta (name text primary key, description text, ...)
subscriptions (user_id, stripe_customer_id, active bool, ...)
```

RLS: each user sees only their own `commands` and `command_uses`. Leaderboard reads happen via a view or RPC that aggregates without exposing per-user details.

---

## The Demo Flow (build toward this)

90 seconds. The story is "the system helps me remember commands I've actually used."

1. Live `cd` into a slurm project → contextual shell hook fires: *"3 slurm commands you logged — `learn here` to review."*
2. Run a real `sbatch` invocation → background log + annotate + embed + skill-classify.
3. Show the dashboard: XP bars rising, command appearing under "Slurm job management" skill.
4. **The reveal:** `learn find "submit a job that requires a GPU"` → returns the exact `sbatch` from step 2 with its annotation.
5. Show the leaderboard, mention Stripe Pro tier monetization.

Build features in the order that supports this demo, not in order of "importance."

---

## What's Cut for v1

- **Quiz feature.** Replaced by `learn find` as the recall moment; tells the same story more vividly.
- **MCP server.** Easy to add post-hackathon; not needed for the demo.
- **Output capture.** Not worth the complexity. Maybe stderr-on-failure later.
- **Multi-device sync UI.** Implicit in having a backend; no UI surface.
- **Visualizing intent clusters.** Rabbit hole.
- **Forgotten-skill decay / streaks / challenges.** Mention in pitch, build later.
- **BYOK flow.** Mention in pitch, build later.

---

## Time Boxing (current plan)

- **0-2h** — Foundation. Supabase project, schema, RLS. Next.js on Vercel with hello-world deployed and connected.
- **2-4h** — Auth end-to-end. Browser sign-in works. Token-display works. CLI `learn login` / `learn whoami` work.
- **4-7h** — Core logging + scoring. `learn log [cmd]` → Vercel API route → Anthropic annotation + embedding → Supabase write. `learn here`, `learn score`, `learn find`.
- **7-9h** — Frontend dashboard. XP bars, recent commands, leaderboard.
- **9-10h** — Stripe (if included). Checkout link, webhook, gated feature.
- **10-12h** — Polish + demo prep. Shell hook for context reminder (high-value demo moment). Copy, logo, tagline, 90-second script.

---

## Open Questions / Spitballed Ideas to Revisit

These came up in conversation and weren't resolved. Worth re-exploring as time allows.

- **Granularity of "project."** Git root works for code projects. What about non-code contexts (a slurm cluster login session with no git repo)? Probably: hostname as fallback, with manual override via `learn log --project foo`.
- **Project auto-naming.** Use directory name? Git remote name? AI inference? Probably git remote → directory name → manual.
- **Cross-user annotation sharing.** If two users log `git checkout <commit> -- <file>`, do they share the annotation? Probably yes (cache by normalized command), but it raises a privacy question for commands with sensitive args. Maybe normalize args out for the cache key.
- **Argument normalization.** `grep "foo" file.txt` and `grep "bar" other.txt` are the same *skill*. The annotation/skill classification should treat them as one; the use counter should too. Argument-stripped command as a secondary key?
- **"Tutor mode."** Instead of just annotating commands the user ran, proactively suggest commands they haven't yet learned in their current context. E.g. "you `cd`'d into a git repo with conflicts — want to learn `git mergetool`?" Risky (could be annoying); compelling (this is the actual *teaching* axis).
- **Failure-driven learning.** Captured `exit_code != 0` events become priority learning items. "You tried `grep -P` on macOS and it failed — here's why and the workaround."
- **Personal vs. shared skill trees.** The skill ontology could be user-specific (emerges from their usage) or curated (shared across users). Curated probably wins for leaderboards.
- **Decay rate for the spacing multiplier.** 24h is arbitrary. Worth tuning based on what feels right in practice.

---

## Working with Me

- I think out loud and brainstorm freely. Push back on ideas that seem off. Nothing in this doc is final until it's built.
- I prefer concrete next steps over abstract planning at this point. We've done enough planning; let's start building.
- When suggesting architecture changes, frame them as "we considered X, going with Y because Z" — preserves the option to revisit.
- Hackathon time pressure is real. When in doubt, cut scope rather than rush quality.
