// =============== Komunikasi ke Backend (fetch) ===============

// =============== Komunikasi ke Backend (fetch) ===============
(function () {
  // ============================================================
  // 🔔 Universal Toast Function (popup auto-hide)
  // ============================================================
  function showToast(message, isError = false, duration = 3000) {
    const existing = document.getElementById("global-toast");
    if (existing) existing.remove();

    const div = document.createElement("div");
    div.id = "global-toast";
    div.textContent = message;

    Object.assign(div.style, {
      position: "fixed",
      bottom: "30px",
      right: "30px",
      background: isError ? "#dc2626" : "#16a34a",
      color: "#fff",
      padding: "12px 18px",
      borderRadius: "8px",
      boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
      fontSize: "14px",
      fontWeight: "500",
      zIndex: 9999,
      opacity: "0",
      transition: "opacity 0.3s ease, transform 0.3s ease",
      transform: "translateY(20px)"
    });

    document.body.appendChild(div);
    requestAnimationFrame(() => {
      div.style.opacity = "1";
      div.style.transform = "translateY(0)";
    });

    setTimeout(() => {
      div.style.opacity = "0";
      div.style.transform = "translateY(20px)";
      setTimeout(() => div.remove(), 400);
    }, duration);
  }

  // ============================================================
  // 🔮 Generate AI
  // ============================================================
  async function generateAI() {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return showToast("❌ Claim ID tidak ditemukan.", true);

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
      console.log("📥 Data core_engine:", result);

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

      showToast("✅ AI recommendations generated successfully");
    } catch (err) {
      console.error("❌ Error generate AI:", err);
      showToast(`❌ Gagal generate AI: ${err.message}`, true);
    } finally {
      document.getElementById("ai-loading")?.remove();
    }
  }

  // ============================================================
  // 💾 SAVE DRAFT UNIVERSAL
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

      console.log("📤 Sending draft as FormData:", Object.fromEntries(formData));

      const res = await fetch(`/claims/${claimId}/update-draft`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Gagal simpan draft (HTTP ${res.status}): ${text}`);
      }

      // 🚫 Jangan auto-refresh walau backend redirect
      console.log("✅ Draft saved successfully (no page reload)");
      showToast("💾 Draft berhasil disimpan");
    } catch (err) {
      console.error("❌ Error saat menyimpan draft:", err);
      showToast(`❌ Gagal menyimpan draft: ${err.message}`, true);
    }
  }
  window.saveDraft = saveDraft;

  window.saveDraft = saveDraft;
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
    if (!claimId) return showToast("❌ Claim ID tidak ditemukan.", true);

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

      showToast("✅ Summary berhasil digenerate");
    } catch (err) {
      console.error("❌ Error generate summary:", err);
      showToast(`❌ Gagal generate summary: ${err.message}`, true);
    } finally {
      document.getElementById("summary-loading")?.remove();
      window.syncHiddenInputs && window.syncHiddenInputs();
    }
  }

  // ============================================================
  // 🩺 Resume Medis
  // ============================================================
  async function generateResumeMedis(claimId) {
    if (!claimId) return showToast("❌ Claim ID tidak ditemukan.", true);
    try {
      const res = await fetch("/resume_medis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim_id: claimId }),
      });
      const result = await res.json();
      console.log("📥 Resume medis:", result);
      showToast("✅ Resume medis berhasil dibuat");
      return result;
    } catch (err) {
      console.error("❌ Error generate resume medis:", err);
      showToast("❌ Gagal generate resume medis", true);
    }
  }

  // ============================================================
  // Exports
  // ============================================================
  window.generateAI = generateAI;
  window.generateSummary = generateSummary;
  window.generateResumeMedis = generateResumeMedis;
})();