import base64, requests
from backend import config

def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def _fetch_jwks():
    resp = requests.get(
        f"https://{config.AUTH0_DOMAIN}/.well-known/jwks.json",
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()

ISSUER = lambda: f"https://{config.AUTH0_DOMAIN}/"
ALGS = ["RS256"]