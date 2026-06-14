"""A simple list picker — used by `learn new` to choose among suggestions.

Up/Down to move, Enter to select, Esc/Ctrl-C to cancel. Returns the chosen item
(a dict with at least "command"), or None if cancelled.
"""

from __future__ import annotations

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

_STYLE = Style.from_dict(
    {
        "title": "bold",
        "cmd": "#5fd700",
        "sel": "reverse",
        "dim": "#888888",
        "keys": "#888888",
        "key": "bold #5fd7ff",
    }
)


def run_picker(title: str, items: list[dict]) -> dict | None:
    selected = {"i": 0}
    chosen: dict = {"item": None}

    def render():
        out: list[tuple[str, str]] = []
        for i, it in enumerate(items):
            sel = i == selected["i"]
            arrow = "❯ " if sel else "  "
            cmd_style = "class:cmd class:sel" if sel else "class:cmd"
            out.append((cmd_style, f"{arrow}{it['command']}"))
            out.append(("", "\n"))
            if it.get("description"):
                out.append(("class:dim", f"    {it['description']}\n"))
        return out

    kb = KeyBindings()

    @kb.add("up")
    def _(event):
        selected["i"] = (selected["i"] - 1) % len(items)
        event.app.invalidate()

    @kb.add("down")
    def _(event):
        selected["i"] = (selected["i"] + 1) % len(items)
        event.app.invalidate()

    @kb.add("enter")
    def _(event):
        chosen["item"] = items[selected["i"]]
        event.app.exit()

    @kb.add("c-c")
    @kb.add("escape")
    def _(event):
        event.app.exit()

    root = HSplit(
        [
            Window(FormattedTextControl(lambda: [("class:title", f"{title}")]), height=1),
            Window(height=1, char="─", style="class:dim"),
            Window(FormattedTextControl(render), height=Dimension(min=1, max=18)),
            Window(
                FormattedTextControl(
                    lambda: [
                        ("class:keys", " "),
                        ("class:key", "↑↓"), ("class:keys", " move   "),
                        ("class:key", "⏎"), ("class:keys", " practice   "),
                        ("class:key", "esc"), ("class:keys", " cancel"),
                    ]
                ),
                height=1,
            ),
        ]
    )

    app: Application = Application(
        layout=Layout(root), key_bindings=kb, style=_STYLE, full_screen=False
    )
    app.run()
    return chosen["item"]
