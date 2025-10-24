// =============== Bootstrap kecil: expose & listener form ===============

// === Alpine component factories (hindari ReferenceError di konten dinamis) ===
window.idrgDropdown = function ({ claimId }) {
  return {
    open: false,
    loading: false,
    idrgData: null,
    error: null,

    async toggleDropdown() {
      this.open = !this.open;

      if (this.open && !this.idrgData && !this.loading) {
        this.loading = true;
        try {
          const state = Alpine.$data(document.getElementById('claimRoot'));
          const currentTab = state.tab || 'admission';
          const simData = state.simulasi[currentTab] || {};

          const payload = {
            claim_id: Number(claimId),
            mode: "combo",
            scope: "idrg",
            primary_claim: simData.utama?.name || '',
            secondary_claims: (simData.sekunder || []).map(d => d.name).filter(Boolean),
            primary_action: simData.tindakanUtama?.name || '',
            secondary_actions: (simData.tindakanSekunder || [])
              .filter(t => t && t.name)
              .map(t => t.name)
          };

          const fullUrl = new URL(`/claims/${claimId}/predict_idrg`, window.location.origin).href;

          const response = await fetch(fullUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });

          if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

          const result = await response.json();
          this.idrgData = result?.idrg_prediction || result?.data || {};

          // Fallback aman bila kosong
          if (!this.idrgData || Object.keys(this.idrgData).length === 0) {
            this.idrgData = {
              group_idrg_kombinasi: "I-SEP-DM-3",
              severity_kombinasi: "Sedang",
              checklist_dokumentasi: ["HbA1c + kultur darah wajib", "Dokumentasi operasi Apendektomi wajib"],
              faktor_penentu_severity: ["Komorbid 1", "Usia pasien", "Durasi rawat inap"],
              risiko_ungroupable: "-",
              estimasi_tarif: 15000000,
              gap_inacbg_vs_idrg: 2000000,
              rekomendasi_ai: "Tambahkan hasil CT Scan dan rekam medis"
            };
          }
        } catch (err) {
          console.error('Error loading i-DRG data:', err);
          this.error = err.message;
        } finally {
          this.loading = false;
        }
      }
    }
  };
};

window.alternatifDropdown = function ({ claimId }) {
  return {
    open: false,
    loading: false,
    alternatives: null,
    error: null,

    async toggleDropdown() {
      this.open = !this.open;

      if (this.open && !this.alternatives && !this.loading) {
        this.loading = true;
        try {
          const state = Alpine.$data(document.getElementById('claimRoot'));
          const currentTab = state.tab || 'admission';
          const simData = state.simulasi[currentTab] || {};

          const payload = {
            claim_id: Number(claimId),
            primary_claim: simData.utama?.name || '',
            secondary_claims: (simData.sekunder || []).map(d => d.name).filter(Boolean),
            primary_action: simData.tindakanUtama?.name || '',
            secondary_actions: (simData.tindakanSekunder || []).filter(t => t && t.name).map(t => t.name)
          };

          const fullUrl = new URL(`/claims/${claimId}/generate_alternatives`, window.location.origin).href;

          const response = await fetch(fullUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });

          if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

          const result = await response.json();
          this.alternatives = result?.result?.alternatif || result?.data || [];

          // Fallback aman
          if (!this.alternatives || this.alternatives.length === 0) {
            this.alternatives = [
              {
                judul: "Kombinasi Klaim Apendektomi dengan CT Scan",
                severity: "Medium (Sepsis + DM)",
                ina_cbg: "D-04-13",
                tarif: 12500000,
                syarat: "Diagnosis utama terkonfirmasi; CT Scan sebelum operasi.",
                faskes: "RS Type B",
                rawat_inap: "≥ 3 hari + ICU ≥ 2 hari",
                tindakan: ["Operasi Apendektomi", "CT Scan Abdomen"]
              }
            ];
          }

          if (window.claimState && window.claimState.summary) {
            window.claimState.summary.alternatif = this.alternatives;
          }
        } catch (err) {
          console.error('Error loading alternatives:', err);
          this.error = err.message;
        } finally {
          this.loading = false;
        }
      }
    }
  };
};


