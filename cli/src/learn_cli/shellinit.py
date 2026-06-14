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
# learn shell integration (bash) — best effort via DEBUG trap
__learn_hist=()
__learn_record() {
  local c="$BASH_COMMAND"
  case "$c" in
    learn|learn\ *|__learn_*) return ;;
  esac
  __learn_hist+=("$c")
  (( ${#__learn_hist[@]} > 50 )) && __learn_hist=("${__learn_hist[@]: -50}")
}
trap '__learn_record' DEBUG
learn() {
  if [[ "$1" == "log" ]]; then
    local IFS=$'\n'
    LEARN_SESSION_HISTORY="${__learn_hist[*]}" command learn "$@"
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
