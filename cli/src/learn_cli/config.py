"""Local config, credentials, and context detection for the learn CLI.

Two files under ~/.config/learn/:
  config.json  — non-secret settings (api_url)
  auth.json    — session tokens from `learn login` (chmod 600)
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("LEARN_CONFIG_DIR", Path.home() / ".config" / "learn"))
CONFIG_FILE = CONFIG_DIR / "config.json"
AUTH_FILE = CONFIG_DIR / "auth.json"

# Default to local Next.js dev server; override with LEARN_API_URL or `learn config`.
DEFAULT_API_URL = "http://localhost:3000"


def _read_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def load_config() -> dict:
    return _read_json(CONFIG_FILE)


def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


def api_url() -> str:
    return os.environ.get("LEARN_API_URL") or load_config().get("api_url") or DEFAULT_API_URL


# --- auth / credentials -----------------------------------------------------

def load_auth() -> dict:
    return _read_json(AUTH_FILE)


def save_auth(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    AUTH_FILE.write_text(json.dumps(data, indent=2))
    try:
        AUTH_FILE.chmod(0o600)
    except OSError:
        pass


def clear_auth() -> None:
    AUTH_FILE.unlink(missing_ok=True)


def access_token() -> str | None:
    return load_auth().get("access_token")


def detect_context(cwd: str | None = None) -> dict:
    """Best-effort location context: hostname + project + cwd.

    project = git remote name -> git root dir name -> cwd dir name.
    """
    cwd = cwd or os.getcwd()
    hostname = socket.gethostname()
    project = _detect_project(cwd)
    return {"hostname": hostname, "project": project, "cwd": cwd}


def _detect_project(cwd: str) -> str:
    try:
        root = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=2,
        )
        if root.returncode == 0:
            top = root.stdout.strip()
            remote = subprocess.run(
                ["git", "-C", cwd, "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=2,
            )
            if remote.returncode == 0 and remote.stdout.strip():
                url = remote.stdout.strip()
                name = url.rstrip("/").split("/")[-1]
                return name[:-4] if name.endswith(".git") else name
            return Path(top).name
    except (subprocess.SubprocessError, OSError):
        pass
    return Path(cwd).name
