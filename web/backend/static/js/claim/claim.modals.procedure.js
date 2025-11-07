// ============================================================
// claim.modals.procedure.js (Lossless Refactor – Part 1/2)
// ============================================================
// ✅ Semua logika diambil 1:1 dari file kamu (tidak ada baris diubah)
// ✅ Hanya ditambah modular import/export & kompatibilitas window
// ============================================================

import { openModal, showAiLoadingModal, hideAiLoadingModal } from "./claim.modals.core.js";
import { renderNotificationBox } from "./claim.modals.diagnosis.js";
import { checkFieldHasRegulation } from "./claim.modals.regulation.js";

// ============================================================
// 🔹 OPEN PROCEDURE MODAL (versi kamu, lossless)
// ============================================================
export async function openProcedureModal(procId, procedureName) {
  window.claimState.fromProcedure = true;
  window.claimState.fromRegulation = false;
  console.log("🧭 [STATE] Buka modal tindakan dari diagnosis.");

  const isDark = document.documentElement.classList.contains("dark");
    const modalBg = isDark ? "bg-slate-800 text-white" : "bg-gray-50 text-gray-900";
    const titleColor = isDark ? "text-yellow-400" : "text-amber-600";

    const claimId = document.getElementById("claimRoot")?.dataset.claimId;

    // Ambil nama tindakan dari DOM jika belum dikirim
    if (!procedureName) {
      const procElement = document.querySelector(`[data-procid="${procId}"] .cursor-pointer`);
      procedureName = procElement?.textContent?.trim() || "Unknown Procedure";
    }

    console.log("🔥 openProcedureModal called", { procId, procedureName, claimId });

    // Check if this is a manual procedure - if so, use openManualDetailModal instead
    const state = Alpine.$data(document.getElementById('claimRoot'));
    const allTindakan = Object.values(state.simulasi || {}).flatMap(stage => stage.tindakan || []);
    const manualTindakan = allTindakan.find(t =>
      t.isManual && (t.nama === procedureName || t.procedure_text === procedureName)
    );

    if (manualTindakan) {
      console.log("🔧 Detected manual procedure, using openManualDetailModal");
      openManualDetailModal(manualTindakan);
      return;
    }

    try {
      // Request ke core_engine /analyze_procedure
      showAiLoadingModal([
        "Mengambil data detail tindakan...",
        "Memuat regulasi multilayer terkait...",
        "Menyiapkan tampilan modal..."
      ]);
      console.log("[REQ] POST /analyze_procedure", { claim_id: claimId, procedure_text: procedureName });
      const res = await fetch(`/claims/${claimId}/analyze_procedure`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_id: parseInt(claimId),
          procedure_text: procedureName,
          rekam_medis: [],
          scope: "tindakan"
        })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      showAiLoadingModal([
        "Mengambil data detail tindakan...",
        "Memuat regulasi multilayer terkait...",
        "Menyiapkan tampilan modal..."
      ]);
      const result = await res.json();

      // 🧩 Simpan ID DB hasil analyze_procedure
      if (result && result.procedure_id) {
        window.claimState.currentProcedure = window.claimState.currentProcedure || {};
        window.claimState.currentProcedure.id = result.procedure_id;
      }
      if (result && result.procedure_text) {
        const actions = window.claimState?.simulasi?.[window.currentStage]?.tindakan || [];
        const idx = actions.findIndex(a => a.procedure_text === result.procedure_text);
        if (idx !== -1) {
          actions[idx].analyzed = true;
          window.claimState.simulasi[window.currentStage].tindakan = [...actions];
        }
      }

      console.log("[RESP] /analyze_procedure", result);
      const d = result.data || result;
      console.log("INA-CBG tarif raw:", d.ina_cbg_tarif, "| ina_cbg:", d.ina_cbg);

      const renderProcBox = (label, value, fieldName = null) => {
        const multilayer = d.multilayer_rules?.[fieldName] || null;
        const hasRules = multilayer && multilayer.items && multilayer.items.length > 0;
        let safeValue = value || "";

        // 💰 Format tarif INA-CBG
        if (fieldName === "ina_cbg" && value && value !== "") {
          const numericValue = parseInt(value);
          if (!isNaN(numericValue)) {
            safeValue = `Rp ${Number(numericValue).toLocaleString('id-ID')}`;
          } else {
            safeValue = value;
          }
        }

        const hasRegulation = checkFieldHasRegulation(fieldName);
        let content = `<span class="text-gray-900 dark:text-white">${safeValue}</span>`;

        if (hasRules) {
          const listItems = multilayer.items
            .map((r) => `
              <li class="ml-5 list-disc marker:text-blue-400 dark:marker:text-blue-300 text-sm leading-snug">
                ${r.isi} <span class="text-gray-400 dark:text-gray-500">(${r.sumber})</span>
              </li>`
            )
            .join("");
          const combinedLabel = multilayer.combined_label
            ? `<div class="text-xs italic text-blue-400 mt-1">Gabungan aturan: ${multilayer.combined_label}</div>`
            : "";
          content = `<ul class="space-y-1 list-outside">${listItems}</ul>${combinedLabel}`;
        } else {
          content = `<div class="whitespace-pre-line leading-relaxed">${safeValue}</div>`;
        }

        if (hasRegulation && fieldName && safeValue !== "") {
          content = `<span class="cursor-pointer hover:underline hover:text-blue-600 regulation-field border-b border-dashed border-gray-400 hover:border-blue-600 transition-all duration-200"
                      title="📋 Klik untuk melihat regulasi ${fieldName}"
                      data-field="${fieldName}"
                      data-procedure-id="${procId}"
                      onclick="window.openRegulationDetailModal('${fieldName}', null, '${procId}')">${safeValue}</span>`;
        }

        return `
          <div class="bg-gray-100 text-gray-900 dark:bg-slate-700 dark:text-white px-3 py-2 rounded-lg font-semibold">
            <b>${label}:</b>
          </div>
          <div class="bg-white text-gray-800 dark:bg-gray-800 dark:text-white px-3 py-2 rounded">${content}</div>
        `;
      };

      // 🔔 Ambil notifikasi dari core_engine (atau fallback dummy)
      const notifications = d.notifications || {
        tindakan: { status: "info", message: "Analisis AI: tindakan ini memerlukan verifikasi tambahan." }
      };
      console.log("📋 Notifications (procedure):", notifications);

      // hanya simpan 1 kode ICD-9 utama
      if (Array.isArray(d.icd9_code)) {
        d.icd9_code = d.icd9_code[0];
      } else if (typeof d.icd9_code === "string" && d.icd9_code.includes(",")) {
        d.icd9_code = d.icd9_code.split(",")[0].trim();
      }

      // 🔹 Konten modal utama
      const content = `
        <div class="${modalBg} flex flex-col items-center animate-fade-in">
          <h2 class="text-center text-xl font-bold ${titleColor} mb-4">Detail Tindakan</h2>
          <h3 class="text-center text-2xl font-extrabold text-${isDark ? "yellow-300" : "amber-500"} mb-6">
            ${procedureName}
          </h3>
          <button type="button"
                  onclick="closeNestedModal()"
                  class="absolute top-0 right-0 text-white bg-red-500 hover:bg-red-600 px-3 py-1 rounded">✕</button>
        </div>

        ${renderNotificationBox("tindakan", notifications)}

        <div class="grid grid-cols-2 gap-2 mt-3">
          ${renderProcBox("Kode ICD-9", d.icd9_code || d.icd9 || "-", "icd9_code")}
          ${renderProcBox("Deskripsi", `ICD-9: ${d.icd9_code || d.icd9 || "-"}, Status: ${d.status_tindakan || d.status || "-"}, INA-CBG: ${d.ina_cbg_tarif || d.ina_cbg || "-"}`, "deskripsi")}
          ${renderProcBox("Validitas", d.validitas, "validitas")}
          ${renderProcBox("Status", d.status_tindakan || d.status, "status")}
          ${renderProcBox("Tarif INA-CBG", d.ina_cbg_tarif || d.ina_cbg, "ina_cbg")}
          ${renderProcBox("Faskes", d.faskes, "faskes")}
          ${renderProcBox("Rawat Inap", d.rawat_inap, "rawat_inap")}
          ${renderProcBox(
            "Syarat Klinis",
            d.multilayer_rules?.syarat_klinis
              ? mergeTextAndRules(d.syarat_klinis, d.multilayer_rules?.syarat_klinis)
              : d.syarat_klinis,
            "syarat_klinis"
          )}
        </div>
      `;

      let newDesc = "";
      const procRow = document.querySelector(`[data-procid="${procId}"]`);
      if (procRow) {
        const descCell = procRow.querySelector("span[title], span.block");
        if (descCell) {
          newDesc = `ICD-9: ${d.icd9_code || d.icd9 || "-"}, Status: ${d.status_tindakan || d.status || "-"}, INA-CBG: ${d.ina_cbg_tarif || d.ina_cbg || "-"}`;
          descCell.textContent = newDesc;
          descCell.setAttribute("title", newDesc);
        }
      }
      d.deskripsi = newDesc;

      // 🩹 Simpan juga ke objek tindakan agar renderTindakan() bisa baca
      try {
        const stage = window.claimState.tab || "admission";
        const tindakanList = window.claimState.simulasi?.[stage]?.tindakan || [];
        tindakanList.forEach(t => {
          if (t.procedure_text === procedureName || t.nama === procedureName) {
            t.deskripsi = newDesc;
            t.analyzed = true;
          }
        });
        // update diagnosis kalau sudah ada
        if (window.claimState.currentDiagnosis?.tindakan?.length) {
          window.claimState.currentDiagnosis.tindakan.forEach(td => {
            if (td.procedure_text === procedureName || td.nama === procedureName) {
              td.deskripsi = newDesc;
              td.analyzed = true;
            }
          });
        }
        console.log("🩵 [SYNC] Deskripsi tindakan disimpan ke data & diagnosis.");
      } catch (err) {
        console.warn("⚠️ [SYNC] gagal simpan deskripsi tindakan ke objek:", err);
      }


      openModal(`Detail Tindakan: ${procedureName}`, content, { hideDefaultClose: true, disableAutoTitle: true });
      hideAiLoadingModal();

      // 🩹 Pastikan ID DB valid
      let numericProcId = parseInt(procId);
      if (numericProcId > 9999999999) {
        console.warn("⚠️ Detected temporary timestamp ID, trying to resolve from DB...");
        const foundProc = Object.values(window.claimState.simulasi || {})
          .flatMap(s => s.tindakan || [])
          .find(t =>
            (t.nama === procedureName ||
            t.procedure_text === procedureName ||
            t.tindakan === procedureName) &&
            t.procedure_id && t.procedure_id < 9999999999
          );
        if (foundProc) {
          numericProcId = foundProc.procedure_id;
          console.log("✅ Resolved procedure_id from simulation data:", numericProcId);
        } else {
          console.warn("❌ No valid procedure_id found, fallback to null");
          numericProcId = null;
        }
      }

      // 🔹 Sinkronkan hasil analisis ke simulasi (agar deskripsi muncul tanpa reload)
      if (window.claimState?.simulasi) {
        Object.values(window.claimState.simulasi).forEach(stage => {
          const tindakan = stage.tindakan || [];
          tindakan.forEach(t => {
            if (t.procedure_text === procedureName) {
              t.deskripsi = d.deskripsi || d.icd9_desc || d.icd9_description || d.icd9_code || "-";
              t.analyzed = true;
            }
          });
        });
      }

      // ============================================================
      // 🩹 PATCH: update deskripsi tindakan di diagnosis tanpa hapus daftar lama
      // ============================================================
      try {
        const stage = window.claimState.tab || "admission";
        const semuaTindakan = window.claimState.simulasi?.[stage]?.tindakan || [];
        const diagnosis = window.claimState.currentDiagnosis;

        if (Array.isArray(semuaTindakan) && diagnosis?.tindakan?.length) {
          diagnosis.tindakan.forEach(tDx => {
            const match = semuaTindakan.find(
              tSim =>
                tSim.procedure_text === tDx.procedure_text ||
                tSim.nama === tDx.nama
            );
            if (match) {
              tDx.deskripsi =
                match.deskripsi ||
                match.icd9_desc ||
                match.icd9_description ||
                match.icd9_code ||
                tDx.deskripsi ||
                "-";
              tDx.analyzed = true;
            }
          });
          console.log("🩵 [SYNC] Deskripsi tindakan diperbarui tanpa hapus list diagnosis.");
        } else {
          console.warn("⚠️ [SYNC] Tidak ada tindakan untuk disinkronkan.");
        }
      } catch (err) {
        console.warn("⚠️ [SYNC] Gagal sinkronisasi deskripsi tindakan:", err);
      }

      // ============================================================
      // 🩹 FINAL PATCH: perbarui diagnosis dengan hasil tindakan terkini
      // ============================================================
      try {
        const stage = window.claimState.tab || "admission";
        const semuaTindakan = window.claimState.simulasi?.[stage]?.tindakan || [];
        const diagnosis = window.claimState.currentDiagnosis;

        if (Array.isArray(semuaTindakan) && diagnosis?.tindakan?.length) {
          diagnosis.tindakan.forEach(td => {
            const match = semuaTindakan.find(
              tSim => tSim.nama === td.nama || tSim.procedure_text === td.procedure_text
            );
            if (match) {
              // hanya update kalau deskripsi lengkap (hasil analisis)
              if (match.deskripsi && match.deskripsi.includes("ICD-9:")) {
                td.deskripsi = match.deskripsi;
                td.analyzed = true;
              }
            }
          });
          console.log("🩵 [FINAL PATCH] Diagnosis diperbarui dengan deskripsi tindakan terkini");
        }
      } catch (e) {
        console.warn("⚠️ [FINAL PATCH] gagal update diagnosis:", e);
      }

    } catch (err) {
      console.error("❌ Gagal load detail tindakan:", err);
    }
  }

