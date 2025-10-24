// =============== Semua modal (diagnosis/procedure/regulasi) ===============

(function () {
  // Pastikan fungsi feedback modal tersedia di global scope
  window.showFeedbackModalForRegulasi = function(ruleId, layer) {
    if (window.showFeedbackModal) window.showFeedbackModal({id: ruleId, layer_name: layer});
  };
  // Helper function untuk truncate text
  function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + "...";
  }

  // Fungsi label dan warna layer regulasi (global scope agar bisa dipanggil di template literal)
  function getLayerLabel(layer) {
    const labels = {
      'permenkes': '🏛️ Permenkes',
      'nasional': '🇮🇩 Nasional',
      'ppk': '🏥 PPK RS',
      'regional': '🗺️ Regional',
      'rs': '🏨 RS Lokal',
      'bridging': '🔗 Bridging',
      'fraud': '⚠️ Fraud',
      'temporary': '⏰ Temporary'
    };
    return labels[layer] || layer.toUpperCase();
  }
  function getLayerColorClass(layer) {
    const colors = {
      'ppk': 'bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-200',
      'rs': 'bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-200',
      'nasional': 'bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-200',
      'regional': 'bg-purple-100 text-purple-800 dark:bg-purple-800 dark:text-purple-200',
      'permenkes': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-800 dark:text-indigo-200'
    };
    return colors[layer] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
  }
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

  // global flag untuk cegah duplikasi modal (restore regulasi)
  window.__suppressModalStack = false;

  function openModal(title, content, options = {}) {
    // pastikan claimState tersedia
    window.claimState = window.claimState || {};
    // 🧹 Prevent modal duplication (gepeng / dua tampilan)
    const existingContents = document.querySelectorAll("#modalContainer .modal-content");
    if (existingContents.length > 0) {
      existingContents.forEach(el => el.remove());
      console.log("♻️ [CLEANUP] Old modal-content removed before opening new one");
    }
    window.claimState.modalStack = window.claimState.modalStack || [];

    // pastikan elemen dasar modal tersedia
    let modalContainer = document.getElementById("modalContainer");
    let modalContent = document.querySelector(".modal-content");
    let modalTitle = document.querySelector(".modal-title");

    if (!modalContainer) {
      modalContainer = document.createElement("div");
      modalContainer.id = "modalContainer";
      modalContainer.className =
        "fixed inset-0 bg-black/40 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 hidden";
      document.body.appendChild(modalContainer);
    }

    if (!modalContent) {
      modalContent = document.createElement("div");
      modalContent.className =
        "modal-content relative bg-gray-50 dark:bg-slate-800 text-slate-900 dark:text-white p-6 rounded-2xl max-h-[90vh] overflow-y-auto shadow-2xl w-[90%] max-w-4xl border border-slate-200 dark:border-slate-700";
      modalContainer.appendChild(modalContent);
    }

    if (!modalTitle) {
      modalTitle = document.createElement("div");
      modalTitle.className =
        "modal-title mb-4 text-center text-xl font-bold text-slate-800 dark:text-white";
      modalContent.prepend(modalTitle);
    }

    // simpan modal lama ke stack (restore system)
    // 🚫 tapi jangan push kalau sedang restore dari overlay regulasi
    if (!window.__suppressModalStack) {
      const oldTitle = modalTitle.innerHTML?.trim();
      const oldHTML = modalContent.innerHTML?.trim();
      if (oldHTML && oldTitle) {
        window.claimState.modalStack.push({ title: oldTitle, content: oldHTML });
        if (window.claimState.modalStack.length > 10)
          window.claimState.modalStack.shift();
      }
    }


    // Log that we're opening the modal
    console.log("🔍 Opening modal with title:", title);
    console.log("🔍 Modal content length:", content?.length || 0);

    // Clear existing content first
    modalContent.innerHTML = "";
    
    // tampilkan modal container
    modalContainer.classList.remove("hidden");
    modalContainer.classList.add("flex");

    // default close button
    const closeButton = options.hideDefaultClose
      ? ""
      : `<button type="button"
                  class="absolute top-3 right-4 text-white bg-red-500 hover:bg-red-600 px-4 py-2 rounded-lg shadow-md hover:shadow-lg transition-all transform hover:-translate-y-0.5"
                  onclick="closeNestedModal()">✕</button>`;

    // render title hanya jika disableAutoTitle = false
    if (!options.disableAutoTitle) {
      modalTitle.innerHTML = `
        <div class="relative w-full bg-blue-600/90 dark:bg-blue-700 text-white rounded-t-xl py-2">
          <h2 class="text-xl font-bold text-center">${title || "(Untitled Modal)"}</h2>
          ${closeButton}
        </div>
      `;
    }

    // isi konten utama — kalau disableAutoTitle true, langsung pakai content-nya aja
    modalContent.innerHTML = options.disableAutoTitle
      ? (content || "<p>Tidak ada konten.</p>")
      : `
        ${modalTitle.outerHTML}
        <div class="modal-body pt-3">${content || "<p>Tidak ada konten.</p>"}</div>
      `;

    // animasi fade-in
    modalContent.classList.add("modal-fade-enter");
    setTimeout(() => {
      modalContent.classList.add("modal-fade-enter-active");
      modalContent.classList.remove("modal-fade-enter");
    }, 10);

    window.claimState.modalOpen = true;

    // Add the following to debug modal visibility
    console.log("🔍 Modal container display:", getComputedStyle(modalContainer).display);
    
    // Initialize Alpine and attach event handlers
    setTimeout(() => {
      Alpine.initTree(modalContent);
      
      // Attach event handlers to regulation fields
      document.querySelectorAll('.regulation-field').forEach(el => {
        el.addEventListener('click', function() {
          const field = this.getAttribute('data-field');
          const diagnosisId = this.getAttribute('data-diagnosis-id');
          const procedureId = this.getAttribute('data-procedure-id');
          
          console.log("🔍 Regulation field clicked:", field, diagnosisId, procedureId);
          window.openRegulationDetailModal(field, diagnosisId, procedureId);
        });
      });
      
      console.log("🔍 Event handlers attached to regulation fields");
    }, 50);

    // ✅ Auto-reset flag setelah modal sukses terbuka (hindari duplikasi restore)
    if (window.__suppressModalStack) {
      console.log("🔧 Reset suppress flag setelah modal dibuka");
      window.__suppressModalStack = false;
    }
  }

  // ======================================================
  // 🔹 AI Loading Modal Handler (non-global)
  // ======================================================

  function showAiLoadingModal(steps = ["Mengambil data...", "Menganalisis hasil...", "Menyiapkan tampilan..."]) {
    const modal = document.getElementById("aiLoadingModal");
    const container = document.getElementById("aiLoadingMessages");
    if (!modal || !container) return;

    modal.classList.remove("hidden");
    container.innerHTML = "";
    let i = 0;
    (function loop() {
      if (i < steps.length) {
        const p = document.createElement("p");
        p.textContent = steps[i];
        container.appendChild(p);
        i++;
        setTimeout(loop, 900);
      }
    })();
  }

  function hideAiLoadingModal() {
    const modal = document.getElementById("aiLoadingModal");
    if (modal) modal.classList.add("hidden");
  }


  // Export kalau pakai module system
  // export { showAiLoading, hideAiLoading };
  function renderRegulationDetailMultilayer(data, fieldName) {
    if (!data || data.length === 0) {
      return `<div class="p-4 text-center text-gray-400">Tidak ada regulasi untuk ditampilkan.</div>`;
    }

    const colorMap = {
      nasional: "bg-blue-500",
      regional: "bg-green-500",
      rs: "bg-yellow-500",
      permenkes: "bg-blue-600",
      ppk: "bg-blue-400",
      bridging: "bg-purple-500",
      fraud: "bg-red-500",
      temporary: "bg-gray-500",
      default: "bg-gray-500",
      error: "bg-red-500"
    };

    const items = data
      .map((r, index) => {
        const layerKey = (r.layer || r.dasar_hukum || "default").toLowerCase();
        const colorClass = colorMap[layerKey] || colorMap.default;
        const borderClass = index > 0 ? 'border-t border-gray-200 dark:border-gray-700 pt-4 mt-4' : '';

        return `
          <div class="regulation-item ${borderClass}">
            <div class="flex items-center gap-2 ${colorClass} px-3 py-2 rounded-t">
              <div class="font-bold text-gray-100 dark:text-white">${(r.layer || 'default').toUpperCase()}</div>
              <div class="text-gray-100 dark:text-white flex-1">${r.judul_regulasi || fieldName.replace('_', ' ')}</div>
              <div class="text-xs text-white opacity-75">${r.sumber || ''}</div>
            </div>
            <div class="p-4 bg-white text-gray-900 dark:bg-gray-800 dark:text-white rounded-b text-gray text-sm whitespace-pre-line">
              ${r.isi || 'Tidak ada detail regulasi.'}
            </div>
            ${r.status || r.update ? `
            <div class="flex justify-between items-center px-3 py-1 text-xs text-gray-400 mt-1">
              ${r.status ? `<div>Status: ${r.status}</div>` : ''}
              ${r.update ? `<div>Update: ${r.update}</div>` : ''}
            </div>
            ` : ''}
          </div>
        `;
      })
      .join("");

    return `
      <div class="bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-gray-100 p-6 rounded-2xl shadow-inner">
        <h2 class="text-center text-xl font-bold mb-6 text-emerald-600 dark:text-emerald-400">
          Detail Regulasi: ${fieldName.replace('_', ' ')}
        </h2>

        <div class="space-y-5">
          ${items}
        </div>

        <div class="mt-6 text-xs text-gray-400 text-right">
          Field:
          <code class="bg-gray-100 dark:bg-slate-800 px-2 py-1 rounded">${fieldName}</code>
        </div>
      </div>
    `;
  }

  function openOverlayModal(title, htmlContent, sourceType = null, sourceId = null) {
    // 🩵 reset global font biar modal lain gak ikut besar
    document.body.classList.remove("text-xl", "text-yellow-500", "font-bold");
    
    // simpan context biar tau nanti harus balik ke mana
    window.claimState = window.claimState || {};
    window.claimState.regulationSource = { type: sourceType, id: sourceId };
    
    let overlay = document.getElementById("overlayRegulasi");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "overlayRegulasi";
      overlay.className = "fixed inset-0 bg-black/40 dark:bg-black/70 flex items-center justify-center z-[9999]";
      document.body.appendChild(overlay);
    }

    overlay.innerHTML = `
      <div class="bg-white dark:bg-slate-800 text-gray-900 dark:text-white 
                  p-6 rounded-2xl max-w-4xl w-[90%] shadow-2xl relative 
                  animate-fade-in border border-slate-200 dark:border-slate-700 
                  max-h-[90vh] overflow-y-auto">
        <button type="button"
                class="absolute top-3 right-4 text-white bg-red-500 hover:bg-red-600 
                      px-4 py-2 rounded-lg shadow-md hover:shadow-lg transition-all 
                      transform hover:-translate-y-0.5"
                onclick="closeOverlayModal()">✕</button>
        <h2 class="text-lg font-semibold mb-4 text-center text-slate-800 dark:text-white">${title}</h2>
        ${htmlContent}
      </div>
    `;

    // ✅ Tambahkan ini di bawah
    requestAnimationFrame(() => {
      overlay.classList.add("visible");
    });
    document.body.classList.add("modal-open");
  }


  // =======================
  // Close overlay regulasi
  // =======================
  function closeOverlayModal() {
    const overlay = document.getElementById("overlayRegulasi");
    if (!overlay) return;

    // ✨ Tambahkan animasi fade-out
    overlay.classList.remove("visible");

    // Kunci scroll balik normal
    document.body.classList.remove("modal-open");

    // Tunggu 250ms (selama animasi fade-out), lalu hapus overlay
    setTimeout(() => {
      overlay.remove();

      const src = window.claimState?.regulationSource || {};
      console.log("🔻 closeOverlayModal triggered:", src);

      const lastType = src.type;
      window.claimState.regulationSource = null;

      // ❌ Reset flag agar tidak ada restore diagnosis ganda
      window.claimState.pendingRestoreDiagnosis = false;

      if (lastType === "procedure" && window.claimState?.currentProcedure?.id) {
        console.log("🩵 Restore modal tindakan:", window.claimState.currentProcedure);
        if (window.claimState.modalOpen) {
          console.warn("⛔ Skip restore tindakan karena modal masih terbuka");
          return;
        }
        openProcedureModal(
          window.claimState.currentProcedure.id,
          window.claimState.currentProcedure.name
        );
      } 
      else if (lastType === "diagnosis" && window.claimState?.currentDiagnosis) {
        console.log("🩵 Restore modal diagnosis:", window.claimState.currentDiagnosis);
        if (window.claimState.modalOpen) {
          console.warn("⛔ Skip restore diagnosis karena modal masih terbuka");
          return;
        }
        window.__suppressModalStack = true;
        openModal(
          `<div class="flex flex-col items-center">
            <span class="text-lg font-bold">Detail Diagnosis</span>
            <span class="font-bold text-2xl mb-2 text-yellow-500">
              ${window.claimState.currentDiagnosisTitle || "Diagnosis"}
            </span>
          </div>`,
          renderDiagnosisDetail(window.claimState.currentDiagnosis),
          { hideDefaultClose: false }
        );
        window.__suppressModalStack = false;
      }
    }, 250); // delay sesuai durasi animasi CSS
  }

  function normalizeId(rawId) {
    if (!rawId) return null;
    const n = parseInt(rawId);
    if (isNaN(n)) return null;

    // 🧠 Jika ID lebih besar dari 10 digit, anggap timestamp, bukan ID DB
    if (n > 9999999999) return null;

    return n;
  }



  // =======================
  // Main function to open regulation modal
  // =======================
  async function openRegulationDetailModal(fieldName, diagnosisId = null, procedureId = null) {
    try {
      const claimId =
        window.claimState?.selectedClaimId ||
        document.querySelector('[data-claim-id]')?.dataset.claimId ||
        new URLSearchParams(window.location.search).get('claim_id') ||
        1;

      const payload = {};

      // 🔹 Determine diagnosis name from multiple possible sources (ensure kategori always diagnosis)
      const diagnosisName =
        window.claimState?.currentDiagnosis?.disease_name ||
        window.claimState?.currentDiagnosis?.diagnosis_text ||
        window.claimState?.currentDiagnosisTitle ||
        document.querySelector('.diagnosis-name, .diagnosis-title, .selected-diagnosis')?.textContent?.trim() ||
        "";

      // 🔹 Determine procedure name if this is a tindakan scope
      const procedureName =
        (procedureId && (window.claimState?.currentProcedure?.name ||
          document.querySelector(`[data-procid="${procedureId}"] .cursor-pointer`)?.textContent?.trim()))
        || window.claimState?.currentProcedure?.name
        || document.querySelector(`[data-procid="${procedureId}"] .cursor-pointer`)?.textContent?.trim()
        || "";

      // Decide scope
      let scope = procedureId ? "tindakan" : "diagnosis";

      // ✅ Normalisasi ID biar gak timestamp
      const normalizedDiagnosisId = normalizeId(diagnosisId);
      const normalizedProcedureId = normalizeId(procedureId);
      // 🩹 PATCH: ganti procedureId langsung ke versi valid
      if (normalizedProcedureId) {
        procedureId = normalizedProcedureId; // gunakan ID valid
      } else if (window.claimState?.currentProcedure?.id) {
        console.log("🩵 Fallback to stored procedure_id:", window.claimState.currentProcedure.id);
        procedureId = window.claimState.currentProcedure.id;
      } else {
        console.warn("⚠️ procedureId invalid (timestamp), dikosongkan");
        procedureId = null;
      }

      // fallback: coba ambil ID dari claimState bila invalid
      if (!normalizedDiagnosisId && window.claimState?.currentDiagnosis?.id) {
        payload.diagnosis_id = window.claimState.currentDiagnosis.id;
      }
      if (!normalizedProcedureId && window.claimState?.currentProcedure?.id) {
        payload.procedure_id = window.claimState.currentProcedure.id;
      }

      // payload utama
      Object.assign(payload,{
        claim_id: claimId,
        // Always send kategori as the diagnosis name (backend expects diagnosis in 'kategori')
        kategori: diagnosisName || "Regulasi Umum",
        field: fieldName,
        scope,
        rs_id: window.claimState?.rs_id || "rs_notopuro",
        region_id: window.claimState?.region_id || "jatim",
      });

      // backward-compatible explicit fields for backend convenience
      if (diagnosisName) {
        payload.diagnosis_name = diagnosisName;
      }

      // jika tindakan, sertakan nama procedure di payload (key 'procedure' untuk konsistensi backend)
      if (procedureId || procedureName) {
        payload.procedure = procedureName || "";
        // keep item_id for procedure context
        if (procedureId) payload.item_id = procedureId;
      }

      // jika dipanggil dengan diagnosisId, sertakan item_id juga
      if (diagnosisId && !payload.item_id) payload.item_id = diagnosisId;

      const currentField = document.querySelector(`[data-field="${fieldName}"] .col-value`);
      if (currentField) payload.current_value = currentField.textContent.trim();

      // 🔹 Diagnosis ID dari DB
      if (scope === "diagnosis" && normalizedDiagnosisId) {
        payload.diagnosis_id = normalizedDiagnosisId;
      }

      // 🔹 Procedure ID dari DB
      if (scope === "tindakan" && normalizedProcedureId) {
        payload.procedure_id = normalizedProcedureId;
      }
      console.log("[REGULATION] Payload sent to backend:", payload);

      const response = await fetch(`/claims/${claimId}/regulation_detail`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const result = await response.json();
      console.log("[REGULATION] Response:", result);

      if (result.status === "success") {
        const rawData = result.data;
        const normalized = Array.isArray(rawData) ? rawData : rawData?.data || [];
        openOverlayModal(
          `${fieldName.replace('_', ' ').toUpperCase()}`,
          renderRegulationDetailMultilayer(normalized, fieldName),
          procedureId ? "procedure" : "diagnosis",
          procedureId || diagnosisId
        );
      } else {
        throw new Error(result.message || "Gagal memuat regulasi");
      }
    } catch (error) {
      console.error(`❌ Error fetching regulation detail:`, error);
      openOverlayModal(
        "Error",
        `<div class="p-4 text-red-500 text-center">
          <p>Gagal memuat detail regulasi: ${error.message || error}</p>
          <div class="mt-4">
            <button onclick="closeOverlayModal()" class="bg-blue-500 text-white px-4 py-2 rounded">
              Tutup
            </button>
          </div>
        </div>`,
        "diagnosis"
      );
    }
  }

// =====================================================
// UPDATE RINGKASAN FROM ROW (asli kamu – tidak diubah isinya)
// =====================================================
function updateRingkasanFromRow(itemId, dx) {
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

  // Buka modal dari klik kategori
  // Buka modal dari klik kategori
async function openModalFromAttr(el, type) {
  const tr = el.closest("tr");
  const dbId = tr?.dataset.dbId;
  const uiId = tr?.dataset.id;
  const claimId = document.getElementById("claimRoot")?.dataset.claimId;
  
  // Ambil nama penyakit dari cell yang diklik
  let diseaseName = "";
  if (el.textContent) {
    diseaseName = el.textContent.replace(/^â†'+\s*/, "").trim();
  } else {
    diseaseName = tr?.querySelector(".kategori-cell")?.textContent?.trim() || tr?.dataset.nama || "";
  }

  try {
    let dx = {};
    // 🔥 NEW: Jika type diagnosis/komorbid/komplikasi, POST ke /analyze_diagnosis (core_engine)
    if (["diagnosis","komorbid","komplikasi"].includes(type) && claimId && diseaseName) {
      showAiLoadingModal([
        "Mengambil data detail diagnosis...",
        "Memuat regulasi multilayer terkait...",
        "Menyiapkan tampilan modal..."
      ]);
      console.log("[REQ] POST /analyze_diagnosis", { claim_id: claimId, disease_name: diseaseName });
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
      showAiLoadingModal([
        "Mengambil data detail diagnosis...",
        "Memuat regulasi multilayer terkait...",
        "Menyiapkan tampilan modal..."
      ]);
      const result = await res.json();
      console.log("[RESP] /analyze_diagnosis", result);
      
      // 🔥 Process core_engine response untuk modal
      dx = result; // Set dx untuk updateRingkasanFromRow
      
      // 🩹 PATCH: Extract ICD-10 code dari nested structure
      const icd10Code = result.icd10?.kode_icd || result.icd10_code || "";
      const justifikasi = result.klinis?.justifikasi || result.justifikasi || "";
      const buktiKlinis = result.klinis?.bukti_klinis || result.bukti_klinis || "";
      
      // ✅ Ensure dx has flattened ICD-10 code for updateRingkasanFromRow
      dx.icd10_code = icd10Code;
      dx.justifikasi = justifikasi;
      dx.bukti_klinis = buktiKlinis;
      dx.kategori = diseaseName;
      
      console.log("🩹 [PATCH] Extracted ICD-10 from analyze_diagnosis:", { 
        icd10Code, 
        fullResult: result 
      });
      
      window.claimState.currentDiagnosis = result;
      window.claimState.currentDiagnosisTitle = diseaseName;
      
      const modalContent = renderDiagnosisDetail(result);
      openModal(`
        <div class="flex flex-col items-start items-center animate-fade-in">
          <span class="text-lg font-bold">Detail Diagnosis</span>
          <span class="font-bold text-2xl mb-2 text-yellow-500">${diseaseName}</span>
        </div>`,
        modalContent,
        { hideDefaultClose: false } // ✅ pastikan default close muncul
      );

      hideAiLoadingModal();

      // 🔥 CRITICAL: Call updateRingkasanFromRow setelah modal dibuka!
      console.log("🔥 Auto-filling table with data:", { uiId, dx });
      updateRingkasanFromRow(uiId, dx);
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
      openModal(`<div class="flex flex-col items-start items-center animate-fade-in">
        <span class="text-lg font-bold">Detail Diagnosis</span>
        <span class="font-bold text-2xl mb-2 text-yellow-500">${window.claimState.currentDiagnosisTitle}</span>
      </div>`, modalContent, { hideDefaultClose: false });
      return;
    }

    hideAiLoadingModal();

    let rawText = tr?.querySelector("td")?.innerText.trim() || "-";
    rawText = rawText.replace(/^â–¶|^â–¼/, "").trim();
    rawText = rawText.replace(/\s+\d+$/, "");
    const namaPenyakit =
      dx?.kategori || dx?.nama_kategori || dx?.diagnosis || dx?.komorbid || dx?.komplikasi || rawText || "";

    // 🔥 Use new renderDiagnosisDetail for consistent parsing
    const modalContent = renderDiagnosisDetail(dx);
    openModal(`<div class="flex flex-col items-start items-center animate-fade-in">
      <span class="text-lg font-bold">Detail Diagnosis</span>
      <span class="font-bold text-2xl mb-2 text-yellow-500">${namaPenyakit}</span>
    </div>`, modalContent, { hideDefaultClose: false });
    window.claimState.currentDiagnosis = dx;
    window.claimState.currentDiagnosisTitle = namaPenyakit;

    hideAiLoadingModal();

    updateRingkasanFromRow(uiId, dx);
  } catch (err) {
    console.error("❌ Gagal load modal detail:", err);
  }
}

  function renderNotificationBox(section, notifications = {}) {
    const colorMap = {
      success: "bg-emerald-50 border-emerald-500 text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-200",
      warning: "bg-amber-50 border-amber-500 text-amber-800 dark:bg-amber-900/20 dark:text-amber-200",
      error: "bg-rose-50 border-rose-500 text-rose-800 dark:bg-rose-900/20 dark:text-rose-200",
      info: "bg-blue-50 border-blue-500 text-blue-800 dark:bg-blue-900/20 dark:text-blue-200",
      default: "bg-slate-50 border-slate-400 text-slate-700 dark:bg-white text-gray-900 dark:bg-slate-800 dark:text-white/50 dark:text-slate-300"
    };

    // Ambil notifikasi per section
    const note = notifications?.[section] || {};
    const status = note.status || "default";
    const msg = note.message || `Belum ada notifikasi untuk bagian ${section.toUpperCase()}.`;
    const cls = colorMap[status] || colorMap.default;

    return `
      <div class="notification-box ${cls} border-l-4 p-3 rounded-lg mb-3 text-sm shadow-sm">
        <div>
          <strong class="font-semibold">Notifikasi AI (${section.toUpperCase()})</strong>
          <div class="text-xs leading-snug mt-1">${msg}</div>
        </div>
      </div>
    `;
  }

  function renderFieldMultilayer(fieldData, label, fieldName = "syarat_klinis", diagnosisId = null) {
  if (!fieldData) {
    return `
      <div class="grid grid-cols-2 align-top">
        <div class="bg-gray-100 text-gray-900 dark:bg-slate-700 dark:text-white px-3 py-2 align-top font-medium">${label}</div>
        <div class="bg-white text-gray-800 dark:bg-slate-700 dark:text-gray-100 px-3 py-2 align-top">-</div>
      </div>
    `;
  }

  const isi = typeof fieldData === 'string' 
    ? fieldData 
    : (fieldData?.isi !== undefined ? fieldData.isi : "-");

  const isMultiline = typeof isi === "string" && (isi.includes("•") || isi.includes("["));

  if (isMultiline) {
    const lines = isi.split(/\n|(?=•)/).filter(line => line.trim() !== "");
    const itemsHtml = lines.map(line => {
      const match = line.match(/(?:•\s*)?\[(.*?)\]\s*([^:]+):\s*(.*?)(?:\((.+?)\))?$/);
      if (match) {
        const layer = match[1].trim().toLowerCase();
        const title = match[2].trim();
        const detail = match[3].trim();
        const sumber = match[4] ? `(${match[4].trim()})` : "";

        const colorClass = getLayerColorClass(layer)
          .replace(/bg\-\w+\-\d+\s?/g, '')
          .replace(/dark\:bg\-\w+\-\d+\s?/g, '');

        return `
          <li class="mb-2 leading-snug">
            <span class="font-semibold ${colorClass} cursor-pointer hover:underline regulation-field"
                  title="📋 Klik untuk melihat regulasi ${label}"
                  data-field="${fieldName}"
                  data-layer="${layer}"
                  data-diagnosis-id="${diagnosisId || ''}"
                  onclick="window.openRegulationDetailModal('${fieldName}', '${diagnosisId || ''}', null, '${layer}')">
              ${title}:
            </span>
            <span class="ml-1">${detail}</span>
            ${sumber ? `<span class="text-xs text-gray-500 dark:text-gray-400 ml-1">${sumber}</span>` : ""}
          </li>
        `;
      } else {
        return `<li class="mb-2 leading-snug">${line.trim().replace(/^•\s*/, '')}</li>`;
      }
    }).join("");

    return `
      <div class="grid grid-cols-2 align-top">
        <div class="bg-gray-100 text-gray-900 dark:bg-slate-700 dark:text-white px-3 py-2 align-top font-medium">${label}</div>
        <div class="bg-white text-gray-800 dark:bg-slate-700 dark:text-gray-100 px-3 py-2 align-top">
          <ul class="list-disc pl-4 space-y-1">${itemsHtml}</ul>
          ${fieldData.label_multilayer ? `<div class="text-xs text-blue-500 dark:text-blue-300 mt-2 italic">${fieldData.label_multilayer}</div>` : ""}
        </div>
      </div>
    `;
  }

  // fallback jika bukan multilayer
  return `
    <div class="grid grid-cols-2 align-top">
      <div class="bg-gray-100 text-gray-900 dark:bg-slate-700 dark:text-white px-3 py-2 align-top font-medium">${label}</div>
      <div class="bg-white text-gray-800 dark:bg-slate-700 dark:text-gray-100 px-3 py-2 text-sm align-top whitespace-pre-line">
        ${isi}
        ${fieldData.label_multilayer ? `<div class="text-xs text-blue-500 dark:text-blue-300 mt-1 italic">${fieldData.label_multilayer}</div>` : ""}
      </div>
    </div>
  `;
  }

  // 🔹 Fungsi render utama modal detail diagnosis
  function renderDiagnosisDetail(it) {
    console.log("📋 renderDiagnosisDetail data:", it);

    const diagnosisId = it.diagnosis_id || it.id

    // parsing aman semua subbagian
    const klinis = it.klinis || {};
    const icd10 = it.icd10 || {};
    const tindakan = Array.isArray(it.tindakan) ? it.tindakan : [];
    const rawat = it.rawat_inap || it.rawat || {};
    const faskes = it.faskes || {};
    const rujukan = it.rujukan || {};
    const inaCbg = it.inaCbg || it.ina_cbg || {};
    const notifications = it.notifications || {}; // 🔔 notifikasi per section dari core_engine
    const safeRender = (cb) => {
      try { return cb(); } catch (e) { console.warn("render skip:", e); return ""; }
    };
    console.log("📋 Parsed notifications:", notifications);
    
    console.log("📋 Parsed klinis:", klinis);
    console.log("📋 Parsed icd10:", icd10);
    console.log("📋 Parsed tindakan count:", tindakan.length);
    console.log("🧩 [DEBUG] Simulasi tindakan saat render ulang:", 
    window.claimState?.simulasi?.[window.claimState?.tab || "admission"]?.tindakan);

    
    // 🔥 Debug specific field values
    console.log("📋 klinis.justifikasi:", klinis.justifikasi);
    console.log("📋 klinis.bukti_klinis:", klinis.bukti_klinis);
    console.log("📋 icd10.kode_icd:", icd10.kode_icd);
    console.log("📋 rawat.indikasi:", rawat.indikasi);

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
        <!-- ✅ UBAH INI: Tambahkan bg-gray-100 untuk light mode -->
        <div class="bg-gray-100 text-gray-900 dark:bg-slate-700 dark:text-white px-3 py-2 font-medium">${label}</div>
        <div class="${colorClass} px-3 py-2">${content}</div>
      </div>
    `;
    return boxHtml;
    };

    // === 3️⃣ Render keseluruhan modal ===
    return `
      <div class="space-y-6 text-sm">
        
        <!-- 🩺 KLINIS -->
        <section class="rounded-xl shadow-md overflow-hidden border border-slate-200 dark:border-slate-700">
          <div class="bg-gradient-to-r from-blue-500 to-blue-600 text-white px-4 py-3 font-bold rounded-t-xl shadow-sm">KLINIS</div>
          <div class="space-y-2 p-3 bg-gray-50 dark:bg-slate-700">
            ${renderNotificationBox("klinis", notifications)}
            ${safeRender(() => renderBox("Justifikasi", klinis.justifikasi, klinis.status, diagnosisId, "justifikasi"))}
            ${safeRender(() => renderBox("Bukti Klinis", klinis.bukti_klinis, null, diagnosisId, "bukti_klinis"))}
            ${safeRender(() => {console.log("📋 KLINIS - syarat_klinis:", klinis.syarat_klinis);
              const hasMultilayers = typeof klinis.syarat_klinis === "string" && (
                klinis.syarat_klinis.includes("[Nasional]") ||
                klinis.syarat_klinis.includes("[PNPK]") ||
                klinis.syarat_klinis.includes("•")
              );
              if (hasMultilayers) {
                return renderFieldMultilayer(
                  { isi: klinis.syarat_klinis },"Syarat Klinis","syarat_klinis",diagnosisId);
              } else {
                return renderBox("Syarat Klinis",klinis.syarat_klinis,klinis.status,diagnosisId,"syarat_klinis");
              }
            })}
          </div>
        </section>

        <!-- 🧾 ICD-10 -->
        <section class="rounded-xl shadow-md overflow-hidden border border-slate-200 dark:border-slate-700">
          <div class="bg-gradient-to-r from-blue-500 to-blue-600 text-white px-4 py-3 font-bold rounded-t-xl shadow-sm">ICD-10</div>
          <div class="space-y-2 p-3 bg-gray-50 dark:bg-slate-700">
            ${renderNotificationBox("icd", notifications)}
            ${safeRender(() => renderBox("Kode ICD", icd10.kode_icd, icd10.status_icd, diagnosisId, "kode_icd"))}
            ${safeRender(() => {console.log("📋 ICD10 - kode_ganda:", icd10.kode_ganda);
              const hasMultilayers = typeof icd10.kode_ganda === "string" && (icd10.kode_ganda.includes("[Nasional]") || icd10.kode_ganda.includes("[PNPK]") || icd10.kode_ganda.includes("•"));
              return hasMultilayers ? renderFieldMultilayer({isi: icd10.kode_ganda}, "Kode Ganda", "kode_ganda", diagnosisId)
                                    : renderBox("Kode Ganda", icd10.kode_ganda, icd10.status_icd, diagnosisId, "kode_ganda");
            })}

            ${safeRender(() => {console.log("📋 ICD10 - z_code:", icd10.z_code);
              const hasMultilayers = typeof icd10.z_code === "string" && (icd10.z_code.includes("[Nasional]") || icd10.z_code.includes("[PNPK]") || icd10.z_code.includes("•"));
              return hasMultilayers ? renderFieldMultilayer({isi: icd10.z_code}, "Z-Code", "z_code", diagnosisId)
                                    : renderBox("Z-Code", icd10.z_code, icd10.status_icd, diagnosisId, "z_code");
            })}

            ${safeRender(() => {console.log("📋 ICD10 - kode_bpjs_khusus:", icd10.kode_bpjs_khusus);
              const hasMultilayers = typeof icd10.kode_bpjs_khusus === "string" && (icd10.kode_bpjs_khusus.includes("[Nasional]") || icd10.kode_bpjs_khusus.includes("[PNPK]") || icd10.kode_bpjs_khusus.includes("•"));
              return hasMultilayers ? renderFieldMultilayer({isi: icd10.kode_bpjs_khusus}, "Kode BPJS Khusus", "kode_bpjs_khusus", diagnosisId)
                                    : renderBox("Kode BPJS Khusus", icd10.kode_bpjs_khusus, icd10.status_icd, diagnosisId, "kode_bpjs_khusus");
            })}
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
            ${safeRender(() => {console.log("📋 RAWAT - indikasi:", rawat.indikasi);
              const hasMultilayers = typeof rawat.indikasi === "string" && (rawat.indikasi.includes("[Nasional]") || rawat.indikasi.includes("[PNPK]") || rawat.indikasi.includes("•"));
              return hasMultilayers ? renderFieldMultilayer({isi: rawat.indikasi}, "Indikasi", "indikasi", diagnosisId)
                                    : renderBox("Indikasi", rawat.indikasi, rawat.status_indikasi, diagnosisId, "indikasi");
            })}

            ${safeRender(() => renderBox("Kriteria", rawat.kriteria, rawat.status_kriteria, diagnosisId, "kriteria"))}
            ${safeRender(() => {console.log("📋 RAWAT - lama_rawat:", rawat.lama_rawat);
              const hasMultilayers = typeof rawat.lama_rawat === "string" && (rawat.lama_rawat.includes("[Nasional]") || rawat.lama_rawat.includes("[PNPK]") || rawat.lama_rawat.includes("•"));
              return hasMultilayers ? renderFieldMultilayer({isi: rawat.lama_rawat}, "Lama Rawat", "lama_rawat", diagnosisId)
                                    : renderBox("Lama Rawat", rawat.lama_rawat, rawat.status_lama, diagnosisId, "lama_rawat");
            })}

          </div>
        </section>

        <!-- 🏢 FASKES -->
        <section class="rounded-xl shadow-md overflow-hidden border border-slate-200 dark:border-slate-700">
          <div class="bg-gradient-to-r from-amber-500 to-amber-600 text-white px-4 py-3 font-bold rounded-t-xl shadow-sm">FASKES</div>
          <div class="space-y-2 p-3 bg-gray-50 dark:bg-slate-700">
            ${renderNotificationBox("faskes", notifications)}
            ${safeRender(() => {console.log("📋 FASKES - tingkat:", faskes.tingkat);
              const hasMultilayers = typeof faskes.tingkat === "string" && (faskes.tingkat.includes("[Nasional]") || faskes.tingkat.includes("[PNPK]") || faskes.tingkat.includes("•"));
              return hasMultilayers ? renderFieldMultilayer({isi: faskes.tingkat}, "Tingkat", "tingkat", diagnosisId)
                                    : renderBox("Tingkat", faskes.tingkat, faskes.status_tingkat, diagnosisId, "tingkat");
            })}
            ${safeRender(() => renderBox("Justifikasi", faskes.justifikasi, faskes.status_justifikasi, diagnosisId, "justifikasi_faskes"))}
            ${safeRender(() => renderBox("Kompetensi", faskes.kompetensi, faskes.status_kompetensi, diagnosisId, "kompetensi"))}
          </div>
        </section>

        <!-- 🔁 RUJUKAN -->
        <section class="rounded-xl shadow-md overflow-hidden border border-slate-200 dark:border-slate-700">
          <div class="bg-gradient-to-r from-orange-500 to-orange-600 text-white px-4 py-3 font-bold rounded-t-xl shadow-sm">RUJUKAN</div>
          <div class="space-y-2 p-3 bg-gray-50 dark:bg-slate-700">
            ${renderNotificationBox("rujukan", notifications)}
            ${safeRender(() => {console.log("📋 RUJUKAN - indikasi:", rujukan.indikasi);
              const hasMultilayers = typeof rujukan.indikasi === "string" && (rujukan.indikasi.includes("[Nasional]") || rujukan.indikasi.includes("[PNPK]") || rujukan.indikasi.includes("•"));
              return hasMultilayers ? renderFieldMultilayer({isi: rujukan.indikasi}, "Indikasi", "indikasi_rujukan", diagnosisId)
                                    : renderBox("Indikasi", rujukan.indikasi, rujukan.status_indikasi, diagnosisId, "indikasi_rujukan");
            })}
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

// Helper functions for i-DRG 
window.getPrediction = function(field) {
  try {
    // For Alpine.js context within renderIdrgSection
    if (this && this.data && this.data.data && this.data.data.idrg_prediction) {
      return this.data.data.idrg_prediction[field] || '-';
    }
    
    // For global context or when called directly
    const data = window.claimState?.currentDiagnosis?.idrg_prediction || {};
    return data[field] || '-';
  } catch (err) {
    console.error('Error in getPrediction:', err);
    return '-';
  }
};
window.getSeverityLabel = function(index) {
  const labels = {
    "1": "Minor (Level 1)",
    "2": "Moderate (Level 2)", 
    "3": "Major (Level 3)",
    "4": "Extreme (Level 4)"
  };
  return labels[index] || index || "-";
};

window.renderChecklistHtml = function(checklist) {
  if (!checklist) return '-';

  // Jika string, split menjadi array baris bila ada newline
  let items = [];
  if (typeof checklist === 'string') {
    items = checklist.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  } else if (Array.isArray(checklist)) {
    items = checklist.slice();
  } else {
    return checklist;
  }

  // Clean each item: remove leading bullets/markers and duplicate bullets
  const cleaned = items.map(item => {
    let s = String(item).trim();
    // remove leading bullet characters or dash/star, optionally repeated
    s = s.replace(/^[•\-\*\u2022]\s*/, '');
    // remove duplicated inner bullets like "• • ..." or duplicated bracketed tags
    s = s.replace(/\s*•\s*/g, ' • ').replace(/\s{2,}/g, ' ').trim();
    return s;
  }).filter(Boolean);

  if (cleaned.length === 0) return '-';

  // Render as list (no extra "• " added if item already starts with bullet)
  const html = cleaned.map(it => {
    const itemText = it.startsWith('•') ? it.replace(/^•\s*/, '') : it;
    return `<li>${itemText}</li>`;
  }).join('');

  return `<ul class="list-disc pl-4">${html}</ul>`;
};

  // Define helper functions at the module level
  function getPrediction(field) {
    try {
      const data = this?.data?.idrg_prediction;
      return data?.[field] || '-';
    } catch (err) {
      console.error('Error in getPrediction:', err);
      return '-';
    }
  }

  window.getPrediction = getPrediction;  // Make it globally available

  function formatRupiah(value) {
    if (value === null || value === undefined || value === '') return '-';
    
    // Jika sudah ada “Rp” di depan, jangan ubah
    if (typeof value === 'string' && value.trim().startsWith('Rp')) return value;

    // Ambil hanya digit angka
    const numeric = Number(String(value).replace(/[^\d]/g, ''));
    if (isNaN(numeric) || numeric === 0) return '-';
    
    return 'Rp ' + numeric.toLocaleString('id-ID');
  }

  function renderIdrgSection(idrg, claimId, diagnosisName = null) {
    if (!claimId) {
      const claimRoot = document.getElementById("claimRoot");
      claimId = claimRoot?.dataset.claimId || "";
    }

    if (!diagnosisName) {
      diagnosisName = window.claimState?.currentDiagnosis?.diagnosis_text || "";
    }

    // Helper function for rendering prediction rows in i-DRG section
        function renderPredictionRow(label, valueHtml) {
          return `
            <div class="grid grid-cols-2">
              <div class="bg-white dark:bg-slate-700 text-gray-800 dark:text-gray-100 px-3 py-2 font-medium">${label}</div>
              <div class="bg-white dark:bg-slate-700 text-gray-800 dark:text-gray-100 px-3 py-2">${valueHtml}</div>
            </div>
          `;
        }
    
    
        // --- Helper untuk data tersimpan ---
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
            </div>
          `;
        };

    // --- Template utama ---
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
        <!-- HEADER -->
        <div class="flex items-center justify-between bg-blue-600 text-white px-3 py-2 font-bold cursor-pointer"
            @click="toggleAndPredict()">
          <span>i-DRG</span>
          <span class="flex items-center">
            <span x-show="loading" class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
            <span x-text="open ? '▼' : '▶'"></span>
          </span>
        </div>

        <!-- CONTENT -->
        <div x-show="open" x-transition>
          <!-- Loading -->
          <div x-show="loading" class="p-4 text-center">
            <div class="inline-flex items-center">
              <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mr-3"></div>
              <span class="text-blue-600 font-medium">Menganalisis dengan OpenAI...</span>
            </div>
          </div>

          <!-- Notifikasi -->
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

          <!-- Prediction -->
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

          <!-- Error -->
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

          <!-- Saved Data -->
          ${idrg ? `
          <div class="p-4 space-y-2 border-t" x-show="!loading">
            <h3 class="font-bold text-gray-800 dark:text-gray-200 mb-2">Data i-DRG Tersimpan</h3>
            ${renderExistingRow("Group i-DRG", idrg.group_idrg || "", "idrg_diagnosis_group")}
            ${renderExistingRow("Severity Index", idrg.severity_index || "", "idrg_diagnosis_severity")}
            ${renderExistingRow("Checklist Dokumentasi", idrg.checklist || "", "idrg_diagnosis_checklist")}
            ${renderExistingRow("Faktor Severity", idrg.faktor_severity || "")}
            ${renderExistingRow("Ungroupable Alert", idrg.ungroupable_alert || "", "idrg_diagnosis_ungroupable")}
            ${renderExistingRow("Simulasi Tarif", idrg.simulasi_tarif || "")}
            ${renderExistingRow("Gap Analysis", idrg.gap_analysis || "")}
          </div>` : ''}
        </div>
      </div>
    `;
  }


  // Update renderIdrgPredictionResult untuk tampil lebih simple

  function renderIdrgPredictionResult(data) {
    if (!data || !data.idrg_prediction) {
      return `<div class="p-4 text-red-500">Data prediksi i-DRG tidak lengkap</div>`;
    }

    const prediction = data.idrg_prediction;

    // helper render baris
    function renderPredictionRow(label, value, isClickable = false) {
      const content = isClickable
        ? `<span class="cursor-pointer hover:underline hover:text-blue-600">${value}</span>`
        : value || "-";
      return `
        <div class="grid grid-cols-2">
          <div class="bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-white px-3 py-2 font-medium">${label}</div>
          <div class="bg-white text-gray-900 dark:bg-gray-600 dark:text-gray-100 px-3 py-2">${content}</div>
        </div>
      `;
    }

    // checklist jadi list
    let checklistHtml = "";
    if (Array.isArray(prediction.checklist_dokumentasi)) {
      checklistHtml = `<ul class="list-disc list-inside space-y-0.5">
        ${prediction.checklist_dokumentasi.map(i => `<li>${i}</li>`).join("")}
      </ul>`;
    } else if (prediction.checklist_dokumentasi) {
      checklistHtml = prediction.checklist_dokumentasi;
    }

    // faktor severity jadi list
    let faktorSeverityHtml = "";
    if (Array.isArray(prediction.faktor_penentu_severity)) {
      faktorSeverityHtml = `<ul class="list-disc list-inside space-y-0.5">
        ${prediction.faktor_penentu_severity.map(i => `<li>${i}</li>`).join("")}
      </ul>`;
    } else if (prediction.faktor_penentu_severity) {
      faktorSeverityHtml = prediction.faktor_penentu_severity;
    }

    // mapping severity
    const severityLabel = {
      "1": "Minor (1)",
      "2": "Moderate (2)",
      "3": "Major (3)",
      "4": "Extreme (4)"
    };

    // hasil akhir
    return `
      <div class="space-y-2 p-4">
        ${renderPredictionRow("Kode i-DRG", prediction.group_idrg || "-", true)}
        ${renderPredictionRow(
          "Severity Index",
          severityLabel[prediction.severity_index] || prediction.severity_index || "-",
          true
        )}
        ${renderPredictionRow("Checklist Dokumentasi", checklistHtml)}
        ${renderPredictionRow("Faktor Penentu Severity", faktorSeverityHtml)}
        ${renderPredictionRow("Ungroupable Alert", prediction.ungroupable_alert || "-")}
        ${renderPredictionRow(
          "Estimasi Tarif",
          `<span>${formatRupiah(prediction.estimasi_tarif_idrg || 0)}</span>`
        )}
        ${renderPredictionRow(
          "Gap Analysis",
          `<span>${formatRupiah(prediction.gap_analysis || 0)}</span>`
        )}

        <div class="text-xs text-blue-600 dark:text-blue-300 mt-3 p-2 rounded border border-blue-100 dark:border-blue-700 bg-white dark:bg-gray-800">
          <strong>Engine:</strong> ${data.engine_version || "OpenAI GPT-4"} •
          <strong>Mode:</strong> Single Diagnosis •
          <strong>Diagnosis:</strong> ${data.diagnosis || "-"} •
          <strong>Generated:</strong> ${new Date().toLocaleString()}
        </div>
      </div>
    `;
  }


  function renderTindakan(list) {
    const isDark = document.documentElement.classList.contains("dark");

    const tindakanList = (list && list.length > 0)
      ? list.map(td => {
          const nama = td.nama || td.tindakan || "";
          const procId = td.procedure_id || td.id || "";

          // 🩵 Kosongkan deskripsi saat pertama kali load, isi hanya kalau ada data AI / manual
          // Tampilkan deskripsi hanya kalau tindakan sudah dianalisis
          const description = td.analyzed
            ? (td.deskripsi_tindakan || td.deskripsi || td.icd9 || "&nbsp;")
            : "&nbsp;";


          return `
            <div class="grid grid-cols-3 gap-4 items-center ${
              isDark
                ? "bg-slate-800 text-white border-slate-700"
                : "bg-white text-gray-900 border-slate-200"
            } p-4 rounded-xl shadow-sm hover:shadow-md transition-shadow border mb-3"
                data-procid="${procId}">
              <div class="font-semibold text-blue-600 underline cursor-pointer truncate"
                  onclick="openProcedureModal('${procId}', '${nama}')">${nama}</div>
              <div>
                <span class="block px-3 py-1 text-sm font-medium ${
                  isDark
                    ? "bg-slate-700 text-gray-100"
                    : "bg-gray-100 text-gray-900"
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
        }).join("")
      : `<div class="italic text-gray-500 dark:text-gray-400">Tidak ada tindakan AI</div>`;

    const manualForm =
      window.claimState?.role === "doctor"
        ? `
        <div class="tindakan-list mt-4"></div>
        <div class="mt-4 p-4 border ${
          isDark
            ? "border-slate-600 bg-slate-800 text-white"
            : "border-slate-200 bg-gray-50 text-gray-900"
        } rounded-xl shadow-sm">
          <div class="font-semibold mb-3">Tambah Tindakan Manual</div>

          <div class="relative flex flex-col gap-2 mt-2" x-data="tindakanAutocomplete()" x-ref="acWrap">
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


    setTimeout(
      () => window.renderManualTindakanList && window.renderManualTindakanList(),
      0
    );

    return tindakanList + manualForm;
  }



  function buildModalContent(it) {
    let content = renderDiagnosisDetail(it);
    content += `<div class="tindakan-list mt-4"></div>`;
    setTimeout(() => window.renderManualTindakanList && window.renderManualTindakanList(), 0);
    return content;
  }

  async function openProcedureModal(procId, procedureName) {
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

      // 🩺 Update kolom deskripsi di daftar tindakan utama
      const procRow = document.querySelector(`[data-procid="${procId}"]`);
      if (procRow) {
        const descCell = procRow.querySelector("span[title], span.block");
        if (descCell) {
          const newDesc = `ICD-9: ${d.icd9_code || d.icd9 || "-"}, Status: ${d.status_tindakan || d.status || "-"}, INA-CBG: ${d.ina_cbg_tarif || d.ina_cbg || "-"}`;
          descCell.textContent = newDesc;
          descCell.setAttribute("title", newDesc);
        }
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

    } catch (err) {
      console.error("❌ Gagal load detail tindakan:", err);
    }
  }


  async function openManualDetailModal(it, tab, idx) {
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
                  onclick="closeNestedModal()"
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

  function renderProcedureDetail(it) {
    const d = (it.detail && it.detail[0]) || it;
    const deskripsi = d.icd9 && d.status && d.ina_cbg
      ? `ICD-9: ${d.icd9}, Status: ${d.status}, INA-CBG: ${d.ina_cbg}`
      : (d.icd9 || d.status || d.ina_cbg || "");
    const renderProcBox = (label, value, skipReg = false) => {
      const safeValue = value || "-";
      const content = (!skipReg)
        ? `<span class="cursor-pointer" title="PNPK Sepsis 2020"
                  @click="openRegulationDetailModal('${d.icd9}', 'procedure')">${safeValue}</span>`
        : safeValue;

      return `<div class="bg-slate-100 text-gray-900 dark:bg-slate-700 dark:text-white px-3 py-2 rounded-lg font-semibold text-white"><b>${label}:</b></div>
              <div class="bg-white text-gray-900 dark:bg-gray-800 dark:text-white px-3 py-2 rounded">${content}</div>`;
    };

    return `
      <div class="grid grid-cols-2 gap-2 text-sm">
        ${renderProcBox("Kode ICD-9", d.icd9)}
        ${renderProcBox("Deskripsi", d.deskripsi || deskripsi)}
        ${renderProcBox("Validitas", d.validitas, true)}
        ${renderProcBox("Status", d.status)}
        ${renderProcBox("Tarif INA-CBG", d.ina_cbg)}
        ${renderProcBox("Faskes", d.faskes)}
        ${renderProcBox("Rawat Inap", d.rawat_inap)}
        ${renderProcBox("Syarat Klinis", d.syarat_klinis)}
      </div>
    `;
  }

  let modalClosing = false;

  function closeNestedModal() {
    if (modalClosing) {
      console.log("⚠️ [DEBUG] closeNestedModal double trigger prevented");
      return;
    }
    modalClosing = true;

    document.body.classList.remove("modal-open");

    // 🚫 MODE VERIFIKATOR: close langsung, tanpa stack restore & Alpine
    if (window.currentUserRole === "verifikator") {
      const modalContainer = document.getElementById("modalContainer");
      if (modalContainer) {
        modalContainer.classList.add("hidden");
        modalContainer.innerHTML = "";
      }
      window.claimState.modalOpen = false;
      modalClosing = false;
      console.log("✅ [VERIFICATOR] Modal closed cleanly.");
      return;
    }


    // 🧩 MODE DOKTER (flow lama utuh)
    try {
      window.persistManualTindakanBeforeClose && window.persistManualTindakanBeforeClose();
    } catch (e) {
      console.warn("⚠️ Gagal persist manual tindakan sebelum close:", e);
    }

    console.log(
      "🧩 [DEBUG] Simulasi tindakan sebelum close:",
      window.claimState?.simulasi?.[window.claimState?.tab || "admission"]?.tindakan
    );

    let modalContainer = document.getElementById("modalContainer");
    let modalContent = document.querySelector(".modal-content");
    let modalTitle = document.querySelector(".modal-title");
    const stack = window.claimState?.modalStack || [];

    if (!modalContainer) {
      console.warn("⚠️ closeNestedModal: modalContainer tidak ditemukan, membuat ulang.");
      modalContainer = document.createElement("div");
      modalContainer.id = "modalContainer";
      document.body.appendChild(modalContainer);
    }
    if (!modalContent) {
      console.warn("⚠️ closeNestedModal: modalContent hilang, membuat ulang.");
      modalContent = document.createElement("div");
      modalContent.className =
        "modal-content relative bg-gray-50 dark:bg-slate-800 text-slate-900 dark:text-white p-6 rounded-2xl max-h-[90vh] overflow-y-auto shadow-2xl w-[90%] max-w-4xl border border-slate-200 dark:border-slate-700";
      modalContainer.appendChild(modalContent);
    }
    if (!modalTitle) {
      modalTitle = document.createElement("div");
      modalTitle.className = "modal-title font-bold text-lg mb-2";
      modalContent.prepend(modalTitle);
    }

    modalContent.classList.add("modal-fade-exit");
    setTimeout(() => modalContent.classList.add("modal-fade-exit-active"), 10);

    setTimeout(() => {
      modalContent.classList.remove("modal-fade-exit", "modal-fade-exit-active");

      if (stack.length > 0) {
        const prev = stack.pop();
        console.log("🧩 restore modal:", prev);
        modalTitle.innerHTML = prev.title || "(Untitled)";
        modalContent.innerHTML = prev.content || "<p>Tidak ada konten sebelumnya</p>";
      } else {
        modalContainer.classList.add("hidden");
        window.claimState.modalOpen = false;
        modalContent.innerHTML = "";
        modalTitle.innerHTML = "";
      }

      document
        .querySelectorAll('ul[x-teleport="body"]')
        .forEach(el => el?._cleanup && el._cleanup());

      setTimeout(() => {
        Alpine.initTree(modalContent);
        setTimeout(() => {
          try {
            if (typeof window.renderManualTindakanList === "function") {
              const tab = window.claimState?.tab || "admission";
              console.log("🧩 Re-render manual tindakan setelah Alpine reinit:", tab);
              window.renderManualTindakanList(tab);
            }
          } catch (e) {
            console.warn("⚠️ Gagal renderManualTindakanList setelah restore:", e);
          }
        }, 150);
      }, 50);

      modalClosing = false;
    }, 250);

    if (window.claimState?.pendingRestoreDiagnosis) {
      setTimeout(() => {
        if (window.claimState?.currentDiagnosis) {
          console.log("🩵 Balik ke modal diagnosis setelah tindakan ditutup");
          openModal(
            `<div class="flex flex-col items-center">
              <span class="text-lg font-bold">Detail Diagnosis</span>
              <span class="font-bold text-2xl mb-2 text-yellow-500">
                ${window.claimState.currentDiagnosisTitle || "Diagnosis"}
              </span>
            </div>`,
            renderDiagnosisDetail(window.claimState.currentDiagnosis),
            { hideDefaultClose: false }
          );
        }
        window.claimState.pendingRestoreDiagnosis = false;
      }, 100);
    }
  }

// ==========================================================
// 🧩 SISTEM NOTES FINAL (DOKTER / CODER / VERIFIKATOR)
// ==========================================================

// ✅ 1. Normalisasi field agar seragam antar role
function normalizeFieldKey(key) {
  if (!key) return key;
  key = key.toLowerCase();

  const mapping = {
    "diagnosis": "primary_diagnosis",
    "utama_diagnosis": "primary_diagnosis",
    "komorbid": "secondary_diagnosis",
    "komplikasi": "secondary_diagnosis",

    "tindakan": "primary_action",
    "utama_tindakan": "primary_action",
    "prosedur": "primary_action",
    "prosedur_sekunder": "secondary_action",
  };

  return mapping[key] || key;
}

// ✅ 2. ID stabil tanpa hash (supaya sama setiap reload)
function getStableItemId(claimId, stage, fieldKey, itemName = "") {
  const key = (fieldKey || "").toLowerCase();

  // Diagnosis
  if (["primary_diagnosis", "diagnosis", "utama_diagnosis"].includes(key)) return 1;
  if (["secondary_diagnosis", "komorbid", "komplikasi"].includes(key)) return 2;

  // Tindakan
  if (["primary_action", "tindakan", "utama_tindakan", "prosedur"].includes(key)) return 3;
  if (["secondary_action", "prosedur_sekunder"].includes(key)) return 4;

  // fallback umum
  return 9999;
}

// ✅ 3. helper untuk dapatkan id diagnosis/procedure asli (origin)
function getOriginItemId(item) {
  // kasus: data hasil evaluasi coder (ClaimDiagnosisEvaluation / ClaimProcedureEvaluation)
  if (item && item.diagnosis_id) return item.diagnosis_id;
  if (item && item.procedure_id) return item.procedure_id;
  // fallback ke id biasa
  return item?.id || null;
}

// ✅ 4. Buka modal catatan (dengan context lengkap)
window.openNoteModal = async function(title, fieldKey, item = null) {
  const root = document.getElementById("claimRoot");
  let state = null;
  try {
    state = Alpine.$data(root);
  } catch {
    console.warn("⚠️ fallback ke window.claimState karena Alpine belum aktif");
    state = window.claimState || {};
  }

  const claimId = root.dataset.claimId;
  const currentStage = state.tab || window.claimState?.tab || "admission";

  // 🔄 Normalisasi field agar seragam
  fieldKey = normalizeFieldKey(fieldKey);

  // Simpan context
  state.currentNoteItem = item;
  state.currentNoteField = fieldKey;
  state.currentNoteStage = currentStage;

  // Tentukan itemId (stabil)
  const itemName = item?.name || "primary";
  let itemId = item?.id || null;

  // Jika role coder → arahkan ke id asal dokter
  if (state.role === "coder") {
    const originId = getOriginItemId(item);
    if (originId && originId !== itemId) {
      console.log("🧩 Mapping coder evaluation id → origin_id:", itemId, "→", originId);
      itemId = originId;
    } else {
      // fallback: gunakan ID stabil (1=utama, 2=sekunder, dst.)
      const stableId = getStableItemId(claimId, currentStage, fieldKey, itemName);
      console.log("🧭 Fallback ke stable ID untuk coder:", itemId, "→", stableId);
      itemId = stableId;
    }
  } else if (!itemId) {
    // fallback untuk dokter/verifikator
    itemId = getStableItemId(claimId, currentStage, fieldKey, itemName);
  }

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

  // tampilkan modal
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
                class="px-4 py-2 rounded bg-gray-600 hover:bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-white"
                onclick="Alpine.$data(document.getElementById('claimRoot')).modalOpen=false">
          Close
        </button>
        <button type="button"
                class="px-4 py-2 rounded bg-blue-600 text-white"
                onclick="saveNote('${fieldKey}', '${currentStage}', ${itemId})">
          Save & Close
        </button>
      </div>

      <hr class="my-4 border-gray-300 dark:border-gray-700">
      <h4 class="font-semibold text-sm">Riwayat Catatan (${notes.length}):</h4>
      <pre class="bg-gray-100 dark:bg-white text-gray-900 dark:bg-gray-800 dark:text-white p-2 rounded text-xs whitespace-pre-wrap max-h-60 overflow-y-auto text-gray-800 dark:text-gray-100">
        ${currentText || 'Belum ada catatan.'}
      </pre>
    </div>
  `;

  state.modalOpen = true;
  console.log("✅ openNoteModal - loaded notes:", notes.length);
};

// ✅ 5. Simpan note baru (frontend + backend sync)
window.saveNote = async function(fieldKey, stage, itemId) {
  const root = document.getElementById("claimRoot");
  const state = Alpine.$data(root);
  const textarea = document.getElementById("noteField");
  const val = textarea.value.trim();
  if (!val) {
    state.modalOpen = false;
    return;
  }

  // 🔄 Normalisasi field sebelum dikirim ke backend
  fieldKey = normalizeFieldKey(fieldKey);

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

    // Tambahkan ke local state agar langsung tampil tanpa reload
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    const role = state.role || "User";
    const log = `[${role} ${hh}:${mm}] ${val}`;


    if (!state.notes) state.notes = {};
    if (!state.notes[stage]) state.notes[stage] = {};
    if (!state.notes[stage][fieldKey]) state.notes[stage][fieldKey] = {};
    if (!state.notes[stage][fieldKey][itemId]) state.notes[stage][fieldKey][itemId] = [];
    state.notes[stage][fieldKey][itemId].push(log);

    console.log("✅ Note saved successfully", { stage, fieldKey, itemId });
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
window.renderIdrgPredictionResult = renderIdrgPredictionResult;
window.renderTindakan = renderTindakan;
window.openProcedureModal = openProcedureModal;
window.openManualDetailModal = openManualDetailModal;
window.closeNestedModal = closeNestedModal;
window.openRegulationDetailModal = openRegulationDetailModal;
window.tindakanAutocomplete = tindakanAutocomplete;
window.showConfirmModal = showConfirmModal;
window.addManualTindakanIfNotFound = addManualTindakanIfNotFound;
window.openOverlayModal = openOverlayModal;
window.closeOverlayModal = closeOverlayModal;
window.showAiLoadingModal = showAiLoadingModal;
window.hideAiLoadingModal = hideAiLoadingModal;
window.formatRupiah = formatRupiah;

// ==================================================
// i-DRG PREDICTION HELPER FUNCTIONS
// ==================================================

// Global helper functions for i-DRG predictions
window.getPrediction = function(field) {
  try {
    if (!this || !this.data || !this.data.idrg_prediction) return '-';
    return this.data.idrg_prediction[field] || '-';
  } catch (err) {
    console.error('Error in getPrediction:', err);
    return '-';
  }
};

window.getSeverityLabel = function(index) {
  const severityLabel = {
    "1": "Minor (1)",
    "2": "Moderate (2)",
    "3": "Major (3)",
    "4": "Extreme (4)"
  };
  return severityLabel[index] || index;
};

window.renderChecklistHtml = function(checklist) {
  if (!checklist) return '-';
  
  if (Array.isArray(checklist) && checklist.length > 0) {
    return `<ul class="list-none pl-0">${checklist.map(item => `<li>• ${item}</li>`).join('')}</ul>`;
  } else if (typeof checklist === 'string') {
    return checklist;
  }
  
  return '-';
};

window.renderFaktorSeverityHtml = function(faktor) {
  if (!faktor) return '-';
  
  if (Array.isArray(faktor) && faktor.length > 0) {
    return `<ul class="list-none pl-0">${faktor.map(item => `<li>• ${item}</li>`).join('')}</ul>`;
  } else if (typeof faktor === 'string') {
    return faktor;
  }
  
  return '-';
};

// ==================================================
// i-DRG PREDICTION
// ==================================================

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
      throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
    }
    
    const json = await response.json();
    console.log("[RESP] /predict_idrg (raw)", json);

    // Normalize shape: always return { status:'success', data: { idrg_prediction: {...}, engine_version, diagnosis } }
    let idrgPrediction = null;
    if (json?.data?.idrg_prediction) {
      idrgPrediction = json.data.idrg_prediction;
    } else if (json?.data && (json.data.group_idrg || json.data.severity_index || json.data.checklist_dokumentasi)) {
      // server returned prediction fields directly under data
      idrgPrediction = json.data;
    } else if (json?.idrg_prediction) {
      idrgPrediction = json.idrg_prediction;
    } else {
      // fallback: use whole payload
      idrgPrediction = json.data || json;
    }

    const normalized = {
      status: 'success',
      data: {
        idrg_prediction: idrgPrediction,
        engine_version: json.engine_version || json.data?.engine_version || 'predict_idrg@local',
        diagnosis: json.diagnosis || diagnosisName || ''
      }
    };
    
    // --- Normalisasi: terima beberapa nama field dari backend ---
    // backend kadang mengirim "estimasi_tarif" atau "estimasi_tarif_idrg"
    const p = normalized.data.idrg_prediction || {};
    if (!p.estimasi_tarif_idrg && p.estimasi_tarif) p.estimasi_tarif_idrg = p.estimasi_tarif;
    // juga map gap analysis
    if (!p.gap_analysis && (p.gap_vs_cbg || p.gap)) p.gap_analysis = p.gap_vs_cbg || p.gap;
    // pastikan checklist_dokumentasi adalah array atau cleaned string
    if (p.checklist_dokumentasi && typeof p.checklist_dokumentasi === 'string') {
      // jika string berisi newline, ubah ke array baris bersih
      const lines = p.checklist_dokumentasi.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
      p.checklist_dokumentasi = lines.length > 1 ? lines : p.checklist_dokumentasi;
    }

    console.log("[RESP] /predict_idrg (normalized)", normalized);
    return normalized;
    
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
  if (!faktor) return '';
  
  if (Array.isArray(faktor) && faktor.length > 0) {
    return `<ul class="list-none pl-0">${faktor.map(item => `<li>• ${item}</li>`).join('')}</ul>`;
  } else if (typeof faktor === 'string') {
    return faktor;
  }
  
  return '';
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
          console.log("Hasil Search Tindakan:", res);
          this.results = res.data || [];
          console.log("Results di Alpine:", this.results);
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

function isTindakanFound(ctx, text) {
  return (ctx.results || []).some(
    t =>
      t.procedure_text?.toLowerCase() === text.toLowerCase() ||
      t.nama?.toLowerCase() === text.toLowerCase()
  );
}

// ===================== Confirm Modal =====================
function showConfirmModal(title, message) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "fixed inset-0 bg-black/40 backdrop-blur-sm z-[9998] flex items-center justify-center";

    const modal = document.createElement("div");
    modal.className = "bg-white dark:bg-white text-gray-900 dark:bg-gray-800 dark:text-white p-6 rounded-lg shadow-lg max-w-sm w-full text-center";
    modal.innerHTML = `
      <h2 class="text-lg font-bold mb-3 text-gray-800 dark:text-gray-100">${title}</h2>
      <p class="text-gray-700 dark:text-gray-200 mb-6">${message}</p>
      <div class="flex justify-center gap-4">
        <button id="confirmYes"
          class="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">Tambahkan</button>
        <button id="confirmNo"
          class="px-4 py-2 rounded bg-gray-300 dark:bg-gray-600 text-gray-800 dark:text-gray-100 hover:bg-gray-400 dark:hover:bg-gray-500">Batal</button>
      </div>
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    function cleanup(result) {
      overlay.remove();
      resolve(result);
    }

    modal.querySelector("#confirmYes").addEventListener("click", () => cleanup(true));
    modal.querySelector("#confirmNo").addEventListener("click", () => cleanup(false));
    overlay.addEventListener("keydown", (e) => e.key === "Escape" && cleanup(false));
  });
}

// 👉 export fungsi ini biar bisa dipakai di file lain
if (typeof module !== "undefined" && module.exports) {
  module.exports = { showConfirmModal };
} else {
  // kalau environment kamu belum pakai module bundler, simpan di namespace kecil
  const ns = window.AIClaim = window.AIClaim || {};
  ns.showConfirmModal = showConfirmModal;
}


// animasi lembut biar konsisten sama modal lain
const style = document.createElement("style");
style.innerHTML = `
@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in-up {
  animation: fade-in-up 0.25s ease-out;
}
`;

document.head.appendChild(style);

  // 🔹 fungsi utama — dipanggil dari tombol + atau Enter
  async function addManualTindakanIfNotFound() {
    try {
      // cari context Alpine (komponen tindakanAutocomplete aktif)
      const root = document.querySelector('[x-data*="tindakanAutocomplete()"]');
      const ctx = root ? Alpine.$data(root) : null;
      if (!ctx) {
        console.warn("⚠️ addManualTindakanIfNotFound: konteks Alpine tidak ditemukan");
        return;
      }

      const text = ctx.query?.trim?.();
      if (!text) return;

      // panggil fungsi helper di atas
      const found = isTindakanFound(ctx, text);

      if (!found) {
        const confirmAdd = await showConfirmModal(
          "Tindakan tidak ditemukan",
          `Tindakan "${text}" tidak ditemukan di database.<br>Tambahkan sebagai input manual baru?`
        );
        if (!confirmAdd) return;


        if (typeof addManualTindakanFromAutocomplete === "function") {
          await addManualTindakanFromAutocomplete(
            window.claimState?.tab || "admission",
            { procedure_text: text, isManual: true }
          );
        }

        ctx.query = "";
        ctx.results = [];
      }
    } catch (err) {
      console.error("❌ Gagal addManualTindakanIfNotFound:", err);
    }
  }

// Helper functions for iDRG prediction display
window.getPrediction = function(field) {
  try {
    if (!this || !this.data || !this.data.idrg_prediction)
      return '-';
    return this.data.idrg_prediction[field] || '-';
  } catch (err) {
    console.error('Error in getPrediction:', err);
    return '-';
  }
};

window.getSeverityLabel = function(index) {
  const severityLabel = {
    "1": "Minor (1)",
    "2": "Moderate (2)",
    "3": "Major (3)",
    "4": "Extreme (4)"
  };
  return severityLabel[index] || index;
};

window.renderChecklistHtml = function(checklist) {
  if (!checklist) return '-';
  
  if (Array.isArray(checklist) && checklist.length > 0) {
    return `<ul class="list-none pl-0">${checklist.map(item => `<li>• ${item}</li>`).join('')}</ul>`;
  } else if (typeof checklist === 'string') {
    return checklist;
  }
  
  return '-';
};

window.renderFaktorSeverityHtml = function(faktor) {
  if (!faktor) return '-';
  
  if (Array.isArray(faktor) && faktor.length > 0) {
    return `<ul class="list-none pl-0">${faktor.map(item => `<li>• ${item}</li>`).join('')}</ul>`;
  } else if (typeof faktor === 'string') {
    return faktor;
  }
  
  return '-';
};

// ===============================================================================================
// 🔍 VERIFICATOR READ-ONLY MODAL FUNCTIONS (USING DATABASE ENDPOINTS)
// ===============================================================================================

/**
 * 🔍 Main function to show stored diagnosis modal for verificator
 * Uses database endpoints instead of core_engine
 */
window.showStoredDiagnosisModalVerificator = async function(diagnosisName) {
  if (!diagnosisName) {
    alert('❌ Nama diagnosis tidak ditemukan');
    return;
  }

  console.log('🔍 [VERIFICATOR] Loading stored diagnosis data for:', diagnosisName);
  
  try {
    const claimId = document.querySelector('[data-claim-id]')?.getAttribute('data-claim-id');
    if (!claimId) {
      throw new Error('Claim ID tidak ditemukan');
    }

    // tampilkan loading langsung di kontainer
    const container = document.getElementById("modalContainer");
    if (container) {
      container.classList.remove("hidden");
      container.innerHTML = `
        <div class="modal-content p-6 text-center bg-white dark:bg-slate-800 rounded-xl shadow-lg">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p class="mt-2 text-gray-600 dark:text-gray-400">Memuat data diagnosis...</p>
        </div>
      `;
    }

    
    const response = await fetch(`/claims/${claimId}/stored-diagnosis-detail/${encodeURIComponent(diagnosisName)}`, {
      method: 'GET',
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log('✅ [VERIFICATOR] Stored diagnosis data loaded:', data);
    
    // Update modal with actual content
    openModal(
      `<div class="flex items-center">
        <span class="text-lg font-bold">🔍 Detail Diagnosis: ${diagnosisName}</span>
        <span class="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">READ-ONLY</span>
      </div>`,
      renderDiagnosisDetailReadOnly(data),
      { hideDefaultClose: false }
    );
    
    // Store current diagnosis for nested modals
    window.claimState.currentDiagnosis = data;
    
  } catch (error) {
    console.error('❌ [VERIFICATOR] Failed to load stored diagnosis data:', error);
    openModal(
      `🔍 Detail Diagnosis: ${diagnosisName}`,
      `<div class="text-center py-8 text-red-500">
        <p>❌ Gagal memuat data diagnosis</p>
        <p class="text-sm mt-2">${error.message}</p>
      </div>`,
      { hideDefaultClose: false }
    );
  }
};

/**
 * 🔧 Main function to show stored procedure modal for verificator  
 * Uses database endpoints instead of core_engine
 */
window.showStoredProcedureModalVerificator = async function(procedureName) {
  if (!procedureName) {
    alert('❌ Nama tindakan tidak ditemukan');
    return;
  }

  console.log('🔧 [VERIFICATOR] Loading stored procedure data for:', procedureName);
  
  try {
    const claimId = document.querySelector('[data-claim-id]')?.getAttribute('data-claim-id');
    if (!claimId) {
      throw new Error('Claim ID tidak ditemukan');
    }

    // tampilkan loading langsung di kontainer
    const container = document.getElementById("modalContainer");
    if (container) {
      container.classList.remove("hidden");
      container.innerHTML = `
        <div class="modal-content p-6 text-center bg-white dark:bg-slate-800 rounded-xl shadow-lg">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p class="mt-2 text-gray-600 dark:text-gray-400">Memuat data diagnosis...</p>
        </div>
      `;
    }

    
    const response = await fetch(`/claims/${claimId}/stored-procedure-detail/${encodeURIComponent(procedureName)}`, {
      method: 'GET',
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log('✅ [VERIFICATOR] Stored procedure data loaded:', data);
    
    // Update modal with actual content
    openModal(
      `<div class="flex items-center">
        <span class="text-lg font-bold">🔧 Detail Tindakan: ${procedureName}</span>
        <span class="ml-2 px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">READ-ONLY</span>
      </div>`,
      renderProcedureDetailReadOnly(data),
      { hideDefaultClose: false }
    );
    
    // Store current procedure for nested modals
    window.claimState.currentProcedure = data;
    
  } catch (error) {
    console.error('❌ [VERIFICATOR] Failed to load stored procedure data:', error);
    openModal(
      `🔧 Detail Tindakan: ${procedureName}`,
      `<div class="text-center py-8 text-red-500">
        <p>❌ Gagal memuat data tindakan</p>
        <p class="text-sm mt-2">${error.message}</p>
      </div>`,
      { hideDefaultClose: false }
    );
  }
};

/**
 * 📋 Function to show stored regulation modal for verificator
 * Uses database endpoints instead of core_engine  
 */
window.showStoredRegulationModalVerificator = async function(fieldName, context = 'general') {
  if (!fieldName) {
    alert('❌ Field name tidak ditemukan');
    return;
  }

  console.log('📋 [VERIFICATOR] Loading stored regulation data for:', fieldName);
  
  try {
    const claimId = document.querySelector('[data-claim-id]')?.getAttribute('data-claim-id');
    if (!claimId) {
      throw new Error('Claim ID tidak ditemukan');
    }

    // Show loading modal  
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
      method: 'GET',
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log('✅ [VERIFICATOR] Stored regulation data loaded:', data);
    
    // Update modal with actual content
    openModal(
      `<div class="flex items-center">
        <span class="text-lg font-bold">📋 Detail Regulasi: ${fieldName}</span>
        <span class="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs">READ-ONLY</span>
      </div>`,
      renderRegulationDetailReadOnly(data),
      { hideDefaultClose: false }
    );
    
  } catch (error) {
    console.error('❌ [VERIFICATOR] Failed to load stored regulation data:', error);
    openModal(
      `📋 Detail Regulasi: ${fieldName}`,
      `<div class="text-center py-8 text-red-500">
        <p>❌ Gagal memuat data regulasi</p>
        <p class="text-sm mt-2">${error.message}</p>
      </div>`,
      { hideDefaultClose: false }
    );
  }
};

/**
 * 🎨 Render diagnosis detail in read-only mode for verificator
 * Same UI as doctor but with read-only styling and database data
 */
function renderDiagnosisDetailReadOnly(data) {
  console.log("📋 [VERIFICATOR] renderDiagnosisDetailReadOnly received data:", data);

  const detail = data.data || {};
  const klinis = detail.klinis || {};
  const icd10 = detail.icd10 || {};
  const faskes = detail.faskes || {};
  const rawat = detail.rawat_inap || {};
  const rujukan = detail.rujukan || {};
  const inacbg = detail.inaCbg || {};
  const idrg = detail.idrg_prediction || {};
  const regulasi = detail.regulasi || [];

  // reusable field renderer
  const fieldRow = (label, value, fieldName = null, context = "diagnosis", diagnosisId = null) => {
    const safeValue = value && value !== "" ? value : "-";

    // aktifkan klik kalau field punya regulasi
    const isClickable =
      fieldName && checkFieldHasRegulation(fieldName) && safeValue !== "-";

    const clickableSpan = isClickable
      ? `<span class="cursor-pointer hover:underline hover:text-blue-600"
                title="📋 Klik untuk melihat regulasi ${fieldName}"
                data-field="${fieldName}"
                data-diagnosis-id="${diagnosisId || ''}"
                onclick="window.showStoredRegulationModalVerificator('${fieldName}', '${context}')">${safeValue}</span>`
      : safeValue;

    return `
      <div class="grid grid-cols-2 border-b border-gray-200 dark:border-gray-700">
        <div class="bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-200 px-3 py-2 font-medium">${label}</div>
        <div class="bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-2 border-l border-gray-100 dark:border-gray-600">
          ${clickableSpan}
        </div>
      </div>
    `;
  };


  const section = (title, rows, color = "blue") => `
    <section class="rounded-lg shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div class="px-4 py-2 font-bold text-white bg-gradient-to-r from-${color}-600 to-${color}-500">${title}</div>
      <div class="bg-white dark:bg-gray-800">${rows}</div>
    </section>
  `;

  const infoBox = (text, icon = "👁️") => `
    <div class="flex items-start gap-2 bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200 border-l-4 border-blue-400 p-3 rounded mb-3">
      <span class="text-lg">${icon}</span>
      <div class="text-sm leading-snug">${text}</div>
    </div>
  `;

  return `
    <div class="space-y-6 text-sm bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-100">
      <!-- Header -->
      <div class="bg-blue-50 dark:bg-blue-900/30 p-4 rounded-lg border-l-4 border-blue-500">
        <div class="flex items-center">
          <span class="text-blue-600 dark:text-blue-300 text-lg mr-2">👁️</span>
          <div>
            <h4 class="font-semibold text-blue-900 dark:text-blue-200">Mode Read-Only Verifikator</h4>
            <p class="text-blue-800 dark:text-blue-400 text-xs">Data ini ditampilkan persis seperti hasil analisis dokter.</p>
          </div>
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

      ${idrg && Object.keys(idrg).length > 0 ? section("i-DRG", `
        ${fieldRow("Group IDRG", idrg.group_idrg)}
        ${fieldRow("Severity Index", idrg.severity_index)}
        ${fieldRow("Estimasi Tarif", idrg.estimasi_tarif)}
        ${fieldRow("Gap Analysis", idrg.gap_analysis)}
        ${fieldRow("Checklist", (idrg.checklist || []).join("<br>"))}
        ${fieldRow("Faktor Severity", (idrg.faktor_severity || []).join("<br>"))}
      `) : ""}

      ${regulasi && regulasi.length > 0 ? section("REGULASI TERKAIT", `
        ${regulasi.map(r => `
          <div class="p-2 border-b border-gray-200 dark:border-gray-700">
            <div class="font-semibold text-yellow-700 dark:text-yellow-300">${r.judul}</div>
            <div class="text-xs text-gray-700 dark:text-gray-400">${r.isi || "-"}</div>
            <div class="text-xs text-gray-500 dark:text-gray-500">${r.dasar_hukum || ""} ${r.bab_pasal || ""}</div>
          </div>
        `).join("")}
      `, "yellow") : ""}
    </div>
  `;
}


/**
 * 🎨 Render procedure detail in read-only mode for verificator
 */
function renderProcedureDetailReadOnly(data) {
  const procedureName = data.procedure_text || data.name || "";
  // Use both procedure_detail and analysis (backward compatibility)
  const detail = data.procedure_detail || {};
  const analysis = data.analysis || {};
  const regulasi = data.regulasi || [];

  // ✅ PATCH: kalau procedure_detail kosong tapi field langsung di root, ambil dari root
  if (Object.keys(detail).length === 0 && (data.icd9_code || data.validitas || data.status_tindakan)) {
    console.log("🩹 [PATCH] Flattened procedure data detected, using root-level fields for read-only view");
    Object.assign(detail, data);
  }

  
  console.log("🔧 [VERIFICATOR] renderProcedureDetailReadOnly received:", data);
  
  const renderProcBoxReadOnly = (label, value, fieldName = null) => {
    const safeValue = value || "-";
    
    let content = safeValue;
    if (fieldName && checkFieldHasRegulation(fieldName) && safeValue !== "-") {
      content = `<span class="cursor-pointer hover:underline hover:text-blue-600" 
                  title="📋 Klik untuk melihat regulasi ${fieldName}" 
                  onclick="window.showStoredRegulationModalVerificator('${fieldName}', 'procedure')">${safeValue}</span>`;
    }

    return `
      <div class="flex flex-col rounded-lg overflow-hidden shadow-sm 
                  bg-white text-slate-900 dark:bg-slate-800 dark:text-slate-100 
                  ring-1 ring-gray-100 dark:ring-slate-700">
        <div class="px-3 py-2 font-medium 
                    bg-gray-50 text-slate-700 dark:bg-slate-700 dark:text-slate-200">
          ${label}
        </div>
        <div class="px-3 py-2">${content}</div>
      </div>
    `;

  };

  return `
    <div class="space-y-6 text-sm">
      <!-- Read-Only Notice -->
      <div class="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg border-l-4 border-green-500">
        <div class="flex items-center">
          <span class="text-green-600 text-lg mr-2">👁️</span>
          <div>
            <h4 class="font-semibold text-green-900 dark:text-green-300">Mode Read-Only Verificator</h4>
            <p class="text-green-800 dark:text-green-400 text-sm">Data ini telah disimpan oleh doctor dan hanya bisa dilihat oleh verificator</p>
          </div>
        </div>
      </div>

      <!-- Basic Info -->
      <div class="grid grid-cols-2 gap-3 text-sm bg-transparent dark:bg-transparent">
        ${renderProcBoxReadOnly("Kode ICD-9", analysis.icd9_code || detail.icd9_code, "icd9_code")}
        ${renderProcBoxReadOnly("Deskripsi", procedureName, "icd9_desc")}
        ${renderProcBoxReadOnly("Validitas", analysis.validitas || detail.validitas, "validitas")}
        ${renderProcBoxReadOnly("Status", analysis.status_tindakan || detail.status_tindakan, "status")}
        ${renderProcBoxReadOnly("Tarif INA-CBG", analysis.ina_cbg || detail.ina_cbg, "ina_cbg")}
        ${renderProcBoxReadOnly("Faskes", analysis.faskes_tindakan || detail.faskes_tindakan, "faskes")}
        ${renderProcBoxReadOnly("Rawat Inap", analysis.rawat_inap_tindakan || detail.rawat_inap_tindakan, "rawat_inap_tindakan")}
        ${renderProcBoxReadOnly("Syarat Klinis", analysis.syarat_klinis || detail.syarat_klinis, "syarat_klinis")}
      </div>
    </div>
  `;
}

/**
 * 🎨 Render regulation detail in read-only mode
 */
function renderRegulationDetailReadOnly(data) {
  const regulations = data.regulations || [];
  const fieldName = data.field_name || "";
  
  if (regulations.length === 0) {
    return `
      <div class="text-center py-8 text-gray-500">
        <p>📋 Belum ada regulasi untuk field: ${fieldName}</p>
        <p class="text-sm mt-2">Sistem menggunakan aturan nasional standar</p>
      </div>
    `;
  }

  // Group by layer and render similar to doctor modal
  const rulesByLayer = {};
  regulations.forEach(rule => {
    if (!rulesByLayer[rule.layer]) {
      rulesByLayer[rule.layer] = [];
    }
    rulesByLayer[rule.layer].push(rule);
  });

  const sortedLayers = Object.keys(rulesByLayer).sort((a, b) => {
    const priorities = { 'permenkes': 1, 'nasional': 2, 'ppk': 3, 'regional': 4, 'rs': 5 };
    return (priorities[a] || 99) - (priorities[b] || 99);
  });

  let html = `
    <div class="space-y-4">
      <!-- Read-Only Notice -->
      <div class="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg border-l-4 border-yellow-500">
        <div class="flex items-center">
          <span class="text-yellow-600 text-lg mr-2">👁️</span>
          <div>
            <h4 class="font-semibold text-yellow-900 dark:text-yellow-300">Mode Read-Only Verificator</h4>
            <p class="text-yellow-800 dark:text-yellow-400 text-sm">Regulasi untuk field: <strong>${fieldName}</strong></p>
          </div>
        </div>
      </div>
  `;

  sortedLayers.forEach(layer => {
    const layerLabel = getLayerLabel(layer);
    const layerColor = getLayerColorClass(layer);
    const rules = rulesByLayer[layer];

    html += `
      <div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        <div class="bg-gray-100 dark:bg-white text-gray-900 dark:bg-gray-800 dark:text-white px-4 py-2">
          <span class="font-semibold">${layerLabel} (${rules.length} aturan)</span>
        </div>
        <div class="space-y-3 p-4">
    `;

    rules.forEach(rule => {
      html += `
        <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3">
          <div class="flex items-center gap-2 mb-2">
            <span class="px-2 py-1 text-xs font-semibold rounded-full ${layerColor}">${layer.toUpperCase()}</span>
            <span class="text-sm font-medium">${rule.field || fieldName}</span>
          </div>
          <div class="text-sm text-gray-800 dark:text-gray-200 mb-2 leading-relaxed">${rule.isi}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400">
            <strong>Sumber:</strong> ${rule.sumber}
          </div>
        </div>
      `;
    });

    html += `</div></div>`;
  });

  html += `</div>`;
  return html;
}

function renderRegulatiListReadOnly(regulations) {
  if (!regulations || regulations.length === 0) {
    return `<div class="italic text-gray-500">Tidak ada regulasi tersimpan</div>`;
  }

  return regulations.map(reg => {
    return `
      <div class="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded border-l-4 border-yellow-500 mb-2 cursor-pointer"
           title="Klik untuk detail regulasi (Read-Only)"
           onclick="window.showStoredRegulationModalVerificator('${reg.field}')">
        <div class="font-medium text-yellow-900 dark:text-yellow-300">${reg.field || 'Field'}</div>
        <div class="text-sm text-yellow-700 dark:text-yellow-400 mt-1">${truncateText(reg.isi || 'Tidak ada detail', 100)}</div>
      </div>
    `;
  }).join("");
}

function renderIdrgSectionReadOnly(idrg_data) {
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

})();