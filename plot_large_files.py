from pathlib import Path

import matplotlib.pyplot as plt

from models import BenchmarkHistory

RESULTS_FILE = Path("benchmark_results.json")
OUTPUT_DIR = Path("plots")


def load_results() -> BenchmarkHistory | None:
    if not RESULTS_FILE.exists():
        return None

    return BenchmarkHistory.model_validate_json(RESULTS_FILE.read_text())


def plot_large_files_performance() -> None:
    history = load_results()

    if not history or not history.runs:
        print("No benchmark results found. Run benchmarks with: python client.py")
        return

    latest_run = history.get_latest()
    if not latest_run:
        print("No benchmark runs available.")
        return

    # Filter for 128MB and above
    large_file_tests = [test for test in latest_run.test_files if test.file_size_bytes >= 128 * 1024 * 1024]

    if not large_file_tests:
        print("No test results for files 128MB or larger.")
        return

    # Extract data for plotting
    file_labels = [test.file_size_label for test in large_file_tests]
    endpoints = [ep.replace("/upload/", "") for ep in latest_run.endpoints]

    # Prepare data structures
    throughput_data = {ep: [] for ep in endpoints}
    memory_data = {ep: [] for ep in endpoints}
    duration_data = {ep: [] for ep in endpoints}

    for test in large_file_tests:
        for endpoint in endpoints:
            metrics = test.results.get(endpoint)
            if metrics:
                throughput_data[endpoint].append(metrics.total_throughput_mbps)
                memory_data[endpoint].append(metrics.memory_delta_mb)
                duration_data[endpoint].append(metrics.total_duration_seconds)
            else:
                throughput_data[endpoint].append(0)
                memory_data[endpoint].append(0)
                duration_data[endpoint].append(0)

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Create figure with 3 subplots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12))
    fig.suptitle(
        f"Large File Upload Performance (128MB+)\nRun: {latest_run.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        fontsize=14,
        fontweight="bold",
    )

    # Plot 1: Throughput comparison
    x_pos = range(len(file_labels))
    width = 0.15
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    for idx, endpoint in enumerate(endpoints):
        offset = (idx - len(endpoints) / 2) * width
        ax1.bar(
            [x + offset for x in x_pos],
            throughput_data[endpoint],
            width,
            label=endpoint,
            color=colors[idx % len(colors)],
        )

    ax1.set_xlabel("File Size", fontsize=11)
    ax1.set_ylabel("Throughput (MB/s)", fontsize=11)
    ax1.set_title("Upload Throughput", fontsize=12, fontweight="bold")
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(file_labels)
    ax1.set_ylim(bottom=0)
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis="y")

    # Plot 2: Memory usage comparison
    for idx, endpoint in enumerate(endpoints):
        offset = (idx - len(endpoints) / 2) * width
        ax2.bar(
            [x + offset for x in x_pos],
            memory_data[endpoint],
            width,
            label=endpoint,
            color=colors[idx % len(colors)],
        )

    ax2.set_xlabel("File Size", fontsize=11)
    ax2.set_ylabel("Memory Delta (MB)", fontsize=11)
    ax2.set_title("Memory Usage (RSS Delta)", fontsize=12, fontweight="bold")
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(file_labels)
    ax2.set_ylim(bottom=0)
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis="y")

    # Plot 3: Duration comparison
    for idx, endpoint in enumerate(endpoints):
        offset = (idx - len(endpoints) / 2) * width
        ax3.bar(
            [x + offset for x in x_pos],
            duration_data[endpoint],
            width,
            label=endpoint,
            color=colors[idx % len(colors)],
        )

    ax3.set_xlabel("File Size", fontsize=11)
    ax3.set_ylabel("Duration (seconds)", fontsize=11)
    ax3.set_title("Total Request Duration", fontsize=12, fontweight="bold")
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(file_labels)
    ax3.set_ylim(bottom=0)
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()

    # Save plot
    output_file = OUTPUT_DIR / "large_files_performance.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"Plot saved to {output_file}")

    plt.close("all")


if __name__ == "__main__":
    plot_large_files_performance()
