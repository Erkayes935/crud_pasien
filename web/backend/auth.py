import httpx
from fastapi import Request, HTTPException, status, Depends, Form
from jose import jwt, JWTError
from .database import SessionLocal
from . import config, models
import time
from typing import Optional, Dict, Any, Iterable, Callable
from functools import wraps
import secrets
from sqlalchemy.orm import Session

# ---------------------------
# DB dependency
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------
# JWKS fetch (async, cached)
# ---------------------------
async def get_jwk() -> Dict[str, Any]:
    """Fetch JWKS once (uncached)."""
    jwks_url = f"https://{config.AUTH0_DOMAIN}/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(jwks_url)
    resp.raise_for_status()
    return resp.json()

class _JWKSCache:
    def __init__(self, ttl_seconds: int = 600):
        self.ttl = ttl_seconds
        self._cached: Optional[Dict[str, Any]] = None
        self._expires_at: float = 0.0
        self._etag: Optional[str] = None

    async def get(self) -> Dict[str, Any]:
        now = time.time()
        if self._cached and now < self._expires_at:
            return self._cached
        jwks_url = f"https://{config.AUTH0_DOMAIN}/.well-known/jwks.json"
        headers = {}
        if self._etag:
            headers["If-None-Match"] = self._etag
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(jwks_url, headers=headers)
        if resp.status_code == 304 and self._cached:
            self._expires_at = now + self.ttl
            return self._cached
        resp.raise_for_status()
        self._cached = resp.json()
        self._expires_at = now + self.ttl
        self._etag = resp.headers.get("ETag")
        return self._cached

_JWKS = _JWKSCache(ttl_seconds=getattr(config, "JWKS_TTL", 600))

def _find_rsa_key(jwks: Dict[str, Any], token: str) -> Dict[str, str]:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Missing 'kid' in token header")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return {
                "kty": key.get("kty"), "kid": key.get("kid"), "use": key.get("use"),
                "n": key.get("n"), "e": key.get("e")
            }
    raise HTTPException(status_code=401, detail="Signing key not found for given 'kid'")

# ---------------------------
# Token verification
# ---------------------------
async def verify_jwt_secure(token: str) -> dict:
    try:
        jwks = await _JWKS.get()
        rsa_key = _find_rsa_key(jwks, token)
        return jwt.decode(
            token,
            rsa_key,
            algorithms=getattr(config, "ALGORITHMS", ["RS256"]),
            audience=getattr(config, "AUDIENCE", None),
            issuer=f"https://{config.AUTH0_DOMAIN}/",
            options={"verify_at_hash": False, "leeway": getattr(config, "JWT_LEEWAY", 10)},
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}") from e
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"JWKS fetch error: {e}") from e

def get_token_from_request(request: Request) -> str:
    token = request.cookies.get("id_token")
    if token:
        return token
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split()[1]
    raise HTTPException(status_code=401, detail="Login required")

async def get_current_user_secure(request: Request, db: Session = Depends(get_db)) -> models.User:
    token = get_token_from_request(request)
    payload = await verify_jwt_secure(token)
    user = db.query(models.User).filter_by(auth0_sub=payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ---------------------------
# Session-based deps
# ---------------------------
def current_user_session(request: Request):
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return {
        "user_id": uid,
        "sub": request.session.get("sub"),
        "email": request.session.get("email"),
        "roles": request.session.get("roles", []),
    }

def require_roles_session(*allowed_roles: str):
    """
    Dependency untuk memeriksa session dan role user.
    Kompatibel dengan sistem multi-role (user_roles) dan legacy (role string dengan koma).
    """
    def _dep(request: Request, db: Session = Depends(get_db)):
        uid = request.session.get("user_id")
        if not uid:
            print("🚫 [AUTH] Tidak ada user_id di session")
            raise HTTPException(status_code=401, detail="Not authenticated")

        user = db.query(models.User).get(uid)
        if not user:
            print(f"🚫 [AUTH] User dengan id={uid} tidak ditemukan di DB")
            raise HTTPException(status_code=401, detail="User not found")

        # --- Ambil semua role user ---
        user_roles = []

        # 1️⃣ dari relasi multi-role
        if user.role_names:
            for r in user.role_names:
                # jika masih ada koma di satu string
                user_roles.extend([x.strip() for x in str(r).split(",") if x.strip()])

        # 2️⃣ fallback ke kolom role (legacy)
        elif user.role:
            user_roles = [r.strip() for r in user.role.split(",") if r.strip()]

        # Simpan ke session untuk FE
        request.session["roles"] = user_roles

        print("🧩 [AUTH DEBUG]")
        print(f"  🔸 user.id      = {user.id}")
        print(f"  🔸 user.email   = {user.email}")
        print(f"  🔸 user.role    = {user.role}")
        print(f"  🔸 user.role_names = {user.role_names}")
        print(f"  🔸 Detected roles = {user_roles}")
        print(f"  🔸 Allowed roles  = {allowed_roles}")

        # --- Validasi role ---
        if allowed_roles and not any(r in user_roles for r in allowed_roles):
            print("🚫 [AUTH] Akses ditolak: tidak cocok dengan allowed_roles")
            raise HTTPException(status_code=403, detail="Forbidden")

        print("✅ [AUTH] Akses diizinkan, lanjut ke endpoint")
        return user

    return _dep


# ---------------------------
# CSRF helpers
# ---------------------------
def issue_csrf_token(request: Request) -> str:
    """Generate a CSRF token and store it in session."""
    token = secrets.token_urlsafe(32)
    request.session["csrf_token"] = token
    return token


async def require_csrf_dep(request: Request):
    """Validate CSRF token sent from HTML form."""
    form = await request.form()
    form_token = form.get("csrf_token")
    session_token = request.session.get("csrf_token")

    # Debugging (optional)
    # print("🧩 CSRF debug — form:", form_token, "| session:", session_token)

    if not session_token or not form_token or form_token != session_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token invalid")

    # Optional: one-time use, remove it
    request.session.pop("csrf_token", None)
    return True

async def require_csrf_json(request: Request):
    """Validate CSRF token sent from JSON headers (for AJAX requests)."""
    # Try multiple header variations
    token_from_header = (
        request.headers.get("X-CSRF-Token") or 
        request.headers.get("X-CSRFToken") or 
        request.headers.get("csrf-token")
    )
    session_token = request.session.get("csrf_token")

    # Debugging
    print(f"🧩 CSRF JSON debug — header: {token_from_header} | session: {session_token}")

    if not session_token or not token_from_header or token_from_header != session_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token invalid")

    # Don't remove token for JSON requests (might be used multiple times)
    return True
def verify_jwt(token: str, expected_aud: str) -> dict:
    jwks = httpx.get(
        f"https://{config.AUTH0_DOMAIN}/.well-known/jwks.json", timeout=10.0
    ).json()
    header = jwt.get_unverified_header(token)
    key = next(k for k in jwks["keys"] if k["kid"] == header["kid"])
    rsa_key = {
        "kty": key.get("kty"),
        "kid": key.get("kid"),
        "use": key.get("use"),
        "n": key.get("n"),
        "e": key.get("e"),
    }
    return jwt.decode(
        token,
        rsa_key,
        algorithms=config.ALGORITHMS,
        audience=expected_aud,
        issuer=f"https://{config.AUTH0_DOMAIN}/",
        options={"verify_at_hash": False},
    )
