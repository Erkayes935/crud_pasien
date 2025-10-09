// =============== Komunikasi ke Backend (fetch) ===============

(function () {
  async function generateAI() {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return alert("❌ Claim ID tidak ditemukan.");
    const state = window.claimState || {};

    // 1️⃣ Backup tindakan manual sebelum generate AI
    const manualBackup = {};
    for (const tab in (state.simulasi || {})) {
      const tindakans = state.simulasi[tab]?.tindakan?.filter(t => t.isManual) || [];
      if (tindakans.length) manualBackup[tab] = tindakans;
    }

    try {
      // � FIXED: Use core_engine endpoint instead of dummy endpoint
      const res = await fetch(`/claims/${claimId}/predict_ddx`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          claim_id: parseInt(claimId),
          stage: state.tab || "admission"
        })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const result = await res.json();
      console.log("🔍 Core engine result:", result);
      
      // 🔥 Handle response from core_engine (already in correct format!)
      const responseData = result.data || result;
      
      // 🔥 GET CORRECT STAGE from current tab
      const currentStage = state.tab || "admission";
      console.log("🔍 Current stage for transformation:", currentStage);
      console.log("🔍 Response data structure:", responseData);
      
      // 🔥 DIRECT USE: Response is already in correct format with kategori/children
      const transformedRows = [];
      
      // Process each category (diagnosis, komorbid, komplikasi)  
      ['diagnosis', 'komorbid', 'komplikasi'].forEach(category => {
        const items = responseData[category] || [];
        items.forEach((item, index) => {
          // 🔥 Fix children klinis to be "-" by default
          const fixedChildren = (item.children || []).map(child => ({
            ...child,
            klinis: "-",  // Children klinis should be "-" until filled by modal
            icd10_code: "-",
            procedure_text: "-"
          }));
          
          // Item already has correct structure: kategori, klinis, children, etc.
          transformedRows.push({
            ...item,
            id: `${category}-${Date.now()}-${index}`,
            stage: currentStage,
            category: category,
            // Fix parent klinis to be "-" instead of diagnosis name
            klinis: "-",
            children: fixedChildren
          });
        });
      });

      console.log("🔍 Transformed rows:", transformedRows);

      // 🔥 CORE_ENGINE: Render transformed recommendations
      if (transformedRows && transformedRows.length > 0) {
        window.renderAI && window.renderAI(transformedRows);
        console.log("✅ Core engine AI recommendations rendered:", transformedRows.length);
      } else {
        console.warn("⚠️ No AI recommendations received from core engine");
      }

      // 🔥 CORE_ENGINE: Restore manual backups if needed
      for (const tab in manualBackup) {
        const manualList = manualBackup[tab];
        if (!manualList?.length) continue;
        if (!state.simulasi[tab]) continue;

        const current = state.simulasi[tab].tindakan || [];
        const merged = [
          ...current.filter(it => !manualList.some(m => m.procedure_text === it.procedure_text)),
          ...manualList,
        ];
        state.simulasi[tab].tindakan = merged;
      }

      // Sync hidden inputs
      window.syncHiddenInputs && window.syncHiddenInputs();

    } catch (err) {
      console.error("❌ Error generate AI:", err);
      alert("Gagal generate AI");
    }
  }




  async function loadSimulations(claimId) {
    try {
      const res = await fetch(`/claims/${claimId}/simulations`);
      if (!res.ok) return;
      const body = await res.json();
      const sims = body.data || [];

      sims.forEach(s => {
        if (s.diagnosis_utama_id) {
          setTimeout(() => window.updateSimulasi("diagnosis", "Primary", {
            id: s.diagnosis_utama_id,
            name: s.diagnosis_utama_name || "(tanpa nama)", mapping: "Primary"
          }, true, s.stage), 0);
        }
        if (s.diagnosis_sekunder_id) {
          setTimeout(() => window.updateSimulasi("diagnosis", "Secondary-Komorbid", {
            id: s.diagnosis_sekunder_id,
            name: s.diagnosis_sekunder_name || "(tanpa nama)", mapping: "Secondary-Komorbid"
          }, true, s.stage), 0);
        }
        if (s.tindakan_utama_id) {
          setTimeout(() => window.updateSimulasi("tindakan", "Primary", {
            id: s.tindakan_utama_id,
            name: s.tindakan_utama_name || "(tanpa nama)", mapping: "Primary"
          }, true, s.stage), 0);
        }
        if (s.tindakan_sekunder_id) {
          setTimeout(() => window.updateSimulasi("tindakan", "Secondary", {
            id: s.tindakan_sekunder_id,
            name: s.tindakan_sekunder_name || "(tanpa nama)", mapping: "Secondary"
          }, true, s.stage), 0);
        }
      });
    } catch (e) {
      console.error("Gagal load simulations", e);
    }
  }

  async function searchDiagnosis(query) {
    const res = await fetch(`/claims/search/diagnosis?query=${query}`);
    return await res.json();
  }

  async function getDiagnosisDetail(code) {
    const res = await fetch(`/claims/search/diagnosis/detail/${code}`);
    return await res.json();
  }

  async function searchTindakan(query) {
    const res = await fetch(`/claims/search/tindakan?query=${query}`);
    return await res.json();
  }
  async function getTindakanDetail(procedure_text) {
    const res = await fetch(`/claims/search/tindakan/detail/${procedure_text}`);
    return await res.json();
  }

  async function generateSummary() {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return alert("❌ Claim ID tidak ditemukan.");

    try {
      const state = Alpine.$data(document.getElementById("claimRoot"));
      
      // 🔥 FIXED: Use core_engine generate_claim_combos endpoint instead of dummy
      const payload = { 
        claim_id: parseInt(claimId), 
        simulasi: state.simulasi,
        // Add required fields for generate_claim_combos
        primary_claim: "Primary diagnosis", // Could be extracted from simulasi
        secondary_claims: [], // Could be extracted from simulasi 
        primary_action: "Primary procedure", // Could be extracted from simulasi
        secondary_actions: [] // Could be extracted from simulasi
      };

      const res = await fetch(`/claims/${claimId}/generate_claim_combos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status} - Gagal request evaluasi`);

      const result = await res.json();
      console.log("🔍 Core engine evaluasi result:", result);
      
      // Handle core_engine response format
      const data = result.data || result;

      window.renderEvaluasiDiagnosis && window.renderEvaluasiDiagnosis(data.evaluasi_diagnosis || data.diagnosis || {});
      window.renderEvaluasiProcedure && window.renderEvaluasiProcedure(data.evaluasi_tindakan || data.procedure || {});
      window.renderEvaluasiIDRGSummary && window.renderEvaluasiIDRGSummary(data.idrg_summary || {});
      window.renderAlternatifKombinasi && window.renderAlternatifKombinasi(data.alternatif || []);

      const summaryField = document.getElementById("summaryField");
      if (summaryField) summaryField.value = JSON.stringify(data);
      window.claimState.summary = data;

      alert("✅ Evaluasi berhasil digenerate");
    } catch (err) {
      console.error("❌ Error generate evaluasi:", err);
      alert(`❌ Gagal generate evaluasi: ${err.message}`);
    } finally {
      window.syncHiddenInputs && window.syncHiddenInputs();
    }
  }

  // 🔥 Helper function to extract form data including Alpine.js state (from development branch)
  function get_form_as_dict() {
    const form = document.getElementById('claimForm');
    if (!form) {
      console.error("❌ Form claimForm not found");
      return {};
    }

    const formData = new FormData(form);
    const result = {};
    
    // Convert FormData entries (KEEP CSRF token!)
    for (let [key, value] of formData.entries()) {
      result[key] = value;
    }
    
    // 🔥 Add Alpine.js simulasi state data from claimRoot
    const claimRoot = document.getElementById("claimRoot");
    if (claimRoot && typeof Alpine !== 'undefined') {
      try {
        const state = Alpine.$data(claimRoot);
        if (state && state.simulasi) {
          result.simulasi = JSON.stringify(state.simulasi);
        }
        // Also add summary if available
        if (window.claimState && window.claimState.summary) {
          result.summary = JSON.stringify(window.claimState.summary);
        }
      } catch (err) {
        console.warn("⚠️ Could not extract Alpine state:", err);
      }
    }
    
    console.log("📋 Form extracted as dict:", result);
    return result;
  }

  // 🔥 Save draft function (adapted from development branch for core_engine)
  async function saveDraft(claimId, data = null) {
    try {
      // Get CSRF token with debugging
      console.log("🔍 Looking for CSRF token...");
      const csrfInput = document.querySelector('input[name="csrf_token"]');
      const csrfMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfGeneric = document.querySelector('[name="csrf_token"]');
      
      console.log("CSRF sources:", {
        input: csrfInput?.value || null,
        meta: csrfMeta?.content || null, 
        generic: csrfGeneric?.value || null
      });
      
      const csrfToken = csrfInput?.value || csrfMeta?.content || csrfGeneric?.value;
      
      // 🔥 If no data provided, extract from form like development branch
      const payload = data || get_form_as_dict();
      
      // � Backend expects CSRF as form data, so create FormData
      const formData = new FormData();
      
      // Add CSRF token as form field (required by require_csrf_dep)
      if (csrfToken) {
        formData.append('csrf_token', csrfToken);
        console.log("🔒 CSRF token added to form data:", csrfToken);
      } else {
        console.warn("⚠️ No CSRF token found");
        throw new Error("CSRF token required");
      }
      
      // Add payload as JSON string in 'payload' field
      formData.append('payload', JSON.stringify(payload));
      
      console.log("📦 Save draft payload:", payload);
      console.log("📦 FormData keys:", Array.from(formData.keys()));
      console.log("📦 Request URL:", `/claims/${claimId}/update-draft`);
      
      // Send as form data (no Content-Type header needed, browser sets multipart/form-data)
      const res = await fetch(`/claims/${claimId}/update-draft`, {
        method: "POST",
        credentials: "include",
        body: formData
      });
      
      console.log("📡 Response:", res.status, res.statusText);

      if (!res.ok) {
        const errorData = await res.json();
        console.error("❌ Save draft error response:", errorData);
        
        // 🔥 Better error display for debugging
        let errorMsg = `HTTP error! status: ${res.status}`;
        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            errorMsg += ` - ${errorData.detail.map(e => e.msg || e).join(', ')}`;
          } else {
            errorMsg += ` - ${errorData.detail}`;
          }
        }
        throw new Error(errorMsg);
      }

      const result = await res.json();
      console.log("📥 Draft saved successfully:", result);
      return result;
    } catch (err) {
      console.error("❌ Error save draft:", err);
      throw err;
    }
  }

  // Export API
  window.generateAI = generateAI;
  window.generateSummary = generateSummary;
  window.loadSimulations = loadSimulations;
  window.searchDiagnosis = searchDiagnosis;
  window.getDiagnosisDetail = getDiagnosisDetail;
  window.searchTindakan = searchTindakan;
  window.getTindakanDetail = getTindakanDetail;
  window.saveDraft = saveDraft;
  window.get_form_as_dict = get_form_as_dict;
})();