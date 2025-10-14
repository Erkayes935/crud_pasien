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


  function openModal(title, content, options = {}) {
    window.claimState = window.claimState || {};
    window.claimState.modalStack = window.claimState.modalStack || [];

    // pastikan elemen dasar modal tersedia
    let modalContainer = document.getElementById("modalContainer");
    let modalContent = document.querySelector(".modal-content");
    let modalTitle = document.querySelector(".modal-title");

    if (!modalContainer) {
      modalContainer = document.createElement("div");
      modalContainer.id = "modalContainer";
      modalContainer.className =
        "fixed inset-0 bg-black/60 flex items-center justify-center z-50 hidden";
      document.body.appendChild(modalContainer);
    }

    if (!modalContent) {
      modalContent = document.createElement("div");
      modalContent.className =
        "modal-content relative bg-gray-900 text-white p-6 rounded-2xl max-h-[90vh] overflow-y-auto shadow-xl w-[90%] max-w-4xl border border-gray-700";
      modalContainer.appendChild(modalContent);
    }

    if (!modalTitle) {
      modalTitle = document.createElement("div");
      modalTitle.className =
        "modal-title mb-4 text-center text-xl font-bold text-white";
      modalContent.prepend(modalTitle);
    }

    // simpan modal lama ke stack (restore system)
    const oldTitle = modalTitle.innerHTML?.trim();
    const oldHTML = modalContent.innerHTML?.trim();
    if (oldHTML && oldTitle) {
      window.claimState.modalStack.push({ title: oldTitle, content: oldHTML });
      if (window.claimState.modalStack.length > 10)
        window.claimState.modalStack.shift();
    }

    // tampilkan modal container
    modalContainer.classList.remove("hidden");
    modalContainer.classList.add("flex");

    // default close button
    const closeButton = options.hideDefaultClose
      ? ""
      : `<button type="button"
                  class="absolute top-3 right-4 text-white bg-red-500 hover:bg-red-600 px-3 py-1 rounded"
                  onclick="closeNestedModal()">✕</button>`;

    // render title hanya jika disableAutoTitle = false
    if (!options.disableAutoTitle) {
      modalTitle.innerHTML = `
        <div class="relative w-full">
          <h2 class="text-xl font-bold text-center text-white">${title || "(Untitled Modal)"}</h2>
          ${closeButton}
        </div>
      `;
    }

    // isi konten utama — kalau disableAutoTitle true, langsung pakai content-nya aja
    modalContent.innerHTML = options.disableAutoTitle
      ? (content || "<p>Tidak ada konten.</p>")
      : `
        ${modalTitle.outerHTML}
        <div class="modal-body">${content || "<p>Tidak ada konten.</p>"}</div>
      `;

    // animasi fade-in
    modalContent.classList.add("modal-fade-enter");
    setTimeout(() => {
      modalContent.classList.add("modal-fade-enter-active");
      modalContent.classList.remove("modal-fade-enter");
    }, 10);

    window.claimState.modalOpen = true;
    setTimeout(() => Alpine.initTree(modalContent), 10);
  }




  // 🔥 Enhanced openRegulationDetailModal untuk multilayer system
  // =========================
  async function openRegulationDetailModal(fieldName, diagnosisId, procedureId = null) {
    console.log('🏥 Opening multilayer regulation modal for:', fieldName, 'diagnosisId:', diagnosisId, 'procedureId:', procedureId);

    // Ambil claimId dari Alpine state
    const root = document.getElementById('claimRoot');
    const state = root ? Alpine.$data(root) : {};
    const claimId = state?.selectedClaimId || state?.id || 1;

    // 🔥 Extract diagnosis name dari current context
    const diagnosisName = window.claimState?.currentDiagnosisTitle || 
                         window.claimState?.currentDiagnosis?.kategori || 
                         window.claimState?.currentDiagnosis?.name || 
                         'Unknown Diagnosis';

    console.log('🔍 Context extracted:', { 
      claimId, fieldName, diagnosisName, 
      currentDiagnosis: window.claimState?.currentDiagnosis 
    });

    try {
      // 🔹 Enhanced payload dengan diagnosis_name dan context untuk multilayer
      const payload = { 
        claim_id: claimId, 
        field: fieldName,
        diagnosis_name: diagnosisName,
        kategori: diagnosisName,
        rs_id: 'rs_notopuro',  // Default atau ambil dari user context
        region_id: 'jatim'     // Default atau ambil dari user context
      };
      
      // Add item context jika ada
      if (diagnosisId) payload.item_id = diagnosisId;
      if (procedureId) payload.item_id = procedureId;
      
      // Add current value dari field jika ada di DOM
      const currentValue = extractCurrentFieldValue(fieldName);
      if (currentValue) payload.current_value = currentValue;

      const endpoint = `/claims/${claimId}/regulation_detail`;
      console.log('📡 Requesting multilayer regulation from:', endpoint, 'with payload:', payload);

      // 🔹 Request ke backend (POST)
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      const data = await response.json();
      console.log('✅ Multilayer regulation response:', data);

      if (data.error) throw new Error(data.error);

      // � Enhanced render dengan diagnosis context
      const regulationContent = renderMultilayerRegulationModal(data, fieldName, diagnosisName);
      
      // 🎯 Modal title dengan diagnosis context
      const modalTitle = `📘 Regulasi Multilayer: ${fieldName} (${diagnosisName})`;
      openModal(modalTitle, regulationContent, { hideDefaultClose: true, disableAutoTitle: true });
    } catch (error) {
      console.error('❌ Error fetching multilayer regulation detail:', error);
      openModal(
        'Error Regulasi Multilayer',
        `<div class="text-center py-8">
          <div class="bg-red-50 dark:bg-red-900/20 p-6 rounded-lg">
            <p class="text-red-500 mb-2">❌ Gagal memuat detail regulasi multilayer</p>
            <p class="text-xs text-red-400">${error.message}</p>
          </div>
        </div>`,
        { hideDefaultClose: true }
      );
    }
  }

  // 🔧 Helper function untuk extract field value dari DOM
  function extractCurrentFieldValue(fieldName) {
    try {
      // Cari field di modal yang sedang terbuka
      const modalBody = document.querySelector('.modal-body');
      if (!modalBody) return null;

      // Berbagai cara untuk extract value berdasarkan field type
      const selectors = [
        `[data-field="${fieldName}"] .col-value`,
        `[data-field="${fieldName}"] span[title]`,
        `.field-${fieldName} .value`,
        `.${fieldName}-value`,
        `#${fieldName}`
      ];

      for (const selector of selectors) {
        const element = modalBody.querySelector(selector);
        if (element) {
          return element.textContent?.trim() || element.innerText?.trim() || null;
        }
      }

      return null;
    } catch (e) {
      console.warn('⚠️ Could not extract field value for:', fieldName, e);
      return null;
    }
  }


