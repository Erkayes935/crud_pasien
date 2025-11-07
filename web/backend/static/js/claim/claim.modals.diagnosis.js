// ============================================================
// claim.modals.diagnosis.js (Lossless Refactor – Part 1/2)
// ============================================================
// Semua logika diagnosis dipertahankan 100% dari file lama
// ============================================================

import { openModal, showAiLoadingModal, hideAiLoadingModal } from "./claim.modals.core.js";
import { checkFieldHasRegulation } from "./claim.modals.regulation.js";

// =====================================================
// UPDATE RINGKASAN FROM ROW (lossless, dari file lama)
// =====================================================
export function updateRingkasanFromRow(itemId, dx) {
  if (!dx || !itemId) return;
  if (dx.isManual) {
    const stage = dx.stage || window.claimState?.tab || "admission";
    window.renderManualTindakanList && window.renderManualTindakanList(stage);
    return;
  }

  console.log("📋 updateRingkasanFromRow called with:", { itemId, dx });

  const row = document.querySelector(`[data-id="${itemId}"]`);
  if (!row) return;
  if (row.closest(".tindakan-list")) {
    const descEl = row.querySelector("span[title], span.block");
    if (descEl) {
      const newText = dx.deskripsi || "&nbsp;";
      descEl.textContent = newText;
      descEl.setAttribute("title", newText);
    }
    return;
  }

  // kolom Klinis
  const klinisCell = row.querySelector(".col-klinis");
  if (klinisCell) {
    let text = "";
    if (dx.klinis) {
      if (Array.isArray(dx.klinis)) {
        text = dx.klinis.filter(Boolean).join(", ");
      } else if (typeof dx.klinis === "string") {
        text = dx.klinis;
      } else if (typeof dx.klinis === "object") {
        text = [dx.klinis.justifikasi, dx.klinis.bukti_klinis, dx.klinis.syarat_klinis]
          .filter(Boolean)
          .join(", ");
      }
    } else {
      text = [dx.justifikasi, dx.bukti_klinis, dx.syarat_klinis].filter(Boolean).join(", ");
    }
    console.log("📋 Setting klinis text:", text);
    klinisCell.innerHTML = text ? `<span title="${text}">${truncateText(text, 44)}</span>` : "&nbsp;";
  }

  // kolom ICD
  const icdCell = row.querySelector(".col-icd");
  if (icdCell) {
    let icdCode = "";
    if (dx.icd10_code) {
      icdCode = dx.icd10_code;
    } else if (dx.icd10 && dx.icd10.kode_icd) {
      icdCode = dx.icd10.kode_icd;
    } else if (dx.icd9_code) {
      icdCode = dx.icd9_code;
    }
    console.log("📋 Setting ICD code:", icdCode);
    icdCell.innerText = icdCode;
    
    // 🩹 PATCH: Update juga di dataset row agar persist
    if (icdCode && row.dataset.row) {
      try {
        const rowData = JSON.parse(row.dataset.row);
        rowData.icd10_code = icdCode;
        if (rowData.icd10) rowData.icd10.kode_icd = icdCode;
        row.dataset.row = JSON.stringify(rowData);
        console.log("🩹 [PATCH] ICD-10 persisted to row dataset:", icdCode);
      } catch (e) {
        console.warn("⚠️ Failed to update row dataset:", e);
      }
    }
  }

  // kolom Tindakan
  const tindakanCell = row.querySelector(".col-tindakan");
  if (tindakanCell) {
    let text = "";
    if (dx.tindakan && Array.isArray(dx.tindakan) && dx.tindakan.length > 0) {
      text = dx.tindakan
        .map(t => t.procedure_text || t.tindakan || t.nama || t.name || t.description || t)
        .join(", ");
    }
    console.log("📋 Setting tindakan text:", text);
    tindakanCell.innerHTML = text !== "" ? `<span title="${text}">${truncateText(text, 44)}</span>` : "&nbsp;";
  }

  // Persist hasil ke state simulasi
  try {
    const stage = dx.stage || window.claimState?.tab || "admission";
    const sim = window.claimState?.simulasi?.[stage];
    if (sim && Array.isArray(sim.diagnosis)) {
      const item = sim.diagnosis.find(d =>
        d.id === dx.id || d.kategori === dx.kategori || d.icd10_code === dx.icd10_code
      );
      if (item) {
        if (dx.klinis) {
          let klinisText = "";
          if (typeof dx.klinis === "object" && dx.klinis !== null) {
            const k = dx.klinis;
            klinisText = [k.justifikasi, k.bukti_klinis, k.syarat_klinis]
              .filter(Boolean)
              .join(", ");
          } else if (Array.isArray(dx.klinis)) {
            klinisText = dx.klinis.filter(Boolean).join(", ");
          } else {
            klinisText = dx.klinis;
          }
          item.klinis = `<span title="${klinisText}">${truncateText(klinisText, 44)}</span>`;
        }

        if (dx.icd10_code || dx.icd10) {
          item.icd10_code = dx.icd10_code || dx.icd10?.kode_icd || "";
          item.icd10 = dx.icd10 || { kode_icd: item.icd10_code };
        }

        if (Array.isArray(dx.tindakan)) {
          const texts = dx.tindakan.map(t => t.procedure_text || t.tindakan).filter(Boolean);
          const tindakanText = texts.join(", ");
          item.tindakan = `<span title="${tindakanText}">${truncateText(tindakanText, 44)}</span>`;
        }
      }
    }
  } catch (err) {
    console.warn("⚠️ gagal persist ringkasan ke state:", err);
  }
}

