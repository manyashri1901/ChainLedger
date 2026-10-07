import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

import registry.load_registry as lr
from common.db import connect
from registry_api.server import app

client = TestClient(app)
KEY = {"X-API-Key": "dev-key"}


def test_api_rejects_missing_key():
    assert client.get("/investors").status_code == 401


def test_api_serves_registry_rows():
    resp = client.get("/fund", headers=KEY)
    assert resp.status_code == 200
    assert resp.json()[0]["total_shares"] == "800"


def test_loader_from_api_matches_csv(monkeypatch):
    monkeypatch.setenv("REGISTRY_API_URL", "http://testserver")
    monkeypatch.setattr(lr, "_fetch", lambda path: client.get(path, headers=KEY).json())
    api_conn = connect(":memory:")
    lr.load_registry(api_conn)

    monkeypatch.delenv("REGISTRY_API_URL")
    csv_conn = connect(":memory:")
    lr.load_registry(csv_conn)

    for table in ("registry_investors", "registry_holdings", "registry_fund"):
        from_api = [tuple(r) for r in api_conn.execute(f"SELECT * FROM {table} ORDER BY 1")]
        from_csv = [tuple(r) for r in csv_conn.execute(f"SELECT * FROM {table} ORDER BY 1")]
        assert from_api == from_csv