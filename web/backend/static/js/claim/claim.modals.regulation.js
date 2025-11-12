// ============================================================
// claim.modals.regulation.js (Lossless Refactor, Dark/Light Mode Ready)
// ============================================================
// Mengelola seluruh logika tampilan multilayer regulasi AI-Claim.
// Overlay/modal tetap dikelola oleh claim.modals.core.js
// ============================================================

import { openOverlayModal } from "./claim.modals.core.js";

// ======================================================
// 🔹 FEEDBACK REGULASI (Global Access Function)
// ======================================================
function showFeedbackModalForRegulasi(ruleId, layer) {
  try {
    if (typeof showFeedbackModal === "function") {
      showFeedbackModal({ id: ruleId, layer_name: layer });
    } else {
      console.warn("⚠️ showFeedbackModal belum terdefinisi di global scope.");
    }
  } catch (err) {
    console.error("❌ Gagal memanggil showFeedbackModal:", err);
  }
}

// ============================================================
// 🏛️ Helper Layer
// ============================================================

export function getLayerLabel(layer) {
  const labels = {
    nasional: "🇮🇩 Nasional",
    pnpk: "📘 PNPK",
    fornas: "💊 Fornas",
    permenkes: "⚖️ Permenkes",
    ppk_rs: "🏥 PPK RS",
    regional: "🗺️ Regional",
    rs_lokal: "🏠 RS Lokal",
    bridging: "🔗 Bridging",
    fraud: "🚨 Fraud",
    temporary: "🧩 Temporary",
    unknown: "🕵️‍♀️ Tidak Dikenal" // tambahkan ini
  };
  return labels[layer?.toLowerCase()] || layer;
}

export function getLayerColorClass(layer) {
  const base = layer?.toLowerCase();
  switch (base) {
    case "nasional":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100";
    case "pnpk":
      return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-100";
    case "fornas":
      return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100";
    case "permenkes":
      return "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100";
    case "ppk_rs":
      return "bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-100";
    case "regional":
      return "bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-100";
    case "rs_lokal":
      return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100";
    case "bridging":
      return "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-100";
    case "fraud":
      return "bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-100";
    case "temporary":
      return "bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-100";
    default:
      return "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100";
  }
}

export function normalizeId(id) {
  if (!id) return null;
  const parsed = parseInt(id);
  return isNaN(parsed) ? null : parsed;
}

// ============================================================
// 📋 Field Map & Checker
// ============================================================

export const REGULATION_FIELDS = {
  diagnosis: [
    "justifikasi", "justifikasi_faskes", "syarat_klinis",
    "kode_icd", "kode_ganda", "z_code", "kode_bpjs_khusus",
    "indikasi", "kriteria", "lama_rawat",
    "tingkat_faskes", "kompetensi_faskes",
    "indikasi_rujukan", "kriteria_rujukan", "tujuan_rujukan",
    "kode", "deskripsi", "tarif"
  ],
  procedure: [
    "syarat_klinis", "status",
    "ina_cbg", "faskes", "rawat_inap"
  ],
  lainnya: [
    "program_nasional",
    "kewenangan_dokter",
    "pelaporan_wajib",
    "kewenangan_pelaksana",
    "syarat_fasilitas",
    "kombinasi_eksklusi",
    "aspek_lainnya",
    "mnt"
  ]
};

export function checkFieldHasRegulation(field) {
  try {
    if (!field) return false;
    // Semua field dianggap valid untuk kategori 'lainnya'
    return true;
  } catch (err) {
    console.warn("⚠️ checkFieldHasRegulation error:", err);
    return false;
  }
}


// ============================================================
// 🧩 Renderer
// ============================================================

export function renderRegulationDetailMultilayer(field, rules) {
  if (!rules || rules.length === 0) {
    return `<div class="text-gray-500 dark:text-gray-400 italic">Tidak ada regulasi ditemukan untuk field ${field}.</div>`;
  }

  const sections = rules.map(rule => {
    const layer = rule.layer || "Unknown";
    const isi = rule.isi || "-";
    const sumber = rule.sumber || "-";
    const tahun = rule.tahun || "-";
    const konteks = rule.konteks_penggunaan || "-";

    const colorClass = getLayerColorClass(layer);
    const layerLabel = getLayerLabel(layer);

    return `
      <div class="rounded-lg border border-slate-200 dark:border-slate-700 p-3 mb-3 shadow-sm bg-white dark:bg-slate-800">
        <div class="flex justify-between items-center mb-2">
          <span class="px-3 py-1 text-xs font-semibold rounded-full ${colorClass}">${layerLabel}</span>
          <span class="text-xs text-gray-500 dark:text-gray-400">${tahun}</span>
        </div>
        <div class="text-sm leading-snug text-gray-800 dark:text-gray-200 whitespace-pre-line">${isi}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400 mt-2 italic">
          <span>📖 ${sumber}</span> — <span>${konteks}</span>
        </div>
      </div>
    `;
  }).join("");

  return `
    <div class="space-y-2">
      <h3 class="text-center text-lg font-bold text-blue-600 dark:text-blue-300 mb-4">
        Regulasi Multilayer: ${field}
      </h3>
      ${sections}
    </div>
  `;
}