// 🔥 Enhanced Multilayer tab modal renderer (matching showRulesModal UI)
function renderMultilayerRegulationModal(response, fieldName, diagnosisName = '') {
  if (!response || response.status !== 'success' || !response.data || response.data.length === 0) {
    return `<div class="text-center py-8">
      <div class="bg-gray-50 dark:bg-gray-800 p-6 rounded-lg">
        <p class="text-gray-500 dark:text-gray-400 mb-2">📋 Belum ada aturan khusus untuk field: <strong>${fieldName}</strong></p>
        <p class="text-xs text-gray-400 dark:text-gray-500">Sistem akan menggunakan aturan nasional standar</p>
      </div>
    </div>`;
  }

  // Group regulations by layer (same as showRulesModal)
  const rulesByLayer = {};
  const layerPriority = {
    'permenkes': 1,
    'nasional': 2,
    'ppk': 3,
    'regional': 4,
    'rs': 5,
    'bridging': 6,
    'fraud': 7,
    'temporary': 8
  };

  // Group rules by layer
  response.data.forEach(rule => {
    if (!rulesByLayer[rule.layer]) {
      rulesByLayer[rule.layer] = [];
    }
    rulesByLayer[rule.layer].push(rule);
  });

  const sortedLayers = Object.keys(rulesByLayer).sort((a, b) => 
    (layerPriority[a] || 99) - (layerPriority[b] || 99)
  );

  const fieldsCount = 1; // Single field
  const layersCount = sortedLayers.length;

  // 🎯 Build complete modal HTML (matching showRulesModal structure)
  return `
    <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto">
      
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div class="flex flex-col">
            <h3 class="font-bold text-xl text-gray-900 dark:text-gray-100">
              📘 Aturan Multilayer: <span class="text-blue-600">${fieldName}</span>
            </h3>
            ${diagnosisName ? `<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Diagnosis: <span class="text-yellow-600 font-medium">${diagnosisName}</span></p>` : ''}
          </div>
          <button type="button" onclick="closeNestedModal()"
                  class="text-gray-400 hover:text-gray-700 dark:hover:text-white text-2xl font-bold">
            ✕
          </button>
        </div>      <!-- Content -->
      <div class="p-6">
        <!-- Summary (matching showRulesModal) -->
        <div class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg mb-6">
          <h4 class="font-semibold text-blue-900 dark:text-blue-300 mb-2">🎯 Ringkasan Aturan</h4>
          <p class="text-blue-800 dark:text-blue-400 text-sm">
            Ditemukan ${fieldsCount} kategori field dengan ${layersCount} layer aturan aktif
          </p>
        </div>

        <!-- Tabs Navigation (matching showRulesModal) -->
        <div class="border-b border-gray-200 dark:border-gray-700 mb-6">
          <nav class="flex space-x-8" id="regulasiTabsNav">
            ${sortedLayers.map((layer, index) => `
              <button type="button" 
                      class="py-2 px-4 text-sm font-medium border-b-2 ${index === 0 ? 
                        'border-blue-500 text-blue-600' : 
                        'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
                      onclick="switchRegulasiTab('${layer}')"
                      id="regulasi-tab-${layer}">
                ${getLayerLabel(layer)} (${rulesByLayer[layer].length})
              </button>
            `).join('')}
          </nav>
        </div>

        <!-- Tab Content (matching showRulesModal style) -->
        <div id="regulasiTabContent">
          ${sortedLayers.map((layer, index) => `
            <div id="regulasi-content-${layer}" style="display: ${index === 0 ? 'block' : 'none'}">
              ${generateRegulasiLayerContent(layer, rulesByLayer[layer])}
            </div>
          `).join('')}
        </div>
      </div>
    </div>
  `;
}

