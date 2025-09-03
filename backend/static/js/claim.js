// ==================== Generate AI ====================
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

    // Admission
    renderTable("diagnosis-admission", data.admission?.diagnosis || [], "diagnosis", "admission")
    renderTable("komorbid-admission", data.admission?.komorbid || [], "komorbid", "admission")
    renderTable("komplikasi-admission", data.admission?.komplikasi || [], "komplikasi", "admission")
    renderTable("tindakan-admission", data.admission?.tindakan || [], "tindakan", "admission")
    state.simulasi.admission = data.admission?.simulasi || {}
    state.summary.admission = data.admission?.summary || {}

    // Daily
    renderTable("diagnosis-daily", data.daily?.diagnosis || [], "diagnosis", "daily")
    renderTable("komorbid-daily", data.daily?.komorbid || [], "komorbid", "daily")
    renderTable("komplikasi-daily", data.daily?.komplikasi || [], "komplikasi", "daily")
    state.simulasi.daily = data.daily?.simulasi || {}
    state.summary.daily = data.daily?.summary || {}

    // Discharge
    renderTable("diagnosis-discharge", data.discharge?.diagnosis || [], "diagnosis", "discharge")
    renderTable("komorbid-discharge", data.discharge?.komorbid || [], "komorbid", "discharge")
    renderTable("komplikasi-discharge", data.discharge?.komplikasi || [], "komplikasi", "discharge")
    renderTable("tindakan-discharge", data.discharge?.tindakan || [], "tindakan", "discharge")
    state.simulasi.discharge = data.discharge?.simulasi || {}
    state.summary.discharge = data.discharge?.summary || {}

    // kirim rekomendasi ke Alpine (panel kanan)
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
function renderTable(id, items, type, tab) {
  const tb = document.getElementById(id)
  if (!tb) return
  if (!items || !Array.isArray(items)) items = []

  const sourceMap = {
    diagnosis: "Utama Klinis",
    komorbid: "Komorbid",
    komplikasi: "Komplikasi",
    tindakan: "Tindakan"
  }
  const sourceLabel = sourceMap[type] || type

  tb.innerHTML = items.map(it => `
    <tr>
      <td class="${it.child ? 'pl-6' : ''}"
          data-item='${JSON.stringify({ ...it, tab }).replace(/"/g,"&quot;")}'
          onclick="openModalFromAttr(this)">
        ${it.kategori || "-"}
      </td>
      <td>${it.klinis || "-"}</td>
      <td>${it.icd || "-"}</td>
      <td>${it.tindakan || "-"}</td>
      <td>${it.score != null ? confidenceBadge(it.score) : "-"}</td>
      <td>
        ${type !== "tindakan" ? `
        <select x-bind:disabled="role === 'verifikator'"onchange="updateSimulasi('diagnosis',this.value,{name:'${it.kategori}',label:'${sourceLabel}'},'${sourceLabel}','${tab}')"
                class='border rounded px-1 text-xs bg-gray-100 dark:bg-gray-700'>
          <option selected>Pilih</option>
          <option value="Primary">Diagnosis Utama</option>
          <option value="Secondary-Komorbid">Komorbid</option>
          <option value="Secondary-Komplikasi">Komplikasi</option>
          <option value="None">None</option>
        </select>` : "-"}
      </td>
    </tr>
  `).join('')

  // update badge jumlah
  const countEl = document.getElementById("count-" + id)
  if (countEl) countEl.textContent = items.length
}

// ==================== Modal ====================
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
  if (!tab) tab = 'admission'
  opt = normalizeOpt(opt)
  const sim = state.simulasi[tab]

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
  if (type === 'diagnosis') {
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

async function simpanFinal() {
  const state = Alpine.$data(document.getElementById('claimRoot'))

  // TODO: ganti claimId sesuai klaim aktif (misalnya ambil dari hidden input / URL)
  const claimId = state.currentClaimId || 1234  

  const payload = {
    simulasi: state.simulasi,
    summary: state.summary
  }

  try {
    const res = await fetch(`/claims/${claimId}/finalize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })

    if (res.ok) {
      // redirect ke dashboard (atau klaim detail)
      window.location.href = "/dashboard"
    } else {
      const err = await res.json()
      alert("Gagal simpan final: " + err.detail)
    }
  } catch (e) {
    console.error(e)
    alert("Error simpan final")
  }
}

async function saveDraft() {
  const state = Alpine.$data(document.getElementById('claimRoot'))
  const claimId = state.currentClaimId || document.getElementById("claimRoot").dataset.claimId

  const payload = {
    simulasi: state.simulasi,
    summary: state.summary
  }

  try {
    const res = await fetch(`/claims/${claimId}/update-draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
    if (res.ok) {
      alert("✅ Draft klaim berhasil disimpan")
    } else {
      const err = await res.json()
      alert("❌ Gagal simpan draft: " + (err.detail || "Unknown error"))
    }
  } catch (e) {
    console.error("Save Draft error:", e)
    alert("❌ Error koneksi")
  }
}

function claimData(init) {
  return {
    role: init.role,
    tab: 'admission',
    simulasi: init.simulasi,
    summary: init.summary,
    recommendations: { medis:[], regulasi:[], tarif:[] },
    modalOpen: false,
    modalTitle: '',
    modalContent: '',
    init(){
      window.addEventListener('update-rekom', e => {
        this.recommendations = e.detail
      })
    },
    openModal(e){
      this.modalOpen = true
      this.modalTitle = e.detail.title
      this.modalContent = e.detail.content
    },
    statusIcon(s){
      if(s==='valid') return "✅"
      if(s==='warning') return "⚠️"
      if(s==='invalid') return "❌"
      return ""
    },
    confidenceBadge(val){
      val=parseInt(val)
      let c=val>=80?'bg-green-600':val>=60?'bg-yellow-500':'bg-red-600'
      return `<span class="px-2 py-0.5 rounded text-white text-xs ${c}">${val}%</span>`
    }
  }
}
