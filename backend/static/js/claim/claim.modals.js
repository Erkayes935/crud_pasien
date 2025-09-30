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
    const dbId = tr?.dataset.dbId;
    const uiId = tr?.dataset.id;
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;

    try {
      let dx;
      if (dbId && !isNaN(Number(dbId))) {
        const url = `/claims/ai/recommendation/detail?claim_id=${claimId}&rec_type=${type}&item_id=${dbId}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const result = await res.json();
        dx = result.data;
      } else {
        dx = tr?.dataset.row ? JSON.parse(tr.dataset.row) : {};
      }

      if ((!dbId || isNaN(Number(dbId))) && tr?.dataset.row) {
        dx = JSON.parse(tr.dataset.row);
        window.claimState.currentDiagnosis = dx;
        window.claimState.currentDiagnosisTitle = dx.kategori || dx.name || "-";
        openModal(`<div class="flex flex-col items-start items-center">
          <span class="text-lg font-bold">Detail Diagnosis</span>
          <span class="font-bold text-2xl mb-2 text-yellow-500">${window.claimState.currentDiagnosisTitle}</span>
        </div>`, buildModalContent(dx));
        return;
      }

      let rawText = tr?.querySelector("td")?.innerText.trim() || "-";
      rawText = rawText.replace(/^▶|^▼/, "").trim();
      rawText = rawText.replace(/\s+\d+$/, "");
      const namaPenyakit =
        dx?.kategori || dx?.nama_kategori || dx?.diagnosis || dx?.komorbid || dx?.komplikasi || rawText || "-";

      openModal(`<div class="flex flex-col items-start items-center">
        <span class="text-lg font-bold">Detail Diagnosis</span>
        <span class="font-bold text-2xl mb-2 text-yellow-500">${namaPenyakit}</span>
      </div>`, buildModalContent(dx));
      window.claimState.currentDiagnosis = dx;
      window.claimState.currentDiagnosisTitle = namaPenyakit;

      updateRingkasanFromRow(uiId, dx);
    } catch (err) {
      console.error("❌ Gagal load modal detail:", err);
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
    const url = `/claims/ai/recommendation/detail?claim_id=${claimId}&rec_type=procedure&item_id=${procId}`;

    try {
      const res = await fetch(url);
      const { data } = await res.json();
      const d = (data.tindakan && data.tindakan[0]) || {};
      const deskripsiGabungan = `ICD-9: ${d.icd9 || '-'}, Status: ${d.status || '-'}, INA-CBG: ${d.ina_cbg || '-'}`;

      const dx = window.claimState.currentDiagnosis;
      if (dx && Array.isArray(dx.tindakan)) {
        dx.tindakan.forEach(td => {
          if (td.id == procId) td.deskripsi = deskripsiGabungan;
        });
      }

      const renderProcBox = (label, value, skipReg = false) => {
        const safeValue = value || "-";
        const content = (!skipReg)
          ? `<span class="cursor-pointer" title="PNPK Sepsis 2020" onclick="openRegulationModal(${procId}, 'procedure')">${safeValue}</span>`
          : safeValue;
        return `<div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>${label}:</b></div>
                <div class="bg-gray-800 px-3 py-2 rounded">${content}</div>`;
      };

      const content = `
        <div class="flex justify-end items-start mb-3">
          <button type="button" onclick="closeNestedModal()"
                  class="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded">✕</button>
        </div>
        <div class="grid grid-cols-2 gap-2">
          ${renderProcBox("Kode ICD-9", d.icd9)}
          ${renderProcBox("Deskripsi", deskripsiGabungan)}
          ${renderProcBox("Validitas", d.validitas, true)}
          ${renderProcBox("Status", d.status)}
          ${renderProcBox("INA-CBG", d.ina_cbg)}
          ${renderProcBox("Faskes", d.faskes)}
          ${renderProcBox("Rawat Inap", d.rawat_inap)}
          ${renderProcBox("Syarat Klinis", d.syarat_klinis)}
        </div>
      `;

      openModal(`Detail Tindakan (${data.procedure_text || '-'})`, content, { hideDefaultClose: true });

      // ✅ simpan reference supaya regulasi tahu asalnya
      window.claimState = window.claimState || {};
      window.claimState.currentProcedure = { id: procId };

      // update tampilan deskripsi list tindakan (instant)
      const itemEl = document.querySelector(`[data-procid='${procId}'] .text-xs`);
      if (itemEl) itemEl.textContent = deskripsiGabungan;
    } catch (err) {
      console.error("Gagal load detail tindakan", err);
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
    let url = `/claims/${claimId}/regulations?`;
    if (type === "diagnosis") url += `diagnosis_id=${id}`;
    else if (type === "procedure") url += `procedure_id=${id}`;
    else if (type === "diagnosis_eval") url += `diagnosis_evaluation_id=${id}`;
    else if (type === "procedure_eval") url += `procedure_evaluation_id=${id}`;

    try {
      const res = await fetch(url);
      const json = await res.json();
      const { data } = json;

      if (!data || data.length === 0) {
        alert("Tidak ada regulasi untuk field ini");
        return;
      }

      // ✅ simpan source biar tau entry point
      window.claimState = window.claimState || {};
      window.claimState.regulationSource = { type, id };

      // Tentukan apakah perlu tombol merah manual
      const isEval = (type === "diagnosis_eval" || type === "procedure_eval");

      const closeBtn = isEval
        ? "" // kalau dari eval → jangan render close merah
        : `<div class="flex justify-end items-start mb-3">
            <button type="button" onclick="closeRegulationModal()"
                    class="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded">✕</button>
          </div>`;

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

      // Kalau dari eval, biarkan default ❌ (jadi `hideDefaultClose=false`)
      openModal("Detail Regulasi", content, { hideDefaultClose: isEval ? false : true });
    } catch (e) {
      console.error("❌ Gagal load regulasi", e);
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

  // Export
  window.openModal = openModal;
  window.openModalFromAttr = openModalFromAttr;
  window.buildModalContent = buildModalContent;
  window.renderDiagnosisDetail = renderDiagnosisDetail;
  window.renderTindakan = renderTindakan;
  window.openProcedureModal = openProcedureModal;
  window.openManualDetailModal = openManualDetailModal;
  window.closeNestedModal = closeNestedModal;
  window.openRegulationModal = openRegulationModal;
  window.closeRegulationModal = closeRegulationModal;
})();
