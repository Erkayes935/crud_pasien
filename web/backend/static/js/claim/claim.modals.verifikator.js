// ==================================================
// 🧾 AI-CLAIM FRONTEND MODULE: VERIFICATOR MODALS
// ==================================================

// ==================================================
// 1️⃣ MAIN FETCH FUNCTIONS (MODALS)
// ==================================================

export async function showStoredDiagnosisModalVerificator(diagnosisName) {
  if (!diagnosisName) {
    alert("❌ Nama diagnosis tidak ditemukan");
    return;
  }

  console.log("🔍 [VERIFICATOR] Loading stored diagnosis data for:", diagnosisName);

  try {
    const claimId = document.querySelector("[data-claim-id]")?.dataset.claimId;
    if (!claimId) throw new Error("Claim ID tidak ditemukan");

    const container = document.getElementById("modalContainer");
    if (container) {
      container.classList.remove("hidden");
      container.innerHTML = `
        <div class="modal-content p-6 text-center bg-white dark:bg-slate-800 rounded-xl shadow-lg">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p class="mt-2 text-gray-600 dark:text-gray-400">Memuat data diagnosis...</p>
        </div>`;
    }

    const response = await fetch(`/claims/${claimId}/stored-diagnosis-detail/${encodeURIComponent(diagnosisName)}`, {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

    const data = await response.json();
    console.log("✅ [VERIFICATOR] Stored diagnosis data loaded:", data);

    openModal(
      `<div class="flex items-center">
        <span class="text-lg font-bold">🔍 Detail Diagnosis: ${diagnosisName}</span>
        <span class="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">READ-ONLY</span>
      </div>`,
      renderDiagnosisDetailReadOnly(data)
    );

    window.claimState.currentDiagnosis = data;
  } catch (error) {
    console.error("❌ [VERIFICATOR] Failed to load stored diagnosis data:", error);
    openModal(
      `🔍 Detail Diagnosis: ${diagnosisName}`,
      `<div class="text-center py-8 text-red-500">
        <p>❌ Gagal memuat data diagnosis</p>
        <p class="text-sm mt-2">${error.message}</p>
      </div>`
    );
  }
}

export async function showStoredProcedureModalVerificator(procedureName) {
  if (!procedureName) {
    alert("❌ Nama tindakan tidak ditemukan");
    return;
  }

  console.log("🔧 [VERIFICATOR] Loading stored procedure data for:", procedureName);

  try {
    const claimId = document.querySelector("[data-claim-id]")?.dataset.claimId;
    if (!claimId) throw new Error("Claim ID tidak ditemukan");

    const container = document.getElementById("modalContainer");
    if (container) {
      container.classList.remove("hidden");
      container.innerHTML = `
        <div class="modal-content p-6 text-center bg-white dark:bg-slate-800 rounded-xl shadow-lg">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
          <p class="mt-2 text-gray-600 dark:text-gray-400">Memuat data tindakan...</p>
        </div>`;
    }

    openModal(
      `<div class="flex items-center">
        <span class="text-lg font-bold">🔧 Detail Tindakan: ${procedureName}</span>
        <span class="ml-2 px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">READ-ONLY</span>
      </div>`,
      `<div class="text-center py-8">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
        <p class="mt-2 text-gray-600 dark:text-gray-400">Memuat data tindakan...</p>
      </div>`
    );

    const response = await fetch(`/claims/${claimId}/stored-procedure-detail/${encodeURIComponent(procedureName)}`, {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

    const data = await response.json();
    console.log("✅ [VERIFICATOR] Stored procedure data loaded:", data);

    openModal(
      `<div class="flex items-center">
        <span class="text-lg font-bold">🔧 Detail Tindakan: ${procedureName}</span>
        <span class="ml-2 px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">READ-ONLY</span>
      </div>`,
      renderProcedureDetailReadOnly(data)
    );

    window.claimState.currentProcedure = data;
  } catch (error) {
    console.error("❌ [VERIFICATOR] Failed to load stored procedure data:", error);
    openModal(
      `🔧 Detail Tindakan: ${procedureName}`,
      `<div class="text-center py-8 text-red-500">
        <p>❌ Gagal memuat data tindakan</p>
        <p class="text-sm mt-2">${error.message}</p>
      </div>`
    );
  }
}

export async function showStoredRegulationModalVerificator(fieldName, context = "general") {
  if (!fieldName) {
    alert("❌ Field name tidak ditemukan");
    return;
  }

  console.log("📋 [VERIFICATOR] Loading stored regulation data for:", fieldName);

  try {
    const claimId = document.querySelector("[data-claim-id]")?.dataset.claimId;
    if (!claimId) throw new Error("Claim ID tidak ditemukan");

    openModal(
      `<div class="flex items-center">
        <span class="text-lg font-bold">📋 Detail Regulasi: ${fieldName}</span>
        <span class="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs">READ-ONLY</span>
      </div>`,
      `<div class="text-center py-8">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-600"></div>
        <p class="mt-2 text-gray-600 dark:text-gray-400">Memuat data regulasi...</p>
      </div>`,
      { hideDefaultClose: false }
    );

    const response = await fetch(`/claims/${claimId}/stored-regulation-detail/${encodeURIComponent(fieldName)}`, {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

    const data = await response.json();
    console.log("✅ [VERIFICATOR] Stored regulation data loaded:", data);

    openModal(
      `<div class="flex items-center">
        <span class="text-lg font-bold">📋 Detail Regulasi: ${fieldName}</span>
        <span class="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs">READ-ONLY</span>
      </div>`,
      renderRegulationReadOnly(data, "detail"),
      { hideDefaultClose: false }
    );
  } catch (error) {
    console.error("❌ [VERIFICATOR] Failed to load stored regulation data:", error);
    openModal(
      `📋 Detail Regulasi: ${fieldName}`,
      `<div class="text-center py-8 text-red-500">
        <p>❌ Gagal memuat data regulasi</p>
        <p class="text-sm mt-2">${error.message}</p>
      </div>`
    );
  }
}

// ==================================================
// 2️⃣ RENDERERS (READ-ONLY SECTIONS)
// ==================================================

export function renderDiagnosisDetailReadOnly(data) {
  const detail = data.data || {};
  const klinis = detail.klinis || {};
  const icd10 = detail.icd10 || {};
  const faskes = detail.faskes || {};
  const rawat = detail.rawat_inap || {};
  const rujukan = detail.rujukan || {};
  const inacbg = detail.inaCbg || {};
  const idrg = detail.idrg_prediction || {};
  const regulasi = detail.regulasi || [];
  const aspek_lainnya = detail.aspek_lainnya || {};

  const fieldRow = (label, value, fieldName = null, context = "diagnosis", diagnosisId = null) => {
    const safeValue = value && value !== "" ? value : "-";
    const isClickable = fieldName && checkFieldHasRegulation(fieldName) && safeValue !== "-";
    const clickable = isClickable
      ? `<span class="cursor-pointer hover:underline hover:text-blue-600"
          data-field="${fieldName}"
          onclick="window.showStoredRegulationModalVerificator('${fieldName}', '${context}')">${safeValue}</span>`
      : safeValue;
    return `
      <div class="grid grid-cols-2 border-b border-gray-200 dark:border-gray-700">
        <div class="bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-3 py-2 font-medium">${label}</div>
        <div class="bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 border-l border-gray-100 dark:border-gray-600">${clickable}</div>
      </div>`;
  };

  const section = (title, rows, color = "blue") => `
    <section class="rounded-lg shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div class="px-4 py-2 font-bold text-white bg-gradient-to-r from-${color}-600 to-${color}-500">${title}</div>
      <div class="bg-white dark:bg-gray-800">${rows}</div>
    </section>`;

  const infoBox = (text, icon = "👁️") => `
    <div class="flex items-start gap-2 bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200 border-l-4 border-blue-400 p-3 rounded mb-3">
      <span class="text-lg">${icon}</span>
      <div class="text-sm leading-snug">${text}</div>
    </div>`;

  return `
    <div class="space-y-6 text-sm bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100">
        <div class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg border-l-4 border-blue-500">
          <div class="flex items-center gap-2">
            <span class="text-lg font-bold">📋 Detail Diagnosis</span>
            <span class="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">READ-ONLY</span>
          </div>
        </div>
      ${section("KLINIS", `
        ${infoBox("Justifikasi, bukti, dan syarat klinis yang disimpan dokter.")}
        ${fieldRow("Justifikasi", klinis.justifikasi)}
        ${fieldRow("Bukti Klinis", klinis.bukti_klinis)}
        ${fieldRow("Syarat Klinis", klinis.syarat_klinis)}
      `)}

      ${section("ICD-10", `
        ${fieldRow("Kode ICD-10", icd10.kode_icd)}
        ${fieldRow("Kode Ganda", icd10.kode_ganda)}
        ${fieldRow("Z-Code", icd10.z_code)}
        ${fieldRow("Kode Khusus BPJS", icd10.kode_bpjs_khusus)}
      `)}

      ${section("FAKTOR FASKES", `
        ${fieldRow("Tingkat Faskes", faskes.tingkat)}
        ${fieldRow("Justifikasi Faskes", faskes.justifikasi)}
        ${fieldRow("Kompetensi Faskes", faskes.kompetensi)}
      `)}

      ${section("RAWAT INAP", `
        ${fieldRow("Lama Rawat", rawat.lama_rawat)}
        ${fieldRow("Indikasi Rawat", rawat.indikasi)}
        ${fieldRow("Kriteria Rawat", rawat.kriteria)}
      `)}

      ${section("RUJUKAN", `
        ${fieldRow("Indikasi Rujukan", rujukan.indikasi)}
        ${fieldRow("Kriteria Rujukan", rujukan.kriteria)}
        ${fieldRow("Tujuan Rujukan", rujukan.tujuan)}
      `)}

      ${section("INA-CBG", `
        ${fieldRow("Kode INA-CBG", inacbg.kode)}
        ${fieldRow("Deskripsi", inacbg.deskripsi)}
        ${fieldRow("Tarif", inacbg.tarif)}
      `)}

      ${section("ASPEK LAINNYA", `
        ${fieldRow("Aspek Lainnya", detail.aspek_lainnya || "-")}
      `)}

      ${idrg && Object.keys(idrg).length ? section("i-DRG", `
        ${fieldRow("Group i-DRG", idrg.group_idrg)}
        ${fieldRow("Severity Index", idrg.severity_index)}
        ${fieldRow("Estimasi Tarif", idrg.estimasi_tarif)}
        ${fieldRow("Gap Analysis", idrg.gap_analysis)}
        ${fieldRow("Checklist", (idrg.checklist || []).join("<br>"))}
        ${fieldRow("Faktor Severity", (idrg.faktor_severity || []).join("<br>"))}
      `) : ""}

      ${regulasi && regulasi.length ? section("REGULASI TERKAIT", renderRegulationReadOnly(regulasi, "list"), "yellow") : ""}
    </div>`;
}

export function renderProcedureDetailReadOnly(data) {
  const procedureName = data.procedure_text || data.name || "";
  const detail = data.procedure_detail || {};
  const analysis = data.analysis || {};

  if (Object.keys(detail).length === 0 && (data.icd9_code || data.validitas)) Object.assign(detail, data);

  const renderProcBox = (label, value, fieldName = null) => {
    const safe = value || "-";
    let content = safe;
    if (fieldName && checkFieldHasRegulation(fieldName) && safe !== "-") {
      content = `<span class="cursor-pointer hover:underline hover:text-blue-600" 
        title="📋 Klik untuk melihat regulasi ${fieldName}" 
        onclick="window.showStoredRegulationModalVerificator('${fieldName}', 'procedure')">${safe}</span>`;
    }
    return `
      <div class="flex flex-col rounded-lg overflow-hidden shadow-sm bg-white dark:bg-slate-800 ring-1 ring-gray-100 dark:ring-slate-700">
        <div class="px-3 py-2 font-medium bg-gray-50 dark:bg-slate-700">${label}</div>
        <div class="px-3 py-2">${content}</div>
      </div>`;
  };

  return `
    <div class="space-y-6 text-sm">
      <div class="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg border-l-4 border-green-500">
        <div class="flex items-center">
          <span class="text-green-600 text-lg mr-2">👁️</span>
          <div>
            <h4 class="font-semibold text-green-900 dark:text-green-300">Mode Read-Only Verifikator</h4>
            <p class="text-green-800 dark:text-green-400 text-sm">Data ini hanya bisa dilihat oleh verifikator</p>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-3">
        ${renderProcBox("Kode ICD-9", analysis.icd9_code || detail.icd9_code, "icd9_code")}
        ${renderProcBox("Deskripsi", procedureName, "icd9_desc")}
        ${renderProcBox("Validitas", analysis.validitas || detail.validitas, "validitas")}
        ${renderProcBox("Status", analysis.status_tindakan || detail.status_tindakan, "status")}
        ${renderProcBox("Tarif INA-CBG", analysis.ina_cbg || detail.ina_cbg, "ina_cbg")}
        ${renderProcBox("Faskes", analysis.faskes_tindakan || detail.faskes_tindakan, "faskes")}
        ${renderProcBox("Rawat Inap", analysis.rawat_inap_tindakan || detail.rawat_inap_tindakan, "rawat_inap_tindakan")}
        ${renderProcBox("Syarat Klinis", analysis.syarat_klinis || detail.syarat_klinis, "syarat_klinis")}
        ${renderProcBox("Aspek Lainnya", analysis.aspek_lainnya || detail.aspek_lainnya, "aspek_lainnya")}
      </div>
    </div>`;
}

export function renderRegulationReadOnly(data, mode = "detail") {
  const regulations = data.regulations || data || [];
  const fieldName = data.field_name || "Regulasi";

  if (!Array.isArray(regulations) || regulations.length === 0) {
    return `<div class="text-center py-6 text-gray-500"><p>📋 Belum ada regulasi untuk field: ${fieldName}</p><p class="text-sm mt-1">Sistem menggunakan aturan nasional standar</p></div>`;
  }

  if (mode === "list") {
    return regulations.map(reg => `
      <div class="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded border-l-4 border-yellow-500 mb-2 cursor-pointer"
           title="Klik untuk detail regulasi"
           onclick="window.showStoredRegulationModalVerificator('${reg.field || fieldName}')">
        <div class="font-medium text-yellow-900 dark:text-yellow-300">${reg.field || fieldName}</div>
        <div class="text-sm text-yellow-700 dark:text-yellow-400 mt-1">${truncateText(reg.isi || "Tidak ada detail", 100)}</div>
      </div>`).join("");
  }

  const rulesByLayer = {};
  regulations.forEach(rule => {
    const layer = rule.layer || "lainnya";
    if (!rulesByLayer[layer]) rulesByLayer[layer] = [];
    rulesByLayer[layer].push(rule);
  });

  const sorted = Object.keys(rulesByLayer).sort((a, b) => {
    const order = { permenkes: 1, nasional: 2, ppk: 3, regional: 4, rs: 5 };
    return (order[a] || 99) - (order[b] || 99);
  });

  return `
    <div class="space-y-4">
      <div class="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg border-l-4 border-yellow-500">
        <div class="flex items-center">
          <span class="text-yellow-600 text-lg mr-2">👁️</span>
          <div>
            <h4 class="font-semibold text-yellow-900 dark:text-yellow-300">Mode Read-Only Verifikator</h4>
            <p class="text-yellow-800 dark:text-yellow-400 text-sm">Regulasi untuk field: <strong>${fieldName}</strong></p>
          </div>
        </div>
      </div>
      ${sorted.map(layer => {
        const label = getLayerLabel(layer);
        const color = getLayerColorClass(layer);
        const rules = rulesByLayer[layer];
        return `
          <div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <div class="bg-gray-100 dark:bg-slate-800 text-gray-900 dark:text-white px-4 py-2 font-semibold">${label} (${rules.length} aturan)</div>
            <div class="p-4 space-y-3">
              ${rules.map(r => `
                <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
                  <div class="flex items-center gap-2 mb-2">
                    <span class="px-2 py-1 text-xs font-semibold rounded-full ${color}">${layer.toUpperCase()}</span>
                    <span class="text-sm font-medium">${r.field || fieldName}</span>
                  </div>
                  <div class="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">${r.isi || "-"}</div>
                  <div class="text-xs text-gray-500 dark:text-gray-400"><strong>Sumber:</strong> ${r.sumber || "-"}</div>
                </div>`).join("")}
            </div>
          </div>`; }).join("")}
    </div>`;
}

export function renderIdrgSectionReadOnly(idrg_data) {
  if (!idrg_data) {
    return `
      <section class="rounded shadow overflow-hidden">
        <div class="bg-gradient-to-r from-blue-500 to-blue-600 text-white px-3 py-2 font-bold">i-DRG</div>
        <div class="p-4 text-center text-gray-500">
          <p>📊 Tidak ada data i-DRG tersimpan</p>
        </div>
      </section>
    `;
  }

  const renderIdrgRow = (label, value) => {
    return `
      <div class="grid grid-cols-2">
        <div class="bg-slate-100 text-gray-900 dark:bg-slate-700 dark:text-white px-3 py-2 font-medium">${label}</div>
        <div class="bg-blue-50 text-blue-800 dark:bg-blue-900 dark:text-blue-100 px-3 py-2">${value || '-'}</div>
      </div>
    `;
  };

  return `
    <section class="rounded shadow overflow-hidden">
      <div class="bg-gradient-to-r from-blue-500 to-blue-600 text-white px-3 py-2 font-bold">i-DRG</div>
      <div class="p-3 bg-gray-100 dark:bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-white">
        <div class="bg-blue-50 dark:bg-blue-900/20 p-3 rounded mb-3 border-l-4 border-blue-500">
          <div class="flex items-center">
            <span class="text-blue-600 text-lg mr-2">👁️</span>
            <div>
              <h4 class="font-semibold text-blue-900 dark:text-blue-300">Data i-DRG Tersimpan</h4>
              <p class="text-blue-800 dark:text-blue-400 text-sm">Data hasil analisis AI yang telah disimpan doctor</p>
            </div>
          </div>
        </div>
        <div class="space-y-1">
          ${renderIdrgRow("Group i-DRG", idrg_data.group_idrg)}
          ${renderIdrgRow("Cost Weight", idrg_data.cost_weight)}
          ${renderIdrgRow("Tarif", idrg_data.tarif ? `Rp ${Number(idrg_data.tarif).toLocaleString('id-ID')}` : '')}
          ${renderIdrgRow("Severity Index", idrg_data.severity_index)}
          ${renderIdrgRow("Checklist", idrg_data.checklist_dokumentasi)}
        </div>
      </div>
    </section>
  `;
}


// ==================================================
// 3️⃣ WINDOW GUARD (GLOBAL)
// ==================================================

if (typeof window !== "undefined") {
  window.showStoredDiagnosisModalVerificator = showStoredDiagnosisModalVerificator;
  window.showStoredProcedureModalVerificator = showStoredProcedureModalVerificator;
  window.showStoredRegulationModalVerificator = showStoredRegulationModalVerificator;
  window.renderDiagnosisDetailReadOnly = renderDiagnosisDetailReadOnly;
  window.renderProcedureDetailReadOnly = renderProcedureDetailReadOnly;
  window.renderRegulationReadOnly = renderRegulationReadOnly;
  window.renderIdrgSectionReadOnly = renderIdrgSectionReadOnly;
}