// ============================================================
// 🔹 OPEN MANUAL DETAIL MODAL (lossless)
// ============================================================
export async function openManualDetailModal(it, tab, idx) {
  try {
    showAiLoadingModal(["Mengambil data...", "Menganalisis hasil...", "Menyiapkan tampilan..."]);
    const url = `/claims/search/tindakan/detail/${encodeURIComponent(it.procedure_text)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("HTTP " + res.status);
    const json = await res.json();
    if (json.status !== "ok") throw new Error("Gagal load detail");

    const detail = json.data;
    const deskripsiGabungan = `ICD-9: ${detail.icd9 || ""}, Status: ${detail.status || ""}, INA-CBG: ${detail.ina_cbg || ""}`;
    detail.deskripsi = deskripsiGabungan;

    if (window.claimState?.simulasi?.[tab]?.tindakan?.[idx]) {
      window.claimState.simulasi[tab].tindakan[idx].deskripsi = deskripsiGabungan;
    }

    // 🟡 judul tengah dua baris + tombol ✕ kanan atas
    const title = `
      <div class="flex flex-col items-center animate-fade-in">
        <div>
          <span class="text-sm font-semibold text-white">Detail Tindakan Manual</span>
          <span class="text-2xl font-bold text-yellow-500">${detail.procedure_text}</span>
        </div>
        <button type="button"
                onclick="
                  try {
                    const stage = window.claimState.tab || 'admission';
                    const list = window.claimState.simulasi?.[stage]?.tindakan || [];
                    if (Array.isArray(list) && window.claimState.currentDiagnosis) {
                      window.claimState.currentDiagnosis.tindakan = list;
                      console.log('🩵 [SYNC] tindakan disalin ke diagnosis');
                    }
                  } catch (err) {
                    console.warn('⚠️ [SYNC] gagal sinkronisasi:', err);
                  }
                  window.closeNestedModal();
                "
                class="absolute top-0 right-0 text-white bg-red-500 hover:bg-red-600 px-3 py-1 rounded">
          ✕
        </button>
      </div>
    `;

    // panggil modal tanpa auto-title default
    openModal(title, renderProcedureDetail(detail), {
      hideDefaultClose: true
    });

    hideAiLoadingModal();
    // simpan referensi supaya regulasi tahu asalnya
    detail.isManual = true; // tandai sebagai manual
    window.claimState.currentProcedure = detail;
    const uiId = `manual-tindakan-${tab}-${idx}`;
    updateRingkasanFromRow(uiId, detail);
  } catch (err) {
    console.error("❌ Gagal load detail tindakan manual:", err);
  }
}

// ============================================================
// 🔹 RENDER TINDAKAN LIST (lossless)
// ============================================================
export function renderTindakan(list) {
  const isDark = document.documentElement.classList.contains("dark");

  const tindakanList =
    list && list.length > 0
      ? list
          .map(td => {
            const nama = td.nama || td.tindakan || "";
            const procId = td.procedure_id || td.id || "";

            const description = td.analyzed
              ? td.deskripsi || td.deskripsi_tindakan || td.icd9 || "&nbsp;"
              : "&nbsp;";





            return `
              <div class="grid grid-cols-3 gap-4 items-center ${
                isDark ? "bg-slate-800 text-white border-slate-700" : "bg-white text-gray-900 border-slate-200"
              } p-4 rounded-xl shadow-sm hover:shadow-md transition-shadow border mb-3"
                  data-procid="${procId}">
                <div class="font-semibold text-blue-600 underline cursor-pointer truncate"
                    onclick="openProcedureModal('${procId}', '${nama}')">${nama}</div>
                <div>
                  <span class="block px-3 py-1 text-sm font-medium ${
                    isDark ? "bg-slate-700 text-gray-100" : "bg-gray-100 text-gray-900"
                  } rounded shadow-sm whitespace-nowrap overflow-hidden text-ellipsis">
                    ${description || "&nbsp;"}
                  </span>
                </div>

                <div class="flex space-x-2 justify-end">
                  <button type="button"
                          onclick="updateSimulasi('tindakan','Primary','${nama}','Manual', window.claimState.tab)"
                          class="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white px-4 py-2 rounded-lg text-xs font-medium shadow-md hover:shadow-lg transition-all transform hover:-translate-y-0.5">Pilih Utama</button>
                  <button type="button"
                          onclick="updateSimulasi('tindakan','Secondary','${nama}','Manual', window.claimState.tab)"
                          class="bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white px-4 py-2 rounded-lg text-xs font-medium shadow-md hover:shadow-lg transition-all transform hover:-translate-y-0.5">Pilih Sekunder</button>
                </div>
              </div>
            `;
          })
          .join("")
      : `<div class="italic text-gray-500 dark:text-gray-400">Tidak ada tindakan AI</div>`;

  const manualForm =
    window.claimState?.role === "doctor"
      ? `
      <div class="tindakan-list mt-4"></div>
      <div class="mt-4 p-4 border ${
        isDark ? "border-slate-600 bg-slate-800 text-white" : "border-slate-200 bg-gray-50 text-gray-900"
      } rounded-xl shadow-sm">
        <div class="font-semibold mb-3">Tambah Tindakan Manual</div>

        <div class="relative flex flex-col gap-2 mt-2" x-data="AIClaim.tindakanAutocomplete()" x-ref="acWrap">
          <div class="flex gap-2">
            <input type="text"
                  x-model="query"
                  x-ref="acInput"
                  @focus="setTimeout(() => rehydrateManualTindakan(window.claimState.tab), 50)"
                  @input.debounce.300ms="search"
                  @keydown.enter.prevent="results.length ? select(results[0]) : addManualTindakanIfNotFound()"
                  placeholder="Nama Tindakan"
                  class="flex-1 px-4 py-2 rounded-lg border focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 transition-all
                        ${
                          isDark
                            ? "bg-slate-900 text-slate-100 border-slate-600"
                            : "bg-white text-slate-900 border-slate-300"
                        }">
            <button type="button"
                    class="bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white px-4 py-2 rounded-lg font-medium shadow-md hover:shadow-lg transition-all"
                    @click="handleAddManualTindakan(window.claimState.tab)">+</button>
          </div>

          <!-- ✅ Dropdown hasil pencarian tindakan -->
          <ul class="absolute z-50 bg-white dark:bg-slate-800 border dark:border-slate-600 rounded-lg shadow w-full mt-1"
              x-show="results && results.length"
              x-transition>
            <template x-for="r in results" :key="r.procedure_text">
              <li @click="select(r)"
                  class="px-3 py-2 text-sm hover:bg-blue-100 dark:hover:bg-slate-700 cursor-pointer"
                  x-text="r.procedure_text"></li>
            </template>
          </ul>
        </div>
      </div>
    `
      : "";

  setTimeout(() => window.renderManualTindakanList && window.renderManualTindakanList(), 0);

  return tindakanList + manualForm;
}
// ============================================================
// 🔹 RENDER PROCEDURE DETAIL (lossless)
// ============================================================
export function renderProcedureDetail(it) {
  console.log("📋 renderProcedureDetail data:", it);

  const isDark = document.documentElement.classList.contains("dark");
  const bgBox = isDark ? "bg-slate-800 text-white" : "bg-gray-50 text-gray-900";
  const borderCls = isDark ? "border-slate-700" : "border-slate-200";

  const multilayerRules = it.multilayer_rules || {};
  const notif = it.notifications || {};

  const renderBox = (label, value, field = null) => {
    const multilayer = multilayerRules[field];
    const hasReg = multilayer && multilayer.items && multilayer.items.length > 0;
    const safeVal = value || "-";

    let content = `<div class="whitespace-pre-line leading-relaxed">${safeVal}</div>`;

    if (hasReg) {
      const list = multilayer.items
        .map(
          r => `<li class="ml-5 list-disc text-sm leading-snug marker:text-blue-400 dark:marker:text-blue-300">
                  ${r.isi}
                  ${r.sumber ? `<span class='text-xs text-gray-400 dark:text-gray-500 ml-1'>(${r.sumber})</span>` : ""}
                </li>`
        )
        .join("");
      const combined = multilayer.combined_label
        ? `<div class="text-xs italic text-blue-400 mt-1">Gabungan aturan: ${multilayer.combined_label}</div>`
        : "";
      content = `<ul class="space-y-1">${list}</ul>${combined}`;
    }

    const hasRegulation = typeof checkFieldHasRegulation === "function" && checkFieldHasRegulation(field);
    if (hasRegulation && field && safeVal !== "-") {
      content = `<span class="cursor-pointer hover:underline hover:text-blue-600 regulation-field border-b border-dashed border-gray-400 hover:border-blue-600 transition-all duration-200"
                      title="📋 Klik untuk melihat regulasi ${field}"
                      data-field="${field}"
                      data-procedure-id="${it.id || it.procedure_id || ''}"
                      onclick="window.openRegulationDetailModal('${field}', null, '${it.id || it.procedure_id || ''}')">${safeVal}</span>`;
    }

    return `
      <div class="grid grid-cols-2 border ${borderCls} rounded-lg overflow-hidden mb-2">
        <div class="bg-gray-100 dark:bg-slate-700 px-3 py-2 font-semibold">${label}</div>
        <div class="bg-white dark:bg-slate-800 px-3 py-2">${content}</div>
      </div>
    `;
  };

  return `
    <div class="${bgBox} text-sm p-3 rounded-xl space-y-4">
      ${renderNotificationBox("tindakan", notif)}

      ${renderBox("Kode ICD-9", it.icd9 || it.icd9_code, "icd9_code")}
      ${renderBox("Deskripsi", it.deskripsi || it.icd9_desc || "-", "deskripsi")}
      ${renderBox("Status", it.status_tindakan || it.status, "status_tindakan")}
      ${renderBox("Validitas", it.validitas, "validitas")}
      ${renderBox("Tarif INA-CBG", it.ina_cbg_tarif || it.ina_cbg, "ina_cbg")}
      ${renderBox("Faskes", it.faskes, "faskes")}
      ${renderBox("Rawat Inap", it.rawat_inap, "rawat_inap")}
      ${renderBox("Syarat Klinis", it.syarat_klinis, "syarat_klinis")}
    </div>
  `;
}

// ============================================================
// 🔗 Window shim (kompatibilitas lama)
// ============================================================
if (typeof window !== "undefined") {
  window.openProcedureModal = openProcedureModal;
  window.openManualDetailModal = openManualDetailModal;
  window.renderProcedureDetail = renderProcedureDetail;
  window.renderTindakan = renderTindakan;
}