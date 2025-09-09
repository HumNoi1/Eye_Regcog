import httpx, time, os
from jose import jwt

JWKS_CACHE = {"exp": 0, "keys": None}

def _jwks_url():
    return f'{os.getenv("SUPABASE_PROJECT_URL")}/auth/v1/keys'

def _get_jwks():
    now = time.time()
    if JWKS_CACHE["keys"] and JWKS_CACHE["exp"] > now:
        return JWKS_CACHE["keys"]
    r = httpx.get(_jwks_url(), timeout=5)
    r.raise_for_status()
    JWKS_CACHE["keys"] = r.json()
    JWKS_CACHE["exp"] = now + 3600
    return JWKS_CACHE["keys"]

def verify_supabase_jwt(authorization: str | None = None):
    if not authorization or not authorization.startswith("Bearer "):
        raise ValueError("Missing Bearer token")
    token = authorization.split(" ", 1)[1]
    payload = jwt.decode(token, _get_jwks(), algorithms=["RS256"], options={"verify_aud": False})
    payload["_token"] = token  # ใช้เรียก REST/RLS ต่อ
    return payload  # มี 'sub' = user_id