// Generate layer content (matching showRulesModal generateLayerContent)
function generateRegulasiLayerContent(layer, rules) {
  const isOverride = layer === 'ppk' || layer === 'rs';
  let html = '';
  
  if (isOverride) {
    html += `
      <div class="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded-lg mb-4 border-l-4 border-yellow-500">
        <p class="text-yellow-800 dark:text-yellow-300 text-sm font-medium">
          ⭐ <strong>OVERRIDE PRIORITY:</strong> Aturan layer ini akan menimpa aturan layer di atasnya
        </p>
      </div>
    `;
  }
  
  rules.forEach(rule => {
    const layerColor = getLayerColorClass(layer);
    
    html += `
      <div class="p-4 border border-gray-200 dark:border-gray-700 rounded-lg mb-4">
        <!-- Header -->
        <div class="flex items-center gap-2 mb-3">
          <span class="px-2 py-1 text-xs font-semibold rounded-full ${layerColor}">
            ${getLayerLabel(layer)}
          </span>
          <span class="text-sm font-medium text-gray-900 dark:text-gray-100">
            📋 ${rule.judul_regulasi || rule.field || 'General'}
          </span>
          ${isOverride ? '<span class="px-2 py-1 text-xs font-bold bg-yellow-100 text-yellow-800 rounded-full">⭐ OVERRIDE</span>' : ''}
        </div>
        
        <!-- Meta Information -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-2 mb-3 text-xs text-gray-500 dark:text-gray-400">
          <div><strong>Dasar Hukum:</strong> ${rule.dasar_hukum || '-'}</div>
          <div><strong>Bab/Pasal:</strong> ${rule.bab_pasal || '-'}</div>
          <div><strong>Status:</strong> 
            <span class="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">
              ${rule.status || 'official'}
            </span>
          </div>
          <div><strong>Update:</strong> ${rule.tanggal_update || new Date().toISOString().split('T')[0]}</div>
        </div>
        
        <!-- Content -->
        <div class="text-sm text-gray-800 dark:text-gray-200 mb-3 leading-relaxed">
          ${Array.isArray(rule.isi) ? rule.isi.map(item => `• ${item}`).join('<br>') : rule.isi}
        </div>
        
        <!-- Footer -->
        <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 border-t pt-2">
          <span><strong>Sumber:</strong> ${rule.sumber || '-'}</span>
        </div>
        
        ${rule.pdf_file ? `
          <div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            <a href="/claims/rules/${rule.id}/pdf" target="_blank" 
               class="inline-flex items-center text-blue-600 hover:text-blue-800 text-sm">
              📎 Lihat Dokumen PDF
            </a>
          </div>
        ` : ''}
        
        <div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <button type="button" 
                  onclick="showFeedbackModalForRegulasi(${rule.id || 0}, '${layer}')" 
                  class="inline-flex items-center text-orange-600 hover:text-orange-800 text-sm font-medium">
            💬 Masukan untuk Regulasi Ini
          </button>
        </div>
      </div>
    `;
  });
  
  return html;
}

