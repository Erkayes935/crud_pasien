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
        const errorData = await res.json().catch(() => ({}));
        if (
          res.status === 403 &&
          errorData.detail &&
          errorData.detail.includes("CSRF")
        ) {
          showToast("CSRF expired. Refresh page and retry.", true);
        }
        throw new Error(
          `HTTP error! status: ${res.status} - ${errorData.detail || ""}`
        );
      }

      const result = await res.json();
      console.log("📥 Draft saved successfully:", result);
      showToast("✅ Draft berhasil disimpan");
      return result;
    } catch (err) {
      console.error("❌ Error save draft:", err);
      showToast(`Gagal menyimpan draft: ${err.message}`, true);
    }
  }

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
        if (state && state.simulasi) result.simulasi = JSON.stringify(state.simulasi);
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

      sims.forEach((s) => {
        if (s.diagnosis_utama_id)
          setTimeout(
            () =>
              window.updateSimulasi("diagnosis", "Primary", {
                id: s.diagnosis_utama_id,
                name: s.diagnosis_utama_name || "(tanpa nama)",
                mapping: "Primary",
              }, true, s.stage),
            0
          );
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

  // ============================================================
  // Exports
  // ============================================================
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
