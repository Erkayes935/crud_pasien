// =============== Komunikasi ke Backend (fetch) ===============

(function () {
  async function generateAI() {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return alert("❌ Claim ID tidak ditemukan.");

    try {
      const state = Alpine.$data(document.getElementById("claimRoot"));
      const stage = state.tab || "admission";

      // Show loading state
      const loadingMsg = document.createElement('div');
      loadingMsg.id = 'ai-loading';
      loadingMsg.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.8); color: white; padding: 20px; border-radius: 8px; z-index: 9999;';
      loadingMsg.innerHTML = 'Generating AI recommendations...';
      document.body.appendChild(loadingMsg);

      const res = await fetch(`/claims/${claimId}/predict_ddx`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          claim_id: claimId, 
          stage,
          global_record: state.globalRecord || {} 
        })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail?.error || errorData.detail || 'Failed to generate AI recommendations');
      }

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      const result = await res.json();
      console.log("📥 Data core_engine:", result);
      
      if (!result || typeof result !== 'object') {
        throw new Error('Invalid response format from core_engine');
      }

      // Render predictions by category
      const categories = ['diagnosis', 'komorbid', 'komplikasi'];
      for (const category of categories) {
        if (Array.isArray(result[category])) {
          console.log(`🔥 DEBUG ${category}:`, result[category]);
          window.renderAI && window.renderAI(result[category], category, stage);
        }
      }

      // Save draft after successful AI generation
      await saveDraft(claimId, {
        ai_recommendations: result,
        stage: stage
      });

      alert("✅ AI recommendations generated successfully");

    } catch (err) {
      console.error("❌ Error generate AI:", err);
      alert(`Gagal generate AI: ${err.message}`);
    } finally {
      // Remove loading message
      const loadingMsg = document.getElementById('ai-loading');
      if (loadingMsg) {
        loadingMsg.remove();
      }
    }
  }

  // ==================== SAVE DRAFT UNIVERSAL ====================
  async function saveDraft(claimId) {
    try {
      const root = document.getElementById("claimRoot");
      const state = Alpine.$data(root);
      const csrfToken = document.querySelector("input[name='csrf_token']")?.value || "";

      // Buat formData (biar cocok dengan Form() di backend)
      const formData = new FormData();
      formData.append("csrf_token", csrfToken);
      formData.append("simulasi", JSON.stringify(state.simulasi || {}));
      formData.append("summary", JSON.stringify(window.claimState?.summary || {}));
      formData.append("ai_recommendations", JSON.stringify(state.ai_recommendations || {}));
      formData.append("stage", state.tab || "admission");

      console.log("📤 Sending draft as FormData:", Object.fromEntries(formData));

      const res = await fetch(`/claims/${claimId}/update-draft`, {
        method: "POST",
        credentials: "include", // biar cookie session ikut
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Gagal simpan draft (HTTP ${res.status}): ${text}`);
      }

      // Kalau backend redirect → res.redirected true
      if (res.redirected) {
        console.log("🔁 Redirected ke:", res.url);
        window.location.href = res.url; // optional reload
        return;
      }

      showToast("💾 Draft berhasil disimpan");
      console.log("✅ Draft saved successfully");

    } catch (err) {
      console.error("❌ Error saat menyimpan draft:", err);
      showToast(`❌ Gagal menyimpan draft: ${err.message}`, true);
    }
  }
  function showToast(msg, isError = false) {
    const div = document.createElement("div");
    div.textContent = msg;
    div.style.position = "fixed";
    div.style.bottom = "20px";
    div.style.right = "20px";
    div.style.padding = "10px 16px";
    div.style.borderRadius = "6px";
    div.style.color = "white";
    div.style.backgroundColor = isError ? "#dc2626" : "#16a34a";
    div.style.zIndex = 9999;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 2500);
  }
  window.saveDraft = saveDraft;

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

window.searchDiagnosis = searchDiagnosis;
window.getDiagnosisDetail = getDiagnosisDetail;

  async function generateSummary() {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return alert("❌ Claim ID tidak ditemukan.");

    try {
      // Show loading message
      const loadingMsg = document.createElement('div');
      loadingMsg.id = 'summary-loading';
      loadingMsg.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.8); color: white; padding: 20px; border-radius: 8px; z-index: 9999;';
      loadingMsg.innerHTML = 'Generating claim summary...';
      document.body.appendChild(loadingMsg);

      const state = Alpine.$data(document.getElementById("claimRoot"));
      
      // Ambil tab aktif
      const currentTab = state.tab || 'admission';
      
      // Ekstrak data diagnosa dan tindakan dari simulasi tab saat ini
      const simData = state.simulasi[currentTab];

      if (!simData) {
        throw new Error("Tidak ada data simulasi di tab ini");
      }

      // Format payload sesuai dengan core_engine
      const payload = { 
        claim_id: parseInt(claimId),
        stage: currentTab,
        // Field sesuai dengan yang diharapkan oleh idrg_service.py
        primary_claim: simData.utama?.name || "",
        secondary_claims: (simData.sekunder || []).map(d => d.name).filter(Boolean),
        primary_action: simData.tindakanUtama?.name || "",
        secondary_actions: (simData.tindakanSekunder || [])
          .filter(t => t && t.name)
          .map(t => t.name)
      };

      console.log("📤 Sending payload to generate_claim_combos:", payload);

      const res = await fetch(`/claims/${claimId}/generate_claim_combos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Gagal request summary (${res.status}): ${errorText}`);
      }

      const data = await res.json();
      console.log("📥 Full summary result:", data);

      if (data.error) {
        throw new Error(`Error from server: ${data.error}`);
      }

      // Detailed debugging
      console.log("===== DEBUGGING RESPONSE STRUCTURE =====");
      
      // Check for result property
      console.log("Has 'result' property:", data.hasOwnProperty('result'));
      if (data.result) {
        console.log("Result structure:", Object.keys(data.result));
      }
      
      // Check for various i-DRG fields
      const idrgPaths = [
        'idrg_summary',
        'result.idrg_summary',
        'result.idrg_prediction',
        'idrg_prediction'
      ];
      
      idrgPaths.forEach(path => {
        const pathParts = path.split('.');
        let value = data;
        
        for (const part of pathParts) {
          if (value && value.hasOwnProperty(part)) {
            value = value[part];
          } else {
            value = null;
            break;
          }
        }
        
        console.log(`Path '${path}' exists:`, value !== null);
        if (value) {
          console.log(`Fields in '${path}':`, Object.keys(value));
        }
      });

      // Normalisasi format result untuk konsistensi
      const resultData = data.result || data;
      
      // Extract diagnosis data
      const diagnosisData = resultData.evaluasi_diagnosis || resultData.diagnosis || {};
      console.log("📊 Extracted diagnosis data:", diagnosisData);
      
      // Extract procedure data
      let procedureData = resultData.evaluasi_tindakan || resultData.procedure || [];
      if (procedureData && typeof procedureData === 'object' && !Array.isArray(procedureData)) {
        procedureData = procedureData.rows || procedureData.items || [procedureData];
      }
      console.log("📊 Extracted procedure data:", procedureData);
      
      // Extract iDRG data with priority checking
      let idrgData = null;
      
      // Priority 1: resultData.idrg_summary
      if (resultData.idrg_summary && Object.keys(resultData.idrg_summary).length > 0) {
        idrgData = resultData.idrg_summary;
        console.log("📊 Found iDRG data in resultData.idrg_summary");
      } 
      // Priority 2: resultData.result.idrg_summary
      else if (resultData.result && resultData.result.idrg_summary) {
        idrgData = resultData.result.idrg_summary;
        console.log("📊 Found iDRG data in resultData.result.idrg_summary");
      }
      // Priority 3: resultData.idrg_prediction
      else if (resultData.idrg_prediction) {
        idrgData = resultData.idrg_prediction;
        console.log("📊 Found iDRG data in resultData.idrg_prediction");
      } 
      // Create dummy data if nothing found
      else {
        console.log("⚠️ No iDRG data found, creating dummy structure");
        idrgData = {
          prediksi_group_idrg_kombinasi: "-",
          severity_kombinasi: "-",
          checklist_idrg_kombinasi: [],
          faktor_penentu_severity: [],
          risiko_ungroupable: "-",
          estimasi_tarif_idrg: "-",
          gap_analysis: "-",
          rekomendasi_ai: []
        };
      }
      
      console.log("📊 Final iDRG data for rendering:", idrgData);
      
      // Extract alternatif kombinasi
      let alternatifData = resultData.alternatif || [];
      console.log("📊 Extracted alternatif data:", alternatifData);
      
      // Update UI sections dengan try/catch untuk isolasi error
      try {
        console.log("🔄 Rendering diagnosis evaluation...");
        window.renderEvaluasiDiagnosis && window.renderEvaluasiDiagnosis(diagnosisData);
        console.log("✅ Diagnosis evaluation rendered");
      } catch (err) {
        console.error("❌ Error rendering diagnosis evaluation:", err);
      }
      
      try {
        console.log("🔄 Rendering procedure evaluation...");
        window.renderEvaluasiProcedure && window.renderEvaluasiProcedure(procedureData);
        console.log("✅ Procedure evaluation rendered");
      } catch (err) {
        console.error("❌ Error rendering procedure evaluation:", err);
      }
      
      try {
        console.log("🔄 Rendering iDRG summary...");
        window.renderEvaluasiIDRGSummary && window.renderEvaluasiIDRGSummary(idrgData, claimId);
        console.log("✅ iDRG summary rendered");
      } catch (err) {
        console.error("❌ Error rendering iDRG summary:", err);
        console.error("Error details:", err.stack);
      }
      
      try {
        console.log("🔄 Rendering alternatif kombinasi...");
        window.renderAlternatifKombinasi && window.renderAlternatifKombinasi(alternatifData);
        console.log("✅ Alternative combinations rendered");
      } catch (err) {
        console.error("❌ Error rendering alternative combinations:", err);
      }

      const summaryField = document.getElementById("summaryField");
      if (summaryField) summaryField.value = JSON.stringify(resultData);
      window.claimState.summary = resultData;

      alert("✅ Summary berhasil digenerate");
    } catch (err) {
      console.error("❌ Error generate summary:", err);
      console.error("Stack trace:", err.stack);
      alert(`❌ Gagal generate summary: ${err.message}`);
    } finally {
      // Remove loading message
      const loadingMsg = document.getElementById('summary-loading');
      if (loadingMsg) {
        loadingMsg.remove();
      }
      window.syncHiddenInputs && window.syncHiddenInputs();
    }
  }

  // 🔥 Resume Medis function untuk core_engine
  async function generateResumeMedis(claimId) {
    if (!claimId) {
      alert("❌ Claim ID tidak ditemukan.");
      return;
    }
    
    try {
      const res = await fetch("/resume_medis", {
        method: "POST", 
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim_id: claimId })
      });
      const result = await res.json();
      console.log("📥 Resume medis:", result);
      return result;
    } catch (err) {
      console.error("❌ Error generate resume medis:", err);
      alert("Gagal generate resume medis");
    }
  }

  // Export API
  window.generateAI = generateAI;
  window.generateSummary = generateSummary;
  window.loadSimulations = loadSimulations;
  window.searchDiagnosis = searchDiagnosis;
  window.getDiagnosisDetail = getDiagnosisDetail;
  window.generateResumeMedis = generateResumeMedis;
})();
