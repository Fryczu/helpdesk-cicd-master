def test_health_endpoint_reports_application_and_database_ready(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_version_endpoint_returns_build_metadata(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "test-version")
    monkeypatch.setenv("GIT_COMMIT", "abc1234")

    response = client.get("/version")

    assert response.status_code == 200
    assert response.get_json() == {
        "application": "HelpDesk",
        "version": "test-version",
        "commit": "abc1234",
    }
