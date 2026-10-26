from cryptography.fernet import Fernet


class Vault:
    """Encrypts HoYoLAB tokens at rest."""

    def __init__(self, key: str | None):
        try:
            self._f = Fernet(key.encode() if key else b"")
        except (ValueError, TypeError):
            raise RuntimeError("FERNET_KEY not set, HoYoLAB features disabled") from None

    def encrypt(self, text: str) -> bytes:
        return self._f.encrypt(text.encode())

    def decrypt(self, blob: bytes) -> str:
        return self._f.decrypt(blob).decode()  # raises InvalidToken on wrong key / tampering
