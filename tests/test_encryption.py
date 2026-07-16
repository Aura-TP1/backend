import pytest

from app.infrastructure import encryption


def test_round_trip():
    plaintext = b"embedding-bytes-1234567890"
    ciphertext = encryption.encrypt(plaintext)

    assert ciphertext != plaintext
    assert encryption.decrypt(ciphertext) == plaintext


def test_different_nonce_each_call():
    plaintext = b"same-plaintext"
    a = encryption.encrypt(plaintext)
    b = encryption.encrypt(plaintext)

    assert a != b  # nonce aleatorio -> ciphertext distinto aunque el plaintext sea igual


def test_tampered_ciphertext_fails_to_decrypt():
    ciphertext = bytearray(encryption.encrypt(b"secret"))
    ciphertext[-1] ^= 0xFF  # corrompe el último byte (parte del tag GCM)

    with pytest.raises(Exception):
        encryption.decrypt(bytes(ciphertext))
