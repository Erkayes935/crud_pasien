// =============== Komunikasi ke Backend (fetch) ===============

(function () {
  // ============================================================
  // 🔔 Universal Toast Function (popup auto-hide) - Enhanced Elegant Design
  // ============================================================
  function showToast(message, isError = false, duration = 4000) {
    // Remove existing toast to prevent overlaps
    const existing = document.getElementById("global-toast");
    if (existing) existing.remove();

    const div = document.createElement("div");
    div.id = "global-toast";
    div.textContent = message;
    div.setAttribute("role", "alert"); // Accessibility improvement
    div.setAttribute("aria-live", "polite");

    // Modern color palette (inspired by Tailwind CSS for elegance)
    const bgColor = isError ? "#ef4444" : "#10b981"; // Red-500 / Green-500
    const shadowColor = isError ? "rgba(239, 68, 68, 0.3)" : "rgba(16, 185, 129, 0.3)";

    Object.assign(div.style, {
      position: "fixed",
      top: "20px", // Changed to top-right for modern feel (bottom-right alternative: bottom: "20px")
      right: "20px",
      background: `linear-gradient(135deg, ${bgColor} 0%, ${isError ? "#dc2626" : "#059669"} 100%)`, // Subtle gradient for depth
      color: "#ffffff",
      padding: "16px 20px", // Slightly more padding for breathing room
      borderRadius: "12px", // Softer, more modern radius
      boxShadow: `
        0 20px 25px -5px ${shadowColor},
        0 10px 10px -5px rgba(0, 0, 0, 0.1),
        0 0 0 1px rgba(255, 255, 255, 0.05) // Subtle inner glow
      `,
      fontSize: "14px",
      fontWeight: "500",
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif", // Modern system font stack
      lineHeight: "1.4", // Better readability
      maxWidth: "350px", // Prevent overflow on long messages
      wordWrap: "break-word",
      zIndex: 9999,
      opacity: "0",
      transform: "translateX(100%) scale(0.95)", // Slide in from right with subtle scale for elegance
      transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)", // Smooth easing curve (ease-out)
      backdropFilter: "blur(10px)", // Optional: subtle blur for modern glassmorphism (if supported)
      border: "1px solid rgba(255, 255, 255, 0.1)" // Subtle border for definition
    });

    document.body.appendChild(div);

    // Animate in
    requestAnimationFrame(() => {
      div.style.opacity = "1";
      div.style.transform = "translateX(0) scale(1)";
    });

    // Auto-hide with animation
    setTimeout(() => {
      div.style.opacity = "0";
      div.style.transform = "translateX(100%) scale(0.95)";
      setTimeout(() => div.remove(), 500); // Slightly longer exit transition
    }, duration);
  }

  // ============================================================
  // 🔮 Generate AI
  // ============================================================
  async function generateAI() {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return showToast("Claim ID tidak ditemukan.", true);

    try {
      const state = Alpine.$data(document.getElementById("claimRoot"));
      const stage = state.tab || "admission";

      const loadingMsg = document.createElement("div");
      loadingMsg.id = "ai-loading";
      loadingMsg.style.cssText =
        "position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.8); color: white; padding: 20px; border-radius: 8px; z-index: 9999;";
      loadingMsg.innerHTML = "Generating AI recommendations...";
      document.body.appendChild(loadingMsg);

      const res = await fetch(`/claims/${claimId}/predict_ddx`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_id: claimId,
          stage,
          global_record: state.globalRecord || {},
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(
          errorData.detail?.error ||
          errorData.detail ||
          `HTTP ${res.status} error`
        );
      }

      const result = await res.json();
      console.log(" Data core_engine:", result);

      if (!result || typeof result !== "object") {
        throw new Error("Invalid response format from core_engine");
      }

      const categories = ["diagnosis", "komorbid", "komplikasi"];
      for (const category of categories) {
        if (Array.isArray(result[category])) {
          window.renderAI && window.renderAI(result[category], category, stage);
        }
      }

      await saveDraft(claimId, {
        ai_recommendations: result,
        stage,
      });

      showToast("AI recommendations generated successfully");
    } catch (err) {
      console.error("Error generate AI:", err);
      showToast(`Gagal generate AI: ${err.message}`, true);
    } finally {
      document.getElementById("ai-loading")?.remove();
    }
  }

  // ============================================================
  // SAVE DRAFT UNIVERSAL
  // ============================================================
  async function saveDraft(claimId) {
    try {
      const root = document.getElementById("claimRoot");
      const state = Alpine.$data(root);
      const csrfToken =
        document.querySelector("input[name='csrf_token']")?.value || "";

      const formData = new FormData();
      formData.append("csrf_token", csrfToken);
      formData.append("simulasi", JSON.stringify(state.simulasi || {}));
      formData.append(
        "summary",
        JSON.stringify(window.claimState?.summary || {})
      );
      formData.append(
        "ai_recommendations",
        JSON.stringify(state.ai_recommendations || {})
      );
      formData.append("stage", state.tab || "admission");

      console.log("Sending draft as FormData:", Object.fromEntries(formData));

      const res = await fetch(`/claims/${claimId}/update-draft`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Gagal simpan draft (HTTP ${res.status}): ${text}`);
      }

      // Jangan auto-refresh walau backend redirect
      console.log("Draft saved successfully (no page reload)");
      showToast("Draft berhasil disimpan");
    } catch (err) {
      console.error("Error saat menyimpan draft:", err);
      showToast(`Gagal menyimpan draft: ${err.message}`, true);
    }
  }
  window.saveDraft = saveDraft;
  window.get_form_as_dict = get_form_as_dict;

  // Remove duplicate and simpler showToast definitions - use the enhanced one above
  // The following lines were duplicates and have been cleaned up

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

  // ============================================================
  // 🧠 Generate Summary
  // ============================================================
  async function generateSummary() {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return showToast("Claim ID tidak ditemukan.", true);

    try {
      const loadingMsg = document.createElement("div");
      loadingMsg.id = "summary-loading";
      loadingMsg.style.cssText =
        "position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.8); color: white; padding: 20px; border-radius: 8px; z-index: 9999;";
      loadingMsg.innerHTML = "Generating claim summary...";
      document.body.appendChild(loadingMsg);

      const state = Alpine.$data(document.getElementById("claimRoot"));
      const currentTab = state.tab || "admission";
      const simData = state.simulasi[currentTab];
      if (!simData) throw new Error("Tidak ada data simulasi di tab ini");

      const payload = {
        claim_id: parseInt(claimId),
        stage: currentTab,
        primary_claim: simData.utama?.name || "",
        secondary_claims:
          (simData.sekunder || []).map((d) => d.name).filter(Boolean),
        primary_action: simData.tindakanUtama?.name || "",
        secondary_actions: (simData.tindakanSekunder || [])
          .filter((t) => t && t.name)
          .map((t) => t.name),
      };

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
      const resultData = data.result || data;
      const diagnosisData =
        resultData.evaluasi_diagnosis || resultData.diagnosis || {};
      let procedureData =
        resultData.evaluasi_tindakan ||
        resultData.procedure ||
        resultData.rows ||
        [];

      window.renderEvaluasiDiagnosis &&
        window.renderEvaluasiDiagnosis(diagnosisData);
      window.renderEvaluasiProcedure &&
        window.renderEvaluasiProcedure(procedureData);

      showToast("Summary berhasil digenerate");
    } catch (err) {
      console.error("Error generate summary:", err);
      showToast(`Gagal generate summary: ${err.message}`, true);
    } finally {
      document.getElementById("summary-loading")?.remove();
      window.syncHiddenInputs && window.syncHiddenInputs();
    }
  }

  // ============================================================
  // 🩺 Resume Medis
  // ============================================================
  async function generateResumeMedis(claimId) {
    if (!claimId) return showToast("Claim ID tidak ditemukan.", true);
    try {
      const res = await fetch("/resume_medis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim_id: claimId }),
      });
      const result = await res.json();
      console.log("Resume medis:", result);
      showToast("Resume medis berhasil dibuat");
      return result;
    } catch (err) {
      console.error("Error generate resume medis:", err);
      showToast("Gagal generate resume medis", true);
    }
  }

  // ============================================================
  // Exports
  // ============================================================
  window.generateAI = generateAI;
  window.generateSummary = generateSummary;
  window.generateResumeMedis = generateResumeMedis;
  window.loadSimulations = loadSimulations;
  window.searchDiagnosis = searchDiagnosis;
  window.getDiagnosisDetail = getDiagnosisDetail;
  window.searchTindakan = searchTindakan;
  window.getTindakanDetail = getTindakanDetail;
})();