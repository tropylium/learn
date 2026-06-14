"""learn CLI.

Core loop:
  learn log "<cmd>"        log a command -> API annotates + embeds + stores
  learn find "<query>"     semantic recall of a command from your own history
  learn here               commands you've logged in this project/context
  learn score              XP per skill + global

Auth:
  learn login              email one-time-code sign-in
  learn logout             forget stored credentials
  learn whoami             show the signed-in account
"""

from __future__ import annotations

import sys

import click
import httpx

from . import config, shell
from .signature import command_signature

TIMEOUT = httpx.Timeout(30.0)


def _client() -> httpx.Client:
    return httpx.Client(base_url=config.api_url(), timeout=TIMEOUT)


def _die(msg: str) -> None:
    click.secho(f"error: {msg}", fg="red", err=True)
    sys.exit(1)


def _try_refresh() -> bool:
    """Exchange the stored refresh token for a new session. Returns success."""
    auth = config.load_auth()
    rt = auth.get("refresh_token")
    if not rt:
        return False
    try:
        with _client() as c:
            r = c.post("/api/auth/refresh", json={"refresh_token": rt})
        if r.status_code != 200:
            return False
        data = r.json()
    except httpx.HTTPError:
        return False
    auth.update(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=data.get("expires_at"),
    )
    config.save_auth(auth)
    return True


def _authed_request(method: str, path: str, **kwargs) -> httpx.Response:
    """Make a request with the Bearer token, refreshing once on a 401."""
    token = config.access_token()
    if not token:
        _die("not logged in — run `learn login` first")

    try:
        headers = {"authorization": f"Bearer {token}"}
        with _client() as c:
            r = c.request(method, path, headers=headers, **kwargs)
            if r.status_code == 401 and _try_refresh():
                headers["authorization"] = f"Bearer {config.access_token()}"
                r = c.request(method, path, headers=headers, **kwargs)
        if r.status_code == 401:
            _die("session expired — run `learn login` again")
        r.raise_for_status()
        return r
    except httpx.HTTPStatusError as e:
        _die(f"API returned {e.response.status_code}: {e.response.text[:200]}")
    except httpx.HTTPError as e:
        _die(f"could not reach API at {config.api_url()}: {e}")


@click.group(help=__doc__)
@click.version_option(package_name="learn")
def cli() -> None:
    pass


# --- auth -------------------------------------------------------------------

@cli.command("login")
@click.option("--email", default=None, help="Email to sign in with (prompted if omitted).")
def login_cmd(email: str | None) -> None:
    """Sign in with a one-time code emailed to you."""
    email = email or click.prompt("Email")
    try:
        with _client() as c:
            r = c.post("/api/auth/start", json={"email": email})
        if r.status_code != 200:
            _die(f"could not send code: {r.json().get('error', r.text[:200])}")
    except httpx.HTTPError as e:
        _die(f"could not reach API at {config.api_url()}: {e}")

    click.echo(f"We emailed a 6-digit code to {email}.")
    code = click.prompt("Code").strip()

    try:
        with _client() as c:
            r = c.post("/api/auth/verify", json={"email": email, "token": code})
        if r.status_code != 200:
            _die(f"sign-in failed: {r.json().get('error', 'invalid or expired code')}")
        data = r.json()
    except httpx.HTTPError as e:
        _die(f"could not reach API: {e}")

    config.save_auth(
        {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": data.get("expires_at"),
            "user_id": data.get("user_id"),
            "email": data.get("email", email),
        }
    )
    click.secho(f"✓ signed in as {data.get('email', email)}", fg="green")


@cli.command("logout")
def logout_cmd() -> None:
    """Forget stored credentials on this machine."""
    config.clear_auth()
    click.secho("✓ logged out", fg="green")


