// =============== Komunikasi ke Backend (fetch) ===============

(function () {
  async function generateAI() {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return alert("❌ Claim ID tidak ditemukan.");

    try {
      // 🔥 Update untuk core_engine
      const state = Alpine.$data(document.getElementById("claimRoot"));
      const stage = state.tab || "admission";
      const res = await fetch("/generate_ai/predict_ddx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim_id: claimId, stage })
      });
      const result = await res.json();
      console.log("📥 Data core_engine:", result);
      
      // 🔥 Render each category separately untuk compatibility dengan core_engine
      if (result.diagnosis) {
        console.log("🔥 DEBUG diagnosis:", result.diagnosis);
        window.renderAI && window.renderAI(result.diagnosis, "diagnosis", stage);
      }
      if (result.komorbid) {
        console.log("🔥 DEBUG komorbid:", result.komorbid);
        window.renderAI && window.renderAI(result.komorbid, "komorbid", stage);
      }
      if (result.komplikasi) {
        console.log("🔥 DEBUG komplikasi:", result.komplikasi);
        window.renderAI && window.renderAI(result.komplikasi, "komplikasi", stage);
      }
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

window.searchDiagnosis = searchDiagnosis;
window.getDiagnosisDetail = getDiagnosisDetail;

  async function generateSummary() {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return alert("❌ Claim ID tidak ditemukan.");

    try {
      const state = Alpine.$data(document.getElementById("claimRoot"));
      const payload = { claim_id: claimId, simulasi: state.simulasi };

      const res = await fetch(`/claims/ai/summary/${claimId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Gagal request summary");

      const data = await res.json();

      window.renderEvaluasiDiagnosis && window.renderEvaluasiDiagnosis(data.diagnosis || {});
      window.renderEvaluasiProcedure && window.renderEvaluasiProcedure(data.procedure || {});
      window.renderEvaluasiIDRGSummary && window.renderEvaluasiIDRGSummary(data.idrg_summary || {});
      window.renderAlternatifKombinasi && window.renderAlternatifKombinasi(data.alternatif || []);

      const summaryField = document.getElementById("summaryField");
      if (summaryField) summaryField.value = JSON.stringify(data);
      window.claimState.summary = data;

      alert("✅ Summary berhasil digenerate");
    } catch (err) {
      console.error("Error generate summary:", err);
      alert("❌ Gagal generate summary");
    } finally {
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
