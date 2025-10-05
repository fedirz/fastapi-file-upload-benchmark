# FastAPI File Upload Benchmark

Benchmarking suite for comparing different file upload handling methods in FastAPI across various file sizes.

> **Disclaimer:** Most of the code in this repository was vibe-coded with [Claude Code](https://github.com/anthropics/claude-code). Apologies for inconsistencies in code style and poor project layout.

## Overview

This project benchmarks five different approaches to handling file uploads in FastAPI:

1. **sync-file** - Synchronous route using `File()` (loads entire file into memory as bytes)
2. **async-file** - Asynchronous route using `File()` (loads entire file into memory as bytes)
3. **sync-uploadfile** - Synchronous route using `UploadFile` with sync `file.file.read()`
4. **async-uploadfile** - Asynchronous route using `UploadFile` with async `await file.read()`
5. **async-stream** - Asynchronous route using `request.stream()` for streaming upload

The benchmark tests each method across 21 file sizes ranging from 1KB to 1GB (doubling at each step) and measures:

- Handler duration (time spent in route handler)
- Total request duration (including FastAPI processing overhead)
- Throughput (MB/s)
- Memory usage (RSS memory delta)

## Key Findings

> **System Specs:** Benchmarks were performed on a MacBook Pro with Apple M3 Pro chip (12 cores: 6 performance + 6 efficiency) and 18 GB memory.

### Performance Comparison (Large Files 128MB+)

![Large File Upload Performance](plots/large_files_performance.png)

The chart above shows performance metrics for large files (128MB to 1GB):

**Throughput**: `async-stream` achieves ~1500 MB/s, significantly outperforming other methods (~750-850 MB/s)

**Memory Usage**: `async-stream` maintains minimal memory footprint (~0 MB delta), while `File()` and `UploadFile` methods accumulate memory proportional to file size (up to 1GB for 1GB files)

**Duration**: `async-stream` completes 1GB uploads in ~0.6s vs ~1.2-1.4s for other methods

> **Note**: The y-axes are somewhat skewed by the 1GB measurements dominating the scale, making smaller file sizes harder to compare. Better visualization (log scales, relative metrics, etc.) would improve readability but I didn't have time to implement it.

### Recommendations

- **For production use with large files**: Use `async-stream` with `request.stream()` for best performance and minimal memory footprint
- **For small files with simple logic**: `async-uploadfile` or `sync-uploadfile` offer good balance of simplicity and performance
- **Avoid**: `sync-file` with `File()` for large files due to high memory usage and slower performance

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

1. Clone the repository:

```bash
git clone https://github.com/fedirz/fastapi-file-upload-benchmark.git

cd fastapi-file-upload-benchmark
```

2. Create and activate virtual environment

```bash
uv venv
source .venv/bin/activate
```

3. Install dependencies using uv:

```bash
uv sync --all-extras
```

## Usage

### Running Benchmarks

1. Start the FastAPI server:

```bash
uv run python server.py
```

The server will start on `http://localhost:8000`.

2. In a separate terminal, run the benchmark client:

```bash
uv run python client.py
```

This will:

- Generate test files (1KB to 1GB) in the `test_files/` directory
- Test each endpoint with each file size
- Save results to `benchmark_results.json`
- Reuse existing test files to save time on subsequent runs

### Viewing Results

After running benchmarks, visualize the results in the terminal:

```bash
uv run python visualize.py
```

This displays:

- Total request time and throughput for each endpoint/file size combination
- Memory usage delta for each test
- Color-coded output for easy analysis

To generate performance plots for large files (128MB+):

```bash
uv run python plot_large_files.py
```

This creates a combined plot showing throughput, memory usage, and duration comparisons, saved to `plots/large_files_performance.png`

## Technical Details

### Measurement Methodology

- **Handler Duration**: Time measured inside the route handler function
- **Total Duration**: Complete request processing time measured via custom middleware (includes multipart parsing, routing, serialization, etc.)
- **Memory Usage**: RSS (Resident Set Size) memory delta measured using psutil
- **Throughput**: Calculated as `file_size_mb / total_duration_seconds`

**Why measure both handler and total duration?**

Measuring only the time spent inside the handler doesn't capture the full picture. FastAPI performs significant work outside the handler when abstractions like `File()` and `UploadFile` are used:

- **Multipart form parsing**: FastAPI parses the multipart/form-data request body before the handler is called
- **File buffering**: For `File()`, the entire file is loaded into memory as bytes before reaching the handler

By using custom middleware that measures from the start of the request to the end of the response, we capture the true end-to-end processing time that a client experiences. This is especially important when comparing different upload methods, as the preprocessing overhead varies significantly between `File()`, `UploadFile`, and `request.stream()`.

### Middleware Implementation

A custom `TimingMiddleware` captures request start time and memory before any FastAPI processing, then measures total duration and memory delta after response generation. These metrics are passed to handlers via `ContextVar` and included in response headers.

### Endpoint Implementations

1. **sync-file**: Uses `File()` which loads the entire upload into memory as `bytes` (synchronous handler)
2. **async-file**: Uses `File()` which loads the entire upload into memory as `bytes` (asynchronous handler)
3. **sync-uploadfile**: Uses `UploadFile` with synchronous `file.file.read()`
4. **async-uploadfile**: Uses `UploadFile` with asynchronous `await file.read()`
5. **async-stream**: Uses `request.stream()` to process upload in chunks without loading into memory

## Relevant Resources

- https://fastapi.tiangolo.com/tutorial/request-files/
- https://fastapi.tiangolo.com/tutorial/request-forms-and-files/
- https://stackoverflow.com/questions/73442335/how-to-upload-a-large-file-%E2%89%A53gb-to-fastapi-backend

## License

MIT
