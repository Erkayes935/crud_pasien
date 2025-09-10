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
      daily: {} // akan diisi dinamis pakai dayId
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
    if (!state.manualInput.daily[dayId]) {
      state.manualInput.daily[dayId] = {
        diagnosis: { kategori:"", klinis:"", icd:"", tindakan:"" },
        komorbid:  { kategori:"", klinis:"", icd:"", tindakan:"" },
        komplikasi:{ kategori:"", klinis:"", icd:"", tindakan:"" }
      }
    }

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
                  <td><input x-model="manualInput.daily['${dayId}'].diagnosis.kategori" :value="manualInput.daily[dayId].diagnosis.kategori" placeholder="Nama penyakit"
                            class="border px-2 py-1 w-full rounded 
                                    bg-white dark:bg-gray-700 
                                    text-gray-900 dark:text-gray-100 
                                    focus:ring-2 focus:ring-blue-400" @click="openModalFromAttr(item)"></td>
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
                    <button @click="addManual('diagnosis','${dayId}')"
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
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.kategori" placeholder="Komorbid"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" @click="openModalFromAttr(item)"></td>
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.klinis" placeholder="Klinis"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400 readonly"></td>
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.icd" placeholder="ICD"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400 readonly"></td>
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.tindakan" placeholder="Tindakan"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400 readonly"></td>
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.score" placeholder="Score"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400 readonly"></td>
                <td>
                  <button @click="addManual('komorbid','${dayId}')"
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
                  <td><input x-model="manualInput.daily['${dayId}'].komplikasi.kategori" placeholder="Komplikasi"
                            class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" @click="openModalFromAttr(item)"></td>
                  <td><input x-model="manualInput.daily['${dayId}'].komplikasi.klinis" placeholder="Klinis"
                            class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400 readonly"></td>
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
                    <button @click="addManual('komplikasi','${dayId}')"
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
    renderTable(`diagnosis-${dayId}`, hari.diagnosis || [], "diagnosis", "daily", dayId)
    renderTable(`komorbid-${dayId}`, hari.komorbid || [], "komorbid", "daily", dayId)
    renderTable(`komplikasi-${dayId}`, hari.komplikasi || [], "komplikasi", "daily", dayId)
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
  const state = Alpine.$data(document.getElementById('claimRoot'))  // ✅ ambil Alpine state
  if (!state.simulasi[tab]) {
    state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [], tindakan: [] }
  }

  // force isi array di state
  if (!Array.isArray(state.simulasi[tab][type])) {
    state.simulasi[tab][type] = []
  }
  state.simulasi[tab][type].splice(
    0,
    state.simulasi[tab][type].length,
    ...(items || []).map(it => ({
      ...it,
      mapping: it.mapping || ""
    }))
  )

  const target = document.getElementById(targetId)
  if (!target) return

  // render semua item AI/rekomendasi
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


  // update counter di header
  let counterId = dayId ? `count-${type}-${dayId}` : `count-${type}-${tab}`
  const countEl = document.getElementById(counterId)
  if (countEl) countEl.textContent = items.length

  console.log("✅ renderTable synced", tab, type, state.simulasi[tab][type])
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
    return { name: val.split(" [")[0] || "-", label: "" }
  }
  return {
    name: val.name || val.kategori || val.icd || "-",
    label: val.label || "",
  }
}


