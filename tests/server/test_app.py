from fastapi.testclient import TestClient


def test_app() -> None:
    # Local import so it does not explode
    from prbot.server.main import app

    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome on prbot!"}
