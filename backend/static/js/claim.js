// ==================== Generate AI ====================
function claimData(init) {
  return {
    role: init.role || 'doctor', // doctor, verifikator, coder
    tab: init.tab || 'admission',
    simulasi: init.sim || {
      admission: { utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null },
      daily: { utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null },
      discharge: { utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null }
    },
    summary: init.summ || {
      admission: { klinis:[], regulasi:[], tarif:[] },
      daily: { klinis:[], regulasi:[], tarif:[] },
      discharge: { klinis:[], regulasi:[], tarif:[] }
    },
    recommendations: { medis:[], regulasi:[], tarif:[] },
    modalOpen: false,
    modalTitle: '',
    modalContent: '',
    init(){
      window.addEventListener('update-rekom', e => {
        this.recommendations = e.detail
      })
    },
    statusIcon(s){
      if(s==='valid') return "✅"
      if(s==='warning') return "⚠️"
      if(s==='invalid') return "❌"
      return ""
    },
  }
}
async function generateAI() {
  const payload = {
    patient_id: 1,
    visit_id: 10,
    context: "all",
    notes: "dummy generate"
  }

  try {
    const res = await fetch("/ai/recommendation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
    const data = await res.json()
    const state = Alpine.$data(document.getElementById('claimRoot'))

    // === Admission ===
    renderTable("diagnosis-admission", data.admission?.diagnosis || [], "diagnosis", "admission")
    renderTable("komorbid-admission", data.admission?.komorbid || [], "komorbid", "admission")
    renderTable("komplikasi-admission", data.admission?.komplikasi || [], "komplikasi", "admission")
    state.simulasi.admission = data.admission?.simulasi || {}
    state.summary.admission = data.admission?.summary || {}

    // === Daily ===
    if (Array.isArray(data.daily)) {
  const dailyContainer = document.getElementById("daily-accordion")
  dailyContainer.innerHTML = ""  // reset

  data.daily.forEach((hari, idx) => {
    const dayId = `daily-${idx}`

    // bikin accordion section baru
dailyContainer.insertAdjacentHTML("beforeend", `
  <div class="bg-white dark:bg-gray-700 rounded shadow-sm" x-data="{open:true}">
    <button @click="open=!open"
            class="w-full flex justify-between px-4 py-2 bg-gray-200 dark:bg-gray-600 font-semibold">
      <span>Hari ${idx+1} (${hari.tanggal || '-'})</span>
      <span x-show="open">⬆️</span><span x-show="!open">⬇️</span>
    </button>
    <div x-show="open" class="p-2 space-y-2">

      ${['Diagnosis','Komorbid','Komplikasi'].map(acc => `
        <div class="bg-white dark:bg-gray-700 rounded shadow-sm" x-data="{open:true}">
          <button @click="open=!open"
                  class="w-full flex justify-between px-4 py-1 bg-gray-100 dark:bg-gray-600 font-semibold text-sm">
            <span>${acc}</span>
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
              <tbody id="${acc.toLowerCase()}-${dayId}"></tbody>
            </table>
          </div>
        </div>
      `).join('')}

    </div>
  </div>
`)
    const tmpl = document.getElementById("daily-form-template")
    if (tmpl) {
      const clone = tmpl.content.cloneNode(true)
      dailyContainer.lastElementChild.querySelector(".p-2.space-y-2").appendChild(clone)
    }
    // render tabel per bagian
    renderTable(`diagnosis-${dayId}`, hari.diagnosis || [], "diagnosis", "daily")
    renderTable(`komorbid-${dayId}`, hari.komorbid || [], "komorbid", "daily")
    renderTable(`komplikasi-${dayId}`, hari.komplikasi || [], "komplikasi", "daily")
      })
    } else {
      // fallback lama kalau backend masih kirim 1 blok
      renderTable("diagnosis-daily", data.daily?.diagnosis || [], "diagnosis", "daily")
      renderTable("komorbid-daily", data.daily?.komorbid || [], "komorbid", "daily")
      renderTable("komplikasi-daily", data.daily?.komplikasi || [], "komplikasi", "daily")
    }
    state.simulasi.daily = {
      utama: (data.daily[0] && data.daily[0].utama) || null,
      sekunder: data.daily.flatMap(d => d.sekunder || []),
      tindakanUtama: (data.daily[0] && data.daily[0].tindakanUtama) || null,
      tindakanSekunder: data.daily.flatMap(d => d.tindakanSekunder || []),
      tarifDraft: null
    }
    state.summary.daily = {
      klinis: data.daily.flatMap(d => d.summary?.klinis || []),
      regulasi: data.daily.flatMap(d => d.summary?.regulasi || []),
      tarif: data.daily.flatMap(d => d.summary?.tarif || [])
    }


    // === Discharge ===
    renderTable("diagnosis-discharge", data.discharge?.diagnosis || [], "diagnosis", "discharge")
    renderTable("komorbid-discharge", data.discharge?.komorbid || [], "komorbid", "discharge")
    renderTable("komplikasi-discharge", data.discharge?.komplikasi || [], "komplikasi", "discharge")
    state.simulasi.discharge = data.discharge?.simulasi || {}
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
function renderTable(targetId, data, type, tab) {
  const target = document.getElementById(targetId)
  if (!target) return

  // ambil role dari Alpine
  const state = Alpine.$data(document.getElementById('claimRoot'))
  const role = state.role

  // amanin data supaya array
  const rows = (data || []).map(it => {
    const sourceLabel = type.charAt(0).toUpperCase() + type.slice(1)
    return `
      <tr class="odd:bg-gray-50 dark:odd:bg-gray-900 hover:bg-gray-200 dark:hover:bg-gray-600">
        <td ${ (type === "diagnosis" || type === "komorbid" || type === "komplikasi")
      ? `data-item='${JSON.stringify({...it, tab})}' onclick="openModalFromAttr(this)" class="text-blue-600 underline cursor-pointer"`
      : "" }>${it.kategori || "-"}</td>
        <td>${it.klinis || "-"}</td>
        <td>${it.icd || "-"}</td>
        <td>${it.tindakan || "-"}</td>
        <td>${it.score ?? "-"}</td>
        <td>
          <select ${role === 'doctor' ? '' : 'disabled'}
                  onchange="updateSimulasi('${type}', this.value, {name:'${it.kategori}', label:'${sourceLabel}'}, '${sourceLabel}', '${tab}')"
                  class="border rounded px-1 text-xs bg-gray-100 dark:bg-gray-700">
            <option value="">Pilih</option>
            <option value="Diagnosis Utama">Diagnosis Utama</option>
            <option value="Komorbid">Komorbid</option>
            <option value="Komplikasi">Komplikasi</option>
            <option value="None">None</option>
          </select>
        </td>
      </tr>
    `
  }).join("")

  target.innerHTML = rows

  // update badge jumlah
  const countEl = document.getElementById("count-" + targetId)
  if (countEl) countEl.textContent = (data || []).length
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
              <div class="space-x-1">
                <button x-bind:disabled="role === 'verifikator'" onclick="updateSimulasi('tindakan','Primary','${td.nama}','', '${it.tab || 'admission'}')"
                        class="bg-blue-600 text-white px-2 py-1 rounded text-xs">Pilih Utama</button>
                <button x-bind:disabled="role === 'verifikator'" onclick="updateSimulasi('tindakan','Secondary','${td.nama}','', '${it.tab || 'admission'}')"
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

function updateSimulasi(type, opt, value, source, tab) {
  const state = Alpine.$data(document.getElementById('claimRoot'))
  const role = state.role
  if (!tab) tab = 'admission'
  opt = normalizeOpt(opt)
  console.log("updateSimulasi", { type, opt, tab, current: state.simulasi[tab] })
  let sim = state.simulasi[tab]
  if (!sim || typeof sim !== 'object' || Array.isArray(sim)) {
    sim = { utama:null, sekunder:[], tindakanUtama:null, tindakanSekunder:[], tarifDraft:null }
    state.simulasi[tab] = sim
  }

  if (!Array.isArray(sim.sekunder)) sim.sekunder = []
  if (!('utama' in sim)) sim.utama = null
  if (!('tindakanUtama' in sim)) sim.tindakanUtama = null
  if (!Array.isArray(sim.tindakanSekunder)) sim.tindakanSekunder = []
  if (!('tarifDraft' in sim)) sim.tarifDraft = null
  // pastikan object {name,label}
  const item = (typeof value === 'string')
    ? { name: value.split(' [')[0], label: '' }
    : { name: value.name, label: value.label || '' }

  // mapping label berdasar dropdown mapping (accordion kiri)
  if (source) {
    if (opt === "Primary") item.label = "Utama Klinis"
    else if (opt === "Secondary-Komorbid") item.label = "Komorbid"
    else if (opt === "Secondary-Komplikasi") item.label = "Komplikasi"
  }

  // ========== DIAGNOSIS ==========
  if (type === 'diagnosis' || type === 'komorbid' || type === 'komplikasi') {
  const sim = state.simulasi[tab]  // admission / daily / discharge
    if (opt === "Primary") {
      const oldPrimary = sim.utama
      sim.sekunder = sim.sekunder.filter(dx => dx.name !== item.name)
      sim.utama = item
      if (oldPrimary && oldPrimary.name !== item.name) {
        sim.sekunder.unshift(oldPrimary)
      }
    }
    else if (opt === "Secondary" || opt === "Secondary-Komorbid" || opt === "Secondary-Komplikasi") {
      if (sim.utama && sim.utama.name === item.name) sim.utama = null
      const idx = sim.sekunder.findIndex(dx => dx.name === item.name)
      if (idx === -1) sim.sekunder.push(item)
      else sim.sekunder[idx] = item
    }
    else if (opt === "None") {
      if (sim.utama && sim.utama.name === item.name) sim.utama = null
      sim.sekunder = sim.sekunder.filter(dx => dx.name !== item.name)
    }
  }

  // ========== TINDAKAN ==========
  if (type === 'tindakan') {
    if (opt === "Primary") {
      const oldPrimary = sim.tindakanUtama
      sim.tindakanSekunder = sim.tindakanSekunder.filter(td => td !== item.name)
      sim.tindakanUtama = item.name
      if (oldPrimary && oldPrimary !== item.name) {
        sim.tindakanSekunder.unshift(oldPrimary)
      }
    }
    else if (opt === "Secondary") {
      if (sim.tindakanUtama === item.name) sim.tindakanUtama = ''
      if (!sim.tindakanSekunder.includes(item.name)) {
        sim.tindakanSekunder.push(item.name)
      }
    }
    else if (opt === "None") {
      if (sim.tindakanUtama === item.name) sim.tindakanUtama = ''
      sim.tindakanSekunder = sim.tindakanSekunder.filter(td => td !== item.name)
    }
  }
}

// ==================== Helpers ====================

function confidenceBadge(val){
  val=parseInt(val)
  let c=val>=80?'bg-green-600':val>=60?'bg-yellow-500':'bg-red-600'
  return `<span class="px-2 py-0.5 rounded text-white text-xs ${c}">${val}%</span>`
}