// =====================================================
// BUKA MODAL DARI KLIK KATEGORI (Lossless)
// =====================================================
export async function openModalFromAttr(el, type) {
  window.claimState.fromProcedure = false;
  window.claimState.fromRegulation = false;
  console.log("🧭 [STATE] Buka modal diagnosis langsung, bukan dari tindakan/regulasi.");
  const tr = el.closest("tr");
  const dbId = tr?.dataset.dbId;
  const uiId = tr?.dataset.id;
  const claimId = document.getElementById("claimRoot")?.dataset.claimId;

  let diseaseName = "";
  if (el.textContent) {
    diseaseName = el.textContent.replace(/^â†'+\s*/, "").trim();
  } else {
    diseaseName = tr?.querySelector(".kategori-cell")?.textContent?.trim() || tr?.dataset.nama || "";
  }

  async function fetchDiagnosisDetail() {
    const res = await fetch(`/claims/${claimId}/analyze_diagnosis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        claim_id: parseInt(claimId),
        disease_name: diseaseName,
        rekam_medis: [],
        scope: "diagnosis"
      })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return await res.json();
  }

  try {
    let dx = {};

    if (["diagnosis", "komorbid", "komplikasi"].includes(type) && claimId && diseaseName) {
      showAiLoadingModal([
        "Mengambil data detail diagnosis...",
        "Memuat regulasi multilayer terkait...",
        "Menyiapkan tampilan modal..."
      ]);

      console.log("[REQ] POST /analyze_diagnosis", { claim_id: claimId, disease_name: diseaseName });

      let result;
      try {
        result = await fetchDiagnosisDetail();
        // 🔧 Normalisasi hasil backend yang punya wrapper {status, data:{...}}
        while (result && typeof result === "object" && result.data) {
          result = result.data;
        }
        console.log("✅ Final flattened result:", result);
      } catch (err) {
        console.warn("⚠️ Gagal fetch pertama, mencoba ulang...", err);
        showAiLoadingModal([
          "Mengakuratkan jawaban AI...",
          "Mengambil ulang data dari core engine...",
          "Mohon tunggu sebentar..."
        ]);

        try {
          result = await fetchDiagnosisDetail();
          // 🔧 Normalisasi hasil backend yang punya wrapper {status, data:{...}}
          while (result && typeof result === "object" && result.data) {
            result = result.data;
          }
          console.log("✅ Final flattened result:", result);
        } catch (err2) {
          console.error("❌ Gagal load modal detail (retry gagal):", err2);
          hideAiLoadingModal();
          openModal(
            `<div class="flex flex-col items-center text-center p-6">
              <span class="text-lg font-bold text-red-500 mb-2">Gagal Memuat Detail Diagnosis</span>
              <p class="text-gray-600 dark:text-gray-300 mb-4">
                Terjadi gangguan saat mengambil data dari core engine.<br>
                Silakan coba lagi beberapa saat.
              </p>
              <button class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                onclick="openModalFromAttr(document.querySelector('[data-id=\'${uiId}\']'), '${type}')">
                🔄 Coba Lagi
              </button>
            </div>`
          );
          return;
        }
      }

      console.log("[RESP] /analyze_diagnosis", result);

      // 🔧 Flatten jika hasil masih mengandung "data"
      const core = result.data ? result.data : result;

      // Pastikan semua data diambil dari level yang benar
      const icd10Code = core.icd10?.kode_icd || core.icd10_code || "";
      const justifikasi = core.klinis?.justifikasi || core.justifikasi || "";
      const buktiKlinis = core.klinis?.bukti_klinis || core.bukti_klinis || "";

      dx = { ...core, icd10_code: icd10Code, justifikasi, bukti_klinis: buktiKlinis, kategori: diseaseName };


      window.claimState.currentDiagnosis = result;
      window.claimState.currentDiagnosisTitle = diseaseName;
      console.log("🧩 renderDiagnosisDetail input:", JSON.stringify(dx, null, 2));

      const modalContent = renderDiagnosisDetail(dx);
      openModal(
        `<div class="flex flex-col items-start items-center animate-fade-in">
          <span class="text-lg font-bold">Detail Diagnosis</span>
          <span class="font-bold text-2xl mb-2 text-yellow-500">${diseaseName}</span>
        </div>`,
        modalContent,
        { hideDefaultClose: false }
      );

      hideAiLoadingModal();
      updateRingkasanFromRow(uiId, dx);
      return;
    }

    // fallback legacy
    if (dbId && !isNaN(Number(dbId))) {
      const url = `/claims/ai/recommendation/detail?claim_id=${claimId}&rec_type=${type}&item_id=${dbId}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const result = await res.json();
      dx = result.data;
    } else {
      dx = tr?.dataset.row ? JSON.parse(tr.dataset.row) : {};
    }

    hideAiLoadingModal();
    const namaPenyakit =
      dx?.kategori || dx?.nama_kategori || dx?.diagnosis || dx?.komorbid || dx?.komplikasi || "-";
    console.log("🧩 renderDiagnosisDetail input:", JSON.stringify(dx, null, 2));
    const modalContent = renderDiagnosisDetail(dx);
    openModal(
      `<div class="flex flex-col items-start items-center animate-fade-in">
        <span class="text-lg font-bold">Detail Diagnosis</span>
        <span class="font-bold text-2xl mb-2 text-yellow-500">${namaPenyakit}</span>
      </div>`,
      modalContent,
      { hideDefaultClose: false }
    );

    window.claimState.currentDiagnosis = dx;
    window.claimState.currentDiagnosisTitle = namaPenyakit;
    updateRingkasanFromRow(uiId, dx);
  } catch (err) {
    console.error("❌ Gagal load modal detail:", err);
    hideAiLoadingModal();
    openModal(
      `<div class="flex flex-col items-center text-center p-6">
        <span class="text-lg font-bold text-red-500 mb-2">Gagal Memuat Data</span>
        <p class="text-gray-600 dark:text-gray-300 mb-4">
          Terjadi kesalahan tak terduga saat memproses permintaan Anda.
        </p>
        <button class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          onclick="openModalFromAttr(document.querySelector('[data-id=\'${uiId}\']'), '${type}')">
          🔄 Coba Lagi
        </button>
      </div>`
    );
  }
}

// ============================================================
// RENDER NOTIFICATION BOX
// ============================================================
export function renderNotificationBox(section, notifications = {}) {
  const colorMap = {
    success:
      "bg-emerald-50/70 border-emerald-400 text-emerald-800 dark:bg-emerald-900/40 dark:border-emerald-500/70 dark:text-emerald-100",
    warning:
      "bg-amber-50/70 border-amber-400 text-amber-800 dark:bg-amber-900/40 dark:border-amber-500/70 dark:text-amber-100",
    error:
      "bg-rose-50/70 border-rose-400 text-rose-800 dark:bg-rose-900/40 dark:border-rose-500/70 dark:text-rose-100",
    info:
      "bg-blue-50/70 border-blue-400 text-blue-800 dark:bg-blue-900/40 dark:border-blue-500/70 dark:text-blue-100",
    default:
      "bg-slate-100/60 border-slate-300 text-slate-700 dark:bg-slate-800/50 dark:border-slate-600 dark:text-slate-200"
  };

  const note = notifications?.[section] || {};
  const status = note.status || "default";
  const msg =
    note.message ||
    `Belum ada notifikasi untuk bagian ${section.toUpperCase()}.`;
  const cls = colorMap[status] || colorMap.default;

  return `
    <div class="notification-box ${cls} border-l-4 p-3 rounded-lg mb-3 text-sm shadow-sm backdrop-blur-sm transition-colors duration-200">
      <div>
        <strong class="font-semibold">Notifikasi AI (${section.toUpperCase()})</strong>
        <div class="text-xs leading-snug mt-1">${msg}</div>
      </div>
    </div>
  `;
}

// ============================================================
// Fungsi utility tambahan
// ============================================================
export function buildModalContent(it) {
  let content = renderDiagnosisDetail(it);
  content += `<div class="tindakan-list mt-4"></div>`;
  setTimeout(() => window.renderManualTindakanList && window.renderManualTindakanList(), 0);
  return content;
}

// ======================================================
// 🔹 Fungsi render utama modal detail diagnosis (Lossless)
// ======================================================
export function renderDiagnosisDetail(it) {
  console.log("📋 renderDiagnosisDetail data:", it);

  // 🧠 Tambahkan deteksi bila hasil punya nested key "data"
  const src = it.data ? it.data : it;

  const diagnosisId = src.diagnosis_id || src.id;

  const klinis = src.klinis || {};
  const icd10 = src.icd10 || {};
  const tindakan = Array.isArray(src.tindakan) ? src.tindakan : [];
  const rawat = src.rawat_inap || src.rawat || {};
  const faskes = src.faskes || {};
  const rujukan = src.rujukan || {};
  const inaCbg = src.inaCbg || src.ina_cbg || {};
  const notifications = src.notifications || {}; // 🔔 notifikasi per section dari core_engine

  const safeRender = (cb) => {
    try {
      return cb();
    } catch (e) {
      console.warn("render skip:", e);
      return "";
    }
  };

  console.log("🧩 [DEBUG] Simulasi tindakan saat render ulang:",
    window.claimState?.simulasi?.[window.claimState?.tab || "admission"]?.tindakan
  );

  const renderBox = (label, value, status = "default", diagnosisId = null, fieldName = null) => {
    let colorClass = "bg-white dark:bg-slate-700 text-gray-800 dark:text-gray-100";
    if (status === "valid") colorClass = "bg-green-50 text-green-800 dark:bg-green-600 dark:text-white";
    if (status === "invalid") colorClass = "bg-red-600 text-white";

    const safeValue = value || "-";
    console.log(`📋 renderBox(${label}): value="${value}", safeValue="${safeValue}"`);

    const hasRegulation = checkFieldHasRegulation(fieldName);

    let content = safeValue;
    if (hasRegulation && diagnosisId && safeValue !== "") {
      // Changed @click Alpine directive to onclick standard DOM event
      content = `<span class="cursor-pointer hover:underline hover:text-blue-600 regulation-field border-b border-dashed border-gray-400 hover:border-blue-600 transition-all duration-200"
                  title="📋 Klik untuk melihat regulasi ${fieldName}"
                  data-field="${fieldName}"
                  data-diagnosis-id="${diagnosisId}"
                  onclick="window.openRegulationDetailModal('${fieldName}', ${diagnosisId})">${safeValue}</span>`;
    }

    const boxHtml = `
      <div class="grid grid-cols-2">
        <div class="bg-gray-100 text-gray-900 dark:bg-slate-700 dark:text-white px-3 py-2 font-medium">${label}</div>
        <div class="${colorClass} px-3 py-2">${content}</div>
      </div>
    `;
    return boxHtml;
  };

  // === Render keseluruhan modal ===
  return `
    <div class="space-y-6 text-sm">

      <!-- 🩺 KLINIS -->
      <section class="rounded-xl shadow-md overflow-hidden border border-slate-200 dark:border-slate-700">
        <div class="bg-gradient-to-r from-blue-500 to-blue-600 text-white px-4 py-3 font-bold rounded-t-xl shadow-sm">KLINIS</div>
        <div class="space-y-2 p-3 bg-gray-50 dark:bg-slate-700">
          ${renderNotificationBox("klinis", notifications)}
          ${safeRender(() => renderBox("Justifikasi", klinis.justifikasi, klinis.status, diagnosisId, "justifikasi"))}
          ${safeRender(() => renderBox("Bukti Klinis", klinis.bukti_klinis, null, diagnosisId, "bukti_klinis"))}
          ${safeRender(() => renderBox("Syarat Klinis", klinis.syarat_klinis, klinis.status, diagnosisId, "syarat_klinis"))}
        </div>
      </section>

      <!-- 🧾 ICD-10 -->
      <section class="rounded-xl shadow-md overflow-hidden border border-slate-200 dark:border-slate-700">
        <div class="bg-gradient-to-r from-blue-500 to-blue-600 text-white px-4 py-3 font-bold rounded-t-xl shadow-sm">ICD-10</div>
        <div class="space-y-2 p-3 bg-gray-50 dark:bg-slate-700">
          ${renderNotificationBox("icd", notifications)}
          ${safeRender(() => renderBox("Kode ICD", icd10.kode_icd, icd10.status_icd, diagnosisId, "kode_icd"))}
          ${safeRender(() => renderBox("Kode Ganda", icd10.kode_ganda, icd10.status_icd, diagnosisId, "kode_ganda"))}
          ${safeRender(() => renderBox("Z-Code", icd10.z_code, icd10.status_icd, diagnosisId, "z_code"))}
          ${safeRender(() => renderBox("Kode BPJS Khusus", icd10.kode_bpjs_khusus, icd10.status_icd, diagnosisId, "kode_bpjs_khusus"))}
        </div>
      </section>

      <!-- 📊 i-DRG -->
      ${safeRender(() => renderIdrgSection(it.idrg_diagnosis))}

      <!-- ⚙️ TINDAKAN -->
      <section class="rounded-xl shadow-md overflow-hidden border border-slate-200 dark:border-slate-700">
        <div class="bg-gradient-to-r from-emerald-500 to-emerald-600 text-white px-4 py-3 font-bold rounded-t-xl shadow-sm">TINDAKAN</div>
        <div class="p-3 bg-gray-50 dark:bg-slate-700">
          ${renderNotificationBox("tindakan", notifications)}
          ${safeRender(() => renderTindakan(tindakan))}
        </div>
      </section>

      <!-- 🏥 RAWAT INAP -->
      <section class="rounded-xl shadow-md overflow-hidden border border-slate-200 dark:border-slate-700">
        <div class="bg-gradient-to-r from-teal-500 to-teal-600 text-white px-4 py-3 font-bold rounded-t-xl shadow-sm">RAWAT INAP</div>
        <div class="space-y-3 p-3 bg-gray-50 dark:bg-slate-700">
          ${renderNotificationBox("rawat", notifications)}
          ${safeRender(() => renderBox("Indikasi", rawat.indikasi, rawat.status_indikasi, diagnosisId, "indikasi"))}
          ${safeRender(() => renderBox("Kriteria", rawat.kriteria, rawat.status_kriteria, diagnosisId, "kriteria"))}
          ${safeRender(() => renderBox("Lama Rawat", rawat.lama_rawat, rawat.status_lama, diagnosisId, "lama_rawat"))}
        </div>
      </section>

      <!-- 🏢 FASKES -->
      <section class="rounded-xl shadow-md overflow-hidden border border-slate-200 dark:border-slate-700">
        <div class="bg-gradient-to-r from-amber-500 to-amber-600 text-white px-4 py-3 font-bold rounded-t-xl shadow-sm">FASKES</div>
        <div class="space-y-2 p-3 bg-gray-50 dark:bg-slate-700">
          ${renderNotificationBox("faskes", notifications)}
          ${safeRender(() => renderBox("Tingkat", faskes.tingkat, faskes.status_tingkat, diagnosisId, "tingkat"))}
          ${safeRender(() => renderBox("Justifikasi", faskes.justifikasi, faskes.status_justifikasi, diagnosisId, "justifikasi_faskes"))}
          ${safeRender(() => renderBox("Kompetensi", faskes.kompetensi, faskes.status_kompetensi, diagnosisId, "kompetensi"))}
        </div>
      </section>

      <!-- 🔁 RUJUKAN -->
      <section class="rounded-xl shadow-md overflow-hidden border border-slate-200 dark:border-slate-700">
        <div class="bg-gradient-to-r from-orange-500 to-orange-600 text-white px-4 py-3 font-bold rounded-t-xl shadow-sm">RUJUKAN</div>
        <div class="space-y-2 p-3 bg-gray-50 dark:bg-slate-700">
          ${renderNotificationBox("rujukan", notifications)}
          ${safeRender(() => renderBox("Indikasi", rujukan.indikasi, rujukan.status_indikasi, diagnosisId, "indikasi_rujukan"))}
          ${safeRender(() => renderBox("Tujuan", rujukan.tujuan, rujukan.status_tujuan, diagnosisId, "tujuan"))}
          ${safeRender(() => renderBox("Kriteria", rujukan.kriteria, rujukan.status_kriteria, diagnosisId, "kriteria_rujukan"))}
        </div>
      </section>

      <!-- 💰 INA-CBG -->
      <section class="rounded-xl shadow-md overflow-hidden border border-slate-200 dark:border-slate-700">
        <div class="bg-gradient-to-r from-rose-500 to-rose-600 text-white px-4 py-3 font-bold rounded-t-xl shadow-sm">INA-CBG</div>
        <div class="space-y-2 p-3 bg-gray-50 dark:bg-slate-700">
          ${renderNotificationBox("inacbg", notifications)}
          ${renderBox("Kode INA-CBG", inaCbg.kode, inaCbg.status_kode, diagnosisId, "kode")}
          ${renderBox("Deskripsi", inaCbg.deskripsi, inaCbg.status_deskripsi, diagnosisId, "deskripsi")}
          ${safeRender(() => renderBox("Tarif", inaCbg.tarif ? `Rp ${Number(String(inaCbg.tarif).replace(/[^\d]/g, '')).toLocaleString('id-ID')}` : "-", inaCbg.status_tarif, diagnosisId, "tarif"))}
        </div>
      </section>

    </div>
  `;
}

// ============================================================
// 🧩 BACKWARD COMPATIBILITY SHIM
// ============================================================
if (typeof window !== "undefined") {
  window.updateRingkasanFromRow = updateRingkasanFromRow;
  window.openModalFromAttr = openModalFromAttr;
  window.renderNotificationBox = renderNotificationBox;
  window.renderDiagnosisDetail = renderDiagnosisDetail;
  window.buildModalContent = buildModalContent;
}