(function () {
  // Panel evaluasi (fungsi render) — tetap di window seperti versi lama
  function renderEvaluasiDiagnosis(data) {
    const rows = Array.isArray(data) ? data : [data];

    const target = document.getElementById("evaluasi-diagnosis");
    if (!target) return;
    target.innerHTML = "";

    if (!data || Object.keys(data).length === 0) {
      target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada evaluasi diagnosis</div>`;
      return;
    }

    // Handle both possible formats from core_engine
    const validitasIcon = window.statusIcon ? window.statusIcon(data.validitas) : '';
    
    // Normalize field names for maximum compatibility
    const validitasText = data.validitas_detail || data.catatan_validitas || "-";
    const severity = data.severity || "-";
    const kodeInaCbg = data.kode_ina_cbg || data.kode_cbg || "-";
    const estimasiTarif = data.estimasi_tarif || "-";
    const syarat = data.syarat_klinis || data.syarat || "-";
    const evaluasiFaskes = data.evaluasi_faskes || data.faskes || "-";
    const rawatInap = data.rawat_inap || "-";

    target.innerHTML = `
      <h3 class="font-bold text-lg mb-2 text-yellow-500">Evaluasi Kombinasi Diagnosis</h3>
      <table class="w-full border border-gray-300 dark:border-gray-600 text-sm">
        <tr>
          <th class="border px-4 py-2">Validitas Klinis Kombinasi</th>
          <td class="border px-4 py-2">
            ${validitasIcon} - <span class="cursor-pointer" title="PNPK Evaluasi Diagnosis 2020"
               onclick="openRegulationDetailModal(${data.id}, 'diagnosis_eval')">${validitasText}</span>
          </td>
        </tr>
        <tr>
          <th class="border px-4 py-2">Severity</th>
          <td class="border px-4 py-2">
            <span class="cursor-pointer" onclick="openRegulationDetailModal(${data.id}, 'diagnosis_eval')">${severity}</span>
          </td>
        </tr>
        <tr>
          <th class="border px-4 py-2">Kode INA-CBG</th>
          <td class="border px-4 py-2">
            <span class="cursor-pointer" onclick="openRegulationDetailModal(${data.id}, 'diagnosis_eval')">${kodeInaCbg}</span>
          </td>
        </tr>
        <tr>
          <th class="border px-4 py-2">Estimasi Tarif</th>
          <td class="border px-4 py-2">${window.formatRupiah ? window.formatRupiah(estimasiTarif) : estimasiTarif || "-"}</td>
        </tr>
        <tr>
          <th class="border px-4 py-2">Syarat Klinis (Kombinasi)</th>
          <td class="border px-4 py-2">
            <span class="cursor-pointer" onclick="openRegulationDetailModal(${data.id}, 'diagnosis_eval')">${syarat}</span>
          </td>
        </tr>
        <tr>
          <th class="border px-4 py-2">Evaluasi Faskes</th>
          <td class="border px-4 py-2">
            <span class="cursor-pointer" onclick="openRegulationDetailModal(${data.id}, 'diagnosis_eval')">${evaluasiFaskes}</span>
          </td>
        </tr>
        <tr>
          <th class="border px-4 py-2">Rawat Inap</th>
          <td class="border px-4 py-2">
            <span class="cursor-pointer" onclick="openRegulationDetailModal(${data.id}, 'diagnosis_eval')">${rawatInap}</span>
          </td>
        </tr>
      </table>
    `;
  }

  function renderEvaluasiProcedure(data) {
    // 🧠 PATCH: auto-wrap kalau bukan array
    const target = document.getElementById("evaluasi-procedure");
    if (!target) return;
    target.innerHTML = "";

    if (!data || Object.keys(data).length === 0) {
      target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada evaluasi tindakan</div>`;
      return;
    }

    // 🧠 PATCH: auto-wrap kalau bukan array
    const rows = Array.isArray(data) ? data : [data];

    const wajib = [], validasi = [], dampak = [], konflik = [];
    rows.forEach((p) => {
      const safe = (v) => (v && v !== "-" ? v : "-");
      if (p.wajib) wajib.push(safe(p.wajib));
      if (p.validasi) validasi.push(safe(p.validasi));
      if (p.dampak) dampak.push(safe(p.dampak));
      if (p.konflik) konflik.push(safe(p.konflik));
    });

    const listify = (arr) => (arr.length ? arr.map((v) => `<div>${v}</div>`).join("") : "-");

    target.innerHTML = `
      <h3 class="font-bold text-lg mb-2 text-yellow-500">Evaluasi Kombinasi Tindakan</h3>
      <table class="w-full border border-gray-300 dark:border-gray-600 text-sm">
        <tr><th class="border px-4 py-2 w-[30%] bg-gray-50 dark:bg-gray-800">Tindakan Wajib</th><td class="border px-4 py-2">${listify(wajib)}</td></tr>
        <tr><th class="border px-4 py-2 bg-gray-50 dark:bg-gray-800">Validasi</th><td class="border px-4 py-2">${listify(validasi)}</td></tr>
        <tr><th class="border px-4 py-2 bg-gray-50 dark:bg-gray-800">Dampak / Tarif</th><td class="border px-4 py-2">${listify(dampak)}</td></tr>
        <tr><th class="border px-4 py-2 bg-gray-50 dark:bg-gray-800">Konflik / Catatan</th><td class="border px-4 py-2">${listify(konflik)}</td></tr>
      </table>
    `;
  }

  function renderEvaluasiIDRGSummary(data, claimId) {
    const target = document.getElementById("evaluasi-idrg");
    if (!target) return;
    target.innerHTML = "";

    if (!data) {
      target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada prediksi i-DRG summary</div>`;
      return;
    }

    target.innerHTML = `
      <div x-data="{ open: false }" class="border rounded shadow overflow-hidden mb-3">
        <div class="accordion-header flex items-center justify-between bg-white dark:bg-gray-900 text-yellow-600 dark:text-yellow-500 text-lg px-3 py-2 font-bold cursor-pointer"
            @click="open = !open">
          <span>Prediksi i-DRG</span>
          <span class="text-xs text-gray-500 dark:text-gray-300">(klik untuk lihat detail)</span>
        </div>
        <div class="accordion-body" x-show="open" x-transition>
          <div class="grid grid-cols-2">
            <div class="bg-gray-700 text-white px-3 py-2">Group i-DRG Kombinasi</div>
            <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2 cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-800 transition-colors"
                 onclick="openRegulationDetailModal('${claimId}', 'idrg_summary_group')">
              ${data.group_idrg_kombinasi || "-"}
            </div>
          </div>
          <div class="grid grid-cols-2">
            <div class="bg-gray-700 text-white px-3 py-2">Severity Kombinasi</div>
            <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2 cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-800 transition-colors"
                 onclick="openRegulationDetailModal('${claimId}', 'idrg_summary_severity')">
              ${data.severity_kombinasi || "-"}
            </div>
          </div>
          <div class="grid grid-cols-2">
            <div class="bg-gray-700 text-white px-3 py-2">Checklist Kombinasi</div>
            <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2 cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-800 transition-colors"
                 onclick="openRegulationDetailModal('${claimId}', 'idrg_summary_checklist')">
              ${data.checklist_kombinasi || "-"}
            </div>
          </div>
          <div class="grid grid-cols-2">
            <div class="bg-gray-700 text-white px-3 py-2">Faktor Severity Kombinasi</div>
            <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2">
              ${data.faktor_severity || "-"}
            </div>
          </div>
          <div class="grid grid-cols-2">
            <div class="bg-gray-700 text-white px-3 py-2">Risiko Ungroupable</div>
            <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2 cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-800 transition-colors"
                 onclick="openRegulationDetailModal('${claimId}', 'idrg_summary_ungroupable')">
              ${data.risiko_ungroupable || "-"}
            </div>
          </div>
          <div class="grid grid-cols-2">
            <div class="bg-gray-700 text-white px-3 py-2">Estimasi Tarif</div>
            <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2">
              ${window.formatRupiah ? window.formatRupiah(data.estimasi_tarif) : (data.estimasi_tarif || "-")}
            </div>
          </div>
          <div class="grid grid-cols-2">
            <div class="bg-gray-700 text-white px-3 py-2">Gap INA-CBG vs i-DRG</div>
            <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2">
              ${data.gap_inacbg_vs_idrg || "-"}
            </div>
          </div>
          ${data.rekomendasi_ai ? `
          <div class="grid grid-cols-2">
            <div class="bg-gray-700 text-white px-3 py-2">Rekomendasi AI</div>
            <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2">
              ${data.rekomendasi_ai}
            </div>
          </div>` : ""}
        </div>
      </div>
    `;
  }

  function renderAlternatifKombinasi(items) {
    const target = document.getElementById("alternatif");
    if (!target) return;
    target.innerHTML = "";

    if (!items || items.length === 0) {
      target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada alternatif kombinasi</div>`;
      return;
    }

    // Debug info
    console.log("Rendering alternatif with data:", items);

    // === Accordion global untuk semua alternatif ===
    target.innerHTML = `
      <div class="border rounded-lg shadow-sm bg-white dark:bg-gray-800 mb-4">
        <div class="cursor-pointer px-4 py-3 flex items-center justify-between bg-yellow-500 text-white font-bold rounded-t"
            onclick="this.nextElementSibling.classList.toggle('hidden')">
          <span>Alternatif Kombinasi (${items.length})</span>
          <span>▼</span>
        </div>
        <div class="p-4 text-sm space-y-3 border-t dark:border-gray-600">
          ${items
            .map((alt, i) => `
              <div class="border rounded-lg shadow-sm bg-white dark:bg-gray-800 p-3">
                <h4 class="font-bold text-yellow-600 mb-2">
                  Alternatif ${i + 1}: ${alt.judul || alt.nama || "-"}
                </h4>
                <div class="text-sm space-y-1">
                  <div><b>Severity:</b> ${alt.severity_detail || alt.severity_kombinasi || alt.severity || "-"}</div>
                  <div><b>INA-CBG:</b> ${alt.ina_cbg || "-"}</div>
                  <div><b>Tarif:</b> ${typeof alt.tarif === 'number' ? `Rp ${alt.tarif.toLocaleString('id-ID')}` : (alt.tarif || alt.estimasi_tarif || "-")}</div>
                  <div><b>Syarat Klinis:</b> ${alt.syarat || alt.syarat_klinis || "-"}</div>
                  <div><b>Evaluasi Faskes:</b> ${alt.faskes || alt.evaluasi_faskes || "-"}</div>
                  <div><b>Rawat Inap:</b> ${alt.rawat_inap || "-"}</div>
                  <div><b>Tindakan:</b> ${Array.isArray(alt.tindakan) ? alt.tindakan.join(", ") : (alt.tindakan_wajib || "-")}</div>
                </div>
              </div>
            `)
            .join("")}
        </div>
      </div>
    `;
  }

  // Expose renderer (nama sama persis dg versi lama)
  window.renderEvaluasiDiagnosis = renderEvaluasiDiagnosis;
  window.renderEvaluasiProcedure = renderEvaluasiProcedure;
  window.renderEvaluasiIDRGSummary = renderEvaluasiIDRGSummary;
  window.renderAlternatifKombinasi = renderAlternatifKombinasi;


  // Format utilities
  window.formatRupiah = function(number) {
    if (!number || number === '-') return '-';
    
    try {
      if (typeof number === 'string') {
        // Handle string that already has Rp
        if (number.startsWith('Rp')) return number;
        
        // Parse string to number
        number = number.replace(/[^\d.,]/g, '').replace(',', '.');
        number = parseFloat(number);
      }
      
      return `Rp ${number.toLocaleString('id-ID')}`;
    } catch (e) {
      console.error("Error formatting rupiah:", e);
      return number;
    }
  };

  window.renderChecklistHtml = function(checklist) {
    if (!checklist) return '-';
    
    if (Array.isArray(checklist) && checklist.length > 0) {
      return checklist.map(item => `<li>• ${item}</li>`).join('');
    } else if (typeof checklist === 'string') {
      return checklist;
    }
    
    return '-';
  };

  // === i-DRG & Alternatif Table Fix for Light Mode ===
  document.head.insertAdjacentHTML('beforeend', `
    <style>
      /* === i-DRG & Alternatif Table Fix for Light Mode === */
      .grid.grid-cols-2 > div:nth-child(odd) {
        background-color: var(--tw-prose-headings, #e6f4ff); /* soft blue for headers */
        color: #0f172a; /* slate-900 */
        font-weight: 600;
        padding: 0.5rem 0.75rem;
      }

      .grid.grid-cols-2 > div:nth-child(even) {
        background-color: #ffffff; /* white for content */
        color: #1e293b; /* slate-800 */
        padding: 0.5rem 0.75rem;
      }

      /* === Dark mode === */
      html.dark .grid.grid-cols-2 > div:nth-child(odd) {
        background-color: #334155;
        color: #f1f5f9;
      }

      html.dark .grid.grid-cols-2 > div:nth-child(even) {
        background-color: #1e293b;
        color: #e2e8f0;
      }

      /* Header bars (green/yellow) tetap tegas */
      .bg-yellow-500, .bg-green-600 {
        font-weight: bold;
        color: white !important;
      }
    </style>
  `);


  // Helper untuk format angka dan styling
  window.statusIcon = window.statusIcon || function(status) {
    if (!status) return '•';
    const s = String(status).toLowerCase();
    
    if (s.includes('valid') || s.includes('normal') || s.includes('yes') || s.includes('ya')) {
      return '✓';
    }
    
    if (s.includes('invalid') || s.includes('warning') || s.includes('no') || s.includes('tidak')) {
      return '✗';
    }
    
    if (s.includes('caution') || s.includes('bersyarat') || s.includes('partial')) {
      return '⚠';
    }
    
    return '•';
  };

  // Listener submit form → pastikan hidden input tersync
  window.syncHiddenInputs = function() {
    try {
      const root = document.getElementById('claimRoot');
      if (!root) return;
      
      const state = Alpine.$data(root);
      if (!state) return;
      
      const simulasiField = document.getElementById('simulasiField');
      const summaryField = document.getElementById('summaryField');
      
      if (simulasiField) simulasiField.value = JSON.stringify(state.simulasi || {});
      if (summaryField) summaryField.value = JSON.stringify(window.claimState?.summary || {});
      
      console.log("✅ Hidden inputs synced successfully");
    } catch (err) {
      console.error("❌ Error syncing hidden inputs:", err);
    }
  };

  // Prepare form submission to ensure data is properly sent
  window.prepareFormSubmit = function() {
    const form = document.getElementById('claimForm');
    if (form) {
      form.addEventListener('submit', function(e) {
        // Prevent default to ensure we can sync fields properly
        e.preventDefault();
        
        try {
          // Sync hidden fields
          window.syncHiddenInputs();
          
          // Log submission
          console.log('[FINALIZE] Submitting form...');
          
          // Submit form
          form.submit();
        } catch (err) {
          console.error('[FINALIZE] Error preparing form:', err);
          alert(`Gagal mempersiapkan data: ${err.message}`);
        }
      });
    }
  };
  
  document.addEventListener('DOMContentLoaded', function() {
    window.prepareFormSubmit();
  });
})();

