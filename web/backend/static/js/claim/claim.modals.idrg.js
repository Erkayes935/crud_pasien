// ==================================================
// 🧠 AI-CLAIM FRONTEND MODULE: I-DRG MODALS (FINAL REFACTORED)
// ==================================================

// ==================================================
// 1️⃣ HELPER FUNCTIONS
// ==================================================

export function getPrediction(field) {
  try {
    if (this?.data?.idrg_prediction) {
      return this.data.idrg_prediction[field] || "-";
    }
    const data = window.claimState?.currentDiagnosis?.idrg_prediction || {};
    return data[field] || "-";
  } catch (err) {
    console.error("Error in getPrediction:", err);
    return "-";
  }
}

export function getSeverityLabel(index) {
  const labels = {
    "1": "Minor (Level 1)",
    "2": "Moderate (Level 2)",
    "3": "Major (Level 3)",
    "4": "Extreme (Level 4)"
  };
  return labels[index] || index || "-";
}

// ============================================================
// 🔹 RENDER CHECKLIST HTML (Versi Panjang dari Diagnosis)
// ============================================================
export function renderChecklistHtml(checklist) {
  if (!checklist) return "-";

  let items = [];
  if (typeof checklist === "string") {
    items = checklist.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  } else if (Array.isArray(checklist)) {
    items = checklist.slice();
  } else {
    return checklist;
  }

  const cleaned = items.map(item => {
    let s = String(item).trim();
    s = s.replace(/^[•\-\*\u2022]\s*/, "");
    s = s.replace(/\s*•\s*/g, " • ").replace(/\s{2,}/g, " ").trim();
    return s;
  }).filter(Boolean);

  if (cleaned.length === 0) return "-";

  const html = cleaned.map(it => {
    const itemText = it.startsWith("•") ? it.replace(/^•\s*/, "") : it;
    return `<li>${itemText}</li>`;
  }).join("");

  return `<ul class="list-disc pl-4">${html}</ul>`;
}

export function renderFaktorSeverityHtml(faktor) {
  if (!faktor) return "-";
  if (Array.isArray(faktor) && faktor.length > 0) {
    return `<ul class="list-none pl-0">${faktor.map(item => `<li>• ${item}</li>`).join("")}</ul>`;
  } else if (typeof faktor === "string") {
    return faktor;
  }
  return "-";
}

// ==================================================
// 2️⃣ PREDICT I-DRG LOGIC
// ==================================================

export async function predictIdrgForDiagnosis(claimId, diagnosisName) {
  console.log("🤖 Predicting i-DRG for diagnosis:", diagnosisName);

  try {
    const currentDiagnosis = window.claimState?.currentDiagnosis || {};
    const payload = {
      mode: "single",
      claim_id: parseInt(claimId),
      diagnosis_name: diagnosisName,
      diagnosis_data: {
        justifikasi: currentDiagnosis.klinis?.justifikasi || currentDiagnosis.justifikasi || "",
        bukti_klinis: currentDiagnosis.klinis?.bukti_klinis || currentDiagnosis.bukti_klinis || "",
        tindakan: currentDiagnosis.tindakan || []
      }
    };

    console.log("[REQ] POST /predict_idrg", payload);

    const response = await fetch(`/claims/${claimId}/predict_idrg`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!response.ok)
      throw new Error(`Server responded with ${response.status}: ${response.statusText}`);

    const json = await response.json();
    console.log("[RESP] /predict_idrg (raw)", json);

    let idrgPrediction = json?.data?.idrg_prediction || json?.idrg_prediction || json.data || json;
    if (json?.data && (json.data.group_idrg || json.data.severity_index)) {
      idrgPrediction = json.data;
    }

    const normalized = {
      status: "success",
      data: {
        idrg_prediction: idrgPrediction,
        engine_version: json.engine_version || json.data?.engine_version || "predict_idrg@local",
        diagnosis: json.diagnosis || diagnosisName || ""
      }
    };

    const p = normalized.data.idrg_prediction || {};
    if (!p.estimasi_tarif_idrg && p.estimasi_tarif) p.estimasi_tarif_idrg = p.estimasi_tarif;
    if (!p.gap_analysis && (p.gap_vs_cbg || p.gap)) p.gap_analysis = p.gap_vs_cbg || p.gap;
    if (p.checklist_dokumentasi && typeof p.checklist_dokumentasi === "string") {
      const lines = p.checklist_dokumentasi.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
      p.checklist_dokumentasi = lines.length > 1 ? lines : p.checklist_dokumentasi;
    }

    console.log("[RESP] /predict_idrg (normalized)", normalized);
    return normalized;
  } catch (error) {
    console.error("❌ Error predicting i-DRG:", error);
    throw error;
  }
}

