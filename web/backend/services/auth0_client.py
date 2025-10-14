import os
import time
import httpx
from typing import Optional

# ==========================
# ENVIRONMENT CONFIG
# ==========================
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
AUTH0_DEFAULT_CONNECTION = os.getenv("AUTH0_DEFAULT_CONNECTION", "Username-Password-Authentication")
AUTH0_SEND_INVITE = os.getenv("AUTH0_SEND_INVITE", "1") == "1"

_token_cache = {"access_token": None, "exp": 0}


# ==========================
# 1️⃣ GET MANAGEMENT TOKEN
# ==========================
async def get_mgmt_token() -> str:
    """Ambil Management API token via client_credentials"""
    now = int(time.time())
    if _token_cache["access_token"] and now < _token_cache["exp"] - 60:
        return _token_cache["access_token"]

    url = f"https://{AUTH0_DOMAIN}/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "audience": AUTH0_AUDIENCE,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=data)
        resp.raise_for_status()
        token_data = resp.json()
        _token_cache["access_token"] = token_data["access_token"]
        _token_cache["exp"] = now + int(token_data.get("expires_in", 900))
        return token_data["access_token"]


# ==========================
# 2️⃣ CREATE AUTH0 USER
# ==========================
async def create_auth0_user(email: str, name: str, password: str | None = None):
    token = await get_mgmt_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"https://{AUTH0_DOMAIN}/api/v2/users"
    payload = {
        "email": email,
        "name": name,
        "connection": AUTH0_DEFAULT_CONNECTION,
    }
    if password:
        payload["password"] = password

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code != 201:
            print("❌ Gagal buat user:", r.status_code, r.text)
        r.raise_for_status()
        return r.json()


# ==========================
# 3️⃣ SEND PASSWORD INVITE
# ==========================
async def send_password_invite(email: str, user_id: Optional[str] = None):
    """
    Kirim link "Set Password" ke email user menggunakan tiket Auth0.
    Kompatibel dengan tenant global maupun regional (JP/EU).
    """
    if not AUTH0_SEND_INVITE:
        return None

    token = await get_mgmt_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 🔹 Gunakan endpoint modern (JP/EU tenants)
    url_new = f"https://{AUTH0_DOMAIN}/api/v2/tickets/user-ticket"
    # 🔹 Fallback global (jika tenant lama)
    url_old = f"https://{AUTH0_DOMAIN}/api/v2/tickets/password-change"

    body = {
        "result_url": "https://login.healthclaim.my.id",  # Redirect setelah set password
        "mark_email_as_verified": True,
    }

    # Email atau user_id bisa digunakan, prefer user_id jika tersedia
    if user_id:
        body["user_id"] = user_id
    else:
        body["email"] = email

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # Coba endpoint modern dulu
            r = await client.post(url_new, headers=headers, json=body)
            if r.status_code == 404:
                # Jika tenant masih global, fallback ke endpoint lama
                r = await client.post(url_old, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            return data.get("ticket")
        except httpx.HTTPStatusError as e:
            print(f"❌ Gagal kirim password invite: {e.response.text}")
            raise

# ==========================
# 4️⃣ ASSIGN ROLES TO AUTH0 USER
# ==========================
async def assign_auth0_roles(user_id: str, role_names: list[str]):
    """
    Assign satu atau beberapa role ke user di Auth0 (sinkronisasi DB lokal ↔ Auth0).
    """
    if not user_id or not role_names:
        return

    token = await get_mgmt_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Ambil semua role yang ada di Auth0
    async with httpx.AsyncClient(timeout=15.0) as client:
        roles_url = f"https://{AUTH0_DOMAIN}/api/v2/roles"
        r = await client.get(roles_url, headers=headers)
        r.raise_for_status()
        all_roles = r.json()

    # Mapping nama → ID
    role_ids = [
        r["id"] for r in all_roles if r["name"].lower() in [x.lower() for x in role_names]
    ]

    if not role_ids:
        print(f"⚠️ Tidak ada role Auth0 yang cocok dengan {role_names}")
        return

    # Assign roles ke user
    assign_url = f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/roles"
    payload = {"roles": role_ids}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(assign_url, headers=headers, json=payload)
        if r.status_code not in (200, 204):
            print(f"⚠️ Gagal assign roles ke user {user_id}: {r.text}")
        else:
            print(f"✅ Role {role_names} berhasil ditambahkan ke user {user_id}")