@cli.command("whoami")
def whoami_cmd() -> None:
    """Show the signed-in account."""
    auth = config.load_auth()
    if not auth.get("access_token"):
        click.secho("not logged in — run `learn login`", fg="yellow")
        return
    click.echo(f"signed in as {auth.get('email', '(unknown)')}")
    click.echo(f"user_id: {auth.get('user_id', '(unknown)')}")


# --- core loop --------------------------------------------------------------

@cli.command("log")
@click.argument("command", nargs=-1, required=False)
@click.option("-n", "num", type=int, default=1,
              help="With no command given, log the last N shell commands.")
@click.option("--exit-code", type=int, default=0,
              help="Exit code (only meaningful with an explicit command).")
@click.option("--project", default=None, help="Override detected project name.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output (for shell hooks).")
def log_cmd(command: tuple[str, ...], num: int, exit_code: int,
            project: str | None, quiet: bool) -> None:
    """Log a command. With no argument, logs your most recent shell command(s).

    \b
      learn log                       # log your last command
      learn log -n 5                  # log your last 5 commands
      learn log "git rebase -i HEAD~3"
    """
    if command:
        cmds = [" ".join(command).strip()]
    else:
        cmds = shell.recent_commands(num)
        if not cmds:
            _die('no recent shell commands found (history may not be flushed; '
                 'try `learn log "<cmd>"`)')

    ctx = config.detect_context()
    if project:
        ctx["project"] = project

    for cmd_str in cmds:
        if not cmd_str:
            continue
        payload = {
            "command": cmd_str,
            "signature": command_signature(cmd_str),
            "exit_code": exit_code,
            **ctx,
        }
        data = _authed_request("POST", "/api/log", json=payload).json()
        if not quiet:
            _print_logged(cmd_str, data)


def _print_logged(cmd_str: str, data: dict) -> None:
    times = data.get("times_used")
    suffix = f"  (used {times}×)" if times else ""
    click.secho(f"✓ logged: {cmd_str}{suffix}", fg="green")
    if data.get("intent"):
        click.echo(f"  intent: {data['intent']}")
    skills = data.get("skills") or []
    if skills:
        click.echo(f"  skills: {', '.join(skills)}")


@cli.command("find")
def find_cmd() -> None:
    """Interactively search your history — substring matches as you type, then
    semantic matches. Up/Down to move, Enter to pick, Esc to cancel."""
    from .tui import run_find_tui

    try:
        chosen = run_find_tui()
    except SystemExit as e:
        _die(str(e))
    except Exception as e:  # e.g. no TTY available
        _die(f"interactive find unavailable ({e}). Are you in a terminal?")
    if chosen:
        click.echo(chosen)


@cli.command("here")
def here_cmd() -> None:
    """Show commands you've logged in the current project/context."""
    ctx = config.detect_context()
    results = _authed_request("GET", "/api/here", params={"project": ctx["project"]}).json().get(
        "results", []
    )

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
    """Show how many commands you've logged, per skill and total."""
    data = _authed_request("GET", "/api/score").json()
    total = data.get("total_uses", 0)
    skills = data.get("skills", [])
    click.secho(f"Commands logged: {total}", bold=True, fg="yellow")
    for s in skills:
        click.echo(f"  {s['skill']:<24} {s['uses']:>5}×")


@cli.command("shell-init")
@click.option("--shell", "shell_name", default=None,
              help="Target shell: zsh or bash (auto-detected from $SHELL).")
def shell_init_cmd(shell_name: str | None) -> None:
    """Print shell integration. Add `eval "$(learn shell-init)"` to your rc
    (the installer does this automatically) so `learn log` can capture the
    current session's last command."""
    from .shellinit import render

    try:
        click.echo(render(shell_name))
    except ValueError as e:
        _die(str(e))


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
        click.echo(f"config:   {config.CONFIG_FILE}")
        auth = config.load_auth()
        click.echo(f"account:  {auth.get('email', '(not logged in)')}")


if __name__ == "__main__":
    cli()
