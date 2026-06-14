"""Read recent commands run in the current shell session.

Preferred source: the LEARN_SESSION_HISTORY env var, populated by the shell
integration (`learn shell-init`). It holds this session's commands, newline-
separated — accurate and session-scoped.

Fallback (no shell integration): the history *file* (~/.zsh_history etc). This
is unreliable — it's global across all sessions, not scoped to this terminal,
and may not be flushed yet. Install shell integration for correct behavior.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# zsh extended-history line prefix: ": <start>:<elapsed>;<command>"
_ZSH_PREFIX = re.compile(r"^: \d+:\d+;")
# Our own invocations — never log these.
_OWN = re.compile(r"^\s*learn(\s|$)")


def _history_file() -> Path | None:
    hf = os.environ.get("HISTFILE")
    if hf and Path(hf).expanduser().exists():
        return Path(hf).expanduser()
    home = Path.home()
    shell = os.environ.get("SHELL", "")
    candidates = []
    if "zsh" in shell:
        candidates = [home / ".zsh_history"]
    elif "bash" in shell:
        candidates = [home / ".bash_history"]
    else:
        candidates = [home / ".zsh_history", home / ".bash_history"]
    for c in candidates:
        if c.exists():
            return c
    return None


def integration_active() -> bool:
    """True if shell integration populated this session's history."""
    return os.environ.get("LEARN_SESSION_HISTORY") is not None


def _filter(cmds: list[str], n: int) -> list[str]:
    out = [c for c in (x.strip() for x in cmds) if c and not _OWN.match(c)]
    return out[-n:] if n > 0 else []


def recent_commands(n: int) -> list[str]:
    """Return the last `n` non-`learn` commands from this session, oldest→newest.

    Uses LEARN_SESSION_HISTORY (from shell integration) when present — even if
    empty, that means shell integration is active and there's simply no history
    yet, so we do NOT fall back to the global file. Only when the var is unset
    do we read the (unreliable) history file.
    """
    env_hist = os.environ.get("LEARN_SESSION_HISTORY")
    if env_hist is not None:
        return _filter(env_hist.splitlines(), n)

    f = _history_file()
    if not f:
        return []
    try:
        lines = f.read_text(errors="replace").splitlines()
    except OSError:
        return []
    return _filter([_ZSH_PREFIX.sub("", line) for line in lines], n)
