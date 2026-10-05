"""Regressions for false success and leaked notebook API processes."""
from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock

import pytest

from scripts import notebook_api, run_notebooks


@pytest.mark.parametrize("numbers", [["99"], ["01", "99"]])
def test_unknown_notebook_is_rejected_before_execution(monkeypatch, tmp_path, numbers):
    (tmp_path / "notebooks").mkdir()
    (tmp_path / "notebooks" / "01_example.py").write_text("# %%\nprint('ok')")
    monkeypatch.setattr(run_notebooks, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["run_notebooks.py", *numbers])
    with pytest.raises(SystemExit) as exc:
        run_notebooks.main()
    assert exc.value.code == 2
    assert not list(tmp_path.rglob("*.ipynb"))


def test_missing_notebook_sources_is_not_success(monkeypatch, tmp_path):
    monkeypatch.setattr(run_notebooks, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["run_notebooks.py"])
    with pytest.raises(SystemExit) as exc:
        run_notebooks.main()
    assert exc.value.code == 2


@pytest.fixture
def api_process(monkeypatch):
    proc = MagicMock()
    proc.poll.return_value = None
    monkeypatch.setattr(notebook_api.subprocess, "Popen", lambda *a, **k: proc)
    sock = MagicMock()
    sock.__enter__.return_value.getsockname.return_value = ("127.0.0.1", 9000)
    monkeypatch.setattr(notebook_api.socket, "socket", lambda: sock)
    response = MagicMock(status_code=200)
    response.json.return_value = {"ready": True}
    monkeypatch.setattr(notebook_api.httpx, "get", lambda *a, **k: response)
    monkeypatch.setattr(notebook_api.time, "sleep", lambda _: None)
    return proc, response


def test_api_stops_when_query_or_benchmark_fails(api_process):
    proc, _ = api_process
    with pytest.raises(RuntimeError, match="query failed"):
        with notebook_api.running_search_api(Path(".")):
            raise RuntimeError("query failed")
    proc.terminate.assert_called_once()
    proc.wait.assert_called_once_with(timeout=10)


def test_api_stops_on_readiness_timeout(api_process):
    proc, response = api_process
    response.status_code = 503
    with pytest.raises(RuntimeError, match="didn't become ready"):
        with notebook_api.running_search_api(Path("."), startup_attempts=1):
            pytest.fail("Unready API must not enter the body")
    proc.terminate.assert_called_once()
    proc.wait.assert_called_once_with(timeout=10)


def test_api_kills_process_if_graceful_stop_times_out(api_process):
    proc, _ = api_process
    proc.wait.side_effect = [subprocess.TimeoutExpired("uvicorn", 10), None]
    with notebook_api.running_search_api(Path(".")) as url:
        assert url == "http://127.0.0.1:9000"
    proc.terminate.assert_called_once()
    proc.kill.assert_called_once()
    assert proc.wait.call_count == 2
