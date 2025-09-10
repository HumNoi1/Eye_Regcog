import secrets
import time
from typing import Dict, Tuple

# in-memory nonce (เดโม): {nonce: expire_ts}
_NONCES: Dict[str, float] = {}

DEFAULT_TTL_SEC = 60

def issue_nonce(ttl_sec: int = DEFAULT_TTL_SEC) -> Tuple[str, int]:
    nonce = secrets.token_urlsafe(16)
    expire_ts = time.time() + ttl_sec
    _NONCES[nonce] = expire_ts
    return nonce, ttl_sec

def consume_nonce(nonce: str) -> bool:
    now = time.time()
    exp = _NONCES.pop(nonce, 0)
    return exp > now