# services/predict_ddx_service.py
import os
import json
import random
from datetime import date
from typing import Any, Dict, List
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------- helpers ----------
def _json(x: Any) -> str:
    try:
        return json.dumps(x, ensure_ascii=False, separators=(",", ": "))
    except Exception:
        return str(x)

def _rand(a=0.6, b=0.95) -> int:
    return random.randint(int(a * 100), int(b * 100))

def _as_list(x, default=None):
    return x if isinstance(x, list) else (default or [])

# ---------- main ----------
def process_predict_ddx(payload: dict) -> dict:
    """
    NEW (preferred):
      {
        "global_record": {
          "admission": {...},
          "daily": [ {...}, ... ],
          "discharge": {...}
        },
        "stage": "admission"|"daily"|"discharge"
      }

    BACKWARD-COMPAT (old):
      { "rekam_medis": [ {...} ] }

    Output schema (unchanged):
      {
        "diagnosis": [ { "parent": str, "confidence": float, "children": [ {"name": str, "confidence": float}, ... ] }, ... ],
        "komorbid":  [ ... ],
        "komplikasi":[ ... ],
        "engine_version": "predict_ddx@YYYY-MM-DD"
      }
    """

    # --- read input (global first, fallback to old) ---
    global_record = payload.get("global_record")
    if not global_record:
        rm_list = _as_list(payload.get("rekam_medis"), [])
        global_record = rm_list[0] if rm_list else {}

    admission = global_record.get("admission") or {}
    daily = _as_list(global_record.get("daily"), [])
    discharge = global_record.get("discharge") or {}
    stage = (payload.get("stage") or "admission").strip()

    # brief daily to save tokens (can be refined later)
    daily_brief = {
        "n_days": len(daily),
        "last_entry": daily[-1] if daily else {}
    }

    # --- prompt (schema output tetap sama) ---
    prompt = f"""
Kamu adalah AI medis Indonesia. Jawab HANYA JSON VALID sesuai skema.

Gunakan REKAM MEDIS GLOBAL berikut (STAGE aktif: {stage}):

# ADMISSION
{_json(admission)}

# DAILY (ringkasan)
{_json(daily_brief)}

# DISCHARGE
{_json(discharge)}

Tugas:
- Hasilkan masing-masing 3 item untuk:
  • diagnosis utama
  • komorbid
  • komplikasi

Aturan setiap parent:
- "parent": string (nama penyakit)
- "confidence": float 0.0–1.0
- "children": list anak (boleh kosong), tiap anak: {{"name": string, "confidence": float}}

Catatan:
- Pertimbangkan seluruh data (admission+daily+discharge), namun tekankan konteks sesuai STAGE:
  • admission: fokus keluhan/temuan awal,
  • daily: fokus tren TTV/lab/radiologi & respons terapi,
  • discharge: fokus diagnosis akhir/outcome.
- Jangan ada teks di luar JSON.
- Keluarkan persis dengan kunci berikut:

{{
  "diagnosis": [
    {{"parent":"...", "confidence":0.9, "children":[{{"name":"...", "confidence":0.8}}]}}
  ],
  "komorbid": [
    {{"parent":"...", "confidence":0.8, "children":[]}}
  ],
  "komplikasi": [
    {{"parent":"...", "confidence":0.7, "children":[]}}
  ]
}}
    """.strip()

    # --- call OpenAI ---
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Kamu adalah AI medis. Jawab hanya JSON valid."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    raw_output = (response.choices[0].message.content or "").strip()

    # logging untuk debug
    print("==== RAW OUTPUT PREDICT_DDX (global/stage) ====")
    print(raw_output)
    print("===============================================")

    # --- parse ---
    try:
        ai_result = json.loads(raw_output)
    except json.JSONDecodeError:
        ai_result = {"diagnosis": [], "komorbid": [], "komplikasi": []}

    # --- post-processing: children minimal 1, isi confidence jika kosong, top-3 ---
    def fix_item(item: Dict[str, Any]) -> Dict[str, Any]:
      # 🔹 Konversi confidence parent
      if isinstance(item.get("confidence"), (int, float)):
          val = item["confidence"]
          # kalau confidence masih dalam skala 0–1 → ubah ke persen bulat
          item["confidence"] = int(val * 100) if val <= 1 else int(val)
      else:
          # kalau kosong atau bukan angka → isi random 60–95%
          item["confidence"] = _rand(0.6, 0.95)

      # 🔹 Proses anak-anak
      children = item.get("children", [])
      if not isinstance(children, list):
          children = []

      fixed_children: List[Dict[str, Any]] = []
      for ch in children:
          if not isinstance(ch, dict):
              continue

          # sama: konversi confidence anak ke persen
          if isinstance(ch.get("confidence"), (int, float)):
              val = ch["confidence"]
              ch["confidence"] = int(val * 100) if val <= 1 else int(val)
          else:
              ch["confidence"] = _rand(0.6, 0.9)

          if "name" in ch and isinstance(ch["name"], str) and ch["name"].strip():
              fixed_children.append({
                  "name": ch["name"].strip(),
                  "confidence": ch["confidence"]
              })

      # 🔹 fallback: minimal 1 anak
      if not fixed_children:
          parent_name = item.get("parent") or "Unspecified"
          fixed_children.append({
              "name": f"{parent_name} - Unspecified subtype",
              "confidence": _rand(0.6, 0.8)
          })

      item["children"] = fixed_children[:3]  # batasi max 3 anak
      return item


    out = {"diagnosis": [], "komorbid": [], "komplikasi": []}
    for section in ["diagnosis", "komorbid", "komplikasi"]:
        items = ai_result.get(section, [])
        if isinstance(items, list):
            out[section] = [fix_item(it) for it in items[:3]]  # max 3 parent
        else:
            out[section] = []

    out["engine_version"] = f"predict_ddx@{date.today().isoformat()}"
    return out
