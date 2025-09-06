// ==================== Generate AI ====================
// Export hasil simulasi ke PDF
document.addEventListener('DOMContentLoaded', function() {
  const btn = document.getElementById('download-pdf');
  if (btn) {
    btn.addEventListener('click', function() {
      // Pilih panel hasil simulasi (kanan)
      var element = document.querySelector('.bg-white.rounded-xl.shadow-sm.p-4.sticky.top-6');
      if (element) {
        html2pdf().set({
          margin: 0.5,
          filename: 'claim_simulasi.pdf',
          image: { type: 'jpeg', quality: 0.98 },
          html2canvas: { scale: 2 },
          jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' }
        }).from(element).save();
      }
    });
  }
});
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
  // Ambil data rekam medis dari form
  const patient_uuid = document.getElementById('patient_uuid')?.value || "1";
  const visit_uuid = document.getElementById('visit_uuid')?.value || "10";
  const keluhan = document.getElementById('keluhan')?.value || "";
  const riwayat_penyakit = document.getElementById('riwayat_penyakit')?.value || "";
  const diagnosis_akhir = document.getElementById('diagnosis_akhir')?.value || "";
  const tindakan = document.getElementById('tindakan')?.value || "";
  const obat = document.getElementById('obat')?.value || "";

  // Request ke core_engine
  try {
    // 1. Diagnosis, Komorbid, Komplikasi
    const ddxRes = await fetch("http://localhost:8002/predict_ddx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patient_uuid, visit_uuid, keluhan, riwayat_penyakit, diagnosis_akhir, tindakan, obat })
    });
    const ddxData = await ddxRes.json();
    renderTable("diagnosis-admission", ddxData.diagnosis || [], "diagnosis", "admission");
    renderTable("komorbid-admission", ddxData.komorbid || [], "komorbid", "admission");
    renderTable("komplikasi-admission", ddxData.komplikasi || [], "komplikasi", "admission");

    // 2. Simulasi Klaim & Summary
    // Ambil diagnosis utama, sekunder, tindakan dari hasil ddx (atau dari user input)
    const primary = ddxData.diagnosis?.[0]?.klinis || "";
    const secondary = ddxData.komorbid?.map(k => k.klinis) || [];
    const procedures = [ddxData.diagnosis?.[0]?.tindakan || ""];
    const claimRes = await fetch("http://localhost:8002/analyze_claim", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ primary, secondary, procedures })
    });
    const claimData = await claimRes.json();
    const state = Alpine.$data(document.getElementById('claimRoot'));
    // Map tindakan dari backend ke panel tindakan
    state.simulasi.admission = {
      utama: state.simulasi.admission.utama,
      sekunder: state.simulasi.admission.sekunder,
      tindakanUtama: claimData.simulasi?.tindakan_utama || null,
      tindakanSekunder: claimData.simulasi?.tindakan_sekunder || [],
      tarifDraft: claimData.simulasi?.tarif_draft || null
    };
    state.summary.admission = claimData.summary || {};

    // Render Saran Simulasi panel
    renderSaranSimulasi('admission', claimData.summary);

    // 3. Rekomendasi Kombinasi
    const combosRes = await fetch("http://localhost:8002/generate_claim_combos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patient_uuid, visit_uuid, keluhan, riwayat_penyakit, diagnosis_akhir, tindakan, obat })
    });
    const combosData = await combosRes.json();
      // Map rekomendasi to recommendations Alpine state for saran simulasi panel
    // Hitung total tarif keseluruhan dari rekomendasi (valid+warning)
    let totalTarif = 0;
    if (combosData.rekomendasi) {
      combosData.rekomendasi.forEach(rec => {
        if (rec.status === 'valid' || rec.status === 'warning') {
          totalTarif += rec.tarif_draft || 0;
        }
      });
    }
    // Tampilkan total di bawah panel saran simulasi
    const totalEl = document.getElementById('total-tarif-simulasi');
    if (totalEl) {
      totalEl.textContent = 'Total Tarif Simulasi: Rp' + totalTarif.toLocaleString();
    }
      const state2 = Alpine.$data(document.getElementById('claimRoot'));
      // Transform combosData.rekomendasi into categories for recommendations panel
      if (combosData.rekomendasi) {
        // Example: group by status (valid, warning, invalid)
        const recs = { valid: [], warning: [], invalid: [] };
        combosData.rekomendasi.forEach(rec => {
          const cat = rec.status || 'valid';
          recs[cat] = recs[cat] || [];
          recs[cat].push({
            target: [rec.diagnosis_utama, ...(rec.diagnosis_sekunder || []), rec.tindakan_utama].filter(Boolean),
            message: `Tarif: Rp${rec.tarif_draft?.toLocaleString()}`,
            status: rec.status,
            confidence: 0.95 // Dummy confidence, adjust if backend provides
          });
        });
        state2.recommendations = recs;
      }
    // Bisa digunakan untuk panel rekomendasi atau simulasi lain
