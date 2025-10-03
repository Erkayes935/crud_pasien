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

  async function addManualFromAutocomplete(tab, selected) {
    const state = Alpine.$data(document.getElementById('claimRoot'));
    if (!state.simulasi[tab]) {
      state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[] };
    }

    // bikin item baru (mirip AI → cuma kategori + score)
    const newItem = {
      kategori: selected.name,
      icd10_code: "",
      klinis: "-",
      tindakan: "-",
      score: 80,
      mapping: "",
      isManual: true,
      source: "Manual"
    };

    // fetch detail dummy
    const detailRes = await window.getDiagnosisDetail(selected.code);
    if (detailRes.status === "ok") {
      newItem.rowData = detailRes.data; // simpan full detail untuk modal
    }

    state.simulasi[tab].diagnosis.push(newItem);

    // render ulang tabel
    window.renderTable && window.renderTable(`diagnosis-${tab}`, state.simulasi[tab].diagnosis, "diagnosis", tab);
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

  // Render list manual tindakan di dalam modal diagnosis
  function renderManualTindakanList(tab) {
    const state = window.claimState || {};
    const listContainer = document.querySelector(".tindakan-list");
    if (!listContainer) return;

    const list = (state.simulasi?.[tab]?.tindakan || [])
      .filter(td => td.procedure_text || td.nama);

    listContainer.innerHTML = "";

    list.forEach((td, idx) => {
      const nama = td.procedure_text || td.nama || "-";
      const deskripsi = td.deskripsi || "-";
      listContainer.insertAdjacentHTML("beforeend", `
        <div class="grid grid-cols-3 gap-4 items-center bg-white dark:bg-gray-800 p-3 rounded shadow mb-2"
            data-id="manual-tindakan-${tab}-${idx}">
          <div class="font-semibold text-blue-600 underline cursor-pointer truncate"
              onclick="openManualDetailModal(window.claimState.simulasi['${tab}'].tindakan[${idx}], '${tab}', ${idx})">
            ${nama}
          </div>
          <div>
            <span class="block px-3 py-1 text-sm font-medium bg-gray-200 dark:bg-gray-700
                        text-gray-900 dark:text-gray-100 rounded shadow-sm whitespace-nowrap overflow-hidden text-ellipsis"
                  title="${deskripsi}">${deskripsi}</span>
          </div>
          ${window.claimState?.role === "doctor" ? `
            <div class="flex space-x-2 justify-end">
              <button type="button"
                      onclick="updateSimulasi('tindakan','Primary','${nama}','Manual','${tab}')"
                      class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs">Pilih Utama</button>
              <button type="button"
                      onclick="updateSimulasi('tindakan','Secondary','${nama}','Manual','${tab}')"
                      class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-xs">Pilih Sekunder</button>
            </div>` : ``}
        </div>
      `);
    });
  }
  
  async function addManualTindakanFromAutocomplete(tab, selected) {
    console.log(">>> addManualTindakanFromAutocomplete CALLED", {tab, selected});

    const state = Alpine.$data(document.getElementById('claimRoot'));
    if (!state.simulasi[tab]) {
      console.warn("tab not found in simulasi, inisialisasi dulu", tab);
      state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [], tindakan: [] };
    }
    if (!Array.isArray(state.simulasi[tab].tindakan)) {
      state.simulasi[tab].tindakan = [];
    }

    const newItem = {
      procedure_text: selected.procedure_text,
      deskripsi: "-",
      isManual: true,
      source: "Manual",
      rowData: null
    };

    const detailRes = await window.getTindakanDetail(selected.procedure_text);
    console.log(">>> detailRes", detailRes);
    if (detailRes?.status === "ok") {
      newItem.rowData = detailRes.data;
    }

    state.simulasi[tab].tindakan.push(newItem);
    console.log(">>> simulasi after push", state.simulasi[tab].tindakan);

    window.renderManualTindakanList?.(tab);
    window.syncHiddenInputs?.();
  }


  // Export
  window.addManual = addManual;
  window.addManualFromAutocomplete = addManualFromAutocomplete;
  window.addManualTindakanFromAutocomplete = addManualTindakanFromAutocomplete;
  window.addManualTindakan = addManualTindakan;
  window.renderManualTindakanList = renderManualTindakanList;
})();
