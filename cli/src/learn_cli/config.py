"""Local config + context detection for the learn CLI.

For the vertical slice there is no auth yet: we use a hardcoded dev user id so
the full log -> annotate -> embed -> find loop can be proven end to end. The
`token`/`user_id` plumbing is here so that swapping in real Supabase auth later
is a small change, not a rewrite.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("LEARN_CONFIG_DIR", Path.home() / ".config" / "learn"))
CONFIG_FILE = CONFIG_DIR / "config.json"

# Default to local Next.js dev server; override with LEARN_API_URL or `learn config`.
DEFAULT_API_URL = "http://localhost:3000"

# Vertical-slice dev identity. Replaced by real auth in a later milestone.
DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


def api_url() -> str:
    return os.environ.get("LEARN_API_URL") or load_config().get("api_url") or DEFAULT_API_URL


def user_id() -> str:
    return load_config().get("user_id") or DEV_USER_ID


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
