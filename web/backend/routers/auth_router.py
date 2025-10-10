from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from urllib.parse import urlencode
import httpx

from backend import config, models
from backend.database import get_db
from backend.utils.templates import templates

router = APIRouter()

@router.get("/welcome")
def welcome(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request})

@router.get("/login")
def login():
    params = {
        "client_id": config.CLIENT_ID,
        "response_type": "code",
        "redirect_uri": config.REDIRECT_URI,
        "scope": "openid profile email",
        "audience": config.AUDIENCE,
    }
    url = f"https://{config.AUTH0_DOMAIN}/authorize?{urlencode(params)}"
    return RedirectResponse(url)

@router.get("/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse({"error": "Missing code"}, status_code=400)

    token_url = f"https://{config.AUTH0_DOMAIN}/oauth/token"
    headers = {"content-type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET,
        "code": code,
        "redirect_uri": config.REDIRECT_URI,
    }

    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=data, headers=headers)
        if token_res.status_code != 200:
            return JSONResponse(token_res.json(), status_code=token_res.status_code)

        token_json = token_res.json()
        access_token = token_json.get("access_token")
        if not access_token:
            return JSONResponse({"error": "No access_token in response", "detail": token_json}, status_code=400)

        userinfo_res = await client.get(
            f"https://{config.AUTH0_DOMAIN}/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if userinfo_res.status_code != 200:
            return JSONResponse(userinfo_res.json(), status_code=userinfo_res.status_code)
        userinfo = userinfo_res.json()

    # cek user di DB
    user = db.query(models.User).filter_by(auth0_sub=userinfo["sub"]).first()
    if not user:
        user = models.User(
            auth0_sub=userinfo["sub"],
            email=userinfo.get("email"),
            name=userinfo.get("name"),
            role="doctor"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    request.session["user_id"] = user.id
    request.session["email"] = user.email
    request.session["name"] = user.name
    request.session["role"] = user.role

    return RedirectResponse(url="/dashboard", status_code=303)

@router.get("/logout")
def logout(request: Request):
    base_url = str(request.base_url).rstrip("/")
    params = {
        "client_id": config.CLIENT_ID,
        # arahkan balik ke halaman login lokal kamu
        "returnTo": f"{base_url}/login"
    }

    url = f"https://{config.AUTH0_DOMAIN}/v2/logout?" + urlencode(params)
    response = RedirectResponse(url)
    response.delete_cookie("id_token")
    return response
