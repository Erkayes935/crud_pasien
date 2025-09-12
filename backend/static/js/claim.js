// ==================== Generate AI ====================
function claimData(init) {

  const state = {
    role: init.role || 'doctor', // doctor, verifikator, coder
    tab: init.tab || 'admission',
    form : {},
    simulasi: init.sim || {
      admission: { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null },
      daily: { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null },
      discharge: { diagnosis: [], komorbid: [], komplikasi: [], utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null }
    },
    summary: init.summ || {
      admission: { klinis:[], regulasi:[], tarif:[] },
      daily: { klinis:[], regulasi:[], tarif:[] },
      discharge: { klinis:[], regulasi:[], tarif:[] }
    },
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
    recommendations: { medis:[], regulasi:[], tarif:[] },
    modalOpen: false,
    modalTitle: '',
    modalContent: '',
    init(){
      window.addEventListener('update-rekom', e => {
        this.recommendations = e.detail
      })
      const role = this.role
      const claimId = document.getElementById("claimRoot")?.dataset.claimId

      if (role === 'verifikator' && claimId) {
        loadRecommendations(claimId)   // otomatis load dari DB
      }
    },
    statusIcon(s){
      if(s==='valid') return "✅"
      if(s==='warning') return "⚠️"
      if(s==='invalid') return "❌"
      return ""
    },
  }
  window.claimState = state  
  return state
}
async function generateAI() {
  const claimId = document.getElementById("claimRoot")?.dataset.claimId
               || document.getElementById("claimIdHidden")?.value

  console.log("✅ claimId terdeteksi:", claimId)

  if (!claimId) {
    alert("❌ Claim ID tidak ditemukan. Pastikan buka halaman klaim yang valid.")
    return
  }

  const payload = {
    claim_id: claimId,
    patient_id: 1,
    visit_id: 10,
    context: "all",
    notes: "dummy generate"
  }

  console.log("📦 Payload yg dikirim:", payload)


  try {
    const res = await fetch("/ai/recommendation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
    const data = await res.json()
    console.log("📥 Data dari BE:", data)

    // ✅ pastikan daily selalu array
    if (!Array.isArray(data.daily)) {
      data.daily = data.daily ? [data.daily] : []
    }
    const state = Alpine.$data(document.getElementById('claimRoot'))

    // === Admission ===
    renderTable("diagnosis-admission", data.admission?.diagnosis || [], "diagnosis", "admission")
    renderTable("komorbid-admission", data.admission?.komorbid || [], "komorbid", "admission")
    renderTable("komplikasi-admission", data.admission?.komplikasi || [], "komplikasi", "admission")
    Object.assign(state.simulasi.admission, data.admission?.simulasi || {})
    state.summary.admission = data.admission?.summary || {}

    // === Daily ===
    if (Array.isArray(data.daily)) {
      const dailyContainer = document.getElementById("daily-accordion")
      dailyContainer.innerHTML = ""  // reset

      data.daily.forEach((hari, idx) => {
    // unique id per hari
        hari.tanggal = hari.tanggal || `2025-09-${String(idx+1).padStart(2, "0")}`
        const dayId = `daily-${idx}`
    // init manualInput untuk setiap dayId
    if (!state.simulasi[dayId]) {
        state.simulasi[dayId] = { diagnosis: [], komorbid: [], komplikasi: [], tindakan: [] }
      }
    
    if (!state.manualInput.daily[dayId]) {
      state.manualInput.daily[dayId] = {
        diagnosis: { kategori:"", klinis:"", icd:"", tindakan:"" },
        komorbid:  { kategori:"", klinis:"", icd:"", tindakan:"" },
        komplikasi:{ kategori:"", klinis:"", icd:"", tindakan:"" }
      }
    }
    const mergeAI = (aiData, type) => {
        const aiItems = (aiData || []).map(it => ({ ...it, isManual: false }))
        const manualItems = state.simulasi[dayId][type]?.filter(it => it.isManual) || []
        state.simulasi[dayId][type] = [...aiItems, ...manualItems]
        renderTable(`${type}-${dayId}`, [], type, dayId)
      }

    mergeAI(hari.diagnosis, "diagnosis")
    mergeAI(hari.komorbid, "komorbid")
    mergeAI(hari.komplikasi, "komplikasi")

    // Setelah mergeAI selesai
    if (!state.simulasi.daily.days) state.simulasi.daily.days = []
    state.simulasi.daily.days[idx] = state.simulasi[dayId]

    // bikin accordion section baru
    dailyContainer.insertAdjacentHTML("beforeend", `
      <div class="bg-white dark:bg-gray-700 rounded shadow-sm" x-data="{open:true}">
        <button type="button" @click="open=!open"
                class="w-full flex justify-between px-4 py-2 bg-gray-200 dark:bg-gray-600 font-semibold">
          <span>Hari ${idx+1} (${hari.tanggal || '-'})</span>
          <span x-show="open">⬆️</span><span x-show="!open">⬇️</span>
        </button>
        <div x-show="open" class="p-2 space-y-2">

          <!-- Diagnosis -->
          <div class="bg-white dark:bg-gray-700 rounded shadow-sm" x-data="{open:true}">
            <button type="button" @click="open=!open"
                    class="w-full flex justify-between px-4 py-1 bg-gray-100 dark:bg-gray-600 font-semibold text-sm">
              <span>
                Diagnosis
                <span id="count-diagnosis-${dayId}"
                      class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">0</span>
              </span>
              <span x-show="open">⬆️</span><span x-show="!open">⬇️</span>
            </button>
            <div x-show="open" class="p-2">
              <table class="w-full text-xs border">
                <thead class="bg-gray-100 dark:bg-gray-800">
                  <tr>
                    <th>Kategori</th><th>Klinis</th><th>ICD</th>
                    <th>Tindakan</th><th>Score</th><th x-show="role === 'doctor'">Mapping</th>
                  </tr>
                </thead>
                <tbody id="diagnosis-${dayId}"></tbody>
                <tbody id="diagnosis-manual-${dayId}">
                <tr class="manual-row bg-gray-50 dark:bg-gray-800">
                  <td><input x-model="manualInput.daily['${dayId}'].diagnosis.kategori"
             placeholder="Nama penyakit"
             class="border px-2 py-1 w-full rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-400"></td>
                  <td><input x-model="manualInput.daily['${dayId}'].diagnosis.klinis" placeholder="Klinis"
                            class="border px-2 py-1 w-full rounded 
                                    bg-white dark:bg-gray-700 
                                    text-gray-900 dark:text-gray-100 
                                    focus:ring-2 focus:ring-blue-400" readonly></td>
                  <td><input x-model="manualInput.daily['${dayId}'].diagnosis.icd" placeholder="ICD"
                            class="border px-2 py-1 w-full rounded 
                                    bg-white dark:bg-gray-700 
                                    text-gray-900 dark:text-gray-100 
                                    focus:ring-2 focus:ring-blue-400" readonly></td>
                  <td><input x-model="manualInput.daily['${dayId}'].diagnosis.tindakan" placeholder="Tindakan"
                            class="border px-2 py-1 w-full rounded 
                                    bg-white dark:bg-gray-700 
                                    text-gray-900 dark:text-gray-100 
                                    focus:ring-2 focus:ring-blue-400" readonly></td>
                  <td><input x-model="manualInput.daily['${dayId}'].diagnosis.score" placeholder="Score"
                            class="border px-2 py-1 w-full rounded 
                                    bg-white dark:bg-gray-700 
                                    text-gray-900 dark:text-gray-100 
                                    focus:ring-2 focus:ring-blue-400" readonly></td>
                  <td>
                    <button type="button" @click="addManual('diagnosis','${dayId}')"
                            class="bg-green-600 text-white px-2 py-1 rounded">➕</button>
                  </td>
                </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Komorbid -->
          <div class="bg-white dark:bg-gray-700 rounded shadow-sm" x-data="{open:true}">
            <button type="button" @click="open=!open"
                    class="w-full flex justify-between px-4 py-1 bg-gray-100 dark:bg-gray-600 font-semibold text-sm">
              <span>
                Komorbid
                <span id="count-komorbid-${dayId}"
                      class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">0</span>
              </span>
              <span x-show="open">⬆️</span><span x-show="!open">⬇️</span>
            </button>
            <div x-show="open" class="p-2">
              <table class="w-full text-xs border">
                <thead class="bg-gray-100 dark:bg-gray-800">
                  <tr>
                    <th>Kategori</th><th>Klinis</th><th>ICD</th>
                    <th>Tindakan</th><th>Score</th><th>Mapping</th>
                  </tr>
                </thead>
                <tbody id="komorbid-${dayId}"></tbody>
                <tbody id="komorbid-manual-${dayId}">
                <tr class="manual-row bg-gray-50 dark:bg-gray-800">
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.kategori"
         placeholder="Nama penyakit"
         class="border px-2 py-1 w-full rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-400"></td>
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.klinis" placeholder="Klinis"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.icd" placeholder="ICD"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.tindakan" placeholder="Tindakan"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.score" placeholder="Score"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                <td>
                  <button type="button" @click="addManual('komorbid','${dayId}')"
                          class="bg-green-600 text-white px-2 py-1 rounded">➕</button>
                </td>
              </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Komplikasi -->
          <div class="bg-white dark:bg-gray-700 rounded shadow-sm" x-data="{open:true}">
            <button type="button" @click="open=!open"
                    class="w-full flex justify-between px-4 py-1 bg-gray-100 dark:bg-gray-600 font-semibold text-sm">
              <span>
                Komplikasi
                <span id="count-komplikasi-${dayId}"
                      class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">0</span>
              </span>
              <span x-show="open">⬆️</span><span x-show="!open">⬇️</span>
            </button>
            <div x-show="open" class="p-2">
              <table class="w-full text-xs border">
                <thead class="bg-gray-100 dark:bg-gray-800">
                  <tr>
                    <th>Kategori</th><th>Klinis</th><th>ICD</th>
                    <th>Tindakan</th><th>Score</th><th>Mapping</th>
                  </tr>
                </thead>
                <tbody id="komplikasi-${dayId}"></tbody>
                <tbody id="komplikasi-manual-${dayId}">
                  <tr class="manual-row bg-gray-50 dark:bg-gray-800">
                  <td> <input x-model="manualInput.daily['${dayId}'].komplikasi.kategori"
         placeholder="Nama penyakit"
         class="border px-2 py-1 w-full rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-400"></td>
                  <td><input x-model="manualInput.daily['${dayId}'].komplikasi.klinis" placeholder="Klinis"
                            class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                  <td><input x-model="manualInput.daily['${dayId}'].komplikasi.icd" placeholder="ICD"
                            class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                  <td><input x-model="manualInput.daily['${dayId}'].komplikasi.tindakan" placeholder="Tindakan"
                            class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                  <td><input x-model="manualInput.daily['${dayId}'].komplikasi.score" placeholder="Score"
                            class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                  <td>
                    <button type="button" @click="addManual('komplikasi','${dayId}')"
                            class="bg-green-600 text-white px-2 py-1 rounded">➕</button>
                  </td>
                </tr>
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>
    `)
    console.log("✅ accordion harusnya dibuat, cek DOM:", document.getElementById("daily-accordion").innerHTML)
    const tmpl = document.getElementById("daily-form-template")
    if (tmpl) {
      const clone = tmpl.content.cloneNode(true)
      dailyContainer.lastElementChild.querySelector(".p-2.space-y-2").appendChild(clone)
    }
    // render tabel per bagian
    renderTable(`diagnosis-${dayId}`, hari.diagnosis || [], "diagnosis", dayId)
    renderTable(`komorbid-${dayId}`, hari.komorbid || [], "komorbid", dayId)
    renderTable(`komplikasi-${dayId}`, hari.komplikasi || [], "komplikasi", dayId)
      })
    } else {
      // fallback lama kalau backend masih kirim 1 blok
      renderTable("diagnosis-daily", data.daily?.diagnosis || [], "diagnosis", "daily")
      renderTable("komorbid-daily", data.daily?.komorbid || [], "komorbid", "daily")
      renderTable("komplikasi-daily", data.daily?.komplikasi || [], "komplikasi", "daily")
    }
    Object.assign(state.simulasi.daily, {
      utama: (data.daily[0] && data.daily[0].utama) || null,
      sekunder: data.daily.flatMap(d => d.sekunder || []),
      tindakanUtama: (data.daily[0] && data.daily[0].tindakanUtama) || null,
      tindakanSekunder: data.daily.flatMap(d => d.tindakanSekunder || []),
      tarifDraft: null
    })
    Object.assign(state.summary.daily, {
      klinis: data.daily.flatMap(d => d.summary?.klinis || []),
      regulasi: data.daily.flatMap(d => d.summary?.regulasi || []),
      tarif: data.daily.flatMap(d => d.summary?.tarif || [])
    })


    // === Discharge ===
    renderTable("diagnosis-discharge", data.discharge?.diagnosis || [], "diagnosis", "discharge")
    renderTable("komorbid-discharge", data.discharge?.komorbid || [], "komorbid", "discharge")
    renderTable("komplikasi-discharge", data.discharge?.komplikasi || [], "komplikasi", "discharge")
    Object.assign(state.simulasi.discharge, data.discharge?.simulasi || {})
    state.summary.discharge = data.discharge?.summary || {}

    // === Panel kanan (SARAN SIMULASI) ===
    window.dispatchEvent(new CustomEvent('update-rekom', {
      detail: {
        medis: [
          ...(data.discharge?.summary?.klinis || [])
        ],
        regulasi: [
          ...(data.discharge?.summary?.regulasi || [])
        ],
        tarif: [
          ...(data.discharge?.summary?.tarif || [])
        ]
      }
    }))

  } catch (err) {
    console.error("Error generate AI:", err)
    alert("Gagal generate AI")
  }
}


// ==================== Render Table ====================
function renderTable(targetId, items, type, tab, dayId = null) {
  const state = Alpine.$data(document.getElementById('claimRoot'))

  if (!state.simulasi[tab]) {
    state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [], tindakan: [] }
  }
  if (!Array.isArray(state.simulasi[tab][type])) {
    state.simulasi[tab][type] = []
  }

  // Ambil isi lama
  const oldItems = state.simulasi[tab][type] || []
  const oldAiItems = oldItems.filter(it => !it.isManual)
  const manualItems = oldItems.filter(it => it.isManual)

  // AI baru
  const newAiItems = (items || []).filter(it => !it.isManual)
  const aiItems = newAiItems.length > 0 ? newAiItems : oldAiItems

  // Gabungan
  let merged = [...aiItems, ...manualItems]

  // Dedup (berdasarkan kategori-icd-tindakan)
  const seen = new Set()
  merged = merged.filter(it => {
    const key = `${it.kategori}-${it.icd}-${it.tindakan}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })

  state.simulasi[tab][type] = merged

  const target = document.getElementById(targetId)
  if (!target) return

  target.innerHTML = ""

  state.simulasi[tab][type].forEach((item, idx) => {
    target.insertAdjacentHTML("beforeend", `
      <tr>
        <td class="border px-2 py-1 cursor-pointer text-blue-600 underline"
            data-item='${JSON.stringify(item)}'
            onclick="openModalFromAttr(this)">
          ${item.kategori || "-"}
        </td>
        <td class="border px-2 py-1">${item.klinis || "-"}</td>
        <td class="border px-2 py-1">${item.icd || "-"}</td>
        <td class="border px-2 py-1">${item.tindakan || "-"}</td>
        <td class="border px-2 py-1">${item.score || "-"}</td>
        <td ${type === "tindakan" ? 'style="display:none"' : ""}>
          <select onchange="onMappingChange(event, '${tab}', '${type}', ${idx})"
                  class="border px-2 py-1 rounded 
                         bg-white dark:bg-gray-700 
                         text-gray-900 dark:text-gray-200 
                         focus:ring-2 focus:ring-blue-400"
                  ${state.role !== 'doctor' ? 'disabled' : ''}>
            <option value="" ${item.mapping===""?"selected":""}>Pilih</option>
            <option value="Diagnosis Utama" ${item.mapping==="Diagnosis Utama"?"selected":""}>Diagnosis Utama</option>
            <option value="Komorbid" ${item.mapping==="Komorbid"?"selected":""}>Komorbid</option>
            <option value="Komplikasi" ${item.mapping==="Komplikasi"?"selected":""}>Komplikasi</option>
            <option value="None" ${item.mapping==="None"?"selected":""}>None</option>
          </select>
        </td>
      </tr>
    `)
  })

  // Update counter
  let counterId = dayId ? `count-${type}-${dayId}` : `count-${type}-${tab}`
  const countEl = document.getElementById(counterId)
  if (countEl) countEl.textContent = state.simulasi[tab][type].length
}

// ==================== Add Manual ====================
function addManual(type, tab) {
  const state = Alpine.$data(document.getElementById('claimRoot'))

  // Pastikan manualInput daily ada
  if (tab.startsWith("daily-") && !state.manualInput.daily[tab]) {
    state.manualInput.daily[tab] = {
      diagnosis: { kategori:"", klinis:"", icd:"", tindakan:"", score:"" },
      komorbid:  { kategori:"", klinis:"", icd:"", tindakan:"", score:"" },
      komplikasi:{ kategori:"", klinis:"", icd:"", tindakan:"", score:"" }
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
    name: input.kategori || "-",
    kategori: input.kategori || "",
    klinis: input.klinis || "-",
    icd: input.icd || "-",
    tindakan: input.tindakan || "-",
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
    state.manualInput.daily[tab][type] = { kategori:"", klinis:"", icd:"", tindakan:"", score:"" }
  } else {
    state.manualInput[tab][type] = { kategori:"", klinis:"", icd:"", tindakan:"", score:"" }
  }

  // Render ulang tabel
  renderTable(`${type}-${tab}`, state.simulasi[tab][type], type, tab)

  // Panggil AI rekomendasi untuk enrich manual
  fetch("/ai/recommendation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kategori: newItem.kategori, tab, type })
  })
  .then(res => res.json())
  .then(data => {
    Object.assign(newItem, data)
    renderTable(`${type}-${tab}`, [], type, tab) // refresh DOM
  })
  .catch(err => console.error("AI recommendation failed", err))
}

window.addManual = addManual


// ==================== Modal ====================

function openModal(title, content) {
  const state = Alpine.$data(document.getElementById('claimRoot'))
  state.modalOpen = true
  state.modalTitle = title
  state.modalContent = content
}

function openModalFromAttr(el) {
  const it = JSON.parse(el.dataset.item)
  openModal(it.kategori, buildModalContent(it))
}

function buildModalContent(it) {
  const d = it.modal_detail || {}
  if (it.tindakan && !d.tindakan) {
    d.tindakan = [{ nama: it.tindakan }]
  }
  return `
    <div class="space-y-4 text-sm">

      <!-- Aspek Klinis -->
      <section class="p-3 bg-gray-50 dark:bg-gray-700 rounded">
        <h4 class="font-semibold mb-2">Aspek Klinis</h4>
        <ul class="list-disc list-inside space-y-1">
          <li><b>Justifikasi:</b> ${d.aspek_klinis?.justifikasi || '-'}</li>
          <li><b>Bukti:</b> ${d.aspek_klinis?.bukti || '-'}</li>
          <li><b>Syarat:</b> ${d.aspek_klinis?.syarat || '-'}</li>
        </ul>
      </section>

      <!-- ICD-10 -->
      <section class="p-3 bg-gray-50 dark:bg-gray-700 rounded">
        <h4 class="font-semibold mb-2">ICD-10</h4>
        <ul class="list-disc list-inside space-y-1">
          <li><b>Struktur Kode:</b> ${d.icd10?.struktur_kode || '-'}</li>
          <li><b>Kode Ganda:</b> ${d.icd10?.kode_ganda || '-'}</li>
          <li><b>Z-Code:</b> ${d.icd10?.z_code || '-'}</li>
          <li><b>Kode BPJS Khusus:</b> ${d.icd10?.kode_bpjs_khusus || '-'}</li>
        </ul>
      </section>

      <!-- Tindakan -->
      <section class="p-3 bg-gray-50 dark:bg-gray-700 rounded">
        <h4 class="font-semibold mb-2">Tindakan</h4>
        <div class="mt-2 space-y-1">
          ${(d.tindakan || []).map(td => `
            <div class="flex justify-between items-center border p-2 rounded">
              <span>${td.nama}</span>
              <div x-show="role !== 'verifikator'" class="space-x-1">
                <button type="button" x-bind:disabled="role === 'verifikator'" onclick="updateSimulasi('tindakan','Primary','${td.nama}','', window.claimState.tab)"
                        class="bg-blue-600 text-white px-2 py-1 rounded text-xs">Pilih Utama</button>
                <button type="button" x-bind:disabled="role === 'verifikator'" onclick="updateSimulasi('tindakan','Secondary','${td.nama}','', window.claimState.tab)"
                        class="bg-blue-600 text-white px-2 py-1 rounded text-xs">Pilih Sekunder</button>
              </div>
            </div>
          `).join('')}
        </div>
      </section>

      <!-- Rawat Inap -->
      <section class="p-3 bg-gray-50 dark:bg-gray-700 rounded">
        <h4 class="font-semibold mb-2">Rawat Inap</h4>
        <ul class="list-disc list-inside space-y-1">
          <li><b>Indikasi:</b> ${d.rawat_inap?.indikasi || '-'}</li>
          <li><b>Lama Rawat:</b> ${d.rawat_inap?.lama_rawat || '-'}</li>
          <li><b>Perpanjangan:</b> ${d.rawat_inap?.perpanjangan || '-'}</li>
        </ul>
      </section>

      <!-- Faskes -->
      <section class="p-3 bg-gray-50 dark:bg-gray-700 rounded">
        <h4 class="font-semibold mb-2">Faskes</h4>
        <ul class="list-disc list-inside space-y-1">
          <li><b>Kesesuaian RS:</b> ${d.faskes?.kesesuaian_rs || '-'}</li>
        </ul>
      </section>

      <!-- Rujukan -->
      <section class="p-3 bg-gray-50 dark:bg-gray-700 rounded">
        <h4 class="font-semibold mb-2">Rujukan</h4>
        <ul class="list-disc list-inside space-y-1">
          <li><b>Syarat:</b> ${d.rujukan?.syarat || '-'}</li>
          <li><b>Kelayakan:</b> ${d.rujukan?.kelayakan || '-'}</li>
        </ul>
      </section>

    </div>
  `
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
  <div class="bg-white dark:bg-gray-700 rounded shadow-sm" x-data="{open:true}">
    <button type="button" @click="open=!open"
            class="w-full flex justify-between px-4 py-2 bg-gray-200 dark:bg-gray-600 font-semibold">
      <span>Hari ${idx+1} (${hari.tanggal || '-'})</span>
      <span x-show="open">⬆️</span><span x-show="!open">⬇️</span>
    </button>
    <div x-show="open" class="p-2 space-y-2">

      <!-- Diagnosis -->
      <div class="bg-white dark:bg-gray-700 rounded shadow-sm" x-data="{open:true}">
        <button type="button" @click="open=!open"
                class="w-full flex justify-between px-4 py-1 bg-gray-100 dark:bg-gray-600 font-semibold text-sm">
          <span>
            Diagnosis
            <span id="count-diagnosis-daily-${idx}"
            class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">
              ${(hari.diagnosis || []).length}
            </span>
          <span x-show="open">⬆️</span><span x-show="!open">⬇️</span>
        </button>
        <div x-show="open" class="p-2">
          <table class="w-full text-xs border">
            <thead class="bg-gray-100 dark:bg-gray-800">
              <tr>
                <th>Kategori</th><th>Klinis</th><th>ICD</th>
                <th>Tindakan</th><th>Score</th><th x-show="role === 'doctor'">Mapping</th>
              </tr>
            </thead>
            <tbody id="diagnosis-${dayId}"></tbody>
            <tbody id="diagnosis-manual-${dayId}">
            <tr class="manual-row bg-gray-50 dark:bg-gray-800">
              <td><input x-model="manualInput.daily['${dayId}'].diagnosis.kategori"
             placeholder="Nama penyakit"
             class="border px-2 py-1 w-full rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-400"></td>
              <td><input x-model="manualInput.daily['${dayId}'].diagnosis.klinis" placeholder="Klinis"
                        class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
              <td><input x-model="manualInput.daily['${dayId}'].diagnosis.icd" placeholder="ICD"
                        class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
              <td><input x-model="manualInput.daily['${dayId}'].diagnosis.tindakan" placeholder="Tindakan"
                        class="border px-2 py-1 w-full rounded bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
              <td><input x-model="manualInput.daily['${dayId}'].diagnosis.score" placeholder="Score"
                        class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
              <td>
                <button type="button" @click="addManual('diagnosis','${dayId}')"
                        class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400">➕</button>
              </td>
            </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Komorbid -->
      <div class="bg-white dark:bg-gray-700 rounded shadow-sm" x-data="{open:true}">
        <button type="button" @click="open=!open"
                class="w-full flex justify-between px-4 py-1 bg-gray-100 dark:bg-gray-600 font-semibold text-sm">
          <span>
            Komorbid
            <span id="count-komorbid-daily-${dayId}"
            class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">
              ${(hari.komorbid || []).length}
            </span>
          <span x-show="open">⬆️</span><span x-show="!open">⬇️</span>
        </button>
        <div x-show="open" class="p-2">
          <table class="w-full text-xs border">
            <thead class="bg-gray-100 dark:bg-gray-800">
              <tr>
                <th>Kategori</th><th>Klinis</th><th>ICD</th>
                <th>Tindakan</th><th>Score</th><th>Mapping</th>
              </tr>
            </thead>
            <tbody id="komorbid-${dayId}"></tbody>
            <tbody id="komorbid-manual-${dayId}">
            <tr class="manual-row bg-gray-50 dark:bg-gray-800">
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.kategori"
         placeholder="Nama penyakit"
         class="border px-2 py-1 w-full rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-400"></td>
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.klinis" placeholder="Klinis"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.icd" placeholder="ICD"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.tindakan" placeholder="Tindakan"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.score" placeholder="Score"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                <td>
                  <button type="button" @click="addManual('komorbid','${dayId}')"
                          class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400">➕</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Komplikasi -->
      <div class="bg-white dark:bg-gray-700 rounded shadow-sm" x-data="{open:true}">
        <button type="button" @click="open=!open"
                class="w-full flex justify-between px-4 py-1 bg-gray-100 dark:bg-gray-600 font-semibold text-sm">
          <span>
            Komplikasi
            <span id="count-komplikasi-daily-${dayId}"
            class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">
              ${(hari.komplikasi || []).length}
            </span>
          <span x-show="open">⬆️</span><span x-show="!open">⬇️</span>
        </button>
        <div x-show="open" class="p-2">
          <table class="w-full text-xs border">
            <thead class="bg-gray-100 dark:bg-gray-800">
              <tr>
                <th>Kategori</th><th>Klinis</th><th>ICD</th>
                <th>Tindakan</th><th>Score</th><th>Mapping</th>
              </tr>
            </thead>
            <tbody id="komplikasi-${dayId}"></tbody>
            <tbody id="komplikasi-manual-${dayId}">
            <tr class="manual-row bg-gray-50 dark:bg-gray-800">
                <td> <input x-model="manualInput.daily['${dayId}'].komplikasi.kategori"
         placeholder="Nama penyakit"
         class="border px-2 py-1 w-full rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-400"></td>
                <td><input x-model="manualInput.daily['${dayId}'].komplikasi.klinis" placeholder="Klinis"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                <td><input x-model="manualInput.daily['${dayId}'].komplikasi.icd" placeholder="ICD"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                <td><input x-model="manualInput.daily['${dayId}'].komplikasi.tindakan" placeholder="Tindakan"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                <td><input x-model="manualInput.daily['${dayId}'].komplikasi.score" placeholder="Score"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                <td>
                  <button type="button" @click="addManual('komplikasi','${dayId}')"
                          class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400">➕</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

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
    kategori: r.sim_text || "-",
    klinis: r.regulation_refs?.klinis || "-",
    icd: r.icd10_code || r.icd9_code || "-",
    tindakan: r.icd9_code || r.regulation_refs?.tindakan || "-",
    score: r.confidence_score || 0,
    child: r.regulation_refs?.child || false,
    name: r.sim_text || "-",  // biar updateSimulasi aman
    modal_detail: r.regulation_refs?.modal_detail || {}
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
