import base64

from app.infrastructure.models import SavedObjectModel, UserSettingsModel

SAMPLE_EMBEDDING = base64.b64encode(b"\x09" * 16).decode("ascii")


def test_delete_account_purges_all_data(client, auth_headers, db_session):
    client.post("/sync/consent", headers=auth_headers)
    client.post(
        "/sync/objects/upload",
        json=[
            {
                "id": 1,
                "name": "objeto de prueba",
                "embedding": SAMPLE_EMBEDDING,
                "thumbnail": None,
                "created_at": "2026-07-16T12:00:00Z",
            }
        ],
        headers=auth_headers,
    )

    response = client.delete("/sync/account", headers=auth_headers)
    assert response.status_code == 204

    assert db_session.query(SavedObjectModel).count() == 0
    assert db_session.query(UserSettingsModel).count() == 0
