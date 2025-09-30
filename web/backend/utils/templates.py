from fastapi.templating import Jinja2Templates
from backend.utils.flash import get_flashed_messages

# satu-satunya instance templates global
templates = Jinja2Templates(directory="frontend/templates")

# inject helper flash messages supaya semua template bisa akses
templates.env.globals["get_flashed_messages"] = get_flashed_messages