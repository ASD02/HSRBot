import re

_REGIONS = {"6": "America", "7": "Europe", "8": "Asia", "9": "Asia", "1": "CN", "2": "CN", "5": "CN"}


def validate_uid(text: str) -> tuple[str, str]:
    """Return (uid, region). Raises ValueError on anything but a 9-10 digit UID."""
    uid = text.strip()
    if not re.fullmatch(r"\d{9,10}", uid):
        raise ValueError("A UID is 9-10 digits.")
    return uid, _REGIONS.get(uid[0], "Unknown")
