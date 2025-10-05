import asyncio
from datetime import datetime
import os
from pathlib import Path
import time

import httpx

from models import BenchmarkHistory, BenchmarkRun, EndpointMetrics, FileSizeTest, ServerResponse

# Test file sizes - 1KB to 1GB, doubling each step
FILE_SIZES = []
size_bytes = 1024  # Start at 1KB
while size_bytes <= 1024 * 1024 * 1024:  # Up to 1GB
    if size_bytes < 1024:
        label = f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        label = f"{size_bytes // 1024}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        label = f"{size_bytes // (1024 * 1024)}MB"
    else:
        label = f"{size_bytes // (1024 * 1024 * 1024)}GB"
    FILE_SIZES.append((label, size_bytes))
    size_bytes *= 2

# Endpoints to test
ENDPOINTS = [
    "/upload/sync-file",
    "/upload/async-file",
    "/upload/sync-uploadfile",
    "/upload/async-uploadfile",
    "/upload/async-stream",
]

BASE_URL = "http://localhost:8000"
TEST_FILES_DIR = Path("test_files")
RESULTS_FILE = Path("benchmark_results.json")


def generate_test_file(size_bytes: int, filename: str) -> Path:
    """Generate a test file of specified size (or reuse if it already exists)"""
    TEST_FILES_DIR.mkdir(exist_ok=True)
    filepath = TEST_FILES_DIR / filename

    # Check if file already exists with correct size
    if filepath.exists() and filepath.stat().st_size == size_bytes:
        return filepath

    # Generate file with random data
    with open(filepath, "wb") as f:
        # Write in chunks to avoid memory issues
        chunk_size = 1024 * 1024  # 1MB
        remaining = size_bytes

        while remaining > 0:
            write_size = min(chunk_size, remaining)
            f.write(os.urandom(write_size))
            remaining -= write_size

    return filepath


async def upload_file(endpoint: str, filepath: Path) -> dict:
    """Upload file to specified endpoint and return metrics"""
    url = f"{BASE_URL}{endpoint}"

    # Track client-side timing
    start_time = time.perf_counter()

    async with httpx.AsyncClient(timeout=300.0) as client:
        with open(filepath, "rb") as f:
            # Use different upload methods based on endpoint
            if "stream" in endpoint:
                # For stream endpoints, send raw body
                response = await client.post(url, content=f.read())
            else:
                # For file/uploadfile endpoints, use multipart form
                files = {"file": (filepath.name, f, "application/octet-stream")}
                response = await client.post(url, files=files)

    end_time = time.perf_counter()
    client_duration = end_time - start_time

    if response.status_code != 200:
        return {
            "error": f"HTTP {response.status_code}",
            "client_duration": client_duration,
        }

    # Parse server response using Pydantic model
    server_data = ServerResponse.model_validate_json(response.text)

    # Extract total request timing from headers
    total_duration = float(response.headers.get("X-Total-Duration", 0))
    total_memory_delta = float(response.headers.get("X-Total-Memory-Delta", 0))

    return {
        "server_response": server_data,
        "client_duration": client_duration,
        "total_duration": total_duration,
        "total_memory_delta": total_memory_delta,
    }


def save_results(benchmark_run: BenchmarkRun) -> None:
    """Save benchmark results to JSON file"""
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            history = BenchmarkHistory.model_validate_json(f.read())
    else:
        history = BenchmarkHistory(runs=[])

    history.add_run(benchmark_run)

    with open(RESULTS_FILE, "w") as f:
        f.write(history.model_dump_json(indent=2))

    print(f"\n✓ Results saved to {RESULTS_FILE}")


async def run_benchmark() -> None:
    """Run the complete benchmark suite"""
    print("=" * 100)
    print("FastAPI File Upload Benchmark")
    print("=" * 100)
    print()

    print(f"Testing {len(FILE_SIZES)} file sizes from {FILE_SIZES[0][0]} to {FILE_SIZES[-1][0]}")
    print(f"Testing {len(ENDPOINTS)} endpoints")
    print()

    print("Preparing test files...")
    test_files = {}
    for size_name, size_bytes in FILE_SIZES:
        filename = f"test_{size_name}.bin"
        filepath = TEST_FILES_DIR / filename

        if filepath.exists() and filepath.stat().st_size == size_bytes:
            print(f"  {size_name} file... ✓ (reusing existing)")
            test_files[size_name] = filepath
        else:
            print(f"  Generating {size_name} file...", end=" ", flush=True)
            filepath = generate_test_file(size_bytes, filename)
            test_files[size_name] = filepath
            print("✓")

    print()
    print("Running benchmarks...")
    print()

    test_results: list[FileSizeTest] = []

    for size_name, filepath in test_files.items():
        size_bytes = filepath.stat().st_size
        print(f"Testing {size_name} file:")
        endpoint_results: dict[str, EndpointMetrics] = {}

        for endpoint in ENDPOINTS:
            endpoint_name = endpoint.replace("/upload/", "")
            print(f"  {endpoint_name}...", end=" ", flush=True)

            try:
                result = await upload_file(endpoint, filepath)

                if "error" in result:
                    print(f"✗ {result['error']}")
                    continue

                server_response = result["server_response"]
                total_duration = result["total_duration"]
                total_memory_delta = result["total_memory_delta"]

                metrics = EndpointMetrics(
                    endpoint=endpoint_name,
                    file_size_bytes=server_response.file_size_bytes,
                    file_size_mb=server_response.file_size_mb,
                    handler_duration_seconds=server_response.handler_duration_seconds,
                    total_duration_seconds=total_duration,
                    total_throughput_mbps=server_response.file_size_mb / total_duration if total_duration > 0 else 0,
                    total_memory_delta_mb=total_memory_delta,
                    memory_start_mb=server_response.memory_start_mb,
                    memory_end_mb=server_response.memory_end_mb,
                    memory_delta_mb=server_response.memory_delta_mb,
                    client_duration=result["client_duration"],
                )

                total_throughput = server_response.file_size_mb / total_duration if total_duration > 0 else 0
                print(
                    f"✓ handler: {server_response.handler_duration_seconds:.3f}s, "
                    f"total: {total_duration:.3f}s ({total_throughput:.2f} MB/s)"
                )

                endpoint_results[endpoint_name] = metrics

            except Exception as e:
                print(f"✗ Error: {e!s}")
                continue

        test_results.append(
            FileSizeTest(
                file_size_label=size_name,
                file_size_bytes=size_bytes,
                results=endpoint_results,
            )
        )

        print()

    # Create benchmark run
    benchmark_run = BenchmarkRun(
        timestamp=datetime.now(),
        test_files=test_results,
        endpoints=ENDPOINTS,
    )

    # Save results
    save_results(benchmark_run)

    print()
    print("=" * 100)
    print("Benchmark complete! View results with: python visualize.py")
    print(f"Test files kept in {TEST_FILES_DIR}/ for reuse")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
