# `learn` CLI

Teach yourself the terminal by reinforcing the commands you've actually used.

## Install

End users:

```sh
curl -LsSf https://learn-one-lac.vercel.app/install.sh | sh
```

This installs the CLI (isolated, via `uv tool`), points it at the API, and adds
shell integration to your rc so `learn log` can see your current session.

Development (from this repo):

```sh
uv sync           # then run via `uv run learn ...`
```

The CLI talks to `http://localhost:3000` by default — override with
`LEARN_API_URL` or `learn config --api-url ...`.

## Commands

| Command | What it does |
|---|---|
| `learn login` | Sign in via a one-time code emailed to you. |
| `learn log [cmd]` | Log a command. No argument → your last shell command; `-n 5` → last 5. |
| `learn find` | Interactive search of your history (substring + semantic). |
| `learn here` | Commands you've logged in the current project. |
| `learn score` | How many commands you've logged, per skill and total. |
| `learn shell-init` | Print shell integration (installer adds this automatically). |
| `learn whoami` / `learn logout` | Show / clear the signed-in account. |
| `learn config` | View or set local config (API URL). |

## Example flow

```sh
# 1. Sign in (one-time code by email)
$ learn login
Email: you@example.com
Code: 123456
✓ signed in as you@example.com

# 2. Run a command, then log it — no retyping
$ grep -rEn 'TODO' --include='*.py' .
$ learn log
✓ logged: grep -rEn 'TODO' --include='*.py' .  (used 1×)
  intent: Recursively search Python files for a pattern, with line numbers
  skills: text-processing, grep

# 3. Later, search your history interactively (type to filter, Enter to pick)
$ learn find
find ❯ search python
❯ grep -rEn 'TODO' --include='*.py' .
    Recursively search Python files for a pattern, with line numbers

# 4. Check your progress
$ learn score
Commands logged: 1
  text-processing              1×
  grep                         1×
```

## What happens behind the scenes

**Commands are grouped by *signature*.** The CLI normalizes each command to a
signature — program + subcommand + flags, with argument *values* dropped — so
`git commit -m "a"` and `git commit -m "b"` are the same thing used twice, while
`git commit` and `git push` stay distinct. The stored command is the most recent
literal invocation (so recall still shows what you actually typed).

**`learn log`** detects local context (hostname, git project, cwd) and `POST`s to
`/api/log`. The server:

1. Looks up the signature for your account.
2. If it's **new**: calls **Claude Haiku** to annotate it — a plain-English
   *intent*, an *explanation*, a 1–5 *complexity*, and *skill* tags (structured
   JSON output) — embeds `intent + command` with **OpenAI `text-embedding-3-small`**
   (1536-dim) and stores it in **Supabase Postgres** (`pgvector`).
   Annotation/embedding are skipped for signatures you've already logged.
3. Records the use. Scoring is a simple **count of uses** per skill.

With no argument, `learn log` reads the **current session's** last command(s)
from shell integration (see below); `learn log "<cmd>"` logs an explicit one.

**`learn find`** is an interactive TUI with two-phase search: instant substring/
prefix matches per keystroke (`/api/search`, ILIKE + trigram index), then
debounced **semantic** matches (`/api/find` → embed the query → `match_commands`
pgvector cosine search over *your* history). Up/Down to move, Enter to pick
(prints the command), Esc/Ctrl-C to cancel. This is why "pull a file from an old
commit" can surface a `git checkout <sha> -- <file>` you ran weeks ago.

**`learn score` / `learn here`** — read-only aggregations: `score` counts uses
per skill (`skill_counts` RPC); `here` lists commands stored for your current
git project.

## Shell integration

`learn log` with no argument needs the **current terminal session's** last
command — but `~/.zsh_history` is shared across *all* sessions and isn't reliably
flushed. Shell integration fixes this: a zsh `preexec` hook / bash `DEBUG` trap
records this session's commands (ignoring `learn` itself) and hands them to the
CLI via `LEARN_SESSION_HISTORY`.

The installer adds it to your rc automatically. To set it up manually:

```sh
eval "$(learn shell-init)"        # add to ~/.zshrc or ~/.bashrc
```

Without it, `learn log` falls back to reading the history file (unreliable;
prefer an explicit `learn log "<cmd>"`). zsh is fully supported; bash is
best-effort.

## Auth & config

`learn login` stores session tokens in `~/.config/learn/auth.json` (chmod 600);
requests send a Bearer token and refresh automatically on expiry. Non-secret
settings (the API URL) live in `~/.config/learn/config.json`.
