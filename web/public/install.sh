#!/bin/sh
# learn — installer
#
#   curl -LsSf https://learn-one-lac.vercel.app/install.sh | sh
#
# No magic — read it top to bottom. This script:
#   1. ensures `uv` is installed            (https://astral.sh/uv)
#   2. installs the `learn` CLI from the public repo, isolated, onto your PATH:
#        uv tool install git+https://github.com/tropylium/learn#subdirectory=cli
#   3. writes ~/.config/learn/config.json pointing at the API
#
# Overrides (optional):
#   LEARN_API_URL     API base URL          (default below)
#   LEARN_REF         git branch/tag to install (default: main)
#   LEARN_CONFIG_DIR  config dir            (default: ~/.config/learn)
set -eu

API_URL="${LEARN_API_URL:-https://learn-one-lac.vercel.app}"
REPO="https://github.com/tropylium/learn"
REF="${LEARN_REF:-main}"
CONFIG_DIR="${LEARN_CONFIG_DIR:-$HOME/.config/learn}"

info() { printf '\033[1;36m=>\033[0m %s\n' "$1"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$1" >&2; }
err()  { printf '\033[1;31merror:\033[0m %s\n' "$1" >&2; exit 1; }

command -v curl >/dev/null 2>&1 || err "curl is required."
command -v git  >/dev/null 2>&1 || err "git is required (uv installs the CLI from a git repo)."

# 1. ensure uv
if ! command -v uv >/dev/null 2>&1; then
  info "Installing uv (https://astral.sh/uv) …"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  [ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env" || true
  export PATH="$HOME/.local/bin:$PATH"
  command -v uv >/dev/null 2>&1 || err "uv install failed; see https://docs.astral.sh/uv/"
fi

# 2. install the learn CLI from the public repo (isolated env, placed on PATH)
info "Installing the 'learn' CLI from $REPO (@$REF) …"
uv tool install --force "git+$REPO@$REF#subdirectory=cli"
uv tool update-shell >/dev/null 2>&1 || true

# 3. point the CLI at the API
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_DIR/config.json" <<EOF
{
  "api_url": "$API_URL"
}
EOF
info "API URL set to $API_URL  ($CONFIG_DIR/config.json)"

# 4. shell integration — lets `learn log` capture the current session's last
#    command. Adds a guarded block to your rc. Opt out with LEARN_NO_SHELL_INIT=1.
install_shell_integration() {
  [ -n "${LEARN_NO_SHELL_INIT:-}" ] && { info "Skipping shell integration (LEARN_NO_SHELL_INIT set)."; return; }
  rc=""
  case "$(basename "${SHELL:-}")" in
    zsh)  rc="${ZDOTDIR:-$HOME}/.zshrc" ;;
    bash) rc="$HOME/.bashrc" ;;
    *)    warn "Unrecognized shell ($SHELL); add 'eval \"\$(learn shell-init)\"' to your rc manually."; return ;;
  esac
  marker="# >>> learn shell integration >>>"
  if [ -f "$rc" ] && grep -qF "$marker" "$rc"; then
    info "Shell integration already present in $rc"
    return
  fi
  {
    printf '\n%s\n' "$marker"
    printf '%s\n' 'export PATH="$HOME/.local/bin:$PATH"'
    printf '%s\n' 'command -v learn >/dev/null 2>&1 && eval "$(learn shell-init)"'
    printf '%s\n' "# <<< learn shell integration <<<"
  } >> "$rc"
  info "Added shell integration to $rc"
}
install_shell_integration

echo
info "Done — 'learn' is installed."
echo
warn "RESTART YOUR TERMINAL (or run 'source ${rc:-your shell rc}') for changes to take effect."
echo "  Shell integration only loads in new shells — until then 'learn log' can't"
echo "  see your current session's commands."
echo
echo "  Then try:"
echo "    learn login"
echo "    <run any command>"
echo "    learn log                       # logs that command"
echo "    learn find                      # search your history"
echo
echo "  To remove later:  learn uninstall"
echo
