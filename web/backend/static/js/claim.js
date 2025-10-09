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

    // 🔹 Notes untuk diagnosis dan procedure
    notes: {
      primary_diagnosis: [],
      secondary_diagnosis: [],
      primary_procedure: [],
      secondary_procedure: []
    },

    openNoteModal(title, noteType) {
      const noteList = this.notes[noteType] || [];
      const content = `
        <div class="space-y-2">
          <h3 class="font-bold">${title}</h3>
          ${noteList.length > 0 
            ? noteList.map((note, idx) => `
                <div class="p-2 bg-gray-100 dark:bg-gray-700 rounded">
                  <div class="text-xs text-gray-500 mb-1">#${idx + 1}</div>
                  <div class="font-mono text-sm">${note}</div>
                </div>
              `).join('')
            : '<p class="text-gray-500 italic">Tidak ada catatan</p>'
          }
        </div>
      `;
      this.modalTitle = title;
      this.modalContent = content;
      this.modalOpen = true;
    },

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
      async saveSimulasiDraft() {
        const claimId = document.getElementById("claimRoot")?.dataset.claimId;
        if (!claimId) {
          alert("❌ Claim ID tidak ditemukan.");
          return;
        }
        
        const state = this;
        try {
          console.log("🔄 Saving simulasi draft via window.saveDraft...");
          
          // Use saveDraft from claim.api.js which calls /update-draft with CSRF
          if (typeof window.saveDraft === 'function') {
            // Sync hidden fields before saving
            if (typeof window.syncHiddenInputs === 'function') {
              window.syncHiddenInputs();
            }
            
            // Call the proper saveDraft function from claim.api.js
            await window.saveDraft(claimId);
            alert("✅ Draft simulasi berhasil disimpan!");
            
          } else {
            console.error("❌ window.saveDraft function not available");
            alert("❌ Save draft function tidak tersedia");
          }
        } catch (err) {
          console.error("❌ Error save simulasi draft:", err);
          alert("❌ Gagal simpan draft: " + err.message);
        }
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
    // PATCH: Use new endpoint and granular payload
    const state = Alpine.$data(document.getElementById("claimRoot"));
    const stage = state.tab || "admission";
    const res = await fetch("/generate_ai/predict_ddx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ claim_id: claimId, stage })
    });
  const result = await res.json();
  console.log("📥 Data pecahan dari BE:", result);
  // Patch: render each category separately
  if (result.diagnosis) renderAI(result.diagnosis, "diagnosis", stage);
  if (result.komorbid) renderAI(result.komorbid, "komorbid", stage);
  if (result.komplikasi) renderAI(result.komplikasi, "komplikasi", stage);
  } catch (err) {
    console.error("❌ Error generate AI:", err);
    alert("Gagal generate AI");
  }
}

