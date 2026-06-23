"""Dependencias de FastAPI: autenticación con Google OAuth.

El móvil hace login con Google en el cliente y envía el Google Access Token
en cada request: `Authorization: Bearer <google_access_token>`.

Aquí validamos ese token llamando al endpoint userinfo de Google, que
devuelve el identificador del usuario (sub) y su email.
No mantenemos tabla de usuarios: todo se identifica por google_user_id (sub).
"""

import os

import requests as http_requests
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()

GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

bearer_scheme = HTTPBearer(auto_error=True)


class CurrentUser:
    """Usuario autenticado, extraído del endpoint userinfo de Google."""

    def __init__(self, google_user_id: str, email: str | None):
        self.google_user_id = google_user_id
        self.email = email


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    """Valida el Google Access Token llamando a userinfo y devuelve el usuario.

    Lanza 401 si el token es inválido o expiró.
    """
    token = credentials.credentials

    try:
        response = http_requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if response.status_code != 200:
            raise ValueError(f"Google userinfo devolvió {response.status_code}")
        info = response.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de Google inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # 'sub' es el identificador único y estable del usuario en Google.
    google_user_id = info.get("sub")
    if not google_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no contiene un identificador de usuario",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        google_user_id=google_user_id,
        email=info.get("email"),
    )
