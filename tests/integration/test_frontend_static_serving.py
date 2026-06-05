from fastapi.testclient import TestClient

import app.main as main_module


def build_frontend_dist(tmp_path):
    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<!doctype html><html><body>frontend-shell</body></html>", encoding="utf-8")
    (assets_dir / "app.js").write_text("console.log('frontend-asset');", encoding="utf-8")
    return dist_dir


def test_root_serves_frontend_index_when_dist_exists(tmp_path, monkeypatch):
    dist_dir = build_frontend_dist(tmp_path)
    monkeypatch.setattr(main_module, "FRONTEND_DIST_DIR", dist_dir)
    client = TestClient(main_module.app)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "frontend-shell" in response.text


def test_spa_routes_fall_back_to_frontend_index(tmp_path, monkeypatch):
    dist_dir = build_frontend_dist(tmp_path)
    monkeypatch.setattr(main_module, "FRONTEND_DIST_DIR", dist_dir)
    client = TestClient(main_module.app)

    response = client.get("/runs/run-123")

    assert response.status_code == 200
    assert "frontend-shell" in response.text


def test_built_assets_are_served_from_frontend_dist(tmp_path, monkeypatch):
    dist_dir = build_frontend_dist(tmp_path)
    monkeypatch.setattr(main_module, "FRONTEND_DIST_DIR", dist_dir)
    client = TestClient(main_module.app)

    response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert "frontend-asset" in response.text