// =====================================================
// UPDATE RINGKASAN FROM ROW (asli kamu — tidak diubah isinya)
// =====================================================
function updateRingkasanFromRow(itemId, dx) {
  if (!dx || !itemId) return;
  if (dx.isManual) {
    const stage = dx.stage || window.claimState?.tab || "admission";
    window.renderManualTindakanList && window.renderManualTindakanList(stage);
    return;
  }

  console.log("🔍 updateRingkasanFromRow called with:", { itemId, dx });

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
    console.log("🔍 Setting klinis text:", text);
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
    console.log("🔍 Setting ICD code:", icdCode);
    icdCell.innerText = icdCode;
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
    console.log("🔍 Setting tindakan text:", text);
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
        dx = result; // Set dx untuk updateRingkasanFromRow
        window.claimState.currentDiagnosis = result;
        window.claimState.currentDiagnosisTitle = diseaseName;
        
        const modalContent = renderDiagnosisDetail(result);
        openModal(`
          <div class="flex flex-col items-start items-center">
            <span class="text-lg font-bold">Detail Diagnosis</span>
            <span class="font-bold text-2xl mb-2 text-yellow-500">${diseaseName}</span>
          </div>`,
          modalContent,
          { hideDefaultClose: false } // ✅ pastikan default close muncul
        );

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
        openModal(`<div class="flex flex-col items-start items-center">
          <span class="text-lg font-bold">Detail Diagnosis</span>
          <span class="font-bold text-2xl mb-2 text-yellow-500">${window.claimState.currentDiagnosisTitle}</span>
        </div>`, modalContent, { hideDefaultClose: false });
        return;
      }

      let rawText = tr?.querySelector("td")?.innerText.trim() || "-";
      rawText = rawText.replace(/^▶|^▼/, "").trim();
      rawText = rawText.replace(/\s+\d+$/, "");
      const namaPenyakit =
        dx?.kategori || dx?.nama_kategori || dx?.diagnosis || dx?.komorbid || dx?.komplikasi || rawText || "";

      // 🔥 Use new renderDiagnosisDetail for consistent parsing
      const modalContent = renderDiagnosisDetail(dx);
      openModal(`<div class="flex flex-col items-start items-center">
        <span class="text-lg font-bold">Detail Diagnosis</span>
        <span class="font-bold text-2xl mb-2 text-yellow-500">${namaPenyakit}</span>
      </div>`, modalContent, { hideDefaultClose: false });
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
    console.log("📋 it.klinis:", it.klinis);
    console.log("📋 it.icd10:", it.icd10);
    console.log("📋 it.tindakan:", it.tindakan);

    // Fallback for diagnosisId - use available id fields
    const diagnosisId = it.id || it.diagnosis_id || it.itemId || Date.now();
    console.log("📋 Using diagnosisId:", diagnosisId);
    
    // Handle nested structure from core_engine - detailed parsing
    const klinis = {
      justifikasi: it.klinis?.justifikasi || it.justifikasi || "",
      bukti_klinis: it.klinis?.bukti_klinis || it.bukti_klinis || "", 
      syarat_klinis: it.klinis?.syarat_klinis || it.syarat_klinis || "",
      status: it.klinis?.status || it.status || "default"
    };

    const icd10 = {
      kode_icd: it.icd10?.kode_icd || it.icd10_code || "",
      struktur_icd10: it.icd10?.struktur_icd10 || it.struktur_icd10 || "",
      kode_ganda: it.icd10?.kode_ganda || it.kode_ganda || "",
      z_code: it.icd10?.z_code || it.z_code || "",
      kode_bpjs_khusus: it.icd10?.kode_bpjs_khusus || it.kode_bpjs_khusus || "",
      status_icd: it.icd10?.status_icd || it.status_icd || "default"
    };
    
    const tindakan = it.tindakan || [];
    const rawat = it.rawat || it.rawat_inap || {};
    const faskes = it.faskes || {};
    const rujukan = it.rujukan || {};
    const inaCbg = it.inaCbg || it.ina_cbg || {};
    const notifications = it.notifications || {}; // 🔔 notifikasi per section dari core_engine
    console.log("📋 Parsed notifications:", notifications);
    
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

      const hasRegulation = checkFieldHasRegulation(fieldName);

      let content = safeValue;
      if (hasRegulation && diagnosisId && safeValue !== "") {
        content = `<span class="cursor-pointer hover:underline hover:text-blue-600 regulation-field border-b border-dashed border-gray-400 hover:border-blue-600 transition-all duration-200" 
                         title="📋 Klik untuk melihat regulasi ${fieldName}" 
                         data-field="${fieldName}"
                         data-diagnosis-id="${diagnosisId}"
                         @click="openRegulationDetailModal('${fieldName}', ${diagnosisId})">${safeValue}</span>`;
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

    // === 3️⃣ Render keseluruhan modal ===
    return `
      <div class="space-y-6 text-sm">
        <!-- 🩺 KLINIS -->
        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">KLINIS</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderNotificationBox("klinis", notifications)}
            ${(console.log("📋 KLINIS - justifikasi:", klinis.justifikasi, "status:", klinis.status), renderBox("Justifikasi", klinis.justifikasi, klinis.status, diagnosisId, "justifikasi"))}
            ${(console.log("📋 KLINIS - bukti_klinis:", klinis.bukti_klinis), renderBox("Bukti Klinis", klinis.bukti_klinis, null, null, "bukti_klinis"))}
            ${(console.log("📋 KLINIS - syarat_klinis:", klinis.syarat_klinis), renderBox("Syarat Klinis", klinis.syarat_klinis, klinis.status, diagnosisId, "syarat_klinis"))}
          </div>
        </section>

        <!-- 🧾 ICD-10 -->
        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">ICD-10</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderNotificationBox("icd", notifications)}
            ${(console.log("📋 ICD10 - kode_icd:", icd10.kode_icd), renderBox("Kode ICD", icd10.kode_icd, icd10.status_icd, diagnosisId, "kode_icd"))}
            ${renderBox("Struktur ICD 10", icd10.struktur_icd10, icd10.status_icd, diagnosisId, "struktur_icd10")}
            ${renderBox("Kode Ganda", icd10.kode_ganda, icd10.status_icd, diagnosisId, "kode_ganda")}
            ${renderBox("Z-Code", icd10.z_code, icd10.status_icd, diagnosisId, "z_code")}
            ${renderBox("Kode Khusus BPJS", icd10.kode_bpjs_khusus, icd10.status_icd, diagnosisId, "kode_bpjs_khusus")}
          </div>
        </section>

        <!-- 📊 i-DRG -->
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
            ${renderBox("Tarif", inaCbg.tarif ? `Rp ${Number(inaCbg.tarif).toLocaleString('id-ID')}` : "-", inaCbg.status_tarif, diagnosisId, "tarif")}
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
  
  // Check if array
  if (Array.isArray(checklist)) {
    // Look for existing bullet points in each item
    return checklist.map(item => {
      // Remove any existing bullet points (• or - or *)
      const cleanItem = item.replace(/^[•\-*]\s*/, '').trim();
      return `<li>• ${cleanItem}</li>`;
    }).join('');
  }
  
  // If string - don't add bullet points, just return as-is
  return checklist;
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

  function renderIdrgSection(idrg, claimId, diagnosisName = null) {
    // Get claim ID dan diagnosis name dari context jika tidak ada parameter
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
          <div class="bg-gray-700 text-white px-3 py-2">${label}</div>
          <div class="bg-gray-100 text-gray-800 dark:bg-gray-600 dark:text-gray-100 px-3 py-2">${valueHtml}</div>
        </div>
      `;
    }

    // Helper function for rendering existing rows in i-DRG section
    function renderExistingRow(label, value, fieldName = null) {
      let content = value || "-";
  
    // Add link to regulation if this field has one and value exists
    if (fieldName && value && checkFieldHasRegulation(fieldName)) {
      content = `<span class="cursor-pointer hover:underline hover:text-blue-600 regulation-field border-b border-dashed border-gray-400 hover:border-blue-600 transition-all duration-200" 
                    title="📋 Klik untuk melihat regulasi ${fieldName}" 
                    data-field="${fieldName}"
                    onclick="openRegulationDetailModal('${fieldName}', null, 'idrg')">${value}</span>`;
    }
  
    return `
      <div class="grid grid-cols-2">
        <div class="bg-gray-700 text-white px-3 py-2">${label}</div>
        <div class="bg-gray-100 text-gray-800 dark:bg-gray-600 dark:text-gray-100 px-3 py-2">${content}</div>
      </div>
    `;
  }

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
          
          <!-- AI Notification (Added here) -->
          <div x-show="!loading && data && data.status === 'success'" class="p-3 bg-gray-100 dark:bg-gray-700">
            <template x-if="data.data && data.data.idrg_prediction && data.data.idrg_prediction.notifications && data.data.idrg_prediction.notifications.idrg">
              <div 
                :class="{
                  'bg-green-100 border-green-500 text-green-800': data.data.idrg_prediction.notifications.idrg.status === 'success',
                  'bg-yellow-100 border-yellow-500 text-yellow-800': data.data.idrg_prediction.notifications.idrg.status === 'warning',
                  'bg-red-100 border-red-500 text-red-800': data.data.idrg_prediction.notifications.idrg.status === 'error',
                  'bg-blue-100 border-blue-500 text-blue-800': data.data.idrg_prediction.notifications.idrg.status === 'info'
                }"
                class="notification-box border-l-4 p-2 rounded mb-2 text-sm flex items-start gap-2">
                <span class="text-lg" x-text="{
                  'success': '✅',
                  'warning': '⚠️',
                  'error': '❌',
                  'info': 'ℹ️'
                }[data.data.idrg_prediction.notifications.idrg.status] || '🔔'"></span>
                <div>
                  <strong>Notifikasi AI (IDRG)</strong>
                  <div class="text-xs leading-snug mt-0.5" x-text="data.data.idrg_prediction.notifications.idrg.message"></div>
                </div>
              </div>
            </template>
            <div x-show="!(data.data && data.data.idrg_prediction && data.data.idrg_prediction.notifications && data.data.idrg_prediction.notifications.idrg)" class="notification-box bg-gray-100 border-gray-400 text-gray-700 border-l-4 p-2 rounded mb-2 text-sm flex items-start gap-2">
              <span class="text-lg">🔔</span>
              <div>
                <strong>Notifikasi AI (IDRG)</strong>
                <div class="text-xs leading-snug mt-0.5">Belum ada notifikasi untuk bagian IDRG.</div>
              </div>
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
                ${renderPredictionRow("Estimasi Tarif", "<span x-text=\"data.data.idrg_prediction.estimasi_tarif_idrg !== '' ? 'Rp ' + parseInt(data.data.idrg_prediction.estimasi_tarif_idrg).toLocaleString('id-ID') : '-'\"></span>")}
                ${renderPredictionRow("Gap Analysis", "<span x-text=\"data.data.idrg_prediction.gap_analysis ? 'Rp ' + parseInt(data.data.idrg_prediction.gap_analysis).toLocaleString('id-ID') : '-'\"></span>")}
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
            
            ${renderExistingRow("Group i-DRG", idrg.group_idrg || "", "idrg_diagnosis_group")}
            ${renderExistingRow("Severity Index", idrg.severity_index || "", "idrg_diagnosis_severity")}
            ${renderExistingRow("Checklist Dokumentasi", idrg.checklist || "", "idrg_diagnosis_checklist")}
            ${renderExistingRow("Faktor Severity", idrg.faktor_severity || "")}
            ${renderExistingRow("Ungroupable Alert", idrg.ungroupable_alert || "", "idrg_diagnosis_ungroupable")}
            ${renderExistingRow("Simulasi Tarif", idrg.simulasi_tarif || "")}
            ${renderExistingRow("Gap Analysis", idrg.gap_analysis || "")}
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
          <div class="bg-blue-100 dark:bg-blue-800 px-3 py-2 text-gray-900 dark:text-gray-100">${content || ""}</div>
        </div>
      `;
    };
    
    // Render checklist dokumentasi sebagai list jika array
    let checklistHtml = "";
    if (prediction.checklist_dokumentasi && Array.isArray(prediction.checklist_dokumentasi) && 
        prediction.checklist_dokumentasi.length > 0) {
      checklistHtml = prediction.checklist_dokumentasi.map(item => `<li>• ${item}</li>`).join('');
      checklistHtml = `<ul class="list-none pl-0">${checklistHtml}</ul>`;
    } else if (prediction.checklist_dokumentasi) {
      checklistHtml = prediction.checklist_dokumentasi;
    }
    
    // Render faktor severity sebagai list jika array
    let faktorSeverityHtml = "";
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
        ${renderPredictionRow("Kode i-DRG", prediction.group_idrg || "", true)}
        ${renderPredictionRow("Severity Index", severityLabel[prediction.severity_index] || prediction.severity_index || "", true)}
        ${renderPredictionRow("Checklist Dokumentasi", checklistHtml)}
        ${renderPredictionRow("Faktor Penentu Severity", faktorSeverityHtml)}
        ${renderPredictionRow("Ungroupable Alert", prediction.ungroupable_alert || "")}
        ${renderPredictionRow("Estimasi Tarif", prediction.estimasi_tarif_idrg ? `Rp ${parseInt(prediction.estimasi_tarif_idrg).toLocaleString('id-ID')}` : "")}
        ${renderPredictionRow("Gap Analysis", prediction.gap_analysis ? `Rp ${parseInt(prediction.gap_analysis).toLocaleString('id-ID')}` : "")}
      </div>
    `;
  }

  function renderTindakan(list) {
    const tindakanList = (list && list.length > 0)
      ? list.map(td => {
          const nama = td.nama || td.tindakan || "";
          const deskripsi = td.deskripsi || td.description || "";
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
        <div class="relative flex gap-2 mt-2" x-data="tindakanAutocomplete()" x-ref="acWrap">
          <input type="text"
                x-model="query"
                x-ref="acInput"
                @input.debounce.300ms="search"
                @keydown.enter.prevent="results.length ? select(results[0]) : addManualTindakanIfNotFound()"
                placeholder="Nama Tindakan"
                class="flex-1 px-2 py-1 rounded bg-white dark:bg-gray-900
                        text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600">
          <button type="button"
                  class="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded"
                  @click="handleAddManualTindakan(window.claimState.tab)">+</button>

          <template x-if="results.length > 0">
            <template x-teleport="body">
              <ul
                x-init="requestAnimationFrame(() => {
                  const i=$refs.acInput;if(!i)return;
                  const r=i.getBoundingClientRect();
                  Object.assign($el.style,{
                    position:'fixed',
                    top:r.bottom+'px',
                    left:r.left+'px',
                    width:r.width+'px',
                    zIndex:99999
                  });
                });
                window.addEventListener('scroll',()=>{$el.style.top=$refs.acInput.getBoundingClientRect().bottom+'px'},true);
                window.addEventListener('resize',()=>{$el.style.top=$refs.acInput.getBoundingClientRect().bottom+'px'});
                "
                class="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600
                      rounded shadow-lg max-h-56 overflow-y-auto text-sm"
              >
                <template x-for="item in results" :key="item.procedure_text">
                  <li
                    @click="select(item)"
                    class="px-2 py-1 cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700"
                    x-text="item.procedure_text"
                  ></li>
                </template>
              </ul>
            </template>
          </template>

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
    console.log("[RESP] /analyze_procedure", result);

    const d = result.data || result;
      console.log("INA-CBG tarif raw:", d.ina_cbg_tarif, "| ina_cbg:", d.ina_cbg);

    const renderProcBox = (label, value, fieldName = null) => {
      let safeValue = value || "";
      
      // Special handling untuk tarif INA-CBG
      if (fieldName === "ina_cbg" && value && value !== "") {
        console.log("💰 Formatting tarif:", value, typeof value);
        const numericValue = parseInt(value);
        if (!isNaN(numericValue)) {
          safeValue = `Rp ${Number(numericValue).toLocaleString('id-ID')}`;
        } else {
          safeValue = value; // keep original if not numeric
        }
      }

      const hasRegulation = checkFieldHasRegulation(fieldName);
      let content = `<span class="text-white">${safeValue}</span>`;
      if (hasRegulation && fieldName && safeValue !== "") {
        content = `<span class="cursor-pointer hover:underline hover:text-yellow-300 regulation-field text-white border-b border-dashed border-gray-500 hover:border-yellow-300 transition-all duration-200"
                         title="📋 Klik untuk melihat regulasi ${fieldName}"
                         data-field="${fieldName}"
                         data-procedure-id="${procId}"
                         @click="openRegulationDetailModal('${fieldName}', null, '${procId}')">${safeValue}</span>`;
      }

      return `<div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>${label}:</b></div>
              <div class="bg-gray-800 px-3 py-2 rounded text-white">${content}</div>`;
    };

    // 🔔 Ambil notifikasi dari core_engine (atau fallback dummy)
    const notifications = d.notifications || {
      tindakan: { status: "info", message: "Analisis AI: tindakan ini memerlukan verifikasi tambahan." }
    };

    console.log("📋 Notifications (procedure):", notifications);

    // 🔹 Tambahkan notifikasi di atas semua detail tindakan
    const content = `
      <div class="relative mb-4 text-center">
        <h3 class="text-xl font-bold text-yellow-500">Detail Tindakan: ${procedureName}</h3>
        <button type="button"
                onclick="closeNestedModal()"
                class="absolute top-0 right-0 text-white bg-red-500 hover:bg-red-600 px-3 py-1 rounded">
          ✕
        </button>
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

    openModal(`Detail Tindakan: ${procedureName}`, content, { hideDefaultClose: true, disableAutoTitle: true });

    // Simpan referensi supaya regulasi tahu asalnya
    window.claimState = window.claimState || {};
    window.claimState.currentProcedure = { id: procId };

    // Update deskripsi list tindakan (instan)
    const itemEl = document.querySelector(`[data-procid='${procId}'] .text-xs`);
    const deskripsiGabungan = d.icd9_desc || d.deskripsi || procedureName;
    if (itemEl) itemEl.textContent = deskripsiGabungan;
  } catch (err) {
    console.error("❌ Gagal load detail tindakan:", err);
  }
}


  async function openManualDetailModal(it, tab, idx) {
    try {
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
        <div class="relative w-full text-center mb-4">
          <div>
            <span class="text-sm font-semibold block">Detail Tindakan Manual</span>
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

      return `<div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>${label}:</b></div>
              <div class="bg-gray-800 px-3 py-2 rounded">${content}</div>`;
    };

    return `
      <div class="grid grid-cols-2 gap-2 text-sm">
        ${renderProcBox("Kode ICD-9", d.icd9)}
        ${renderProcBox("Deskripsi", d.deskripsi || deskripsi)}
        ${renderProcBox("Validitas", d.validitas, true)}
        ${renderProcBox("Status", d.status)}
        ${renderProcBox("INA-CBG", d.ina_cbg)}
        ${renderProcBox("Faskes", d.faskes)}
        ${renderProcBox("Rawat Inap", d.rawat_inap)}
        ${renderProcBox("Syarat Klinis", d.syarat_klinis)}
      </div>
    `;
  }

  // ===================== CLOSE NESTED MODAL (aman + restore) =====================
  function closeNestedModal() {
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
        "modal-content bg-gray-900 text-white p-4 rounded-lg max-h-[90vh] overflow-y-auto shadow-lg w-[90%] max-w-4xl";
      modalContainer.appendChild(modalContent);
    }
    if (!modalTitle) {
      modalTitle = document.createElement("div");
      modalTitle.className = "modal-title font-bold text-lg mb-2";
      modalContent.prepend(modalTitle);
    }

    // 🪄 Animasi fade-out
    modalContent.classList.add("modal-fade-exit");
    setTimeout(() => modalContent.classList.add("modal-fade-exit-active"), 10);

    setTimeout(() => {
      modalContent.classList.remove("modal-fade-exit", "modal-fade-exit-active");

      if (stack.length > 0) {
        // restore modal sebelumnya
        const prev = stack.pop();
        console.log("🧩 restore modal:", prev);

        modalTitle.innerHTML = prev.title || "(Untitled)";
        modalContent.innerHTML = prev.content || "<p>Tidak ada konten sebelumnya</p>";

        setTimeout(() => {
          Alpine.initTree(modalContent);
          if (typeof window.renderManualTindakanList === "function") {
            const tab = window.claimState?.tab || "admission";
            window.renderManualTindakanList(tab);
          }
        }, 50);
      } else {
        // tutup total
        modalContainer.classList.add("hidden");
        window.claimState.modalOpen = false;
        modalContent.innerHTML = "";
        modalTitle.innerHTML = "";
      }
    }, 250); // durasi sinkron dengan CSS transition
  }




  // === Tutup Regulasi (Balik ke modal asal) ===
  // ===================== CLOSE REGULATION MODAL (context-aware) =====================
  function closeRegulationModal() {
    const source = window.claimState?.regulationSource || {};
    console.log("🔻 closeRegulationModal triggered with source:", source);

    if (source.type === "procedure" && window.claimState?.currentProcedure) {
      openProcedureModal(window.claimState.currentProcedure.id);
    } else if (source.type?.startsWith("idrg_diagnosis")) {
      closeNestedModal();
    } else if (source.type?.startsWith("idrg_summary")) {
      const state = Alpine.$data(document.getElementById('claimRoot'));
      state.modalOpen = false;
    } else {
      closeNestedModal();
    }

    window.claimState.regulationSource = null; // reset context
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
  window.renderTindakan = renderTindakan;
  window.openProcedureModal = openProcedureModal;
  window.openManualDetailModal = openManualDetailModal;
  window.closeNestedModal = closeNestedModal;
  window.openRegulationDetailModal = openRegulationDetailModal;
  window.closeRegulationModal = closeRegulationModal;
  window.tindakanAutocomplete = tindakanAutocomplete;
  window.showConfirmModal = showConfirmModal;
  window.addManualTindakanIfNotFound = addManualTindakanIfNotFound;

  // ================= Note Modal (Diagnosis / Tindakan) =================
// ======================== SISTEM NOTES FINAL STABIL (MERGED FOR VERSION B) ========================

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
    "1": "Minor (Level 1)",
    "2": "Moderate (Level 2)", 
    "3": "Major (Level 3)",
    "4": "Extreme (Level 4)"
  };
  return severityLabel[index] || index || "-";
};

window.renderChecklistHtml = function(checklist) {
  if (!checklist) return '-';
  if (Array.isArray(checklist)) {
    return checklist.map(item => `<li>• ${item}</li>`).join('');
  }
  return checklist;
};

window.renderFaktorSeverityHtml = function(faktor) {
  if (!faktor) return '-';
  if (Array.isArray(faktor)) {
    return faktor.map(item => `<li>• ${item}</li>`).join('');
  }
  return faktor;
};

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
      throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
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
  if (!faktor) return '';
  
  if (Array.isArray(faktor) && faktor.length > 0) {
    return `<ul class="list-none pl-0">${faktor.map(item => `<li>• ${item}</li>`).join('')}</ul>`;
  } else if (typeof faktor === 'string') {
    return faktor;
  }
  
  return '';
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
        <div class="bg-blue-100 dark:bg-blue-800 px-3 py-2 text-gray-900 dark:text-gray-100">${content || ""}</div>
      </div>
    `;
  };
  
  // Render checklist dokumentasi sebagai list jika array
  let checklistHtml = "";
  if (prediction.checklist_dokumentasi && Array.isArray(prediction.checklist_dokumentasi) && 
      prediction.checklist_dokumentasi.length > 0) {
    checklistHtml = prediction.checklist_dokumentasi.map(item => `<li>• ${item}</li>`).join('');
    checklistHtml = `<ul class="list-none pl-0">${checklistHtml}</ul>`;
  } else if (prediction.checklist_dokumentasi) {
    checklistHtml = prediction.checklist_dokumentasi;
  }
  
  // Render faktor severity sebagai list jika array
  let faktorSeverityHtml = "";
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
      ${renderPredictionRow("Kode i-DRG", prediction.group_idrg || "", true)}
      ${renderPredictionRow("Severity Index", severityLabel[prediction.severity_index] || prediction.severity_index || "", true)}
      ${renderPredictionRow("Checklist Dokumentasi", checklistHtml)}
      ${renderPredictionRow("Faktor Penentu Severity", faktorSeverityHtml)}
      ${renderPredictionRow("Ungroupable Alert", prediction.ungroupable_alert || "")}
      ${renderPredictionRow("Estimasi Tarif", prediction.estimasi_tarif_idrg ? `Rp ${parseInt(prediction.estimasi_tarif_idrg).toLocaleString('id-ID')}` : "")}
      ${renderPredictionRow("Gap Analysis", prediction.gap_analysis !== undefined ? `${prediction.gap_analysis}` : "")}
      
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

