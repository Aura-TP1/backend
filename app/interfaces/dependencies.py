"""Dependencias de FastAPI: autenticación con Google OAuth.

El móvil hace login con Google en el cliente y envía el Google Access Token
en cada request: `Authorization: Bearer <google_access_token>`.

Validamos ese token contra el endpoint tokeninfo de Google, que además de
devolver el identificador del usuario (sub) y su email, expone el `aud`
(client_id al que se emitió el token). Verificamos ese `aud` contra
GOOGLE_CLIENT_ID para rechazar tokens válidos de Google pero emitidos para
otra aplicación (sin este chequeo, cualquier access token de Google —
emitido para cualquier app — autenticaría contra este backend).
No mantenemos tabla de usuarios: todo se identifica por google_user_id (sub).
"""

import logging
import os

import requests as http_requests
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()

logger = logging.getLogger(__name__)

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

if not GOOGLE_CLIENT_ID:
    logger.warning(
        "GOOGLE_CLIENT_ID no está configurado: la verificación de audience "
        "de los tokens OAuth fallará (fail-closed) hasta que se configure."
    )

bearer_scheme = HTTPBearer(auto_error=True)


class CurrentUser:
    """Usuario autenticado, extraído del endpoint userinfo de Google."""

    def __init__(self, google_user_id: str, email: str | None):
        self.google_user_id = google_user_id
        self.email = email


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    """Valida el Google Access Token contra tokeninfo y devuelve el usuario.

    Lanza 401 si el token es inválido, expiró, o fue emitido para una
    aplicación distinta de GOOGLE_CLIENT_ID (audience incorrecto).
    """
    if not GOOGLE_CLIENT_ID:
        # Fail-closed: sin GOOGLE_CLIENT_ID configurado no podemos verificar
        # el audience, así que no aceptamos ningún token.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El servidor no tiene GOOGLE_CLIENT_ID configurado.",
        )

    token = credentials.credentials

    try:
        response = http_requests.get(
            GOOGLE_TOKENINFO_URL,
            params={"access_token": token},
            timeout=10,
        )
        if response.status_code != 200:
            raise ValueError(f"Google tokeninfo devolvió {response.status_code}")
        info = response.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de Google inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # 'aud' (o 'azp') identifica la app para la que se emitió el token.
    # Sin este chequeo, cualquier access token válido de Google -emitido
    # para cualquier otra aplicación- autenticaría contra este backend.
    audience = info.get("aud") or info.get("azp")
    if audience != GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no fue emitido para esta aplicación",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
