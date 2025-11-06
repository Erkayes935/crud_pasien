// =============== State Alpine + helper struktur simulasi ===============

(function () {
  function ensureDaily(dayId) {
    const state = Alpine.$data(document.getElementById("claimRoot"));
    if (!state.manualInput) state.manualInput = {};
    if (!state.manualInput.daily) state.manualInput.daily = {};
    if (!state.simulasi) state.simulasi = {};

    // 🔧 kalau "daily-global" belum ada, siapkan kosong
    if (!state.manualInput.daily["daily-global"]) {
      state.manualInput.daily["daily-global"] = {
        diagnosis: { kategori: "", klinis: "", icd10_code: "", procedure_text: "", score: "" },
        komorbid: { kategori: "", klinis: "", icd10_code: "", procedure_text: "", score: "" },
        komplikasi: { kategori: "", klinis: "", icd10_code: "", procedure_text: "", score: "" },
      };
    }

    // 🔧 pastikan struktur simulasi daily-global juga siap
    if (!state.simulasi["daily-global"]) {
      state.simulasi["daily-global"] = {
        diagnosis: [],
        komorbid: [],
        komplikasi: [],
        utama: null,
        sekunder: [],
        tindakan: [],
      };
    }
  }

  function renderDailyAccordion(state) {
    const container = document.getElementById("daily-accordion");
    if (!container) return;
    container.innerHTML = "";

    const days = state.simulasi.daily.days || [];
    if (days.length === 0) return;

    days.forEach((day, idx) => {
      const dayId = `daily-${idx}`;
      const isLast = idx === days.length - 1;

      container.insertAdjacentHTML("beforeend", `
        <div class="bg-white dark:bg-gray-700 rounded shadow-sm mb-2" x-data="{open:${isLast}}">
          <button type="button" @click="open=!open"
            class="w-full flex items-center justify-between px-4 py-2 bg-gray-200 dark:bg-gray-600 font-semibold">
            <div class="flex items-center gap-2">
              <span>Hari ke-${idx + 1} – ${formatDate(day.tanggal)}</span>
              ${!isLast
                ? '<span class="text-xs text-gray-500">(locked)</span>'
                : '<span class="text-xs text-green-600">(active)</span>'}
            </div>
            <div>
              <span x-show="open">⬆</span><span x-show="!open">⬇</span>
            </div>
          </button>

          <div x-show="open" class="p-3 space-y-3 ${!isLast ? 'opacity-60' : ''}">
            <details open class="border rounded">
              <summary class="cursor-pointer px-3 py-2 bg-gray-200 dark:bg-gray-700 font-semibold">
                Rekam Medis
              </summary>
              <div class="p-3 space-y-3">
                ${renderDailyMedicalForm(dayId)}
              </div>
            </details>
          </div>
        </div>
      `);

      // 🧩 Kalau bukan hari terakhir, disable semua input di dalam accordion ini
      if (!isLast) {
        const lastDiv = container.lastElementChild;
        const formFields = lastDiv.querySelectorAll("input, textarea, select, button");
        formFields.forEach(el => {
          if (el.tagName === "BUTTON") el.disabled = true;
          else el.setAttribute("readonly", true);
        });
      }
    });
  }

  function formatDate(dateStr) {
    if (!dateStr) return "-";
    const d = new Date(dateStr);
    return d.toLocaleDateString("id-ID", {
      day: "2-digit",
      month: "short",
      year: "numeric"
    });
  }

  // =============== FORM BUILDER UNTUK REKAM MEDIS =================
  function renderDailyMedicalForm(dayId) {
    const tmpl = document.querySelector('template#rekamMedisTemplate');
    if (tmpl) return tmpl.innerHTML; // isi dari template HTML
    // fallback kalau template gak ketemu
    return `<p class="text-gray-500 italic">Form rekam medis belum dikonfigurasi.</p>`;
  }

  // ========================== TAMBAH HARI BARU ==========================
  function addNewDailyDay(state) {
    // 🧩 pastikan struktur dasar ada
    if (!state.simulasi) state.simulasi = {};
    if (!state.simulasi.daily || typeof state.simulasi.daily !== "object") {
      state.simulasi.daily = { days: [], utama: null, sekunder: [] };
    }
    if (!Array.isArray(state.simulasi.daily.days)) {
      state.simulasi.daily.days = [];
    }

    const idx = state.simulasi.daily.days.length;
    const newId = `daily-${idx}`;
    const prevDay = idx > 0 ? state.simulasi.daily.days[idx - 1] : null;

    // pastikan manual & simulasi siap
    ensureDaily(newId);

    // 🗓️ tentukan tanggal hari baru
    let newDate;
    if (prevDay?.tanggal) {
      const [y, m, d] = prevDay.tanggal.split("-").map(Number);
      const next = new Date(y, m - 1, d + 1);
      newDate = next.toLocaleDateString("sv-SE"); // format yyyy-mm-dd
    } else {
      const base = state.visit?.tanggal_masuk || state.claim?.tanggal_masuk;
      newDate = base || new Date().toLocaleDateString("sv-SE");
    }

    // buat objek hari baru
    const newDay = {
      rekamMedis: prevDay?.rekamMedis
        ? JSON.parse(JSON.stringify(prevDay.rekamMedis))
        : {},
      tanggal: newDate,
      diagnosis: [],
      komorbid: [],
      komplikasi: [],
      utama: null,
      sekunder: [],
      tindakan: [],
    };

    // tambahkan ke struktur utama
    state.simulasi.daily.days.push(newDay);
    state.simulasi[newId] = newDay;

    // 🩹 kalau hari sebelumnya punya nilai rekam medis (belum disimpan pun), clone ke hari baru
    if (prevDay && prevDay.rekamMedis) {
      // clone dalam memori
      newDay.rekamMedis = JSON.parse(JSON.stringify(prevDay.rekamMedis));

      // kalau form di-tab daily pakai manualInput.daily['daily-X'].rekamMedis
      if (state.manualInput?.daily?.[`daily-${idx - 1}`]?.rekamMedis) {
        state.manualInput.daily[newId] = state.manualInput.daily[newId] || {};
        state.manualInput.daily[newId].rekamMedis = JSON.parse(
          JSON.stringify(state.manualInput.daily[`daily-${idx - 1}`].rekamMedis)
        );
      }

      console.log("🧩 Rekam medis di-clone sementara dari hari sebelumnya:", newId);
    }


    // tampilkan notifikasi & render ulang
    if (idx > 0 && typeof showToast === "function") {
      showToast(`✅ Hari ${idx + 1} menyalin Rekam Medis Hari ${idx}`, false, 2500);
    }

    renderDailyAccordion(state);

    // 🧭 Scroll ke hari baru
    setTimeout(() => {
      const last = document.querySelector("#daily-accordion > div:last-child");
      if (last) {
        last.scrollIntoView({ behavior: "smooth", block: "center" });
        last.classList.add("ring-4", "ring-green-400", "ring-offset-2");
        setTimeout(() => last.classList.remove("ring-4", "ring-green-400", "ring-offset-2"), 1800);
      }
    }, 300);
  }

  // normalisasi opsi mapping (universal untuk diagnosis & tindakan)
  function normalizeOpt(opt, type = null) {
    if (!opt) return opt;
    const o = String(opt).trim();

    // Diagnosis
    if (o === "Diagnosis Utama" || o === "Utama" || o === "Primary Claim" || o === "Primary")
      return type === "tindakan" ? "Primary Action" : "Primary";
    if (o === "Komorbid" || o === "Secondary-Komorbid") return "Secondary-Komorbid";
    if (o === "Komplikasi" || o === "Secondary-Komplikasi") return "Secondary-Komplikasi";
    if (o === "Sekunder" || o === "Secondary Claim" || o === "Secondary")
      return type === "tindakan" ? "Secondary Actions" : "Secondary";

    if (o === "Primary Action" || o === "Tindakan Utama") return "Primary Action";
    if (o === "Secondary Actions" || o === "Tindakan Sekunder") return "Secondary Actions";

    if (o === "None") return "None";
    return o;
  }



  function normalizeItem(val) {
    if (typeof val === "string") {
      return {
        name: val.split(" [")[0] || "",
        kategori: val.split(" [")[0] || "",
        label: "",
        mapping: "",
        source: "Manual",
        isManual: true
      };
    }
    const nama = val.kategori || val.nama_kategori || val.name || "";
    return {
      ...val,
      name: nama,
      kategori: nama,
      label: val.label || "",
      mapping: val.mapping || "",
    };
  }


  function normalizeProcedure(td) {
    if (!td) return { nama: "" };
    return { ...td, nama: td.nama || td.name || td.procedure_text || td.kategori || "" };
  }

  // state utama (dipasang via x-data="claimData(init)")
  function claimData(init) {
    let serverStages = {};
    try {
      const el = document.getElementById("claimRoot");
      if (el && el.hasAttribute("data-stages")) {
        serverStages = JSON.parse(el.getAttribute("data-stages"));
        console.log("📦 [CLAIM STATE] Loaded stages from server:", serverStages);
      }
    } catch (e) {
      console.warn("⚠️ [CLAIM STATE] Gagal parse data-stages:", e);
    }
    const state = {
      role: init.role || 'doctor', // doctor, verifikator, coder
      tab: init.tab || 'admission',
      stages: serverStages,
      form: {},

      // simulasi hasil AI
      simulasi: init.sim || {
        admission: { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[] },
        "daily-0": { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[] },
        "daily-1": { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[] },
        discharge: { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[] },
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

      // fungsi
      addNewDailyDay() { addNewDailyDay(this); },
      renderDailyAccordion() { renderDailyAccordion(this); },
      async init() {
        const role = this.role;
        const claimId = document.getElementById("claimRoot")?.dataset.claimId;
        
        console.log("🚀 [ALPINE INIT] Starting initialization", { role, claimId });
        console.log("🔍 [ALPINE INIT] Initial simulasi state:", JSON.stringify(this.simulasi, null, 2));
        
        if (this.simulasi.daily.days.length === 0) {
          this.addNewDailyDay();   // bikin Hari 1 kosong
        }

        // ✅ Tambahan debug
        if (role === 'coder') {
          console.log("📋 [CODER INIT] stages loaded:", this.stages);
        }
        
        // 🎯 CRITICAL FIX: Load simulations IMMEDIATELY in init, not setTimeout
        if ((role === 'verifikator' || role === 'doctor') && claimId) {
          console.log("🔄 [ALPINE INIT] Loading simulations with safe delay...");
          if (window.loadSimulations) {
            setTimeout(async () => {
              try {
                await window.loadSimulations(claimId);
                console.log("✅ [ALPINE INIT] Simulations loaded successfully (delayed)");
              } catch (e) {
                console.error("❌ [ALPINE INIT] Failed to load simulations:", e);
              }
            }, 500); // 🔧 beri jeda 0.5 detik agar Alpine siap
          }
        }

        
        console.log("🏁 [ALPINE INIT] Initialization completed");
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
    console.log("🔥 updateSimulasi CALLED", { type, opt, tab, value });
    if (tab === "daily") tab = "daily-global";
    const state = Alpine.$data(document.getElementById("claimRoot"));
    if (!tab) tab = "admission";
    const finalOpt = normalizeOpt(opt || value?.mapping || "", type);
    console.log("🎯 normalizeOpt result:", { original: opt, normalized: finalOpt });
    
    if (!state.simulasi[tab] || typeof state.simulasi[tab] !== "object" || Array.isArray(state.simulasi[tab])) {
      state.simulasi[tab] = {};
    }
    let sim = state.simulasi[tab];
    
    // 🔍 DEBUG: Check current sim state before update
    console.log("📋 [BEFORE UPDATE] Current sim state:", {
      utama: sim.utama,
      sekunder: sim.sekunder,
      tindakanUtama: sim.tindakanUtama,
      tindakanSekunder: sim.tindakanSekunder
    });

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

    // 🎯 FIX: Set proper labels for loaded data
    if (source) {
      if (finalOpt === "Primary") item.label = "Utama Klinis";
      else if (finalOpt === "Secondary-Komorbid") item.label = "Komorbid";
      else if (finalOpt === "Secondary-Komplikasi") item.label = "Komplikasi";
      else if (finalOpt === "Secondary") item.label = "Sekunder Klinis"; // ✅ NEW: Label for secondary diagnosis
    }

    // Diagnosis
    // Diagnosis
    if (["diagnosis", "komorbid", "komplikasi"].includes(type)) {
      if (finalOpt === "Primary") {
        const oldPrimary = sim.utama;
        sim.sekunder = sim.sekunder.filter(dx => dx.name !== item.name);

        // 🩹 set mapping agar dropdown tidak nyangkut
        item.mapping = "Primary";
        
        // 🩹 PATCH: Preserve ICD-10 code from original value
        if (value && value.icd10_code) {
          item.icd10_code = value.icd10_code;
          console.log("🩹 [PATCH] Preserving ICD-10 for Primary:", value.icd10_code);
        }
        if (value && value.icd10 && value.icd10.kode_icd) {
          item.icd10 = value.icd10;
          item.icd10_code = value.icd10.kode_icd;
          console.log("🩹 [PATCH] Preserving nested ICD-10:", value.icd10.kode_icd);
        }
        
        sim.utama = { diagnosis_utama_id: item.id, ...item };
        console.log("🩹 [PATCH] Set Primary Diagnosis with ICD-10:", sim.utama);

        // kalau ada primary lama, ubah mapping-nya jadi secondary biar turun
        if (oldPrimary && oldPrimary.name !== item.name) {
          oldPrimary.mapping = "Secondary";
          sim.sekunder.unshift(oldPrimary);
        }

      } else if (finalOpt.startsWith("Secondary")) {
        if (sim.utama && sim.utama.name === item.name) sim.utama = null;

        // 🩹 pastikan mapping tertulis "Secondary"
        item.mapping = "Secondary";
        
        // 🩹 PATCH: Preserve ICD-10 code for secondary
        if (value && value.icd10_code) {
          item.icd10_code = value.icd10_code;
          console.log("🩹 [PATCH] Preserving ICD-10 for Secondary:", value.icd10_code);
        }
        if (value && value.icd10 && value.icd10.kode_icd) {
          item.icd10 = value.icd10;
          item.icd10_code = value.icd10.kode_icd;
        }

        const idx = sim.sekunder.findIndex(dx => dx.name === item.name);
        const secItem = { diagnosis_sekunder_id: item.id, ...item };
        if (idx === -1) sim.sekunder.push(secItem);
        else sim.sekunder[idx] = secItem;
        console.log("🩹 [PATCH] Set Secondary Diagnosis with ICD-10:", secItem);

      } else if (finalOpt === "None") {
        if (sim.utama && sim.utama.name === item.name) sim.utama = null;
        sim.sekunder = sim.sekunder.filter(dx => dx.name !== item.name);
      }
    }


    // Tindakan
    if (type === "tindakan") {
      const nama = typeof value === "string" ? value : (value.name || value.label || "(tanpa nama)");
      const id = typeof value === "string" ? null : (value.id || null);

      console.log("🔍 [TINDAKAN DEBUG] Values:", { finalOpt, nama, id, typeOfFinalOpt: typeof finalOpt });
      console.log("🔍 [TINDAKAN DEBUG] Comparison:", finalOpt === "Primary", finalOpt === "Secondary");

      // 🎯 FIX: Handle normalized "Primary" for tindakan
      if (finalOpt === "Primary" || finalOpt === "Primary Action") {
        console.log("✅ [TINDAKAN] Entering PRIMARY branch");
        const oldPrimary = sim.tindakanUtama;
        sim.tindakanSekunder = sim.tindakanSekunder.filter(td => td.name !== nama);
        sim.tindakanUtama = { tindakan_utama_id: id, name: nama };
        if (oldPrimary && oldPrimary.name !== nama) sim.tindakanSekunder.unshift(oldPrimary);
        console.log("✅ [TINDAKAN] Set tindakanUtama:", sim.tindakanUtama);
      } 
      // 🎯 FIX: Handle normalized "Secondary" for tindakan
      else if (finalOpt === "Secondary" || finalOpt === "Secondary Actions") {
        console.log("✅ [TINDAKAN] Entering SECONDARY branch");
        if (sim.tindakanUtama?.name === nama) sim.tindakanUtama = null;
        if (!sim.tindakanSekunder.find(td => td.name === nama)) {
          sim.tindakanSekunder.push({ tindakan_sekunder_id: id, name: nama });
        }
        console.log("✅ [TINDAKAN] Added to tindakanSekunder:", sim.tindakanSekunder);
      } else if (finalOpt === "None") {
        console.log("✅ [TINDAKAN] Entering NONE branch");
        if (sim.tindakanUtama?.name === nama) sim.tindakanUtama = null;
        sim.tindakanSekunder = sim.tindakanSekunder.filter(td => td.name !== nama);
      } else {
        console.log("❌ [TINDAKAN] NO BRANCH MATCHED! finalOpt:", finalOpt);
      }
      
      // 🔍 DEBUG: Check sim state after tindakan update
      console.log("🎯 [AFTER TINDAKAN UPDATE] Updated sim state:", {
        tindakanUtama: sim.tindakanUtama,
        tindakanSekunder: sim.tindakanSekunder,
        finalOpt: finalOpt,
        nama: nama
      });
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

    // 🩹 juga sinkronkan jika tab === 'daily-global'
    if (tab === "daily-global" && Array.isArray(state.simulasi.daily?.days)) {
      const lastIdx = state.simulasi.daily.days.length - 1;
      if (lastIdx >= 0) {
        const lastDay = state.simulasi.daily.days[lastIdx];
        ["diagnosis","komorbid","komplikasi","tindakan"].forEach(tp=>{
          if (!Array.isArray(lastDay[tp])) lastDay[tp]=[];
          lastDay[tp] = [...state.simulasi["daily-global"][tp]];
        });
        state.simulasi[`daily-${lastIdx}`] = lastDay;
      }
    }

    // 🧩 Tambahkan log debug di sini
    console.log("🧩 updateSimulasi DEBUG - tab:", tab, "type:", type, "finalOpt:", finalOpt);
    console.log("📋 [BEFORE] sim state:", JSON.parse(JSON.stringify(state.simulasi[tab])));
    console.log("📋 [AFTER] sim setelah update:", JSON.parse(JSON.stringify(state.simulasi[tab])));
    
    // 🔍 CRITICAL DEBUG: Check final tindakan state
    if (type === "tindakan") {
      console.log("🎯 TINDAKAN FINAL STATE:");
      console.log("  - tindakanUtama:", state.simulasi[tab].tindakanUtama);
      console.log("  - tindakanSekunder:", state.simulasi[tab].tindakanSekunder);
      console.log("  - Template should show:", {
        primaryAction: state.simulasi[tab].tindakanUtama?.name || "TIDAK ADA",
        secondaryActions: (state.simulasi[tab].tindakanSekunder || []).map(t => t.name)
      });
      
      // 🔥 FORCE ALPINE REACTIVITY CHECK
      console.log("🔥 [REACTIVITY CHECK] Full simulasi object:", state.simulasi);
      console.log("🔥 [REACTIVITY CHECK] Alpine state reference:", typeof state, !!state);
      
      // 🚨 CRITICAL: Force template update
      try {
        const claimRoot = document.getElementById("claimRoot");
        if (claimRoot && Alpine) {
          console.log("🔄 [FORCE UPDATE] Triggering Alpine refresh...");
          Alpine.nextTick(() => {
            console.log("✅ [FORCE UPDATE] NextTick completed");
          });
        }
      } catch (e) {
        console.error("❌ [FORCE UPDATE] Failed:", e);
      }
    }

    // 🩹 sinkron ringkasan kanan khusus untuk tab Daily
    if (["daily", "daily-global"].includes(tab)) {
      const summary = state.simulasi.summary || { diagnosis: [], tindakan: [] };
      const allDiag = [];

      // gabungkan semua diagnosis dari tab daily-global
      ["diagnosis", "komorbid", "komplikasi"].forEach(tp => {
        const arr = (state.simulasi["daily-global"]?.[tp] || []).map(d => ({
          ...d,
          type: tp,
        }));
        allDiag.push(...arr);
      });

      summary.diagnosis = allDiag;
      state.simulasi.summary = summary;

      console.log("✅ Summary updated (daily):", summary);
    }

    // 🩹 sinkron juga ke struktur harian agar panel kanan update
    if (["daily", "daily-global"].includes(tab)) {
      if (Array.isArray(state.simulasi.daily?.days)) {
        const lastIdx = state.simulasi.daily.days.length - 1;
        if (lastIdx >= 0) {
          const lastDay = state.simulasi.daily.days[lastIdx];
          ["diagnosis", "komorbid", "komplikasi"].forEach(tp => {
            lastDay[tp] = JSON.parse(
              JSON.stringify(state.simulasi["daily-global"]?.[tp] || [])
            );
          });
          state.simulasi[`daily-${lastIdx}`] = lastDay;
          console.log("🧩 Synced daily-global → daily days:", lastDay);
        }
      }
    }

    // 🩹 Hard sync agar daily-global selalu mirror ke hari terakhir di daily.days & daily-0
    if (tab === "daily-global" && Array.isArray(state.simulasi.daily?.days)) {
      const lastIdx = state.simulasi.daily.days.length - 1;
      if (lastIdx >= 0) {
        const lastDay = state.simulasi.daily.days[lastIdx];

        // clone penuh daily-global ke daily-{lastIdx} dan daily-0
        ["diagnosis", "komorbid", "komplikasi", "tindakan"].forEach(tp => {
          const cloned = JSON.parse(JSON.stringify(state.simulasi["daily-global"]?.[tp] || []));
          lastDay[tp] = cloned;
          state.simulasi[`daily-${lastIdx}`][tp] = cloned;
          if (state.simulasi["daily-0"]) state.simulasi["daily-0"][tp] = cloned;
        });

        // mirror juga utama & sekunder
        lastDay.utama = state.simulasi["daily-global"].utama || null;
        lastDay.sekunder = state.simulasi["daily-global"].sekunder || [];
        state.simulasi[`daily-${lastIdx}`].utama = lastDay.utama;
        state.simulasi[`daily-${lastIdx}`].sekunder = lastDay.sekunder;

        console.log("🧩 Hard synced daily-global →", `daily-${lastIdx} & daily-0`, lastDay);
      }
    }

    window.syncHiddenInputs && window.syncHiddenInputs();
  }

  // onMappingChange handler
  function onMappingChange(event, tab, type, itemId) {
    try {
      let originalTab = tab;
      if (tab === "daily" || tab === "daily-0") tab = "daily-global";
      if (originalTab === "daily" || originalTab === "daily-0") originalTab = "daily-global";

      const state = Alpine.$data(document.getElementById("claimRoot"));
      const opt = event.target.value;
      const keyDecoded = decodeURIComponent(itemId || "");

      // siapkan kandidat array
      let arr = state.simulasi?.[originalTab]?.[type] || [];
      // kalau data manual gak ada di simulasi[tab][type], cari di seluruh simulasi
      if (!arr.length) {
        arr = Object.keys(state.simulasi)
          .filter(k => typeof state.simulasi[k] === "object")
          .flatMap(k => {
            const obj = state.simulasi[k];
            return Array.isArray(obj[type]) ? obj[type] : [];
          });
      }

      if (originalTab === "daily") {
        const allDaily = Object.keys(state.simulasi).filter(k => k.startsWith("daily-"));
        arr = allDaily.flatMap(k => state.simulasi[k]?.[type] || []);
      }

      // cari item
      function matchKey(it) {
        const name = (it.nama_kategori || it.kategori || it.name || "").trim();
        if (!name) return false;
        // hapus angka indeks jika ada (misal -child-0 atau -child-1)
        const cleanKey = keyDecoded.replace(/-child-\d+$/, "");
        return (
          cleanKey === `${originalTab}-${type}-${name}` ||
          cleanKey === `daily-global-${type}-${name}` ||
          cleanKey.endsWith(`-${name}`)
        );
      }

      // cari dulu di daftar utama
      let item = arr.find(matchKey);

      // kalau belum ketemu, coba cari di anak-anaknya (children)
      if (!item) {
        const children = arr.flatMap(p => p.children || []);
        item = children.find(matchKey);
      }

      if (!item) {
        console.warn("⚠️ onMappingChange: item not found", { originalTab, type, itemId, arr });
        return;
      }

      console.table(arr.map(a => ({
        kategori: a.kategori,
        nama_kategori: a.nama_kategori,
        isManual: a.isManual,
        mapping: a.mapping
      })));
      console.log("arr yang dicari:", JSON.parse(JSON.stringify(arr)));
      console.log("item yang dicari:", JSON.parse(JSON.stringify(item)));

      item.mapping = opt;
      updateSimulasi(
        type,
        opt,
        normalizeItem(item),
        item.source || (item.isManual ? "Manual" : "AI"),
        // biarkan tab apa adanya (jangan paksa ke daily-global di sini)
        originalTab.startsWith("daily") ? "daily-global" : originalTab
      );

      console.log("✅ Mapping updated:", (item.kategori || item.nama_kategori || item.name), opt);
    } catch (err) {
      console.error("❌ onMappingChange fatal:", err);
    }
  }




  // Expose
  window.claimData = claimData;
  window.ensureDaily = ensureDaily;
  window.updateSimulasi = updateSimulasi;
  window.onMappingChange = onMappingChange;
  window.normalizeProcedure = normalizeProcedure;
  window.addNewDailyDay = addNewDailyDay;
  window.renderDailyAccordion = renderDailyAccordion;
  window.renderDailyMedicalForm = renderDailyMedicalForm;
  window.normalizeItem = normalizeItem;
  window.normalizeOpt = normalizeOpt;
  window.formatDate = formatDate;
})();