// claim.modals.js - CLEAN VERSION
// Modal system untuk diagnosis dan procedure details

(() => {
  "use strict";

  // === MODAL SYSTEM ===
  function openModal(title, content, options = {}) {
    const modal = document.createElement("div");
    modal.className = "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50";
    modal.innerHTML = `
      <div class="bg-white dark:bg-gray-900 max-w-6xl w-full max-h-screen overflow-auto p-6 rounded shadow-lg relative mx-4">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold text-gray-900 dark:text-gray-100">${title}</h2>
          ${!options.hideDefaultClose ? `<button onclick="this.closest('.fixed').remove()" class="text-red-500 hover:text-red-700 text-xl font-bold">✕</button>` : ''}
        </div>
        <div class="text-gray-900 dark:text-gray-100">${content}</div>
      </div>
    `;
    document.body.appendChild(modal);
  }

  function closeNestedModal() {
    const modals = document.querySelectorAll(".fixed.inset-0");
    if (modals.length > 1) {
      modals[modals.length - 1].remove();
    }
  }

  // === DIAGNOSIS MODAL ===
  async function openModalFromAttr(claimId, diseaseName, element) {
    try {
      if (!claimId || !diseaseName) {
        console.error("❌ Missing claimId or diseaseName", { claimId, diseaseName });
        return;
      }

      // Simpan current diagnosis untuk regulation modal
      window.claimState = window.claimState || {};
      window.claimState.currentDiagnosis = { 
        id: element?.dataset?.diagnosisId || claimId, 
        name: diseaseName 
      };

      console.log("[REQ] POST /analyze_diagnosis", { claim_id: claimId, disease_name: diseaseName });

      // Request ke core_engine via proxy endpoint
      const response = await fetch("/analyze_diagnosis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_id: parseInt(claimId),
          disease_name: diseaseName,
          rekam_medis: []
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      console.log("[RESP] /analyze_diagnosis", result);
      
      if (result && typeof result === 'object') {
        const content = renderDiagnosisDetail(result);
        openModal(`Detail Diagnosis: ${diseaseName}`, content, { hideDefaultClose: false });
      } else {
        console.error("❌ Invalid response format:", result);
        alert("Response tidak valid dari server");
      }

    } catch (error) {
      console.error("❌ Error in openModalFromAttr:", error);
      alert(`Gagal memuat detail diagnosis: ${error.message}`);
    }
  }

  // === PROCEDURE MODAL ===
  async function openProcedureModal(procedureId, procedureName) {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    
    console.log("🔥 openProcedureModal called", { procedureId, procedureName, claimId });
    
    if (!claimId || !procedureName) {
      alert("Claim ID atau nama tindakan tidak ditemukan.");
      return;
    }

    // Simpan current procedure untuk regulation modal
    window.claimState = window.claimState || {};
    window.claimState.currentProcedure = { 
      id: procedureId, 
      name: procedureName 
    };

    try {
      console.log("[REQ] POST /analyze_procedure", { claim_id: claimId, procedure_name: procedureName });
      
      const res = await fetch("/analyze_procedure", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          claim_id: parseInt(claimId), 
          procedure_name: procedureName,
          rekam_medis: []
        })
      });
      
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      
      const result = await res.json();
      console.log("[RESP] /analyze_procedure", result);
      
      const d = result.data || result;

      const content = `
        <div class="flex justify-between items-center mb-3">
          <h3 class="text-lg font-bold">Detail Tindakan: ${procedureName}</h3>
          <button type="button" onclick="closeNestedModal()" class="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded">✕</button>
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white">Kode ICD-9:</div>
          <div class="bg-gray-800 px-3 py-2 rounded text-white">${d.icd9_code || '-'}</div>
          <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white">Deskripsi:</div>
          <div class="bg-gray-800 px-3 py-2 rounded text-white">${d.icd9_desc || '-'}</div>
          <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white">Validitas:</div>
          <div class="bg-gray-800 px-3 py-2 rounded text-white">${d.validitas || '-'}</div>
          <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white">Status:</div>
          <div class="bg-gray-800 px-3 py-2 rounded text-white">${d.status_tindakan || '-'}</div>
          <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white">INA-CBG:</div>
          <div class="bg-gray-800 px-3 py-2 rounded text-white">${d.ina_cbg_tarif || '-'}</div>
        </div>
      `;

      openModal(`Detail Tindakan: ${procedureName}`, content, { hideDefaultClose: true });

    } catch (err) {
      console.error("❌ Gagal load detail tindakan:", err);
      alert(`Error loading procedure detail: ${err.message}`);
    }
  }

  // === DIAGNOSIS DETAIL RENDERER ===
  function renderDiagnosisDetail(it) {
    // Parse data from /analyze_diagnosis response format
    const klinis = {
      justifikasi: it.justifikasi || "-",
      bukti_klinis: it.bukti_klinis || "-", 
      syarat_klinis: it.syarat_klinis || "-"
    };

    const icd10 = {
      kode_icd: it.icd10_code || "-",
      struktur_icd10: it.struktur_icd10 || "-",
      kode_ganda: it.kode_ganda || "-",
      z_code: it.z_code || "-",
      kode_bpjs_khusus: it.kode_bpjs_khusus || "-"
    };
    
    const tindakan = it.tindakan || [];
    const rawat = it.rawat_inap || {};
    const faskes = it.faskes || {};
    const rujukan = it.rujukan || {};
    const inaCbg = it.ina_cbg || {};

    // Fields yang memerlukan regulasi
    const regulationFields = {
      "Justifikasi": "justifikasi",
      "Syarat Klinis": "syarat_klinis", 
      "Kode ICD": "icd10_code",
      "Struktur ICD 10": "struktur_icd10",
      "Kode Ganda": "kode_ganda",
      "Z-Code": "z_code",
      "Kode Khusus BPJS": "kode_bpjs_khusus",
      "Indikasi": "indikasi_rawat",
      "Kriteria": "kriteria_rawat",
      "Lama Rawat": "lama_rawat",
      "Tingkat": "kesesuaian_rs",
      "Kompetensi": "kompetensi_rs",
      "Tujuan": "tujuan_rujukan",
      "Kode INA-CBG": "kode_ina_cbg"
    };

    const renderBox = (label, value, status = "default") => {
      let colorClass = "bg-gray-200 text-gray-800";
      if (status === "valid") colorClass = "bg-green-600 text-white";
      if (status === "invalid") colorClass = "bg-red-600 text-white";
      const safeValue = value || "-";
      
      // Check if this field needs regulation
      const fieldName = regulationFields[label];
      const hasRegulation = fieldName && safeValue !== "-";
      
      const content = hasRegulation
        ? `<span class="cursor-pointer underline hover:text-blue-600" title="Klik untuk lihat regulasi" onclick="openRegulationDetailModal('${fieldName}', '${label}', '${safeValue}', null)">${safeValue}</span>`
        : safeValue;
        
      return `
        <div class="grid grid-cols-2">
          <div class="bg-gray-700 text-white px-3 py-2">${label}</div>
          <div class="${colorClass} px-3 py-2">${content}</div>
        </div>
      `;
    };

    return `
      <div class="space-y-6 text-sm">
        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">KLINIS</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderBox("Justifikasi", klinis.justifikasi)}
            ${renderBox("Bukti Klinis", klinis.bukti_klinis)}
            ${renderBox("Syarat Klinis", klinis.syarat_klinis)}
          </div>
        </section>

        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">ICD-10</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderBox("Kode ICD", icd10.kode_icd)}
            ${renderBox("Struktur ICD 10", icd10.struktur_icd10)}
            ${renderBox("Kode Ganda", icd10.kode_ganda)}
            ${renderBox("Z-Code", icd10.z_code)}
            ${renderBox("Kode Khusus BPJS", icd10.kode_bpjs_khusus)}
          </div>
        </section>

        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">TINDAKAN</div>
          <div class="p-3 bg-gray-100 dark:bg-gray-700">
            ${renderTindakan(tindakan)}
          </div>
        </section>

        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">RAWAT INAP</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderBox("Indikasi", rawat.indikasi)}
            ${renderBox("Kriteria", rawat.kriteria)}
            ${renderBox("Lama Rawat", rawat.lama_rawat)}
          </div>
        </section>

        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">FASKES</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderBox("Tingkat", faskes.tingkat)}
            ${renderBox("Justifikasi", faskes.justifikasi)}
            ${renderBox("Kompetensi", faskes.kompetensi)}
          </div>
        </section>

        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">RUJUKAN</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderBox("Indikasi", rujukan.indikasi)}
            ${renderBox("Tujuan", rujukan.tujuan)}
            ${renderBox("Kriteria", rujukan.kriteria)}
          </div>
        </section>

        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">INA-CBG</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderBox("Kode INA-CBG", inaCbg.kode)}
            ${renderBox("Deskripsi", inaCbg.deskripsi)}
            ${renderBox("Tarif", inaCbg.tarif ? `Rp ${parseInt(inaCbg.tarif).toLocaleString('id-ID')}` : "-")}
          </div>
        </section>
      </div>
    `;
  }

  function renderTindakan(list) {
    const tindakanList = (list && list.length > 0)
      ? list.map(td => {
          const nama = td.nama || td.tindakan || "-";
          const deskripsi = td.deskripsi || td.description || "-";
          const kode = td.kode || td.code || "";
          const procId = td.id || td.procedure_id || kode || "";
          return `
            <div class="grid grid-cols-3 gap-4 items-center bg-white dark:bg-gray-800 p-3 rounded shadow mb-2"
                data-procid="${procId}">
              <div class="font-semibold text-blue-600 underline cursor-pointer truncate"
                   onclick="openProcedureModal('${procId}', '${nama}')">${nama}</div>
              <div>
                <span class="block px-3 py-1 text-sm font-medium bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded shadow-sm whitespace-nowrap overflow-hidden text-ellipsis"
                      title="${deskripsi}">${deskripsi}</span>
              </div>
              ${window.claimState?.role === "doctor" ? `
                <div class="flex space-x-2 justify-end">
                  <button type="button"
                          class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs">Pilih Utama</button>
                  <button type="button"
                          class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-xs">Pilih Sekunder</button>
                </div>` : ``}
            </div>
          `;
        }).join("")
      : `<div class="italic text-gray-500">Tidak ada tindakan AI</div>`;

    return `<div class="space-y-4">${tindakanList}</div>`;
  }

  // === REGULATION MODAL ===
  async function openRegulationDetailModal(fieldName, fieldLabel, currentValue, diagnosisId) {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    
    if (!claimId) {
      alert("Claim ID tidak ditemukan");
      return;
    }

    try {
      const url = `/claims/${claimId}/regulations?field_name=${fieldName}&field_type=diagnosis${diagnosisId ? `&diagnosis_id=${diagnosisId}` : ''}`;
      
      console.log(`[REQ] GET ${url} for field: ${fieldName}`);
      
      const response = await fetch(url);
      const result = await response.json();
      
      console.log("[RESP] Regulation detail", result);
      
      if (result.status === "success" && result.data && result.data.length > 0) {
        const regulation = result.data[0];
        
        const content = `
          <div class="space-y-4 text-sm">
            <div class="bg-blue-100 p-3 rounded mb-4">
              <strong>Field:</strong> ${fieldLabel}<br>
              <strong>Nilai:</strong> ${currentValue}
            </div>
            <div class="grid grid-cols-2 gap-y-2 text-sm">
              <div class="bg-gray-700 text-white font-semibold px-3 py-2 rounded-l">Dasar Hukum</div>
              <div class="bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2 rounded-r text-gray-800">${regulation.dasar_hukum}</div>

              <div class="bg-gray-700 text-white font-semibold px-3 py-2 rounded-l">Judul Regulasi</div>
              <div class="bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2 rounded-r text-gray-800">${regulation.judul_regulasi}</div>

              <div class="bg-gray-700 text-white font-semibold px-3 py-2 rounded-l">Pasal / Ayat / Bab</div>
              <div class="bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2 rounded-r italic text-gray-800">${regulation.bab_pasal}</div>

              <div class="bg-gray-700 text-white font-semibold px-3 py-2 rounded-l">Isi / Penjelasan</div>
              <div class="bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2 rounded-r text-gray-800">${
                Array.isArray(regulation.isi) 
                  ? regulation.isi.map(item => `• ${item}`).join('<br>') 
                  : regulation.isi
              }</div>
            </div>
          </div>
        `;

        openModal(`Regulasi: ${fieldLabel}`, content, { hideDefaultClose: false });
        
      } else {
        alert(result.message || "Tidak ada regulasi untuk field ini");
      }
      
    } catch (error) {
      console.error("❌ Error loading regulation:", error);
      alert("Gagal memuat detail regulasi");
    }
  }

  // === EXPORTS ===
  window.openModal = openModal;
  window.closeNestedModal = closeNestedModal;
  window.openModalFromAttr = openModalFromAttr;
  window.openProcedureModal = openProcedureModal;
  window.renderDiagnosisDetail = renderDiagnosisDetail;
  window.renderTindakan = renderTindakan;
  window.openRegulationDetailModal = openRegulationDetailModal;

})();