export function renderRegulationDetailReadOnly(field, rules) {
  if (!rules || rules.length === 0) return "<em>Tidak ada data regulasi</em>";

  return rules.map(r => {
    const colorClass = getLayerColorClass(r.layer);
    const label = getLayerLabel(r.layer);
    return `
      <div class="p-2 mb-2 border-l-4 rounded ${colorClass}">
        <div class="font-semibold">${label}</div>
        <div class="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-line">${r.isi || "-"}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400 mt-1 italic">
          ${r.sumber ? `📄 ${r.sumber}` : ""} ${r.tahun ? `(${r.tahun})` : ""}
        </div>
      </div>
    `;
  }).join("");
}

// ============================================================
// 🔍 Modal Handler
// ============================================================

export async function openRegulationDetailModal(
  field,
  diagnosisId = null,
  procedureId = null,
  layer = null
) {
  try {
    // --------------------------------------------------------
    // 🔹 Ambil konteks klaim & identitas RS
    // --------------------------------------------------------
    const rsId = window.claimState?.rs_id || "rs_notopuro";
    const regionId = window.claimState?.region_id || "jatim";
    const root = document.getElementById("claimRoot");
    const claimId =
      root?.dataset.claimId ||
      document.getElementById("claimForm")?.dataset.claimId ||
      window.claimState?.currentClaimId ||
      window.claimState?.id ||
      null;

    console.log("[DEBUG] claimId detected:", claimId);
    const userRole = window.claimState?.role || "doctor";

    // --------------------------------------------------------
    // 🔹 Deteksi konteks field secara dinamis (tanpa hardcode)
    // --------------------------------------------------------
    let scope = "lainnya"; // default fallback
    if (field) {
      const f = field.toLowerCase();
      if (REGULATION_FIELDS.diagnosis.some(k => f.includes(k))) scope = "diagnosis";
      else if (REGULATION_FIELDS.procedure.some(k => f.includes(k))) scope = "procedure";
      else scope = "lainnya";
    }

    // Role-based override
    if (["verifikator", "admin_rs", "superadmin"].includes(userRole)) {
      scope = scope + "_eval";
    }

    // --------------------------------------------------------
    // 🔹 Siapkan payload ke backend
    // --------------------------------------------------------
    // 🩵 Tambahan penting:
    const currentDiagnosis = window.currentDiagnosisName 
      || window.selectedDiagnosisName 
      || document.querySelector("[data-diagnosis-name]")?.dataset.diagnosisName 
      || null;

    const currentProcedure = window.currentProcedureName 
      || window.selectedProcedureName 
      || document.querySelector("[data-procedure-name]")?.dataset.procedureName 
      || null;


    const payload = {
      claim_id: claimId,
      field,
      scope,
      diagnosis_id: diagnosisId,
      procedure_id: procedureId,
      diagnosis_name: currentDiagnosis,
      procedure_name: currentProcedure,
      rs_id: rsId,
      region_id: regionId,
      layer,
    };

    console.log("[REGULATION_DETAIL] 🔄 Payload:", payload);

    // --------------------------------------------------------
    // 🔹 Fetch regulasi dari backend
    // --------------------------------------------------------
    const res = await fetch("/claims/regulation/detail", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();

    // beberapa endpoint backend kirim data di `data`, kadang langsung array
    const rules = Array.isArray(json?.data) ? json.data : json || [];
    console.log("[REGULATION_DETAIL] ✅ Diterima:", rules);

    // --------------------------------------------------------
    // 🔹 Render hasil regulasi multilayer
    // --------------------------------------------------------
    const content = renderRegulationDetailMultilayer(field, rules);
    const title = `Regulasi: ${field}`;

    // Gunakan scope yang sudah ditentukan di atas, tanpa variabel lama
    const sourceType = scope?.replace("_eval", "") || "lainnya";
    const sourceId = diagnosisId || procedureId || null;

    openOverlayModal(title, content, sourceType, sourceId);

  } catch (err) {
    console.error("❌ Gagal memuat detail regulasi:", err);
    const fallback = `
      <div class="p-6 text-center">
        <p class="text-red-500 font-semibold mb-2">
          Gagal Memuat Detail Regulasi
        </p>
        <p class="text-gray-600 dark:text-gray-300 mb-3">
          Terjadi kesalahan saat mengambil data dari server.
        </p>
        <button onclick="window.closeOverlayModal()"
                class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          Tutup
        </button>
      </div>`;
    openOverlayModal("Error", fallback, "error", null);
  }
}



// ============================================================
// 🌐 Window Shim (kompatibilitas lama)
// ============================================================

if (typeof window !== "undefined") {
  window.showFeedbackModalForRegulasi = showFeedbackModalForRegulasi;
  window.getLayerLabel = getLayerLabel;
  window.getLayerColorClass = getLayerColorClass;
  window.renderRegulationDetailMultilayer = renderRegulationDetailMultilayer;
  window.renderRegulationDetailReadOnly = renderRegulationDetailReadOnly;
  window.openRegulationDetailModal = openRegulationDetailModal;
  window.checkFieldHasRegulation = checkFieldHasRegulation;
}