function updateSimulasi(type, opt, value, source, tab) {
  const state = Alpine.$data(document.getElementById("claimRoot"));
  if (!tab) tab = "admission";
  opt = normalizeOpt(opt);

  let sim = state.simulasi[tab];
  if (!sim || typeof sim !== "object" || Array.isArray(sim)) {
    sim = { utama: null, sekunder: [], tindakanUtama: null, tindakanSekunder: [], tarifDraft: null };
    state.simulasi[tab] = sim;
  }

  if (!Array.isArray(sim.sekunder)) sim.sekunder = [];
  if (!("utama" in sim)) sim.utama = null;
  if (!("tindakanUtama" in sim)) sim.tindakanUtama = null;
  if (!Array.isArray(sim.tindakanSekunder)) sim.tindakanSekunder = [];

  const item = typeof value === "string"
    ? { name: value.split(" [")[0], label: "" }
    : { name: value.name, label: value.label || "" };

  if (source) {
    if (opt === "Primary") item.label = "Utama Klinis";
    else if (opt === "Secondary-Komorbid") item.label = "Komorbid";
    else if (opt === "Secondary-Komplikasi") item.label = "Komplikasi";
  }

  // Diagnosis, Komorbid, Komplikasi
  if (type === "diagnosis" || type === "komorbid" || type === "komplikasi") {
    if (opt === "Primary") {
      const oldPrimary = sim.utama;
      sim.sekunder = sim.sekunder.filter(dx => dx.name !== item.name);
      sim.utama = item;
      if (oldPrimary && oldPrimary.name !== item.name) sim.sekunder.unshift(oldPrimary);
    } else if (opt.startsWith("Secondary")) {
      if (sim.utama && sim.utama.name === item.name) sim.utama = null;
      const idx = sim.sekunder.findIndex(dx => dx.name === item.name);
      if (idx === -1) sim.sekunder.push(item);
      else sim.sekunder[idx] = item;
    } else if (opt === "None") {
      if (sim.utama && sim.utama.name === item.name) sim.utama = null;
      sim.sekunder = sim.sekunder.filter(dx => dx.name !== item.name);
    }
  }

  // Tindakan
  if (type === "tindakan") {
    const nama = typeof value === "string" ? value : value.name;
    if (opt === "Primary") {
      const oldPrimary = sim.tindakanUtama;
      sim.tindakanSekunder = sim.tindakanSekunder.filter(td => td.name !== nama);
      sim.tindakanUtama = { name: nama };
      if (oldPrimary && oldPrimary.name !== nama) sim.tindakanSekunder.unshift(oldPrimary);
    } else if (opt === "Secondary") {
      if (sim.tindakanUtama?.name === nama) sim.tindakanUtama = null;
      if (!sim.tindakanSekunder.find(td => td.name === nama)) {
        sim.tindakanSekunder.push({ name: nama });
      }
    } else if (opt === "None") {
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
              <td><input x-model="manualInput.daily['${dayId}'].diagnosis.kategori" placeholder="Nama penyakit"
                        class="border px-2 py-1 w-full rounded 
                                bg-white dark:bg-gray-700 
                                text-gray-900 dark:text-gray-100 
                                focus:ring-2 focus:ring-blue-400" @click="openModalFromAttr(item)"></td>
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
                <button @click="addManual('diagnosis','${dayId}')"
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
            <span id="count-komorbid-daily-${idx}"
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
                <td><input x-model="manualInput.daily['${dayId}'].komorbid.kategori" placeholder="Komorbid"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" @click="openModalFromAttr(item)"></td>
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
                  <button @click="addManual('komorbid','${dayId}')"
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
            <span id="count-komplikasi-daily-${idx}"
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
                <td><input x-model="manualInput.daily['${dayId}'].komplikasi.kategori" placeholder="Komplikasi"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" @click="openModalFromAttr(item)"></td>
                <td><input x-model="manualInput.daily['${dayId}'].komplikasi.klinis" placeholder="Klinis"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400" readonly></td>
                <td><input x-model="manualInput.daily['${dayId}'].komplikasi.icd" placeholder="ICD"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400 readonly"></td>
                <td><input x-model="manualInput.daily['${dayId}'].komplikasi.tindakan" placeholder="Tindakan"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400 readonly"></td>
                <td><input x-model="manualInput.daily['${dayId}'].komplikasi.score" placeholder="Score"
                           class="border px-2 py-1 w-full rounded 
       bg-white dark:bg-gray-700 
       text-gray-900 dark:text-gray-100 
       focus:ring-2 focus:ring-blue-400 readonly"></td>
                <td>
                  <button @click="addManual('komplikasi','${dayId}')"
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

      renderTable(`diagnosis-${dayId}`, (hari.diagnosis || []).map(mapRecommendation), "diagnosis", "daily")
      renderTable(`komorbid-${dayId}`, (hari.komorbid || []).map(mapRecommendation), "komorbid", "daily")
      renderTable(`komplikasi-${dayId}`, (hari.komplikasi || []).map(mapRecommendation), "komplikasi", "daily")
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


function addManual(type, tab) {
  const state = Alpine.$data(document.getElementById('claimRoot'))

  if (!state.simulasi[tab]) {
    state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [], tindakan: [] }
  }
  if (!Array.isArray(state.simulasi[tab][type])) {
    state.simulasi[tab][type] = []
  }
  
  let input
  if (tab.startsWith("daily-")) {
    input = state.manualInput.daily[tab][type]
  } else {
    input = state.manualInput[tab][type]
  }


  // Buat object baru dari input manual
  // PERBAIKAN
  const newItem = {
    name: input.kategori || "-",
    kategori: input.kategori || "",
    klinis: input.klinis || "-",
    icd: input.icd || "-",
    tindakan: input.tindakan || "-",
    score: 0,
    mapping: ""
  }


  // Masukkan ke simulasi
  state.simulasi[tab][type].push(newItem)

  const manualBody = document.getElementById(`${type}-manual-${tab}`)
  manualBody.insertAdjacentHTML("beforeend", `
    <tr class="bg-gray-50 dark:bg-gray-800">
      <td>${newItem.kategori}</td>
      <td>${newItem.klinis}</td>
      <td>${newItem.icd}</td>
      <td>${newItem.tindakan}</td>
      <td>${newItem.score}</td>
      <td>-</td>
    </tr>
  `)

  // Reset input manual (jangan ganti object)
  // PERBAIKAN
  if (tab.startsWith("daily-")) {
  state.manualInput.daily[tab][type] = { kategori:"", klinis:"", icd:"", tindakan:"", score:"" }
  } else {
    state.manualInput[tab][type] = { kategori:"", klinis:"", icd:"", tindakan:"", score:"" }
  }

  // Trigger AI recommendation
  fetch("/ai/recommendation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kategori: newItem.kategori })
  })
  .then(res => res.json())
  .then(data => {
    const idx = state.simulasi[tab][type].length - 1
    state.simulasi[tab][type][idx].klinis   = data.klinis   || state.simulasi[tab][type][idx].klinis
    state.simulasi[tab][type][idx].icd      = data.icd      || state.simulasi[tab][type][idx].icd
    state.simulasi[tab][type][idx].tindakan = data.tindakan || state.simulasi[tab][type][idx].tindakan
    state.simulasi[tab][type][idx].score    = data.score    ?? state.simulasi[tab][type][idx].score
  })
  .catch(err => console.error("AI recommendation failed", err))
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
  updateSimulasi("diagnosis", opt, normalizeItem(item), "AI", tab)
}