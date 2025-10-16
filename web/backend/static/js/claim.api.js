// =============== Komunikasi ke Backend (fetch) ===============

(function () {
  // ============================================================
  // 🔔 Universal Toast Function (popup auto-hide) - Enhanced Elegant Design
  // ============================================================
  function showToast(message, isError = false, duration = 4000) {
    const existing = document.getElementById("global-toast");
    if (existing) existing.remove();

    const div = document.createElement("div");
    div.id = "global-toast";
    div.textContent = message;
    div.setAttribute("role", "alert");
    div.setAttribute("aria-live", "polite");

    const bgColor = isError ? "#ef4444" : "#10b981"; // Red / Green
    const shadowColor = isError ? "rgba(239,68,68,0.3)" : "rgba(16,185,129,0.3)";

    Object.assign(div.style, {
      position: "fixed",
      top: "20px",
      right: "20px",
      background: `linear-gradient(135deg, ${bgColor} 0%, ${
        isError ? "#dc2626" : "#059669"
      } 100%)`,
      color: "#fff",
      padding: "16px 20px",
      borderRadius: "12px",
      boxShadow: `
        0 20px 25px -5px ${shadowColor},
        0 10px 10px -5px rgba(0,0,0,0.1)
      `,
      fontSize: "14px",
      fontWeight: "500",
      fontFamily:
        "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif",
      lineHeight: "1.4",
      maxWidth: "350px",
      wordWrap: "break-word",
      zIndex: 9999,
      opacity: "0",
      transform: "translateX(100%) scale(0.95)",
      transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
      backdropFilter: "blur(10px)",
      border: "1px solid rgba(255,255,255,0.1)",
    });

    document.body.appendChild(div);
    requestAnimationFrame(() => {
      div.style.opacity = "1";
      div.style.transform = "translateX(0) scale(1)";
    });
    setTimeout(() => {
      div.style.opacity = "0";
      div.style.transform = "translateX(100%) scale(0.95)";
      setTimeout(() => div.remove(), 500);
    }, duration);
  }

  // ============================================================
  // 🔮 Generate AI
  // ============================================================
  async function generateAI() {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return showToast("❌ Claim ID tidak ditemukan.", true);
    const state = window.claimState || {};

    const manualBackup = {};
    for (const tab in state.simulasi || {}) {
      const tindakans =
        state.simulasi[tab]?.tindakan?.filter((t) => t.isManual) || [];
      if (tindakans.length) manualBackup[tab] = tindakans;
    }

    const loadingMsg = document.createElement("div");
    loadingMsg.id = "ai-loading";
    loadingMsg.style.cssText =
      "position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.8); color: white; padding: 20px; border-radius: 8px; z-index: 9999;";
    loadingMsg.innerHTML = "Generating AI recommendations...";
    document.body.appendChild(loadingMsg);

    try {
      const res = await fetch(`/claims/${claimId}/predict_ddx`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_id: parseInt(claimId),
          stage: state.tab || "admission",
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const result = await res.json();
      console.log("🔍 Core engine result:", result);

      const responseData = result.data || result;
      const currentStage = state.tab || "admission";
      const transformedRows = [];

      ["diagnosis", "komorbid", "komplikasi"].forEach((category) => {
        const items = responseData[category] || [];
        items.forEach((item, index) => {
          const fixedChildren = (item.children || []).map((child) => ({
            ...child,
            klinis: "-",
            icd10_code: "-",
            procedure_text: "-",
          }));
          transformedRows.push({
            ...item,
            id: `${category}-${Date.now()}-${index}`,
            stage: currentStage,
            category,
            klinis: "-",
            children: fixedChildren,
          });
        });
      });

      if (transformedRows.length > 0) {
        window.renderAI && window.renderAI(transformedRows);
        showToast("✅ AI recommendations generated successfully");
      } else {
        showToast("⚠️ No AI recommendations received from core engine", true);
      }

      for (const tab in manualBackup) {
        const manualList = manualBackup[tab];
        if (!manualList?.length) continue;
        if (!state.simulasi[tab]) continue;

        const current = state.simulasi[tab].tindakan || [];
        const merged = [
          ...current.filter(
            (it) =>
              !manualList.some((m) => m.procedure_text === it.procedure_text)
          ),
          ...manualList,
        ];
        state.simulasi[tab].tindakan = merged;
      }

      window.syncHiddenInputs && window.syncHiddenInputs();
    } catch (err) {
      console.error("❌ Error generate AI:", err);
      showToast("Gagal generate AI", true);
    } finally {
      document.getElementById("ai-loading")?.remove();
    }
  }

  // ============================================================
  // 🧠 Generate Summary
  // ============================================================
  async function generateSummary() {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return showToast("❌ Claim ID tidak ditemukan.", true);

    try {
      const state = Alpine.$data(document.getElementById("claimRoot"));

      const payload = {
        claim_id: parseInt(claimId),
        simulasi: state.simulasi,
        primary_claim: "Primary diagnosis",
        secondary_claims: [],
        primary_action: "Primary procedure",
        secondary_actions: [],
      };

      const res = await fetch(`/claims/${claimId}/generate_claim_combos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok)
        throw new Error(`HTTP ${res.status} - Gagal request evaluasi`);

      const result = await res.json();
      console.log("🔍 Core engine evaluasi result:", result);
      const data = result.data || result;

      window.renderEvaluasiDiagnosis &&
        window.renderEvaluasiDiagnosis(
          data.evaluasi_diagnosis || data.diagnosis || {}
        );
      window.renderEvaluasiProcedure &&
        window.renderEvaluasiProcedure(
          data.evaluasi_tindakan || data.procedure || {}
        );
      window.renderEvaluasiIDRGSummary &&
        window.renderEvaluasiIDRGSummary(data.idrg_summary || {});
      window.renderAlternatifKombinasi &&
        window.renderAlternatifKombinasi(data.alternatif || []);

      const summaryField = document.getElementById("summaryField");
      if (summaryField) summaryField.value = JSON.stringify(data);
      window.claimState.summary = data;

      showToast("✅ Evaluasi berhasil digenerate");
    } catch (err) {
      console.error("❌ Error generate evaluasi:", err);
      showToast(`❌ Gagal generate evaluasi: ${err.message}`, true);
    } finally {
      window.syncHiddenInputs && window.syncHiddenInputs();
    }
  }

  // ============================================================
  // 💾 Save Draft (with CSRF retry)
  // ============================================================
  async function saveDraft(claimId, data = null) {
    try {
      const csrfInput = document.querySelector('input[name="csrf_token"]');
      const csrfMeta = document.querySelector('meta[name="csrf-token"]');
      const csrfGeneric = document.querySelector('[name="csrf_token"]');
      const csrfToken =
        csrfInput?.value || csrfMeta?.content || csrfGeneric?.value;

      const payload = data || get_form_as_dict();
      const formData = new FormData();

      if (csrfToken) {
        formData.append("csrf_token", csrfToken);
      } else {
        throw new Error("CSRF token required");
      }

      formData.append("payload", JSON.stringify(payload));

      const res = await fetch(`/claims/${claimId}/update-draft`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      if (!res.ok) {
      // kalau token invalid, coba refresh
      if (res.status === 403) {
        showToast("⏳ Refreshing CSRF token...", true);
        const refresh = await fetch("/claims/csrf/refresh");
        const data = await refresh.json();
        document.querySelector('input[name="csrf_token"]').value = data.csrf_token;
        showToast("🔁 CSRF token diperbarui, silakan simpan lagi");
      }
      throw new Error(`HTTP ${res.status}`);
    }
    
      const result = await res.json();
      console.log("📥 Draft saved successfully:", result);
      showToast("✅ Draft berhasil disimpan");
      // after success save
      const newTokenRes = await fetch("/claims/csrf/refresh");
      const newToken = await newTokenRes.json();
      document.querySelector('input[name="csrf_token"]').value = newToken.csrf_token;

      return result;
      // after success save
    } catch (err) {
      console.error("❌ Error save draft:", err);
      showToast(`Gagal menyimpan draft: ${err.message}`, true);
    }
  }
  window.saveDraft = saveDraft;
  window.get_form_as_dict = get_form_as_dict;

  // ============================================================
  // Helper: Form Extractor
  // ============================================================
  function get_form_as_dict() {
    const form = document.getElementById("claimForm");
    if (!form) {
      showToast("Form claimForm tidak ditemukan", true);
      return {};
    }

    const formData = new FormData(form);
    const result = {};

    for (let [key, value] of formData.entries()) {
      result[key] = value;
    }

    const claimRoot = document.getElementById("claimRoot");
    if (claimRoot && typeof Alpine !== "undefined") {
      try {
        const state = Alpine.$data(claimRoot);
        if (state && state.simulasi) {
          console.log("🔍 [SAVE_DEBUG] Current state.simulasi:", state.simulasi);
          
          // 🎯 TRANSFORM: Convert frontend structure to backend-expected format
          const transformedSimulasi = transformSimulasiForBackend(state.simulasi);
          console.log("🔄 [SAVE_DEBUG] Transformed simulasi:", transformedSimulasi);
          
          result.simulasi = JSON.stringify(transformedSimulasi);
        }
        if (window.claimState && window.claimState.summary)
          result.summary = JSON.stringify(window.claimState.summary);
      } catch (err) {
        console.warn("⚠️ Could not extract Alpine state:", err);
      }
    }

    return result;
  }

  // ============================================================
  // Utilities (Search, Load)
  // ============================================================
  async function loadSimulations(claimId) {
    try {
      const res = await fetch(`/claims/${claimId}/simulations`);
      if (!res.ok) return;
      const body = await res.json();
      const sims = body.data || [];

      console.log(`🔄 [LOAD_SIMULATIONS] Loading ${sims.length} simulation records for claim ${claimId}`);

      sims.forEach((s, index) => {
        console.log(`📄 Processing simulation ${index + 1}:`, {
          stage: s.stage,
          primary_diag: s.diagnosis_utama_name,
          secondary_diag: s.diagnosis_sekunder_name,
          primary_action: s.tindakan_utama_name,
          secondary_action: s.tindakan_sekunder_name
        });

        // 🎯 PRIMARY DIAGNOSIS
        if (s.diagnosis_utama_id) {
          setTimeout(
            () => {
              console.log(`✅ Loading PRIMARY diagnosis: ${s.diagnosis_utama_name} (stage: ${s.stage})`);
              window.updateSimulasi("diagnosis", "Primary", {
                id: s.diagnosis_utama_id,
                name: s.diagnosis_utama_name || "(tanpa nama)",
                mapping: "Primary",
              }, true, s.stage);
            },
            index * 10 // Stagger timing to avoid conflicts
          );
        }

        // 🎯 SECONDARY DIAGNOSIS  
        if (s.diagnosis_sekunder_id) {
          setTimeout(
            () => {
              console.log(`✅ Loading SECONDARY diagnosis: ${s.diagnosis_sekunder_name} (stage: ${s.stage})`);
              window.updateSimulasi("diagnosis", "Secondary", {
                id: s.diagnosis_sekunder_id,
                name: s.diagnosis_sekunder_name || "(tanpa nama)",
                mapping: "Secondary",
              }, true, s.stage);
            },
            index * 10 + 5
          );
        }

        // 🎯 PRIMARY ACTION
        if (s.tindakan_utama_id) {
          setTimeout(
            () => {
              console.log(`✅ Loading PRIMARY action: ${s.tindakan_utama_name} (stage: ${s.stage})`);
              window.updateSimulasi("tindakan", "Primary Action", {
                id: s.tindakan_utama_id,
                name: s.tindakan_utama_name || "(tanpa nama)",
                mapping: "Primary Action",
              }, true, s.stage);
            },
            index * 10 + 10
          );
        }

        // 🎯 SECONDARY ACTION
        if (s.tindakan_sekunder_id) {
          setTimeout(
            () => {
              console.log(`✅ Loading SECONDARY action: ${s.tindakan_sekunder_name} (stage: ${s.stage})`);
              window.updateSimulasi("tindakan", "Secondary Actions", {
                id: s.tindakan_sekunder_id,
                name: s.tindakan_sekunder_name || "(tanpa nama)",
                mapping: "Secondary Actions",
              }, true, s.stage);
            },
            index * 10 + 15
          );
        }
      });

      console.log(`🎉 [LOAD_SIMULATIONS] Completed loading simulations for claim ${claimId}`);
    } catch (e) {
      console.error("❌ [LOAD_SIMULATIONS] Gagal load simulations:", e);
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


  // ============================================================
// 🧾 Submit Verification (Coder)
// ============================================================
async function submitCoderVerification(claimId, payload) {
  try {
    const csrfToken =
      document.querySelector('input[name="csrf_token"]')?.value ||
      document.querySelector('meta[name="csrf-token"]')?.content;

    const headers = { "Content-Type": "application/json" };
    if (csrfToken) headers["X-CSRF-Token"] = csrfToken;

    const res = await fetch(`/claims/${claimId}/coder`, {
      method: "POST",
      headers,
      credentials: "include",
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const errText = await res.text();
      console.error("❌ Verification failed:", errText);
      showToast("Gagal verifikasi klaim", true);
      return null;
    }

    const data = await res.json();
    console.log("✅ Verification success:", data);
    showToast("✅ Verifikasi berhasil dikirim");
    return data;
  } catch (err) {
    console.error("❌ Error submit verification:", err);
    showToast("❌ Gagal kirim verifikasi", true);
  }
}

window.submitCoderVerification = submitCoderVerification;


  // ============================================================
  // Exports
  // ============================================================
  window.generateAI = generateAI;
  window.generateSummary = generateSummary;
  window.loadSimulations = loadSimulations;
  // ============================================================
  // � Rules Functions
  // ============================================================
  
  async function loadRules(diagnosisName) {
    try {
      const response = await fetch(`/claims/rules/check/${encodeURIComponent(diagnosisName)}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      return result;
    } catch (error) {
      console.error('Error loading rules:', error);
      showToast(`Gagal memuat aturan: ${error.message}`, true);
      throw error;
    }
  }

  // ============================================================
  // �🔄 Feedback Functions
  // ============================================================
  
  async function submitRuleFeedback(ruleId, feedback) {
    try {
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
      
      const response = await fetch(`/claims/rules/${ruleId}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ feedback })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const result = await response.json();
      showToast('Masukan berhasil dikirim! Terima kasih atas kontribusi Anda.', false);
      return result;
    } catch (error) {
      console.error('Error submitting feedback:', error);
      showToast(`Gagal mengirim masukan: ${error.message}`, true);
      throw error;
    }
  }

  // ============================================================
  // TRANSFORM SIMULASI FOR BACKEND
  // ============================================================
  function transformSimulasiForBackend(frontendSimulasi) {
    /**
     * Transform frontend simulasi structure to backend-expected format
     * 
     * Frontend: { stage: { utama: {...}, sekunder: [...], tindakanUtama: {...}, tindakanSekunder: [...] } }
     * Backend Expected: { stage: { diagnosis: [...], komorbid: [...], komplikasi: [...], tindakan: [...] } }
     */
    const transformed = {};
    
    for (const [stage, stageData] of Object.entries(frontendSimulasi)) {
      if (!stageData || typeof stageData !== 'object') continue;
      
      transformed[stage] = {
        diagnosis: [],
        komorbid: [],
        komplikasi: [],
        tindakan: []
      };
      
      // 🎯 PRIMARY DIAGNOSIS (utama)
      if (stageData.utama) {
        const primaryDiag = {
          ...stageData.utama,
          mapping: "Primary" // Ensure consistent mapping
        };
        transformed[stage].diagnosis.push(primaryDiag);
        console.log(`🔄 [TRANSFORM] Added PRIMARY diagnosis: ${primaryDiag.name}`);
      }
      
      // 🎯 SECONDARY DIAGNOSES (sekunder)
      if (Array.isArray(stageData.sekunder)) {
        stageData.sekunder.forEach(diag => {
          if (diag && typeof diag === 'object') {
            const secondaryDiag = {
              ...diag,
              mapping: diag.mapping || "Secondary" // Ensure mapping
            };
            
            // Categorize by mapping type
            if (diag.mapping === "Komorbid" || diag.mapping === "Secondary-Komorbid") {
              transformed[stage].komorbid.push(secondaryDiag);
              console.log(`🔄 [TRANSFORM] Added KOMORBID: ${diag.name}`);
            } else if (diag.mapping === "Komplikasi" || diag.mapping === "Secondary-Komplikasi") {
              transformed[stage].komplikasi.push(secondaryDiag);
              console.log(`🔄 [TRANSFORM] Added KOMPLIKASI: ${diag.name}`);
            } else {
              transformed[stage].diagnosis.push(secondaryDiag);
              console.log(`🔄 [TRANSFORM] Added SECONDARY diagnosis: ${diag.name}`);
            }
          }
        });
      }
      
      // 🎯 PRIMARY ACTION (tindakanUtama)
      if (stageData.tindakanUtama) {
        const primaryAction = {
          ...stageData.tindakanUtama,
          mapping: "Primary Action" // Ensure consistent mapping
        };
        transformed[stage].tindakan.push(primaryAction);
        console.log(`🔄 [TRANSFORM] Added PRIMARY action: ${primaryAction.name}`);
      }
      
      // 🎯 SECONDARY ACTIONS (tindakanSekunder)
      if (Array.isArray(stageData.tindakanSekunder)) {
        stageData.tindakanSekunder.forEach(action => {
          if (action && typeof action === 'object') {
            const secondaryAction = {
              ...action,
              mapping: "Secondary Actions" // Ensure consistent mapping
            };
            transformed[stage].tindakan.push(secondaryAction);
            console.log(`🔄 [TRANSFORM] Added SECONDARY action: ${action.name}`);
          }
        });
      }
      
      // 🎯 LEGACY: Also include arrays from original structure if they exist
      ['diagnosis', 'komorbid', 'komplikasi', 'tindakan'].forEach(category => {
        if (Array.isArray(stageData[category])) {
          stageData[category].forEach(item => {
            if (item && typeof item === 'object' && !transformed[stage][category].some(existing => existing.name === item.name)) {
              transformed[stage][category].push(item);
              console.log(`🔄 [TRANSFORM] Added legacy ${category}: ${item.name}`);
            }
          });
        }
      });
    }
    
    console.log(`🎉 [TRANSFORM] Transformation complete for ${Object.keys(transformed).length} stages`);
    return transformed;
  }

  window.searchDiagnosis = searchDiagnosis;
  window.getDiagnosisDetail = getDiagnosisDetail;
  window.searchTindakan = searchTindakan;
  window.getTindakanDetail = getTindakanDetail;
  window.saveDraft = saveDraft;
  window.get_form_as_dict = get_form_as_dict;
  window.loadRules = loadRules;
  window.submitRuleFeedback = submitRuleFeedback;
  window.transformSimulasiForBackend = transformSimulasiForBackend;
})();