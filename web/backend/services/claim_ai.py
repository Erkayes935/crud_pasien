import json
import httpx
from fastapi import HTTPException
from backend import config

async def proxy_core_engine(endpoint: str, payload: dict):
    """
    Proxy request ke core_engine dengan:
    - timeout 120 detik (sesuai main.py lama)
    - logging payload (print pretty JSON)
    - mapping error httpx -> HTTPException FastAPI
    """
    timeout = httpx.Timeout(120.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            # Logging payload (dev)
            print("=== PROXY PAYLOAD ===")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            print("======================")

            url = f"{config.CORE_ENGINE_URL}{endpoint}"
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()

        except httpx.HTTPStatusError as e:
            # Teruskan status code dari core_engine + body error-nya
            raise HTTPException(
                status_code=e.response.status_code,
                detail={
                    "error": str(e),
                    "detail": e.response.text
                },
            )
        except httpx.RequestError as e:
            # Koneksi/timeout/DNS dll.
            raise HTTPException(status_code=500, detail=f"Core Engine error: {str(e)}")


async def predict_ddx(payload: dict):
    return await proxy_core_engine("/predict_ddx", payload)


async def analyze_diagnosis(payload: dict):
    return await proxy_core_engine("/analyze_diagnosis", payload)


async def analyze_procedure(payload: dict):
    return await proxy_core_engine("/analyze_procedure", payload)


async def generate_claim_combos(payload: dict):
    return await proxy_core_engine("/generate_claim_combos", payload)


async def resume_medis(payload: dict):
    return await proxy_core_engine("/resume_medis", payload)


async def regulation_detail(payload: dict):
    return await proxy_core_engine("/regulation_detail", payload)
