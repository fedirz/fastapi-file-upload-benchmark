"""Visualize benchmark results using rich tables"""

from pathlib import Path
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from models import BenchmarkHistory, BenchmarkRun

RESULTS_FILE = Path("benchmark_results.json")


def load_results() -> BenchmarkHistory | None:
    """Load benchmark results from JSON file"""
    if not RESULTS_FILE.exists():
        return None

    with open(RESULTS_FILE) as f:
        return BenchmarkHistory.model_validate_json(f.read())


def create_total_timing_table(run: BenchmarkRun) -> Table:
    """Create table showing total timing (complete request processing)"""
    table = Table(
        title="Total Request Time (Handler + FastAPI Processing)",
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("File Size", style="dim", width=12)
    for endpoint in run.endpoints:
        endpoint_name = endpoint.replace("/upload/", "")
        table.add_column(endpoint_name, justify="right", width=20)

    for test in run.test_files:
        row = [test.file_size_label]
        for endpoint in run.endpoints:
            endpoint_name = endpoint.replace("/upload/", "")
            metrics = test.results.get(endpoint_name)

            if metrics:
                duration = metrics.total_duration_seconds
                throughput = metrics.total_throughput_mbps
                cell = f"{duration:.4f}s ({throughput:.1f}MB/s)"
                row.append(cell)
            else:
                row.append("[dim]N/A[/dim]")

        table.add_row(*row)

    return table


def create_memory_table(run: BenchmarkRun) -> Table:
    """Create table showing memory usage"""
    table = Table(title="Memory Usage (Delta)", show_header=True, header_style="bold cyan")

    table.add_column("File Size", style="dim", width=12)
    for endpoint in run.endpoints:
        endpoint_name = endpoint.replace("/upload/", "")
        table.add_column(endpoint_name, justify="right", width=20)

    for test in run.test_files:
        row = [test.file_size_label]
        for endpoint in run.endpoints:
            endpoint_name = endpoint.replace("/upload/", "")
            metrics = test.results.get(endpoint_name)

            if metrics:
                memory_delta = metrics.memory_delta_mb
                if memory_delta > 0:
                    cell = f"[red]+{memory_delta:.2f} MB[/red]"
                elif memory_delta < 0:
                    cell = f"[green]{memory_delta:.2f} MB[/green]"
                else:
                    cell = f"{memory_delta:.2f} MB"
                row.append(cell)
            else:
                row.append("[dim]N/A[/dim]")

        table.add_row(*row)

    return table


def visualize_run(run: BenchmarkRun, console: Console) -> None:
    """Visualize a single benchmark run"""
    # Header
    title = Text()
    title.append("FastAPI File Upload Benchmark Results\n", style="bold white")
    title.append(f"Run: {run.timestamp.strftime('%Y-%m-%d %H:%M:%S')}", style="dim")

    console.print(Panel(title, border_style="blue"))
    console.print()

    # Display tables
    console.print(create_total_timing_table(run))
    console.print()

    console.print(create_memory_table(run))
    console.print()


def main() -> None:
    """Main entry point"""
    console = Console()

    # Load results
    history = load_results()

    if not history or not history.runs:
        console.print("[red]No benchmark results found.[/red]")
        console.print("Run benchmarks with: [cyan]python client.py[/cyan]")
        sys.exit(1)

    # Get the latest run
    latest_run = history.get_latest()

    if not latest_run:
        console.print("[red]No benchmark runs available.[/red]")
        sys.exit(1)

    # Display results
    visualize_run(latest_run, console)

    # Show available runs
    if len(history.runs) > 1:
        console.print()
        console.print(f"[dim]Total runs available: {len(history.runs)}[/dim]")
        console.print("[dim]Showing latest run. Edit this script to compare multiple runs.[/dim]")


if __name__ == "__main__":
    main()
