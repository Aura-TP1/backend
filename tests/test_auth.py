def test_upload_without_token_is_401(client):
    response = client.post("/sync/objects/upload", json=[])
    assert response.status_code == 401


def test_upload_with_wrong_audience_is_401(client, wrong_audience_headers):
    response = client.post(
        "/sync/objects/upload", json=[], headers=wrong_audience_headers
    )
    assert response.status_code == 401


def test_upload_with_correct_audience_passes_auth(client, auth_headers):
    # Con audience correcto pero sin consentimiento previo, debe llegar a la
    # capa de negocio (403 por falta de consentimiento), no quedarse en 401.
    response = client.post("/sync/objects/upload", json=[], headers=auth_headers)
    assert response.status_code == 403