// ==================================================
// 3️⃣ REFRESH PREDICTION
// ==================================================

export async function refreshIdrgPrediction(claimId, diagnosisName) {
  try {
    const result = await predictIdrgForDiagnosis(claimId, diagnosisName);
    const idrgSection = document.querySelector('[x-data*="open: false, loading: false, data: null"]');
    if (idrgSection) {
      const alpineData = Alpine.$data(idrgSection);
      alpineData.data = result;
      alpineData.loading = false;
      alpineData.error = null;
    }
    console.log("✅ i-DRG prediction refreshed successfully");
  } catch (error) {
    console.error("❌ Error refreshing i-DRG prediction:", error);
    alert("Gagal refresh prediksi i-DRG: " + error.message);
  }
}

// ==================================================
// 4️⃣ RENDER I-DRG SECTION (DIAGNOSIS MODAL)
// ==================================================

export function renderIdrgSection(idrg, claimId, diagnosisName = null) {
  if (!claimId) {
    const claimRoot = document.getElementById("claimRoot");
    claimId = claimRoot?.dataset.claimId || "";
  }
  if (!diagnosisName) {
    diagnosisName = window.claimState?.currentDiagnosis?.diagnosis_text || "";
  }

  const renderPredictionRow = (label, valueHtml) => `
    <div class="grid grid-cols-2">
      <div class="bg-white dark:bg-slate-700 text-gray-800 dark:text-gray-100 px-3 py-2 font-medium">${label}</div>
      <div class="bg-white dark:bg-slate-700 text-gray-800 dark:text-gray-100 px-3 py-2">${valueHtml}</div>
    </div>`;

  const renderExistingRow = (label, value, fieldName = null) => {
    let content = value || "-";
    if (fieldName && value && checkFieldHasRegulation(fieldName)) {
      content = `
        <span class="cursor-pointer hover:underline hover:text-blue-600 border-b border-dashed border-gray-400 hover:border-blue-600 transition-all duration-200"
              title="📋 Klik untuk melihat regulasi ${fieldName}"
              data-field="${fieldName}"
              onclick="openRegulationDetailModal('${fieldName}', null, 'idrg')">${value}</span>`;
    }
    return `
      <div class="grid grid-cols-2">
        <div class="bg-white dark:bg-slate-700 text-gray-800 dark:text-gray-100 px-3 py-2 font-medium">${label}</div>
        <div class="bg-white text-gray-900 dark:bg-gray-600 dark:text-gray-100 px-3 py-2">${content}</div>
      </div>`;
  };

  return `
    <div x-data="{
      open: false,
      loading: false,
      data: null,
      error: null,
      async toggleAndPredict() {
        this.open = !this.open;
        if (this.open && !this.data && !this.loading && !this.error) {
          this.loading = true;
          try {
            console.log('🤖 Auto-predicting i-DRG on section open');
            const result = await predictIdrgForDiagnosis('${claimId}', '${diagnosisName}');
            this.data = result;
            console.log('🔍 i-DRG prediction result:', result);
          } catch (err) {
            this.error = err.message;
            console.error('Prediction error:', err);
          } finally {
            this.loading = false;
          }
        }
      }
    }">
      <div class="flex items-center justify-between bg-blue-600 text-white px-3 py-2 font-bold cursor-pointer"
          @click="toggleAndPredict()">
        <span>i-DRG</span>
        <span class="flex items-center">
          <span x-show="loading" class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
          <span x-text="open ? '▼' : '▶'"></span>
        </span>
      </div>

      <div x-show="open" x-transition>
        <div x-show="loading" class="p-4 text-center">
          <div class="inline-flex items-center">
            <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mr-3"></div>
            <span class="text-blue-600 font-medium">Menganalisis dengan OpenAI...</span>
          </div>
        </div>

        <template x-if="!loading && data?.data?.idrg_prediction">
          <div class="p-3 mb-2 border-l-4 rounded text-sm flex items-start gap-2"
            :class="{
              'bg-green-100 border-green-500 text-green-800': data.data.idrg_prediction.notifications?.idrg?.status === 'success',
              'bg-yellow-100 border-yellow-500 text-yellow-800': data.data.idrg_prediction.notifications?.idrg?.status === 'warning',
              'bg-red-100 border-red-500 text-red-800': data.data.idrg_prediction.notifications?.idrg?.status === 'error',
              'bg-blue-100 border-blue-500 text-blue-800': !data.data.idrg_prediction.notifications?.idrg?.status
            }">
            <span class="text-lg" 
              x-text="{
                'success':'✅','warning':'⚠️','error':'❌'
              }[data.data.idrg_prediction.notifications?.idrg?.status] || 'ℹ️'"></span>
            <div>
              <strong>Notifikasi AI (i-DRG)</strong>
              <div class="text-xs mt-0.5"
                x-text="data.data.idrg_prediction.notifications?.idrg?.message || data.data.idrg_prediction.notification?.message || '-'"></div>
            </div>
          </div>
        </template>

        <template x-if="!loading && data?.data?.idrg_prediction">
          <div class="space-y-2 p-4">
            ${renderPredictionRow("Kode i-DRG", "<span x-text='data.data.idrg_prediction.group_idrg || \"-\"'></span>")}
            ${renderPredictionRow("Severity Index", "<span x-text='getSeverityLabel(data.data.idrg_prediction.severity_index) || \"-\"'></span>")}
            ${renderPredictionRow("Checklist Dokumentasi", "<span x-html='renderChecklistHtml(data.data.idrg_prediction.checklist_dokumentasi)'></span>")}
            ${renderPredictionRow("Faktor Penentu Severity", "<span x-html='renderFaktorSeverityHtml(data.data.idrg_prediction.faktor_penentu_severity)'></span>")}
            ${renderPredictionRow("Ungroupable Alert", "<span x-text='data.data.idrg_prediction.ungroupable_alert || \"-\"'></span>")}
            ${renderPredictionRow("Estimasi Tarif", "<span x-text='formatRupiah(data.data.idrg_prediction.estimasi_tarif_idrg)'></span>")}
            ${renderPredictionRow("Gap Analysis", "<span x-text='formatRupiah(data.data.idrg_prediction.gap_analysis)'></span>")}
          </div>
        </template>

        <div x-show="!loading && error" class="p-4 bg-red-50 border border-red-200 rounded m-4">
          <div class="flex items-center text-red-700">
            <span class="text-xl mr-3">❌</span>
            <span class="font-semibold">Error Prediksi i-DRG:</span>
          </div>
          <div class="mt-2 text-sm text-red-600" x-text="error"></div>
          <button
            @click="loading = true; error = null; predictIdrgForDiagnosis('${claimId}', '${diagnosisName}').then(result => { data = result; loading = false; }).catch(err => { error = err.message; loading = false; })"
            class="mt-3 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm">
            🔄 Coba Lagi
          </button>
        </div>

        ${
          idrg
            ? `<div class="p-4 space-y-2 border-t" x-show="!loading">
                <h3 class="font-bold text-gray-800 dark:text-gray-200 mb-2">Data i-DRG Tersimpan</h3>
                ${renderExistingRow("Group i-DRG", idrg.group_idrg || "", "idrg_diagnosis_group")}
                ${renderExistingRow("Severity Index", idrg.severity_index || "", "idrg_diagnosis_severity")}
                ${renderExistingRow("Checklist Dokumentasi", idrg.checklist || "", "idrg_diagnosis_checklist")}
                ${renderExistingRow("Faktor Severity", idrg.faktor_severity || "")}
                ${renderExistingRow("Ungroupable Alert", idrg.ungroupable_alert || "", "idrg_diagnosis_ungroupable")}
                ${renderExistingRow("Simulasi Tarif", idrg.simulasi_tarif || "")}
                ${renderExistingRow("Gap Analysis", idrg.gap_analysis || "")}
              </div>`
            : ""
        }
      </div>
    </div>`;
}

