"""Encriptación en reposo (AES-256-GCM) para columnas binarias sensibles.

Protege embedding/thumbnail/name contra un dump robado de la base de datos.
No protege contra un atacante que compromete el propio proceso del backend
en ejecución (tiene la clave en memoria) — ese caso queda documentado como
limitación aceptada en SECURITY.md.

Formato de salida: nonce (12 bytes) || ciphertext || tag (los últimos 16
bytes del ciphertext son el tag de GCM, ya incluidos por AESGCM.encrypt).
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_SIZE = 12


class EncryptionKeyNotConfigured(RuntimeError):
    pass


def _load_key() -> bytes:
    encoded_key = os.getenv("AURA_ENCRYPTION_KEY")
    if not encoded_key:
        raise EncryptionKeyNotConfigured(
            "AURA_ENCRYPTION_KEY no está configurada. En producción debe "
            "provenir de un secret manager, no de un .env versionado."
        )
    try:
        key = base64.b64decode(encoded_key, validate=True)
    except Exception as exc:
        raise EncryptionKeyNotConfigured(
            "AURA_ENCRYPTION_KEY debe ser una clave de 32 bytes en base64."
        ) from exc
    if len(key) != 32:
        raise EncryptionKeyNotConfigured(
            "AURA_ENCRYPTION_KEY debe decodificar a exactamente 32 bytes "
            "(AES-256)."
        )
    return key


def encrypt(plaintext: bytes) -> bytes:
    """Encripta bytes con AES-256-GCM. Devuelve nonce || ciphertext+tag."""
    aesgcm = AESGCM(_load_key())
    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)
    return nonce + ciphertext


def decrypt(payload: bytes) -> bytes:
    """Revierte encrypt(). Lanza ValueError si el payload fue alterado."""
    if len(payload) < _NONCE_SIZE:
        raise ValueError("Payload cifrado demasiado corto.")
    aesgcm = AESGCM(_load_key())
    nonce, ciphertext = payload[:_NONCE_SIZE], payload[_NONCE_SIZE:]
    return aesgcm.decrypt(nonce, ciphertext, associated_data=None)
