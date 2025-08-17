"""
Module: backend.auth

Contains minimal Auth0/JWT verification helpers and a small role-based
authorization decorator. `get_current_user` reads the `id_token` cookie,
verifies the token against Auth0 JWKS, and resolves a local `User` record.

Notes:
- JWKS fetching should be cached in production to avoid per-request network
    latency and outages.
- The `require_role` decorator assumes route handlers accept a `user`
    keyword argument (FastAPI dependency injection provides it via
    `Depends(get_current_user)`).
"""

from fastapi import Request, HTTPException, status, Depends, Form
from functools import wraps
from jose import jwt
from .database import SessionLocal
from . import config, models
import requests
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_jwk():
    """Fetch the JWKS document from Auth0.

    Returns the parsed JSON. In production this should be cached to avoid
    network calls on every token verification.
    """

    jwks_url = f"https://{config.AUTH0_DOMAIN}/.well-known/jwks.json"
    return requests.get(jwks_url).json()

def verify_jwt(token: str) -> dict:
    try:
        jwks = get_jwk()
        header = jwt.get_unverified_header(token)
        key = next(k for k in jwks["keys"] if k["kid"] == header["kid"])
        return jwt.decode(
            token,
            key,
            algorithms=config.ALGORITHMS,
            audience=config.AUDIENCE,
            issuer=f"https://{config.AUTH0_DOMAIN}/"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    """Resolve the current logged-in user from the `id_token` cookie.

    Raises HTTPException(401) when not logged in or when the user cannot be
    found in the local database.
    """
    token = request.cookies.get("id_token")
    if not token:
        raise HTTPException(status_code=401, detail="Login required")
    payload = verify_jwt(token)
    user = db.query(models.User).filter_by(auth0_sub=payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_role(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, user: models.User | None = None, **kwargs):
            if user is None:
                raise HTTPException(status_code=401, detail="Login required")
            if user.role not in roles:
                raise HTTPException(status_code=403, detail="Forbidden: insufficient role")
            return func(*args, user=user, **kwargs)
        return wrapper
    return decorator