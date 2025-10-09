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
    if (dx.isManual) {
      const stage = dx.stage || window.claimState?.tab || "admission";
      window.renderManualTindakanList && window.renderManualTindakanList(stage);
      return;
    }

    const row = document.querySelector(`[data-id="${itemId}"]`);
    if (!row) return;
    if (row.closest(".tindakan-list")) {
      const descEl = row.querySelector("span[title], span.block");
      if (descEl) {
        const newText = dx.deskripsi || "-";
        descEl.textContent = newText;
        descEl.setAttribute("title", newText);
      }
      return;
    }

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

    // Persist semua perubahan hasil modal ke state simulasi
    try {
      const stage = dx.stage || window.claimState?.tab || "admission";
      const sim = window.claimState?.simulasi?.[stage];
      if (sim && Array.isArray(sim.diagnosis)) {
        const item = sim.diagnosis.find(d =>
          d.id === dx.id ||
          d.kategori === dx.kategori ||
          d.icd10_code === dx.icd10_code
        );
        if (item) {
          if (dx.klinis) {
            let klinisText = "";
            if (typeof dx.klinis === "object" && dx.klinis !== null) {
              const k = dx.klinis;
              klinisText = [k.justifikasi, k.bukti_klinis, k.syarat_klinis]
                .filter(Boolean)
                .join(", ");
            } else if (Array.isArray(dx.klinis)) {
              klinisText = dx.klinis.filter(Boolean).join(", ");
            } else {
              klinisText = dx.klinis;
            }
            item.klinis = `<span title="${klinisText}">${truncateText(klinisText, 44)}</span>`;
          }

          if (dx.icd10_code || dx.icd10) {
            item.icd10_code = dx.icd10_code || dx.icd10?.kode_icd || "-";
            item.icd10 = dx.icd10 || { kode_icd: item.icd10_code };
          }

          if (Array.isArray(dx.tindakan)) {
            const texts = dx.tindakan.map(t => t.procedure_text || t.tindakan).filter(Boolean);
            const tindakanText = texts.join(", ");
            item.tindakan = `<span title="${tindakanText}">${truncateText(tindakanText, 44)}</span>`;
          }
        }
      }
    } catch (err) {
      console.warn("⚠️ gagal persist ringkasan ke state:", err);
    }
  }

  // ================== Modal detail dari tabel ==================
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
        dx = result.data || {};

        if (Array.isArray(dx.tindakan)) {
          dx.tindakan = dx.tindakan.map(td => ({ ...td, source: td.source || "AI" }));
        }

        // 🔥 Fetch i-DRG data if not present (for core_engine compatibility)
        if (!dx.idrg_diagnosis && dx.icd10_code && type === "diagnosis") {
          try {
            console.log("🔍 Fetching i-DRG data for diagnosis:", dx.nama_kategori);
            const idrgUrl = `/claims/${claimId}/analyze_diagnosis`;
            const idrgPayload = {
              diagnosis: {
                icd10_code: dx.icd10_code,
                name: dx.nama_kategori || dx.kategori
              }
            };
            
            const idrgRes = await fetch(idrgUrl, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(idrgPayload)
            });
            
            if (idrgRes.ok) {
              const idrgData = await idrgRes.json();
              console.log("📥 i-DRG data received:", idrgData);
              
              // Map core_engine response to expected format
              if (idrgData && (idrgData.data || idrgData.idrg_diagnosis)) {
                dx.idrg_diagnosis = idrgData.data || idrgData.idrg_diagnosis || idrgData;
              }
            } else {
              console.warn("⚠️ Could not fetch i-DRG data:", idrgRes.status);
            }
          } catch (err) {
            console.warn("⚠️ Error fetching i-DRG data:", err);
          }
        }

        if ((!Array.isArray(dx.tindakan) || !dx.tindakan.length) && window.claimState?.simulasi) {
          const stage = dx.stage || window.claimState.tab || "admission";
          const semua = window.claimState.simulasi[stage]?.tindakan || [];
          const tindakanAI = semua.filter(td => td.is_manual === false);
          if (tindakanAI.length) {
            dx.tindakan = tindakanAI.map(td => ({
              procedure_text: td.procedure_text || td.tindakan || "-",
              deskripsi: td.deskripsi || "-",
              icd9: td.icd9 || "-",
              status: td.status || "-",
              isManual: false,
              source: "AI"
            }));
          }
        }

        if (dx && Array.isArray(dx.tindakan) && dx.tindakan.length) {
          window.claimState.cache = window.claimState.cache || {};
          if (!Array.isArray(window.claimState.cache.tindakanAI))
            window.claimState.cache.tindakanAI = [];

          const stage = dx.stage || window.claimState.tab || "admission";

          dx.tindakan.forEach(td => {
            const exists = window.claimState.cache.tindakanAI.some(
              t => t.procedure_text === td.procedure_text && t.stage === stage
            );
            if (!exists) {
              window.claimState.cache.tindakanAI.push({
                ...td,
                stage,
                diagnosis_id: dx.id,
                diagnosis_code: dx.icd10_code,
                isManual: false,
                source: "AI"
              });
            }
          });
        }
      } else {
        dx = tr?.dataset.row ? JSON.parse(tr.dataset.row) : {};
        const stage = dx.stage || window.claimState?.tab || "admission";

        const tindakanAIAll = Array.isArray(window.claimState?.cache?.tindakanAI)
          ? window.claimState.cache.tindakanAI.filter(td =>
              td && (td.source === "AI" || td.isManual === false || td.is_manual === false)
            )
          : [];

        const tindakanAIFinal = tindakanAIAll
          .map(td => ({
            ...td,
            id: td.id ?? td.procedure_id ?? td.item_id ?? null,
            diagnosis_id: td.diagnosis_id ?? td.parent_id ?? null,
            diagnosis_code: td.diagnosis_code ?? td.icd10_code ?? null,
            stage: td.stage || stage,
            source: "AI",
            isManual: false
          }));

        const existingManual = Array.isArray(dx.tindakan)
          ? dx.tindakan.filter(t => t.isManual === true)
          : [];

        dx.tindakan = existingManual.length
          ? [...tindakanAIFinal, ...existingManual]
          : tindakanAIFinal;

        const stageKey = dx.stage || window.claimState?.tab || "admission";
        if (!window.claimState.simulasi[stageKey]) window.claimState.simulasi[stageKey] = {};
        const currentAll = window.claimState.simulasi[stageKey].tindakan || [];
        const merged = [...currentAll];
        dx.tindakan.forEach(td => {
          if (!merged.some(m => m.procedure_text === td.procedure_text && m.source === td.source))
            merged.push(td);
        });
        window.claimState.simulasi[stageKey].tindakan = merged;
      }

      const rawText = tr?.querySelector("td")?.innerText.trim() || "-";
      const namaPenyakit =
        dx?.kategori || dx?.nama_kategori || dx?.diagnosis ||
        dx?.komorbid || dx?.komplikasi || rawText || "-";

      window.claimState.currentDiagnosis = dx;
      window.claimState.currentDiagnosisTitle = namaPenyakit;

      const title = `
        <div class="flex flex-col items-start items-center">
          <span class="text-lg font-bold">Detail Diagnosis</span>
          <span class="font-bold text-2xl mb-2 text-yellow-500">${namaPenyakit}</span>
        </div>`;

      const stageKey = dx.stage || window.claimState?.tab || "admission";
      if (!window.claimState.simulasi[stageKey]) window.claimState.simulasi[stageKey] = {};
      window.claimState.simulasi[stageKey].tindakan = dx.tindakan;

      openModal(title, buildModalContent(dx));
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
          <div class="bg-blue-600 text-white px-3 py-2 font-bold">i-DRG</div>
          <div class="p-3 bg-gray-100 dark:bg-gray-700">
            ${renderIdrgSection(it.idrg_diagnosis)}
          </div>
        </section>

        <section class="rounded shadow overflow-visible">
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

  function renderIdrgSection(idrg, claimId) {
    if (!idrg) {
      return `<div class="italic text-gray-500">Tidak ada prediksi i-DRG</div>`;
    }

    const renderRow = (label, value) => `
      <div class="grid grid-cols-2">
        <div class="bg-gray-700 text-white px-3 py-2">${label}</div>
        <div class="bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2">${value || "-"}</div>
      </div>
    `;

    const renderRowClickable = (label, value, field) => `
      <div class="grid grid-cols-2">
        <div class="bg-gray-700 text-white px-3 py-2">${label}</div>
        <div class="bg-gray-200 dark:bg-gray-800 px-3 py-2"
            onclick="openRegulationModal('${claimId}', '${field}')">
          ${value || "-"}
        </div>
      </div>
    `;

    return `
      <div x-data="{ open: false }" class="border rounded shadow overflow-hidden mb-3">
        <div class="accordion-header flex items-center justify-between bg-blue-600 text-white px-3 py-2 font-bold cursor-pointer"
            @click="open = !open">
          <span>Prediksi i-DRG (Diagnosis)</span>
          <span x-text="open ? '▼' : '▶'"></span>
        </div>
        <div class="accordion-body" x-show="open" x-transition>
          ${renderRowClickable("Group i-DRG", idrg.group_idrg, "idrg_diagnosis_group")}
          ${renderRowClickable("Severity Index", idrg.severity_index, "idrg_diagnosis_severity")}
          ${renderRowClickable("Checklist Dokumentasi", idrg.checklist, "idrg_diagnosis_checklist")}
          ${renderRow("Faktor Severity", idrg.faktor_severity)}
          ${renderRowClickable("Ungroupable Alert", idrg.ungroupable_alert, "idrg_diagnosis_ungroupable")}
          ${renderRow("Simulasi Tarif", idrg.simulasi_tarif)}
          ${renderRow("Gap Analysis", idrg.gap_analysis)}
        </div>
      </div>
    `;
  }

  function tindakanAutocomplete() {
    return {
      query: "",
      results: [],
      async search() {
        if (!this.query) { this.results = []; return; }
        const res = await window.searchTindakan(this.query);
        this.results = res.data || [];
      },
      async select(item) {
        this.query = item.procedure_text;
        this.results = [];
        await window.addManualTindakanFromAutocomplete(window.claimState.tab, item);
      }
    }
  }

  function renderTindakan(list) {
    const all = Array.isArray(list) ? list : [];

    const normalized = all.map(td => ({
      ...td,
      source: (td.source || "").toUpperCase(),
      isManual: td.isManual ?? td.is_manual ?? false,
    }));

    const unique = [];
    const seen = new Set();
    for (const td of normalized) {
      const key = `${td.procedure_text || td.nama || td.tindakan}-${td.source}`;
      if (!seen.has(key)) {
        unique.push(td);
        seen.add(key);
      }
    }

    const aiList = unique.filter(td => !td.isManual && td.source === "AI");

    const aiSection = aiList.length
      ? aiList
          .map(td => {
            const nama = td.procedure_text || td.nama || td.procedure_name || td.tindakan;
            const deskripsi = td.deskripsi && td.deskripsi !== "-" ? td.deskripsi : "";
            const procId = td.id || td.procedure_id || "";
            return `
              <div class="grid grid-cols-3 gap-4 items-center bg-white dark:bg-gray-800 p-3 rounded shadow mb-2"
                  data-procid="${procId}">
                <div class="font-semibold text-blue-600 underline cursor-pointer truncate"
                    onclick="openProcedureModal('${procId}')">${nama}</div>
                <div>
                  <span class="block px-3 py-1 text-sm font-medium bg-gray-200 dark:bg-gray-700
                              text-gray-900 dark:text-gray-100 rounded shadow-sm whitespace-nowrap overflow-hidden text-ellipsis"
                        title="${deskripsi}">${deskripsi}</span>
                </div>
                ${window.claimState?.role === "doctor" ? `
                  <div class="flex space-x-2 justify-end">
                    <button type="button"
                            onclick="updateSimulasi('tindakan','Primary','${nama}','AI', window.claimState.tab)"
                            class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-xs">Pilih Utama</button>
                    <button type="button"
                            onclick="updateSimulasi('tindakan','Secondary','${nama}','AI', window.claimState.tab)"
                            class="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-xs">Pilih Sekunder</button>
                  </div>` : ``}
              </div>
            `;
          })
          .join("")
      : `<div class="italic text-gray-500">Tidak ada tindakan AI</div>`;

    const manualArea = `
      <div class="tindakan-list"></div>
      <div class="mt-4 p-3 border rounded bg-gray-50 dark:bg-gray-700">
        <div class="font-semibold mb-2">Tambah Tindakan Manual</div>
        <div class="relative flex gap-2 mt-2" x-data="tindakanAutocomplete()">
          <input type="text"
                x-model="query"
                @input.debounce.300ms="search"
                @keydown.enter.prevent="results.length && select(results[0])"
                placeholder="Nama Tindakan"
                class="flex-1 px-2 py-1 rounded bg-white dark:bg-gray-900
                        text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600">
          <button type="button"
                  class="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded"
                  @click="handleAddManualTindakan(window.claimState.tab)">+</button>

          <ul x-show="results.length > 0"
              class="absolute top-full left-0 mt-1 z-50 
                    bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 
                    rounded shadow-lg w-full max-h-40 overflow-y-auto">
            <template x-for="item in results" :key="item.procedure_text">
              <li @click="select(item)"
                  class="px-2 py-1 cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700"
                  x-text="item.procedure_text"></li>
            </template>
          </ul>
        </div>
      </div>
    `;

    setTimeout(() => {
      const tab = window.claimState?.tab || "admission";
      const sim = window.claimState?.simulasi?.[tab];
      if (sim?.tindakan?.some(td => td.isManual)) {
        window.renderManualTindakanList(tab);
      }
    }, 0);

    return aiSection + manualArea;
  }

  function buildModalContent(it) {
    if (it.icd10) {
      let content = renderDiagnosisDetail(it);
      content += `<div class="tindakan-list mt-4"></div>`;
      setTimeout(() => {
        const tab = window.claimState?.tab || "admission";
        window.renderManualTindakanList && window.renderManualTindakanList(tab);
      }, 0);
      return content;
    }

    if (it.icd9 || it.detail) {
      return renderProcedureDetail(it);
    }

    return `<div class="italic text-gray-500">Tidak ada detail tersedia</div>`;
  }

  async function openProcedureModal(procId) {
    if (!procId || procId === "undefined" || procId === "null") {
      console.warn("⚠️ Tidak bisa buka detail tindakan: procId kosong");
      return;
    }

    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    const url = `/claims/ai/recommendation/detail?claim_id=${claimId}&rec_type=procedure&item_id=${procId}`;

    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      const data = json?.data || {};
      const d = (data?.tindakan && data.tindakan[0]) ? data.tindakan[0] : data;

      const deskripsiGabungan = `ICD-9: ${d.icd9 || '-'}, Status: ${d.status || '-'}, INA-CBG: ${d.ina_cbg || '-'}`;
      const procedureName = data?.procedure_text || d.procedure_text || "-";

      const dx = window.claimState.currentDiagnosis;
      if (dx && Array.isArray(dx.tindakan)) {
        dx.tindakan.forEach(td => {
          if (td.id == procId || td.procedure_id == procId)
            td.deskripsi = deskripsiGabungan;
        });
      }

      const renderProcBox = (label, value, skipReg = false) => {
        const safeValue = value || "-";
        const content = (!skipReg)
          ? `<span class="cursor-pointer" title="PNPK Sepsis 2020"
                  onclick="openRegulationModal(${procId}, 'procedure')">${safeValue}</span>`
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

      openModal(
        `<div class="flex flex-col items-start items-center">
          <span class="text-lg font-semibold">Detail Tindakan</span>
          <span class="font-bold text-2xl mb-2 text-yellow-500">${procedureName}</span>
        </div>`,
        content,
        { hideDefaultClose: true }
      );

      window.claimState.currentProcedure = { id: procId };

      const itemEl = document.querySelector(`[data-procid='${procId}'] .text-xs`);
      if (itemEl) itemEl.textContent = deskripsiGabungan;
    } catch (err) {
      console.error("❌ Gagal load detail tindakan:", err);
    }
  }

  async function openManualDetailModal(it, tab, idx) {
    try {
      const url = `/claims/search/tindakan/detail/${encodeURIComponent(it.procedure_text)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("HTTP " + res.status);
      const json = await res.json();
      if (json.status !== "ok") throw new Error("Gagal load detail");

      const detail = json.data;
      const deskripsiGabungan = `ICD-9: ${detail.icd9 || "-"}, Status: ${detail.status || "-"}, INA-CBG: ${detail.ina_cbg || "-"}`;
      detail.deskripsi = deskripsiGabungan;

      if (window.claimState?.simulasi?.[tab]?.tindakan?.[idx]) {
        window.claimState.simulasi[tab].tindakan[idx].deskripsi = deskripsiGabungan;
      }

      const title = `<div class="flex flex-col items-start items-center">
        <span class="text-sm font-semibold">Detail Tindakan Manual</span>
        <span class="font-bold text-2xl mb-2 text-yellow-500">${detail.procedure_text}</span>
      </div>`;

      openModal(title, renderProcedureDetail(detail), { hideDefaultClose: true });

      window.claimState.currentProcedure = detail;
      const uiId = `manual-tindakan-${tab}-${idx}`;
      updateRingkasanFromRow(uiId, detail);
    } catch (err) {
      console.error("❌ Gagal load detail tindakan manual:", err);
    }
  }

  function renderProcedureDetail(it) {
    const d = (it.detail && it.detail[0]) || it;
    const deskripsi = d.icd9 && d.status && d.ina_cbg
      ? `ICD-9: ${d.icd9}, Status: ${d.status}, INA-CBG: ${d.ina_cbg}`
      : (d.icd9 || d.status || d.ina_cbg || "-");
    const renderProcBox = (label, value, skipReg = false) => {
      const safeValue = value || "-";
      const content = (!skipReg)
        ? `<span class="cursor-pointer" title="PNPK Sepsis 2020"
                  onclick="openRegulationModal('${d.icd9}', 'procedure')">${safeValue}</span>`
        : safeValue;

      return `<div class="bg-gray-700 px-3 py-2 rounded font-semibold text-white"><b>${label}:</b></div>
              <div class="bg-gray-800 px-3 py-2 rounded">${content}</div>`;
    };

    return `
      <div class="flex justify-end items-start mb-3">
            <button type="button" onclick="closeNestedModal()"
                    class="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded">✕</button>
      </div>
      <div class="grid grid-cols-2 gap-2 text-sm">
        ${renderProcBox("Kode ICD-9", d.icd9)}
        ${renderProcBox("Deskripsi", d.deskripsi || deskripsi)}
        ${renderProcBox("Validitas", d.validitas, true)}
        ${renderProcBox("Status", d.status)}
        ${renderProcBox("INA-CBG", d.ina_cbg)}
        ${renderProcBox("Faskes", d.faskes)}
        ${renderProcBox("Rawat Inap", d.rawat_inap)}
        ${renderProcBox("Syarat Klinis", d.syarat_klinis)}
      </div>
    `;
  }

  function closeNestedModal() {
    const dx = window.claimState.currentDiagnosis;
    if (!dx) {
      const state = Alpine.$data(document.getElementById('claimRoot'));
      state.modalOpen = false;
      return;
    }

    const stage = dx.stage || window.claimState?.tab || "admission";
    const nama = window.claimState.currentDiagnosisTitle || dx?.kategori || "-";

    openModal(`<div class="flex flex-col items-start items-center">
      <span class="text-lg font-bold">Detail Diagnosis</span>
      <span class="font-bold text-2xl mb-2 text-yellow-500">${nama}</span>
    </div>`, buildModalContent(dx), { hideDefaultClose: false });

    setTimeout(() => {
      window.renderManualTindakanList && window.renderManualTindakanList(stage);
    }, 0);
  }

  async function openRegulationModal(id, type = "diagnosis") {
    const claimId = document.getElementById("claimRoot")?.dataset.claimId;
    let url = `/claims/${claimId}/regulations?`;

    if (type === "diagnosis") url += `diagnosis_id=${id}`;
    else if (type === "procedure") url += `procedure_id=${id}`;
    else if (type === "diagnosis_eval") url += `diagnosis_evaluation_id=${id}`;
    else if (type === "procedure_eval") url += `procedure_evaluation_id=${id}`;
    else if (type === "idrg_diagnosis") url += `idrg_diagnosis_id=${id}`;
    else if (type === "idrg_summary") url += `idrg_summary_id=${id}`;

    try {
      const res = await fetch(url);
      const json = await res.json();
      const { data } = json;

      if (!data || data.length === 0) {
        alert("Tidak ada regulasi untuk field ini");
        return;
      }

      window.claimState = window.claimState || {};
      window.claimState.regulationSource = { type, id };

      const isEval =
        type === "diagnosis_eval" ||
        type === "procedure_eval" ||
        type.startsWith("idrg_summary");

      let closeBtn = "";
      if (isEval) {
        closeBtn = "";
      } else {
        closeBtn = `<div class="flex justify-end items-start mb-3">
                      <button type="button" onclick="closeRegulationModal()"
                              class="text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded">✕</button>
                    </div>`;
      }

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

      openModal("Detail Regulasi", content, { hideDefaultClose: isEval ? false : true });
    } catch (e) {
      console.error("❌ Gagal load regulasi", e);
    }
  }

  function closeRegulationModal() {
    const source = window.claimState?.regulationSource;

    if (source?.type === "procedure" && window.claimState?.currentProcedure) {
      openProcedureModal(window.claimState.currentProcedure.id);
    } else if (source?.type?.startsWith("idrg_diagnosis") && window.claimState?.currentDiagnosis) {
      closeNestedModal();
    } else if (source?.type?.startsWith("idrg_summary")) {
      const state = Alpine.$data(document.getElementById('claimRoot'));
      state.modalOpen = false;
    } else {
      closeNestedModal();
    }
  }

  // ================= SISTEM NOTES YANG DIPERBAIKI =================
  
// ======================== SISTEM NOTES FINAL STABIL ========================

// ✅ ID stabil tanpa hash (supaya sama setiap reload)
function getStableItemId(claimId, stage, fieldKey, itemName = "") {
  const key = fieldKey.toLowerCase();
  if (key === "primary_diagnosis" || key === "primary_action") return 1;
  if (key === "secondary_diagnosis" || key === "secondary_action") return 2;
  return 9999; // fallback umum
}

// ✅ Buka modal catatan (dengan context lengkap)
window.openNoteModal = async function(title, fieldKey, item = null) {
  const root = document.getElementById("claimRoot");
  let state = null;
  try {
    state = Alpine.$data(root);
  } catch (e) {
    console.warn("⚠️ fallback ke window.claimState karena Alpine belum aktif");
    state = window.claimState || {};
  }

  const claimId = root.dataset.claimId;
  const currentStage = state.tab || window.claimState?.tab || "admission";

  // Simpan context
  state.currentNoteItem = item;
  state.currentNoteField = fieldKey;
  state.currentNoteStage = currentStage;

  // Tentukan itemId (stabil)
  const itemName = item?.name || "primary";
  const itemId = item?.id || getStableItemId(claimId, currentStage, fieldKey, itemName);

  console.log("📝 openNoteModal context:", { stage: currentStage, fieldKey, itemId, itemName });

  // Ambil notes dari backend
  let notes = [];
  try {
    const url = `/claims/${claimId}/notes?stage=${currentStage}&field_key=${fieldKey}&item_id=${itemId}`;
    console.log("🔍 Fetching notes from:", url);
    const res = await fetch(url);
    const json = await res.json();

    if (res.ok) {
      // Tambahkan fallback ID lama agar note lama tetap terbaca
      const oldIds = [804880226, 2184760293, 32548051, 1, 2];
      notes = (json.data || []).filter(n =>
        n.stage === currentStage &&
        n.field_key === fieldKey &&
        (String(n.item_id) === String(itemId) || oldIds.includes(Number(n.item_id)))
      );

      console.log("🧩 Filter debug", {
        currentStage,
        fieldKey,
        itemId,
        totalBefore: (json.data || []).length,
        totalAfter: notes.length,
        exampleMatch: notes.slice(0, 2).map(n => n.item_id)
      });
    }
  } catch (err) {
    console.error("❌ Gagal fetch notes:", err);
  }

  // Render riwayat catatan
  const existingLogs = notes.map(n => {
    const utcString = n.timestamp?.endsWith("Z") ? n.timestamp : n.timestamp + "Z";
    const time = new Date(utcString).toLocaleString("id-ID", {
      timeZone: "Asia/Jakarta",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit"
    });
    return `[${n.role} ${time} WIB] ${n.note_text}`;
  });

  const currentText = existingLogs.join("\n");

  state.modalTitle = `${title} - ${currentStage.toUpperCase()}`;
  state.modalContent = `
    <div class="space-y-4">
      <div class="bg-blue-50 dark:bg-blue-900 p-3 rounded">
        <p class="text-sm"><strong>Stage:</strong> ${currentStage}</p>
        <p class="text-sm"><strong>Field:</strong> ${fieldKey}</p>
        <p class="text-sm"><strong>Item:</strong> ${itemName}</p>
      </div>

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
                onclick="saveNote('${fieldKey}', '${currentStage}', ${itemId})">
          Save & Close
        </button>
      </div>

      <hr class="my-4">
      <h4 class="font-semibold text-sm">Riwayat Catatan (${notes.length}):</h4>
      <pre class="bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs whitespace-pre-wrap max-h-60 overflow-y-auto">
        ${currentText || 'Belum ada catatan.'}
      </pre>
    </div>
  `;

  state.modalOpen = true;
  console.log("✅ openNoteModal - loaded notes:", notes.length);
};


// ✅ Simpan note baru (frontend + backend sync)
window.saveNote = async function(fieldKey, stage, itemId) {
  const root = document.getElementById("claimRoot");
  const state = Alpine.$data(root);
  const textarea = document.getElementById("noteField");
  const val = textarea.value.trim();

  if (!val) {
    state.modalOpen = false;
    return;
  }

  const claimId = root.dataset.claimId;

  console.log("💾 saveNote FINAL:", { fieldKey, itemId, stage, valueToSend: val });

  try {
    const headers = { "Content-Type": "application/json" };
    if (window.csrfToken) headers["X-CSRF-Token"] = window.csrfToken;

    const resp = await fetch(`/claims/${claimId}/notes`, {
      method: "POST",
      headers,
      credentials: "include",
      body: JSON.stringify({
        item_id: itemId,
        note_text: val,
        parent_id: null,
        field_key: fieldKey,
        stage: stage
      })
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    // Tambahkan ke local state (agar langsung muncul tanpa reload)
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    const role = state.role ? state.role : "User";
    const log = `[${role} ${hh}:${mm}] ${val}`;

    if (!state.notes) state.notes = {};
    if (!state.notes[stage]) state.notes[stage] = {};
    if (!state.notes[stage][fieldKey]) state.notes[stage][fieldKey] = {};
    if (!state.notes[stage][fieldKey][itemId]) state.notes[stage][fieldKey][itemId] = [];
    state.notes[stage][fieldKey][itemId].push(log);

    console.log("✅ Note saved successfully", {
      stage,
      fieldKey,
      itemId,
      totalNotes: state.notes[stage][fieldKey][itemId].length
    });
  } catch (e) {
    console.error("❌ saveNote error:", e);
    alert("Gagal menyimpan catatan: " + e.message);
  }

  state.modalOpen = false;
};


  // Export
  window.openModal = openModal;
  window.openModalFromAttr = openModalFromAttr;
  window.buildModalContent = buildModalContent;
  window.renderDiagnosisDetail = renderDiagnosisDetail;
  window.renderIdrgSection = renderIdrgSection;
  window.renderTindakan = renderTindakan;
  window.tindakanAutocomplete = tindakanAutocomplete;
  window.openProcedureModal = openProcedureModal;
  window.openManualDetailModal = openManualDetailModal;
  window.closeNestedModal = closeNestedModal;
  window.openRegulationModal = openRegulationModal;
  window.closeRegulationModal = closeRegulationModal;
})();