// ==================================================
// 5️⃣ RENDER STATIC PREDICTION RESULT
// ==================================================

export function renderIdrgPredictionResult(data) {
  if (!data || !data.idrg_prediction) {
    return `<div class="p-4 text-red-500">Data prediksi i-DRG tidak lengkap</div>`;
  }

  const prediction = data.idrg_prediction;
  const severityLabel = {
    "1": "Minor (1)",
    "2": "Moderate (2)",
    "3": "Major (3)",
    "4": "Extreme (4)"
  };

  const renderPredictionRow = (label, value, isClickable = false) => {
    const content = isClickable
      ? `<span class="cursor-pointer hover:underline hover:text-blue-600">${value}</span>`
      : value || "-";
    return `
      <div class="grid grid-cols-2">
        <div class="bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-white px-3 py-2 font-medium">${label}</div>
        <div class="bg-white text-gray-900 dark:bg-gray-600 dark:text-gray-100 px-3 py-2">${content}</div>
      </div>`;
  };

  const checklistHtml = renderChecklistHtml(prediction.checklist_dokumentasi);
  const faktorSeverityHtml = renderFaktorSeverityHtml(prediction.faktor_penentu_severity);

  return `
    <div class="space-y-2 p-4">
      ${renderPredictionRow("Kode i-DRG", prediction.group_idrg || "-", true)}
      ${renderPredictionRow("Severity Index", severityLabel[prediction.severity_index] || prediction.severity_index || "-", true)}
      ${renderPredictionRow("Checklist Dokumentasi", checklistHtml)}
      ${renderPredictionRow("Faktor Penentu Severity", faktorSeverityHtml)}
      ${renderPredictionRow("Ungroupable Alert", prediction.ungroupable_alert || "-")}
      ${renderPredictionRow("Estimasi Tarif", "<span>" + formatRupiah(prediction.estimasi_tarif_idrg || 0) + "</span>")}
      ${renderPredictionRow("Gap Analysis", "<span>" + formatRupiah(prediction.gap_analysis || 0) + "</span>")}
      <div class="text-xs text-blue-600 dark:text-blue-300 mt-3 p-2 rounded border border-blue-100 dark:border-blue-700 bg-white dark:bg-gray-800">
        <strong>Engine:</strong> ${data.engine_version || "OpenAI GPT-4"} •
        <strong>Mode:</strong> Single Diagnosis •
        <strong>Diagnosis:</strong> ${data.diagnosis || "-"} •
        <strong>Generated:</strong> ${new Date().toLocaleString()}
      </div>
    </div>`;
}

// ==================================================
// 6️⃣ GLOBAL EXPORT GUARD
// ==================================================

if (typeof window !== "undefined") {
  window.getPrediction = getPrediction;
  window.getSeverityLabel = getSeverityLabel;
  window.renderChecklistHtml = renderChecklistHtml;
  window.renderFaktorSeverityHtml = renderFaktorSeverityHtml;
  window.predictIdrgForDiagnosis = predictIdrgForDiagnosis;
  window.refreshIdrgPrediction = refreshIdrgPrediction;
  window.renderIdrgSection = renderIdrgSection;
  window.renderIdrgPredictionResult = renderIdrgPredictionResult;
}
