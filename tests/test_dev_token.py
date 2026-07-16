"""Los endpoints /dev/token solo deben existir con ENVIRONMENT=development.

En cualquier otro entorno (incluida producción) no deben registrarse -
antes filtraban el último token OAuth visto a cualquiera que los llamara.
"""

import importlib
import os

import app.main as app_main_module


def test_dev_token_endpoints_absent_by_default(client):
    assert client.get("/dev/token").status_code == 404
    assert client.post("/dev/token", json={"token": "x"}).status_code == 404


def test_dev_token_endpoints_present_only_in_development():
    from fastapi.testclient import TestClient

    original_environment = os.environ.get("ENVIRONMENT")
    os.environ["ENVIRONMENT"] = "development"
    try:
        importlib.reload(app_main_module)
        with TestClient(app_main_module.app) as dev_client:
            assert (
                dev_client.post("/dev/token", json={"token": "abc"}).status_code
                == 200
            )
            get_response = dev_client.get("/dev/token")
            assert get_response.status_code == 200
            assert get_response.json() == {"token": "abc"}
    finally:
        if original_environment is None:
            os.environ.pop("ENVIRONMENT", None)
        else:
            os.environ["ENVIRONMENT"] = original_environment
        importlib.reload(app_main_module)
