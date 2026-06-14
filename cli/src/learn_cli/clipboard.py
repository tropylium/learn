"""Cross-platform clipboard copy. Best-effort; returns whether it succeeded."""

from __future__ import annotations

import shutil
import subprocess
import sys


def _candidates() -> list[list[str]]:
    if sys.platform == "darwin":
        return [["pbcopy"]]
    if sys.platform.startswith("win"):
        return [["clip"]]
    # Linux/BSD: prefer Wayland, then X11.
    cands = []
    if shutil.which("wl-copy"):
        cands.append(["wl-copy"])
    if shutil.which("xclip"):
        cands.append(["xclip", "-selection", "clipboard"])
    if shutil.which("xsel"):
        cands.append(["xsel", "--clipboard", "--input"])
    return cands


def copy(text: str) -> bool:
    for cmd in _candidates():
        if not shutil.which(cmd[0]):
            continue
        try:
            p = subprocess.run(cmd, input=text.encode(), check=True)
            if p.returncode == 0:
                return True
        except (subprocess.SubprocessError, OSError):
            continue
    return False
