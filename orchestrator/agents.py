import threading
import time
import random
import csv
import os
from typing import List
import requests
import subprocess
import redis

class LoadAgent:
    def __init__(self, nodes: List[str], run_id: str, rps: float = 0.0):
        """
        nodes: list of base URLs like http://localhost:8001
        run_id: used for output directory
        rps: initial requests per second
        """
        self.nodes = nodes
        self.rps = rps
        self._stop_flag = threading.Event()

        # Set up output directory and file
        self.run_dir = os.path.join("runs", run_id)
        os.makedirs(self.run_dir, exist_ok=True)
        self.metrics_path = os.path.join(self.run_dir, "metrics.csv")

        self._thread = threading.Thread(target=self._run_loop, daemon=True)

        # If file doesn't exist, create with header
        if not os.path.exists(self.metrics_path):
            with open(self.metrics_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "node", "status_code", "latency_ms", "error"])

    def start_load(self, rps: float):
        """Start load generation at given RPS."""
        self.rps = rps
        if not self._thread.is_alive():
            self._stop_flag.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def update_rps(self, rps: float):
        """Update the current RPS without restarting the thread."""
        self.rps = rps

    def stop(self):
        """Stop load generation and wait for thread to finish."""
        self._stop_flag.set()
        if self._thread.is_alive():
            self._thread.join()

    def _run_loop(self):
        """
        Simple RPS control:
        - 1 / rps seconds between attempts
        - each iteration sends 1 request to a random node
        """
        while not self._stop_flag.is_set():
            if self.rps <= 0:
                time.sleep(0.1)
                continue

            interval = 1.0 / self.rps

            node = random.choice(self.nodes)
            url = f"{node}/work"
            start = time.time()
            error = ""
            status_code = None

            try:
                resp = requests.post(url, json={"payload": "test"})
                status_code = resp.status_code
            except Exception as e:
                error = str(e)

            end = time.time()
            latency_ms = (end - start) * 1000.0

            # Log row
            with open(self.metrics_path, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([start, node, status_code, latency_ms, error])

            # Sleep until next request time
            elapsed = time.time() - start
            sleep_time = max(0.0, interval - elapsed)
            time.sleep(sleep_time)


class ControlAgent:
    """
    Controls containers via `docker compose` CLI.
    Assumes it's run from the project root where docker-compose.yml lives.
    """

    def stop_container(self, service_name: str):
        # This will stop a service defined in docker-compose.yml
        print(f"[ControlAgent] Stopping container: {service_name}")
        subprocess.run(["docker", "compose", "stop", service_name], check=False)

    def start_container(self, service_name: str):
        print(f"[ControlAgent] Starting container: {service_name}")
        subprocess.run(["docker", "compose", "start", service_name], check=False)


class RedisLoadAgent:
    """
    Similar idea to LoadAgent, but uses Redis commands instead of HTTP.

    - hosts: list of redis:// URLs, e.g. ["redis://localhost:6379", "redis://localhost:6380"]
    - logs to runs/<run_id>/redis_metrics.csv with the same schema:
      timestamp,node,status_code,latency_ms,error

    We treat status_code=200 as "success" and None for failures so we can
    reuse the same metrics/analysis pipeline.
    """

    def __init__(self, hosts, run_id: str, rps: float = 0.0):
        self.clients = [
            redis.Redis.from_url(url, decode_responses=True)
            for url in hosts
        ]
        self.hosts = hosts
        self.rps = rps
        self._stop_flag = threading.Event()

        self.run_dir = os.path.join("runs", run_id)
        os.makedirs(self.run_dir, exist_ok=True)
        self.metrics_path = os.path.join(self.run_dir, "redis_metrics.csv")

        self._thread = threading.Thread(target=self._run_loop, daemon=True)

        if not os.path.exists(self.metrics_path):
            with open(self.metrics_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "node", "status_code", "latency_ms", "error"])

    def start_load(self, rps: float):
        self.rps = rps
        if not self._thread.is_alive():
            self._stop_flag.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def update_rps(self, rps: float):
        self.rps = rps

    def stop(self):
        self._stop_flag.set()
        if self._thread.is_alive():
            self._thread.join()

    def _run_loop(self):
        while not self._stop_flag.is_set():
            if self.rps <= 0:
                time.sleep(0.1)
                continue

            interval = 1.0 / self.rps

            idx = random.randrange(len(self.clients))
            client = self.clients[idx]
            host = self.hosts[idx]

            start = time.time()
            error = ""
            status_code = None

            try:
                # simple workload: increment a key and read it back
                client.incr("orchestrator_counter")
                _ = client.get("orchestrator_counter")
                status_code = 200
            except Exception as e:
                error = str(e)

            end = time.time()
            latency_ms = (end - start) * 1000.0

            with open(self.metrics_path, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([start, host, status_code, latency_ms, error])

            elapsed = time.time() - start
            sleep_time = max(0.0, interval - elapsed)
            time.sleep(sleep_time)