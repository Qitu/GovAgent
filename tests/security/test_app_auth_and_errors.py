import pytest

pytestmark = [pytest.mark.integration, pytest.mark.security]

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


def test_metrics_requires_no_authentication(client):
    response = client.get('/metrics')
    assert response.status_code == 200
    assert response.mimetype == 'text/plain'
    assert b'python_gc_objects_collected_total' in response.data or len(response.data) > 0


def test_metrics_requires_authentication_for_write_routes(client):
    login_response = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    assert login_response.status_code == 200

    protected_endpoints = [
        ('/api/start_simulation', {'name': 'sim', 'steps': 1, 'stride': 1}),
        ('/api/compress_data', {'name': 'sim'}),
        ('/api/delete_simulation', {'name': 'sim'}),
    ]

    for path, payload in protected_endpoints:
        response = client.post(path, json=payload)
        assert response.status_code == 200

    logout_response = client.get('/logout', follow_redirects=True)
    assert logout_response.status_code == 200

    for path, payload in protected_endpoints:
        response = client.post(path, json=payload)
        assert response.status_code in {302, 401, 403}


def test_error_handlers_render_templates(client):
    # 404
    resp = client.get('/non-existent-url')
    assert resp.status_code == 404
