"""Fixtures compartidas: variables de entorno de test, DB SQLite en memoria
y un cliente HTTP con la autenticación de Google mockeada."""

import base64
import os
from unittest.mock import patch

# Deben estar seteadas ANTES de importar app.main / app.interfaces.dependencies,
# que leen estas variables a nivel de módulo.
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault(
    "AURA_ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode()
)
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.database import Base, get_db
from app.main import app

TEST_SUB = "test-google-user-id"
TEST_EMAIL = "user@example.com"


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _fake_tokeninfo_response(aud: str = "test-client-id", sub: str = TEST_SUB):
    class _Response:
        status_code = 200

        def json(self_inner):
            return {"aud": aud, "sub": sub, "email": TEST_EMAIL}

    return _Response()


@pytest.fixture()
def auth_headers():
    """Headers con un token que el mock de Google acepta (aud correcto)."""
    with patch(
        "app.interfaces.dependencies.http_requests.get",
        return_value=_fake_tokeninfo_response(),
    ):
        yield {"Authorization": "Bearer valid-token-for-this-app"}


@pytest.fixture()
def wrong_audience_headers():
    """Headers con un token válido de Google pero emitido para OTRA app."""
    with patch(
        "app.interfaces.dependencies.http_requests.get",
        return_value=_fake_tokeninfo_response(aud="some-other-app-client-id"),
    ):
        yield {"Authorization": "Bearer token-for-another-app"}
