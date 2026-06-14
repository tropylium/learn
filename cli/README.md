# `learn` CLI

Teach yourself the terminal by reinforcing the commands you've actually used.

## Install

```sh
uv sync
```

Commands run via `uv run learn ...`. The CLI talks to `http://localhost:3000` by
default — override with `LEARN_API_URL` or `uv run learn config --api-url ...`.

## Commands

| Command | What it does |
|---|---|
| `learn log "<cmd>"` | Log a command — it gets annotated, embedded, scored, and stored. |
| `learn find "<query>"` | Semantic recall: describe what you want, get back a command you've used. |
| `learn here` | Commands you've logged in the current project. |
| `learn score` | XP per skill and total. |
| `learn config` | View or set local config (API URL). |

## Example flow

```sh
# 1. Log a command you just figured out
$ uv run learn log "grep -rEn 'TODO' --include='*.py' ."
✓ logged: grep -rEn 'TODO' --include='*.py' .
  intent:     Recursively search Python files for a pattern, with line numbers
  skills:     text-processing, grep
  complexity: 3/5
  +30.0 XP

# 2. A week later, you forgot the exact flags. Ask in plain English:
$ uv run learn find "search python files for some text and show line numbers"
1. grep -rEn 'TODO' --include='*.py' .   (91% match)
   Recursively search Python files for a pattern, with line numbers
   Searches recursively (-r), shows line numbers (-n), uses extended regex (-E),
   and restricts to .py files via --include.

# 3. Check your progress
$ uv run learn score
Total XP: 30.0
  text-processing            30.0 XP
  grep                       30.0 XP
```

## What happens behind the scenes

**`learn log`** — The CLI detects local context (hostname, git project, cwd) and
`POST`s the command to `/api/log`. The server:

1. Checks whether you've logged this exact command before (per-user).
2. If it's **new**: calls **Claude Haiku** to annotate it — producing a plain-English
   *intent*, an explanation, a 1–5 *complexity* rating, and *skill* tags — via
   structured JSON output so the fields are guaranteed parseable. It then embeds
   `intent + command` with **OpenAI `text-embedding-3-small`** (1536-dim vector)
   and writes a row to the `commands` table in **Supabase Postgres** (with
   `pgvector`).
3. Scores this use as `novelty × complexity × spacing` — novelty decays ~10→1
   over the first ~10 uses, spacing rewards reuse spread over time — and records
   it in `command_uses`. Annotation/embedding are skipped on repeat commands, so
   re-logging is cheap.

**`learn find`** — The CLI sends your natural-language query to `/api/find`. The
server embeds the query with the same model, then runs the `match_commands`
pgvector RPC (cosine distance, scoped to your user) to return the nearest
commands from *your own* history — ranked by semantic similarity, not keyword
match. This is why "pull a file from an old commit" can surface a
`git checkout <sha> -- <file>` you ran weeks ago.

**`learn score` / `learn here`** — Read-only aggregations: `score` sums
`points_awarded` per skill via the `skill_scores` RPC; `here` lists the commands
stored for your current git project.

> **Note (vertical slice):** there's no auth yet — the CLI uses a hardcoded dev
> user id. Real auth (`learn login`) is a later milestone.
