"""`learn practice` — guided fill-in (Model B).

Shows the goal + a skeleton with the program visible and the rest masked. As you
type, correct tokens fill in (green) and each part's explanation appears below.
When the whole command is reconstructed, Enter copies it.

Explanations are fetched once (one cached LLM call) before this screen opens, so
typing is instant — no per-keystroke API calls.
"""

from __future__ import annotations

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

from .practice import compute_filled
from .signature import PROGRAM

_STYLE = Style.from_dict(
    {
        "goal": "bold",
        "label": "#888888",
        "blank": "#666666",
        "filled": "bold #5fd700",
        "prog": "bold #5fd7ff",
        "expl": "",
        "tok": "bold #5fd700",
        "done": "bold #5fd700",
        "keys": "#888888",
        "key": "bold #5fd7ff",
    }
)


def run_practice_tui(
    command: str,
    target: list[tuple[str, str]],
    explanations: list[str],
    intent: str,
) -> str | None:
    """Returns the command if the user completed it (to be copied), else None."""
    input_buffer = Buffer(multiline=False)
    state = {"filled": [False] * len(target), "done": False}

    def recompute(_buffer=None) -> None:
        state["filled"] = compute_filled(target, input_buffer.text)
        state["done"] = bool(state["filled"]) and all(state["filled"])

    input_buffer.on_text_changed += recompute

    def goal_view():
        return [("class:label", "Goal: "), ("class:goal", intent or "(reconstruct the command)")]

    def skeleton_view():
        out: list[tuple[str, str]] = []
        for i, (tok, kind) in enumerate(target):
            if i:
                out.append(("", " "))
            if kind == PROGRAM:
                out.append(("class:prog", tok))
            elif state["filled"][i]:
                out.append(("class:filled", tok))
            else:
                out.append(("class:blank", "▢" * max(2, len(tok))))
        return out

    def reveal_view():
        out: list[tuple[str, str]] = []
        for i, (tok, kind) in enumerate(target):
            if state["filled"][i] and explanations[i]:
                out.append(("class:tok", f"  {tok:<14}"))
                out.append(("class:expl", f" {explanations[i]}\n"))
        if not out:
            return [("class:label", "  (type the command — explanations appear as you go)")]
        return out

    def status_view():
        if state["done"]:
            return [("class:done", " ✓ you've got it — Enter to copy")]
        done = sum(state["filled"])
        return [("class:label", f" {done}/{len(target)} parts")]

    def footer():
        return [
            ("class:keys", " "),
            ("class:key", "⏎"), ("class:keys", " copy (when complete)   "),
            ("class:key", "esc"), ("class:keys", " cancel"),
        ]

    chosen: dict = {"cmd": None}
    kb = KeyBindings()

    @kb.add("enter")
    def _(event):
        if state["done"]:
            chosen["cmd"] = command
            event.app.exit()

    @kb.add("c-c")
    @kb.add("escape")
    def _(event):
        event.app.exit()

    root = HSplit(
        [
            Window(FormattedTextControl(goal_view), height=1),
            Window(height=1, char=" "),
            Window(FormattedTextControl(skeleton_view), height=Dimension(min=1, max=3)),
            Window(height=1, char="─", style="class:label"),
            VSplit([Window(FormattedTextControl([("class:prompt", "type ❯ ")]), width=7, height=1),
                    Window(BufferControl(buffer=input_buffer), height=1)]),
            Window(height=1, char="─", style="class:label"),
            Window(FormattedTextControl(reveal_view), height=Dimension(min=1, max=12)),
            Window(FormattedTextControl(status_view), height=1),
            Window(FormattedTextControl(footer), height=1),
        ]
    )

    app: Application = Application(
        layout=Layout(root, focused_element=input_buffer),
        key_bindings=kb,
        style=_STYLE,
        full_screen=False,
    )
    app.run()
    return chosen["cmd"]
