"""Read recent commands from the user's shell history (zero-setup logging).

Caveat: shells don't always flush history immediately. zsh with
SHARE_HISTORY / INC_APPEND_HISTORY (oh-my-zsh default) and bash with
PROMPT_COMMAND='history -a' write as you go; otherwise the most recent command
may not be on disk until the shell exits. The shell hook (later milestone)
removes this limitation.
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


def recent_commands(n: int) -> list[str]:
    """Return the last `n` distinct-from-`learn` commands, oldest→newest."""
    f = _history_file()
    if not f:
        return []
    try:
        lines = f.read_text(errors="replace").splitlines()
    except OSError:
        return []

    cmds: list[str] = []
    for line in lines:
        cmd = _ZSH_PREFIX.sub("", line).strip()
        if cmd and not _OWN.match(cmd):
            cmds.append(cmd)
    return cmds[-n:] if n > 0 else []
