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


def test_login_logout_flow(client):
    # GET login page
    resp = client.get('/login')
    assert resp.status_code == 200

    # Wrong credentials
    resp = client.post('/login', data={'username': 'x', 'password': 'y'})
    assert resp.status_code == 200  # page reload with flash

    # Correct credentials
    resp = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    assert resp.status_code == 200

    # Logout
    resp = client.get('/logout', follow_redirects=True)
    assert resp.status_code == 200


def test_metrics_endpoint(client):
    # metrics are public in create_app()
    resp = client.get('/metrics')
    assert resp.status_code == 200
    assert b'ollama_requests_total' in resp.data or len(resp.data) > 0


def test_error_handlers_render_templates(client):
    # 404
    resp = client.get('/non-existent-url')
    assert resp.status_code == 404
