"""Shell integration snippets emitted by `learn shell-init`.

The integration does two things in your interactive shell:

  1. Records each command you run *this session* into an in-memory list (a
     zsh preexec hook / bash DEBUG trap), skipping `learn` invocations.
  2. Wraps `learn` so that `learn log` (no explicit command) passes that
     session history to the binary via LEARN_SESSION_HISTORY.

This is what makes `learn log` capture the current terminal's last command —
the global ~/.zsh_history file can't be scoped to one session.

Installed automatically by the installer (a guarded block in your rc that runs
`eval "$(learn shell-init)"`); also printable manually.
"""

from __future__ import annotations

import os
from pathlib import Path

# Delimiters of the block the installer adds to the user's rc. Must stay in sync
# with web/public/install.sh so `learn uninstall` can strip the exact block.
RC_MARKER_START = "# >>> learn shell integration >>>"
RC_MARKER_END = "# <<< learn shell integration <<<"

_ZSH = r"""
# learn shell integration (zsh)
typeset -ga __learn_hist
autoload -Uz add-zsh-hook
__learn_record() {
  case "$1" in
    (learn|learn' '*) return ;;
  esac
  __learn_hist+=("$1")
  (( ${#__learn_hist} > 50 )) && __learn_hist=(${__learn_hist[-50,-1]})
}
add-zsh-hook preexec __learn_record
learn() {
  if [[ "$1" == "log" ]]; then
    LEARN_SESSION_HISTORY="${(F)__learn_hist}" command learn "$@"
  else
    command learn "$@"
  fi
}
"""

_BASH = r"""
# learn shell integration (bash)
# `learn log` reads this session's command history via the `history` builtin.
# Unlike a DEBUG trap, the history list excludes prompt machinery (e.g. a
# PROMPT_COMMAND that sets the terminal title), so it never logs those.
learn() {
  if [[ "$1" == "log" ]]; then
    local _lh
    _lh=$(builtin history 50 2>/dev/null \
          | sed 's/^[[:space:]]*[0-9]*[[:space:]]*//' \
          | grep -vE '^[[:space:]]*learn([[:space:]]|$)')
    LEARN_SESSION_HISTORY="$_lh" command learn "$@"
  else
    command learn "$@"
  fi
}
"""


def detect_shell(name: str | None = None) -> str:
    if name:
        return name.lower()
    shell = os.environ.get("SHELL", "")
    if "bash" in shell:
        return "bash"
    return "zsh"  # default


def render(name: str | None = None) -> str:
    shell = detect_shell(name)
    if shell == "bash":
        return _BASH.strip()
    if shell == "zsh":
        return _ZSH.strip()
    raise ValueError(f"unsupported shell: {shell} (supported: zsh, bash)")


def _rc_candidates() -> list[Path]:
    home = Path.home()
    zdot = os.environ.get("ZDOTDIR")
    paths = [home / ".zshrc", home / ".bashrc"]
    if zdot:
        paths.insert(0, Path(zdot) / ".zshrc")
    return paths


def remove_from_rc() -> list[Path]:
    """Strip the guarded shell-integration block from known rc files.

    Returns the list of files actually modified.
    """
    modified: list[Path] = []
    for rc in _rc_candidates():
        if not rc.exists():
            continue
        try:
            lines = rc.read_text().splitlines()
        except OSError:
            continue
        if not any(RC_MARKER_START in ln for ln in lines):
            continue

        out: list[str] = []
        skipping = False
        for ln in lines:
            if RC_MARKER_START in ln:
                skipping = True
                # drop a single blank line that precedes the block, if any
                if out and out[-1].strip() == "":
                    out.pop()
                continue
            if RC_MARKER_END in ln:
                skipping = False
                continue
            if not skipping:
                out.append(ln)

        rc.write_text("\n".join(out) + ("\n" if out else ""))
        modified.append(rc)
    return modified
