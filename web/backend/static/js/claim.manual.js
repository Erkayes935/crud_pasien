// =============== Input manual (diagnosis/komorbid/komplikasi + tindakan) ===============

(function () {
  function addManual(type, tab) {
    if (tab === "daily") tab = "daily-global";
    const state = Alpine.$data(document.getElementById("claimRoot"));

    // pastikan struktur daily siap
    if (String(tab).startsWith("daily-")) window.ensureDaily && window.ensureDaily(tab);

    const input = String(tab).startsWith("daily-")
      ? state.manualInput.daily?.[tab]?.[type] || {}
      : state.manualInput?.[tab]?.[type] || {};

    if (!input) return console.warn("❌ manualInput kosong:", tab, type);

    const newItem = {
      kategori: input.kategori || "(Manual)",
      klinis: input.klinis || "",
      icd10_code: input.icd10_code || "",
      procedure_text: input.procedure_text || "",
      score: input.score || 0,
      mapping: "",
      isManual: true,
      source: "Manual"
    };

    // pastikan struktur simulasi tab aman
    if (!state.simulasi[tab]) {
      state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakan:[] };
    }
    if (!Array.isArray(state.simulasi[tab][type])) state.simulasi[tab][type] = [];

    // push item
    state.simulasi[tab][type].push(newItem);
    console.groupCollapsed("🧩 addManual DEBUG");
    console.log("tab:", tab, "type:", type);
    console.log("newItem:", newItem);
    console.log("state.simulasi[tab][type]:", JSON.parse(JSON.stringify(state.simulasi[tab][type])));
    console.groupEnd();

    // sinkron ke daily.days (khusus daily tab)
    if (String(tab).startsWith("daily-")) {
      const idx = parseInt(tab.split("-")[1], 10);
      if (!state.simulasi.daily) state.simulasi.daily = { days: [], utama:null, sekunder:[] };
      state.simulasi.daily.days[idx] = state.simulasi[tab];
    }

    // render ulang tabel
    window.renderTable && window.renderTable(`${type}-${tab}`, state.simulasi[tab][type], type, tab);
    window.syncHiddenInputs && window.syncHiddenInputs();

    // reset input
    Object.keys(input).forEach(k => input[k] = "");

    console.log("✅ Input manual ditambahkan:", newItem);
  }


  async function addManualFromAutocomplete(tab, selected, type = "diagnosis") {
    try {
      // 🧩 perbaiki konteks daily
      if (tab === "daily") tab = "daily-global";
      const state = Alpine.$data(document.getElementById("claimRoot"));

      // pastikan struktur simulasi aman
      if (!state.simulasi[tab])
        state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [], tindakan: [] };
      if (!Array.isArray(state.simulasi[tab][type]))
        state.simulasi[tab][type] = [];

      // ambil detail dari backend (fallback kalau code kosong)
      let rowData = {};
      try {
        if (selected.code) {
          const detailRes = await window.getDiagnosisDetail(selected.code);
          rowData = detailRes?.data || {};
        } else {
          // ⚙️ fallback jika diagnosis tidak ada di database
          rowData = {
            name: selected.name || "(Manual Input)",
            kategori: selected.name || "(Manual Input)",
            klinis: "",
            icd10_code: "",
            source: "Manual",
          };
        }
      } catch (err) {
        console.warn("⚠️ getDiagnosisDetail gagal, gunakan fallback manual:", err);
        rowData = {
          name: selected.name || "(Manual Input)",
          kategori: selected.name || "(Manual Input)",
          klinis: "",
          icd10_code: "",
          source: "Manual",
        };
      }


      // buat item manual baru
      const newItem = {
        kategori: selected.name || selected.kategori || "(Manual)",
        klinis: "",
        icd10_code: "",
        procedure_text: "",
        score: 85,
        mapping: "",
        isManual: true,
        source: "Manual",
        rowData
      };

      // 🧹 hapus duplikat nama yang sama biar gak nambah dobel
      state.simulasi[tab][type] = state.simulasi[tab][type].filter(
        it => it.kategori !== newItem.kategori
      );

      // push ke array simulasi
      state.simulasi[tab][type].push(newItem);

      // render ulang tabel
      const targetId = `${type}-${tab}`.replace("daily-global", "daily");
      window.renderTable && window.renderTable(targetId, state.simulasi[tab][type], type, tab);

      // sinkron input hidden
      window.syncHiddenInputs && window.syncHiddenInputs();

      console.log("✅ Diagnosis manual ditambahkan dari autocomplete:", newItem);
    } catch (err) {
      console.error("❌ Gagal addManualFromAutocomplete:", err);
    }
  }

  // ===== Manual tindakan (list & nested modal) =====

  function addManualTindakan() {
    const namaEl = document.getElementById("manualNamaTindakan");
    if (!namaEl) return alert("Input manual tindakan tidak ditemukan");

    const nama = namaEl.value.trim();
    if (!nama) return alert("Nama tindakan wajib diisi");

    const state = window.claimState || {};
    if (!state.manualTindakan) state.manualTindakan = [];

    const idx = state.manualTindakan.findIndex(td => td.nama === nama);
    let newTd = { nama, deskripsi: "", source: "Manual", isManual: true };
    newTd = window.normalizeProcedure ? window.normalizeProcedure(newTd) : newTd;

    if (idx !== -1) state.manualTindakan[idx] = newTd;
    else state.manualTindakan.push(newTd);

    renderManualTindakanList();
    namaEl.value = "";
  }

  function renderManualTindakanList(tab, containerEl) {
    try {
      const state = window.claimState || {};
      const listContainer =
        containerEl?.querySelector(".tindakan-list") ||
        document.querySelector(".modal-content .tindakan-list") ||
        document.querySelector(".tindakan-list");
      if (!listContainer) return;

      // 🧹 Hapus event listener lama sebelum isi ulang
      listContainer.replaceChildren();

      // 🧩 Ambil data aman
      const rawList = (state.simulasi?.[tab]?.tindakan || []).filter(
        td => td && (td.procedure_text || td.nama)
      );

      // 🔥 Filter unik biar gak dobel
      const list = [];
      const seen = new Set();
      for (const td of rawList) {
        const key = (td.procedure_text || td.nama || "") + (td.source || "");
        if (!seen.has(key)) {
          list.push(td);
          seen.add(key);
        }
      }

      if (list.length === 0) {
        listContainer.innerHTML =
          `<div class="italic text-gray-500 text-center py-2">Belum ada tindakan manual</div>`;
        return;
      }

      // 🧠 Render aman
      list.forEach((td, idx) => {
        const nama = (td.procedure_text || td.nama || "").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
        const deskripsi =
          td.deskripsi && td.deskripsi.trim() !== "" ? td.deskripsi : "&nbsp;";

        const row = document.createElement("div");
        row.className =
          "grid grid-cols-3 gap-4 items-center bg-white dark:bg-gray-800 p-3 rounded shadow mb-2";
        row.dataset.id = `manual-tindakan-${tab}-${idx}`;
        row.dataset.manualIdx = idx;

        // nama tindakan (klik buat buka detail)
        const namaCol = document.createElement("div");
        namaCol.className = "font-semibold text-blue-600 underline cursor-pointer truncate";
        namaCol.textContent = nama;
        namaCol.onclick = () =>
          openManualDetailModal({ procedure_text: nama }, tab, idx);

        // deskripsi
        const descCol = document.createElement("div");
        descCol.innerHTML = `<span class="block px-3 py-1 text-sm font-medium bg-gray-200 dark:bg-gray-700
                              text-gray-900 dark:text-gray-100 rounded shadow-sm whitespace-nowrap overflow-hidden text-ellipsis"
                              title="${deskripsi}">${deskripsi}</span>`;

        // tombol pilih (hanya doctor)
        const btnCol = document.createElement("div");
        if (state.role === "doctor") {
          btnCol.className = "flex space-x-2 justify-end";
          btnCol.innerHTML = `
            <button type="button"
              onclick="updateSimulasi('tindakan','Primary','${nama}','Manual','${tab}')"
              class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs">
              Pilih Utama
            </button>
            <button type="button"
              onclick="updateSimulasi('tindakan','Secondary','${nama}','Manual','${tab}')"
              class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-xs">
              Pilih Sekunder
            </button>`;
        }

        row.appendChild(namaCol);
        row.appendChild(descCol);
        if (state.role === "doctor") row.appendChild(btnCol);

        listContainer.appendChild(row);
      });
    } catch (err) {
      console.error("❌ renderManualTindakanList failed:", err);
    }
  }

  function rehydrateManualTindakan(tab) {
    try {
      const state = claimState || {};
      const sim = state.simulasi?.[tab];
      if (!sim) return;

      // hanya jalan kalau belum dirender atau masih kosong
      const container = document.querySelector(".tindakan-list");
      const hasList = container && container.children.length > 0;
      if (hasList) return;

      const existingManuals = (sim.tindakan || []).filter(td => td?.isManual);
      if (existingManuals.length > 0) {
        console.log("🧩 Rehydrate tindakan manual lama:", existingManuals.length);
        renderManualTindakanList(tab);
      }
    } catch (e) {
      console.warn("⚠️ Gagal rehydrate manual:", e);
    }
  }


  // ====================== Tambah Tindakan Manual ======================
  async function addManualTindakanFromAutocomplete(tab, selected) {
    try {
      const root = document.getElementById("claimRoot");
      const state = Alpine.$data(root);
      if (!state.simulasi[tab]) state.simulasi[tab] = { tindakan: [] };
      if (!Array.isArray(state.simulasi[tab].tindakan)) state.simulasi[tab].tindakan = [];

      // ambil detail dari backend (dummy_data.py)
      const res = await fetch(`/claims/search/tindakan/detail/${encodeURIComponent(selected.procedure_text)}`);
      const json = await res.json();
      const detail = json.data || {};

      const newItem = {
        ...selected,
        ...detail,
        isManual: true,
        source: "Manual",
        procedure_text: selected.procedure_text || detail.procedure_text || "",
        deskripsi: "&nbsp;", // awalnya kosong, nanti diisi setelah fetch detail
      };

      // 🧹 hapus duplikat nama sama sebelum push
      state.simulasi[tab].tindakan = state.simulasi[tab].tindakan.filter(
        td => td.procedure_text !== newItem.procedure_text
      );

      state.simulasi[tab].tindakan.push(newItem);

      // 🔁 render ulang list manual di modal
      setTimeout(() => {
        window.renderManualTindakanList && window.renderManualTindakanList(tab);
      }, 50);

      window.syncHiddenInputs && window.syncHiddenInputs();
    } catch (err) {
      console.error("❌ Gagal tambah tindakan manual:", err);
    }
  }



  // ====================== Tombol "+" ======================
  async function handleAddManualTindakan(tab) {
    // ambil konteks Alpine autocomplete
    const alpineCtx = Alpine.$data(document.querySelector('[x-data="tindakanAutocomplete()"]'));
    const text = alpineCtx?.query?.trim?.() || "";
    if (!text) return;

    const found = window.cachedTindakan?.some(td =>
      td.procedure_text.toLowerCase() === text.toLowerCase()
    );

    if (!found) {
      const confirmAdd = confirm(`Tindakan "${text}" tidak ditemukan di database.\nTambahkan sebagai input manual baru?`);
      if (!confirmAdd) return;
    }

    addManualTindakanFromAutocomplete(tab, { procedure_text: text });
    alpineCtx.query = ""; // reset input
  }

  function persistManualTindakanBeforeClose() {
    const root = document.getElementById("claimRoot");
    const state = Alpine.$data(root);
    const tab = state?.tab || "admission";

    // cari konteks autocomplete aktif
    const ctx = document.querySelector('[x-data="tindakanAutocomplete()"] input');
    if (!ctx) return;

    const value = ctx.value.trim();
    if (!value) return;

    // push ke state global kalau belum ada
    state.simulasi[tab] = state.simulasi[tab] || { tindakan: [] };
    const already = state.simulasi[tab].tindakan.some(
      t => t.procedure_text?.toLowerCase() === value.toLowerCase()
    );
    if (!already) {
      state.simulasi[tab].tindakan.push({
        procedure_text: value,
        isManual: true,
        source: "Manual",
        deskripsi: "&nbsp;"
      });
    }

    window.syncHiddenInputs && window.syncHiddenInputs();
  }


  // Export
  window.addManual = addManual;
  window.persistManualTindakanBeforeClose = persistManualTindakanBeforeClose;
  window.addManualFromAutocomplete = addManualFromAutocomplete;
  window.handleAddManualTindakan = handleAddManualTindakan;
  window.addManualTindakan = addManualTindakan;
  window.addManualTindakanFromAutocomplete = addManualTindakanFromAutocomplete;
  window.renderManualTindakanList = renderManualTindakanList;
  window.rehydrateManualTindakan = rehydrateManualTindakan;
})();
