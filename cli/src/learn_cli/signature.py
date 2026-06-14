"""Normalize a command into a *signature* — the unit we count and group by.

Rule (deterministic, no LLM):
  signature = program + subcommand + sorted unique flag-names

- argument *values* are dropped (flag values and operands), so
  `git commit -m "a"` and `git commit -m "b"` share a signature.
- flags are order-independent (sorted) and de-duplicated.
- for known sub-command multiplexers (git, docker, …) the first positional is
  kept as the subcommand; for everything else all positionals are dropped, so
  `grep "foo" a` and `grep "bar" b` share a signature.
- bundled short flags (`-rEn`) are kept as-typed (not split).
"""

from __future__ import annotations

import shlex

# Programs whose first positional is a meaningful subcommand, not an operand.
_MULTIPLEXERS = {
    "git", "gh", "hub", "docker", "docker-compose", "podman", "kubectl", "helm",
    "npm", "yarn", "pnpm", "bun", "deno", "pip", "pip3", "uv", "pipx", "poetry",
    "conda", "cargo", "rustup", "go", "gem", "bundle", "rails", "composer",
    "dotnet", "brew", "apt", "apt-get", "dnf", "yum", "pacman", "systemctl",
    "service", "make", "just", "task", "aws", "gcloud", "az", "terraform",
    "vagrant", "heroku", "fly", "flyctl", "supabase", "vercel", "wrangler",
    "tmux", "git-lfs", "pre-commit", "nix", "ip", "tsc",
}

_SKIP_PREFIXES = {"sudo", "env", "command", "exec", "nice", "nohup", "time"}


def command_signature(command: str) -> str:
    command = command.strip()
    if not command:
        return command
    try:
        toks = shlex.split(command)
    except ValueError:
        toks = command.split()
    if not toks:
        return command

    # Drop leading wrappers like `sudo` / `env`.
    while toks and toks[0] in _SKIP_PREFIXES:
        toks = toks[1:]
    if not toks:
        return command

    prog = toks[0]
    flags: list[str] = []
    positionals: list[str] = []
    seen_flag = False
    for t in toks[1:]:
        if t.startswith("-") and t != "-":
            flags.append(t.split("=", 1)[0])
            seen_flag = True
        elif not seen_flag:
            positionals.append(t)
        # operands (after a flag, or "-") are dropped

    subcmds = positionals[:1] if (prog in _MULTIPLEXERS and positionals) else []
    return " ".join([prog, *subcmds, *sorted(set(flags))])


def _split(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


# Token kinds used by `learn practice` to build the fill-in skeleton + matching.
PROGRAM = "program"
SUBCOMMAND = "subcommand"
FLAG = "flag"
OPERAND = "operand"


def classify_tokens(command: str) -> list[tuple[str, str]]:
    """Return [(token, kind)] for a command. Mirrors command_signature's rules:
    program first, one subcommand for known multiplexers, flags, operands."""
    toks = _split(command)
    while toks and toks[0] in _SKIP_PREFIXES:
        toks = toks[1:]
    if not toks:
        return []

    out: list[tuple[str, str]] = [(toks[0], PROGRAM)]
    is_mux = toks[0] in _MULTIPLEXERS
    seen_flag = False
    took_sub = False
    for t in toks[1:]:
        if t.startswith("-") and t != "-":
            out.append((t, FLAG))
            seen_flag = True
        elif not seen_flag and is_mux and not took_sub:
            out.append((t, SUBCOMMAND))
            took_sub = True
        else:
            out.append((t, OPERAND))
    return out