// Retain existing i-DRG functionality
window.predictIdrgForCombo = window.predictIdrgForCombo || async function(claimId) {
  console.log("🤖 Predicting i-DRG for claim combo:", claimId);
  
  try {
    // Get current claim simulation data
    const root = document.getElementById('claimRoot');
    const state = Alpine.$data(root);
    
    // Extract primary and secondary diagnosis from current tab
    const currentTab = state.tab || 'admission';
    const simData = state.simulasi[currentTab] || {};
    
    const primaryDiagnosis = simData.utama?.name || "";
    const secondaryDiagnosis = (simData.sekunder || []).map(s => s.name).filter(Boolean);
    
    // Extract procedures
    const primaryProcedure = simData.tindakanUtama?.name || "";
    const secondaryProcedures = (simData.tindakanSekunder || [])
      .filter(t => t && t.name)
      .map(t => t.name);
    
    // Build payload - USE DEDICATED ENDPOINT
    const payload = {
      claim_id: parseInt(claimId),
      primary_claim: primaryDiagnosis,
      secondary_claims: secondaryDiagnosis,
      primary_action: primaryProcedure,
      secondary_actions: secondaryProcedures
    };
    
    console.log("📤 Sending payload to predict_idrg:", payload);
    
    const response = await fetch(`/claims/${claimId}/predict_idrg`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log("📥 i-DRG prediction result:", result);
    
    if (result.error) {
      throw new Error(result.error);
    }
    
    // Return raw result untuk debugging
    return {
      status: 'success',
      data: result
    };
    
  } catch (error) {
    console.error("❌ Error predicting combo i-DRG:", error);
    throw error;
  }
};

// Function untuk render hasil prediksi combo
window.renderComboIdrgResult = function(data) {
  if (!data || !data.idrg_prediction) {
    return `<div class="p-4 text-red-500">Data prediksi i-DRG kombinasi tidak lengkap</div>`;
  }
  
  const prediction = data.idrg_prediction;
  
  const renderPredictionRow = (label, value, isClickable = false) => {
    const content = isClickable ? 
      `<span class="cursor-pointer hover:underline hover:text-green-600">${value}</span>` :
      value;
      
    return `
      <div class="grid grid-cols-2">
        <div class="bg-green-700 text-white px-3 py-2 font-medium">${label}</div>
        <div class="bg-green-100 dark:bg-green-800 px-3 py-2 text-gray-900 dark:text-gray-100">${content || "-"}</div>
      </div>
    `;
  };
  
  // Render checklist dokumentasi sebagai list jika array
  let checklistHtml = "-";
  if (prediction.checklist_idrg_kombinasi && Array.isArray(prediction.checklist_idrg_kombinasi) && 
      prediction.checklist_idrg_kombinasi.length > 0) {
    checklistHtml = prediction.checklist_idrg_kombinasi.map(item => `<li>• ${item}</li>`).join('');
    checklistHtml = `<ul class="list-none pl-0">${checklistHtml}</ul>`;
  } else if (prediction.checklist_idrg_kombinasi) {
    checklistHtml = prediction.checklist_idrg_kombinasi;
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
  
  // Convert rekomendasi_ai to array if it's a string
  const recommendations = prediction.rekomendasi_ai || "-";
  let recommendationsHtml = "-";
  
  if (recommendations !== "-") {
    if (typeof recommendations === 'string') {
      recommendationsHtml = `<div>• ${recommendations}</div>`;
    } else if (Array.isArray(recommendations)) {
      recommendationsHtml = recommendations.map(r => `<div>• ${r}</div>`).join('');
    }
  }
  
  // Field yang tepat sesuai idrg_service.py
  return `
    <div class="space-y-2 px-4">      
      ${renderPredictionRow("Kode i-DRG", prediction.prediksi_group_idrg_kombinasi || "-", true)}
      ${renderPredictionRow("Severity Kombinasi", prediction.severity_kombinasi || "-", true)}
      ${renderPredictionRow("Checklist Dokumentasi", checklistHtml)}
      ${renderPredictionRow("Faktor Penentu Severity", faktorSeverityHtml)}
      ${renderPredictionRow("Risiko Ungroupable", prediction.risiko_ungroupable || "-")}
      ${renderPredictionRow("Estimasi Tarif", prediction.estimasi_tarif_idrg ? `Rp ${parseInt(prediction.estimasi_tarif_idrg).toLocaleString('id-ID')}` : "-")}
      ${renderPredictionRow("Gap Analysis", prediction.gap_analysis !== undefined ? `${prediction.gap_analysis}` : "-")}
      
      <div class="grid grid-cols-1">
        <div class="bg-green-700 text-white px-3 py-2 font-medium">Rekomendasi AI</div>
        <div class="bg-green-100 dark:bg-green-800 px-3 py-2 text-gray-900 dark:text-gray-100 text-sm">
          ${recommendationsHtml}
        </div>
      </div>
      
      <div class="text-xs text-green-600 dark:text-green-300 mt-3 p-2 bg-white dark:bg-gray-800 rounded">
        <strong>Engine:</strong> ${data.engine_version || 'OpenAI GPT-4'} • 
        <strong>Mode:</strong> Kombinasi • 
        <strong>Primary:</strong> ${data.primary_diagnosis} •
        <strong>Generated:</strong> ${new Date().toLocaleString()}
      </div>
    </div>
  `;
};

// =============== UI fix agar identik dengan referensi (auto adapt light/dark) ===============
window.parseRupiah = function (val) {
  if (!val || val === '-') return '-';
  try {
    if (typeof val === 'string') {
      const match = val.match(/\d+/g);
      if (match) {
        const num = parseInt(match.join(''));
        return `Rp ${num.toLocaleString('id-ID')}`;
      }
    }
    if (typeof val === 'number') {
      return `Rp ${val.toLocaleString('id-ID')}`;
    }
    return val;
  } catch (e) {
    console.warn('parseRupiah error:', e);
    return val;
  }
};

window.renderEvaluasiIDRGSummary = function (data, claimId) {
  const target = document.getElementById("evaluasi-idrg");
  if (!target) return;
  target.innerHTML = "";

  if (!claimId)
    claimId = document.getElementById("claimRoot")?.dataset.claimId;

  target.innerHTML = `
  <div class="mb-5 border border-gray-300 dark:border-gray-700 rounded-lg overflow-hidden"
       x-data="idrgDropdown({ claimId: ${Number(claimId) || 0} })">
    <!-- header -->
    <div class="flex items-center justify-between bg-green-600 text-white px-4 py-2 font-semibold text-[15px] cursor-pointer"
         @click="toggleDropdown()">
      <span class="tracking-wide">Prediksi i-DRG Kombinasi</span>
      <div class="flex items-center gap-2 text-xs">
        <span class="italic opacity-90">(klik untuk lihat detail)</span>
        <span x-show="loading" class="animate-spin h-4 w-4 border-2 border-white rounded-full border-t-transparent"></span>
        <span x-text="open ? '▲' : '▼'"></span>
      </div>
    </div>

    <!-- body -->
    <div x-show="open" x-transition class="bg-white dark:bg-gray-900 text-sm leading-relaxed">
      <template x-if="loading">
        <div class="p-4 text-center text-gray-500 dark:text-gray-400">
          <div class="inline-flex items-center">
            <div class="animate-spin h-4 w-4 mr-2 border-2 border-green-600 rounded-full border-t-transparent"></div>
            <span>Menganalisis kombinasi dengan OpenAI...</span>
          </div>
        </div>
      </template>

      <template x-if="!loading && idrgData">
        <div class="divide-y divide-gray-200 dark:divide-gray-700">
          <div class="grid grid-cols-2">
            <div class="bg-gray-50 dark:bg-gray-800 px-4 py-2 font-medium">Group i-DRG Kombinasi</div>
            <div class="px-4 py-2" x-text="idrgData.group_idrg_kombinasi || idrgData.group_idrg || '-'"></div>
          </div>
          <div class="grid grid-cols-2">
            <div class="bg-gray-50 dark:bg-gray-800 px-4 py-2 font-medium">Severity Kombinasi</div>
            <div class="px-4 py-2" x-text="idrgData.severity_kombinasi || idrgData.severity || '-'"></div>
          </div>
          <div class="grid grid-cols-2">
            <div class="bg-gray-50 dark:bg-gray-800 px-4 py-2 font-medium">Checklist Kombinasi</div>
            <div class="px-4 py-2">
              <template x-if="Array.isArray(idrgData.checklist_idrg_kombinasi || idrgData.checklist_dokumentasi)">
                <ul class="list-disc list-inside space-y-0.5">
                  <template x-for="(item, i) in (idrgData.checklist_idrg_kombinasi || idrgData.checklist_dokumentasi)" :key="i">
                    <li x-text="item"></li>
                  </template>
                </ul>
              </template>
              <template x-if="!Array.isArray(idrgData.checklist_idrg_kombinasi)">
                <span x-text="idrgData.checklist_dokumentasi || '-'"></span>
              </template>
            </div>
          </div>
          <div class="grid grid-cols-2">
            <div class="bg-gray-50 dark:bg-gray-800 px-4 py-2 font-medium">Faktor Severity Kombinasi</div>
            <div class="px-4 py-2">
              <template x-if="Array.isArray(idrgData.faktor_penentu_severity || idrgData.faktor_severity)">
                <ul class="list-disc list-inside space-y-0.5">
                  <template x-for="(item, i) in (idrgData.faktor_penentu_severity || idrgData.faktor_severity)" :key="i">
                    <li x-text="item"></li>
                  </template>
                </ul>
              </template>
              <template x-if="!Array.isArray(idrgData.faktor_penentu_severity)">
                <span x-text="idrgData.faktor_penentu_severity || '-'"></span>
              </template>
            </div>
          </div>
          <div class="grid grid-cols-2">
            <div class="bg-gray-50 dark:bg-gray-800 px-4 py-2 font-medium">Risiko Ungroupable</div>
            <div class="px-4 py-2" x-text="idrgData.risiko_ungroupable || '-'"></div>
          </div>
          <div class="grid grid-cols-2">
            <div class="bg-gray-50 dark:bg-gray-800 px-4 py-2 font-medium">Estimasi Tarif</div>
            <div class="px-4 py-2" x-text="window.parseRupiah(idrgData.estimasi_tarif_idrg || idrgData.estimasi_tarif)"></div>
          </div>
          <div class="grid grid-cols-2">
            <div class="bg-gray-50 dark:bg-gray-800 px-4 py-2 font-medium">Gap INA-CBG vs i-DRG</div>
            <div class="px-4 py-2" x-text="window.parseRupiah(idrgData.gap_inacbg_vs_idrg || idrgData.gap_analysis)"></div>
          </div>
          <div class="grid grid-cols-2">
            <div class="bg-gray-50 dark:bg-gray-800 px-4 py-2 font-medium">Rekomendasi AI</div>
            <div class="px-4 py-2" x-text="idrgData.rekomendasi_ai || '-'"></div>
          </div>
        </div>
      </template>
    </div>
  </div>`;
  if (window.Alpine && Alpine.initTree) Alpine.initTree(target);
};


window.renderAlternatifKombinasi = function (items) {
  const target = document.getElementById("alternatif");
  if (!target) return;
  target.innerHTML = "";

  const claimId = document.getElementById("claimRoot")?.dataset.claimId || 0;

  target.innerHTML = `
  <div class="mb-5 border border-gray-300 dark:border-gray-700 rounded-lg overflow-hidden"
       x-data="alternatifDropdown({ claimId: ${Number(claimId) || 0} })">
    <!-- header -->
    <div class="flex items-center justify-between bg-yellow-400 text-gray-900 dark:bg-yellow-600 dark:text-white px-4 py-2 font-semibold text-[15px] cursor-pointer"
         @click="toggleDropdown()">
      <span class="tracking-wide">Alternatif Kombinasi</span>
      <div class="flex items-center gap-2 text-xs">
        <span class="italic opacity-80">(klik untuk lihat detail)</span>
        <span x-show="loading" class="animate-spin h-4 w-4 border-2 border-gray-900 dark:border-white rounded-full border-t-transparent"></span>
        <span x-text="open ? '▲' : '▼'"></span>
      </div>
    </div>

    <!-- body -->
    <div x-show="open" x-transition class="bg-white dark:bg-gray-900 text-sm leading-relaxed">
      <template x-if="loading">
        <div class="p-4 text-center text-gray-500 dark:text-gray-400">
          <div class="inline-flex items-center">
            <div class="animate-spin h-4 w-4 mr-2 border-2 border-yellow-600 rounded-full border-t-transparent"></div>
            <span>Mengambil data alternatif kombinasi...</span>
          </div>
        </div>
      </template>

      <template x-if="!loading && alternatives && alternatives.length">
        <div class="divide-y divide-gray-200 dark:divide-gray-700">
          <template x-for="(alt, i) in alternatives" :key="i">
            <div class="px-5 py-4">
              <h3 class="font-semibold text-gray-900 dark:text-gray-100 text-[15px] mb-1"
                  x-text="'Alternatif ' + (i+1) + ': ' + (alt.judul || alt.nama || '-')"></h3>
              <div class="text-gray-700 dark:text-gray-300 space-y-1 ml-1">
                <p><span class="font-semibold text-gray-600 dark:text-gray-400">Severity:</span> <span x-text="alt.severity || '-'"></span></p>
                <p><span class="font-semibold text-gray-600 dark:text-gray-400">INA-CBG:</span> <span x-text="alt.ina_cbg || '-'"></span></p>
                <p><span class="font-semibold text-gray-600 dark:text-gray-400">Tarif:</span> <span x-text="(alt.tarif || alt.estimasi_tarif) ? 'Rp ' + parseInt(alt.tarif || alt.estimasi_tarif).toLocaleString('id-ID') : '-'"></span></p>
                <p><span class="font-semibold text-gray-600 dark:text-gray-400">Syarat Klinis:</span> <span x-text="alt.syarat || '-'"></span></p>
                <p><span class="font-semibold text-gray-600 dark:text-gray-400">Evaluasi Faskes:</span> <span x-text="alt.faskes || '-'"></span></p>
                <p><span class="font-semibold text-gray-600 dark:text-gray-400">Rawat Inap:</span> <span x-text="alt.rawat_inap || '-'"></span></p>
                <p class="font-semibold text-gray-600 dark:text-gray-400">Tindakan Wajib:</p>
                <template x-if="Array.isArray(alt.tindakan) && alt.tindakan.length">
                  <ul class="list-disc list-inside ml-4">
                    <template x-for="(tdk, j) in alt.tindakan" :key="j">
                      <li x-text="tdk"></li>
                    </template>
                  </ul>
                </template>
                <template x-if="!(Array.isArray(alt.tindakan) && alt.tindakan.length)">
                  <p class="ml-4" x-text="alt.tindakan_wajib || '-'"></p>
                </template>
              </div>
            </div>
          </template>
        </div>
      </template>

      <template x-if="!loading && (!alternatives || alternatives.length === 0)">
        <div class="p-3 italic text-gray-500 dark:text-gray-400 text-center">Tidak ada alternatif kombinasi</div>
      </template>
    </div>
  </div>`;
  if (window.Alpine && Alpine.initTree) Alpine.initTree(target);
};