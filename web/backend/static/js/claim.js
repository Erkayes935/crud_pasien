function ensureDaily(dayId) {
  if (!window.manualInput) window.manualInput = { daily: {} };
  if (!manualInput.daily) manualInput.daily = {};
  if (!manualInput.daily[dayId]) {
    manualInput.daily[dayId] = {
      diagnosis:   { kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" },
      komorbid:    { kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" },
      komplikasi:  { kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" }
    };
  }
  return manualInput.daily[dayId];
}

// ==================== Generate AI ====================
function claimData(init) {
  const state = {
    role: init.role || 'doctor', // doctor, verifikator, coder
    tab: init.tab || 'admission',
    form: {},

    // 🔹 Simulasi hasil AI (utama/sekunder) → dari ClaimSimulation
    simulasi: init.sim || {
      admission: { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null },
      "daily-0": { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null },
      "daily-1": { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null },
      discharge: { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null },
      daily: { days: [], utama: null, sekunder: [] }
    },


    // 🔹 Evaluasi hasil klaim → dari ClaimDiagnosisEvaluation / ClaimProcedureEvaluation / ClaimCombinationAlternative
    evaluasiDiagnosis: [],
    evaluasiProcedure: [],
    alternatifKombinasi: [],

    // 🔹 Manual input tetap ada
    showManual: {
      admission: { diagnosis:false, komorbid:false, komplikasi:false },
      daily: {},
      discharge: { diagnosis:false, komorbid:false, komplikasi:false }
    },
    manualInput: {
      admission: {
        diagnosis: { kategori:"", klinis:"", icd:"", tindakan:"", score:"" },
        komorbid: { kategori:"", klinis:"", icd:"", tindakan:"", score:"" },
        komplikasi: { kategori:"", klinis:"", icd:"", tindakan:"", score:"" }
      },
      discharge: {
        diagnosis: { kategori:"", klinis:"", icd:"", tindakan:"", score:"" },
        komorbid: { kategori:"", klinis:"", icd:"", tindakan:"", score:"" },
        komplikasi: { kategori:"", klinis:"", icd:"", tindakan:"", score:"" }
      },
      daily: {}
    },

    modalOpen: false,
    modalTitle: '',
    modalContent: '',
    hideDefaultClose: false,
    currentDiagnosis: null,

    init() {
      const role = this.role;
      const claimId = document.getElementById("claimRoot")?.dataset.claimId;

      if (role === 'verifikator' && claimId) {
        // 🔹 langsung load dari DB (BE pecahan)
        loadRecommendations(claimId);
      }
    },

    statusIcon(s) {
      if (s === 'valid') return "✅";
      if (s === 'warning') return "⚠️";
      if (s === 'invalid') return "❌";
      return "";
    },
  };
  window.claimState = state;
  return state;
}

// 1. wrapper yang fetch data dari BE
async function generateAI() {
  const claimId = document.getElementById("claimRoot")?.dataset.claimId;
  if (!claimId) {
    alert("❌ Claim ID tidak ditemukan.");
    return;
  }

  try {
    const res = await fetch("/ai/recommendation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ claim_id: claimId })
    });
    const result = await res.json();
    console.log("📥 Data pecahan dari BE:", result);

    renderAI(result.data || []);   // 👉 lempar ke renderer
  } catch (err) {
    console.error("❌ Error generate AI:", err);
    alert("Gagal generate AI");
  }
}

// 2. pure renderer (kayak kodeku sebelumnya)
function renderAI(rows) {
  const state = Alpine.$data(document.getElementById("claimRoot"));

  const admission = rows.filter(r => r.stage === "admission");
  const daily = rows.filter(r => r.stage.startsWith("daily"));
  const discharge = rows.filter(r => r.stage === "discharge");


  // Admission
  renderTable("diagnosis-admission", admission.filter(r => r.category==="diagnosis"), "diagnosis", "admission");
  renderTable("komorbid-admission", admission.filter(r => r.category==="komorbid"), "komorbid", "admission");
  renderTable("komplikasi-admission", admission.filter(r => r.category==="komplikasi"), "komplikasi", "admission");

  // Daily (pakai groupedDaily kayak yg udah kita bahas)
  const dailyContainer = document.getElementById("daily-accordion");
  dailyContainer.innerHTML = "";
  const groupedDaily = {};
  daily.forEach(r => {
    if (!groupedDaily[r.stage]) groupedDaily[r.stage] = [];
    groupedDaily[r.stage].push(r);
  });

  Object.keys(groupedDaily).forEach((stage, idx) => {
    const hari = groupedDaily[stage];
    const dayId = `daily-${idx}`;

    ensureDaily(dayId);

    // accordion + counter
    dailyContainer.insertAdjacentHTML("beforeend", `
      <div class="bg-white dark:bg-gray-700 rounded shadow-sm mb-2" x-data="{open:false}">
        <button type="button" @click="open=!open"
          class="w-full flex justify-between px-4 py-2 bg-gray-200 dark:bg-gray-600 font-semibold">
          <span>Hari ${idx+1} </span>
          <div class="flex items-center gap-3">
            <span id="count-daily-${dayId}" class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">0</span>
            <span x-show="open">⬆</span>
            <span x-show="!open">⬇</span>
          </div>
        </button>
        <div x-show="open" class="p-2 space-y-2">
          <!-- Accordion Diagnosis -->
          <details class="border rounded mb-2">
            <summary class="cursor-pointer px-3 py-2 bg-gray-200 dark:bg-gray-700 flex items-center justify-between">
              <span class="font-semibold">Diagnosis</span>
              <span id="count-diagnosis-${dayId}"
                    class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">0</span>
            </summary>
            <div class="p-3">
              <table class="w-full text-xs border table-fixed">
                <tbody id="diagnosis-${dayId}"></tbody>
              </table>
            </div>
          </details>

          <!-- Accordion Komorbid -->
          <details class="border rounded mb-2">
            <summary class="cursor-pointer px-3 py-2 bg-gray-200 dark:bg-gray-700 flex items-center justify-between">
              <span class="font-semibold">Komorbid</span>
              <span id="count-komorbid-${dayId}"
                    class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">0</span>
            </summary>
            <div class="p-3">
              <table class="w-full text-xs border table-fixed">
                <tbody id="komorbid-${dayId}"></tbody>
              </table>
            </div>
          </details>

          <!-- Accordion Komplikasi -->
          <details class="border rounded">
            <summary class="cursor-pointer px-3 py-2 bg-gray-200 dark:bg-gray-700 flex items-center justify-between">
              <span class="font-semibold">Komplikasi</span>
              <span id="count-komplikasi-${dayId}"
                    class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">0</span>
            </summary>
            <div class="p-3">
              <table class="w-full text-xs border table-fixed">
                <tbody id="komplikasi-${dayId}"></tbody>
              </table>
            </div>
          </details>
        </div>
      </div>
    `);


    // render kategori
    renderTable(`diagnosis-${dayId}`, hari.filter(r => r.category==="diagnosis"), "diagnosis", dayId);
    renderTable(`komorbid-${dayId}`, hari.filter(r => r.category==="komorbid"), "komorbid", dayId);
    renderTable(`komplikasi-${dayId}`, hari.filter(r => r.category==="komplikasi"), "komplikasi", dayId);


    // hitung total counter daily
    const dailyCounter = document.getElementById(`count-daily-${dayId}`);
    if (dailyCounter) {
      const totalDaily =
        document.getElementById(`count-diagnosis-${dayId}`)?.textContent || 0 +
        document.getElementById(`count-diagnosis-${dayId}`)?.textContent || 0 +
        document.getElementById(`count-diagnosis-${dayId}`)?.textContent || 0;
      dailyCounter.textContent = totalDaily;
    }
  });

  // Discharge
  renderTable("diagnosis-discharge", discharge.filter(r => r.category==="diagnosis"), "diagnosis", "discharge");
  renderTable("komorbid-discharge", discharge.filter(r => r.category==="komorbid"), "komorbid", "discharge");
  renderTable("komplikasi-discharge", discharge.filter(r => r.category==="komplikasi"), "komplikasi", "discharge");
}



// ==================== Render Table ====================
function renderTable(targetId, items, type, tab, dayId = null) {
  const state = Alpine.$data(document.getElementById("claimRoot"))

  if (!state.simulasi[tab]) {
    state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [], tindakan: [] }
  }

  // === Filter AI vs Manual ===
  const oldItems = state.simulasi[tab][type] || []
  const oldAiItems = oldItems.filter(it => !it.isManual)
  const manualItems = oldItems.filter(it => it.isManual)

  const newAiItems = (items || []).filter(it => !it.isManual)
  const aiItems = newAiItems.length > 0 ? newAiItems : oldAiItems

  let merged = [...aiItems, ...manualItems]

  // === Hindari duplikat ===
  const seen = new Set()
  merged = merged.filter(it => {
    const key = `${it.kategori}-${it.icd10_code || it.icd9_code}-${it.tindakan || it.procedure_text}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })

  state.simulasi[tab][type] = merged

  const target = document.getElementById(targetId)
  if (!target) return
  target.innerHTML = ""

  // === Grouping Parent & Child ===
  let grouped = []
  let parentMap = {}
  let lastParentKey = null;

  merged.forEach(it => {
    if (!it.kategori) return;
    const name = it.kategori.trim();
    const type = it.type || "diagnosis"; // pastikan tiap item punya field type

    if (name.startsWith("→")) {
      // === Child ===
      if (lastParentKey && parentMap[lastParentKey]) {
        parentMap[lastParentKey].children.push({
          ...it,
          kategori: name.replace("→", "").trim()
        });
      }
    } else {
      // === Parent ===
      const parentKey = `${type}:${name}`; // gabungkan type biar unik
      parentMap[parentKey] = { ...it, children: [] };
      grouped.push(parentMap[parentKey]);
      lastParentKey = parentKey;
    }
  });

  // === Header Table ===
  const table = target.closest("table")
  if (table && !table.querySelector("thead")) {
    const thead = document.createElement("thead")
    thead.className = "bg-gray-100 dark:bg-gray-800"
    thead.innerHTML = `
      <tr>
        <th class="border px-3 py-2">Kategori</th>
        <th class="border px-3 py-2">Klinis</th>
        <th class="border px-3 py-2">ICD</th>
        <th class="border px-3 py-2">Tindakan</th>
        <th class="border px-3 py-2">Score</th>
        ${state.role === "doctor" ? `<th class="border px-3 py-2">Mapping</th>` : ``}
      </tr>`
    table.insertBefore(thead, table.firstChild)
  }

  // === Render Parent & Child ===
  grouped.forEach((parent, idx) => {
  const counter = 1 + (parent.children ? parent.children.length : 0)

  // <tbody> jadi scope Alpine
  const tbody = document.createElement("tbody")
  tbody.setAttribute("x-data", "{ open:false }")

  // parent row
  tbody.insertAdjacentHTML("beforeend", `
    <tr class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 font-medium text-sm"
        data-id="${dayId || tab}-${type}-${idx}" data-db-id="${parent.id}">
        <td class="border px-5 py-2 whitespace-nowrap overflow-hidden text-ellipsis max-w-[180px]">
          <span @click="open=!open" class="mr-1 cursor-pointer">
            <span x-show="!open" x-cloak>▶</span>
            <span x-show="open" x-cloak>▼</span>
          </span>
          <span class="cursor-pointer"
                onclick="openModalFromAttr(this, '${type}')">
          ${parent.kategori || parent.category || parent.nama_kategori || "-"}
          </span>
          <span class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">${counter}</span>
        </td>
        <td class="col-klinis border px-6 py-2">
          <div class="w-full max-w-[200px] whitespace-nowrap overflow-hidden text-ellipsis">
            ${parent.klinis || "-"}
          </div>
        </td>
        <td class="col-icd border px-[19px] py-2 text-center">${parent.icd10_code || parent.icd9_code || "-"}</td>
        <td class="col-tindakan border px-6 py-2">
          <div class="w-full max-w-[180px] truncate whitespace-nowrap overflow-hidden text-ellipsis">
          ${parent.tindakan || parent.procedure_text || "-"}</div>
        </td>
        <td class="border px-[18px] py-2 text-center">${parent.score || "-"}</div></td>
        ${state.role === "doctor" ? `
        <td class="border px-3 py-2 text-center">
          ${renderMappingSelect(parent, tab, type, idx)}
        </td>` : ``}
      </tr>
    `)

  // child rows ikut scope open
  parent.children.forEach((child, cIdx) => {
    tbody.insertAdjacentHTML("beforeend", `
      <tr x-show="open" x-cloak
          class="bg-gray-50 dark:bg-gray-800 italic text-sm"
          data-id="child-${dayId || tab}-${type}-${idx}-${cIdx}"
          data-db-id="${child.id}">
        <td class="border px-5 py-2 cursor-pointer whitespace-nowrap overflow-hidden text-ellipsis max-w-[180px]"
            onclick="openModalFromAttr(this, '${type}')">
          → ${child.kategori || "-"}
        </td>
        <td class="col-klinis border px-6 py-2">
          <div class="w-full max-w-[200px] whitespace-nowrap overflow-hidden text-ellipsis">
          ${child.klinis || "-"}</div>
        </td>
        <td class="col-icd border px-[19px] py-2 text-center">${child.icd10_code || child.icd9_code || "-"}</td>
        <td class="col-tindakan border px-6 py-2 whitespace-nowrap overflow-hidden text-ellipsis">
          <div class="w-full max-w-[180px] truncate whitespace-nowrap overflow-hidden text-ellipsis">
          ${child.tindakan || child.procedure_text || "-"}
          </div>
        </td>
        <td class="border px-[18px] py-2 text-center">${child.score || "-"}</td>
        ${state.role === "doctor" ? `
        <td class="border px-3 py-2 text-center">
          ${renderMappingSelect(child, tab, type, idx)}
        </td>` : ``}
      </tr>
    `)
  })

  target.appendChild(tbody)
  Alpine.initTree(tbody)
})

  // === Update Counter ===
  const counterId = dayId ? `count-${type}-${dayId}` : `count-${type}-${tab}`
  const countEl = document.getElementById(counterId)
  if (countEl) {
    let total = grouped.reduce((sum, p) => sum + 1 + p.children.length, 0)
    countEl.textContent = total
  }
  if (dayId) {
  const dailyCounter = document.getElementById(`count-daily-${dayId}`);
    if (dailyCounter) {
      // hitung total dari semua kategori (diagnosis + komorbid + komplikasi)
      const totalDaily =
      (parseInt(document.getElementById(`count-diagnosis-${dayId}`)?.textContent) || 0) +
      (parseInt(document.getElementById(`count-komorbid-${dayId}`)?.textContent) || 0) +
      (parseInt(document.getElementById(`count-komplikasi-${dayId}`)?.textContent) || 0);

      dailyCounter.textContent = totalDaily;
    }
  }

  // === Manual Row Input ===
  if (state.role === "doctor") {
    if (tab === "admission" || tab === "discharge" || tab.startsWith("daily-")) {
      const manualTbody = document.createElement("tbody")
      const tabPath = tab.startsWith("daily-") 
        ? `manualInput.daily['${tab}'].${type}`
        : `manualInput.${tab}.${type}`

      manualTbody.insertAdjacentHTML("beforeend", `
        <tr class="manual-row bg-gray-50 dark:bg-gray-800">
          <td class="border px-3 py-2 whitespace-nowrap overflow-hidden text-ellipsis max-w-[180px]"><input x-model="${tabPath}.kategori" placeholder="Nama Penyakit" class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600"></td>
          <td class="col-klinis border px-6 py-2 whitespace-nowrap overflow-hidden text-ellipsis max-w-[200px]"><input x-model="${tabPath}.klinis" placeholder="Klinis" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600"></td>
          <td class="col-icd border px-3 py-2"><input x-model="${tabPath}.icd10_code" placeholder="ICD-10" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600"></td>
          <td class="col-tindakan border px-3 py-2 whitespace-nowrap overflow-hidden text-ellipsis max-w-[180px]"><input x-model="${tabPath}.procedure_text" placeholder="Tindakan" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600"></td>
          <td class="border px-3 py-2"><input x-model="${tabPath}.score" placeholder="Score" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600"></td>
          <td class="border px-3 py-2 text-center">
            <button type="button" onclick="addManual('${type}','${tab}')" class="bg-green-600 text-white px-2 py-1 rounded">➕</button>
          </td>
        </tr>
      `)

      target.appendChild(manualTbody)
      Alpine.initTree(manualTbody)
    }
  }
}

// helper untuk potong teks + tooltip
function truncateText(text, max) {
  return text && text.length > max ? text.substring(0, max) + "…" : text
}

// helper untuk mapping select
function renderMappingSelect(item, tab, type, idx, isChild=false) {
  const disabled = window.claimState.role !== 'doctor' ? 'disabled' : ''
  return `
    <select onchange="onMappingChange(event, '${tab}', '${type}', ${idx})"
            class="border px-2 py-1 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-200 max-w-[120px] truncate"
            ${disabled}>
      <option value="" ${item.mapping===""?"selected":""}>Pilih</option>
      <option value="Diagnosis Utama" ${item.mapping==="Diagnosis Utama"?"selected":""}>Diagnosis Utama</option>
      <option value="Komorbid" ${item.mapping==="Komorbid"?"selected":""}>Komorbid</option>
      <option value="Komplikasi" ${item.mapping==="Komplikasi"?"selected":""}>Komplikasi</option>
      <option value="None" ${item.mapping==="None"?"selected":""}>None</option>
    </select>
  `
}


// ==================== Add Manual ====================
function addManual(type, tab) {
  const state = Alpine.$data(document.getElementById('claimRoot'))

  // Pastikan manualInput daily ada
  if (tab.startsWith("daily-") && !state.manualInput.daily[tab]) {
    state.manualInput.daily[tab] = {
      diagnosis: { kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" },
      komorbid:  { kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" },
      komplikasi:{ kategori:"", klinis:"", icd10_code:"", procedure_text:"", score:"" }
    }
  }

  // Ambil input
  const input = tab.startsWith("daily-")
    ? state.manualInput.daily[tab][type]
    : state.manualInput[tab][type]

  if (!input) {
    console.warn("❌ manualInput kosong:", tab, type)
    return
  }

  // Buat item manual
  const newItem = {
    kategori: input.kategori || "",
    klinis: input.klinis || "",
    icd10_code: input.icd10_code || "",
    procedure_text: input.procedure_text || "",
    score: input.score || 0,
    mapping: "",
    isManual: true,
    source: "Manual"
  }

  // Pastikan simulasi[tab][type] ada
  if (!state.simulasi[tab]) {
    state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[] }
  }
  if (!Array.isArray(state.simulasi[tab][type])) {
    state.simulasi[tab][type] = []
  }

  // Tambahkan item ke simulasi per-tab
  state.simulasi[tab][type].push(newItem)

  // Sinkronisasi daily summary
  if (tab.startsWith("daily-")) {
    const idx = parseInt(tab.split("-")[1], 10);
    if (!state.simulasi.daily) state.simulasi.daily = { days: [], utama:null, sekunder:[] };
    state.simulasi.daily.days[idx] = state.simulasi[tab];

    const allDays = state.simulasi.daily.days || [];
    state.simulasi.daily.utama = null;
    state.simulasi.daily.sekunder = [];
    allDays.forEach(d => {
      if (d.utama && !state.simulasi.daily.utama) state.simulasi.daily.utama = d.utama;
      if (Array.isArray(d.sekunder)) state.simulasi.daily.sekunder.push(...d.sekunder);
    });
  }

  ensureDaily(dayId);

  // Render ulang tabel
  renderTable(`${type}-${tab}`, state.simulasi[tab][type], type, tab)

  // 🚨 Enrichment BE kalau endpoint memang ada

  fetch("/ai/recommendation/detail", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      claim_id: state.claimId,
      type,
      ...newItem
    })
  })
  .then(res => res.json())
  .then(data => {
    Object.assign(newItem, data.data || {})
    renderTable(`${type}-${tab}`, state.simulasi[tab][type], type, tab)
  })
  .catch(err => console.error("AI enrichment failed", err))
}

function addManualTindakan() {
  const namaEl = document.getElementById("manualNamaTindakan");
  if (!namaEl) return alert("Input manual tindakan tidak ditemukan");

  const nama = namaEl.value.trim();
  if (!nama) {
    alert("Nama tindakan wajib diisi");
    return;
  }

  // 🔹 object manual tanpa id (id nanti dari DB saat Save Draft)
  const newTd = {
    nama,
    deskripsi: "-",       // sementara kosong, nanti bisa diisi autocomplete/bridging
    source: "Manual",
    isManual: true
  };

  // 🔹 simpan ke state FE
  const state = window.claimState;
  if (!state.manualTindakan) state.manualTindakan = [];
  state.manualTindakan.push(newTd);

  // 🔹 ambil index array manual terbaru (buat referensi openManualDetailModal)
  const idx = state.manualTindakan.length - 1;

  // 🔹 render ke UI (pakai index, bukan id)
  const listContainer = document.querySelector(".tindakan-list");
  if (listContainer) {
    listContainer.insertAdjacentHTML("afterbegin", `
      <div class="grid grid-cols-3 items-center bg-white dark:bg-gray-800 p-3 rounded shadow mb-2 gap-4">

        <!-- Nama tindakan -->
        <div class="font-semibold text-blue-600 underline cursor-pointer truncate"
            onclick="openManualNestedProcedureModal(${idx})">
          ${newTd.nama}
        </div>

        <!-- Deskripsi -->
        <div class="px-3 py-1 text-sm font-medium bg-gray-200 dark:bg-gray-700
                    text-gray-900 dark:text-gray-100 rounded shadow-sm truncate"
            title="${(newTd.deskripsi && newTd.deskripsi.includes('ICD-9:')) ? newTd.deskripsi : '-'}">
          ${(newTd.deskripsi && newTd.deskripsi.includes("ICD-9:")) ? newTd.deskripsi : '-'}
        </div>

        <!-- Tombol -->
        <div class="flex space-x-2 justify-end">
          <button type="button"
                  onclick="updateSimulasi('tindakan','Primary','${newTd.nama}','Manual', window.claimState.tab)"
                  class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs">Pilih Utama</button>
          <button type="button"
                  onclick="updateSimulasi('tindakan','Secondary','${newTd.nama}','Manual', window.claimState.tab)"
                  class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-xs">Pilih Sekunder</button>
        </div>
      </div>


    `);
  }

  // reset input
  namaEl.value = "";
}

// ==================== Modal ====================

function openModal(title, content, { hideDefaultClose = false } = {}) {
  const state = Alpine.$data(document.getElementById('claimRoot'))
  state.modalOpen = true
  state.modalTitle = title
  state.modalContent = content
  state.hideDefaultClose = hideDefaultClose
}

function updateRingkasanFromRow(itemId, dx) {
  if (!dx || !itemId) return;

  const row = document.querySelector(`[data-id="${itemId}"]`);
  if (!row) return;

  // === update kolom Klinis ===
  const klinisCell = row.querySelector(".col-klinis");
  if (klinisCell) {
    let text = "";

    if (Array.isArray(dx.klinis)) {
      text = dx.klinis.filter(Boolean).join(", ");
    } else if (typeof dx.klinis === "string") {
      text = dx.klinis;
    } else if (typeof dx.klinis === "object" && dx.klinis !== null) {
      text = [
        dx.klinis.justifikasi,
        dx.klinis.bukti_klinis,
        dx.klinis.syarat_klinis
      ].filter(Boolean).join(", ");
    }

    klinisCell.innerHTML = text
      ? `<span title="${text}">${truncateText(text, 20)}</span>`
      : "-";
  }

  // === update kolom ICD ===
  const icdCell = row.querySelector(".col-icd");
  if (icdCell) {
    if (dx.icd10_code) {
      icdCell.innerText = dx.icd10_code;
    } else if (dx.icd10 && dx.icd10.kode_icd) {
      icdCell.innerText = dx.icd10.kode_icd;
    } else if (dx.icd9_code) {
      icdCell.innerText = dx.icd9_code;
    } else {
      icdCell.innerText = "-";
    }
  }

  // === update kolom Tindakan ===
  const tindakanCell = row.querySelector(".col-tindakan");
  if (tindakanCell) {
    if (dx.tindakan && dx.tindakan.length > 0) {
      const text = dx.tindakan.map(t => t.procedure_text || t.nama).join(", ");
      tindakanCell.innerHTML = `<span title="${text}">${truncateText(text, 20)}</span>`;
    } else {
      tindakanCell.innerText = "-";
    }
  }
}


async function openModalFromAttr(el, type) {
  const tr = el.closest("tr");
  const dbId = tr?.dataset.dbId;
  const uiId = tr?.dataset.id;
  const claimId = document.getElementById("claimRoot")?.dataset.claimId;

  try {
    let dx;
    if (dbId && !isNaN(Number(dbId))) {
      const url = `/ai/recommendation/detail?claim_id=${claimId}&rec_type=${type}&item_id=${dbId}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const result = await res.json();
      dx = result.data;
    } else {
      dx = tr?.dataset.row ? JSON.parse(tr.dataset.row) : {};
    }

    // 🔹 tampilkan modal
    openModal(`Detail ${type}`, buildModalContent(dx));

    // 🔹 baru update ringkasan (kolom tabel)
    updateRingkasanFromRow(uiId, dx);

  } catch (err) {
    console.error("❌ Gagal load modal detail:", err);
  }
}




function openManualDetailModal(it) {
  // bikin payload mirip hasil backend supaya bisa diproses buildModalContent
  const dummy = {
    kategori: it.kategori || "Manual",
    klinis: it.klinis || "-",
    icd10: {
      kode_icd: it.icd10_code || "-",
      deskripsi: "-"
    },
    tindakan: it.procedure_text ? [{ procedure_text: it.procedure_text }] : [],
    // field tambahan sesuai struktur asli
    validitas: "-",
    status: "-",
    ina_cbg: "-",
    faskes: "-",
    rawat_inap: "-",
    syarat_klinis: "-"
  }

  const title = `Detail Diagnosis (${dummy.kategori})`
  openModal(title, buildModalContent(dummy))

  // update ringkasan biar kolom Klinis / ICD / Tindakan juga keisi
  updateRingkasanFromRow(dummy)
}


function buildModalContent(it) {
  return renderDiagnosisDetail(it);
}

function renderDiagnosisDetail(it) {
  const klinisRaw = it.klinis || {};
  let klinis = {};
  if (typeof klinisRaw === "string") {
    klinis = { justifikasi: klinisRaw, bukti_klinis: "-", syarat_klinis: "-" };
  } else if (Array.isArray(klinisRaw)) {
    klinis = { justifikasi: klinisRaw.join(", "), bukti_klinis: "-", syarat_klinis: "-" };
  } else if (typeof klinisRaw === "object" && klinisRaw !== null) {
    klinis = {
      justifikasi: klinisRaw.justifikasi || "-",
      bukti_klinis: klinisRaw.bukti_klinis || "-",
      syarat_klinis: klinisRaw.syarat_klinis || "-"
    };
  } else {
    klinis = { justifikasi: "-", bukti_klinis: "-", syarat_klinis: "-" };
  }

  const icd10 = it.icd10 || { kode_icd: it.icd10_code || "-" };
  const tindakan = it.tindakan || [];
  const rawat = it.rawat_inap || {};
  const faskes = it.faskes || {};
  const rujukan = it.rujukan || {};

  // helper box 2 kolom
  const renderBox = (label, value, status = "default") => {
    let colorClass = "bg-gray-200 text-gray-800"; // default abu
    if (status === "valid") colorClass = "bg-green-600 text-white";
    if (status === "invalid") colorClass = "bg-red-600 text-white";
    const safeValue = value || "-";
    return `
      <div class="grid grid-cols-2">
        <div class="bg-gray-700 text-white px-3 py-2">${label}</div>
        <div class="${colorClass} px-3 py-2">${safeValue}</div>
      </div>
    `;
  };

  return `
    <div class="space-y-6 text-sm">

      <!-- KLINIS -->
      <section class="rounded shadow overflow-hidden">
        <div class="bg-blue-600 text-white px-3 py-2 font-bold">KLINIS</div>
        <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
          ${renderBox("Justifikasi", klinis.justifikasi, klinis.status)}
          ${renderBox("Bukti Klinis", klinis.bukti || klinis.bukti_klinis, klinis.status_bukti)}
          ${renderBox("Syarat Klinis", klinis.syarat || klinis.syarat_klinis, klinis.status_syarat)}
        </div>
      </section>

      <!-- ICD-10 -->
      <section class="rounded shadow overflow-hidden">
        <div class="bg-blue-600 text-white px-3 py-2 font-bold">ICD-10</div>
        <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
          ${renderBox("Kode ICD", icd10.kode_icd, icd10.status_icd)}
          ${renderBox("Struktur ICD", icd10.struktur_kode, icd10.status)}
          ${renderBox("Kode Ganda", icd10.kode_ganda, icd10.status_ganda)}
          ${renderBox("Z-Code", icd10.z_code, icd10.status_z)}
          ${renderBox("Kode Khusus BPJS", icd10.kode_bpjs_khusus, icd10.status_bpjs)}
        </div>
      </section>

      <!-- TINDAKAN -->
      <section class="rounded shadow overflow-hidden">
        <div class="bg-blue-600 text-white px-3 py-2 font-bold">TINDAKAN</div>
        <div class="p-3 bg-gray-100 dark:bg-gray-700">
          ${renderTindakan(tindakan)}
        </div>
      </section>

      <!-- RAWAT INAP -->
      <section class="rounded shadow overflow-hidden">
        <div class="bg-blue-600 text-white px-3 py-2 font-bold">RAWAT INAP</div>
        <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
          ${renderBox("Indikasi", rawat.indikasi, rawat.status_indikasi)}
          ${renderBox("Lama Rawat", rawat.lama_rawat, rawat.status_lama)}
          ${renderBox("Perpanjangan", rawat.perpanjangan, rawat.status_perpanjangan)}
        </div>
      </section>

      <!-- FASKES -->
      <section class="rounded shadow overflow-hidden">
        <div class="bg-blue-600 text-white px-3 py-2 font-bold">FASKES</div>
        <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
          ${renderBox("Kesesuaian RS", faskes.kesesuaian_rs, faskes.status)}
        </div>
      </section>

      <!-- RUJUKAN -->
      <section class="rounded shadow overflow-hidden">
        <div class="bg-blue-600 text-white px-3 py-2 font-bold">RUJUKAN</div>
        <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
          ${renderBox("Syarat", rujukan.syarat, rujukan.status_syarat)}
          ${renderBox("Kelayakan", rujukan.kelayakan, rujukan.status_kelayakan)}
        </div>
      </section>

    </div>
  `;
}


function renderTindakan(list) {
  const tindakanList = list && list.length > 0 
    ? list.map(td => `
      <div class="grid grid-cols-3 gap-4 items-center bg-white dark:bg-gray-800 p-3 rounded shadow mb-2"
          data-procid="${td.id}">
        <!-- Nama Tindakan -->
        <div class="font-semibold text-blue-600 underline cursor-pointer truncate"
            onclick="openProcedureModal('${td.id || ''}')">
          ${td.nama}
        </div>

        <!-- Deskripsi -->
        <div>
          <span
            class="block px-3 py-1 text-sm font-medium bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded shadow-sm whitespace-nowrap overflow-hidden text-ellipsis"
            title="${(td.deskripsi && td.deskripsi.includes('ICD-9:')) ? td.deskripsi : '-'}">
            ${(td.deskripsi && td.deskripsi.includes("ICD-9:")) ? td.deskripsi : '-'}
          </span>
        </div>

        <!-- Tombol -->
        <div class="flex justify-end space-x-2">
          <button type="button"
                  onclick="updateSimulasi('tindakan','Primary','${td.nama}','', window.claimState.tab)"
                  class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs shadow">
            Pilih Utama
          </button>
          <button type="button"
                  onclick="updateSimulasi('tindakan','Secondary','${td.nama}','', window.claimState.tab)"
                  class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-xs shadow">
            Pilih Sekunder
          </button>
        </div>
      </div>
    `).join("")
    : `<div class="italic text-gray-500">Tidak ada tindakan AI</div>`;

  const manualForm = `
    <div class="tindakan-list mt-4"></div>
    <div class="mt-4 p-3 border rounded bg-gray-50 dark:bg-gray-700">
      <div class="font-semibold mb-2">Tambah Tindakan Manual</div>
      <input id="manualNamaTindakan" placeholder="Nama Tindakan" 
            class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600" />
      <button type="button" onclick="addManualTindakan()" 
              class="mt-2 bg-green-600 text-white px-3 py-1 rounded">➕ Tambah</button>
    </div>
  `;
  
  return tindakanList + manualForm;
}


async function openProcedureModal(procId) {
  const claimId = document.getElementById("claimRoot")?.dataset.claimId;
  const url = `/ai/recommendation/detail?claim_id=${claimId}&rec_type=procedure&item_id=${procId}`;

  try {
    const res = await fetch(url);
    const { data } = await res.json();
    const d = (data.tindakan && data.tindakan[0]) || {};

    const deskripsiGabungan = `ICD-9: ${d.icd9 || '-'}, Status: ${d.status || '-'}, INA-CBG: ${d.ina_cbg || '-'}`;

    const dx = window.claimState.currentDiagnosis;
    if (dx && Array.isArray(dx.tindakan)) {
      dx.tindakan.forEach(td => {
        if (td.id == procId) {
          td.deskripsi = deskripsiGabungan;
        }
      });
    }
    // tampilkan nested modal
    const content = `
      <div class="flex justify-between items-center mb-3">
        <h3 class="text-lg font-bold">Detail Tindakan (${data.procedure_text || '-'})</h3>
        <button type="button" onclick="closeNestedModal()" class="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded">✕</button>
      </div>
      <div class="grid grid-cols-2 gap-2">
        <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Kode ICD-9:</b></div>
        <div class="bg-gray-800 px-3 py-2 rounded">${d.icd9 || '-'}</div>
        
        <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Deskripsi:</b></div> 
        <div class="bg-gray-800 px-3 py-2 rounded">${deskripsiGabungan}</div>

        <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Validitas:</b></div>
        <div class="bg-gray-800 px-3 py-2 rounded">${d.validitas || '-'}</div>

        <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Status:</b></div>
        <div class="bg-gray-800 px-3 py-2 rounded">${d.status || '-'}</div>

        <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>INA-CBG:</b></div>
        <div class="bg-gray-800 px-3 py-2 rounded">${d.ina_cbg || '-'}</div>

        <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Faskes:</b></div>
        <div class="bg-gray-800 px-3 py-2 rounded">${d.faskes || '-'}</div>

        <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Rawat Inap:</b></div>
        <div class="bg-gray-800 px-3 py-2 rounded">${d.rawat_inap || '-'}</div>

        <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Syarat Klinis:</b></div>
        <div class="bg-gray-800 px-3 py-2 rounded">${d.syarat_klinis || '-'}</div>
      </div>
    `;
    openModal(`Detail Tindakan (${data.procedure_text || '-'})`, content, { hideDefaultClose: true });

    // ✅ update DOM langsung (biar instant)
    const itemEl = document.querySelector(`[data-procid='${procId}'] .text-xs`);
    if (itemEl) itemEl.textContent = deskripsiGabungan;

  } catch (err) {
    console.error("Gagal load detail tindakan", err);
  }
}


function openManualNestedProcedureModal(idx) {
  const td = window.claimState.manualTindakan[idx] || {};

  const content = `
    <div class="flex justify-between items-center mb-3">
      <h3 class="text-lg font-bold">Detail Tindakan (${td.nama} - Manual)</h3>
      <button type="button" onclick="closeNestedModal()" 
              class="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded">✕</button>
    </div>

    <div class="grid grid-cols-2 gap-2">
      <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Kode ICD-9:</b></div>
      <div class="bg-gray-800 px-3 py-2 rounded field-icd9">${td.icd9 || '-'}</div>
      
      <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Deskripsi:</b></div> 
      <div class="bg-gray-800 px-3 py-2 rounded">${td.deskripsi || '-'}</div>

      <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Validitas:</b></div>
      <div class="bg-gray-800 px-3 py-2 rounded">${td.validitas || '-'}</div>

      <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Status:</b></div>
      <div class="bg-gray-800 px-3 py-2 rounded field-status">${td.status || '-'}</div>

      <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>INA-CBG:</b></div>
      <div class="bg-gray-800 px-3 py-2 rounded field-inacbg">${td.ina_cbg || '-'}</div>

      <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Faskes:</b></div>
      <div class="bg-gray-800 px-3 py-2 rounded">${td.faskes || '-'}</div>

      <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Rawat Inap:</b></div>
      <div class="bg-gray-800 px-3 py-2 rounded">${td.rawat_inap || '-'}</div>

      <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Syarat Klinis:</b></div>
      <div class="bg-gray-800 px-3 py-2 rounded">${td.syarat_klinis || '-'}</div>
    </div>
  `;

  openModal(`Detail Tindakan (${td.nama} - Manual)`, content);
}


function closeNestedModal() {
  const dx = window.claimState.currentDiagnosis;
  if (dx) {
    // panggil ulang modal diagnosis
    const title = `Detail Diagnosis (${dx.kategori || '-'})`;
    openModal(title, buildModalContent(dx));
  } else {
    // fallback: kalau nggak ada data, baru beneran nutup modal
    const state = Alpine.$data(document.getElementById('claimRoot'));
    state.modalOpen = false;
  }
}

// ==================== Simulasi ====================
function normalizeOpt(opt) {
  if (opt === "Diagnosis Utama" || opt === "Utama" || opt === "Primary Claim" || opt === "Primary") return "Primary"
  if (opt === "Komorbid" || opt === "Secondary-Komorbid") return "Secondary-Komorbid"
  if (opt === "Komplikasi" || opt === "Secondary-Komplikasi") return "Secondary-Komplikasi"
  if (opt === "Sekunder" || opt === "Secondary Claim" || opt === "Secondary") return "Secondary"
  if (opt === "None") return "None"
  return opt
}

function normalizeItem(val) {
  if (typeof val === "string") {
    return { 
      name: val.split(" [")[0] || "-", 
      label: "", 
      mapping: "", 
      source: "Manual", 
      isManual: true 
    }
  }
  return {
    ...val,  // jaga semua field biar tetap ada
    name: val.name || val.kategori || val.icd || "-",
    label: val.label || "",
    mapping: val.mapping || ""
  }
}

function updateSimulasi(type, opt, value, source, tab) {
  const state = Alpine.$data(document.getElementById("claimRoot"));
  if (!tab) tab = "admission";
  const finalOpt = normalizeOpt(opt || value.mapping || "");

  // --- pastikan struktur simulasi[tab] selalu ada & lengkap ---
  if (!state.simulasi[tab] || typeof state.simulasi[tab] !== "object" || Array.isArray(state.simulasi[tab])) {
    state.simulasi[tab] = {};
  }
  let sim = state.simulasi[tab];

  if (!("utama" in sim)) sim.utama = null;
  if (!Array.isArray(sim.sekunder)) sim.sekunder = [];
  if (!("tindakanUtama" in sim)) sim.tindakanUtama = null;
  if (!Array.isArray(sim.tindakanSekunder)) sim.tindakanSekunder = [];
  if (!("tarifDraft" in sim)) sim.tarifDraft = null;

  const item = typeof value === "string"
  ? { name: value.split(" [")[0], label: "", source: "Manual", isManual: true }
  : { ...value };


  if (source) {
    if (finalOpt === "Primary") item.label = "Utama Klinis";
    else if (finalOpt === "Secondary-Komorbid") item.label = "Komorbid";
    else if (finalOpt === "Secondary-Komplikasi") item.label = "Komplikasi";
  }

  // Diagnosis, Komorbid, Komplikasi
  if (type === "diagnosis" || type === "komorbid" || type === "komplikasi") {
    if (finalOpt === "Primary") {
      const oldPrimary = sim.utama;
      sim.sekunder = sim.sekunder.filter(dx => dx.name !== item.name);
      sim.utama = item;
      if (oldPrimary && oldPrimary.name !== item.name) sim.sekunder.unshift(oldPrimary);
    } else if (finalOpt.startsWith("Secondary")) {
      if (sim.utama && sim.utama.name === item.name) sim.utama = null;
      const idx = sim.sekunder.findIndex(dx => dx.name === item.name);
      if (idx === -1) sim.sekunder.push(item);
      else sim.sekunder[idx] = item;
    } else if (finalOpt === "None") {
      if (sim.utama && sim.utama.name === item.name) sim.utama = null;
      sim.sekunder = sim.sekunder.filter(dx => dx.name !== item.name);
    }
  }

  // Tindakan
  if (type === "tindakan") {
    const nama = typeof value === "string" ? value : value.name;
    if (finalOpt === "Primary") {
      const oldPrimary = sim.tindakanUtama;
      sim.tindakanSekunder = sim.tindakanSekunder.filter(td => td.name !== nama);
      sim.tindakanUtama = { name: nama };
      if (oldPrimary && oldPrimary.name !== nama) sim.tindakanSekunder.unshift(oldPrimary);
    } else if (finalOpt === "Secondary") {
      if (sim.tindakanUtama?.name === nama) sim.tindakanUtama = null;
      if (!sim.tindakanSekunder.find(td => td.name === nama)) {
        sim.tindakanSekunder.push({ name: nama });
      }
    } else if (finalOpt === "None") {
      if (sim.tindakanUtama?.name === nama) sim.tindakanUtama = null;
      sim.tindakanSekunder = sim.tindakanSekunder.filter(td => td.name !== nama);
    }
  }

  // 🔄 khusus untuk daily, sync ke summary
  if (tab.startsWith("daily-")) {
    const idxDay = parseInt(tab.split("-")[1], 10);
    if (!state.simulasi.daily.days) state.simulasi.daily.days = [];
    state.simulasi.daily.days[idxDay] = state.simulasi[tab];

    // rebuild summary daily
    state.simulasi.daily.utama = null;
    state.simulasi.daily.sekunder = [];
    state.simulasi.daily.days.forEach(d => {
      if (d?.utama && !state.simulasi.daily.utama) {
        state.simulasi.daily.utama = d.utama;
      }
      if (Array.isArray(d?.sekunder)) {
        state.simulasi.daily.sekunder.push(...d.sekunder);
      }
    });
  }

  console.log("🟢 Simulasi updated:", state.simulasi);
}


// ==================== Helpers ====================

function confidenceBadge(val){
  val=parseInt(val)
  let c=val>=80?'bg-green-600':val>=60?'bg-yellow-500':'bg-red-600'
  return `<span class="px-2 py-0.5 rounded text-white text-xs ${c}">${val}%</span>`
}

async function loadRecommendations(claimId) {
  try {
    const res = await fetch(`/claims/${claimId}/recommendations`)
    if (!res.ok) {
      console.error("❌ Gagal load rekomendasi dari DB")
      return
    }
    const recs = await res.json()
    console.log("📥 Data rekomendasi dari DB:", recs)

    // Grouping per stage & category
    const grouped = { admission: {}, discharge: {}, daily: {} }
    recs.forEach(r => {
      const parts = r.category.split("_", 2)
      const stage = parts[0]
      const cat = parts[1] || "unknown"

      if (stage === "admission") {
        grouped.admission[cat] = grouped.admission[cat] || []
        grouped.admission[cat].push(r)
      } else if (stage === "discharge") {
        grouped.discharge[cat] = grouped.discharge[cat] || []
        grouped.discharge[cat].push(r)
      } else if (stage.startsWith("daily")) {
        grouped.daily[stage] = grouped.daily[stage] || { diagnosis: [], komorbid: [], komplikasi: [] }
        grouped.daily[stage][cat] = grouped.daily[stage][cat] || []
        grouped.daily[stage][cat].push(r)
      }
    })

    // === Admission ===
    renderTable("diagnosis-admission", (grouped.admission.diagnosis || []).map(mapRecommendation), "diagnosis", "admission")
    renderTable("komorbid-admission", (grouped.admission.komorbid || []).map(mapRecommendation), "komorbid", "admission")
    renderTable("komplikasi-admission", (grouped.admission.komplikasi || []).map(mapRecommendation), "komplikasi", "admission")

    // === Daily ===
    const dailyContainer = document.getElementById("daily-accordion")
    dailyContainer.innerHTML = ""

    Object.keys(grouped.daily).forEach((stage, idx) => {
      const hari = grouped.daily[stage]
      hari.tanggal = hari.tanggal || `2025-09-${String(idx+1).padStart(2, "0")}`
      const dayId = `daily-${idx}`

      dailyContainer.insertAdjacentHTML("beforeend", `
        <div class="bg-white dark:bg-gray-700 rounded shadow-sm" x-data="{open:false}">
          <button type="button" @click="open=!open"
                  class="w-full flex justify-between px-4 py-2 bg-gray-200 dark:bg-gray-600 font-semibold">
            <span>Hari ${idx+1} (${hari.tanggal || '-'})</span>
            <span x-show="open">⬆️</span><span x-show="!open">⬇️</span>
          </button>
          <div x-show="open" class="p-2 space-y-2">
            <div><table class="w-full text-xs border table-fixed"><tbody id="diagnosis-${dayId}"></tbody></table></div>
            <div><table class="w-full text-xs border table-fixed"><tbody id="komorbid-${dayId}"></tbody></table></div>
            <div><table class="w-full text-xs border table-fixed"><tbody id="komplikasi-${dayId}"></tbody></table></div>
          </div>
        </div>
      `)

      renderTable(`diagnosis-${dayId}`, (hari.diagnosis || []).map(mapRecommendation), "diagnosis", dayId)
      renderTable(`komorbid-${dayId}`, (hari.komorbid || []).map(mapRecommendation), "komorbid", dayId)
      renderTable(`komplikasi-${dayId}`, (hari.komplikasi || []).map(mapRecommendation), "komplikasi", dayId)
    })

    // === Discharge ===
    renderTable("diagnosis-discharge", (grouped.discharge.diagnosis || []).map(mapRecommendation), "diagnosis", "discharge")
    renderTable("komorbid-discharge", (grouped.discharge.komorbid || []).map(mapRecommendation), "komorbid", "discharge")
    renderTable("komplikasi-discharge", (grouped.discharge.komplikasi || []).map(mapRecommendation), "komplikasi", "discharge")

  } catch (err) {
    console.error("❌ Error loadRecommendations:", err)
  }
}

function mapRecommendation(r) {
  return {
    id: r.id,
    kategori: r.nama_kategori || r.kategori || r.category || r.nama || "-",
    klinis: r.klinis || r.justifikasi || "-",
    icd10_code: r.icd10_code || r.icd || "-",
    procedure_text: r.tindakan || r.procedure_text || "-",
    score: r.confidence_score || r.score || 0,
    child: r.child || false,
    isManual: r.is_manual || false,
  };
}

function onMappingChange(event, tab, type, idx) {
  const state = Alpine.$data(document.getElementById('claimRoot'))
  const arr = state.simulasi?.[tab]?.[type] || []
  const item = arr[idx]

  if (!item) {
    console.warn("❌ onMappingChange: item not found", { tab, type, idx })
    return
  }

  const opt = event.target.value
  item.mapping = opt
  updateSimulasi(type, opt, normalizeItem(item), item.source || (item.isManual ? "Manual" : "AI"), tab)

  // 🔄 sinkronisasi tambahan untuk Daily
  if (tab.startsWith("daily-")) {
    const idxDay = parseInt(tab.split("-")[1], 10)
    if (!state.simulasi.daily.days) state.simulasi.daily.days = []
    state.simulasi.daily.days[idxDay] = state.simulasi[tab]

    // rebuild summary daily
    state.simulasi.daily.utama = null
    state.simulasi.daily.sekunder = []
    state.simulasi.daily.days.forEach(d => {
      if (d?.utama && !state.simulasi.daily.utama) {
        state.simulasi.daily.utama = d.utama
      }
      if (Array.isArray(d?.sekunder)) {
        state.simulasi.daily.sekunder.push(...d.sekunder)
      }
    })
  }
}

// ==================== Generate Summary ====================
async function generateSummary() {
  const claimId = document.getElementById("claimRoot")?.dataset.claimId;
  if (!claimId) {
    alert("❌ Claim ID tidak ditemukan.");
    return;
  }

  try {
    const state = Alpine.$data(document.getElementById("claimRoot"));

    const payload = {
      claim_id: claimId,
      simulasi: state.simulasi,
    };

    const res = await fetch(`/ai/summary/${claimId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("Gagal request summary");
    const data = await res.json();

    console.log("📥 Summary dari BE:", data);

    // Render ke panel
    renderEvaluasiDiagnosis(data.diagnosis || {});
    renderEvaluasiProcedure(data.procedure || {});
    renderAlternatifKombinasi(data.alternatif || []);

    alert("✅ Summary berhasil digenerate");
  } catch (err) {
    console.error("Error generate summary:", err);
    alert("❌ Gagal generate summary");
  }
}

// ==================== Panel Evaluasi Diagnosis ====================
function renderEvaluasiDiagnosis(data) {
  const target = document.getElementById("evaluasi-diagnosis");
  if (!target) return;
  target.innerHTML = "";

  if (!data || Object.keys(data).length === 0) {
    target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada evaluasi</div>`;
    return;
  }

  target.innerHTML = `
    <table class="w-full border border-gray-300 dark:border-gray-600 text-sm">
      <tr><th class="bg-gray-200 dark:bg-gray-700 px-3 py-2 text-left">Validitas Klinis Kombinasi</th>
          <td class="px-3 py-2">${statusIcon(data.validitas)}</td></tr>
      <tr><th class="bg-gray-200 dark:bg-gray-700 px-3 py-2 text-left">Severity</th>
          <td class="px-3 py-2">${data.severity || "-"}</td></tr>
      <tr><th class="bg-gray-200 dark:bg-gray-700 px-3 py-2 text-left">Kode INA-CBG</th>
          <td class="px-3 py-2">${data.ina_cbg || "-"}</td></tr>
      <tr><th class="bg-gray-200 dark:bg-gray-700 px-3 py-2 text-left">Estimasi Tarif</th>
          <td class="px-3 py-2">${formatRupiah(data.tarif)}</td></tr>
      <tr><th class="bg-gray-200 dark:bg-gray-700 px-3 py-2 text-left">Syarat Klinis</th>
          <td class="px-3 py-2">${data.syarat || "-"}</td></tr>
      <tr><th class="bg-gray-200 dark:bg-gray-700 px-3 py-2 text-left">Evaluasi Faskes</th>
          <td class="px-3 py-2">${data.faskes || "-"}</td></tr>
      <tr><th class="bg-gray-200 dark:bg-gray-700 px-3 py-2 text-left">Rawat Inap</th>
          <td class="px-3 py-2">${data.rawat_inap || "-"}</td></tr>
    </table>
  `;
}

// ==================== Panel Evaluasi Tindakan ====================
function renderEvaluasiProcedure(data) {
  const target = document.getElementById("evaluasi-procedure");
  if (!target) return;
  target.innerHTML = "";

  if (!data || Object.keys(data).length === 0) {
    target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada evaluasi tindakan</div>`;
    return;
  }

  target.innerHTML = `
    <table class="w-full border border-gray-300 dark:border-gray-600 text-sm">
      <tr><th class="bg-gray-200 dark:bg-gray-700 px-3 py-2 text-left">Tindakan Wajib Kombinasi</th>
          <td class="px-3 py-2">${statusIcon(data.tindakan_wajib)}</td></tr>
      <tr><th class="bg-gray-200 dark:bg-gray-700 px-3 py-2 text-left">Validasi Pilihan Verifikator</th>
          <td class="px-3 py-2">${statusIcon(data.validasi)}</td></tr>
      <tr><th class="bg-gray-200 dark:bg-gray-700 px-3 py-2 text-left">Dampak INA-CBG / Tarif</th>
          <td class="px-3 py-2">${data.dampak || "-"}</td></tr>
      <tr><th class="bg-gray-200 dark:bg-gray-700 px-3 py-2 text-left">Konflik / Duplikasi</th>
          <td class="px-3 py-2">${data.konflik || "-"}</td></tr>
    </table>
  `;
}

// ==================== Panel Alternatif Kombinasi ====================
function renderAlternatifKombinasi(items) {
  const target = document.getElementById("alternatif");
  if (!target) return;
  target.innerHTML = "";

  if (!items || items.length === 0) {
    target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada alternatif kombinasi</div>`;
    return;
  }

  items.forEach((alt, i) => {
    target.insertAdjacentHTML("beforeend", `
      <div class="border rounded-lg shadow mb-3 bg-white dark:bg-gray-800 p-3">
        <h4 class="font-bold text-blue-600 mb-2">Alternatif ${i + 1}: ${alt.nama || "-"}</h4>
        <div class="text-sm">
          <div><b>Severity:</b> ${alt.severity || "-"}</div>
          <div><b>INA-CBG:</b> ${alt.ina_cbg || "-"}</div>
          <div><b>Tarif:</b> ${formatRupiah(alt.tarif)}</div>
          <div><b>Syarat Klinis:</b> ${alt.syarat || "-"}</div>
          <div><b>Evaluasi Faskes:</b> ${alt.faskes || "-"}</div>
          <div><b>Rawat Inap:</b> ${alt.rawat_inap || "-"}</div>
          <div><b>Tindakan Wajib:</b> ${alt.tindakan_wajib || "-"}</div>
        </div>
      </div>
    `);
  });
}

// ==================== Helper ====================
function statusIcon(val) {
  if (!val) return `<span class="text-gray-400">-</span>`;
  if (val.toLowerCase().includes("valid"))
    return `<span class="text-green-600 font-bold">✔️ ${val}</span>`;
  if (val.toLowerCase().includes("tidak"))
    return `<span class="text-red-600 font-bold">❌ ${val}</span>`;
  if (val.toLowerCase().includes("warning") || val.toLowerCase().includes("butuh"))
    return `<span class="text-yellow-600 font-bold">⚠️ ${val}</span>`;
  return val;
}

function formatRupiah(num) {
  if (!num) return "-";
  return "Rp " + Number(num).toLocaleString("id-ID");
}

// Expose ke global


window.addManual = addManual
window.openProcedureModal = openProcedureModal;
window.closeNestedModal = closeNestedModal;
window.generateSummary = generateSummary;
window.renderEvaluasiDiagnosis = renderEvaluasiDiagnosis;
window.renderEvaluasiProcedure = renderEvaluasiProcedure;
window.renderAlternatifKombinasi = renderAlternatifKombinasi;
