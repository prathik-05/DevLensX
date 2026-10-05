"""E2E test fixtures for deterministic, isolated testing."""

import pytest
import tempfile
import socket
import subprocess
import time
import requests
import os
import shutil
import sys
from pathlib import Path
from typing import Generator


def find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class IsolatedTestEnvironment:
    """Isolated test environment with dedicated resources."""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.temp_dir = tempfile.mkdtemp(prefix=f"devlensx_e2e_{test_name}_")
        self.backend_port = find_free_port()
        self.frontend_port = find_free_port()
        self.kuzu_dir = Path(self.temp_dir) / "kuzu"
        self.kuzu_dir.mkdir(parents=True, exist_ok=True)

        self.backend_proc: subprocess.Popen | None = None
        self.frontend_proc: subprocess.Popen | None = None
        self.base_url = f"http://127.0.0.1:{self.backend_port}"
        self.frontend_url = f"http://127.0.0.1:{self.frontend_port}"

    def start(self) -> None:
        """Start backend and frontend servers."""
        env = os.environ.copy()
        env["KUZU_DB_PATH"] = str(self.kuzu_dir)
        env["DEVLENSX_BACKEND_PORT"] = str(self.backend_port)
        env["DEVLENSX_FRONTEND_PORT"] = str(self.frontend_port)
        env["DEVLENSX_TEMP_DIR"] = self.temp_dir

        # Start backend with test entry point that applies Kuzu patch
        self.backend_proc = subprocess.Popen(
            [
                sys.executable, "tests/e2e/fixtures/test_backend.py"
            ],
            cwd=Path.cwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        # Wait for backend health
        self._wait_for_health(self.base_url, timeout=60)

        # Start frontend using built assets served by Python http.server
        # This is more reliable for E2E tests than the Vite dev server
        frontend_dist = Path.cwd() / "web" / "dist"
        if not frontend_dist.exists():
            print("[IsolatedEnv] Building frontend...", flush=True)
            build_result = subprocess.run(
                ["npm", "run", "build"],
                cwd=Path.cwd() / "web",
                capture_output=True,
                text=True,
                shell=(os.name == 'nt'),
                timeout=120,
            )
            if build_result.returncode != 0:
                raise RuntimeError(f"Frontend build failed: {build_result.stderr}")
            print("[IsolatedEnv] Frontend built successfully", flush=True)
        
        # Serve dist with Python http.server
        print(f"[IsolatedEnv] Starting frontend HTTP server on port {self.frontend_port}", flush=True)
        self.frontend_proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(self.frontend_port)],
            cwd=frontend_dist,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print(f"[IsolatedEnv] Frontend HTTP server started with PID {self.frontend_proc.pid}", flush=True)

        # Wait for frontend
        self._wait_for_frontend(timeout=120)

    def _wait_for_health(self, base_url: str, timeout: int = 60) -> None:
        """Wait for backend /api/health to return ok."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = requests.get(f"{base_url}/api/health", timeout=2)
                if resp.status_code == 200 and resp.json().get("status") == "ok":
                    return
            except Exception as e:
                pass
            time.sleep(0.5)
        # If we get here, print backend logs for debugging
        if self.backend_proc:
            stdout, stderr = self.backend_proc.communicate(timeout=5)
            print(f"=== BACKEND STDOUT ===\n{stdout.decode()}")
            print(f"=== BACKEND STDERR ===\n{stderr.decode()}")
        raise RuntimeError(f"Backend did not become healthy within {timeout}s")

    def _wait_for_frontend(self, timeout: int = 60) -> None:
        """Wait for frontend to serve content."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = requests.get(self.frontend_url, timeout=2)
                # The built frontend is a React SPA with minimal initial HTML
                # Check for the root div or title which are in the initial HTML
                if resp.status_code == 200 and ("root" in resp.text or "web" in resp.text):
                    return
            except Exception:
                pass
            time.sleep(0.5)
        # Print frontend logs for debugging
        if self.frontend_proc:
            try:
                stdout, stderr = self.frontend_proc.communicate(timeout=5)
                print(f"=== FRONTEND STDOUT ===\n{stdout.decode()}")
                print(f"=== FRONTEND STDERR ===\n{stderr.decode()}")
            except Exception:
                pass
        raise RuntimeError(f"Frontend did not become ready within {timeout}s")

    def analyze_repo(self, repo_path: str) -> dict:
        """Analyze a repository and return the analysis result."""
        resp = requests.post(
            f"{self.base_url}/api/analyze",
            json={"repo_path": repo_path, "inject_hallucination": False},
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json()

    def cleanup(self) -> None:
        """Terminate processes and clean up temp directory."""
        if self.backend_proc:
            self.backend_proc.terminate()
            try:
                self.backend_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.backend_proc.kill()

        if self.frontend_proc:
            self.frontend_proc.terminate()
            try:
                self.frontend_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.frontend_proc.kill()

        # Clean up temp directory
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass


@pytest.fixture(scope="function")
def isolated_env(request) -> Generator[IsolatedTestEnvironment, None, None]:
    """Fixture providing a fully isolated test environment."""
    env = IsolatedTestEnvironment(request.node.name)
    try:
        env.start()
        yield env
    finally:
        env.cleanup()


@pytest.fixture(scope="function")
def petclinic_analysis(isolated_env: IsolatedTestEnvironment) -> dict:
    """Analyze PetClinic in an isolated environment."""
    return isolated_env.analyze_repo("eval_repos/spring-petclinic")


@pytest.fixture(scope="function")
def battleship_analysis(isolated_env: IsolatedTestEnvironment) -> dict:
    """Analyze Battleship in an isolated environment."""
    return isolated_env.analyze_repo("eval_repos/battleship-python")