from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from jose import jwt, JWTError
from .config import get_config

LEGACY_SUB_EMAIL = "legacy_email"

class TokenDecodeError(Exception):
    pass

def create_access_token(user: Dict[str, Any], *, expires_minutes: Optional[int] = None) -> str:
    """Create a JWT access token using canonical user id in `sub` and include legacy email for backward compatibility.

    Payload layout:
      sub: canonical internal user id (preferred)
      email: user email (for convenience)
      legacy_email: duplicate email for older decoders expecting email in sub
      exp: expiry timestamp
    """
    config = get_config()
    mins = expires_minutes or config.jwt_access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=mins)
    payload = {
        "sub": user.get("id") or user.get("email"),
        "email": user.get("email"),
        LEGACY_SUB_EMAIL: user.get("email"),
        "exp": expire,
    }
    return jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)

def decode_token(token: str) -> Dict[str, Any]:
    """Decode token and return payload. Raises TokenDecodeError on failure."""
    config = get_config()
    try:
        return jwt.decode(token, config.jwt_secret_key, algorithms=[config.jwt_algorithm])
    except JWTError as e:
        raise TokenDecodeError(str(e)) from e

def extract_subject(payload: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """Return (user_id, email) from decoded payload.

    Backward compatibility: if `sub` looks like an email and no separate email present, accept it.
    If `sub` is an email but a different internal id is needed, migration code can map later.
    """
    sub = payload.get("sub")
    email = payload.get("email") or payload.get(LEGACY_SUB_EMAIL)
    # Simple heuristic: if sub contains '@' and email missing, treat as email/legacy token
    if not email and isinstance(sub, str) and "@" in sub:
        email = sub
    return sub, email
