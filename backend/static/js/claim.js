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
    currentProcedure: null,

    init() {
      const role = this.role;
      const claimId = document.getElementById("claimRoot")?.dataset.claimId;

      if (role === 'verifikator' && claimId) {
        // 🔹 langsung load dari DB (BE pecahan)
        loadRecommendations(claimId);
        loadSimulations(claimId);
      }
    },

    statusIcon(s) {
      if (!s) return "";
      const val = String(s).trim().toLowerCase();
      console.log("statusIcon input:", s, "→ parsed:", val);

      if (val === "invalid") return "❌";
      if (val === "warning" || val.includes("optional")) return "⚠️";
      if (val === "valid") return "✅";
      return "";
    }
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
    console.log("🔍 Semua tindakan:", (result.data || []).filter(r => r.category === "tindakan"));

    renderAI(result.data || []);   // 👉 lempar ke renderer
  } catch (err) {
    console.error("❌ Error generate AI:", err);
    alert("Gagal generate AI");
  }
}

// 2. pure renderer (kayak kodeku sebelumnya)
function renderAI(rows) {
  console.log("🔍 renderAI rows:", rows);

  // 🔥 injeksi tindakan ke tiap diagnosis sebelum render
  attachTindakan(rows);

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

    // hitung total counter daily (fix: diagnosis + komorbid + komplikasi)
    const dailyCounter = document.getElementById(`count-daily-${dayId}`);
    if (dailyCounter) {
      const totalDaily =
        (parseInt(document.getElementById(`count-diagnosis-${dayId}`)?.textContent || 0)) +
        (parseInt(document.getElementById(`count-komorbid-${dayId}`)?.textContent || 0)) +
        (parseInt(document.getElementById(`count-komplikasi-${dayId}`)?.textContent || 0));
      dailyCounter.textContent = totalDaily;
    }
  });

  // Discharge
  renderTable("diagnosis-discharge", discharge.filter(r => r.category==="diagnosis"), "diagnosis", "discharge");
  renderTable("komorbid-discharge", discharge.filter(r => r.category==="komorbid"), "komorbid", "discharge");
  renderTable("komplikasi-discharge", discharge.filter(r => r.category==="komplikasi"), "komplikasi", "discharge");
}


// 🔑 Definisi attachTindakan (wajib ada)
function attachTindakan(rows) {
  const tindakanAll = rows.filter(r => r.category === "tindakan");
  console.log("🔗 Semua tindakan:", tindakanAll);

  rows.forEach(d => {
    const arr = tindakanAll.filter(t => t.stage === d.stage && t.category === d.category);
    d.tindakan = arr.length ? arr : "-";
  });

}


