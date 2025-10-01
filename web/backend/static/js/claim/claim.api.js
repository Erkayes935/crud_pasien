// =============== Komunikasi ke Backend (fetch) ===============

(function () {
  async function generateAI() {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return alert("❌ Claim ID tidak ditemukan.");

    try {
      const state = Alpine.$data(document.getElementById("claimRoot"));
      const stage = state.tab || "admission";

      // ✅ endpoint baru
      const res = await fetch(`/claims/${claimId}/predict_ddx`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stage })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const result = await res.json();

      const allData = []
        .concat((result.diagnosis || []).map(r => ({ ...r, category: "diagnosis", stage })))
        .concat((result.komorbid  || []).map(r => ({ ...r, category: "komorbid", stage })))
        .concat((result.komplikasi|| []).map(r => ({ ...r, category: "komplikasi", stage })));

      window.renderAI && window.renderAI(allData);
    } catch (err) {
      console.error("❌ Error generate AI:", err);
      alert("Gagal generate AI dari core_engine");
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

  async function generateSummary() {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return;

    try {
      const state = Alpine.$data(document.getElementById("claimRoot"));
      const res = await fetch(`/claims/${claimId}/generate_claim_combos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ simulasi: state.simulasi })
      });
      if (!res.ok) throw new Error("Gagal request summary");

      const result = await res.json();

      window.renderEvaluasiDiagnosis && window.renderEvaluasiDiagnosis(result.evaluasiDiagnosis || {});
      window.renderEvaluasiProcedure && window.renderEvaluasiProcedure(result.evaluasiProcedure || {});
      window.renderAlternatifKombinasi && window.renderAlternatifKombinasi(result.alternatifKombinasi || []);

      // Hidden field & state summary
      const summaryField = document.getElementById("summaryField");
      if (summaryField) summaryField.value = JSON.stringify(result);
      window.claimState.summary = result;

      alert("✅ Evaluasi klaim berhasil digenerate");
    } catch (err) {
      console.error("❌ Error generate summary:", err);
      alert("Gagal generate evaluasi klaim");
    } finally {
      window.syncHiddenInputs && window.syncHiddenInputs();
    }
  }

  // Export API
  window.generateAI = generateAI;
  window.generateSummary = generateSummary;
  window.loadSimulations = loadSimulations;
})();
