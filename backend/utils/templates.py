from fastapi.templating import Jinja2Templates
from backend.utils.flash import get_flashed_messages
from datetime import datetime
from zoneinfo import ZoneInfo

# ============================================================
# Satu-satunya instance templates global
# ============================================================
templates = Jinja2Templates(directory="frontend/templates")

# Inject helper flash messages supaya semua template bisa akses
templates.env.globals["get_flashed_messages"] = get_flashed_messages


# ============================================================
# 🕐 Custom Jinja Filter: Konversi UTC → WIB (Asia/Jakarta)
# ============================================================
def to_wib(dt: datetime):
    """Konversi datetime UTC ke waktu lokal WIB."""
    if not dt:
        return ""
    try:
        # pastikan timezone aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        local = dt.astimezone(ZoneInfo("Asia/Jakarta"))
        return local.strftime("%Y-%m-%d %H:%M") + " WIB"
    except Exception:
        return str(dt)


# Daftarkan filter ke environment Jinja
templates.env.filters["to_wib"] = to_wib