// ========== REUSABLE UI KONFIRMASI (tidak pakai window.) ==========
async function showConfirmModal(title, message) {
  return new Promise((resolve) => {
    const old = document.getElementById("confirmModal");
    if (old) old.remove();

    const modal = document.createElement("div");
    modal.id = "confirmModal";
    modal.className =
      "fixed inset-0 flex items-center justify-center bg-black/60 z-[9999]";

    modal.innerHTML = `
      <div class="bg-gray-900 text-white rounded-xl shadow-xl p-6 w-[90%] max-w-md text-center border border-gray-700 animate-fade-in-up">
        <h3 class="text-lg font-semibold mb-3">${title}</h3>
        <p class="text-sm text-gray-300 mb-6">${message}</p>
        <div class="flex justify-center space-x-4">
          <button id="confirmNo"
                  class="px-4 py-2 rounded bg-gray-600 hover:bg-gray-700 text-white">
            Batal
          </button>
          <button id="confirmYes"
                  class="px-4 py-2 rounded bg-green-600 hover:bg-green-700 text-white">
            Tambahkan
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.querySelector("#confirmNo").onclick = () => {
      modal.remove();
      resolve(false);
    };
    modal.querySelector("#confirmYes").onclick = () => {
      modal.remove();
      resolve(true);
    };
  });
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

// 🔥 Global function untuk switch tab multilayer regulation modal
window.switchRegulasiTab = function(activeLayer) {
  // Update tab buttons
  document.querySelectorAll('#regulasiTabsNav button').forEach(btn => {
    btn.className = btn.id === `regulasi-tab-${activeLayer}` ?
      'py-2 px-4 text-sm font-medium border-b-2 border-blue-500 text-blue-600' :
      'py-2 px-4 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300';
  });
  
  // Update content
  document.querySelectorAll('#regulasiTabContent > div').forEach(content => {
    content.style.display = content.id === `regulasi-content-${activeLayer}` ? 'block' : 'none';
  });
};

})();
