# performance.py
import json
import os
import time
from collections import defaultdict
from typing import Dict, Any

LOG_FILE = "performance_log.jsonl"
ANALYSIS_WINDOW_SECONDS = 3600  # Analyze the last hour of performance

class PerformanceMonitor:
    def log_event(self, task_name: str, status: str, details: Dict[str, Any] = None):
        """
        Logs a performance event.
        - task_name: Name of the task (e.g., 'ollama_response', 'tts_generation').
        - status: 'success' or 'failure'.
        - details: A dictionary with any relevant context (e.g., error message).
        """
        log_entry = {
            "timestamp": time.time(),
            "task": task_name,
            "status": status,
            "details": details or {}
        }
        try:
            with open(LOG_FILE, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Error writing to performance log: {e}")

    def get_performance_summary(self) -> str:
        """
        Analyzes the performance log and returns a brief summary.
        """
        if not os.path.exists(LOG_FILE):
            return "No performance data logged yet."

        task_stats = defaultdict(lambda: {'success': 0, 'failure': 0})
        now = time.time()
        
        try:
            with open(LOG_FILE, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if (now - entry.get("timestamp", 0)) < ANALYSIS_WINDOW_SECONDS:
                            task = entry.get("task")
                            status = entry.get("status")
                            if task and status in ['success', 'failure']:
                                task_stats[task][status] += 1
                    except json.JSONDecodeError:
                        continue # Skip corrupted lines
        except Exception as e:
            return f"Error analyzing performance: {e}"

        if not task_stats:
            return "No performance events in the last hour."

        summary_lines = ["Recent Performance Analysis:"]
        for task, stats in task_stats.items():
            total = stats['success'] + stats['failure']
            if total == 0: continue
            
            success_rate = (stats['success'] / total) * 100
            summary_lines.append(f"- Task '{task}': {success_rate:.0f}% success ({stats['success']}/{total})")
        
        return " ".join(summary_lines) 