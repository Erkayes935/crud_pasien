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

  function renderManualTindakanList() {
    const state = window.claimState || {};
    const listContainer = document.querySelector(".tindakan-list");
    if (!listContainer) return;

    state.manualTindakan = (state.manualTindakan || []).filter(td => td.nama && td.nama !== "-" && td.nama !== "undefined");
    listContainer.innerHTML = "";

    (state.manualTindakan || []).forEach((td, idx) => {
      listContainer.insertAdjacentHTML("beforeend", `
        <div class="grid grid-cols-3 items-center bg-white dark:bg-gray-800 p-3 rounded shadow mb-2 gap-4">
          <div class="font-semibold text-blue-600 underline cursor-pointer truncate"
              onclick="openManualNestedProcedureModal(${idx})">
            ${td.nama}
          </div>
          <div class="px-3 py-1 text-sm font-medium bg-gray-200 dark:bg-gray-700
                      text-gray-900 dark:text-gray-100 rounded shadow-sm truncate"
              title="${(td.deskripsi && td.deskripsi.includes('ICD-9:')) ? td.deskripsi : '-'}">
            ${(td.deskripsi && td.deskripsi.includes("ICD-9:")) ? td.deskripsi : '-'}
          </div>
          ${state.role === "doctor" ? `
            <div class="flex space-x-2 justify-end">
              <button type="button"
                      onclick="updateSimulasi('tindakan','Primary','${td.nama}','Manual', window.claimState.tab)"
                      class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs">Pilih Utama</button>
              <button type="button"
                      onclick="updateSimulasi('tindakan','Secondary','${td.nama}','Manual', window.claimState.tab)"
                      class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-xs">Pilih Sekunder</button>
            </div>` : ``}
        </div>
      `);
    });
  }

  // Export
  window.addManual = addManual;
  window.addManualTindakan = addManualTindakan;
  window.renderManualTindakanList = renderManualTindakanList;
})();
