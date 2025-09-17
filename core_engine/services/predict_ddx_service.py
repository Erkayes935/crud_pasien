# services/predict_ddx_service.py
import os
import json
import random
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def process_predict_ddx(payload: dict) -> dict:
    """
    Generate daftar diagnosis, komorbid, komplikasi dari rekam medis.
    Output format:
    {
      "diagnosis": [
        { "parent": "...", "confidence": 0.9,
          "children": [ {"name":"...", "confidence":0.8}, ... ] }
      ],
      "komorbid": [...],
      "komplikasi": [...],
      "engine_version": "predict_ddx@2025-09-17"
    }
    """

    rekam_medis = payload.get("rekam_medis", [])

    prompt = f"""
    Berdasarkan data rekam medis berikut:
    {rekam_medis}

    Hasilkan daftar:
    - diagnosis utama (3 parent)
    - komorbid (3 parent)
    - komplikasi (3 parent)

    Setiap parent WAJIB punya field:
    - "parent": nama penyakit
    - "confidence": angka float 0.0–1.0
    - "children": daftar anak penyakit (boleh lebih dari 1)

    Setiap child WAJIB punya:
    - "name": nama penyakit turunan
    - "confidence": angka float 0.0–1.0

    Format JSON ketat, tanpa teks tambahan di luar JSON:
    {{
      "diagnosis": [
        {{"parent": "...", "confidence": 0.9, "children":[{{"name":"...", "confidence":0.8}}]}}
      ],
      "komorbid": [...],
      "komplikasi": [...]
    }}
    """

    # Request ke OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Kamu adalah AI medis. Jawab hanya JSON valid."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    raw_output = response.choices[0].message.content.strip()

    # --- Logging supaya bisa debug kalau parsing gagal ---
    print("==== RAW OUTPUT PREDICT_DDX ====")
    print(raw_output)
    print("================================")

    try:
        ai_result = json.loads(raw_output)
    except json.JSONDecodeError:
        ai_result = {"diagnosis": [], "komorbid": [], "komplikasi": []}

    # ==== fallback cleaning ====
    def fix_item(item):
        # parent confidence
        if not isinstance(item.get("confidence"), (int, float)):
            item["confidence"] = round(random.uniform(0.6, 0.95), 2)

        # children
        children = item.get("children", [])
        if not isinstance(children, list):
            children = []
        fixed_children = []
        for ch in children:
            if not isinstance(ch, dict):
                continue
            if not isinstance(ch.get("confidence"), (int, float)):
                ch["confidence"] = round(random.uniform(0.6, 0.9), 2)
            fixed_children.append(ch)
        # kalau kosong → tambahkan dummy
        if not fixed_children:
            fixed_children.append({
                "name": f"{item['parent']} - Unspecified subtype",
                "confidence": round(random.uniform(0.6, 0.8), 2)
            })
        item["children"] = fixed_children
        return item

    for section in ["diagnosis", "komorbid", "komplikasi"]:
        items = ai_result.get(section, [])
        if isinstance(items, list):
            ai_result[section] = [fix_item(it) for it in items[:3]]  # max 3 parent
        else:
            ai_result[section] = []

    ai_result["engine_version"] = "predict_ddx@2025-09-17"
    return ai_result
