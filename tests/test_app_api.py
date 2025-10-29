import json
from types import SimpleNamespace

import pytest

from generative_agents.app import create_app


@pytest.fixture()
def app():
    app = create_app()
    app.config.update({"TESTING": True, "WTF_CSRF_ENABLED": False, "SECRET_KEY": "test"})
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def login_session(client):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "tester"


def test_get_status(client):
    login_session(client)
    resp = client.get("/api/get_status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(["running", "current_simulation", "progress", "last_output", "last_error"]).issubset(data.keys())


def test_start_simulation_background_thread_and_subprocess(monkeypatch, client):
    login_session(client)

    # Fake subprocess.run to avoid executing real command
    class DummyResult:
        def __init__(self):
            self.stdout = "ok"
            self.stderr = ""
            self.returncode = 0
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: DummyResult())

    # Make Thread run target immediately without real threading
    class DummyThread:
        def __init__(self, target):
            self._target = target
            self.daemon = True
        def start(self):
            self._target()
    monkeypatch.setattr("threading.Thread", lambda target: DummyThread(target))

    payload = {"name": "sim-x", "steps": 1, "stride": 1}
    resp = client.post("/api/start_simulation", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] in {"success", "error"}


def test_compress_and_delete_simulation(monkeypatch, client, tmp_path):
    login_session(client)

    # Prepare fake files
    base = tmp_path / "results" / "checkpoints" / "abc"
    base.mkdir(parents=True)
    (base / "conversation.json").write_text("{}", encoding="utf-8")

    # Monkeypatch os.path.exists to map to tmp folder
    import os
    orig_exists = os.path.exists
    def fake_exists(path):
        path = str(path)
        path = path.replace("results/checkpoints/abc", str(base))
        path = path.replace("results/compressed/abc", str(tmp_path / "results" / "compressed" / "abc"))
        return orig_exists(path)
    monkeypatch.setattr(os.path, "exists", fake_exists)

    # Fake subprocess.run for compression
    class DummyResult:
        def __init__(self, returncode=0):
            self.stdout = "compressed"
            self.stderr = ""
            self.returncode = returncode
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: DummyResult(0))

    resp = client.post("/api/compress_data", json={"name": "abc"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] in {"success", "error"}

    # Create directories for deletion
    comp = tmp_path / "results" / "compressed" / "abc"
    comp.mkdir(parents=True, exist_ok=True)

    # Patch shutil.rmtree to operate on the mapped tmp paths
    import shutil as _shutil
    orig_rmtree = _shutil.rmtree
    def fake_rmtree(path):
        path = str(path)
        path = path.replace("results/checkpoints/abc", str(base))
        path = path.replace("results/compressed/abc", str(comp))
        return orig_rmtree(path)
    monkeypatch.setattr(_shutil, "rmtree", fake_rmtree)

    resp2 = client.post("/api/delete_simulation", json={"name": "abc"})
    assert resp2.status_code == 200
    assert resp2.get_json()["status"] == "success"
