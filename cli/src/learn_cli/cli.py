"""learn CLI — vertical slice.

Commands that prove the core loop:
  learn log "<cmd>"        log a command -> API annotates + embeds + stores
  learn find "<query>"     semantic recall of a command from your own history
  learn here               commands you've logged in this project/context
  learn score              XP per skill + global

Plus config helpers (login/whoami are stubbed until real auth lands).
"""

from __future__ import annotations

import sys

import click
import httpx

from . import config

TIMEOUT = httpx.Timeout(30.0)


def _client() -> httpx.Client:
    return httpx.Client(base_url=config.api_url(), timeout=TIMEOUT)


def _die(msg: str) -> None:
    click.secho(f"error: {msg}", fg="red", err=True)
    sys.exit(1)


@click.group(help=__doc__)
@click.version_option(package_name="learn")
def cli() -> None:
    pass


@cli.command("log")
@click.argument("command", nargs=-1, required=True)
@click.option("--exit-code", type=int, default=0, help="Exit code of the command.")
@click.option("--project", default=None, help="Override detected project name.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress annotation output (for shell hooks).")
def log_cmd(command: tuple[str, ...], exit_code: int, project: str | None, quiet: bool) -> None:
    """Log a command. The API annotates, embeds, scores, and stores it."""
    cmd_str = " ".join(command).strip()
    if not cmd_str:
        _die("empty command")

    ctx = config.detect_context()
    if project:
        ctx["project"] = project

    payload = {
        "user_id": config.user_id(),
        "command": cmd_str,
        "exit_code": exit_code,
        **ctx,
    }

    try:
        with _client() as c:
            r = c.post("/api/log", json=payload)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        _die(f"API returned {e.response.status_code}: {e.response.text[:200]}")
    except httpx.HTTPError as e:
        _die(f"could not reach API at {config.api_url()}: {e}")

    if quiet:
        return

    intent = data.get("intent", "")
    skills = data.get("skills", []) or []
    complexity = data.get("complexity")
    points = data.get("points_awarded")

    click.secho(f"✓ logged: {cmd_str}", fg="green")
    if intent:
        click.echo(f"  intent:     {intent}")
    if skills:
        click.echo(f"  skills:     {', '.join(skills)}")
    if complexity is not None:
        click.echo(f"  complexity: {complexity}/5")
    if points is not None:
        click.secho(f"  +{points} XP", fg="yellow")


@cli.command("find")
@click.argument("query", nargs=-1, required=True)
@click.option("--limit", "-n", type=int, default=5, help="Max results.")
def find_cmd(query: tuple[str, ...], limit: int) -> None:
    """Semantic recall: describe what you want, get back a command you've used."""
    q = " ".join(query).strip()
    if not q:
        _die("empty query")

    try:
        with _client() as c:
            r = c.get("/api/find", params={"user_id": config.user_id(), "q": q, "limit": limit})
            r.raise_for_status()
            results = r.json().get("results", [])
    except httpx.HTTPError as e:
        _die(f"could not reach API: {e}")

    if not results:
        click.secho("no matches in your history yet.", fg="yellow")
        return

    for i, res in enumerate(results, 1):
        sim = res.get("similarity")
        sim_str = f"  ({sim:.0%} match)" if isinstance(sim, (int, float)) else ""
        click.secho(f"{i}. {res['command']}{sim_str}", fg="cyan", bold=True)
        if res.get("intent"):
            click.echo(f"   {res['intent']}")
        if res.get("explanation"):
            click.echo(f"   {res['explanation']}")
        click.echo()


@cli.command("here")
def here_cmd() -> None:
    """Show commands you've logged in the current project/context."""
    ctx = config.detect_context()
    try:
        with _client() as c:
            r = c.get("/api/here", params={"user_id": config.user_id(), "project": ctx["project"]})
            r.raise_for_status()
            results = r.json().get("results", [])
    except httpx.HTTPError as e:
        _die(f"could not reach API: {e}")

    click.secho(f"project: {ctx['project']}", bold=True)
    if not results:
        click.secho("  nothing logged here yet.", fg="yellow")
        return
    for res in results:
        click.secho(f"  • {res['command']}", fg="cyan")
        if res.get("intent"):
            click.echo(f"    {res['intent']}")


@cli.command("score")
def score_cmd() -> None:
    """Show XP per skill and total."""
    try:
        with _client() as c:
            r = c.get("/api/score", params={"user_id": config.user_id()})
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as e:
        _die(f"could not reach API: {e}")

    total = data.get("total_xp", 0)
    skills = data.get("skills", [])
    click.secho(f"Total XP: {total}", bold=True, fg="yellow")
    for s in skills:
        click.echo(f"  {s['skill']:<24} {s['xp']:>6} XP")


@cli.command("config")
@click.option("--api-url", "api_url_opt", default=None, help="Set the API base URL.")
@click.option("--show", is_flag=True, help="Show current config.")
def config_cmd(api_url_opt: str | None, show: bool) -> None:
    """View or set local config."""
    cfg = config.load_config()
    if api_url_opt:
        cfg["api_url"] = api_url_opt
        config.save_config(cfg)
        click.secho(f"api_url set to {api_url_opt}", fg="green")
    if show or not api_url_opt:
        click.echo(f"api_url:  {config.api_url()}")
        click.echo(f"user_id:  {config.user_id()}")
        click.echo(f"config:   {config.CONFIG_FILE}")


if __name__ == "__main__":
    cli()
