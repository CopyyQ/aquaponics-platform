from app.main import app


def test_http_device_telemetry_ingestion_is_not_exposed() -> None:
    paths = {path for route in app.routes if (path := getattr(route, "path", None))}
    assert "/device-api/v1/telemetry" not in paths