// ==================== Render Table ====================
function renderTable(targetId, items, type, tab, dayId = null, skipManualRow = false) { 
  const state = Alpine.$data(document.getElementById("claimRoot"))

  if (!state.simulasi[tab]) {
    state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [] }
  }

  // === Filter AI vs Manual ===
  const oldItems = state.simulasi[tab][type] || []
  const oldAiItems = oldItems.filter(it => !it.isManual)
  const manualItems = oldItems.filter(it => it.isManual)

  const newAiItems = (items || []).filter(it => !it.isManual)
  const aiItems = newAiItems.length > 0 ? newAiItems : oldAiItems

  let merged
  if (type === "tindakan") {
    // manual tindakan dihandle terpisah
    merged = [...aiItems]
  } else {
    // selain itu (diagnosis/komorbid/komplikasi) tetap digabung manual
    merged = [...aiItems, ...manualItems]
  }

  // === Hindari duplikat ===
  const seen = new Set()
  merged = merged.filter(it => {
    const key = `${it.id}-${(it.nama_kategori || it.kategori || "").trim()}-${it.icd10_code || it.icd9_code || ""}-${it.tindakan || it.procedure_text || ""}-${it.child ? "child" : "parent"}`
    if (seen.has(key)) return false
    seen.add(key)
    console.log("Dedup key:", key, "→ child?", it.child, it)
    return true
  })



  state.simulasi[tab][type] = merged

  console.log("🟢 renderTable merged:", merged.map(it => ({
    id: it.id,
    kategori: it.kategori || it.nama_kategori,
    icd10: it.icd10_code,
    tindakan: it.tindakan || it.procedure_text,
    score: it.score
  })));

  const target = document.getElementById(targetId)
  if (!target) return
  target.innerHTML = ""

  // === Grouping Parent & Child ===
  let grouped = []
  let parentMap = {}
  let lastParentKey = null;

  merged.forEach(it => {
    const name = (it.nama_kategori || it.kategori || "").trim()
    if (!name) return
    const itemType = it.type || type || "diagnosis"

    if (it.child === true) {
      // === Child ===
      if (lastParentKey && parentMap[lastParentKey]) {
        parentMap[lastParentKey].children.push({
          ...it,
          kategori: `${name} ${String.fromCharCode(97 + parentMap[lastParentKey].children.length)}`,
          nama_kategori: name
        })
      }
    } else {
      // === Parent ===
      const parentKey = `${itemType}:${name}`
      parentMap[parentKey] = { ...it, kategori: name, nama_kategori: name, children: [] }
      grouped.push(parentMap[parentKey])
      lastParentKey = parentKey
    }
  })

  console.log("📌 Grouped parent-child:", grouped.map(g => ({
  parent: g.kategori,
  children: g.children.map(c => c.kategori)
  })));



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
            <span onclick="window.openModalFromAttr && window.openModalFromAttr(this, '${type}')" class="text-blue-600 underline">${parent.kategori || parent.nama_kategori || "-"}</span>
            <span class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">${counter}</span>
          </td>
          <td class="col-klinis border px-6 py-2">
            <div class="w-full max-w-[200px] whitespace-nowrap overflow-hidden text-ellipsis" title="${parent.klinis || ""}">
              ${parent.klinis || "-"}
            </div>
          </td>
          <td class="col-icd border px-[19px] py-2 text-center">${parent.icd10_code || parent.icd9_code || "-"}</td>
          <td class="col-tindakan border px-6 py-2">
            <div class="w-full max-w-[180px] truncate whitespace-nowrap overflow-hidden text-ellipsis" title="${parent.tindakan || parent.procedure_text || "-"}">
              ${parent.tindakan || parent.procedure_text || "-"}
            </div>
          </td>
          <td class="border px-[18px] py-2 text-center">${parent.score || "-"}</td>
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
              onclick="window.openModalFromAttr && window.openModalFromAttr(this, '${type}')">
            → ${child.nama_kategori || child.kategori || "-"}
          </td>
          <td class="col-klinis border px-6 py-2">
            <div class="w-full max-w-[200px] whitespace-nowrap overflow-hidden text-ellipsis" title="${child.klinis || ""}">
              ${child.klinis || "-"}
            </div>
          </td>
          <td class="col-icd border px-[19px] py-2 text-center">${child.icd10_code || child.icd9_code || "-"}</td>
          <td class="col-tindakan border px-6 py-2 whitespace-nowrap overflow-hidden text-ellipsis" title="${child.tindakan || child.procedure_text || "-"}">
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
  if (!skipManualRow && state.role === "doctor") {
    if (tab === "admission" || tab === "discharge" || tab.startsWith("daily-")) {
      const manualTbody = document.createElement("tbody")
      const tabPath = tab.startsWith("daily-") 
        ? `manualInput.daily['${tab}'].${type}`
        : `manualInput.${tab}.${type}`

      manualTbody.insertAdjacentHTML("beforeend", `
        <tr class="manual-row bg-gray-50 dark:bg-gray-800">
          <td class="border px-3 py-2 whitespace-nowrap overflow-hidden text-ellipsis max-w-[180px]">
            <input x-model="${tabPath}.kategori" placeholder="Nama Penyakit" class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600">
          </td>
          <td class="col-klinis border px-6 py-2 whitespace-nowrap overflow-hidden text-ellipsis max-w-[200px]">
            <input x-model="${tabPath}.klinis" placeholder="Klinis" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600">
          </td>
          <td class="col-icd border px-3 py-2">
            <input x-model="${tabPath}.icd10_code" placeholder="ICD-10" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600">
          </td>
          <td class="col-tindakan border px-3 py-2 whitespace-nowrap overflow-hidden text-ellipsis max-w-[180px]">
            <input x-model="${tabPath}.procedure_text" placeholder="Tindakan" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600">
          </td>
          <td class="border px-3 py-2">
            <input x-model="${tabPath}.score" placeholder="Score" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600">
          </td>
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
function renderMappingSelect(item, tab, type) {
  const disabled = window.claimState.role !== 'doctor' ? 'disabled' : ''
  return `
    <select onchange="onMappingChange(event, '${tab}', '${type}', ${item.id})"
            class="border px-2 py-1 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-200 max-w-[120px] truncate"
            ${disabled}>
      <option value="" ${!item.mapping ? "selected" : ""}>Pilih</option>
      <option value="Diagnosis Utama" ${item.mapping==="Diagnosis Utama"?"selected":""}>Diagnosis Utama</option>
      <option value="Komorbid" ${item.mapping==="Komorbid"?"selected":""}>Komorbid</option>
      <option value="Komplikasi" ${item.mapping==="Komplikasi"?"selected":""}>Komplikasi</option>
      <option value="None" ${item.mapping==="None"?"selected":""}>None</option>
    </select>
  `
}



// ==================== Add Manual ====================
function addManual(type, tab) {
  const state = Alpine.$data(document.getElementById('claimRoot'));

  // Daily setup
  if (tab.startsWith("daily-")) ensureDaily(tab);

  // Ambil input
  const input = tab.startsWith("daily-")
    ? state.manualInput.daily[tab][type]
    : state.manualInput[tab][type];

  if (!input) {
    console.warn("❌ manualInput kosong:", tab, type);
    return;
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
  };

  // Pastikan simulasi[tab] ada
  if (!state.simulasi[tab]) {
    state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[] };
  }
  if (!Array.isArray(state.simulasi[tab][type])) {
    state.simulasi[tab][type] = [];
  }

  // Push ke simulasi per-tab
  state.simulasi[tab][type].push(newItem);

  // ✅ Sinkronisasi daily summary
  if (tab.startsWith("daily-")) {
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

  // ✅ Render ulang table tanpa manual row
  renderTable(`${type}-${tab}`, state.simulasi[tab][type], type, tab, null, true);

  // ✅ Reset input
  Object.keys(input).forEach(k => input[k] = "");

  // ✅ Tambah lagi row input manual supaya bisa isi lagi
  renderTable(`${type}-${tab}`, state.simulasi[tab][type], type, tab);
}




function addManualTindakan() {
  const namaEl = document.getElementById("manualNamaTindakan");
  if (!namaEl) return alert("Input manual tindakan tidak ditemukan");

  const nama = namaEl.value.trim();
  if (!nama) {
    alert("Nama tindakan wajib diisi");
    return;
  }

  const state = window.claimState;
  if (!state.manualTindakan) state.manualTindakan = [];

  // cari index lama
  const idx = state.manualTindakan.findIndex(td => td.nama === nama);

  let newTd = {
    nama: nama,
    deskripsi: "-",
    source: "Manual",
    isManual: true
  };
  newTd = normalizeProcedure(newTd);

  if (idx !== -1) {
    // 🔄 replace langsung, jangan push
    state.manualTindakan[idx] = newTd;
  } else {
    state.manualTindakan.push(newTd);
  }

  renderManualTindakanList();
  namaEl.value = "";
}





function renderManualTindakanList() {
  const state = window.claimState;
  const listContainer = document.querySelector(".tindakan-list");
  if (!listContainer) return;

  state.manualTindakan = (state.manualTindakan || []).filter(td => td.nama && td.nama !== "-" && td.nama !== "undefined");

  listContainer.innerHTML = ""; // bersihin dulu

  (state.manualTindakan || []).forEach((td, idx) => {
    listContainer.insertAdjacentHTML("beforeend", `
      <div class="grid grid-cols-3 items-center bg-white dark:bg-gray-800 p-3 rounded shadow mb-2 gap-4">

        <!-- Nama tindakan -->
        <div class="font-semibold text-blue-600 underline cursor-pointer truncate"
            onclick="openManualNestedProcedureModal(${idx})">
          ${td.nama}
        </div>

        <!-- Deskripsi -->
        <div class="px-3 py-1 text-sm font-medium bg-gray-200 dark:bg-gray-700
                    text-gray-900 dark:text-gray-100 rounded shadow-sm truncate"
            title="${(td.deskripsi && td.deskripsi.includes('ICD-9:')) ? td.deskripsi : '-'}">
          ${(td.deskripsi && td.deskripsi.includes("ICD-9:")) ? td.deskripsi : '-'}
        </div>

        <!-- Tombol -->
        ${state.role === "doctor" ? `
          <div class="flex space-x-2 justify-end">
            <button type="button"
                    onclick="updateSimulasi('tindakan','Primary','${td.nama}','Manual', window.claimState.tab)"
                    class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs">Pilih Utama</button>
            <button type="button"
                    onclick="updateSimulasi('tindakan','Secondary','${td.nama}','Manual', window.claimState.tab)"
                    class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-xs">Pilih Sekunder</button>
          </div>
        ` : ''}
      </div>
    `);
  });
}



// ==================== Modal ====================

function openModal(title, content, { hideDefaultClose = false } = {}) {
  const root = document.getElementById('claimRoot')
  const state = Alpine.$data(root)   // 👈 ambil instance Alpine aktif
  console.log("🔥 openModal called, state:", state)
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
      const text = dx.tindakan.map(t => t.procedure_text || t.tindakan).join(", ");
      tindakanCell.innerHTML = `<span title="${text}">${truncateText(text, 20)}</span>`;
    } else {
      tindakanCell.innerText = "-";
    }
  }
}


async function openModalFromAttr(el, type) {
  console.log("🔥 openModalFromAttr terpanggil", el, type);
  const tr = el.closest("tr");
  const dbId = tr?.dataset.dbId;
  const uiId = tr?.dataset.id;
  const claimId = document.getElementById("claimRoot")?.dataset.claimId;

  try {
    let dx;
    // 🔹 ambil data dari database
    if (dbId && !isNaN(Number(dbId))) {
      const url = `/ai/recommendation/detail?claim_id=${claimId}&rec_type=${type}&item_id=${dbId}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const result = await res.json();
      dx = result.data;
      console.log("🔎 Detail DX dari BE:", dx);
      console.log("🔎 Tindakan di DX:", dx?.tindakan);

    } else {
      dx = tr?.dataset.row ? JSON.parse(tr.dataset.row) : {};
    }

    // 🔹 tampilkan modal dummy (jika tidak ada data di database)
    if ((!dbId || isNaN(Number(dbId))) && tr?.dataset.row) {
      dx = JSON.parse(tr.dataset.row);

      // simpan judul diagnosis manual
      window.claimState.currentDiagnosis = dx;
      window.claimState.currentDiagnosisTitle = dx.kategori || dx.name || "-";

      openModal(`Detail Diagnosis (${window.claimState.currentDiagnosisTitle})`, buildModalContent(dx));
      return;
    }
    

    // 🔹 tampilkan modal (selalu pakai format "Detail Diagnosis (nama penyakit)")
    let rawText = tr?.querySelector("td")?.innerText.trim() || "-";
    // buang segitiga dan angka di ujung
    rawText = rawText.replace(/^▶|^▼/, "").trim(); // hapus ikon di awal
    rawText = rawText.replace(/\s+\d+$/, "");
    const namaPenyakit =
    dx?.kategori ||
    dx?.nama_kategori ||
    dx?.diagnosis ||
    dx?.komorbid ||
    dx?.komplikasi ||
    rawText ||
    "-";
    openModal(`Detail Diagnosis (${namaPenyakit})`, buildModalContent(dx));
    // set current diagnosis dulu
    window.claimState.currentDiagnosis = dx;
    window.claimState.currentDiagnosisTitle = namaPenyakit;


    // update ringkasan tabel
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
  window.claimState.currentProcedure = dummy

  // update ringkasan biar kolom Klinis / ICD / Tindakan juga keisi
  updateRingkasanFromRow(dummy)
}


function buildModalContent(it) {
  console.log("🔍 Passing ke renderDiagnosisDetail:", it);

  let content = renderDiagnosisDetail(it);

  // slot untuk list manual, terpisah dari tindakan AI/DB
  content += `
    <div class="tindakan-list mt-4"></div>
  `;

  // render manual setelah modal terbuka
  setTimeout(() => {
    renderManualTindakanList();
  }, 0);

  return content;
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

  const icd10 = it.icd10 || { 
    kode_icd: it.icd10_code || "-",
    struktur_icd10: it.struktur_icd10 || "-",
    kode_ganda: it.kode_ganda || "-",
    z_code: it.z_code || "-",
    kode_bpjs_khusus: it.kode_bpjs_khusus || "-"
  };
  const tindakan = it.tindakan || [];
  const rawat = {
    indikasi: it.rawat_inap?.indikasi || "-",
    lama_rawat: it.rawat_inap?.lama_rawat || "-",
    perpanjangan: it.rawat_inap?.perpanjangan || "-"
  };

  const faskes = {
    kesesuaian_rs: it.faskes?.kesesuaian_rs || "-"
  };

  const rujukan = {
    syarat: it.rujukan?.syarat || "-",
    kelayakan: it.rujukan?.kelayakan || "-"
  };

  // helper box 2 kolom
  const renderBox = (label, value, status = "default", diagnosisId = null) => {
    let colorClass = "bg-gray-200 text-gray-800"; // default abu
    if (status === "valid") colorClass = "bg-green-600 text-white";
    if (status === "invalid") colorClass = "bg-red-600 text-white";
    const safeValue = value || "-";

    // kalau ada diagnosisId → aktifkan tooltip + klik regulasi
    const content = diagnosisId
    ? `<span 
        class="cursor-pointer"
        title="PNPK Sepsis 2020"
        onclick="openRegulationModal(${diagnosisId}, 'diagnosis')"
      >${safeValue}</span>`
    : safeValue;


    return `
      <div class="grid grid-cols-2">
        <div class="bg-gray-700 text-white px-3 py-2">${label}</div>
        <div class="${colorClass} px-3 py-2">${content}</div>
      </div>
    `;
  };


  return `
    <div class="space-y-6 text-sm">

      <!-- KLINIS -->
      <section class="rounded shadow overflow-hidden">
        <div class="bg-blue-600 text-white px-3 py-2 font-bold">KLINIS</div>
        <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
          ${renderBox("Justifikasi", klinis.justifikasi, klinis.status, it.id)}
          ${renderBox("Bukti Klinis", klinis.bukti_klinis)}
          ${renderBox("Syarat Klinis", klinis.syarat_klinis, klinis.status, it.id)}
          
        </div>
      </section>

      <!-- ICD-10 -->
      <section class="rounded shadow overflow-hidden">
        <div class="bg-blue-600 text-white px-3 py-2 font-bold">ICD-10</div>
        <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
          ${renderBox("Kode ICD", icd10.kode_icd, icd10.status_icd, it.id)}
          ${renderBox("Struktur ICD 10", icd10.struktur_icd10, icd10.status_icd, it.id)}
          ${renderBox("Kode Ganda", icd10.kode_ganda, icd10.status_icd, it.id)}
          ${renderBox("Z-Code", icd10.z_code, icd10.status_icd, it.id)}
          ${renderBox("Kode Khusus BPJS", icd10.kode_bpjs_khusus, icd10.status_icd, it.id)}
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
          ${renderBox("Indikasi", rawat.indikasi, rawat.status_indikasi, it.id)}
          ${renderBox("Lama Rawat", rawat.lama_rawat, rawat.status_lama, it.id)}
          ${renderBox("Perpanjangan", rawat.perpanjangan, rawat.status_perpanjangan, it.id)}
        </div>
      </section>

      <!-- FASKES -->
      <section class="rounded shadow overflow-hidden">
        <div class="bg-blue-600 text-white px-3 py-2 font-bold">FASKES</div>
        <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
          ${renderBox("Kesesuaian RS", faskes.kesesuaian_rs, faskes.status, it.id)}
        </div>
      </section>

      <!-- RUJUKAN -->
      <section class="rounded shadow overflow-hidden">
        <div class="bg-blue-600 text-white px-3 py-2 font-bold">RUJUKAN</div>
        <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
          ${renderBox("Syarat", rujukan.syarat, rujukan.status_syarat, it.id)}
          ${renderBox("Kelayakan", rujukan.kelayakan, rujukan.status_kelayakan, it.id)}
        </div>
      </section>

    </div>
  `;
}


function renderTindakan(list) {
  console.log("🛠 renderTindakan list:", list);

  const tindakanList = list && list.length > 0 
    ? list.map(td => {
        // fallback: BE bisa kirim nama/tindakan, description/deskripsi
        const nama = td.nama || td.tindakan || "-";
        const deskripsi = td.deskripsi || td.description || "-";
        const procId = td.id || td.procedure_id || "";

        return `
          <div class="grid grid-cols-3 gap-4 items-center bg-white dark:bg-gray-800 p-3 rounded shadow mb-2"
              data-procid="${procId}">
            
            <!-- Nama Tindakan -->
            <div class="font-semibold text-blue-600 underline cursor-pointer truncate"
                onclick="openProcedureModal('${procId}')">
              ${nama}
            </div>

            <!-- Deskripsi -->
            <div>
              <span class="block px-3 py-1 text-sm font-medium bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded shadow-sm whitespace-nowrap overflow-hidden text-ellipsis"
                title="${deskripsi}">
                ${deskripsi}
              </span>
            </div>

            <!-- Tombol -->
            ${window.claimState.role === "doctor" ? `
              <div class="flex space-x-2 justify-end">
                <button type="button"
                        onclick="updateSimulasi('tindakan','Primary','${nama}','Manual', window.claimState.tab)"
                        class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs">Pilih Utama</button>
                <button type="button"
                        onclick="updateSimulasi('tindakan','Secondary','${nama}','Manual', window.claimState.tab)"
                        class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-xs">Pilih Sekunder</button>
              </div>
            ` : ''}
          </div>
        `;
      }).join("")
    : `<div class="italic text-gray-500">Tidak ada tindakan AI</div>`;
  
  // form manual tetap sama
  const manualForm = `
  ${window.claimState.role === "doctor" ? `
    <div class="tindakan-list mt-4"></div>
    <div class="mt-4 p-3 border rounded bg-gray-50 dark:bg-gray-700">
      <div class="font-semibold mb-2">Tambah Tindakan Manual</div>
      <div class="flex gap-2">
        <input id="manualNamaTindakan" placeholder="Nama Tindakan" 
              class="flex-1 px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600" />
        <button type="button" onclick="addManualTindakan()" 
                class="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded flex items-center">
          ➕ Tambah
        </button>
      </div>
    </div>
  ` : ''}`
  
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

    // 🔹 helper mirip renderBox
    const renderProcBox = (label, value, skipReg = false) => {
      const safeValue = value || "-";
      const content = (!skipReg)
        ? `<span class="cursor-pointer" title="PNPK Sepsis 2020"
                 onclick="openRegulationModal(${procId}, 'procedure')">${safeValue}</span>`
        : safeValue;

      return `
        <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>${label}:</b></div>
        <div class="bg-gray-800 px-3 py-2 rounded">${content}</div>
      `;
    };

    // tampilkan nested modal
    const content = `
      <div class="flex justify-end items-start mb-3">
        <button type="button"
                onclick="closeNestedModal()"
                class="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded">
          ✕
        </button>
      </div>
      <div class="grid grid-cols-2 gap-2">
        ${renderProcBox("Kode ICD-9", d.icd9)}
        ${renderProcBox("Deskripsi", deskripsiGabungan)}
        ${renderProcBox("Validitas", d.validitas, true)}   <!-- ❌ regulasi skip -->
        ${renderProcBox("Status", d.status)}
        ${renderProcBox("INA-CBG", d.ina_cbg)}
        ${renderProcBox("Faskes", d.faskes)}
        ${renderProcBox("Rawat Inap", d.rawat_inap)}
        ${renderProcBox("Syarat Klinis", d.syarat_klinis)}
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
  let td = normalizeProcedure(window.claimState.manualTindakan[idx] || {});

  const content = `
    <div class="flex justify-end items-start mb-3">
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

  const titleNama = td?.nama || td?.procedure_text || "Manual";
  openModal(`Detail Tindakan (${titleNama} - Manual)`, content);
  window.claimState.currentProcedure = td;
}

function closeNestedModal() {
  const dx = window.claimState.currentDiagnosis;
  if (dx) {
    const nama = window.claimState.currentDiagnosisTitle 
          || dx?.kategori 
          || "-";
    openModal(`Detail Diagnosis (${nama})`, buildModalContent(dx));

  } else {
    const state = Alpine.$data(document.getElementById('claimRoot'));
    state.modalOpen = false;
  }
}

async function openRegulationModal(id, type = "diagnosis") {
  const claimId = document.getElementById("claimRoot")?.dataset.claimId;

  // bedakan param di URL
  const paramKey = type === "procedure" ? "procedure_id" : "diagnosis_id";
  const url = `/claims/${claimId}/regulations?${paramKey}=${id}`;

  try {
    const res = await fetch(url);
    const { data } = await res.json();

    if (!data || data.length === 0) {
      alert("Tidak ada regulasi untuk field ini");
      return;
    }

    const r = data[0]; // ambil 1 dulu
    const content = `
      <div class="space-y-4 text-sm">
        <div class="grid grid-cols-2 gap-2 p-3 bg-gray-100 dark:bg-gray-700 rounded">
          <div class="bg-gray-700 text-white px-3 py-2">Judul Regulasi</div>
          <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2">${r.judul_regulasi || '-'}</div>

          <div class="bg-gray-700 text-white px-3 py-2">Dasar Hukum</div>
          <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2">${r.dasar_hukum || '-'}</div>

          <div class="bg-gray-700 text-white px-3 py-2">Bab/Pasal</div>
          <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2">${r.bab_pasal || '-'}</div>

          <div class="bg-gray-700 text-white px-3 py-2">Isi</div>
          <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2">${r.isi || '-'}</div>
        </div>
      </div>
    `;
    openModal("Detail Regulasi", content);
  } catch (e) {
    console.error("❌ Gagal load regulasi", e);
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

  const item = typeof value === "string"
  ? { name: value.split(" [")[0] || "", label: "", source: "Manual", isManual: true, id: null }
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

  // Diagnosis, Komorbid, Komplikasi
  if (type === "diagnosis" || type === "komorbid" || type === "komplikasi") {
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
  const nama = typeof value === "string" 
    ? value 
    : (value.name || value.label || "(tanpa nama)");
  const id = typeof value === "string" ? null : (value.id || null);
   // ambil ID kalau ada

  if (type === "tindakan") {
    if (finalOpt === "Primary") {
      const oldPrimary = sim.tindakanUtama;
      sim.tindakanSekunder = sim.tindakanSekunder.filter(td => td.name !== nama);
      sim.tindakanUtama = { tindakan_utama_id: id, name: nama };   // ⬅️ inject ID
      if (oldPrimary && oldPrimary.name !== nama) sim.tindakanSekunder.unshift(oldPrimary);
    } else if (finalOpt === "Secondary") {
      if (sim.tindakanUtama?.name === nama) sim.tindakanUtama = null;
      if (!sim.tindakanSekunder.find(td => td.name === nama)) {
        sim.tindakanSekunder.push({ tindakan_sekunder_id: id, name: nama });  // ⬅️ inject ID
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

    // rebuild summary harian
    state.simulasi.daily.summary = state.simulasi.daily.days.map((d, i) => {
      if (!d) return null;
      return {
        dayIndex: i,
        utama: d.utama || null,
        sekunder: Array.isArray(d.sekunder) ? d.sekunder : []
      };
    }).filter(Boolean);
  }

  syncHiddenInputs();
  console.log("🟢 Simulasi updated:", state.simulasi);
}


function normalizeProcedure(td) {
  if (!td) return { nama: "-" };
  return {
    ...td,
    nama: td.nama || td.name || td.procedure_text || td.kategori || "-"
  };
}


// ==================== Helpers ====================

function confidenceBadge(val){
  val=parseInt(val)
  let c=val>=80?'bg-green-600':val>=60?'bg-yellow-500':'bg-red-600'
  return `<span class="px-2 py-0.5 rounded text-white text-xs ${c}">${val}%</span>`
}

async function loadRecommendations(claimId) {
  try {
    const res = await fetch(`/claims/${claimId}/recommendations`);
    if (!res.ok) {
      return console.error("❌ Gagal load rekomendasi dari DB");
    }
    const body = await res.json();
    const recs = body.data || [];
    console.log("📥 Data rekomendasi dari DB:", recs);

    // Grouping per stage & category
    const grouped = { admission: {}, discharge: {}, daily: {} };

    recs.forEach(r => {
      const stage = r.stage || "admission";   // fallback kalau kosong
      const cat = r.category || "unknown";

      if (stage === "admission") {
        grouped.admission[cat] = grouped.admission[cat] || [];
        grouped.admission[cat].push(r);
      } 
      else if (stage === "discharge") {
        grouped.discharge[cat] = grouped.discharge[cat] || [];
        grouped.discharge[cat].push(r);
      } 
      else if (stage.startsWith("daily")) {
        if (!["diagnosis","komorbid","komplikasi"].includes(cat)) return; // skip category aneh
        grouped.daily[stage] = grouped.daily[stage] || { diagnosis: [], komorbid: [], komplikasi: [] };
        grouped.daily[stage][cat].push(r);
      }
    });

    // 🔍 Debug setelah grouping
    console.log("🟢 Grouped Admission:", grouped.admission);
    console.log("🟢 Grouped Discharge:", grouped.discharge);
    console.log("🟢 Grouped Daily:", grouped.daily);

    // === Admission ===
    renderTable(
      "diagnosis-admission",
      (grouped.admission.diagnosis || []).map(mapRecommendation),
      "diagnosis",
      "admission"
    );
    renderTable(
      "komorbid-admission",
      (grouped.admission.komorbid || []).map(mapRecommendation),
      "komorbid",
      "admission"
    );
    renderTable(
      "komplikasi-admission",
      (grouped.admission.komplikasi || []).map(mapRecommendation),
      "komplikasi",
      "admission"
    );

    // === Daily ===
    const dailyContainer = document.getElementById("daily-accordion");
    dailyContainer.innerHTML = "";

    Object.keys(grouped.daily).forEach((stage, idx) => {
      const hari = grouped.daily[stage];
      hari.tanggal = hari.tanggal || `2025-09-${String(idx + 1).padStart(2, "0")}`;
      const dayId = `daily-${idx}`;

      dailyContainer.insertAdjacentHTML(
        "beforeend",
        `
        <div class="bg-white dark:bg-gray-700 rounded shadow-sm" x-data="{open:false}">
          <button type="button" @click="open=!open"
                  class="w-full flex justify-between px-4 py-2 bg-gray-200 dark:bg-gray-600 font-semibold">
            <span>Hari ${idx + 1} (${hari.tanggal || '-'})</span>
            <span x-show="open">⬆️</span><span x-show="!open">⬇️</span>
          </button>
          <div x-show="open" class="p-2 space-y-2">
            <div><table class="w-full text-xs border table-fixed"><tbody id="diagnosis-${dayId}"></tbody></table></div>
            <div><table class="w-full text-xs border table-fixed"><tbody id="komorbid-${dayId}"></tbody></table></div>
            <div><table class="w-full text-xs border table-fixed"><tbody id="komplikasi-${dayId}"></tbody></table></div>
          </div>
        </div>
      `
      );

      renderTable(`diagnosis-${dayId}`, (hari.diagnosis || []).map(mapRecommendation), "diagnosis", dayId);
      renderTable(`komorbid-${dayId}`, (hari.komorbid || []).map(mapRecommendation), "komorbid", dayId);
      renderTable(`komplikasi-${dayId}`, (hari.komplikasi || []).map(mapRecommendation), "komplikasi", dayId);
    });

    // === Discharge ===
    renderTable(
      "diagnosis-discharge",
      (grouped.discharge.diagnosis || []).map(mapRecommendation),
      "diagnosis",
      "discharge"
    );
    renderTable(
      "komorbid-discharge",
      (grouped.discharge.komorbid || []).map(mapRecommendation),
      "komorbid",
      "discharge"
    );
    renderTable(
      "komplikasi-discharge",
      (grouped.discharge.komplikasi || []).map(mapRecommendation),
      "komplikasi",
      "discharge"
    );

  } catch (err) {
    console.error("❌ Error loadRecommendations:", err);
  }
}


async function loadSimulations(claimId) {
  const res = await fetch(`/claims/${claimId}/simulations`)
  if (!res.ok) return
  const body = await res.json()
  const sims = body.data || []
  console.log("📥 Simulasi dari DB:", sims)

  sims.forEach(s => {
    // Diagnosis utama
    if (s.diagnosis_utama_id) {
      setTimeout(() => {
        updateSimulasi("diagnosis", "Primary", { 
          id: s.diagnosis_utama_id, 
          name: s.diagnosis_utama_name || "(tanpa nama)",  // ⬅️ fallback
          mapping: "Primary"
        }, true, s.stage)
      }, 0)
    }

    // Diagnosis sekunder
    if (s.diagnosis_sekunder_id) {
      setTimeout(() => {
        updateSimulasi("diagnosis", "Secondary-Komorbid", { 
          id: s.diagnosis_sekunder_id, 
          name: s.diagnosis_sekunder_name || "(tanpa nama)", // ⬅️ fallback
          mapping: "Secondary-Komorbid"
        }, true, s.stage)
      }, 0)
    }

    // Tindakan utama
    if (s.tindakan_utama_id) {
      setTimeout(() => {
        updateSimulasi("tindakan", "Primary", { 
          id: s.tindakan_utama_id, 
          name: s.tindakan_utama_name || "(tanpa nama)", // ⬅️ fallback
          mapping: "Primary"
        }, true, s.stage)
      }, 0)
    }

    // Tindakan sekunder
    if (s.tindakan_sekunder_id) {
      setTimeout(() => {
        updateSimulasi("tindakan", "Secondary", { 
          id: s.tindakan_sekunder_id, 
          name: s.tindakan_sekunder_name,   // ⬅ langsung pakai string
          mapping: "Secondary"
        }, true, s.stage)
      }, 0)
    }
  })
}




function mapRecommendation(r) {
  const mapped = {
    id: r.id,
    kategori: r.diagnosis_text ?? r.nama_kategori ?? r.kategori ?? r.category ?? r.nama ?? "-",
    nama_kategori: r.diagnosis_text ?? r.nama_kategori ?? r.kategori ?? r.category ?? r.nama ?? "-",
    klinis: r.klinis ?? r.justifikasi ?? "-",
    icd10_code: r.icd10_code ?? r.icd ?? "-",
    procedure_text: r.tindakan ?? r.procedure_text ?? "-",
    score: r.confidence_score || r.score || 0,
    child: r.child === true,
    isManual: r.is_manual ?? false,
  };

  console.log("📥 Mapped recommendation:", mapped);

  return mapped;
}



function onMappingChange(event, tab, type, itemId) {
  const state = Alpine.$data(document.getElementById('claimRoot'))
  const arr = state.simulasi?.[tab]?.[type] || []
  const item = arr.find(it => it.id == itemId)

  if (!item) {
    console.warn("❌ onMappingChange: item not found", { tab, type, itemId })
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

    const summaryField = document.getElementById("summaryField");
    if (summaryField) {
      summaryField.value = JSON.stringify(data); // ⬅️ dari AI BE
    }
    window.claimState.summary = data; // sync juga ke state global

    alert("✅ Summary berhasil digenerate");
  } catch (err) {
    console.error("Error generate summary:", err);
    alert("❌ Gagal generate summary");
  }
  syncHiddenInputs();
}

// ==================== Panel Evaluasi Diagnosis ====================
function renderEvaluasiDiagnosis(data) {
  const target = document.getElementById("evaluasi-diagnosis");
  if (!target) return;
  target.innerHTML = "";

  if (!data || Object.keys(data).length === 0) {
    target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada evaluasi diagnosis</div>`;
    return;
  }

  // pakai detail (misal: "Sepsis + DM valid (komorbid umum)")
  const validitasIcon = statusIcon(data.validitas);
  const validitasText = data.validitas_detail || "-";

  target.innerHTML = `
    <h3 class="font-bold text-lg mb-2 text-yellow-500">Evaluasi Kombinasi Diagnosis</h3>
    <table class="w-full border border-gray-300 dark:border-gray-600 text-sm">
      <tr>
        <th class="border px-4 py-2">Validitas Klinis Kombinasi</th>
        <td class="border px-4 py-2">
          ${validitasIcon} - ${validitasText}
        </td>
      </tr>
      <tr>
        <th class="border px-4 py-2">Severity</th>
        <td class="border px-4 py-2">📊 ${data.severity || "-"}</td>
      </tr>
      <tr>
        <th class="border px-4 py-2">Kode INA-CBG</th>
        <td class="border px-4 py-2">${data.kode_ina_cbg || "-"}</td>
      </tr>
      <tr>
        <th class="border px-4 py-2">Estimasi Tarif</th>
        <td class="border px-4 py-2">${formatRupiah(data.estimasi_tarif) || "-"}</td>
      </tr>
      <tr>
        <th class="border px-4 py-2">Syarat Klinis (Kombinasi)</th>
        <td class="border px-4 py-2">${data.syarat || "-"}</td>
      </tr>
      <tr>
        <th class="border px-4 py-2">Evaluasi Faskes</th>
        <td class="border px-4 py-2">${data.evaluasi_faskes || "-"}</td>
      </tr>
      <tr>
        <th class="border px-4 py-2">Rawat Inap</th>
        <td class="border px-4 py-2">${data.rawat_inap || "-"}</td>
      </tr>
    </table>
  `;
}

// ==================== Panel Evaluasi Tindakan ====================
function renderEvaluasiProcedure(rows) {
  const target = document.getElementById("evaluasi-procedure");
  if (!target) return;
  target.innerHTML = "";

  if (!rows || rows.length === 0) {
    target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada evaluasi tindakan</div>`;
    return;
  }

  const wajib = [];
  const validasi = [];
  const dampak = [];
  const konflik = [];

  rows.forEach(p => {
    const icon = statusIcon(p.validitas); // ✅ pakai validitas utk icon
    const tindakan = p.tindakan || p.validitas_detail || p.status_tindakan || "-";

    // Wajib
    if (p.status_tindakan && ["wajib","mandatory"].includes(p.status_tindakan.toLowerCase())) {
      wajib.push(`${icon} - ${tindakan}`);
    }

    // Validasi Verifikator
    if (p.status_tindakan && !["wajib","mandatory"].includes(p.status_tindakan.toLowerCase())) {
      validasi.push(`${icon} - ${tindakan}`);
    }

    // Dampak tarif
    if (p.tarif_impact && p.tarif_impact !== "-") {
      dampak.push(`${icon} ${tindakan} → ${p.tarif_impact}`);
    }

    // Konflik
    if (p.syarat_klinis && p.syarat_klinis !== "-") {
      konflik.push(`${icon} - ${p.syarat_klinis}`);
    }
  });

  const listify = (arr) => arr.length ? arr.map(v=>`<div>${v}</div>`).join("") : "-";

  target.innerHTML = `
    <h3 class="font-bold text-lg mb-2 text-yellow-500">Evaluasi Kombinasi Tindakan</h3>
    <table class="w-full border border-gray-300 dark:border-gray-600 text-sm">
      <tr>
        <th class="border px-4 py-2">Tindakan Wajib Kombinasi</th>
        <td class="border px-4 py-2">${listify(wajib)}</td>
      </tr>
      <tr>
        <th class="border px-4 py-2">Validasi Pilihan Verifikator</th>
        <td class="border px-4 py-2">${listify(validasi)}</td>
      </tr>
      <tr>
        <th class="border px-4 py-2">Dampak INA-CBG / Tarif</th>
        <td class="border px-4 py-2">${listify(dampak)}</td>
      </tr>
      <tr>
        <th class="border px-4 py-2">Konflik / Duplikasi</th>
        <td class="border px-4 py-2">${listify(konflik)}</td>
      </tr>
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

  // 🔹 Tambahin judul dengan counter
  target.insertAdjacentHTML("beforeend", `
    <h3 class="font-bold text-lg mb-2 text-yellow-500">
      Alternatif Kombinasi (${items.length})
    </h3>
  `);

  items.forEach((alt, i) => {
    target.insertAdjacentHTML("beforeend", `
      <div class="border rounded-lg shadow mb-3 bg-white dark:bg-gray-800 p-3">
        <h4 class="font-bold text-blue-600 mb-2">Alternatif ${i + 1}: ${statusIcon(alt.nama) || "-"}</h4>
        <div class="text-sm">
          <div><b>Severity:</b>${alt.severity_detail || "-"} </div></div>
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
function syncHiddenInputs() {
  const simInput = document.getElementById("simulasiField");
  const summInput = document.getElementById("summaryField");

  if (simInput) {
    simInput.value = JSON.stringify(window.claimState.simulasi || {});
  }
  if (summInput) {
    summInput.value = JSON.stringify(window.claimState.summary || {});
  }
}


window.addManual = addManual
window.openModalFromAttr = openModalFromAttr;
window.openProcedureModal = openProcedureModal;
window.closeNestedModal = closeNestedModal;
window.generateSummary = generateSummary;
window.renderEvaluasiDiagnosis = renderEvaluasiDiagnosis;
window.renderEvaluasiProcedure = renderEvaluasiProcedure;
window.renderAlternatifKombinasi = renderAlternatifKombinasi;
document.querySelector("#claimForm")
  .addEventListener("submit", syncHiddenInputs);
