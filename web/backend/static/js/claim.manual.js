// =============== Input manual (diagnosis/komorbid/komplikasi + tindakan) ===============

(function () {
  function addManual(type, tab) {
    const state = Alpine.$data(document.getElementById('claimRoot'));

    if (String(tab).startsWith("daily-")) window.ensureDaily && window.ensureDaily(tab);

    const input = String(tab).startsWith("daily-")
      ? state.manualInput.daily[tab][type]
      : state.manualInput[tab][type];

    if (!input) return console.warn("❌ manualInput kosong:", tab, type);

    const newItem = {
      kategori: input.kategori || "",
      klinis: input.klinis || "",
      icd10_code: input.icd10_code || "",
      procedure_text: input.procedure_text || "",
      score: input.score || 0,
      mapping: "",
      isManual: true,
      source: "Manual"
    };

    if (!state.simulasi[tab]) {
      state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[] };
    }
    if (!Array.isArray(state.simulasi[tab][type])) state.simulasi[tab][type] = [];

    state.simulasi[tab][type].push(newItem);

    if (String(tab).startsWith("daily-")) {
      const idx = parseInt(tab.split("-")[1], 10);
      if (!state.simulasi.daily) state.simulasi.daily = { days: [], utama:null, sekunder:[] };
      state.simulasi.daily.days[idx] = state.simulasi[tab];

      const allDays = state.simulasi.daily.days || [];
      state.simulasi.daily.utama = null;
      state.simulasi.daily.sekunder = [];
      allDays.forEach(d => {
        if (d?.utama && !state.simulasi.daily.utama) state.simulasi.daily.utama = d.utama;
        if (Array.isArray(d?.sekunder)) state.simulasi.daily.sekunder.push(...d.sekunder);
      });
    }

    window.renderTable && window.renderTable(`${type}-${tab}`, state.simulasi[tab][type], type, tab, null, true);

    Object.keys(input).forEach(k => input[k] = ""); // reset

    window.renderTable && window.renderTable(`${type}-${tab}`, state.simulasi[tab][type], type, tab);
    window.syncHiddenInputs && window.syncHiddenInputs();
  }

  async function addManualFromAutocomplete(tab, selected, type = "diagnosis") {
    const state = Alpine.$data(document.getElementById("claimRoot"));
    if (!state.simulasi[tab]) {
      state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [] };
    }

    const newItem = {
      kategori: selected.name,
      icd10_code: "-",
      klinis: "-",
      tindakan: "-",
      score: 80,
      mapping: "",
      isManual: true,
      source: "Manual",
    };

    const detailRes = await window.getDiagnosisDetail(selected.code);
    if (detailRes.status === "ok") {
      newItem.rowData = detailRes.data;
    }

    // 🔥 arahkan ke array sesuai tipe
    state.simulasi[tab][type].push(newItem);

    // render ulang tabel sesuai accordion aktif
    window.renderTable &&
      window.renderTable(`${type}-${tab}`, state.simulasi[tab][type], type, tab);
    window.syncHiddenInputs && window.syncHiddenInputs();
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
    let newTd = { nama, deskripsi: "-", source: "Manual", isManual: true };
    newTd = window.normalizeProcedure ? window.normalizeProcedure(newTd) : newTd;

    if (idx !== -1) state.manualTindakan[idx] = newTd;
    else state.manualTindakan.push(newTd);

    renderManualTindakanList();
    namaEl.value = "";
  }

  function renderManualTindakanList(tab, containerEl) {
    const state = window.claimState || {};
    const listContainer =
      containerEl?.querySelector(".tindakan-list") ||
      document.querySelector(".modal-content .tindakan-list") ||
      document.querySelector(".tindakan-list");
    if (!listContainer) return;

    const rawList = (state.simulasi?.[tab]?.tindakan || [])
      .filter(td => td.procedure_text && td.procedure_text !== "-");

    // 🔥 filter unik biar tidak looping terus
    const list = [];
    const seen = new Set();
    for (const td of rawList) {
      const key = td.procedure_text + (td.source || "");
      if (!seen.has(key)) {
        list.push(td);
        seen.add(key);
      }
    }
    listContainer.innerHTML = "";

    if (!list.length) {
      listContainer.innerHTML =
        `<div class="italic text-gray-500 text-center py-2">Belum ada tindakan manual</div>`;
      return;
    }

    list.forEach((td, idx) => {
      const nama = td.procedure_text || td.nama || "-";
      const deskripsi = td.deskripsi && td.deskripsi !== "-" ? td.deskripsi : "";
      listContainer.insertAdjacentHTML(
        "beforeend",
        `
        <div class="grid grid-cols-3 gap-4 items-center bg-white dark:bg-gray-800 p-3 rounded shadow mb-2"
            data-id="manual-tindakan-${tab}-${idx}"
            data-manual-idx="${idx}">
          <div class="font-semibold text-blue-600 underline cursor-pointer truncate"
              onclick="openManualDetailModal({ procedure_text: '${nama}' }, '${tab}', ${idx})">
            ${nama}
          </div>
          <div>
            <span class="block px-3 py-1 text-sm font-medium bg-gray-200 dark:bg-gray-700
                        text-gray-900 dark:text-gray-100 rounded shadow-sm whitespace-nowrap overflow-hidden text-ellipsis"
                  title="${deskripsi}">${deskripsi || "&nbsp;"}</span>
          </div>
          ${window.claimState?.role === "doctor"
            ? `<div class="flex space-x-2 justify-end">
                <button type="button"
                        onclick="updateSimulasi('tindakan','Primary','${nama}','Manual','${tab}')"
                        class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs">Pilih Utama</button>
                <button type="button"
                        onclick="updateSimulasi('tindakan','Secondary','${nama}','Manual','${tab}')"
                        class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-xs">Pilih Sekunder</button>
              </div>`
            : ``}
        </div>`
      );
    });
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
        procedure_text: selected.procedure_text || detail.procedure_text || "-",
        deskripsi: "", // awalnya kosong, nanti diisi setelah fetch detail
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

  // Export
  window.addManual = addManual;
  window.addManualFromAutocomplete = addManualFromAutocomplete;
  window.handleAddManualTindakan = handleAddManualTindakan;
  window.addManualTindakan = addManualTindakan;
  window.addManualTindakanFromAutocomplete = addManualTindakanFromAutocomplete;
  window.renderManualTindakanList = renderManualTindakanList;
})();
