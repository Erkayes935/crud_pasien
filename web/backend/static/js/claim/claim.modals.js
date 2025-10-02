// =============== Semua modal (diagnosis/procedure/regulasi) ===============

(function () {
  function openModal(title, content, { hideDefaultClose = false } = {}) {
    const root = document.getElementById('claimRoot');
    const state = Alpine.$data(root);
    state.modalOpen = true;
    state.modalTitle = title;
    state.modalContent = content;
    state.hideDefaultClose = hideDefaultClose;
  }

  function updateRingkasanFromRow(itemId, dx) {
    if (!dx || !itemId) return;

    const row = document.querySelector(`[data-id="${itemId}"]`);
    if (!row) return;

    // kolom Klinis
    const klinisCell = row.querySelector(".col-klinis");
    if (klinisCell) {
      let text = "";
      if (Array.isArray(dx.klinis)) text = dx.klinis.filter(Boolean).join(", ");
      else if (typeof dx.klinis === "string") text = dx.klinis;
      else if (typeof dx.klinis === "object" && dx.klinis !== null) {
        text = [dx.klinis.justifikasi, dx.klinis.bukti_klinis, dx.klinis.syarat_klinis].filter(Boolean).join(", ");
      }
      klinisCell.innerHTML = text ? `<span title="${text}">${truncateText(text, 44)}</span>` : "-";
    }

    // kolom ICD
    const icdCell = row.querySelector(".col-icd");
    if (icdCell) {
      if (dx.icd10_code) icdCell.innerText = dx.icd10_code;
      else if (dx.icd10 && dx.icd10.kode_icd) icdCell.innerText = dx.icd10.kode_icd;
      else if (dx.icd9_code) icdCell.innerText = dx.icd9_code;
      else icdCell.innerText = "-";
    }

    // kolom Tindakan
    const tindakanCell = row.querySelector(".col-tindakan");
    if (tindakanCell) {
      if (dx.tindakan && dx.tindakan.length > 0) {
        const text = dx.tindakan.map(t => t.procedure_text || t.tindakan).join(", ");
        tindakanCell.innerHTML = `<span title="${text}">${truncateText(text, 44)}</span>`;
      } else {
        tindakanCell.innerText = "-";
      }
    }
  }

  // Buka modal dari klik kategori
  async function openModalFromAttr(el, type) {
    const tr = el.closest("tr");
    const uiId = tr?.dataset.id;
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return alert("❌ Claim ID tidak ditemukan.");

    const name = (el.textContent || "").replace(/^→+\s*/, "").trim();
    if (!name) return;

    try {
      let dx;
      if (["diagnosis","komorbid","komplikasi"].includes(type)) {
        const res = await fetch(`/claims/${claimId}/analyze_diagnosis`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ disease_name: name })
        });
        dx = await res.json();
      } else if (type === "procedure") {
        const res = await fetch(`/claims/${claimId}/analyze_procedure`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ procedure_name: name })
        });
        dx = await res.json();
      } else {
        dx = tr?.dataset.row ? JSON.parse(tr.dataset.row) : {};
      }

      // Simpan ke ClaimState
      window.claimState = window.claimState || {};
      window.claimState.currentDiagnosis = dx;
      window.claimState.currentDiagnosisTitle = name;

      openModal(`<div class="flex flex-col items-start items-center">
        <span class="text-lg font-bold">Detail ${type}</span>
        <span class="font-bold text-2xl mb-2 text-yellow-500">${name}</span>
      </div>`, buildModalContent(dx));

      updateRingkasanFromRow(uiId, dx);
    } catch (err) {
      console.error("❌ Gagal load modal detail:", err);
      alert("Gagal ambil detail dari core_engine");
    }
  }

  function renderDiagnosisDetail(it) {
    const klinisRaw = it.klinis || {};
    let klinis = {};
    if (typeof klinisRaw === "string") klinis = { justifikasi: klinisRaw, bukti_klinis: "-", syarat_klinis: "-" };
    else if (Array.isArray(klinisRaw)) klinis = { justifikasi: klinisRaw.join(", "), bukti_klinis: "-", syarat_klinis: "-" };
    else if (typeof klinisRaw === "object" && klinisRaw !== null) {
      klinis = {
        justifikasi: klinisRaw.justifikasi || "-",
        bukti_klinis: klinisRaw.bukti_klinis || "-",
        syarat_klinis: klinisRaw.syarat_klinis || "-"
      };
    } else klinis = { justifikasi: "-", bukti_klinis: "-", syarat_klinis: "-" };

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
    const faskes = { kesesuaian_rs: it.faskes?.kesesuaian_rs || "-" };
    const rujukan = { syarat: it.rujukan?.syarat || "-", kelayakan: it.rujukan?.kelayakan || "-" };

    const renderBox = (label, value, status = "default", diagnosisId = null) => {
      let colorClass = "bg-gray-200 text-gray-800";
      if (status === "valid") colorClass = "bg-green-600 text-white";
      if (status === "invalid") colorClass = "bg-red-600 text-white";
      const safeValue = value || "-";
      const content = diagnosisId
        ? `<span class="cursor-pointer" title="PNPK Sepsis 2020" onclick="openRegulationModal(${diagnosisId}, 'diagnosis')">${safeValue}</span>`
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
        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">KLINIS</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderBox("Justifikasi", klinis.justifikasi, klinis.status, it.id)}
            ${renderBox("Bukti Klinis", klinis.bukti_klinis)}
            ${renderBox("Syarat Klinis", klinis.syarat_klinis, klinis.status, it.id)}
          </div>
        </section>

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

        // <!-- i-DRG Section -->
        // <section class="rounded shadow overflow-hidden">
        //   <div class="bg-blue-600 text-white px-3 py-2 font-bold">i-DRG</div>
        //   <div class="p-3 bg-gray-100 dark:bg-gray-700">
        //     ${renderIdrgSection(it.idrg_diagnosis)}
        //   </div>
        // </section>
        // (perubahan di atas)

        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">TINDAKAN</div>
          <div class="p-3 bg-gray-100 dark:bg-gray-700">
            ${renderTindakan(tindakan)}
          </div>
        </section>

        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">RAWAT INAP</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderBox("Indikasi", rawat.indikasi, rawat.status_indikasi, it.id)}
            ${renderBox("Lama Rawat", rawat.lama_rawat, rawat.status_lama, it.id)}
            ${renderBox("Perpanjangan", rawat.perpanjangan, rawat.status_perpanjangan, it.id)}
          </div>
        </section>

        <section class="rounded shadow overflow-hidden">
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">FASKES</div>
          <div class="space-y-2 p-3 bg-gray-100 dark:bg-gray-700">
            ${renderBox("Kesesuaian RS", faskes.kesesuaian_rs, faskes.status, it.id)}
          </div>
        </section>

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

  function renderIdrgSection(idrg) {
    if (!idrg) {
      return `<div class="italic text-gray-500">Tidak ada prediksi i-DRG</div>`;
    }

    const renderRow = (label, value) => `
      <div class="grid grid-cols-2">
        <div class="bg-gray-700 text-white px-3 py-2">${label}</div>
        <div class="bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2">${value || "-"}</div>
      </div>
    `;

    return `
      <div x-data="{ open: false }" class="border rounded shadow overflow-hidden mb-3">
        <div class="accordion-header flex items-center justify-between bg-blue-600 text-white px-3 py-2 font-bold cursor-pointer"
            @click="open = !open">
          <span>Prediksi i-DRG</span>
          <span x-text="open ? '▼' : '▶'"></span>
        </div>
        <div class="accordion-body" x-show="open" x-transition>
          ${renderRow("Group i-DRG", idrg.group_idrg)}
          ${renderRow("Severity Index", idrg.severity_index)}
          ${renderRow("Checklist", idrg.checklist)}
          ${renderRow("Faktor Severity", idrg.faktor_severity)}
          ${renderRow("Ungroupable Alert", idrg.ungroupable_alert)}
          ${renderRow("Simulasi Tarif", idrg.simulasi_tarif)}
          ${renderRow("Gap Analysis", idrg.gap_analysis)}
          ${idrg.rekomendasi_ai ? renderRow("Rekomendasi AI", idrg.rekomendasi_ai) : ""}
        </div>
      </div>
    `;
  }

  function renderTindakan(list) {
    const tindakanList = (list && list.length > 0)
      ? list.map(td => {
          const nama = td.nama || td.tindakan || "-";
          const deskripsi = td.deskripsi || td.description || "-";
          const procId = td.id || td.procedure_id || "";
          return `
            <div class="grid grid-cols-3 gap-4 items-center bg-white dark:bg-gray-800 p-3 rounded shadow mb-2"
                data-procid="${procId}">
              <div class="font-semibold text-blue-600 underline cursor-pointer truncate"
                   onclick="openProcedureModal('${procId}')">${nama}</div>
              <div>
                <span class="block px-3 py-1 text-sm font-medium bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded shadow-sm whitespace-nowrap overflow-hidden text-ellipsis"
                      title="${deskripsi}">${deskripsi}</span>
              </div>
              ${window.claimState?.role === "doctor" ? `
                <div class="flex space-x-2 justify-end">
                  <button type="button"
                          onclick="updateSimulasi('tindakan','Primary','${nama}','Manual', window.claimState.tab)"
                          class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs">Pilih Utama</button>
                  <button type="button"
                          onclick="updateSimulasi('tindakan','Secondary','${nama}','Manual', window.claimState.tab)"
                          class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-xs">Pilih Sekunder</button>
                </div>` : ``}
            </div>
          `;
        }).join("")
      : `<div class="italic text-gray-500">Tidak ada tindakan AI</div>`;

    const manualForm = window.claimState?.role === "doctor" ? `
      <div class="tindakan-list mt-4"></div>
      <div class="mt-4 p-3 border rounded bg-gray-50 dark:bg-gray-700">
        <div class="font-semibold mb-2">Tambah Tindakan Manual</div>
        <div class="flex gap-2">
          <input id="manualNamaTindakan" placeholder="Nama Tindakan"
                 class="flex-1 px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600" />
          <button type="button" onclick="addManualTindakan()"
                  class="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded flex items-center">➕ Tambah</button>
        </div>
      </div>
    ` : '';

    // render list manual setelah modal terbuka
    setTimeout(() => window.renderManualTindakanList && window.renderManualTindakanList(), 0);

    return tindakanList + manualForm;
  }

  function buildModalContent(it) {
    let content = renderDiagnosisDetail(it);
    content += `<div class="tindakan-list mt-4"></div>`;
    setTimeout(() => window.renderManualTindakanList && window.renderManualTindakanList(), 0);
    return content;
  }

  async function openProcedureModal(procId) {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return alert("❌ Claim ID tidak ditemukan.");

    try {
      const res = await fetch(`/claims/${claimId}/analyze_procedure`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ procedure_id: procId })
      });
      const result = await res.json();
      const d = result.data || result;

      // Simpan ke Claimstate
      window.claimState = window.claimState || {};
      window.claimState.currentProcedure = { id: procId, data: d };

      // ✅ UI markup tetap sama (punya temenmu)
      const content = `
        <div class="flex justify-end items-start mb-3">
          <button type="button" onclick="closeNestedModal()"
                  class="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded">✕</button>
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Kode ICD-9:</b></div>
          <div class="bg-gray-800 px-3 py-2 rounded">${d.icd9_code || '-'}</div>
          <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Deskripsi:</b></div>
          <div class="bg-gray-800 px-3 py-2 rounded">${d.icd9_desc || '-'}</div>
          <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Validitas:</b></div>
          <div class="bg-gray-800 px-3 py-2 rounded">${d.validitas || '-'}</div>
          <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Status:</b></div>
          <div class="bg-gray-800 px-3 py-2 rounded">${d.status_tindakan || '-'}</div>
          <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>INA-CBG:</b></div>
          <div class="bg-gray-800 px-3 py-2 rounded">${d.ina_cbg_tarif || d.ina_cbg || '-'}</div>
          <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Faskes:</b></div>
          <div class="bg-gray-800 px-3 py-2 rounded">${d.faskes || '-'}</div>
          <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Rawat Inap:</b></div>
          <div class="bg-gray-800 px-3 py-2 rounded">${d.rawat_inap || '-'}</div>
          <div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>Syarat Klinis:</b></div>
          <div class="bg-gray-800 px-3 py-2 rounded">${d.syarat_klinis || '-'}</div>
        </div>
      `;

      openModal(`Detail Tindakan (${d.procedure || d.nama || '-'})`, content, { hideDefaultClose: true });
    } catch (err) {
      console.error("❌ Gagal load detail tindakan:", err);
      alert("Gagal ambil detail tindakan dari core_engine");
    }
  }

  function openManualDetailModal(it) {
    const dummy = {
      kategori: it.kategori || "Manual",
      klinis: it.klinis || "-",
      icd10: { kode_icd: it.icd10_code || "-", deskripsi: "-" },
      tindakan: it.procedure_text ? [{ procedure_text: it.procedure_text }] : [],
      validitas: "-",
      status: "-",
      ina_cbg: "-",
      faskes: "-",
      rawat_inap: "-",
      syarat_klinis: "-"
    };
    const title = `<div class="flex flex-col items-start items-center">
      <span class="text-lg font-bold">Detail Tindakan Manual</span>
      <span class="text-sm font-normal">${it.procedure_text || "-"}</span>
    </div>`;
    openModal(title, buildModalContent(dummy));
    window.claimState.currentProcedure = dummy;
    updateRingkasanFromRow(dummy);
  }

  function closeNestedModal() {
    const dx = window.claimState.currentDiagnosis;
    if (dx) {
      const nama = window.claimState.currentDiagnosisTitle || dx?.kategori || "-";
      openModal(`<div class="flex flex-col items-start items-center">
        <span class="text-lg font-bold">Detail Diagnosis</span>
        <span class="font-bold text-2xl mb-2 text-yellow-500">${nama}</span>
        </div>`, buildModalContent(dx), { hideDefaultClose: false });
    } else {
      const state = Alpine.$data(document.getElementById('claimRoot'));
      state.modalOpen = false;
    }
  }

  async function openRegulationModal(id, type = "diagnosis") {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    if (!claimId) return alert("❌ Claim ID tidak ditemukan.");

    try {
      // ✅ endpoint baru sesuai mapping
      const res = await fetch(`/claims/${claimId}/regulation_detail`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ field: type, claim_id: claimId, id })
      });
      const json = await res.json();
      const { data } = json;

      if (!data || data.length === 0) {
        alert("Tidak ada regulasi untuk field ini");
        return;
      }

      // ✅ tetap simpan source (buat balik modal asal)
      window.claimState = window.claimState || {};
      window.claimState.regulationSource = { type, id };

      // ✅ tentukan apakah perlu tombol merah manual
      const isEval = (type === "diagnosis_eval" || type === "procedure_eval");
      const closeBtn = isEval
        ? ""
        : `<div class="flex justify-end items-start mb-3">
            <button type="button" onclick="closeRegulationModal()"
                    class="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded">✕</button>
          </div>`;

      // ✅ pakai markup UI versi temenmu
      const content = `
        <div class="space-y-4 text-sm">
          ${closeBtn}
          <div class="grid grid-cols-2 gap-y-2 text-sm">
            <div class="bg-gray-700 text-white font-semibold px-3 py-2 rounded-l">Dasar Hukum</div>
            <div class="bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2 rounded-r text-gray-800">${data[0].dasar_hukum}</div>

            <div class="bg-gray-700 text-white font-semibold px-3 py-2 rounded-l">Judul Regulasi</div>
            <div class="bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2 rounded-r text-gray-800">${data[0].judul_regulasi}</div>

            <div class="bg-gray-700 text-white font-semibold px-3 py-2 rounded-l">Pasal / Ayat / Bab</div>
            <div class="bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2 rounded-r italic text-gray-800">${data[0].bab_pasal}</div>

            <div class="bg-gray-700 text-white font-semibold px-3 py-2 rounded-l">Isi / Penjelasan</div>
            <div class="bg-white dark:bg-gray-800 dark:text-gray-100 px-3 py-2 rounded-r text-gray-800">${data[0].isi}</div>
          </div>
        </div>
      `;

      window.openModal && window.openModal("Detail Regulasi", content, { hideDefaultClose: isEval ? false : true });
    } catch (err) {
      console.error("❌ Gagal load regulasi:", err);
      alert("Gagal memuat regulasi dari core_engine");
    }
  }

  // === Tutup Regulasi (Balik ke modal asal) ===
  function closeRegulationModal() {
    const source = window.claimState?.regulationSource;

    if (source?.type === "procedure" && window.claimState?.currentProcedure) {
      // Balik ke modal tindakan
      openProcedureModal(window.claimState.currentProcedure.id);
    } else {
      // Default → balik ke modal diagnosis
      closeNestedModal();
    }
  }

    
  window.openNoteModal = function(title, fieldKey) {
    const root = document.getElementById('claimRoot');
    const state = Alpine.$data(root);

    const existingLogs = (state.notes && state.notes[fieldKey]) ? state.notes[fieldKey] : [];
    const currentText = existingLogs.join("\n");

    state.modalTitle = title;
    state.modalContent = `
      <div class="space-y-4">
        <label class="block text-sm font-medium">Tambahkan Catatan:</label>
        <textarea id="noteField"
                  class="w-full border rounded p-2 text-sm"
                  rows="4"
                  placeholder="Tulis catatan..."></textarea>

        <div class="flex justify-end gap-2">
          <button type="button"
                  class="px-4 py-2 bg-gray-300 rounded"
                  onclick="Alpine.$data(document.getElementById('claimRoot')).modalOpen=false">
            Close
          </button>
          <button type="button"
                  class="px-4 py-2 bg-blue-600 text-white rounded"
                  onclick="saveNote('${fieldKey}')">
            Save & Close
          </button>
        </div>

        <hr class="my-4">
        <h4 class="font-semibold text-sm">Riwayat Catatan:</h4>
        <pre class="bg-gray-100 p-2 rounded text-xs whitespace-pre-wrap">${currentText || 'Belum ada catatan.'}</pre>
      </div>
    `;
    state.modalOpen = true;
  };


  window.saveNote = function(fieldKey) {
    const root = document.getElementById('claimRoot');
    const state = Alpine.$data(root);

    const textarea = document.getElementById("noteField");
    const val = textarea.value.trim();
    if (!val) {
      state.modalOpen = false;
      return;
    }

    // generate timestamp
    const now = new Date();
    const hh = String(now.getHours()).padStart(2,'0');
    const mm = String(now.getMinutes()).padStart(2,'0');
    const role = state.role.charAt(0).toUpperCase() + state.role.slice(1);

    const log = `[${role} ${hh}:${mm}] ${val}`;

    // ✅ pastikan array ada
    if (!state.notes) state.notes = {};
    if (!state.notes[fieldKey]) state.notes[fieldKey] = [];

    state.notes[fieldKey].push(log);

    state.modalOpen = false;
  };


  // Export
  window.openModal = openModal;
  window.openModalFromAttr = openModalFromAttr;
  window.buildModalContent = buildModalContent;
  window.renderDiagnosisDetail = renderDiagnosisDetail;
  window.renderIdrgSection = renderIdrgSection;
  window.renderTindakan = renderTindakan;
  window.openProcedureModal = openProcedureModal;
  window.openManualDetailModal = openManualDetailModal;
  window.closeNestedModal = closeNestedModal;
  window.openRegulationModal = openRegulationModal;
  window.closeRegulationModal = closeRegulationModal;
})();
