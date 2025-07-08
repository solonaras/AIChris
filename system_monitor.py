import psutil
import time
import threading
import datetime

class SystemMonitor:
    def __init__(self):
        self.metrics = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_percent": 0.0,
            "uptime_string": "0d 0h 0m 0s",
        }
        self.start_time = datetime.datetime.now()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)

    def start(self):
        """Starts the background monitoring thread."""
        if not self._thread.is_alive():
            print("Starting system monitor...")
            self._thread.start()

    def stop(self):
        """Stops the background monitoring thread."""
        print("Stopping system monitor...")
        self._stop_event.set()
        self._thread.join()

    def _monitor_loop(self):
        """Continuously updates system metrics in the background."""
        while not self._stop_event.is_set():
            self.update_metrics()
            time.sleep(30) # Update every 30 seconds

    def update_metrics(self):
        """Fetches and updates the latest system metrics."""
        self.metrics["cpu_percent"] = psutil.cpu_percent(interval=1)
        self.metrics["memory_percent"] = psutil.virtual_memory().percent
        self.metrics["disk_percent"] = psutil.disk_usage('/').percent
        
        # Calculate uptime
        uptime_delta = datetime.datetime.now() - self.start_time
        total_seconds = int(uptime_delta.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.metrics["uptime_string"] = f"{days}d {hours}h {minutes}m {seconds}s"

    def get_metrics(self) -> dict:
        """Returns the latest collected metrics."""
        return self.metrics

    def get_report_string(self) -> str:
        """Returns a formatted string of the system metrics."""
        m = self.metrics
        return (
            f"CPU Load: {m['cpu_percent']:.1f}% | "
            f"Memory Usage: {m['memory_percent']:.1f}% | "
            f"Disk Usage: {m['disk_percent']:.1f}% | "
            f"Uptime: {m['uptime_string']}"
        ) 