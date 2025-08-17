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
    jwks_url = f"https://{config.AUTH0_DOMAIN}/.well-known/jwks.json"
    return requests.get(jwks_url).json()

def verify_jwt(token: str):
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

def get_current_user(request: Request, db: Session = Depends(get_db)):
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
        def wrapper(*args, user=None, **kwargs):
            if user is None:
                raise HTTPException(status_code=401, detail="Login required")
            if user.role not in roles:
                raise HTTPException(status_code=403, detail="Forbidden: insufficient role")
            return func(*args, user=user, **kwargs)
        return wrapper
    return decorator