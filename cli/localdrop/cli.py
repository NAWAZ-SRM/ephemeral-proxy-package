import asyncio
import signal
import sys
from pathlib import Path
from urllib.parse import urlparse
import httpx

import typer
from typing import Optional

from .config import config, set_server_url, get_ssh_key_path, parse_ttl, get_auth_token, save_config, TunnelConfig
from .api_client import TunnelAPIClient
from .ssh import SSHManager
from .websocket import stream_logs
from .display import Display
from .auth import login, logout

app = typer.Typer(
    name="tunnel",
    help="Instant localhost sharing for developers",
    add_completion=False,
)
config_app = typer.Typer(help="Manage configuration")
app.add_typer(config_app, name="config")

SHARE_HELP = """Share a local port via a public HTTPS URL.

 Examples:
   tunnel share 3000                    Share localhost:3000
   tunnel share 8080 --ttl 1h         Share with 1 hour expiry
   tunnel share 5000 --name myapp      Custom subdomain
   tunnel share 3000 --auth @company.com  Restricted access
"""

LIST_HELP = """List your active tunnels (requires authentication)."""

STOP_HELP = """Stop a specific tunnel."""

LOGS_HELP = """Stream logs for an existing tunnel."""


@app.command(help=SHARE_HELP)
def share(
    port: int = typer.Argument(..., help="Local port to expose", min=1, max=65535),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Custom subdomain slug"),
    ttl: str = typer.Option("2h", "--ttl", help="Auto-expiry (e.g., 30m, 2h, 24h, forever)"),
    auth_domain: Optional[str] = typer.Option(None, "--auth", help="Restrict to email domain (e.g. @company.com)"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password protection"),
    local_url: Optional[str] = typer.Option(None, "--local-url", help="Full local URL (e.g. http://localhost:3000 or http://192.168.1.100:8080)"),
    inspect: bool = typer.Option(False, "--inspect", help="Open browser dashboard on start"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output, just print the URL"),
    region: Optional[str] = typer.Option(None, "--region", help="Preferred server region (us, eu, asia)"),
    server_url: Optional[str] = typer.Option(None, "--server", help="Tunnel server URL"),
):
    asyncio.run(_share(
        port=port,
        name=name,
        ttl=ttl,
        auth_domain=auth_domain,
        password=password,
        local_url=local_url,
        inspect=inspect,
        quiet=quiet,
        region=region,
        server_url=server_url,
    ))


async def _share(
    port: int,
    name: Optional[str],
    ttl: str,
    auth_domain: Optional[str],
    password: Optional[str],
    local_url: Optional[str],
    inspect: bool,
    quiet: bool,
    region: Optional[str],
    server_url: Optional[str],
):
    display = Display(quiet=quiet)
    stop_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        display.console.print("\n[yellow]Stopping tunnel...[/yellow]")
        stop_event.set()
    
    old_handler = signal.signal(signal.SIGINT, signal_handler)
    old_handler_sigterm = signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        api_url = server_url or config.server_url
        parsed = urlparse(api_url)
        server_host = parsed.netloc or "tunnel.dev"
        
        is_local = server_host in ("localhost", "localhost:8000", "127.0.0.1", "127.0.0.1:8000")
        
        if is_local and not local_url:
            local_url = f"http://dashboard:80"
        
        try:
            ttl_seconds = parse_ttl(ttl)
        except ValueError as e:
            display.print_error(str(e))
            sys.exit(1)
        
        client = TunnelAPIClient(base_url=api_url)
        
        display.print_info("Creating tunnel...")
        
        try:
            tunnel = await client.create_tunnel(
                port=port,
                local_url=local_url,
                name=name,
                ttl=ttl_seconds,
                auth_domain=auth_domain,
                password=password,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                display.print_error(f"Name '{name}' is already taken.")
            elif e.response.status_code == 429:
                display.print_error("You have reached the maximum number of active tunnels.")
            else:
                display.print_error(f"API error: {e.response.text}")
            sys.exit(1)
        except Exception as e:
            display.print_error(f"Failed to create tunnel: {e}")
            display.print_info("Is the server running? Check your internet connection.")
            sys.exit(1)
        
        display.print_banner(
            url=tunnel.url,
            dashboard_url=tunnel.dashboard_url,
            expires_at=tunnel.expires_at,
            local_port=port,
            slug=tunnel.slug,
        )
        
        if inspect:
            import webbrowser
            webbrowser.open(tunnel.dashboard_url)
        
        ssh_key_path = get_ssh_key_path()
        ssh_manager = SSHManager(
            assigned_port=tunnel.assigned_port,
            local_port=port,
            local_url=local_url,
            ssh_key_path=ssh_key_path,
            server_host=server_host,
        )

        if is_local:
            try:
                await client.activate_tunnel(tunnel.slug)
                display.print_info("Tunnel activated (local mode)")
            except Exception as e:
                display.print_warning(f"Could not activate tunnel: {e}")
        
        if not is_local:
            try:
                ssh_manager.start()
            except FileNotFoundError:
                display.print_error("SSH command not found. Please install OpenSSH.")
                await client.expire_tunnel(tunnel.slug)
                sys.exit(1)
            
            await asyncio.sleep(1)
            
            if not ssh_manager.is_alive():
                display.print_warning("SSH connection may have failed. Checking tunnel status...")
            
            await asyncio.sleep(2)
        else:
            display.print_info("Local mode: skipping SSH tunnel (use a real VPS for public URLs)")
        
        try:
            await stream_logs(tunnel.slug, api_url, get_auth_token(), display, stop_event)
        except Exception as e:
            display.print_error(f"Stream error: {e}")
        
        try:
            summary = await client.expire_tunnel(tunnel.slug)
            display.print_summary({
                "duration_seconds": 0,
                "total_requests": display.total_requests,
                "unique_visitors": "N/A",
            })
        except Exception:
            pass
        
        if not is_local:
            ssh_manager.stop()
    
    finally:
        signal.signal(signal.SIGINT, old_handler)
        signal.signal(signal.SIGTERM, old_handler_sigterm)


@app.command(help=LIST_HELP)
def list_tunnels(
    server_url: Optional[str] = typer.Option(None, "--server", help="Tunnel server URL"),
):
    if not config.auth_token:
        typer.echo("Not logged in. Run 'tunnel login' first.")
        raise typer.Exit(1)
    
    asyncio.run(_list_tunnels(server_url))


async def _list_tunnels(server_url: Optional[str]):
    from .api_client import TunnelAPIClient
    from rich.table import Table
    from rich.console import Console

    api_url = server_url or config.server_url
    client = TunnelAPIClient(base_url=api_url, token=get_auth_token())
    console = Console()

    console.print("[dim]Fetching active tunnels...[/dim]")

    try:
        tunnels = await client.get_user_tunnels()
        if not tunnels:
            console.print("[yellow]No active tunnels found.[/yellow]")
            return

        table = Table(title="Active Tunnels")
        table.add_column("Slug", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("URL", style="blue")

        for t in tunnels:
            table.add_row(
                t.get("slug", "?"),
                t.get("status", "?"),
                t.get("url", "?"),
            )

        console.print(table)
        console.print(f"\n[dim]Found {len(tunnels)} tunnel(s)[/dim]")
    except Exception as e:
        console.print(f"[red]Failed to list tunnels: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Failed to list tunnels: {e}[/red]")
        raise typer.Exit(1)


@app.command(help=STOP_HELP)
def stop(
    slug: str = typer.Argument(..., help="Tunnel slug to stop"),
    server_url: Optional[str] = typer.Option(None, "--server", help="Tunnel server URL"),
):
    asyncio.run(_stop_tunnel(slug, server_url))


async def _stop_tunnel(slug: str, server_url: Optional[str]):
    client = TunnelAPIClient(base_url=server_url)
    try:
        summary = await client.expire_tunnel(slug)
        typer.echo(f"✅ Tunnel '{slug}' stopped.")
        typer.echo(f"   Duration: {summary.duration_seconds}s, Requests: {summary.total_requests}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            typer.echo(f"❌ Tunnel '{slug}' not found.")
        else:
            typer.echo(f"❌ Error: {e.response.text}")
        raise typer.Exit(1)


@app.command(help=LOGS_HELP)
def logs(
    slug: str = typer.Argument(..., help="Tunnel slug"),
    server_url: Optional[str] = typer.Option(None, "--server", help="Tunnel server URL"),
):
    asyncio.run(_stream_logs(slug, server_url))


async def _stream_logs(slug: str, server_url: Optional[str]):
    from .websocket import stream_logs
    
    display = Display()
    stop_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        stop_event.set()
    
    old_handler = signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await stream_logs(slug, server_url or config.server_url, get_auth_token(), display, stop_event)
    finally:
        signal.signal(signal.SIGINT, old_handler)


@app.command()
def login_cmd(
    server_url: Optional[str] = typer.Option(None, "--server", help="Tunnel server URL"),
):
    asyncio.run(login(server_url))


@app.command()
def logout_cmd():
    logout()


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Key (e.g. server-url)"),
    value: str = typer.Argument(..., help="Value"),
):
    if key == "server-url":
        set_server_url(value)
        typer.echo(f"Server URL set to: {value}")
    else:
        typer.echo(f"Unknown config key: {key}", err=True)


@config_app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Key (e.g. server-url)"),
):
    if key == "server-url":
        typer.echo(config.server_url)
    elif key == "auth-token":
        typer.echo("***" if config.auth_token else "(not set)")
    else:
        typer.echo(f"Unknown config key: {key}", err=True)


@config_app.command("list")
def config_list():
    typer.echo(f"server-url:  {config.server_url}")
    typer.echo(f"auth-token:  {'***' if config.auth_token else '(not set)'}")
    typer.echo(f"default-ttl: {config.default_ttl}")
    typer.echo(f"ssh-key:     {config.ssh_key_path}")


@app.command()
def version():
    from . import __version__
    typer.echo(f"tunnel {__version__}")


@app.command()
def version_cmd():
    typer.echo("tunnel 1.0.0")


if __name__ == "__main__":
    app()
