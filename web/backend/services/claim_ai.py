import orjson
import httpx
from fastapi import HTTPException
from backend import config

async def proxy_core_engine(endpoint: str, payload: dict):
    """
    Proxy request ke core_engine (optimized)
    - pakai http2 + orjson untuk speed
    - timeout 300 detik untuk GPT/fuzzy
    """
    timeout = httpx.Timeout(300.0, connect=10.0)
    async with httpx.AsyncClient(http2=True, timeout=timeout) as client:
        try:
            url = f"{config.CORE_ENGINE_URL}{endpoint}"
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                data = await resp.aread()          # streaming read
                return orjson.loads(data)

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail={
                    "error": str(e),
                    "detail": e.response.text,
                },
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Core Engine error: {str(e)}")



async def predict_ddx(payload: dict):
    return await proxy_core_engine("/predict_ddx", payload)


async def analyze_diagnosis(payload: dict):
    return await proxy_core_engine("/analyze_diagnosis", payload)


async def analyze_procedure(payload: dict):
    return await proxy_core_engine("/analyze_procedure", payload)


async def resume_medis(payload: dict):
    return await proxy_core_engine("/resume_medis", payload)


async def regulation_detail(payload: dict):
    """
    Get regulation detail from core_engine.
    """
    try:
        field = payload.get("field", "")
        if not field:
            return {"error": "Field is required"}
        
        # ✅ Inject procedure_name dari procedure_text jika ada
        # Ini untuk backward compatibility karena DB pakai procedure_text
        # tapi regulation_service.py expect procedure_name
        if not payload.get("procedure_name") and payload.get("procedure_text"):
            payload["procedure_name"] = payload["procedure_text"]
            payload["procedure"] = payload["procedure_text"]
            print(f"[REGULATION] 💉 Injected procedure_name from procedure_text: {payload['procedure_text']}")
        
        result = await proxy_core_engine("/regulation_detail", payload)
        return result
    except Exception as e:
        print(f"[REGULATION] Error: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "data": [{
                "layer": "error",
                "sumber": "Error",
                "judul_regulasi": "Error",
                "isi": f"Terjadi kesalahan saat memuat regulasi: {str(e)}",
                "update": None,
                "status": "Error",
                "color": "#ef4444",
            }]
        }


async def generate_claim_combos(payload: dict):
    return await proxy_core_engine("/generate_claim_combos", payload)


async def generate_alternatives(payload: dict):
    """
    Proxy ke /generate_alternatives endpoint.
    Menghasilkan daftar alternatif kombinasi.
    """
    return await proxy_core_engine("/generate_alternatives", payload)


async def predict_idrg(payload: dict):
    """
    Proxy untuk prediksi i-DRG (single atau combo).
    """
    mode = payload.get("mode", "single")
    print(f"[PREDICT_IDRG] Mode: {mode}, Payload: {payload}")
    return await proxy_core_engine("/predict_idrg", payload)

async def predict_idrg_combo(payload: dict):
    """
    Proxy spesifik untuk prediksi i-DRG mode combo.
    """
    # Pastikan mode selalu combo
    payload["mode"] = "combo"
    print(f"[PREDICT_IDRG_COMBO] Payload: {payload}")
    return await proxy_core_engine("/predict_idrg", payload)
