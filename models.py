from datetime import datetime

from pydantic import BaseModel, Field


class ServerResponse(BaseModel):
    """Response from server endpoints - matches what server.py returns"""

    endpoint: str
    file_size_bytes: int
    file_size_mb: float
    handler_duration_seconds: float
    memory_start_mb: float
    memory_end_mb: float
    memory_delta_mb: float


class EndpointMetrics(BaseModel):
    """Metrics for a single endpoint test"""

    endpoint: str
    file_size_bytes: int
    file_size_mb: float
    handler_duration_seconds: float
    total_duration_seconds: float = Field(description="Total request processing time including FastAPI overhead")
    total_throughput_mbps: float = Field(description="Throughput based on total duration")
    total_memory_delta_mb: float = Field(description="Memory delta measured across entire request")
    memory_start_mb: float
    memory_end_mb: float
    memory_delta_mb: float
    client_duration: float


class FileSizeTest(BaseModel):
    """All endpoint tests for a specific file size"""

    file_size_label: str  # e.g., "1KB", "10MB"
    file_size_bytes: int
    results: dict[str, EndpointMetrics]  # endpoint_name -> metrics


class BenchmarkRun(BaseModel):
    """Complete benchmark run with all file sizes and endpoints"""

    timestamp: datetime
    test_files: list[FileSizeTest]
    endpoints: list[str]
    summary: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Aggregated statistics per endpoint",
    )


class BenchmarkHistory(BaseModel):
    """Collection of benchmark runs over time"""

    runs: list[BenchmarkRun]

    def add_run(self, run: BenchmarkRun) -> None:
        """Add a new benchmark run to history"""
        self.runs.append(run)

    def get_latest(self) -> BenchmarkRun | None:
        """Get the most recent benchmark run"""
        return self.runs[-1] if self.runs else None

    def get_run_by_timestamp(self, timestamp: datetime) -> BenchmarkRun | None:
        """Get a specific benchmark run by timestamp"""
        for run in self.runs:
            if run.timestamp == timestamp:
                return run
        return None
