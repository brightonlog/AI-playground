import base64
import re
import secrets

_ID_RE = re.compile(r"^(an|sh)_[a-z2-7]{8}$")


def new_id(prefix: str) -> str:
    # 5 random bytes encode to exactly 8 base32 chars.
    return f"{prefix}_{base64.b32encode(secrets.token_bytes(5)).decode().lower()}"


def is_valid_id(value: str) -> bool:
    return bool(_ID_RE.fullmatch(value))
