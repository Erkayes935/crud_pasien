// =============== State Alpine + helper struktur simulasi ===============

(function () {
  function ensureDaily(dayId) {
    const state = Alpine.$data(document.getElementById("claimRoot"));
    if (!state.manualInput.daily) state.manualInput.daily = {};
    if (!state.manualInput.daily[dayId]) {
      state.manualInput.daily[dayId] = {
        diagnosis: { kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" },
        komorbid:  { kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" },
        komplikasi:{ kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" }
      };
    }
  }

  // normalisasi opsi mapping
  function normalizeOpt(opt) {
    if (opt === "Diagnosis Utama" || opt === "Utama" || opt === "Primary Claim" || opt === "Primary") return "Primary";
    if (opt === "Komorbid" || opt === "Secondary-Komorbid") return "Secondary-Komorbid";
    if (opt === "Komplikasi" || opt === "Secondary-Komplikasi") return "Secondary-Komplikasi";
    if (opt === "Sekunder" || opt === "Secondary Claim" || opt === "Secondary") return "Secondary";
    if (opt === "None") return "None";
    return opt;
  }

  function normalizeItem(val) {
    if (typeof val === "string") {
      return { name: val.split(" [")[0] || "", label: "", mapping: "", source: "Manual", isManual: true };
    }
    return {
      ...val,
      name: val.name || val.kategori || val.icd || "-",
      label: val.label || "",
      mapping: val.mapping || ""
    };
  }

  function normalizeProcedure(td) {
    if (!td) return { nama: "" };
    return { ...td, nama: td.nama || td.name || td.procedure_text || td.kategori || "" };
  }

  // state utama (dipasang via x-data="claimData(init)")
  function claimData(init) {
    const state = {
      role: init.role || 'doctor', // doctor, verifikator, coder
      tab: init.tab || 'admission',
      form: {},

      // simulasi hasil AI
      simulasi: init.sim || {
        admission: { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null },
        "daily-0": { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null },
        "daily-1": { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null },
        discharge: { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null },
        daily: { days: [], utama: null, sekunder: [] }
      },

      // cache tindakan untuk coder
      cache: { tindakanAI: [] },

      // evaluasi (summary)
      evaluasiDiagnosis: [],
      evaluasiProcedure: [],
      alternatifKombinasi: [],

      // manual input flags
      showManual: {
        admission: { diagnosis:false, komorbid:false, komplikasi:false },
        daily: {},
        discharge: { diagnosis:false, komorbid:false, komplikasi:false }
      },
      manualInput: {
        admission: {
          diagnosis: { kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" },
          komorbid: { kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" },
          komplikasi: { kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" }
        },
        discharge: {
          diagnosis: { kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" },
          komorbid: { kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" },
          komplikasi: { kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" }
        },
        daily: {}
      },

      // ======================== NOTE SYSTEM (sinkron BE) ========================
      notes: {
        admission: {},
        discharge: {},
        daily: {},
        primary_diagnosis: [],
        secondary_diagnosis: [],
        primary_action: [],
        secondary_action: []
      },
      currentNoteItem: null,
      currentNoteField: null,
      currentNoteStage: null,

      // modal
      modalOpen: false,
      modalTitle: '',
      modalContent: '',
      hideDefaultClose: false,
      currentDiagnosis: null,
      currentProcedure: null,

      // rules modal
      rulesModalOpen: false,

      // feedback modal
      feedbackModalOpen: false,
      selectedFeedbackRule: null,
      feedbackForm: { feedback: '' },
      feedbackSubmitting: false,

      init() {
        const role = this.role;
        const claimId = document.getElementById("claimRoot")?.dataset.claimId;
        if ((role === 'verifikator' || role === 'doctor') && claimId) {
          setTimeout(() => window.loadSimulations && window.loadSimulations(claimId), 0);
        }
      },

      statusIcon(s) {
        if (!s) return "";
        const val = String(s).trim().toLowerCase();
        if (val === "invalid") return "❌";
        if (val === "warning" || val.includes("optional")) return "⚠️";
        if (val === "valid") return "✅";
        return "";
      }
    };

    window.claimState = state;
    return state;
  }

  // updateSimulasi
  function updateSimulasi(type, opt, value, source, tab) {
    const state = Alpine.$data(document.getElementById("claimRoot"));
    if (!tab) tab = "admission";
    const finalOpt = normalizeOpt(opt || value?.mapping || "");

    if (!state.simulasi[tab] || typeof state.simulasi[tab] !== "object" || Array.isArray(state.simulasi[tab])) {
      state.simulasi[tab] = {};
    }
    let sim = state.simulasi[tab];

    if (!("utama" in sim)) sim.utama = null;
    if (!Array.isArray(sim.sekunder)) sim.sekunder = [];
    if (!("tindakanUtama" in sim)) sim.tindakanUtama = null;
    if (!Array.isArray(sim.tindakanSekunder)) sim.tindakanSekunder = [];

    const item = (typeof value === "string")
      ? { id: null, name: value.split(" [")[0] || "", label: "", source: "Manual", isManual: true }
      : {
          ...value,
          id: value.id || null,
          name: value.name || value.diagnosis_utama_name || value.diagnosis_sekunder_name ||
                value.tindakan_utama_name || value.tindakan_sekunder_name || "(tanpa nama)",
          label: value.label || ""
        };

    if (source) {
      if (finalOpt === "Primary") item.label = "Utama Klinis";
      else if (finalOpt === "Secondary-Komorbid") item.label = "Komorbid";
      else if (finalOpt === "Secondary-Komplikasi") item.label = "Komplikasi";
    }

    // Diagnosis
    if (["diagnosis", "komorbid", "komplikasi"].includes(type)) {
      if (finalOpt === "Primary") {
        const oldPrimary = sim.utama;
        sim.sekunder = sim.sekunder.filter(dx => dx.name !== item.name);
        sim.utama = { diagnosis_utama_id: item.id, ...item };
        if (oldPrimary && oldPrimary.name !== item.name) sim.sekunder.unshift(oldPrimary);
      } else if (finalOpt.startsWith("Secondary")) {
        if (sim.utama && sim.utama.name === item.name) sim.utama = null;
        const idx = sim.sekunder.findIndex(dx => dx.name === item.name);
        const secItem = { diagnosis_sekunder_id: item.id, ...item };
        if (idx === -1) sim.sekunder.push(secItem);
        else sim.sekunder[idx] = secItem;
      } else if (finalOpt === "None") {
        if (sim.utama && sim.utama.name === item.name) sim.utama = null;
        sim.sekunder = sim.sekunder.filter(dx => dx.name !== item.name);
      }
    }

    // Tindakan
    if (type === "tindakan") {
      const nama = typeof value === "string" ? value : (value.name || value.label || "(tanpa nama)");
      const id = typeof value === "string" ? null : (value.id || null);

      if (finalOpt === "Primary") {
        const oldPrimary = sim.tindakanUtama;
        sim.tindakanSekunder = sim.tindakanSekunder.filter(td => td.name !== nama);
        sim.tindakanUtama = { tindakan_utama_id: id, name: nama };
        if (oldPrimary && oldPrimary.name !== nama) sim.tindakanSekunder.unshift(oldPrimary);
      } else if (finalOpt === "Secondary") {
        if (sim.tindakanUtama?.name === nama) sim.tindakanUtama = null;
        if (!sim.tindakanSekunder.find(td => td.name === nama)) {
          sim.tindakanSekunder.push({ tindakan_sekunder_id: id, name: nama });
        }
      } else if (finalOpt === "None") {
        if (sim.tindakanUtama?.name === nama) sim.tindakanUtama = null;
        sim.tindakanSekunder = sim.tindakanSekunder.filter(td => td.name !== nama);
      }
    }

    // Daily tab sync
    if (tab.startsWith("daily-")) {
      const idxDay = parseInt(tab.split("-")[1], 10);
      if (!state.simulasi.daily.days) state.simulasi.daily.days = [];
      state.simulasi.daily.days[idxDay] = state.simulasi[tab];
      state.simulasi.daily.utama = null;
      state.simulasi.daily.sekunder = [];
      state.simulasi.daily.days.forEach(d => {
        if (d?.utama && !state.simulasi.daily.utama) state.simulasi.daily.utama = d.utama;
        if (Array.isArray(d?.sekunder)) state.simulasi.daily.sekunder.push(...d.sekunder);
      });
    }

    window.syncHiddenInputs && window.syncHiddenInputs();
  }

  // onMappingChange handler
  function onMappingChange(event, tab, type, itemId) {
    try {
      console.log("🔍 onMappingChange called:", { tab, type, itemId, value: event.target.value });
      
      // Ensure Alpine state is available
      const claimRoot = document.getElementById('claimRoot');
      if (!claimRoot) {
        console.error("❌ claimRoot element not found");
        return;
      }
      
      const state = Alpine.$data(claimRoot);
      if (!state) {
        console.error("❌ Alpine state not available");
        return;
      }
      
      const arr = state.simulasi?.[tab]?.[type] || [];
      
      console.log("🔍 Available items in simulasi[" + tab + "][" + type + "]:", arr);
      console.log("🔍 Looking for itemId:", itemId, "type:", typeof itemId);
      
      const keyDecoded = decodeURIComponent(itemId || "");
      const item = arr.find(it => {
        const keyCandidate = `${tab}-${type}-${it.kategori}`;
        return keyCandidate === keyDecoded;
      });
      
      console.log("🔍 Found item:", item);

      if (!item) {
        console.error("❌ onMappingChange: item not found", { tab, type, itemId, availableItems: arr });
        return;
      }

      const opt = event.target.value;
      console.log("✅ Found item, mapping to:", opt);
      item.mapping = opt;
      
      // Call updateSimulasi with error handling
      if (typeof updateSimulasi === 'function') {
        updateSimulasi(type, opt, normalizeItem(item), item.source || (item.isManual ? "Manual" : "AI"), tab);
      } else {
        console.error("❌ updateSimulasi function not available");
      }
    } catch (error) {
      console.error("❌ onMappingChange error:", error);
    }
  }

  // Expose
  window.claimData = claimData;
  window.ensureDaily = ensureDaily;
  window.updateSimulasi = updateSimulasi;
  window.onMappingChange = onMappingChange;
  window.normalizeProcedure = normalizeProcedure;
})();