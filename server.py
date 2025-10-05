from contextvars import ContextVar
import time
from typing import Annotated

from fastapi import FastAPI, File, Request, Response, UploadFile
import psutil
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from models import ServerResponse

app = FastAPI()

# Chunk size for file reading (0.25 MB)
# This size was chosen to match the typical chunk size emitted by request.stream()
# for a more fair comparison between different upload methods
CHUNK_SIZE = 256 * 1024

# Context variables to store timing information
request_start_time: ContextVar[float] = ContextVar("request_start_time")
request_start_memory: ContextVar[float] = ContextVar("request_start_memory")


def get_memory_usage_mb() -> float:
    """Get current process memory usage in MB"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to capture total request processing time including FastAPI overhead"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Capture timing and memory BEFORE any FastAPI processing
        start_time = time.perf_counter()
        start_memory = get_memory_usage_mb()

        # Store in context for route handlers to access
        request_start_time.set(start_time)
        request_start_memory.set(start_memory)

        # Process request
        response = await call_next(request)

        # Calculate total request metrics
        end_time = time.perf_counter()
        end_memory = get_memory_usage_mb()
        total_duration = end_time - start_time

        # Add timing headers for inspection
        response.headers["X-Total-Duration"] = str(total_duration)
        response.headers["X-Total-Memory-Delta"] = str(end_memory - start_memory)

        return response


# Add middleware
app.add_middleware(TimingMiddleware)


@app.post("/upload/sync-file")
def upload_sync_file(file: Annotated[bytes, File()]) -> ServerResponse:
    """Sync route with File() - FastAPI loads entire file into memory before handler"""
    # Get middleware timing
    start_memory = request_start_memory.get()

    # Handler timing starts here
    handler_start_time = time.perf_counter()

    # File is already in memory as bytes (loaded by FastAPI, cannot be chunked)
    file_size = len(file)

    handler_end_time = time.perf_counter()
    end_memory = get_memory_usage_mb()
    handler_duration = handler_end_time - handler_start_time

    return ServerResponse(
        endpoint="sync-file",
        file_size_bytes=file_size,
        file_size_mb=file_size / 1024 / 1024,
        handler_duration_seconds=handler_duration,
        memory_start_mb=start_memory,
        memory_end_mb=end_memory,
        memory_delta_mb=end_memory - start_memory,
    )


@app.post("/upload/async-file")
async def upload_async_file(file: Annotated[bytes, File()]) -> ServerResponse:
    """Async route with File() - FastAPI loads entire file into memory before handler"""
    # Get middleware timing
    start_memory = request_start_memory.get()

    # Handler timing starts here
    handler_start_time = time.perf_counter()

    # File is already in memory as bytes (loaded by FastAPI, cannot be chunked)
    file_size = len(file)

    handler_end_time = time.perf_counter()
    end_memory = get_memory_usage_mb()
    handler_duration = handler_end_time - handler_start_time

    return ServerResponse(
        endpoint="async-file",
        file_size_bytes=file_size,
        file_size_mb=file_size / 1024 / 1024,
        handler_duration_seconds=handler_duration,
        memory_start_mb=start_memory,
        memory_end_mb=end_memory,
        memory_delta_mb=end_memory - start_memory,
    )


@app.post("/upload/sync-uploadfile")
def upload_sync_uploadfile(file: UploadFile) -> ServerResponse:
    """Sync route with UploadFile using sync chunked reading"""
    start_memory = request_start_memory.get()

    # Handler timing starts here
    handler_start_time = time.perf_counter()

    # Read file synchronously in chunks using the underlying file object
    file_size = 0
    while chunk := file.file.read(CHUNK_SIZE):
        file_size += len(chunk)

    handler_end_time = time.perf_counter()
    end_memory = get_memory_usage_mb()
    handler_duration = handler_end_time - handler_start_time

    return ServerResponse(
        endpoint="sync-uploadfile",
        file_size_bytes=file_size,
        file_size_mb=file_size / 1024 / 1024,
        handler_duration_seconds=handler_duration,
        memory_start_mb=start_memory,
        memory_end_mb=end_memory,
        memory_delta_mb=end_memory - start_memory,
    )


@app.post("/upload/async-uploadfile")
async def upload_async_uploadfile(file: UploadFile) -> ServerResponse:
    """Async route with UploadFile using async chunked reading"""
    start_memory = request_start_memory.get()

    # Handler timing starts here
    handler_start_time = time.perf_counter()

    # Read file asynchronously in chunks
    file_size = 0
    while chunk := await file.read(CHUNK_SIZE):
        file_size += len(chunk)

    handler_end_time = time.perf_counter()
    end_memory = get_memory_usage_mb()
    handler_duration = handler_end_time - handler_start_time

    return ServerResponse(
        endpoint="async-uploadfile",
        file_size_bytes=file_size,
        file_size_mb=file_size / 1024 / 1024,
        handler_duration_seconds=handler_duration,
        memory_start_mb=start_memory,
        memory_end_mb=end_memory,
        memory_delta_mb=end_memory - start_memory,
    )


@app.post("/upload/async-stream")
async def upload_async_stream(request: Request) -> ServerResponse:
    """Async route using request.stream() with async processing"""
    # Get middleware timing
    start_memory = request_start_memory.get()
    # Handler timing starts here
    handler_start_time = time.perf_counter()

    # Process stream asynchronously (no file writing, just consume the data)
    file_size = 0
    async for chunk in request.stream():
        file_size += len(chunk)

    handler_end_time = time.perf_counter()
    end_memory = get_memory_usage_mb()
    handler_duration = handler_end_time - handler_start_time

    return ServerResponse(
        endpoint="async-stream",
        file_size_bytes=file_size,
        file_size_mb=file_size / 1024 / 1024,
        handler_duration_seconds=handler_duration,
        memory_start_mb=start_memory,
        memory_end_mb=end_memory,
        memory_delta_mb=end_memory - start_memory,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
