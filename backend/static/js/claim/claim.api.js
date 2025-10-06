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
      // 🔹 Fetch utama rekomendasi AI
      const res = await fetch("/claims/ai/recommendation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim_id: claimId })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const result = await res.json();
      const rows = result.data || [];
      console.log("🔍 result.data:", rows);

      // ------------------------------------------------------------------
      // 🧠 PREFETCH semua detail diagnosis untuk ambil tindakan AI-nya
      // ------------------------------------------------------------------
      window.claimState.cache = window.claimState.cache || {};
      if (!Array.isArray(window.claimState.cache.tindakanAI))
        window.claimState.cache.tindakanAI = [];

      // buat semua request paralel
      const detailPromises = rows.map(async row => {
        const url = `/claims/ai/recommendation/detail?claim_id=${claimId}&rec_type=diagnosis&item_id=${row.id}`;
        try {
          const res = await fetch(url);
          if (!res.ok) return [];
          const detail = await res.json();
          const tindakanList = detail.data?.data?.tindakan || detail.data?.tindakan || [];
          return tindakanList.map(td => ({
            ...td,
            stage: row.stage || "admission",
            isManual: false,
            source: "AI",
          }));
        } catch (e) {
          console.warn("prefetch gagal:", e);
          return [];
        }
      });

      const allDetails = (await Promise.all(detailPromises)).flat();
      window.claimState.cache.tindakanAI.push(...allDetails);
      console.log("✅ Cache tindakanAI global:", window.claimState.cache.tindakanAI.length);

      // ------------------------------------------------------------------
      // 🔹 Render tabel AI + update simulasi state
      // ------------------------------------------------------------------
      window.renderAI && window.renderAI(rows);

      const tindakanAll = [];

      // dari nested tindakan di tiap diagnosis (kalau ada)
      rows.forEach(row => {
        if (Array.isArray(row.tindakan) && row.tindakan.length) {
          row.tindakan.forEach(td => {
            tindakanAll.push({
              ...td,
              diagnosis_id: row.id,
              diagnosis_code: row.icd10_code,
              stage: row.stage || "admission",
              isManual: false,
              source: "AI",
            });
          });
        }
      });

      // tambahkan hasil prefetch detail ke list tindakanAll
      tindakanAll.push(...allDetails);

      // simpan ke simulasi agar bisa dibaca cache global
      tindakanAll.forEach(td => {
        const stage = td.stage || "admission";
        if (!window.claimState.simulasi[stage]) window.claimState.simulasi[stage] = {};
        if (!Array.isArray(window.claimState.simulasi[stage].tindakan))
          window.claimState.simulasi[stage].tindakan = [];
        window.claimState.simulasi[stage].tindakan.push(td);
      });

      console.log("✅ Tindakan AI global ditambahkan:", tindakanAll.length);

      // sinkronisasi cache global
      setTimeout(() => {
        const allAI = [];
        Object.values(window.claimState.simulasi).forEach(stageObj => {
          if (Array.isArray(stageObj.tindakan)) {
            allAI.push(...stageObj.tindakan.filter(td => !(td.isManual || td.is_manual)));
          }
        });
        window.claimState.cache.tindakanAI = allAI;
        console.log("✅ [Synced] Cache tindakanAI global:", allAI.length, "item");
      }, 500);

      // ------------------------------------------------------------------
      // 3️⃣ Kembalikan tindakan manual yg dibackup sebelumnya
      // ------------------------------------------------------------------
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

      // ------------------------------------------------------------------
      // 4️⃣ Refresh tampilan list tindakan di modal
      // ------------------------------------------------------------------
      Object.keys(state.simulasi).forEach(tab => {
        window.renderManualTindakanList &&
          window.renderManualTindakanList(tab);
      });

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

  // Export API
  window.generateAI = generateAI;
  window.generateSummary = generateSummary;
  window.loadSimulations = loadSimulations;
  window.searchDiagnosis = searchDiagnosis;
  window.getDiagnosisDetail = getDiagnosisDetail;
  window.searchTindakan = searchTindakan;
  window.getTindakanDetail = getTindakanDetail;
})();
