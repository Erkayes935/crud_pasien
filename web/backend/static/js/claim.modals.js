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
        const res = await fetch(`/claims/${claimId}/analyze_diagnosis`, {
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

  function renderNotificationBox(section, notifications = {}) {
    const colorMap = {
      success: "bg-green-100 border-green-500 text-green-800",
      warning: "bg-yellow-100 border-yellow-500 text-yellow-800",
      error: "bg-red-100 border-red-500 text-red-800",
      info: "bg-blue-100 border-blue-500 text-blue-800",
      default: "bg-gray-100 border-gray-400 text-gray-700"
    };

    const iconMap = {
      success: "✅",
      warning: "⚠️",
      error: "❌",
      info: "ℹ️",
      default: "🔔"
    };

    // Ambil notifikasi per section
    const note = notifications?.[section] || {};
    const status = note.status || "default";
    const msg = note.message || `Belum ada notifikasi untuk bagian ${section.toUpperCase()}.`;
    const cls = colorMap[status] || colorMap.default;
    const icon = iconMap[status] || iconMap.default;

    return `
      <div class="notification-box ${cls} border-l-4 p-2 rounded mb-2 text-sm flex items-start gap-2">
        <span class="text-lg">${icon}</span>
        <div>
          <strong>Notifikasi AI (${section.toUpperCase()})</strong>
          <div class="text-xs leading-snug mt-0.5">${msg}</div>
        </div>
      </div>
    `;
  }

  // 🔹 Fungsi render utama modal detail diagnosis
  function renderDiagnosisDetail(it) {
    console.log("📋 renderDiagnosisDetail received data:", it);

    // === 1️⃣ Parsing data dasar ===
    const diagnosisId = it.id || it.diagnosis_id || Date.now();
    const klinis = {
      justifikasi: it.klinis?.justifikasi || it.justifikasi || "-",
      bukti_klinis: it.klinis?.bukti_klinis || it.bukti_klinis || "-",
      syarat_klinis: it.klinis?.syarat_klinis || it.syarat_klinis || "-",
      status: it.klinis?.status || it.status || "default",
    };

    const icd10 = {
      kode_icd: it.icd10?.kode_icd || it.icd10_code || "-",
      struktur_icd10: it.icd10?.struktur_icd10 || it.struktur_icd10 || "-",
      kode_ganda: it.icd10?.kode_ganda || it.kode_ganda || "-",
      z_code: it.icd10?.z_code || it.z_code || "-",
      kode_bpjs_khusus: it.icd10?.kode_bpjs_khusus || it.kode_bpjs_khusus || "-",
      status_icd: it.icd10?.status_icd || it.status_icd || "default",
    };

    const tindakan = it.tindakan || [];
    const rawat = it.rawat || it.rawat_inap || {};
    const faskes = it.faskes || {};
    const rujukan = it.rujukan || {};
    const inaCbg = it.inaCbg || it.ina_cbg || {};
    const notifications = it.notifications || {}; // 🔔 notifikasi per section dari core_engine

    console.log("📋 Parsed notifications:", notifications);

    // === 2️⃣ Helper: render box per field ===
    const renderBox = (label, value, status = "default", diagnosisId = null, fieldName = null) => {
      let colorClass = "bg-gray-100 text-gray-800 dark:bg-gray-600 dark:text-gray-100";
      if (status === "valid") colorClass = "bg-green-600 text-white";
      if (status === "invalid") colorClass = "bg-red-600 text-white";

      const safeValue = value || "-";
      const hasRegulation = checkFieldHasRegulation(fieldName);

      let content = safeValue;
      if (hasRegulation && diagnosisId && safeValue !== "-") {
        content = `<span class="cursor-pointer hover:underline hover:text-blue-600 regulation-field border-b border-dashed border-gray-400 hover:border-blue-600 transition-all duration-200"
                        title="📋 Klik untuk melihat regulasi ${fieldName}"
                        data-field="${fieldName}"
                        data-diagnosis-id="${diagnosisId}"
                        onclick="openRegulationDetailModal('${fieldName}', ${diagnosisId})">${safeValue}</span>`;
      }

      return `
        <div class="grid grid-cols-2">
          <div class="bg-gray-700 text-white px-3 py-2">${label}</div>
          <div class="${colorClass} px-3 py-2">${content}</div>
        </div>
      `;
    };

    // === 3️⃣ Render keseluruhan modal ===
    return `
      <div class="space-y-6 text-sm">

        <!-- 🩺 KLINIS -->
        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">KLINIS</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderNotificationBox("klinis", notifications)}
            ${renderBox("Justifikasi", klinis.justifikasi, klinis.status, diagnosisId, "justifikasi")}
            ${renderBox("Bukti Klinis", klinis.bukti_klinis, null, null, "bukti_klinis")}
            ${renderBox("Syarat Klinis", klinis.syarat_klinis, klinis.status, diagnosisId, "syarat_klinis")}
          </div>
        </section>

        <!-- 🧾 ICD-10 -->
        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">ICD-10</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderNotificationBox("icd", notifications)}
            ${renderBox("Kode ICD", icd10.kode_icd, icd10.status_icd, diagnosisId, "kode_icd")}
            ${renderBox("Struktur ICD 10", icd10.struktur_icd10, icd10.status_icd, diagnosisId, "struktur_icd10")}
            ${renderBox("Kode Ganda", icd10.kode_ganda, icd10.status_icd, diagnosisId, "kode_ganda")}
            ${renderBox("Z-Code", icd10.z_code, icd10.status_icd, diagnosisId, "z_code")}
            ${renderBox("Kode Khusus BPJS", icd10.kode_bpjs_khusus, icd10.status_icd, diagnosisId, "kode_bpjs_khusus")}
          </div>
        </section>

        <!-- 📊 i-DRG -->
        ${renderNotificationBox("idrg", notifications)}
        ${renderIdrgSection(it.idrg_diagnosis)}

        <!-- ⚙️ TINDAKAN -->
        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">TINDAKAN</div>
          <div class="p-3 bg-gray-100 dark:bg-gray-700">
            ${renderNotificationBox("tindakan", notifications)}
            ${renderTindakan(tindakan)}
          </div>
        </section>

        <!-- 🏥 RAWAT INAP -->
        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">RAWAT INAP</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderNotificationBox("rawat", notifications)}
            ${renderBox("Indikasi", rawat.indikasi, rawat.status_indikasi, diagnosisId, "indikasi")}
            ${renderBox("Kriteria", rawat.kriteria, rawat.status_kriteria, diagnosisId, "kriteria")}
            ${renderBox("Lama Rawat", rawat.lama_rawat, rawat.status_lama, diagnosisId, "lama_rawat")}
          </div>
        </section>

        <!-- 🏢 FASKES -->
        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">FASKES</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderNotificationBox("faskes", notifications)}
            ${renderBox("Tingkat", faskes.tingkat, faskes.status_tingkat, diagnosisId, "tingkat")}
            ${renderBox("Justifikasi", faskes.justifikasi, faskes.status_justifikasi, diagnosisId, "justifikasi_faskes")}
            ${renderBox("Kompetensi", faskes.kompetensi, faskes.status_kompetensi, diagnosisId, "kompetensi")}
          </div>
        </section>

        <!-- 🔁 RUJUKAN -->
        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">RUJUKAN</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderNotificationBox("rujukan", notifications)}
            ${renderBox("Indikasi", rujukan.indikasi, rujukan.status_indikasi, diagnosisId, "indikasi_rujukan")}
            ${renderBox("Tujuan", rujukan.tujuan, rujukan.status_tujuan, diagnosisId, "tujuan")}
            ${renderBox("Kriteria", rujukan.kriteria, rujukan.status_kriteria, diagnosisId, "kriteria_rujukan")}
          </div>
        </section>

        <!-- 💰 INA-CBG -->
        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">INA-CBG</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderNotificationBox("inacbg", notifications)}
            ${renderBox("Kode INA-CBG", inaCbg.kode, inaCbg.status_kode, diagnosisId, "kode")}
            ${renderBox("Deskripsi", inaCbg.deskripsi, inaCbg.status_deskripsi, diagnosisId, "deskripsi")}
            ${renderBox("Tarif", inaCbg.tarif ? `Rp ${parseInt(inaCbg.tarif).toLocaleString('id-ID')}` : "-", inaCbg.status_tarif, diagnosisId, "tarif")}
          </div>
        </section>

      </div>
    `;
  }


  // Fungsi renderIdrgSection yang dioptimalkan (single dropdown)

  function renderIdrgSection(idrg, claimId, diagnosisName = null) {
    // Get claim ID dan diagnosis name dari context jika tidak ada parameter
    if (!claimId) {
        claimId = document.getElementById("claimRoot")?.dataset.claimId || 
                 window.claimState?.currentClaimId || 
                 document.querySelector('[data-claim-id]')?.dataset.claimId;
    }
    
    if (!diagnosisName) {
        diagnosisName = window.claimState?.currentDiagnosisTitle || 
                       document.querySelector('.modal-title')?.textContent?.trim();
    }

    // Helper function untuk render rows
    const renderPredictionRow = (label, value) => `
      <div class="grid grid-cols-2">
        <div class="bg-blue-600 text-white px-3 py-2 font-medium">${label}</div>
        <div class="bg-blue-100 dark:bg-blue-800 px-3 py-2 text-gray-900 dark:text-gray-100">${value || "-"}</div>
      </div>
    `;

    const renderExistingRow = (label, value, field) => {
      const isClickable = field && value !== "-";
      return `
        <div class="grid grid-cols-2">
          <div class="bg-gray-700 text-white px-3 py-2">${label}</div>
          <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2 ${isClickable ? 'cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-800 transition-colors' : ''}"
               ${isClickable ? `onclick="openRegulationModal('${claimId}', '${field}')"` : ''}>
            ${value || "-"}
          </div>
        </div>
      `;
    };

    // TEMPLATE BARU - LANGSUNG TANPA NESTED
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
            } catch (err) {
              this.error = err.message;
              console.error('Prediction error:', err);
            } finally {
              this.loading = false;
            }
          }
        }
      }">
        
        <!-- HEADER UTAMA i-DRG (KLIK DROPDOWN INI LANGSUNG PREDIKSI) -->
        <div class="flex items-center justify-between bg-blue-600 text-white px-3 py-2 font-bold cursor-pointer"
            @click="toggleAndPredict()">
          <span>i-DRG</span>
          <span class="flex items-center">
            <span x-show="loading" class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
            <span x-text="open ? '▼' : '▶'"></span>
          </span>
        </div>
        
        <!-- CONTENT AREA (LANGSUNG HASIL) -->
        <div x-show="open" x-transition>
          
          <!-- Loading State -->
          <div x-show="loading" class="p-4 text-center">
            <div class="inline-flex items-center">
              <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mr-3"></div>
              <span class="text-blue-600 font-medium">Menganalisis dengan OpenAI...</span>
            </div>
          </div>
          
          <!-- Prediction Results -->
          <div x-show="!loading && data && data.status === 'success'">
            <template x-if="data.data && data.data.idrg_prediction">
              <div class="space-y-2 p-4">
                ${renderPredictionRow("Kode i-DRG", "<span x-text='data.data.idrg_prediction.group_idrg || \"-\"'></span>")}
                ${renderPredictionRow("Severity Index", "<span x-text='getSeverityLabel(data.data.idrg_prediction.severity_index) || \"-\"'></span>")}
                ${renderPredictionRow("Checklist Dokumentasi", "<span x-html='renderChecklistHtml(data.data.idrg_prediction.checklist_dokumentasi)'></span>")}
                ${renderPredictionRow("Faktor Penentu Severity", "<span x-html='renderFaktorSeverityHtml(data.data.idrg_prediction.faktor_penentu_severity)'></span>")}
                ${renderPredictionRow("Ungroupable Alert", "<span x-text='data.data.idrg_prediction.ungroupable_alert || \"-\"'></span>")}
                ${renderPredictionRow("Estimasi Tarif", "<span x-text=\"data.data.idrg_prediction.estimasi_tarif_idrg ? 'Rp ' + parseInt(data.data.idrg_prediction.estimasi_tarif_idrg).toLocaleString('id-ID') : '-'\"></span>")}
                ${renderPredictionRow("Gap Analysis", "<span x-text='data.data.idrg_prediction.gap_analysis || \"-\"'></span>")}
                
                <div class="text-xs text-blue-600 dark:text-blue-300 mt-3 p-2 bg-white dark:bg-gray-800 rounded">
                  <strong>Engine:</strong> <span x-text="data.data.engine_version || 'OpenAI GPT-4'"></span> • 
                  <strong>Mode:</strong> Single Diagnosis • 
                  <strong>Generated:</strong> ${new Date().toLocaleString()}
                </div>
              </div>
            </template>
          </div>
          
          <!-- Error State -->
          <div x-show="!loading && error" class="p-4 bg-red-50 border border-red-200 rounded m-4">
            <div class="flex items-center text-red-700">
              <span class="text-xl mr-3">❌</span>
              <span class="font-semibold">Error Prediksi i-DRG:</span>
            </div>
            <div class="mt-2 text-sm text-red-600" x-text="error"></div>
            <button @click="loading = true; error = null; predictIdrgForDiagnosis('${claimId}', '${diagnosisName}').then(result => { data = result; loading = false; }).catch(err => { error = err.message; loading = false; })" 
                    class="mt-3 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm">
              🔄 Coba Lagi
            </button>
          </div>
          
          <!-- Saved Data Section, jika ada -->
          ${idrg ? `
          <div class="p-4 space-y-2 border-t" x-show="!loading">
            <h3 class="font-bold text-gray-800 dark:text-gray-200 mb-2">Data i-DRG Tersimpan</h3>
            
            ${renderExistingRow("Group i-DRG", idrg.group_idrg || "-", "idrg_diagnosis_group")}
            ${renderExistingRow("Severity Index", idrg.severity_index || "-", "idrg_diagnosis_severity")}
            ${renderExistingRow("Checklist Dokumentasi", idrg.checklist || "-", "idrg_diagnosis_checklist")}
            ${renderExistingRow("Faktor Severity", idrg.faktor_severity || "-")}
            ${renderExistingRow("Ungroupable Alert", idrg.ungroupable_alert || "-", "idrg_diagnosis_ungroupable")}
            ${renderExistingRow("Simulasi Tarif", idrg.simulasi_tarif || "-")}
            ${renderExistingRow("Gap Analysis", idrg.gap_analysis || "-")}
          </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  // Update renderIdrgPredictionResult untuk tampil lebih simple

  window.renderIdrgPredictionResult = function(data) {
    if (!data || !data.idrg_prediction) {
      return `<div class="p-4 text-red-500">Data prediksi i-DRG tidak lengkap</div>`;
    }
    
    const prediction = data.idrg_prediction;
    
    const renderPredictionRow = (label, value, isClickable = false) => {
      const content = isClickable ? 
        `<span class="cursor-pointer hover:underline hover:text-blue-600">${value}</span>` :
        value;
        
      return `
        <div class="grid grid-cols-2">
          <div class="bg-blue-700 text-white px-3 py-2 font-medium">${label}</div>
          <div class="bg-blue-100 dark:bg-blue-800 px-3 py-2 text-gray-900 dark:text-gray-100">${content || "-"}</div>
        </div>
      `;
    };
    
    // Render checklist dokumentasi sebagai list jika array
    let checklistHtml = "-";
    if (prediction.checklist_dokumentasi && Array.isArray(prediction.checklist_dokumentasi) && 
        prediction.checklist_dokumentasi.length > 0) {
      checklistHtml = prediction.checklist_dokumentasi.map(item => `<li>• ${item}</li>`).join('');
      checklistHtml = `<ul class="list-none pl-0">${checklistHtml}</ul>`;
    } else if (prediction.checklist_dokumentasi) {
      checklistHtml = prediction.checklist_dokumentasi;
    }
    
    // Render faktor severity sebagai list jika array
    let faktorSeverityHtml = "-";
    if (prediction.faktor_penentu_severity && Array.isArray(prediction.faktor_penentu_severity) && 
        prediction.faktor_penentu_severity.length > 0) {
      faktorSeverityHtml = prediction.faktor_penentu_severity.map(item => `<li>• ${item}</li>`).join('');
      faktorSeverityHtml = `<ul class="list-none pl-0">${faktorSeverityHtml}</ul>`;
    } else if (prediction.faktor_penentu_severity) {
      faktorSeverityHtml = prediction.faktor_penentu_severity;
    }
    
    // Map severity index ke label
    const severityLabel = {
      "1": "Minor (1)",
      "2": "Moderate (2)",
      "3": "Major (3)",
      "4": "Extreme (4)"
    };
    
    // Field yang tepat sesuai idrg_service.py
    return `
      <div class="space-y-2 px-4">      
        ${renderPredictionRow("Kode i-DRG", prediction.group_idrg || "-", true)}
        ${renderPredictionRow("Severity Index", severityLabel[prediction.severity_index] || prediction.severity_index || "-", true)}
        ${renderPredictionRow("Checklist Dokumentasi", checklistHtml)}
        ${renderPredictionRow("Faktor Penentu Severity", faktorSeverityHtml)}
        ${renderPredictionRow("Ungroupable Alert", prediction.ungroupable_alert || "-")}
        ${renderPredictionRow("Estimasi Tarif", prediction.estimasi_tarif_idrg ? `Rp ${parseInt(prediction.estimasi_tarif_idrg).toLocaleString('id-ID')}` : "-")}
        ${renderPredictionRow("Gap Analysis", prediction.gap_analysis !== undefined ? `${prediction.gap_analysis}` : "-")}
        
        <div class="text-xs text-blue-600 dark:text-blue-300 mt-3 p-2 bg-white dark:bg-gray-800 rounded">
          <strong>Engine:</strong> ${data.engine_version || 'OpenAI GPT-4'} • 
          <strong>Mode:</strong> Single Diagnosis • 
          <strong>Diagnosis:</strong> ${data.diagnosis} •
          <strong>Generated:</strong> ${new Date().toLocaleString()}
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

  // Ambil nama tindakan dari DOM jika belum dikirim
  if (!procedureName) {
    const procElement = document.querySelector(`[data-procid="${procId}"] .cursor-pointer`);
    procedureName = procElement?.textContent?.trim() || "Unknown Procedure";
  }

  console.log("🔥 openProcedureModal called", { procId, procedureName, claimId });

  try {
    // 🔥 Request ke core_engine /analyze_procedure
    console.log("[REQ] POST /analyze_procedure", { claim_id: claimId, procedure_name: procedureName });
    const res = await fetch(`/claims/${claimId}/analyze_procedure`, {
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
    const d = result.data || result;

    // 🔔 Ambil notifikasi dari core_engine (atau fallback dummy)
    const notifications = d.notifications || {
      tindakan: { status: "info", message: "Analisis AI: tindakan ini memerlukan verifikasi tambahan." }
    };

    console.log("📋 Notifications (procedure):", notifications);

    const renderProcBox = (label, value, fieldName = null) => {
      let safeValue = value || "-";
      if (fieldName === "ina_cbg" && value && value !== "-") {
        const numericValue = parseInt(value);
        safeValue = !isNaN(numericValue)
          ? `Rp ${numericValue.toLocaleString('id-ID')}`
          : value;
      }

      const hasRegulation = checkFieldHasRegulation(fieldName);
      let content = `<span class="text-white">${safeValue}</span>`;
      if (hasRegulation && fieldName && safeValue !== "-") {
        content = `<span class="cursor-pointer hover:underline hover:text-yellow-300 regulation-field text-white border-b border-dashed border-gray-500 hover:border-yellow-300 transition-all duration-200"
                         title="📋 Klik untuk melihat regulasi ${fieldName}"
                         data-field="${fieldName}"
                         data-procedure-id="${procId}"
                         onclick="openRegulationDetailModal('${fieldName}', null, '${procId}')">${safeValue}</span>`;
      }

      return `
        <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>${label}:</b></div>
        <div class="bg-gray-800 px-3 py-2 rounded text-white">${content}</div>
      `;
    };

    // 🔹 Tambahkan notifikasi di atas semua detail tindakan
    const content = `
      <div class="flex justify-between items-center mb-3">
        <h3 class="text-lg font-bold">Detail Tindakan: ${procedureName}</h3>
        <button type="button" onclick="closeNestedModal()"
                class="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded">✕</button>
      </div>

      ${renderNotificationBox("tindakan", notifications)}

      <div class="grid grid-cols-2 gap-2 mt-3">
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

    // Simpan referensi supaya regulasi tahu asalnya
    window.claimState = window.claimState || {};
    window.claimState.currentProcedure = { id: procId };

    // Update deskripsi list tindakan (instan)
    const itemEl = document.querySelector(`[data-procid='${procId}'] .text-xs`);
    const deskripsiGabungan = d.icd9_desc || d.deskripsi || procedureName;
    if (itemEl) itemEl.textContent = deskripsiGabungan;
  } catch (err) {
    console.error("❌ Gagal load detail tindakan:", err);
    openModal("Error", `<div class='p-4 text-red-500'>Gagal memuat detail tindakan.<br>${err.message}</div>`);
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
    let url = `/claims/${claimId}/regulation_detail`;

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
// ✅ ID stabil tanpa hash (supaya sama setiap reload)
  // ================= SISTEM NOTES YANG DIPERBAIKI =================
  
// ======================== SISTEM NOTES FINAL STABIL ========================

// ✅ ID stabil tanpa hash (supaya sama setiap reload)
function getStableItemId(claimId, stage, fieldKey, itemName = "") {
  const key = fieldKey.toLowerCase();
  if (key === "primary_diagnosis" || key === "primary_action") return 1;
  if (key === "secondary_diagnosis" || key === "secondary_action") return 2;
  return 9999; // fallback umum
}

// ✅ Buka modal catatan (dengan context lengkap)
window.openNoteModal = async function(title, fieldKey, item = null) {
  const root = document.getElementById("claimRoot");
  let state = null;
  try {
    state = Alpine.$data(root);
  } catch (e) {
    console.warn("⚠️ fallback ke window.claimState karena Alpine belum aktif");
    state = window.claimState || {};
  }

  const claimId = root.dataset.claimId;
  const currentStage = state.tab || window.claimState?.tab || "admission";

  // Simpan context
  state.currentNoteItem = item;
  state.currentNoteField = fieldKey;
  state.currentNoteStage = currentStage;

  // Tentukan itemId (stabil)
  const itemName = item?.name || "primary";
  const itemId = item?.id || getStableItemId(claimId, currentStage, fieldKey, itemName);

  console.log("📝 openNoteModal context:", { stage: currentStage, fieldKey, itemId, itemName });

  // Ambil notes dari backend
  let notes = [];
  try {
    const url = `/claims/${claimId}/notes?stage=${currentStage}&field_key=${fieldKey}&item_id=${itemId}`;
    console.log("🔍 Fetching notes from:", url);
    const res = await fetch(url);
    const json = await res.json();

    if (res.ok) {
      // Tambahkan fallback ID lama agar note lama tetap terbaca
      const oldIds = [804880226, 2184760293, 32548051, 1, 2];
      notes = (json.data || []).filter(n =>
        n.stage === currentStage &&
        n.field_key === fieldKey &&
        (String(n.item_id) === String(itemId) || oldIds.includes(Number(n.item_id)))
      );

      console.log("🧩 Filter debug", {
        currentStage,
        fieldKey,
        itemId,
        totalBefore: (json.data || []).length,
        totalAfter: notes.length,
        exampleMatch: notes.slice(0, 2).map(n => n.item_id)
      });
    }
  } catch (err) {
    console.error("❌ Gagal fetch notes:", err);
  }

  // Render riwayat catatan
  const existingLogs = notes.map(n => {
    const utcString = n.timestamp?.endsWith("Z") ? n.timestamp : n.timestamp + "Z";
    const time = new Date(utcString).toLocaleString("id-ID", {
      timeZone: "Asia/Jakarta",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit"
    });
    return `[${n.role} ${time} WIB] ${n.note_text}`;
  });

  const currentText = existingLogs.join("\n");

  state.modalTitle = `${title} - ${currentStage.toUpperCase()}`;
  state.modalContent = `
    <div class="space-y-4">
      <label class="block text-sm font-medium">Tambahkan Catatan:</label>
      <textarea id="noteField"
                class="w-full border rounded p-2 text-sm bg-white text-gray-800
                      focus:outline-none focus:ring-2 focus:ring-blue-400
                      dark:bg-gray-100 dark:text-gray-900"
                rows="4"
                placeholder="Tulis catatan..."></textarea>

      <div class="flex justify-end gap-2">
        <button type="button"
                class="px-4 py-2 bg-gray-300 dark:bg-gray-700 dark:text-gray-200 rounded"
                onclick="Alpine.$data(document.getElementById('claimRoot')).modalOpen=false">
          Close
        </button>
        <button type="button"
                class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                onclick="saveNote('${fieldKey}', '${currentStage}', ${itemId})">
          Save & Close
        </button>
      </div>

      <hr class="my-4 border-gray-300 dark:border-gray-700">
      <h4 class="font-semibold text-sm">Riwayat Catatan (${notes.length}):</h4>
      <pre class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs whitespace-pre-wrap max-h-60 overflow-y-auto text-gray-800 dark:text-gray-100">
        ${currentText || 'Belum ada catatan.'}
      </pre>
    </div>
  `;


  state.modalOpen = true;
  console.log("✅ openNoteModal - loaded notes:", notes.length);
};


// ✅ Simpan note baru (frontend + backend sync)
window.saveNote = async function(fieldKey, stage, itemId) {
  const root = document.getElementById("claimRoot");
  const state = Alpine.$data(root);
  const textarea = document.getElementById("noteField");
  const val = textarea.value.trim();

  if (!val) {
    state.modalOpen = false;
    return;
  }

  const claimId = root.dataset.claimId;

  console.log("💾 saveNote FINAL:", { fieldKey, itemId, stage, valueToSend: val });

  try {
    const headers = { "Content-Type": "application/json" };
    if (window.csrfToken) headers["X-CSRF-Token"] = window.csrfToken;

    const resp = await fetch(`/claims/${claimId}/notes`, {
      method: "POST",
      headers,
      credentials: "include",
      body: JSON.stringify({
        item_id: itemId,
        note_text: val,
        parent_id: null,
        field_key: fieldKey,
        stage: stage
      })
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    // Tambahkan ke local state (agar langsung muncul tanpa reload)
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    const role = state.role ? state.role : "User";
    const log = `[${role} ${hh}:${mm}] ${val}`;

    if (!state.notes) state.notes = {};
    if (!state.notes[stage]) state.notes[stage] = {};
    if (!state.notes[stage][fieldKey]) state.notes[stage][fieldKey] = {};
    if (!state.notes[stage][fieldKey][itemId]) state.notes[stage][fieldKey][itemId] = [];
    state.notes[stage][fieldKey][itemId].push(log);

    console.log("✅ Note saved successfully", {
      stage,
      fieldKey,
      itemId,
      totalNotes: state.notes[stage][fieldKey][itemId].length
    });
  } catch (e) {
    console.error("❌ saveNote error:", e);
    alert("Gagal menyimpan catatan: " + e.message);
  }

  state.modalOpen = false;
};


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
// ======================== SISTEM NOTES FINAL STABIL (MERGED FOR VERSION B) ========================

  // Function to open regulation detail modal
  window.openRegulationDetailModal = async function(fieldName, diagnosisId, procedureId = null) {
    console.log('Opening regulation modal for:', fieldName, 'diagnosisId:', diagnosisId, 'procedureId:', procedureId);
    
    // Get current claim ID from Alpine state
    const root = document.getElementById('claimRoot');
    const state = Alpine.$data(root);
    const claimId = state.selectedClaimId || state.id || 1; // fallback to 1 if not found
    
    try {
      // Buat payload untuk POST request
      const payload = {
        claim_id: claimId,
        field: fieldName
      };
      
      // Tambahkan diagnosisId atau procedureId jika ada
      if (diagnosisId) payload.item_id = diagnosisId;
      if (procedureId) payload.item_id = procedureId;
      
      const endpoint = `/claims/${claimId}/regulation_detail`;
      console.log('Requesting regulation detail from:', endpoint, 'with payload:', payload);
      
      // Ubah dari GET ke POST dan kirim payload
      const response = await fetch(endpoint, {
        method: 'POST', // Ubah dari GET ke POST
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload) // Tambahkan payload sebagai body
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

// ==================================================
// i-DRG PREDICTION
// ==================================================

// Function untuk prediksi i-DRG individual diagnosis
window.predictIdrgForDiagnosis = async function(claimId, diagnosisName) {
  console.log("🤖 Predicting i-DRG for diagnosis:", diagnosisName);
  
  try {
    // Get current diagnosis data from window state
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
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log("[RESP] /predict_idrg", result);
    
    if (result.error) {
      throw new Error(result.error);
    }
    
    return {
      status: 'success',
      data: result
    };
    
  } catch (error) {
    console.error("❌ Error predicting i-DRG:", error);
    throw error;
  }
};

// Tambahkan fungsi helper untuk render format array dan severity label

// Fungsi untuk convert severity index ke label
window.getSeverityLabel = function(index) {
  const severityLabel = {
    "1": "Minor (1)",
    "2": "Moderate (2)",
    "3": "Major (3)",
    "4": "Extreme (4)"
  };
  return severityLabel[index] || index;
};

// Fungsi untuk render checklist dokumentasi
window.renderChecklistHtml = function(checklist) {
  if (!checklist) return '-';
  
  if (Array.isArray(checklist) && checklist.length > 0) {
    return `<ul class="list-none pl-0">${checklist.map(item => `<li>• ${item}</li>`).join('')}</ul>`;
  } else if (typeof checklist === 'string') {
    return checklist;
  }
  
  return '-';
};

// Fungsi untuk render faktor severity
window.renderFaktorSeverityHtml = function(faktor) {
  if (!faktor) return '-';
  
  if (Array.isArray(faktor) && faktor.length > 0) {
    return `<ul class="list-none pl-0">${faktor.map(item => `<li>• ${item}</li>`).join('')}</ul>`;
  } else if (typeof faktor === 'string') {
    return faktor;
  }
  
  return '-';
};

// Function untuk render hasil prediksi i-DRG
window.renderIdrgPredictionResult = function(data) {
  if (!data || !data.idrg_prediction) {
    return `<div class="p-4 text-red-500">Data prediksi i-DRG tidak lengkap</div>`;
  }
  
  const prediction = data.idrg_prediction;
  
  const renderPredictionRow = (label, value, isClickable = false) => {
    const content = isClickable ? 
      `<span class="cursor-pointer hover:underline hover:text-blue-600">${value}</span>` :
      value;
      
    return `
      <div class="grid grid-cols-2">
        <div class="bg-blue-700 text-white px-3 py-2 font-medium">${label}</div>
        <div class="bg-blue-100 dark:bg-blue-800 px-3 py-2 text-gray-900 dark:text-gray-100">${content || "-"}</div>
      </div>
    `;
  };
  
  // Render checklist dokumentasi sebagai list jika array
  let checklistHtml = "-";
  if (prediction.checklist_dokumentasi && Array.isArray(prediction.checklist_dokumentasi) && 
      prediction.checklist_dokumentasi.length > 0) {
    checklistHtml = prediction.checklist_dokumentasi.map(item => `<li>• ${item}</li>`).join('');
    checklistHtml = `<ul class="list-none pl-0">${checklistHtml}</ul>`;
  } else if (prediction.checklist_dokumentasi) {
    checklistHtml = prediction.checklist_dokumentasi;
  }
  
  // Render faktor severity sebagai list jika array
  let faktorSeverityHtml = "-";
  if (prediction.faktor_penentu_severity && Array.isArray(prediction.faktor_penentu_severity) && 
      prediction.faktor_penentu_severity.length > 0) {
    faktorSeverityHtml = prediction.faktor_penentu_severity.map(item => `<li>• ${item}</li>`).join('');
    faktorSeverityHtml = `<ul class="list-none pl-0">${faktorSeverityHtml}</ul>`;
  } else if (prediction.faktor_penentu_severity) {
    faktorSeverityHtml = prediction.faktor_penentu_severity;
  }
  
  // Map severity index ke label
  const severityLabel = {
    "1": "Minor (1)",
    "2": "Moderate (2)",
    "3": "Major (3)",
    "4": "Extreme (4)"
  };
  
  // Field yang tepat sesuai idrg_service.py
  return `
    <div class="space-y-2 px-4">      
      ${renderPredictionRow("Kode i-DRG", prediction.group_idrg || "-", true)}
      ${renderPredictionRow("Severity Index", severityLabel[prediction.severity_index] || prediction.severity_index || "-", true)}
      ${renderPredictionRow("Checklist Dokumentasi", checklistHtml)}
      ${renderPredictionRow("Faktor Penentu Severity", faktorSeverityHtml)}
      ${renderPredictionRow("Ungroupable Alert", prediction.ungroupable_alert || "-")}
      ${renderPredictionRow("Estimasi Tarif", prediction.estimasi_tarif_idrg ? `Rp ${parseInt(prediction.estimasi_tarif_idrg).toLocaleString('id-ID')}` : "-")}
      ${renderPredictionRow("Gap Analysis", prediction.gap_analysis !== undefined ? `${prediction.gap_analysis}` : "-")}
      
      <div class="text-xs text-blue-600 dark:text-blue-300 mt-3 p-2 bg-white dark:bg-gray-800 rounded">
        <strong>Engine:</strong> ${data.engine_version || 'OpenAI GPT-4'} • 
        <strong>Mode:</strong> Single Diagnosis • 
        <strong>Diagnosis:</strong> ${data.diagnosis} •
        <strong>Generated:</strong> ${new Date().toLocaleString()}
      </div>
    </div>
  `;
};

// Function untuk refresh prediksi i-DRG
window.refreshIdrgPrediction = async function(claimId, diagnosisName) {
  try {
    const result = await predictIdrgForDiagnosis(claimId, diagnosisName);
    
    // Update section i-DRG di modal yang sedang terbuka
    const idrgSection = document.querySelector('[x-data*="open: false, loading: false, data: null"]');
    if (idrgSection) {
      // Trigger Alpine.js untuk update data
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
};

// Tambahkan fungsi tindakanAutocomplete

function tindakanAutocomplete() {
  return {
    query: "",
    results: [],
    async search() {
      if (!this.query) { this.results = []; return; }
      try {
        if (window.searchTindakan) {
          const res = await window.searchTindakan(this.query);
          this.results = res.data || [];
        } else {
          console.warn("searchTindakan function not available");
          this.results = [];
        }
      } catch (err) {
        console.error("Error searching tindakan:", err);
        this.results = [];
      }
    },
    async select(item) {
      this.query = item.procedure_text;
      this.results = [];
      if (window.addManualTindakanFromAutocomplete) {
        await window.addManualTindakanFromAutocomplete(window.claimState?.tab || 'admission', item);
      }
    }
  }
}

// Expose the function
window.tindakanAutocomplete = tindakanAutocomplete;

// Add statusIcon function if not exists
if (!window.statusIcon) {
  window.statusIcon = function(status) {
    if (!status) return '⚫';
    const s = String(status).toLowerCase();
    
    if (s.includes('valid') || s.includes('normal') || s.includes('yes') || s.includes('ya')) {
      return '🟢';
    }
    
    if (s.includes('invalid') || s.includes('warning') || s.includes('no') || s.includes('tidak')) {
      return '🔴';
    }
    
    if (s.includes('caution') || s.includes('bersyarat') || s.includes('partial')) {
      return '🟠';
    }
    
    return '⚫';
  };
}

// Add handleAddManualTindakan function if missing
if (!window.handleAddManualTindakan) {
  window.handleAddManualTindakan = function(tab) {
    const input = document.getElementById('manualNamaTindakan');
    const value = input?.value?.trim();
    
    if (!value) {
      alert("Nama tindakan tidak boleh kosong");
      return;
    }
    
    if (window.addManualTindakan) {
      window.addManualTindakan(tab, value);
    } else {
      console.warn("addManualTindakan function not available");
    }
    
    if (input) input.value = '';
  };
}