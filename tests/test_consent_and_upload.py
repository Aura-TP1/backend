import base64

from app.infrastructure.models import SavedObjectModel

SAMPLE_EMBEDDING = base64.b64encode(b"\x01\x02\x03" * 8).decode("ascii")
SAMPLE_NAME = "llaves de casa"


def _sample_object(object_id: int = 1):
    return {
        "id": object_id,
        "name": SAMPLE_NAME,
        "embedding": SAMPLE_EMBEDDING,
        "thumbnail": None,
        "created_at": "2026-07-16T12:00:00Z",
    }


def test_upload_without_consent_is_forbidden(client, auth_headers):
    response = client.post(
        "/sync/objects/upload", json=[_sample_object()], headers=auth_headers
    )
    assert response.status_code == 403


def test_consent_then_upload_succeeds_and_encrypts_at_rest(
    client, auth_headers, db_session
):
    consent_response = client.post("/sync/consent", headers=auth_headers)
    assert consent_response.status_code == 200
    assert consent_response.json()["consent_given"] is True

    upload_response = client.post(
        "/sync/objects/upload", json=[_sample_object()], headers=auth_headers
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["synced"] == 1

    # El valor crudo en la "base de datos" no debe ser el plaintext.
    row = db_session.query(SavedObjectModel).filter_by(id=1).first()
    assert row is not None
    assert row.name != SAMPLE_NAME.encode("utf-8")
    assert row.embedding != base64.b64decode(SAMPLE_EMBEDDING)

    # Pero el download debe devolver los valores originales, desencriptados.
    download_response = client.get("/sync/objects/download", headers=auth_headers)
    assert download_response.status_code == 200
    [obj] = download_response.json()
    assert obj["name"] == SAMPLE_NAME
    assert obj["embedding"] == SAMPLE_EMBEDDING


def test_revoke_consent_blocks_future_uploads(client, auth_headers):
    client.post("/sync/consent", headers=auth_headers)
    client.delete("/sync/consent", headers=auth_headers)

    response = client.post(
        "/sync/objects/upload", json=[_sample_object()], headers=auth_headers
    )
    assert response.status_code == 403
