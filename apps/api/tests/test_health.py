from api.health import health_status


def test_health_status_ok():
    assert health_status() == {"status": "ok"}
