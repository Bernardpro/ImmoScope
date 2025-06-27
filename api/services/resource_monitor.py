import logging
import time
from typing import Callable

import psutil
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResourceMetrics:
    def __init__(self):
        self.process = psutil.Process()
        self.start_cpu_percent = 0
        self.end_cpu_percent = 0
        self.start_memory = 0
        self.end_memory = 0
        self.cpu_times_start = None
        self.cpu_times_end = None

    def start_monitoring(self):
        # Capture CPU percentage (average over 0.1 second interval)
        self.start_cpu_percent = self.process.cpu_percent(interval=0.1)
        # Capture CPU times for more detailed analysis
        self.cpu_times_start = self.process.cpu_times()
        # Capture memory (RSS: Resident Set Size)
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        # logger.info(
        #     "Request started - Initial metrics:"
        #     f"\nCPU Usage: {self.start_cpu_percent}%"
        #     f"\nMemory: {self.start_memory:.2f}MB"
        #     f"\nSystem CPU times: User={self.cpu_times_start.user:.2f}s, System={self.cpu_times_start.system:.2f}s"
        # )

    def stop_monitoring(self):
        # Capture final metrics
        self.end_cpu_percent = self.process.cpu_percent(interval=0.1)
        self.cpu_times_end = self.process.cpu_times()
        self.end_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        # logger.info(
        #     "Request finished - Final metrics:"
        #     f"\nCPU Usage: {self.end_cpu_percent}%"
        #     f"\nMemory: {self.end_memory:.2f}MB"
        #     f"\nSystem CPU times: User={self.cpu_times_end.user:.2f}s, System={self.cpu_times_end.system:.2f}s"
        # )

    @property
    def cpu_usage(self):
        """Calculate total CPU time used (user + system)"""
        cpu_user = self.cpu_times_end.user - self.cpu_times_start.user
        cpu_system = self.cpu_times_end.system - self.cpu_times_start.system
        return cpu_user + cpu_system

    @property
    def cpu_percent_change(self):
        """Calculate the change in CPU percentage"""
        return self.end_cpu_percent - self.start_cpu_percent

    @property
    def memory_usage(self):
        """Calculate memory change in MB"""
        return self.end_memory - self.start_memory

    def get_detailed_metrics(self):
        """Return detailed metrics as a dictionary"""
        return {
            "cpu_percent": self.cpu_percent_change,
            "cpu_time_total": self.cpu_usage,
            "cpu_time_user": self.cpu_times_end.user - self.cpu_times_start.user,
            "cpu_time_system": self.cpu_times_end.system - self.cpu_times_start.system,
            "memory_change_mb": self.memory_usage,
            "carbon_footprint": self.estimate_carbon_footprint(),
        }

    def estimate_carbon_footprint(self, kwh_per_cpu_hour=0.0006):
        """
        Estimate carbon footprint based on CPU usage
        More accurate estimation using both CPU time and percentage
        """
        cpu_hours = self.cpu_usage / 3600  # convert to hours
        # Adjust based on CPU percentage utilization
        cpu_utilization = (self.start_cpu_percent + self.end_cpu_percent) / 2 / 100
        kwh_consumed = cpu_hours * kwh_per_cpu_hour * cpu_utilization
        co2_per_kwh = 0.475  # kg CO2 per kWh (world average)
        return kwh_consumed * co2_per_kwh


class ResourceMonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        metrics = ResourceMetrics()

        # Start monitoring
        metrics.start_monitoring()
        start_time = time.time()

        # Execute request
        response = await call_next(request)

        # Stop monitoring
        metrics.stop_monitoring()
        process_time = time.time() - start_time

        # Get detailed metrics
        detailed_metrics = metrics.get_detailed_metrics()

        # Add metrics to response headers
        response.headers.update(
            {
                "X-Process-Time": f"{process_time:.4f}s",
                "X-CPU-Usage": f"{detailed_metrics['cpu_time_total']:.4f}s",
                "X-CPU-Percent": f"{detailed_metrics['cpu_percent']:.1f}%",
                "X-Memory-Usage": f"{detailed_metrics['memory_change_mb']:.2f}MB",
                "X-Carbon-Footprint": f"{detailed_metrics['carbon_footprint']:.8f}kg CO2",
            }
        )

        # Log detailed metrics
        # logger.info(
        #     f"Request completed - Path: {request.url.path}"
        #     f"\nProcess time: {process_time:.4f}s"
        #     f"\nCPU usage: {detailed_metrics['cpu_time_total']:.4f}s"
        #     f"\nCPU %: {detailed_metrics['cpu_percent']:.1f}%"
        #     f"\nMemory change: {detailed_metrics['memory_change_mb']:.2f}MB"
        #     f"\nCarbon footprint: {detailed_metrics['carbon_footprint']:.8f}kg CO2"
        # )

        return response
