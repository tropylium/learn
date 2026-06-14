"""Interactive `learn find` — type a query, see matches update live.

Two-phase search:
  - substring/prefix matches (fast SQL ILIKE) on a short debounce, per keystroke
  - semantic matches (embeddings) on a longer debounce, appended

Keys: Up/Down move · Enter copies the command · Tab opens `practice` on it ·
Esc/Ctrl-C cancels. (Plain letters go to the query, so the secondary action is
Tab, not a letter.)

Returns an (action, command) tuple: action is "copy" or "practice".
"""

from __future__ import annotations

import asyncio

import httpx
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

from . import config

SUBSTRING_DEBOUNCE = 0.12  # seconds
SEMANTIC_DEBOUNCE = 0.45

_STYLE = Style.from_dict(
    {
        "prompt": "bold #5fd7ff",
        "sel": "reverse",
        "dim": "#888888",
        "tag": "#5f8700",
        "status": "#888888 italic",
        "keys": "#888888",
        "key": "bold #5fd7ff",
    }
)


def run_find_tui() -> tuple[str, str] | None:
    """Run the search UI. Returns (action, command) or None if cancelled."""
    token = config.access_token()
    if not token:
        raise SystemExit("not logged in — run `learn login` first")

    client = httpx.AsyncClient(base_url=config.api_url(), timeout=httpx.Timeout(20.0))
    auth = {"token": token}
    results: list[dict] = []
    selected = {"i": 0}
    status = {"msg": "type to search…"}
    chosen: dict = {"action": None, "cmd": None}
    pending: dict[str, asyncio.Task] = {}

    input_buffer = Buffer(multiline=False)

    async def _get(path: str, query: str, limit: int) -> list[dict]:
        for attempt in range(2):
            r = await client.get(
                path,
                params={"q": query, "limit": limit},
                headers={"authorization": f"Bearer {auth['token']}"},
            )
            if r.status_code == 401 and attempt == 0 and await _refresh():
                continue
            if r.status_code == 200:
                return r.json().get("results", [])
            if r.status_code == 401:
                status["msg"] = "session expired — run `learn login`"
            return []
        return []

    async def _refresh() -> bool:
        rt = config.load_auth().get("refresh_token")
        if not rt:
            return False
        r = await client.post("/api/auth/refresh", json={"refresh_token": rt})
        if r.status_code != 200:
            return False
        data = r.json()
        stored = config.load_auth()
        stored.update(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=data.get("expires_at"),
        )
        config.save_auth(stored)
        auth["token"] = data["access_token"]
        return True

    def _merge(new: list[dict], *, replace: bool) -> None:
        if replace:
            results.clear()
        existing = {r["id"] for r in results}
        for r in new:
            if r["id"] not in existing:
                results.append(r)
                existing.add(r["id"])
        if selected["i"] >= len(results):
            selected["i"] = max(0, len(results) - 1)

    async def _do_search(query: str) -> None:
        for t in pending.values():
            t.cancel()
        pending.clear()
        if not query.strip():
            results.clear()
            selected["i"] = 0
            status["msg"] = "type to search…"
            app.invalidate()
            return

        async def substring() -> None:
            await asyncio.sleep(SUBSTRING_DEBOUNCE)
            status["msg"] = "searching…"
            app.invalidate()
            res = await _get("/api/search", query, 8)
            for r in res:
                r["_src"] = "match"
            _merge(res, replace=True)
            app.invalidate()

        async def semantic() -> None:
            await asyncio.sleep(SEMANTIC_DEBOUNCE)
            res = await _get("/api/find", query, 5)
            for r in res:
                r["_src"] = "semantic"
            _merge(res, replace=False)
            status["msg"] = f"{len(results)} result(s)"
            app.invalidate()

        pending["sub"] = asyncio.ensure_future(substring())
        pending["sem"] = asyncio.ensure_future(semantic())

    def on_change(_buffer) -> None:
        asyncio.ensure_future(_do_search(input_buffer.text))

    input_buffer.on_text_changed += on_change

    def render():
        if not results:
            return [("class:dim", "  (no matches yet)")]
        out: list[tuple[str, str]] = []
        for i, r in enumerate(results):
            cur = "class:sel" if i == selected["i"] else ""
            arrow = "❯ " if i == selected["i"] else "  "
            out.append((cur, f"{arrow}{r['command']}"))
            if r.get("_src") == "semantic":
                out.append(("class:tag", "  ~semantic"))
            out.append(("", "\n"))
            if r.get("intent"):
                out.append(("class:dim", f"    {r['intent']}\n"))
        return out

    def footer():
        return [
            ("class:keys", " "),
            ("class:key", "↑↓"), ("class:keys", " move   "),
            ("class:key", "⏎"), ("class:keys", " copy   "),
            ("class:key", "Tab"), ("class:keys", " practice   "),
            ("class:key", "esc"), ("class:keys", " cancel"),
        ]

    kb = KeyBindings()

    @kb.add("up")
    def _(event):
        if results:
            selected["i"] = (selected["i"] - 1) % len(results)
        event.app.invalidate()

    @kb.add("down")
    def _(event):
        if results:
            selected["i"] = (selected["i"] + 1) % len(results)
        event.app.invalidate()

    @kb.add("enter")
    def _(event):
        if results:
            chosen["action"] = "copy"
            chosen["cmd"] = results[selected["i"]]["command"]
        event.app.exit()

    @kb.add("tab")
    def _(event):
        if results:
            chosen["action"] = "practice"
            chosen["cmd"] = results[selected["i"]]["command"]
        event.app.exit()

    @kb.add("c-c")
    @kb.add("c-q")
    @kb.add("escape")
    def _(event):
        event.app.exit()

    root = HSplit(
        [
            VSplit(
                [
                    Window(
                        FormattedTextControl([("class:prompt", "find ❯ ")]),
                        width=7,
                        height=1,
                    ),
                    Window(BufferControl(buffer=input_buffer), height=1),
                ]
            ),
            Window(height=1, char="─", style="class:dim"),
            Window(FormattedTextControl(render), height=Dimension(min=1, max=14)),
            Window(FormattedTextControl(lambda: [("class:status", " " + status["msg"])]), height=1),
            Window(FormattedTextControl(footer), height=1),
        ]
    )

    app: Application = Application(
        layout=Layout(root, focused_element=input_buffer),
        key_bindings=kb,
        style=_STYLE,
        full_screen=False,
        mouse_support=False,
    )

    try:
        app.run()
    finally:
        try:
            asyncio.get_event_loop().run_until_complete(client.aclose())
        except Exception:
            pass

    if chosen["action"] and chosen["cmd"]:
        return (chosen["action"], chosen["cmd"])
    return None
