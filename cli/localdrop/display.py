from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from datetime import datetime
from typing import Optional


class Display:
    def __init__(self, quiet: bool = False):
        self.console = Console()
        self.quiet = quiet
        self.start_time = datetime.now()
        self.total_requests = 0
        self.live_visitors = 0
        self._table = None
        self._live = None

    def print_banner(self, url: str, dashboard_url: str, expires_at: Optional[datetime], local_port: int, slug: str):
        if self.quiet:
            print(url)
            return
        
        from rich.align import Align
        
        expires_str = "never" if not expires_at else expires_at.strftime("%I:%M %p %Z")
        
        content = Text()
        content.append("Public URL:    ", style="bold cyan")
        content.append(url + "\n", style="cyan link " + url)
        content.append("Dashboard:     ", style="bold cyan")
        content.append(dashboard_url + "\n", style="link " + dashboard_url)
        content.append("Expires:       ", style="bold yellow")
        content.append(f"{expires_str}  [Ctrl+C to stop]\n", style="yellow")
        content.append("Forwarding:    ", style="bold green")
        content.append(f"{url} → localhost:{local_port}\n", style="green")
        content.append("\nWaiting for visitors...", style="dim")
        
        panel = Panel(
            Align.left(content),
            title="🚀 Tunnel Active",
            border_style="green",
            padding=(1, 2),
        )
        self.console.print(panel)
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time", style="dim", width=10)
        table.add_column("Method", width=7)
        table.add_column("Path", style="cyan")
        table.add_column("Status", width=8)
        table.add_column("Latency", width=8)
        table.add_column("Country", width=6)
        self._table = table
        self.console.print(table)

    def print_request_row(self, data: dict):
        if self.quiet:
            return
        
        self.total_requests += 1
        
        time_str = data.get("timestamp", datetime.now().isoformat())
        try:
            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            time_str = dt.strftime("%H:%M:%S")
        except Exception:
            pass
        
        method = data.get("method", "GET")
        path = data.get("path", "/")
        status = data.get("status_code", 200)
        latency = data.get("latency_ms", 0)
        flag = data.get("flag_emoji", "🌐")
        country = data.get("country_code", "XX")
        
        if len(path) > 50:
            path = path[:47] + "..."
        
        status_style = "green" if status < 400 else "red" if status >= 500 else "yellow"
        
        self.console.print(
            f"[dim]{time_str}[/dim]  "
            f"[bold]{method}[/bold]  "
            f"[cyan]{path}[/cyan]  "
            f"[{status_style}]{status}[/{status_style}]  "
            f"{latency}ms  "
            f"{flag} {country}",
            end="\r"
        )

    def print_summary(self, summary: dict):
        if self.quiet:
            return
        
        duration = summary.get("duration_seconds", 0)
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        
        self.console.print()
        self.console.print(Panel(
            f"[bold green]✅ Tunnel stopped[/bold green]\n\n"
            f"Duration:        [cyan]{duration_str}[/cyan]\n"
            f"Total requests:  [cyan]{summary.get('total_requests', self.total_requests)}[/cyan]\n"
            f"Unique visitors: [cyan]{summary.get('unique_visitors', 'N/A')}[/cyan]",
            title="Session Summary",
            border_style="blue",
        ))

    def print_error(self, msg: str):
        self.console.print(f"[bold red]ERROR:[/bold red] {msg}")

    def print_warning(self, msg: str):
        self.console.print(f"[bold yellow]WARNING:[/bold yellow] {msg}")

    def print_info(self, msg: str):
        self.console.print(f"[dim]{msg}[/dim]")

    def print_idle_warning(self, expires_in_seconds: int):
        minutes = expires_in_seconds // 60
        self.console.print(
            f"\n[bold yellow]⚠️  No requests in 15 minutes. "
            f"Tunnel will auto-expire in {minutes} more minutes.[/bold yellow]"
        )

    def print_expired(self, reason: str, summary: dict):
        self.console.print()
        self.console.print(f"[bold red]🔒 Tunnel has expired[/bold red] (reason: {reason})")
        self.print_summary(summary)

    def update_visitor_count(self, count: int, countries: list):
        self.live_visitors = count
