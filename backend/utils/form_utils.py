# utils/form_utils.py
from fastapi import Request, Form, Depends
from typing import Dict

async def get_form_as_dict(request: Request) -> Dict[str, str]:
    """
    Ambil semua field dari request.form() lalu kembalikan sebagai dict.
    Otomatis handle semua field tanpa harus didefinisikan satu2 di route.
    """
    form = await request.form()
    return {k: v for k, v in form.items()}
