// ==================== Generate AI ====================
function claimData(init) {
  const state = {
    role: init.role || 'doctor', // doctor, verifikator, coder
    tab: init.tab || 'admission',
    form: {},

    // 🔹 Simulasi hasil AI (utama/sekunder) → dari ClaimSimulation
    simulasi: {
      admission: { utama: [], sekunder: [] },
      daily: {},
      discharge: { utama: [], sekunder: [] }
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

async function generateAI() {
  const claimId = document.getElementById("claimRoot")?.dataset.claimId
               || document.getElementById("claimIdHidden")?.value;

  if (!claimId) {
    alert("❌ Claim ID tidak ditemukan. Pastikan buka halaman klaim yang valid.");
    return;
  }

  try {
    // ✅ endpoint sesuai BE (POST + body claim_id)
    const res = await fetch("/ai/recommendation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ claim_id: claimId })
    });

    if (!res.ok) {
      throw new Error("Server error: " + res.status);
    }

    const data = await res.json();
    console.log("📥 Data pecahan dari BE:", data);

    const state = Alpine.$data(document.getElementById("claimRoot"));

    // === Admission ===
    renderTable("diagnosis-admission", data.admission?.diagnosis || [], "diagnosis", "admission");
    renderTable("komorbid-admission", data.admission?.komorbid || [], "komorbid", "admission");
    renderTable("komplikasi-admission", data.admission?.komplikasi || [], "komplikasi", "admission");

    state.simulasi.admission = { ...(state.simulasi.admission || {}), ...(data.admission?.simulasi || {}) };

    // === Daily (array) ===
    const dailyContainer = document.getElementById("daily-accordion");
    dailyContainer.innerHTML = "";

    if (Array.isArray(data.daily)) {
      data.daily.forEach((hari, idx) => {
        const dayId = `daily-${idx}`;

        if (!state.simulasi[dayId]) {
          state.simulasi[dayId] = { diagnosis: [], komorbid: [], komplikasi: [], tindakan: [] };
        }
        if (!state.manualInput.daily[dayId]) {
          state.manualInput.daily[dayId] = {
            diagnosis: { kategori:"", klinis:"", icd:"", tindakan:"", score:"" },
            komorbid:  { kategori:"", klinis:"", icd:"", tindakan:"", score:"" },
            komplikasi:{ kategori:"", klinis:"", icd:"", tindakan:"", score:"" }
          };
        }

        // accordion harian
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
        `);
        Alpine.initTree(dailyContainer);

        renderTable(`diagnosis-${dayId}`, hari.diagnosis || [], "diagnosis", dayId);
        renderTable(`komorbid-${dayId}`, hari.komorbid || [], "komorbid", dayId);
        renderTable(`komplikasi-${dayId}`, hari.komplikasi || [], "komplikasi", dayId);

        // simpan ke state
        state.simulasi.daily.days = state.simulasi.daily.days || [];
        state.simulasi.daily.days[idx] = state.simulasi[dayId];
      });
    }

    // === Discharge ===
    renderTable("diagnosis-discharge", data.discharge?.diagnosis || [], "diagnosis", "discharge");
    renderTable("komorbid-discharge", data.discharge?.komorbid || [], "komorbid", "discharge");
    renderTable("komplikasi-discharge", data.discharge?.komplikasi || [], "komplikasi", "discharge");

    state.simulasi.discharge = { ...(state.simulasi.discharge || {}), ...(data.discharge?.simulasi || {}) };

    // === Evaluasi & Kombinasi (panel kanan) ===
    renderEvaluasiDiagnosis(data.evaluasi_diagnosis || []);
    renderEvaluasiProcedure(data.evaluasi_procedure || []);
    renderAlternatifKombinasi(data.alternatif || []);

    // ✅ update rekomendasi ke Alpine store
    window.dispatchEvent(new CustomEvent('update-rekom', {
      detail: {
        medis: data.evaluasi_diagnosis || [],
        regulasi: data.evaluasi_procedure || [],
        tarif: data.alternatif || []
      }
    }));

  } catch (err) {
    console.error("Error generate AI:", err);
    alert("Gagal generate AI");
  }
}

// ==================== Render Table ====================
function renderTable(targetId, items, type, tab, dayId = null) {
  const state = Alpine.$data(document.getElementById("claimRoot"))

  if (!state.simulasi[tab]) {
    state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [], tindakan: [] }
  }

  // filter AI vs manual
  const oldItems = state.simulasi[tab][type] || []
  const oldAiItems = oldItems.filter(it => !it.isManual)
  const manualItems = oldItems.filter(it => it.isManual)

  const newAiItems = (items || []).filter(it => !it.isManual)
  const aiItems = newAiItems.length > 0 ? newAiItems : oldAiItems

  let merged = [...aiItems, ...manualItems]

  // hindari duplikat
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

  // grup parent-child
  let grouped = []
  let currentParent = null
  merged.forEach(it => {
    if (!it.child) {
      currentParent = { ...it, children: [] }
      grouped.push(currentParent)
    } else if (currentParent) {
      currentParent.children.push(it)
    }
  })

  // header table
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
        <th class="border px-3 py-2 text-center">Score</th>
        ${state.role === "doctor" ? `<th class="border px-3 py-2 text-center">Mapping</th>` : ``}
      </tr>`
    table.insertBefore(thead, table.firstChild)
  }

  grouped.forEach((parent, idx) => {
    const counter = 1 + (parent.children ? parent.children.length : 0)
    const tbody = document.createElement("tbody")
    tbody.setAttribute("x-data", "{ open:false }")

    // parent row
    tbody.insertAdjacentHTML("beforeend", `
      <tr class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 font-medium text-sm">
        <td class="border px-3 py-2 whitespace-nowrap overflow-hidden text-ellipsis max-w-[200px]"
            data-item='${JSON.stringify(parent)}'
            onclick="openModalFromAttr(this)">
          <span @click.stop="open=!open" class="mr-1 cursor-pointer">
            <span x-show="!open" x-cloak>▶</span>
            <span x-show="open" x-cloak>▼</span>
          </span>
          ${parent.kategori || "-"}
          <span class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">${counter}</span>
        </td>
        <td class="border px-3 py-2 text-ellipsis max-w-[200px]" title="${parent.klinis || ""}">
          ${parent.klinis ? truncateText(parent.klinis, 20) : "…"}
        </td>
        <td class="border px-3 py-2 text-center">${parent.icd10_code || parent.icd9_code || "-"}</td>
        <td class="border px-3 py-2 text-ellipsis max-w-[200px]" 
            title="${parent.tindakan || parent.procedure_text || ""}"
            onclick="openProcedureModal('${parent.id || ''}')">
          ${parent.tindakan ? truncateText(parent.tindakan, 20) 
                           : parent.procedure_text ? truncateText(parent.procedure_text, 20) 
                           : "…"}
        </td>
        <td class="border px-3 py-2 text-center">${parent.score || "-"}</td>
        ${state.role === "doctor" ? `
        <td class="border px-3 py-2 text-center">
          ${renderMappingSelect(parent, tab, type, idx)}
        </td>` : ``}
      </tr>
    `)

    // children
    parent.children.forEach(child => {
      tbody.insertAdjacentHTML("beforeend", `
        <tr x-show="open" x-cloak
            class="bg-gray-50 dark:bg-gray-800 italic text-sm">
          <td class="border px-3 py-2 whitespace-nowrap overflow-hidden text-ellipsis max-w-[200px]"
              data-item='${JSON.stringify(child)}'
              onclick="openModalFromAttr(this)">
            → ${child.kategori || "-"}
          </td>
          <td class="border px-3 py-2 text-ellipsis max-w-[200px]" title="${child.klinis || ""}">
            ${child.klinis ? truncateText(child.klinis, 20) : "…"}
          </td>
          <td class="border px-3 py-2 text-center">${child.icd10_code || child.icd9_code || "-"}</td>
          <td class="border px-3 py-2 text-ellipsis max-w-[200px]" 
              title="${child.tindakan || child.procedure_text || ""}"
              onclick="openProcedureModal('${child.id || ''}')">
            ${child.tindakan ? truncateText(child.tindakan, 20) 
                             : child.procedure_text ? truncateText(child.procedure_text, 20) 
                             : "…"}
          </td>
          <td class="border px-3 py-2 text-center">${child.score || "-"}</td>
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

  // update counter
  const counterId = dayId ? `count-${type}-${dayId}` : `count-${type}-${tab}`
  const countEl = document.getElementById(counterId)
  if (countEl) {
    let total = grouped.reduce((sum, p) => sum + 1 + p.children.length, 0)
    countEl.textContent = total
  }

  // manual row tetap ada
  if (state.role === "doctor") {
    if (tab === "admission" || tab === "discharge" || tab.startsWith("daily-")) {
      const manualTbody = document.createElement("tbody")
      const tabPath = tab.startsWith("daily-") 
        ? `manualInput.daily['${tab}'].${type}`
        : `manualInput.${tab}.${type}`

      manualTbody.insertAdjacentHTML("beforeend", `
        <tr class="manual-row bg-gray-50 dark:bg-gray-800">
          <td class="border px-3 py-2"><input x-model="${tabPath}.kategori" placeholder="Nama Penyakit" class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600"></td>
          <td class="border px-3 py-2"><input x-model="${tabPath}.klinis" placeholder="Klinis" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600"></td>
          <td class="border px-3 py-2"><input x-model="${tabPath}.icd10_code" placeholder="ICD-10" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600"></td>
          <td class="border px-3 py-2"><input x-model="${tabPath}.procedure_text" placeholder="Tindakan" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600"></td>
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
      diagnosis: { kategori:"", klinis:"", icd10_code:"", tindakan:"", score:"" },
      komorbid:  { kategori:"", klinis:"", icd10_code:"", tindakan:"", score:"" },
      komplikasi:{ kategori:"", klinis:"", icd10_code:"", tindakan:"", score:"" }
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

  // Buat item manual sesuai schema baru
  const newItem = {
    kategori: input.kategori || "",
    klinis: input.klinis || "",
    icd10_code: input.icd10_code || "",   // ✅ ganti field icd → icd10_code
    tindakan: input.tindakan || "",
    score: input.score || 0,
    mapping: "",
    isManual: true,
    source: "Manual"
  }

  // Pastikan simulasi[tab][type] ada
  if (!state.simulasi[tab]) {
    state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [], tindakan: [] }
  }
  if (!Array.isArray(state.simulasi[tab][type])) {
    state.simulasi[tab][type] = []
  }

  // Tambahkan item ke simulasi per-tab
  state.simulasi[tab][type].push(newItem)

  // Sinkronisasi ke struktur daily.days (tanpa auto masuk sekunder!)
  if (tab.startsWith("daily-")) {
    const idx = parseInt(tab.split("-")[1], 10);
    if (!state.simulasi.daily.days) state.simulasi.daily.days = [];
    state.simulasi.daily.days[idx] = state.simulasi[tab];

    // 🔄 sinkronisasi ke summary daily
    const allDays = state.simulasi.daily.days || [];
    state.simulasi.daily.utama = null;
    state.simulasi.daily.sekunder = [];

    allDays.forEach(d => {
      if (d.utama && !state.simulasi.daily.utama) {
        state.simulasi.daily.utama = d.utama;
      }
      if (Array.isArray(d.sekunder)) {
        state.simulasi.daily.sekunder.push(...d.sekunder);
      }
    });
  }

  // Reset form input
  if (tab.startsWith("daily-")) {
    state.manualInput.daily[tab][type] = { kategori:"", klinis:"", icd10_code:"", tindakan:"", score:"" }
  } else {
    state.manualInput[tab][type] = { kategori:"", klinis:"", icd10_code:"", tindakan:"", score:"" }
  }

  // Render ulang tabel
  renderTable(`${type}-${tab}`, state.simulasi[tab][type], type, tab)

  // 🚨 Opsional: panggil BE buat enrich manual input
  fetch("/ai/recommendation/detail", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      claim_id: state.claimId,
      type,
      kategori: newItem.kategori,
      klinis: newItem.klinis,
      icd10_code: newItem.icd10_code,
      tindakan: newItem.tindakan,
      score: newItem.score
    })
  })
  .then(res => res.json())
  .then(data => {
    Object.assign(newItem, data.data || {})
    renderTable(`${type}-${tab}`, [], type, tab) // refresh DOM
  })
  .catch(err => console.error("AI enrichment failed", err))
}

// ==================== Modal ====================

function openModal(title, content) {
  const state = Alpine.$data(document.getElementById('claimRoot'))
  state.modalOpen = true
  state.modalTitle = title
  state.modalContent = content
}

function openModalFromAttr(el) {
  const it = JSON.parse(el.dataset.item)
  // Ubah title jadi format sesuai pic
  const title = `Detail Diagnosis (${it.kategori || '-'})`
  openModal(title, buildModalContent(it))
}

function buildModalContent(it) {
  const d = it.modal_detail || {};
  const klinis = it.detail_klinis || d.aspek_klinis || {};
  const icd10 = it.detail_icd10 || d.icd10 || {};
  const tindakan = it.detail_tindakan || d.tindakan || [];
  const rawat = it.detail_rawat_inap || d.rawat_inap || {};
  const faskes = it.detail_faskes || d.faskes || {};
  const rujukan = it.detail_rujukan || d.rujukan || {};

  // helper untuk kotak info
  const renderBox = (label, value, status = "default") => {
    let colorClass = "bg-gray-200 text-gray-800"; // default abu
    if (status === "valid") colorClass = "bg-green-500 text-white";
    if (status === "invalid") colorClass = "bg-red-500 text-white";

    return `
      <div class="${colorClass} px-3 py-2 rounded text-sm flex justify-between items-center">
        <span class="font-medium">${label}</span>
        <span>${value || "-"}</span>
      </div>
    `;
  };

  // helper tindakan
  const renderTindakan = (list) => {
    if (!list || list.length === 0) {
      return `<div class="italic text-gray-500">Tidak ada tindakan</div>`;
    }
    return list.map(td => `
      <div class="flex justify-between items-center bg-white dark:bg-gray-800 p-3 rounded shadow mb-2">
        <div>
          <div class="font-semibold">${td.nama || "-"}</div>
          <div class="text-xs text-gray-500">${td.keterangan || ""}</div>
        </div>
        <div class="space-x-1">
          <button class="bg-blue-600 text-white px-2 py-1 rounded text-xs">Pilih Utama</button>
          <button class="bg-purple-600 text-white px-2 py-1 rounded text-xs">Pilih Sekunder</button>
        </div>
      </div>
    `).join("");
  };

  return `
    <div class="space-y-6 text-sm">

      <!-- KLINIS -->
      <section>
        <div class="bg-blue-600 text-white px-3 py-2 rounded-t font-bold">KLINIS</div>
        <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700 rounded-b">
          ${renderBox("Justifikasi", klinis.justifikasi, klinis.status)}
          ${renderBox("Bukti Klinis", klinis.bukti || klinis.bukti_klinis, klinis.status_bukti)}
          ${renderBox("Syarat Klinis", klinis.syarat || klinis.syarat_klinis, klinis.status_syarat)}
        </div>
      </section>

      <!-- ICD-10 -->
      <section>
        <div class="bg-blue-600 text-white px-3 py-2 rounded-t font-bold">ICD-10</div>
        <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700 rounded-b">
          ${renderBox("Struktur ICD", icd10.struktur, icd10.status)}
          ${renderBox("Kode Ganda", icd10.kode_ganda, icd10.status_ganda)}
          ${renderBox("Z-Code", icd10.z_code, icd10.status_z)}
          ${renderBox("Kode Khusus BPJS", icd10.kode_bpjs, icd10.status_bpjs)}
        </div>
      </section>

      <!-- TINDAKAN -->
      <section>
        <div class="bg-blue-600 text-white px-3 py-2 rounded-t font-bold">TINDAKAN</div>
        <div class="p-3 bg-gray-100 dark:bg-gray-700 rounded-b">
          ${renderTindakan(tindakan)}
        </div>
      </section>

      <!-- RAWAT INAP -->
      <section>
        <div class="bg-blue-600 text-white px-3 py-2 rounded-t font-bold">RAWAT INAP</div>
        <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700 rounded-b">
          ${renderBox("Indikasi", rawat.indikasi, rawat.status_indikasi)}
          ${renderBox("Lama Rawat", rawat.lama, rawat.status_lama)}
          ${renderBox("Perpanjangan", rawat.perpanjangan, rawat.status_perpanjangan)}
        </div>
      </section>

      <!-- FASKES -->
      <section>
        <div class="bg-blue-600 text-white px-3 py-2 rounded-t font-bold">FASKES</div>
        <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700 rounded-b">
          ${renderBox("Kesesuaian RS", faskes.kesesuaian, faskes.status)}
        </div>
      </section>

      <!-- RUJUKAN -->
      <section>
        <div class="bg-blue-600 text-white px-3 py-2 rounded-t font-bold">RUJUKAN</div>
        <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700 rounded-b">
          ${renderBox("Syarat", rujukan.syarat, rujukan.status_syarat)}
          ${renderBox("Kelayakan", rujukan.kelayakan, rujukan.status_kelayakan)}
        </div>
      </section>

    </div>
  `;
}


function openProcedureModal(procId) {
  // TODO: bisa diubah jadi fetch ke BE kalau mau ambil detail tindakan real
  // sementara contoh dummy lookup dari state / mapping lokal
  const state = Alpine.$data(document.getElementById("claimRoot"))
  const allDiag = [...(state.simulasi?.admission?.diagnosis || []),
                   ...(state.simulasi?.discharge?.diagnosis || []),
                   ...(state.simulasi?.daily?.flatMap(d => d.diagnosis) || [])]

  let procDetail = null
  for (const diag of allDiag) {
    const tindakanList = diag.modal_detail?.tindakan || []
    const found = tindakanList.find(td => td.kode === procId || td.nama === procId)
    if (found) {
      procDetail = found
      break
    }
  }

  if (!procDetail) {
    alert("Detail tindakan tidak ditemukan")
    return
  }

  const content = `
    <div class="space-y-4 text-sm">
      <section class="p-3 bg-gray-50 dark:bg-gray-700 rounded">
        <h4 class="font-semibold mb-2">Detail Tindakan</h4>
        <ul class="list-disc list-inside space-y-1">
          <li><b>Kode:</b> ${procDetail.kode || '-'}</li>
          <li><b>Nama:</b> ${procDetail.nama || '-'}</li>
          <li><b>Deskripsi:</b> ${procDetail.deskripsi || '-'}</li>
          <li><b>Kategori:</b> ${procDetail.kategori || '-'}</li>
        </ul>
      </section>
    </div>
  `

  openModal(`Detail Tindakan (${procDetail.nama})`, content)
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
    id: r.id, // ✅ penting untuk openProcedureModal
    kategori: r.kategori || r.sim_text || "-",
    klinis: r.klinis || "-", // langsung dari kolom BE
    icd10_code: r.icd10_code || "-",
    tindakan: r.procedure_text || r.tindakan || "-", // ambil dari ClaimProcedure
    score: r.confidence_score || r.score || 0,
    child: r.child || false,
    isManual: r.is_manual || false,
    modal_detail: r.modal_detail || {}
  }
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

async function generateSummary() {
  const claimId = document.getElementById("claimRoot")?.dataset.claimId;
  if (!claimId) {
    alert("❌ Claim ID tidak ditemukan.");
    return;
  }

  try {
    // Ambil state simulasi dari Alpine
    const state = Alpine.$data(document.getElementById("claimRoot"));

    // Payload minimal: mapping utama/sekunder dari simulasi
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

    // Render evaluasi hasil summary
    renderEvaluasiDiagnosis(data.diagnosis || []);
    renderEvaluasiProcedure(data.procedure || []);
    renderAlternatifKombinasi(data.alternatif || []);

    // Trigger Alpine untuk update rekomendasi
    window.dispatchEvent(new CustomEvent("update-rekom", {
      detail: {
        medis: data.diagnosis || [],
        regulasi: data.procedure || [],
        tarif: data.alternatif || []
      }
    }));

    alert("✅ Summary berhasil digenerate");

  } catch (err) {
    console.error("Error generate summary:", err);
    alert("❌ Gagal generate summary");
  }
}



// ==================== Panel Evaluasi & Alternatif ====================

function renderEvaluasiDiagnosis(items) {
  const target = document.getElementById("evaluasi-diagnosis");
  if (!target) return;
  target.innerHTML = "";

  (items || [])
    .filter(it => it.kategori || it.klinis || it.score)  // 🚨 filter yang kosong
    .forEach(it => {
      target.insertAdjacentHTML("beforeend", `
        <div class="p-2 border-b">
          <b>${it.kategori || "-"}</b> - ${it.klinis || "-"}
          <span class="ml-2">${confidenceBadge(it.score || 0)}</span>
        </div>
      `);
    });

  if (target.innerHTML.trim() === "") {
    target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada evaluasi</div>`;
  }
}

function renderEvaluasiProcedure(items) {
  const target = document.getElementById("evaluasi-procedure");
  if (!target) return;
  target.innerHTML = "";

  (items || [])
    .filter(it => it.kategori || it.tindakan || it.score) // filter kosong
    .forEach(it => {
      target.insertAdjacentHTML("beforeend", `
        <div class="p-2 border-b">
          <b>${it.kategori || "-"}</b> - ${it.tindakan || "-"}
          <span class="ml-2">${confidenceBadge(it.score || 0)}</span>
        </div>
      `);
    });

  if (target.innerHTML.trim() === "") {
    target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada evaluasi tindakan</div>`;
  }
}


function renderAlternatifKombinasi(items) {
  const target = document.getElementById("alternatif");
  if (!target) return;
  target.innerHTML = "";

  (items || [])
    .filter(it => it.nama || it.deskripsi || it.score) // filter kosong
    .forEach(it => {
      target.insertAdjacentHTML("beforeend", `
        <div class="p-2 border-b">
          <b>${it.nama || "Alternatif"}</b> - ${it.deskripsi || "-"}
          <span class="ml-2">${confidenceBadge(it.score || 0)}</span>
        </div>
      `);
    });

  if (target.innerHTML.trim() === "") {
    target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada alternatif kombinasi</div>`;
  }
}


window.addManual = addManual
window.generateSummary = generateSummary;
window.renderEvaluasiDiagnosis = renderEvaluasiDiagnosis;
window.renderEvaluasiProcedure = renderEvaluasiProcedure;
window.renderAlternatifKombinasi = renderAlternatifKombinasi;
