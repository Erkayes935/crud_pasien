from fastapi.templating import Jinja2Templates
from backend.utils.flash import get_flashed_messages
import json

# satu-satunya instance templates global
templates = Jinja2Templates(directory="frontend/templates")

# inject helper flash messages supaya semua template bisa akses
templates.env.globals["get_flashed_messages"] = get_flashed_messages

# add custom filters
def from_json(value):
    """Parse JSON string to Python object"""
    try:
        if isinstance(value, str):
            return json.loads(value)
        return value
    except (json.JSONDecodeError, TypeError):
        return None

templates.env.filters["from_json"] = from_json