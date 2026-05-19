"""Dependencias de FastAPI: autenticación con Google OAuth.

El móvil hace login con Google en el cliente y envía el Google ID Token
en cada request: `Authorization: Bearer <google_id_token>`.

Aquí validamos ese token contra Google y extraemos el identificador del
usuario (google_user_id) y su email. No mantenemos tabla de usuarios:
todo se identifica por google_user_id.
"""

import os

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Esquema Bearer: hace que Swagger muestre el botón "Authorize".
bearer_scheme = HTTPBearer(auto_error=True)


class CurrentUser:
    """Usuario autenticado, extraído del Google ID Token."""

    def __init__(self, google_user_id: str, email: str | None):
        self.google_user_id = google_user_id
        self.email = email


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    """Valida el Google ID Token y devuelve el usuario actual.

    Lanza 401 si el token es inválido, expiró o no corresponde a este
    GOOGLE_CLIENT_ID.
    """
    token = credentials.credentials

    try:
        # google-auth verifica firma, expiración y audiencia (aud == client_id).
        claims = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de Google inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 'sub' es el identificador único y estable del usuario en Google.
    google_user_id = claims.get("sub")
    if not google_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no contiene un identificador de usuario",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        google_user_id=google_user_id,
        email=claims.get("email"),
    )