// 2. pure renderer (kayak kodeku sebelumnya)
function renderAI(rows, type, tab) {
  // rows: array of diagnosis/komorbid/komplikasi
  // type: "diagnosis" | "komorbid" | "komplikasi"
  // tab: "admission" | "daily" | "discharge"
  if (!Array.isArray(rows)) return;
  // Map AI result to expected table row format
  const mappedRows = rows.map(item => ({
    kategori: item.parent || "-",
    klinis: "-", // parent klinis always strip
    icd10_code: item.icd10_code || item.icd || "-",
    icd9_code: item.icd9_code || "-",
    procedure_text: item.tindakan || item.procedure_text || "-",
    score: item.confidence || "-",
    mapping: "", // Fill if needed
    children: (item.children && Array.isArray(item.children)) ? item.children.map(child => ({
      kategori: `→ ${child.name || '-'}`,
      klinis: '-', // always strip for child
      icd10_code: child.icd10_code || child.icd || '-',
      icd9_code: child.icd9_code || '-',
      procedure_text: child.tindakan || child.procedure_text || '-',
      score: child.confidence || '-',
      mapping: ""
    })) : []
  }));
  // Admission
  if (tab === "admission") {
    renderTable(`${type}-admission`, mappedRows, type, tab);
  }
  // Discharge
  if (tab === "discharge") {
    renderTable(`${type}-discharge`, mappedRows, type, tab);
  }
  // Daily (future: handle daily tabs)
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

    // Define grouped for counter calculation
    const grouped = merged;
    state.simulasi[tab][type] = merged;

  const target = document.getElementById(targetId)
  if (!target) {
    console.warn("⚠️ Target tbody tidak ditemukan:", targetId)
    return
  }
  target.innerHTML = ""

  // === Header Table ===
  const table = target.closest("table")
  if (table) {
    table.classList.add("table-fixed")
    if (!table.querySelector("thead")) {
      const thead = document.createElement("thead")
      thead.className = "bg-gray-100 dark:bg-gray-800"
      thead.innerHTML = `
        <tr>
          <th class="border px-4 py-2 w-40">Kategori</th>
          <th class="border px-4 py-2 w-40">Klinis</th>
          <th class="border px-4 py-2 w-24 text-center">ICD</th>
          <th class="border px-4 py-2 w-40">Tindakan</th>
          <th class="border px-4 py-2 w-20 text-center">Score</th>
          ${state.role === "doctor" ? `<th class="border px-4 py-2 w-32 text-center">Mapping</th>` : ``}
        </tr>`
      table.insertBefore(thead, table.firstChild)
    }
  }

  // === Render Parent & Child ===
  (items || []).forEach((parent, idx) => {
    const counter = 1 + (parent.children ? parent.children.length : 0)
  const tbody = document.createElement("tbody")
  tbody.setAttribute("x-data", "{ open:false }")
  // Debug: log tipe dan value tbody
  console.log("[DEBUG] tbody type:", typeof tbody, "constructor:", tbody.constructor.name, tbody)
    // parent row
    tbody.innerHTML += `
      <tr class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 font-medium text-sm"
          data-id="${dayId || tab}-${type}-${idx}" data-db-id="${parent.id}">
          <td class="border px-4 py-2 w-40">
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
          <td class="border px-4 py-2 w-40">${parent.klinis || "-"}</td>
          <td class="border px-4 py-2 w-24 text-center">${parent.icd10_code || parent.icd9_code || "-"}</td>
          <td class="border px-4 py-2 w-40">${parent.tindakan || parent.procedure_text || "-"}</td>
          <td class="border px-4 py-2 w-20 text-center">${parent.score || "-"}</td>
          ${state.role === "doctor" ? `
          <td class="border px-4 py-2 w-32 text-center">
            ${renderMappingSelect(parent, tab, type, idx)}
          </td>` : ``}
        </tr>
    `;
    // child rows ikut scope open
    (parent.children || []).forEach((child, cIdx) => {
      tbody.innerHTML += `
        <tr x-show="open" x-cloak
            class="bg-gray-50 dark:bg-gray-800 italic text-sm"
            data-id="child-${dayId || tab}-${type}-${idx}-${cIdx}"
            data-db-id="${child.id}">
          <td class="border px-4 py-2 w-40 cursor-pointer"
              onclick="openModalFromAttr(this, '${type}')">
            → → ${child.kategori || "-"}
          </td>
          <td class="border px-4 py-2 w-40">-</td>
          <td class="border px-4 py-2 w-24 text-center">${child.icd10_code || child.icd9_code || "-"}</td>
          <td class="border px-4 py-2 w-40">${child.tindakan || child.procedure_text || "-"}</td>
          <td class="border px-4 py-2 w-20 text-center">${child.score || "-"}</td>
          ${state.role === "doctor" ? `
          <td class="border px-4 py-2 w-32 text-center">
            ${renderMappingSelect(child, tab, type, idx)}
          </td>` : ``}
        </tr>
      `;
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

  // 🔥 FIXED: Use core_engine endpoint instead of dummy
  fetch(`/claims/${state.claimId}/analyze_diagnosis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      claim_id: state.claimId,
      disease_name: newItem.nama_kategori || newItem.kategori || "Unknown",
      item_id: newItem.id
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
  // Ambil nama penyakit dari cell yang diklik
  let diseaseName = "";
  // Cek parent/child: ambil dari cell yang diklik
  if (el.textContent) {
    diseaseName = el.textContent.replace(/^→+\s*/, "").trim();
  } else {
    diseaseName = tr?.querySelector(".kategori-cell")?.textContent?.trim() || tr?.dataset.nama || "";
  }

  try {
    let dx = {};
    // Patch: jika type diagnosis/komorbid/komplikasi, POST ke /analyze_diagnosis
    if (["diagnosis","komorbid","komplikasi"].includes(type) && claimId && diseaseName) {
      // Debug log
      console.log("[REQ] POST /analyze_diagnosis", { claim_id: claimId, disease_name: diseaseName });
      const res = await fetch("/analyze_diagnosis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim_id: claimId, disease_name: diseaseName })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const result = await res.json();
      console.log("[RESP] /analyze_diagnosis", result);
      // Gunakan langsung response JSON untuk modal
      dx = result;
    } else if (dbId && !isNaN(Number(dbId))) {
      // 🔥 FIXED: Use core_engine endpoint instead of dummy
      const url = type === "diagnosis" ? 
        `/claims/${claimId}/analyze_diagnosis` : 
        `/claims/${claimId}/analyze_procedure`;
      const payload = {
        claim_id: parseInt(claimId),
        [type === "diagnosis" ? "disease_name" : "procedure_name"]: 
          tr?.textContent?.trim() || `Unknown ${type}`,
        item_id: dbId
      };
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const result = await res.json();
      dx = result.data || result;
    } else {
      dx = tr?.dataset.row ? JSON.parse(tr.dataset.row) : {};
    }

    // 🔹 tampilkan modal
    openModal(`Detail ${type}`, buildModalContent(dx));

    // 🔹 update ringkasan (kolom tabel)
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
  // Patch: ambil langsung dari response JSON
  const klinis = {
    justifikasi: it.justifikasi || "-",
    bukti_klinis: it.bukti_klinis || "-",
    syarat_klinis: it.syarat_klinis || "-"
  };

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
            onclick="openProcedureModal('${td.id}', '${td.nama}')">
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


async function openProcedureModal(procId, procedureName) {
  const claimId = document.getElementById("claimRoot")?.dataset.claimId;
  // Pastikan procedureName diterima dari argumen
  if (!claimId || !procedureName) {
    alert("Claim ID atau nama tindakan tidak ditemukan.");
    return;
  }
  try {
    const res = await fetch("/analyze_procedure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ claim_id: claimId, procedure_name: procedureName })
    });
    const result = await res.json();
    const d = result.data || result;
    const content = `
      <div class="flex justify-between items-center mb-3">
        <h3 class="text-lg font-bold">Detail Tindakan (${d.procedure || procedureName || '-'})</h3>
        <button type="button" onclick="closeNestedModal()" class="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded">✕</button>
      </div>
      <div class="grid grid-cols-2 gap-2">
  <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Kode ICD-9:</b></div>
  <div class="bg-gray-800 px-3 py-2 rounded text-white">${d.icd9_code || '-'}</div>
  <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Deskripsi:</b></div>
  <div class="bg-gray-800 px-3 py-2 rounded text-white">${d.icd9_desc || '-'}</div>
  <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Validitas:</b></div>
  <div class="bg-gray-800 px-3 py-2 rounded text-white">${d.validitas || '-'}</div>
  <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Status:</b></div>
  <div class="bg-gray-800 px-3 py-2 rounded text-white">${d.status_tindakan || '-'}</div>
  <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>INA-CBG:</b></div>
  <div class="bg-gray-800 px-3 py-2 rounded text-white">${d.ina_cbg_tarif || '-'}</div>
  <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Faskes:</b></div>
  <div class="bg-gray-800 px-3 py-2 rounded text-white">${d.faskes || '-'}</div>
  <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Rawat Inap:</b></div>
  <div class="bg-gray-800 px-3 py-2 rounded text-white">${d.rawat_inap || '-'}</div>
  <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Syarat Klinis:</b></div>
  <div class="bg-gray-800 px-3 py-2 rounded text-white">${d.syarat_klinis || '-'}</div>
      </div>
    `;
    openModal(`Detail Tindakan (${d.procedure || procedureName || '-'})`, content, { hideDefaultClose: true });
  } catch (err) {
    console.error("Gagal load detail granular tindakan", err);
    alert("Gagal load detail granular tindakan");
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

    // 🔥 FIXED: Use core_engine endpoint instead of dummy
    const res = await fetch(`/claims/${claimId}/generate_claim_combos`, {
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
    <tr><th class="bg-green-100 dark:bg-green-700 px-3 py-2 text-left">Validitas Klinis Kombinasi</th>
      <td class="px-3 py-2">${statusIcon(data.validitas)} ${data.validitas || "-"}</td></tr>
    <tr><th class="bg-gray-100 dark:bg-gray-700 px-3 py-2 text-left">Severity</th>
      <td class="px-3 py-2">${data.severity || "-"}</td></tr>
    <tr><th class="bg-gray-100 dark:bg-gray-700 px-3 py-2 text-left">Kode INA-CBG</th>
      <td class="px-3 py-2">${data.kode_cbg || data.kode_ina_cbg || data.ina_cbg || "-"}</td></tr>
    <tr><th class="bg-gray-100 dark:bg-gray-700 px-3 py-2 text-left">Estimasi Tarif</th>
      <td class="px-3 py-2">${data.estimasi_tarif || formatRupiah(data.tarif) || "-"}</td></tr>
    <tr><th class="bg-gray-100 dark:bg-gray-700 px-3 py-2 text-left">Syarat Klinis (Kombinasi)</th>
      <td class="px-3 py-2">${data.syarat_klinis || data.syarat || "-"}</td></tr>
    <tr><th class="bg-gray-100 dark:bg-gray-700 px-3 py-2 text-left">Evaluasi Faskes</th>
      <td class="px-3 py-2">${data.evaluasi_faskes || data.faskes || "-"}</td></tr>
    <tr><th class="bg-gray-100 dark:bg-gray-700 px-3 py-2 text-left">Rawat Inap</th>
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
      <tr><th class="bg-green-100 dark:bg-green-700 px-3 py-2 text-left">Tindakan Wajib Kombinasi</th>
          <td class="px-3 py-2">${statusIcon(data.wajib || data.tindakan_wajib)} ${data.wajib || data.tindakan_wajib || "-"}</td></tr>
      <tr><th class="bg-gray-100 dark:bg-gray-700 px-3 py-2 text-left">Validasi Pilihan Verifikator</th>
          <td class="px-3 py-2">${statusIcon(data.validasi)} ${data.validasi || "-"}</td></tr>
      <tr><th class="bg-gray-100 dark:bg-gray-700 px-3 py-2 text-left">Dampak INA-CBG / Tarif</th>
          <td class="px-3 py-2">${data.dampak || "-"}</td></tr>
      <tr><th class="bg-gray-100 dark:bg-gray-700 px-3 py-2 text-left">Konflik / Duplikasi</th>
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
  items.forEach((alt, idx) => {
    target.innerHTML += `
      <div class="mb-3 p-3 rounded shadow bg-white border">
        <div class="font-semibold text-blue-700 mb-1">${alt.judul ? alt.judul : `Alternatif ${idx + 1}`}</div>
        <div><b>Severity:</b> ${alt.severity || "-"}</div>
        <div><b>INA-CBG:</b> ${alt.kode_ina_cbg || alt.kode_cbg || alt.ina_cbg || "-"}</div>
        <div><b>Tarif:</b> ${alt.estimasi_tarif || formatRupiah(alt.tarif) || "-"}</div>
        <div><b>Syarat Klinis:</b> ${alt.syarat_klinis || alt.syarat || "-"}</div>
        <div><b>Evaluasi Faskes:</b> ${alt.faskes || "-"}</div>
        <div><b>Rawat Inap:</b> ${alt.rawat_inap || "-"}</div>
        <div><b>Tindakan:</b> ${(Array.isArray(alt.tindakan) ? alt.tindakan.join(", ") : alt.tindakan_wajib || "-")}</div>
        <div class="mt-1 text-gray-600 text-xs">${alt.catatan || ""}</div>
      </div>
    `;
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

// --- PATCH: New API handlers for granular AI claim workflow ---

async function analyzeDiagnosis() {
  const claimId = document.getElementById("claimRoot")?.dataset.claimId;
  const state = Alpine.$data(document.getElementById("claimRoot"));
  const stage = state.tab || "admission";
  try {
    const res = await fetch("/analyze_diagnosis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ claim_id: claimId, stage })
    });
    const result = await res.json();
    console.log("📥 Diagnosis analysis:", result);
    renderEvaluasiDiagnosis(result.data || result);
  } catch (err) {
    console.error("❌ Error analyze diagnosis:", err);
    alert("Gagal analisa diagnosis");
  }
}

async function analyzeProcedure(procedureName) {
  const claimId = document.getElementById("claimRoot")?.dataset.claimId;
  const state = Alpine.$data(document.getElementById("claimRoot"));
  const stage = state.tab || "admission";
  try {
    const res = await fetch("/analyze_procedure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ claim_id: claimId, procedure_name: procedureName, stage })
    });
    const result = await res.json();
    console.log("📥 Procedure analysis:", result);
    renderEvaluasiProcedure(result.data || result);
  } catch (err) {
    console.error("❌ Error analyze procedure:", err);
    alert("Gagal analisa tindakan");
  }
}

async function generateClaimCombos() {
  const claimId = document.getElementById("claimRoot")?.dataset.claimId;
  const state = Alpine.$data(document.getElementById("claimRoot"));
  const stage = state.tab || "admission";
  // Build granular payload from simulasi
  const sim = state.simulasi[stage] || {};
  const payload = {
    claim_id: claimId,
    stage,
    primary_claim: sim.utama?.name || "",
    secondary_claims: Array.isArray(sim.sekunder) ? sim.sekunder.map(dx => dx.name) : [],
    primary_action: sim.tindakanUtama?.name || "",
    secondary_actions: Array.isArray(sim.tindakanSekunder) ? sim.tindakanSekunder.map(td => td.name) : []
  };
  try {
    const res = await fetch("/generate_claim_combos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    console.log("📥 Claim combos:", result);
    // Ambil granular dari result.result jika ada
    const granular = result.result || {};
    renderEvaluasiDiagnosis(granular.evaluasi_diagnosis || {});
    renderEvaluasiProcedure(granular.evaluasi_tindakan || {});
    renderAlternatifKombinasi(granular.alternatif || []);
    alert("✅ Summary berhasil digenerate");
  } catch (err) {
    console.error("❌ Error generate claim combos:", err);
    alert("Gagal generate kombinasi klaim");
  }
}

async function resumeMedis() {
  const claimId = document.getElementById("claimRoot")?.dataset.claimId;
  const state = Alpine.$data(document.getElementById("claimRoot"));
  const stage = state.tab || "admission";
  try {
    const res = await fetch("/resume_medis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ claim_id: claimId, stage })
    });
    const result = await res.json();
    console.log("📥 Resume medis:", result);
    // You can add a renderer for resume if needed
    alert("Resume medis berhasil digenerate");
  } catch (err) {
    console.error("❌ Error resume medis:", err);
    alert("Gagal generate resume medis");
  }
}

window.analyzeDiagnosis = analyzeDiagnosis;
window.analyzeProcedure = analyzeProcedure;
window.generateClaimCombos = generateClaimCombos;
window.resumeMedis = resumeMedis;


window.addManual = addManual
window.openProcedureModal = openProcedureModal;
window.closeNestedModal = closeNestedModal;
window.generateSummary = generateSummary;
window.renderEvaluasiDiagnosis = renderEvaluasiDiagnosis;
window.renderEvaluasiProcedure = renderEvaluasiProcedure;
window.renderAlternatifKombinasi = renderAlternatifKombinasi;