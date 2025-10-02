// =============== Semua modal (diagnosis/procedure/regulasi) ===============

(function () {
  // Field regulation mapping based on requirements
  const REGULATION_FIELDS = {
    // Detail Diagnosis - Aspek Klinis
    'justifikasi': true,           // ✅ Perlu regulasi (PNPK/CP/Permenkes)
    'bukti_klinis': false,         // ❌ Tidak perlu regulasi (hanya evidence klinis)
    'syarat_klinis': true,         // ✅ Perlu regulasi (PNPK, CP, Permenkes)
    'confidence_ai': false,        // ❌ Tidak perlu regulasi (murni hasil AI)
    
    // ICD-10
    'kode_icd': true,             // ✅ Perlu regulasi (ICD-10 WHO + mapping BPJS)
    'struktur_icd10': true,       // ✅ Perlu regulasi (aturan ICD-10 resmi)
    'kode_ganda': true,           // ✅ Perlu regulasi (aturan ICD-10 resmi)
    'z_code': true,               // ✅ Perlu regulasi (aturan ICD-10 resmi)
    'kode_bpjs_khusus': true,     // ✅ Perlu regulasi (aturan BPJS/e-Claim)
    
    // Tindakan terkait
    'syarat_klinis_tindakan': true,   // ✅ Perlu regulasi (PNPK/CP)
    'status_tindakan': true,          // ✅ Perlu regulasi (CP/INA-CBG)
    'ina_cbg_impact': true,           // ✅ Perlu regulasi (Casemix INA-CBG)
    
    // Rawat Inap
    'indikasi': true,             // ✅ Perlu regulasi (CP/PNPK)
    'kriteria': true,             // ✅ Perlu regulasi (CP/PNPK)
    'lama_rawat': true,           // ✅ Perlu regulasi (INA-CBG)
    
    // Faskes
    'tingkat': true,              // ✅ Perlu regulasi (Permenkes RS)
    'justifikasi_faskes': true,   // ✅ Perlu regulasi (Permenkes RS)
    'kompetensi': true,           // ✅ Perlu regulasi (Permenkes RS)
    
    // Rujukan
    'indikasi_rujukan': true,     // ✅ Perlu regulasi (Permenkes Rujukan)
    'tujuan': true,               // ✅ Perlu regulasi (Permenkes Rujukan)
    'kriteria_rujukan': true,     // ✅ Perlu regulasi (Permenkes Rujukan)
    
    // INA-CBG
    'kode': true,                 // ✅ Perlu regulasi (INA-CBG resmi)
    'deskripsi': true,            // ✅ Perlu regulasi (INA-CBG resmi)
    'tarif': true,                // ✅ Perlu regulasi (Casemix INA-CBG)
    
    // Detail Tindakan (Modal Procedure)
    'icd9_code': true,            // ✅ Perlu regulasi (ICD-9-CM resmi)
    'icd9_desc': true,            // ✅ Perlu regulasi (ICD-9-CM resmi)
    'deskripsi': true,            // ✅ Perlu regulasi (ICD-9-CM resmi)
    'validitas': false,           // ❌ Tidak perlu regulasi (logic sistem AI)
    'status': true,               // ✅ Perlu regulasi (CP/PNPK, INA-CBG)
    'ina_cbg': true,              // ✅ Perlu regulasi (Casemix INA-CBG)
    'faskes': true,               // ✅ Perlu regulasi (Permenkes RS)
    'rawat_inap': true,           // ✅ Perlu regulasi (INA-CBG, PNPK)
    'syarat_klinis': true,        // ✅ Perlu regulasi (CP/PNPK)
    'rawat_inap_tindakan': true,  // ✅ Perlu regulasi (INA-CBG, PNPK)
  };

  function checkFieldHasRegulation(fieldName) {
    if (!fieldName) return false;
    return REGULATION_FIELDS[fieldName] === true;
  }
  function openModal(title, content, { hideDefaultClose = false } = {}) {
    const root = document.getElementById('claimRoot');
    const state = Alpine.$data(root);
    state.modalOpen = true;
    state.modalTitle = title;
    state.modalContent = content;
    state.hideDefaultClose = hideDefaultClose;
  }

  function updateRingkasanFromRow(itemId, dx) {
    if (!dx || !itemId) return;

    const row = document.querySelector(`[data-id="${itemId}"]`);
    if (!row) return;

    // kolom Klinis
    const klinisCell = row.querySelector(".col-klinis");
    if (klinisCell) {
      let text = "";
      if (Array.isArray(dx.klinis)) text = dx.klinis.filter(Boolean).join(", ");
      else if (typeof dx.klinis === "string") text = dx.klinis;
      else if (typeof dx.klinis === "object" && dx.klinis !== null) {
        text = [dx.klinis.justifikasi, dx.klinis.bukti_klinis, dx.klinis.syarat_klinis].filter(Boolean).join(", ");
      }
      klinisCell.innerHTML = text ? `<span title="${text}">${truncateText(text, 44)}</span>` : "-";
    }

    // kolom ICD
    const icdCell = row.querySelector(".col-icd");
    if (icdCell) {
      if (dx.icd10_code) icdCell.innerText = dx.icd10_code;
      else if (dx.icd10 && dx.icd10.kode_icd) icdCell.innerText = dx.icd10.kode_icd;
      else if (dx.icd9_code) icdCell.innerText = dx.icd9_code;
      else icdCell.innerText = "-";
    }

    // kolom Tindakan
    const tindakanCell = row.querySelector(".col-tindakan");
    if (tindakanCell) {
      if (dx.tindakan && dx.tindakan.length > 0) {
        const text = dx.tindakan.map(t => t.procedure_text || t.tindakan).join(", ");
        tindakanCell.innerHTML = `<span title="${text}">${truncateText(text, 44)}</span>`;
      } else {
        tindakanCell.innerText = "-";
      }
    }
  }

  // Buka modal dari klik kategori
  async function openModalFromAttr(el, type) {
    const tr = el.closest("tr");
    const dbId = tr?.dataset.dbId;
    const uiId = tr?.dataset.id;
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    
    // Ambil nama penyakit dari cell yang diklik
    let diseaseName = "";
    if (el.textContent) {
      diseaseName = el.textContent.replace(/^→+\s*/, "").trim();
    } else {
      diseaseName = tr?.querySelector(".kategori-cell")?.textContent?.trim() || tr?.dataset.nama || "";
    }

    try {
      let dx = {};
      // 🔥 NEW: Jika type diagnosis/komorbid/komplikasi, POST ke /analyze_diagnosis (core_engine)
      if (["diagnosis","komorbid","komplikasi"].includes(type) && claimId && diseaseName) {
        console.log("[REQ] POST /analyze_diagnosis", { claim_id: claimId, disease_name: diseaseName });
        const res = await fetch("/analyze_diagnosis", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            claim_id: parseInt(claimId), 
            disease_name: diseaseName,
            rekam_medis: []
          })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        const result = await res.json();
        console.log("[RESP] /analyze_diagnosis", result);
        
        // 🔥 Process core_engine response untuk modal
        window.claimState.currentDiagnosis = result;
        window.claimState.currentDiagnosisTitle = diseaseName;
        
        const modalContent = renderDiagnosisDetail(result);
        openModal(`<div class="flex flex-col items-start items-center">
          <span class="text-lg font-bold">Detail Diagnosis</span>
          <span class="font-bold text-2xl mb-2 text-yellow-500">${diseaseName}</span>
        </div>`, modalContent);
        return;
      } else if (dbId && !isNaN(Number(dbId))) {
        // fallback legacy detail
        const url = `/claims/ai/recommendation/detail?claim_id=${claimId}&rec_type=${type}&item_id=${dbId}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const result = await res.json();
        dx = result.data;
      } else {
        dx = tr?.dataset.row ? JSON.parse(tr.dataset.row) : {};
      }

      if ((!dbId || isNaN(Number(dbId))) && tr?.dataset.row) {
        dx = JSON.parse(tr.dataset.row);
        window.claimState.currentDiagnosis = dx;
        window.claimState.currentDiagnosisTitle = dx.kategori || dx.name || "-";
        
        // 🔥 Use new renderDiagnosisDetail for consistent parsing
        const modalContent = renderDiagnosisDetail(dx);
        openModal(`<div class="flex flex-col items-start items-center">
          <span class="text-lg font-bold">Detail Diagnosis</span>
          <span class="font-bold text-2xl mb-2 text-yellow-500">${window.claimState.currentDiagnosisTitle}</span>
        </div>`, modalContent);
        return;
      }

      let rawText = tr?.querySelector("td")?.innerText.trim() || "-";
      rawText = rawText.replace(/^▶|^▼/, "").trim();
      rawText = rawText.replace(/\s+\d+$/, "");
      const namaPenyakit =
        dx?.kategori || dx?.nama_kategori || dx?.diagnosis || dx?.komorbid || dx?.komplikasi || rawText || "-";

      // 🔥 Use new renderDiagnosisDetail for consistent parsing
      const modalContent = renderDiagnosisDetail(dx);
      openModal(`<div class="flex flex-col items-start items-center">
        <span class="text-lg font-bold">Detail Diagnosis</span>
        <span class="font-bold text-2xl mb-2 text-yellow-500">${namaPenyakit}</span>
      </div>`, modalContent);
      window.claimState.currentDiagnosis = dx;
      window.claimState.currentDiagnosisTitle = namaPenyakit;

      updateRingkasanFromRow(uiId, dx);
    } catch (err) {
      console.error("❌ Gagal load modal detail:", err);
    }
  }

  function renderDiagnosisDetail(it) {
    // 🔥 Parse data from /analyze_diagnosis response format (nested structure)
    console.log("📋 renderDiagnosisDetail received data:", it);
    console.log("📋 it.klinis:", it.klinis);
    console.log("📋 it.icd10:", it.icd10);
    console.log("📋 it.tindakan:", it.tindakan);
    
    // Fallback for diagnosisId - use available id fields
    const diagnosisId = it.id || it.diagnosis_id || it.itemId || Date.now();
    console.log("📋 Using diagnosisId:", diagnosisId);
    
    // Handle nested structure from core_engine - detailed parsing
    const klinis = {
      justifikasi: it.klinis?.justifikasi || it.justifikasi || "-",
      bukti_klinis: it.klinis?.bukti_klinis || it.bukti_klinis || "-", 
      syarat_klinis: it.klinis?.syarat_klinis || it.syarat_klinis || "-",
      status: it.klinis?.status || it.status || "default"
    };

    const icd10 = {
      kode_icd: it.icd10?.kode_icd || it.icd10_code || "-",
      struktur_icd10: it.icd10?.struktur_icd10 || it.struktur_icd10 || "-",
      kode_ganda: it.icd10?.kode_ganda || it.kode_ganda || "-",
      z_code: it.icd10?.z_code || it.z_code || "-",
      kode_bpjs_khusus: it.icd10?.kode_bpjs_khusus || it.kode_bpjs_khusus || "-",
      status_icd: it.icd10?.status_icd || it.status_icd || "default"
    };
    
    const tindakan = it.tindakan || [];
    const rawat = it.rawat || it.rawat_inap || {};
    const faskes = it.faskes || {};
    const rujukan = it.rujukan || {};
    const inaCbg = it.inaCbg || it.ina_cbg || {};
    
    console.log("📋 Parsed klinis:", klinis);
    console.log("📋 Parsed icd10:", icd10);
    console.log("📋 Parsed tindakan count:", tindakan.length);
    
    // 🔥 Debug specific field values
    console.log("📋 klinis.justifikasi:", klinis.justifikasi);
    console.log("📋 klinis.bukti_klinis:", klinis.bukti_klinis);
    console.log("📋 icd10.kode_icd:", icd10.kode_icd);
    console.log("📋 rawat.indikasi:", rawat.indikasi);

    const renderBox = (label, value, status = "default", diagnosisId = null, fieldName = null) => {
      let colorClass = "bg-gray-100 text-gray-800 dark:bg-gray-600 dark:text-gray-100";
      if (status === "valid") colorClass = "bg-green-600 text-white";
      if (status === "invalid") colorClass = "bg-red-600 text-white";
      
      const safeValue = value || "-";
      console.log(`📋 renderBox(${label}): value="${value}", safeValue="${safeValue}"`);
      
      // Check if field has regulation based on field mapping
      const hasRegulation = checkFieldHasRegulation(fieldName);
      
      let content = safeValue;
      if (hasRegulation && diagnosisId && safeValue !== "-") {
        content = `<span class="cursor-pointer hover:underline hover:text-blue-600 regulation-field border-b border-dashed border-gray-400 hover:border-blue-600 transition-all duration-200" 
                         title="📋 Klik untuk melihat regulasi ${fieldName}" 
                         data-field="${fieldName}"
                         data-diagnosis-id="${diagnosisId}"
                         onclick="openRegulationDetailModal('${fieldName}', ${diagnosisId})">${safeValue}</span>`;
      }
      
      const boxHtml = `
        <div class="grid grid-cols-2">
          <div class="bg-gray-700 text-white px-3 py-2">${label}</div>
          <div class="${colorClass} px-3 py-2">${content}</div>
        </div>
      `;
      console.log(`📋 renderBox(${label}) HTML:`, boxHtml);
      return boxHtml;
    };

    return `
      <div class="space-y-6 text-sm">
        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">KLINIS</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${(console.log("📋 KLINIS - justifikasi:", klinis.justifikasi, "status:", klinis.status), renderBox("Justifikasi", klinis.justifikasi, klinis.status, diagnosisId, "justifikasi"))}
            ${(console.log("📋 KLINIS - bukti_klinis:", klinis.bukti_klinis), renderBox("Bukti Klinis", klinis.bukti_klinis, null, null, "bukti_klinis"))}
            ${(console.log("📋 KLINIS - syarat_klinis:", klinis.syarat_klinis), renderBox("Syarat Klinis", klinis.syarat_klinis, klinis.status, diagnosisId, "syarat_klinis"))}
          </div>
        </section>

        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">ICD-10</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${(console.log("📋 ICD10 - kode_icd:", icd10.kode_icd), renderBox("Kode ICD", icd10.kode_icd, icd10.status_icd, diagnosisId, "kode_icd"))}
            ${renderBox("Struktur ICD 10", icd10.struktur_icd10, icd10.status_icd, diagnosisId, "struktur_icd10")}
            ${renderBox("Kode Ganda", icd10.kode_ganda, icd10.status_icd, diagnosisId, "kode_ganda")}
            ${renderBox("Z-Code", icd10.z_code, icd10.status_icd, diagnosisId, "z_code")}
            ${renderBox("Kode Khusus BPJS", icd10.kode_bpjs_khusus, icd10.status_icd, diagnosisId, "kode_bpjs_khusus")}
          </div>
        </section>

        <!-- i-DRG Section -->
        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">i-DRG</div>
          <div class="p-3 bg-gray-100 dark:bg-gray-700">
            ${renderIdrgSection(it.idrg_diagnosis)}
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
            ${renderBox("Indikasi", rawat.indikasi, rawat.status_indikasi, diagnosisId, "indikasi")}
            ${renderBox("Kriteria", rawat.kriteria, rawat.status_kriteria, diagnosisId, "kriteria")}
            ${renderBox("Lama Rawat", rawat.lama_rawat, rawat.status_lama, diagnosisId, "lama_rawat")}
          </div>
        </section>

        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">FASKES</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderBox("Tingkat", faskes.tingkat, faskes.status_tingkat, diagnosisId, "tingkat")}
            ${renderBox("Justifikasi", faskes.justifikasi, faskes.status_justifikasi, diagnosisId, "justifikasi_faskes")}
            ${renderBox("Kompetensi", faskes.kompetensi, faskes.status_kompetensi, diagnosisId, "kompetensi")}
          </div>
        </section>

        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">RUJUKAN</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderBox("Indikasi", rujukan.indikasi, rujukan.status_indikasi, diagnosisId, "indikasi_rujukan")}
            ${renderBox("Tujuan", rujukan.tujuan, rujukan.status_tujuan, diagnosisId, "tujuan")}
            ${renderBox("Kriteria", rujukan.kriteria, rujukan.status_kriteria, diagnosisId, "kriteria_rujukan")}
          </div>
        </section>

        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">INA-CBG</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderBox("Kode INA-CBG", inaCbg.kode, inaCbg.status_kode, diagnosisId, "kode")}
            ${renderBox("Deskripsi", inaCbg.deskripsi, inaCbg.status_deskripsi, diagnosisId, "deskripsi")}
            ${renderBox("Tarif", inaCbg.tarif ? `Rp ${parseInt(inaCbg.tarif).toLocaleString('id-ID')}` : "-", inaCbg.status_tarif, diagnosisId, "tarif")}
          </div>
        </section>
      </div>
    `;
  }

  function renderIdrgSection(idrg, claimId) {
    if (!idrg) {
      return `<div class="italic text-gray-500">Tidak ada prediksi i-DRG</div>`;
    }

    const renderRow = (label, value) => `
      <div class="grid grid-cols-2">
        <div class="bg-gray-700 text-white px-3 py-2">${label}</div>
        <div class="bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2">${value || "-"}</div>
      </div>
    `;

    const renderRowClickable = (label, value, field) => `
      <div class="grid grid-cols-2">
        <div class="bg-gray-700 text-white px-3 py-2">${label}</div>
        <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2"
            onclick="openRegulationModal('${claimId}', '${field}')">
          ${value || "-"}
        </div>
      </div>
    `;

    return `
      <div x-data="{ open: false }" class="border rounded shadow overflow-hidden mb-3">
        <div class="accordion-header flex items-center justify-between bg-blue-600 text-white px-3 py-2 font-bold cursor-pointer"
            @click="open = !open">
          <span>Prediksi i-DRG (Diagnosis)</span>
          <span x-text="open ? '▼' : '▶'"></span>
        </div>
        <div class="accordion-body" x-show="open" x-transition>
          ${renderRowClickable("Group i-DRG", idrg.group_idrg, "idrg_diagnosis_group")}
          ${renderRowClickable("Severity Index", idrg.severity_index, "idrg_diagnosis_severity")}
          ${renderRowClickable("Checklist Dokumentasi", idrg.checklist, "idrg_diagnosis_checklist")}
          ${renderRow("Faktor Severity", idrg.faktor_severity)}
          ${renderRowClickable("Ungroupable Alert", idrg.ungroupable_alert, "idrg_diagnosis_ungroupable")}
          ${renderRow("Simulasi Tarif", idrg.simulasi_tarif)}
          ${renderRow("Gap Analysis", idrg.gap_analysis)}
        </div>
      </div>
    `;
  }



  function renderTindakan(list) {
    const tindakanList = (list && list.length > 0)
      ? list.map(td => {
          const nama = td.nama || td.tindakan || "-";
          const deskripsi = td.deskripsi || td.description || "-";
          const procId = td.id || td.procedure_id || "";
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
                          onclick="updateSimulasi('tindakan','Primary','${nama}','Manual', window.claimState.tab)"
                          class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs">Pilih Utama</button>
                  <button type="button"
                          onclick="updateSimulasi('tindakan','Secondary','${nama}','Manual', window.claimState.tab)"
                          class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-xs">Pilih Sekunder</button>
                </div>` : ``}
            </div>
          `;
        }).join("")
      : `<div class="italic text-gray-500">Tidak ada tindakan AI</div>`;

    const manualForm = window.claimState?.role === "doctor" ? `
      <div class="tindakan-list mt-4"></div>
      <div class="mt-4 p-3 border rounded bg-gray-50 dark:bg-gray-700">
        <div class="font-semibold mb-2">Tambah Tindakan Manual</div>
        <div class="flex gap-2">
          <input id="manualNamaTindakan" placeholder="Nama Tindakan"
                 class="flex-1 px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600" />
          <button type="button" onclick="addManualTindakan()"
                  class="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded flex items-center">➕ Tambah</button>
        </div>
      </div>
    ` : '';

    // render list manual setelah modal terbuka
    setTimeout(() => window.renderManualTindakanList && window.renderManualTindakanList(), 0);

    return tindakanList + manualForm;
  }

  function buildModalContent(it) {
    let content = renderDiagnosisDetail(it);
    content += `<div class="tindakan-list mt-4"></div>`;
    setTimeout(() => window.renderManualTindakanList && window.renderManualTindakanList(), 0);
    return content;
  }

  async function openProcedureModal(procId, procedureName) {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    
    // Get procedure name from DOM if not provided
    if (!procedureName) {
      const procElement = document.querySelector(`[data-procid="${procId}"] .cursor-pointer`);
      procedureName = procElement?.textContent?.trim() || "Unknown Procedure";
    }
    
    console.log("🔥 openProcedureModal called", { procId, procedureName, claimId });

    try {
      // 🔥 NEW: Request ke core_engine /analyze_procedure
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
      
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const result = await res.json();
      console.log("[RESP] /analyze_procedure", result);
      
      const d = result.data || result;
      console.log("🧮 INA-CBG tarif raw:", d.ina_cbg_tarif, "| ina_cbg:", d.ina_cbg);

      const renderProcBox = (label, value, fieldName = null) => {
        let safeValue = value || "-";
        
        // 🧮 Special handling untuk tarif INA-CBG
        if (fieldName === "ina_cbg" && value && value !== "-") {
          console.log("💰 Formatting tarif:", value, typeof value);
          const numericValue = parseInt(value);
          if (!isNaN(numericValue)) {
            safeValue = `Rp ${numericValue.toLocaleString('id-ID')}`;
          } else {
            safeValue = value; // keep original if not numeric
          }
        }
        
        // Check if field has regulation
        const hasRegulation = checkFieldHasRegulation(fieldName);
        
        let content = `<span class="text-white">${safeValue}</span>`;
        if (hasRegulation && fieldName && safeValue !== "-") {
          content = `<span class="cursor-pointer hover:underline hover:text-yellow-300 regulation-field text-white border-b border-dashed border-gray-500 hover:border-yellow-300 transition-all duration-200" 
                           title="📋 Klik untuk melihat regulasi ${fieldName}" 
                           data-field="${fieldName}"
                           data-procedure-id="${procId}"
                           onclick="openRegulationDetailModal('${fieldName}', null, '${procId}')">${safeValue}</span>`;
        }
        
        return `<div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>${label}:</b></div>
                <div class="bg-gray-800 px-3 py-2 rounded text-white">${content}</div>`;
      };

      const content = `
        <div class="flex justify-between items-center mb-3">
          <h3 class="text-lg font-bold">Detail Tindakan: ${procedureName}</h3>
          <button type="button" onclick="closeNestedModal()"
                  class="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded">✕</button>
        </div>
        <div class="grid grid-cols-2 gap-2">
          ${renderProcBox("Kode ICD-9", d.icd9_code || d.icd9, "icd9_code")}
          ${renderProcBox("Deskripsi", d.icd9_desc || d.deskripsi, "deskripsi")}
          ${renderProcBox("Validitas", d.validitas, "validitas")}
          ${renderProcBox("Status", d.status_tindakan || d.status, "status")}
          ${renderProcBox("INA-CBG", d.ina_cbg_tarif || d.ina_cbg, "ina_cbg")}
          ${renderProcBox("Faskes", d.faskes, "faskes")}
          ${renderProcBox("Rawat Inap", d.rawat_inap, "rawat_inap")}
          ${renderProcBox("Syarat Klinis", d.syarat_klinis, "syarat_klinis")}
        </div>
      `;

      openModal(`Detail Tindakan: ${procedureName}`, content, { hideDefaultClose: true });

      // ✅ simpan reference supaya regulasi tahu asalnya
      window.claimState = window.claimState || {};
      window.claimState.currentProcedure = { id: procId };

      // update tampilan deskripsi list tindakan (instant)
      const itemEl = document.querySelector(`[data-procid='${procId}'] .text-xs`);
      const deskripsiGabungan = d.icd9_desc || d.deskripsi || procedureName;
      if (itemEl) itemEl.textContent = deskripsiGabungan;
    } catch (err) {
      console.error("Gagal load detail tindakan", err);
    }
  }

  function openManualDetailModal(it) {
    const dummy = {
      kategori: it.kategori || "Manual",
      klinis: it.klinis || "-",
      icd10: { kode_icd: it.icd10_code || "-", deskripsi: "-" },
      tindakan: it.procedure_text ? [{ procedure_text: it.procedure_text }] : [],
      validitas: "-",
      status: "-",
      ina_cbg: "-",
      faskes: "-",
      rawat_inap: "-",
      syarat_klinis: "-"
    };
    const title = `<div class="flex flex-col items-start items-center">
      <span class="text-lg font-bold">Detail Tindakan Manual</span>
      <span class="text-sm font-normal">${it.procedure_text || "-"}</span>
    </div>`;
    openModal(title, buildModalContent(dummy));
    window.claimState.currentProcedure = dummy;
    updateRingkasanFromRow(dummy);
  }

  function closeNestedModal() {
    const dx = window.claimState.currentDiagnosis;
    if (dx) {
      const nama = window.claimState.currentDiagnosisTitle || dx?.kategori || "-";
      openModal(`<div class="flex flex-col items-start items-center">
        <span class="text-lg font-bold">Detail Diagnosis</span>
        <span class="font-bold text-2xl mb-2 text-yellow-500">${nama}</span>
        </div>`, buildModalContent(dx), { hideDefaultClose: false });
    } else {
      const state = Alpine.$data(document.getElementById('claimRoot'));
      state.modalOpen = false;
    }
  }

  async function openRegulationModal(id, type = "diagnosis") {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    let url = `/claims/${claimId}/regulations?`;

    if (type === "diagnosis") url += `diagnosis_id=${id}`;
    else if (type === "procedure") url += `procedure_id=${id}`;
    else if (type === "diagnosis_eval") url += `diagnosis_evaluation_id=${id}`;
    else if (type === "procedure_eval") url += `procedure_evaluation_id=${id}`;

    // 🔹 Tambahin untuk i-DRG Diagnosis
    else if (type === "idrg_diagnosis") {
      url += `idrg_diagnosis_id=${id}`;
    }

    // 🔹 Tambahin untuk i-DRG Summary
    else if (type === "idrg_summary") {
      url += `idrg_summary_id=${id}`;
    }

    try {
      const res = await fetch(url);
      const json = await res.json();
      const { data } = json;

      if (!data || data.length === 0) {
        alert("Tidak ada regulasi untuk field ini");
        return;
      }

      // ✅ simpan source biar tau entry point
      window.claimState = window.claimState || {};
      window.claimState.regulationSource = { type, id };

      const isEval =
        type === "diagnosis_eval" ||
        type === "procedure_eval" ||
        type.startsWith("idrg_summary");   // ✅ hanya summary yang close langsung

      const isIdrgDiagnosis = type.startsWith("idrg_diagnosis"); // treat i-DRG juga seperti evaluasi

      let closeBtn = "";
      if (isEval) {
        // evaluasi & summary → pakai default close bawaan modal
        closeBtn = "";
      } else {
        // diagnosis/procedure/i-DRG diagnosis → render tombol merah manual
        closeBtn = `<div class="flex justify-end items-start mb-3">
                      <button type="button" onclick="closeRegulationModal()"
                              class="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded">✕</button>
                    </div>`;
      }

      const content = `
        <div class="space-y-4 text-sm">
          ${closeBtn}
          <div class="grid grid-cols-2 gap-y-2 text-sm">
            <div class="bg-gray-700 text-white font-semibold px-3 py-2 rounded-l">Dasar Hukum</div>
            <div class="bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2 rounded-r text-gray-800">${data[0].dasar_hukum}</div>

            <div class="bg-gray-700 text-white font-semibold px-3 py-2 rounded-l">Judul Regulasi</div>
            <div class="bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2 rounded-r text-gray-800">${data[0].judul_regulasi}</div>

            <div class="bg-gray-700 text-white font-semibold px-3 py-2 rounded-l">Pasal / Ayat / Bab</div>
            <div class="bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2 rounded-r italic text-gray-800">${data[0].bab_pasal}</div>

            <div class="bg-gray-700 text-white font-semibold px-3 py-2 rounded-l">Isi / Penjelasan</div>
            <div class="bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2 rounded-r text-gray-800">${data[0].isi}</div>
          </div>
        </div>
      `;

      openModal("Detail Regulasi", content, { hideDefaultClose: isEval ? false : true });
    } catch (e) {
      console.error("❌ Gagal load regulasi", e);
    }
  }



  // === Tutup Regulasi (Balik ke modal asal) ===
  function closeRegulationModal() {
    const source = window.claimState?.regulationSource;

    if (source?.type === "procedure" && window.claimState?.currentProcedure) {
      // Balik ke modal tindakan
      openProcedureModal(window.claimState.currentProcedure.id);

    } else if (source?.type?.startsWith("idrg_diagnosis") && window.claimState?.currentDiagnosis) {
      // Balik ke modal diagnosis
      closeNestedModal();

    } else if (source?.type?.startsWith("idrg_summary")) {
      // i-DRG Summary → langsung close modal (kayak evaluasi)
      const state = Alpine.$data(document.getElementById('claimRoot'));
      state.modalOpen = false;

    } else {
      // default → close diagnosis
      closeNestedModal();
    }
  }


  // Export
  window.openModal = openModal;
  window.openModalFromAttr = openModalFromAttr;
  window.buildModalContent = buildModalContent;
  window.renderDiagnosisDetail = renderDiagnosisDetail;
  window.renderIdrgSection = renderIdrgSection;
  window.renderTindakan = renderTindakan;
  window.openProcedureModal = openProcedureModal;
  window.openManualDetailModal = openManualDetailModal;
  window.closeNestedModal = closeNestedModal;
  window.openRegulationModal = openRegulationModal;
  window.closeRegulationModal = closeRegulationModal;

  // ================= Note Modal (Diagnosis / Tindakan) =================
window.openNoteModal = function(title, fieldKey) {
  const root = document.getElementById("claimRoot");
  const state = Alpine.$data(root);

  const existingLogs = (state.notes && state.notes[fieldKey]) ? state.notes[fieldKey] : [];
  const currentText = existingLogs.join("\n");

  state.modalTitle = title;
  state.modalContent = `
    <div class="space-y-4">
      <label class="block text-sm font-medium">Tambahkan Catatan:</label>
      <textarea id="noteField"
                class="w-full border rounded p-2 text-sm"
                rows="4"
                placeholder="Tulis catatan..."></textarea>

      <div class="flex justify-end gap-2">
        <button type="button"
                class="px-4 py-2 bg-gray-300 rounded"
                onclick="Alpine.$data(document.getElementById('claimRoot')).modalOpen=false">
          Close
        </button>
        <button type="button"
                class="px-4 py-2 bg-blue-600 text-white rounded"
                onclick="saveNote('${fieldKey}')">
          Save & Close
        </button>
      </div>

      <hr class="my-4">
      <h4 class="font-semibold text-sm">Riwayat Catatan:</h4>
      <pre class="bg-gray-100 p-2 rounded text-xs whitespace-pre-wrap">${currentText || 'Belum ada catatan.'}</pre>
    </div>
  `;
  state.modalOpen = true;
};

window.saveNote = function(fieldKey) {
  const root = document.getElementById("claimRoot");
  const state = Alpine.$data(root);

  const textarea = document.getElementById("noteField");
  const val = textarea.value.trim();
  if (!val) {
    state.modalOpen = false;
    return;
  }

  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  const role = state.role.charAt(0).toUpperCase() + state.role.slice(1);

  const log = `[${role} ${hh}:${mm}] ${val}`;

    if (!state.notes) state.notes = {};
    if (!state.notes[fieldKey]) state.notes[fieldKey] = [];

    state.notes[fieldKey].push(log);

    state.modalOpen = false;
  };

  // Function to open regulation detail modal
  window.openRegulationDetailModal = async function(fieldName, diagnosisId, procedureId = null) {
    console.log('Opening regulation modal for:', fieldName, 'diagnosisId:', diagnosisId, 'procedureId:', procedureId);
    
    // Get current claim ID from Alpine state
    const root = document.getElementById('claimRoot');
    const state = Alpine.$data(root);
    const claimId = state.selectedClaimId || state.id || 1; // fallback to 1 if not found
    
    try {
      // Build query parameters
      const params = new URLSearchParams({
        field_name: fieldName
      });
      
      if (diagnosisId) params.append('diagnosis_id', diagnosisId);
      if (procedureId) params.append('procedure_id', procedureId);
      
      const endpoint = `/claims/${claimId}/regulations?${params.toString()}`;
      console.log('Requesting regulation detail from:', endpoint);
      
      const response = await fetch(endpoint, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Regulation detail response:', data);
      
      if (data.error) {
        throw new Error(data.error);
      }
      
      // Render regulation detail modal
      const regulationContent = renderRegulationDetail(data, fieldName);
      openModal(`Regulasi: ${fieldName}`, regulationContent);
      
    } catch (error) {
      console.error('Error fetching regulation detail:', error);
      openModal('Error', `<p class="text-red-500">Gagal memuat detail regulasi: ${error.message}</p>`);
    }
  };

  function renderRegulationDetail(response, fieldName) {
    if (!response || response.status !== 'success' || !response.data || response.data.length === 0) {
      return `<div class="text-center py-8">
        <p class="text-gray-500">Tidak ada regulasi tersedia untuk field: ${fieldName}</p>
        <p class="text-xs text-gray-400 mt-2">Field ini tidak memerlukan regulasi atau belum dikonfigurasi</p>
      </div>`;
    }
    
    const regulationData = response.data[0]; // Get first regulation
    const { dasar_hukum, judul_regulasi, bab_pasal, isi } = regulationData;
    
    return `
      <div class="space-y-4 text-sm">
        <div class="bg-blue-50 dark:bg-blue-900 p-4 rounded">
          <h3 class="font-bold text-blue-800 dark:text-blue-200 mb-2">${judul_regulasi || 'Regulasi ' + fieldName}</h3>
          <div class="grid grid-cols-1 gap-2 text-xs">
            <div><strong>Dasar Hukum:</strong> ${dasar_hukum || '-'}</div>
            <div><strong>Bab/Pasal:</strong> ${bab_pasal || '-'}</div>
          </div>
        </div>
        
        <div class="bg-white dark:bg-gray-800 p-4 rounded border">
          <h4 class="font-semibold mb-2 text-gray-800 dark:text-gray-200">Isi Regulasi:</h4>
          <div class="text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">${isi || 'Detail regulasi sedang dimuat...'}</div>
        </div>
        
        <div class="text-xs text-gray-500 text-center">
          Field: <code class="bg-gray-100 dark:bg-gray-700 px-1 rounded">${fieldName}</code>
        </div>
      </div>
    `;
  }

})();