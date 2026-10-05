"""Own the notebook's API process and release it even when a cell fails."""
from contextlib import contextmanager
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx


@contextmanager
def running_search_api(root: Path, startup_attempts: int = 180):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning"],
        cwd=str(root),
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(startup_attempts):
            if proc.poll() is not None:
                raise RuntimeError(f"API exited during startup: {proc.returncode}")
            try:
                response = httpx.get(f"{url}/healthz", timeout=2.0)
                if response.status_code == 200 and response.json().get("ready"):
                    break
            except httpx.HTTPError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError(f"API didn't become ready within {startup_attempts} attempts")
        yield url
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
        print("API server stopped")