// Render Saran Simulasi panel
function renderSaranSimulasi(tab, summary) {
  if (!summary) return;
  const medisEl = document.getElementById(`saran-medis-${tab}`);
  const regulasiEl = document.getElementById(`saran-regulasi-${tab}`);
  const tarifEl = document.getElementById(`saran-tarif-${tab}`);
  if (medisEl) medisEl.textContent = (summary.medis || []).join("; ");
  if (regulasiEl) regulasiEl.textContent = (summary.regulasi || []).join("; ");
  if (tarifEl) tarifEl.textContent = (summary.tarif || []).join("; ");
}

  } catch (err) {
    console.error("Error generate AI:", err);
    alert("Gagal generate AI");
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

async function openModalFromAttr(el) {
  const it = JSON.parse(el.dataset.item)
  // Request detail ke backend
  try {
    const res = await fetch("http://localhost:8002/analyze_diagnosis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ diagnosis_text: it.klinis })
    })
    const detail = await res.json()
    openModal(it.kategori, buildModalContent({ ...it, modal_detail: detail }))
  } catch (err) {
    openModal(it.kategori, '<div class="text-red-500">Gagal mengambil detail diagnosis</div>')
  }
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

// Export hasil simulasi ke PDF
document.addEventListener('DOMContentLoaded', function() {
  var btn = document.getElementById('download-pdf');
  if (btn) {
    btn.addEventListener('click', function() {
      // Pilih parent container panel kanan (simulasi klaim)
      var panel = btn.closest('.lg\:col-span-1');
      if (!panel) {
        panel = document.querySelector('.bg-white.rounded-xl.shadow-sm.p-4.sticky.top-6');
      }
      if (!panel) {
        alert('Panel hasil simulasi tidak ditemukan!');
        return;
      }
      // Clone panel agar dropdown/select tidak ikut
      var clone = panel.cloneNode(true);
      clone.querySelectorAll('select').forEach(function(sel){ sel.style.display='none'; });
      clone.querySelectorAll('button').forEach(function(b){ b.style.display='none'; });
      var tempDiv = document.createElement('div');
      tempDiv.style.position = 'fixed';
      tempDiv.style.left = '-9999px';
      tempDiv.appendChild(clone);
      document.body.appendChild(tempDiv);
      html2pdf().set({
        margin: 0.5,
        filename: 'claim_simulasi.pdf',
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' }
      }).from(clone).save().then(function(){
        document.body.removeChild(tempDiv);
      });
    });
  }
});

function confidenceBadge(val){
  val=parseInt(val)
  let c=val>=80?'bg-green-600':val>=60?'bg-yellow-500':'bg-red-600'
  return `<span class="px-2 py-0.5 rounded text-white text-xs ${c}">${val}%</span>`
}

async function simpanFinal() {
  const state = Alpine.$data(document.getElementById('claimRoot'))

  // TODO: ganti claimId sesuai klaim aktif (misalnya ambil dari hidden input / URL)
  const claimId = state.currentClaimId || document.getElementById("claimRoot").dataset.claimId  

  // Ambil UUID dari hidden input atau Alpine state
  const patient_uuid = document.getElementById('patient_uuid')?.value || state.patient_uuid || null;
  const visit_uuid = document.getElementById('visit_uuid')?.value || state.visit_uuid || null;
  const payload = {
    simulasi: state.simulasi,
    summary: state.summary,
    patient_uuid,
    visit_uuid
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
