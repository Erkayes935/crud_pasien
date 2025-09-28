from fastapi import Request

def flash(request: Request, message: str, category: str = "success"):
    if "flashes" not in request.session:
        request.session["flashes"] = []
    request.session["flashes"].append({"message": message, "category": category})

def get_flashed_messages(request: Request):
    flashes = request.session.get("flashes", [])
    request.session["flashes"] = []  # clear setelah dibaca
    return flashes
