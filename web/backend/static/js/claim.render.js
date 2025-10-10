// =============== Rendering simulasi, tabel, dan mapping select ===============

(function () {
  function attachTindakan(rows) {
    const tindakanAll = rows.filter(r => r.category === "tindakan");
    rows.forEach(d => {
      const arr = tindakanAll.filter(
        t => t.stage === d.stage &&
            (t.diagnosis_id === d.id || t.diagnosis_code === d.icd10_code)
      );
      d.tindakan = arr.length ? arr : "-";
    });
  }

  function diagnosisAutocomplete(tab, tabPath, type = "diagnosis") {
    return {
      query: "",
      results: [],

      // 🔍 cari diagnosis dari backend
      async search() {
        if (!this.query) {
          this.results = [];
          return;
        }
        try {
          const res = await window.searchDiagnosis(this.query);
          this.results = res?.data || [];
        } catch (err) {
          console.error("❌ Gagal cari diagnosis:", err);
        }
      },

      // 🩺 pilih hasil dari dropdown
      async select(item) {
        this.query = `${item.code} - ${item.name}`;
        this.results = [];
        await window.addManualFromAutocomplete(tab, item, type);
      },

      // ➕ tombol tambah manual
      async addManualIfNotFound() {
        await window.addManualIfNotFound(tab, type); // panggil versi global
      },
    };
  }

  // ================= Fungsi Global: Add Manual If Not Found =================
  async function addManualIfNotFound(tab, type = "diagnosis") {
    // 🔎 cari komponen Alpine yang punya x-data diagnosisAutocomplete dan mengandung tab + type
    let el = document.querySelector(
      `[x-data*="diagnosisAutocomplete('${tab}'"][x-data*="'${type}')"]`
    );

    // fallback untuk daily tab (kadang id bisa berubah)
    if (!el && String(tab).startsWith("daily-")) {
      el = document.querySelector(
        `[x-data*="diagnosisAutocomplete('daily"][x-data*="'${type}')"]`
      );
    }

    const ctx = el ? Alpine.$data(el) : null;
    if (!ctx) {
      console.warn("⚠️ addManualIfNotFound: konteks Alpine tidak ditemukan untuk", tab, type);
      return;
    }

    const text = ctx.query?.trim?.();
    if (!text) return;

    const found = (ctx.results || []).some(
      dx =>
        dx.name?.toLowerCase() === text.toLowerCase() ||
        dx.code?.toLowerCase() === text.toLowerCase()
    );

    if (!found) {
      const confirmAdd = confirm(
        `${type.charAt(0).toUpperCase() + type.slice(1)} "${text}" tidak ditemukan di database.\nTambahkan sebagai input manual baru?`
      );
      if (!confirmAdd) return;
      await window.addManualFromAutocomplete(tab, { name: text, code: null }, type);
      ctx.query = "";
      ctx.results = [];
    }
  }

  // Pure renderer untuk data pecahan (support core_engine format)
  function renderAI(rows, type, tab) {
    // 🔥 Support format core_engine (renderAI(diagnosis_array, "diagnosis", "admission"))
    if (type && tab) {
      // Map AI result to expected table row format
      const mappedRows = rows.map(item => ({
        kategori: item.parent || "",
        klinis: "", // parent klinis always strip  
        icd10_code: item.icd10_code || item.icd || "",
        icd9_code: item.icd9_code || "",
        procedure_text: item.tindakan || item.procedure_text || "",
        score: item.confidence || "",
        mapping: "", // Fill if needed
        children: (item.children && Array.isArray(item.children)) ? item.children.map(child => ({
          kategori: `→ ${child.name || ''}`,
          klinis: '', // always strip for child
          icd10_code: child.icd10_code || child.icd || '',
          icd9_code: child.icd9_code || '',
          procedure_text: child.tindakan || child.procedure_text || '',
          score: child.confidence || '',
          mapping: ""
        })) : []
      }));
      
      console.log(`🔥 DEBUG mappedRows for ${type}:`, mappedRows);
      
      // Render to specific target based on tab and type
      if (tab === "admission") {
        renderTable(`${type}-admission`, mappedRows, type, tab);
        return;
      }

      if (tab === "discharge") {
        renderTable(`${type}-discharge`, mappedRows, type, tab);
        return;
      }

      if (String(tab).startsWith("daily")) {
        const container = document.getElementById("daily-accordion");
        if (container && !document.getElementById(`section-${tab}`)) {
          container.insertAdjacentHTML("beforeend", `
            <details id="section-${tab}" class="border rounded">
              <summary class="cursor-pointer px-3 py-2 bg-gray-200 dark:bg-gray-700 flex items-center justify-between">
                <span class="font-semibold">Diagnosis</span>
                <span id="count-diagnosis-${tab}" class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">0</span>
              </summary>
              <div class="p-3 overflow-x-auto">
                <table class="w-full text-xs border" id="diagnosis-${tab}">
                  <tbody id="diagnosis-${tab}"></tbody>
                </table>
              </div>
            </details>

            <details class="border rounded">
              <summary class="cursor-pointer px-3 py-2 bg-gray-200 dark:bg-gray-700 flex items-center justify-between">
                <span class="font-semibold">Komorbid</span>
                <span id="count-komorbid-${tab}" class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">0</span>
              </summary>
              <div class="p-3 overflow-x-auto">
                <table class="w-full text-xs border" id="komorbid-${tab}">
                  <tbody id="komorbid-${tab}"></tbody>
                </table>
              </div>
            </details>

            <details class="border rounded">
              <summary class="cursor-pointer px-3 py-2 bg-gray-200 dark:bg-gray-700 flex items-center justify-between">
                <span class="font-semibold">Komplikasi</span>
                <span id="count-komplikasi-${tab}" class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">0</span>
              </summary>
              <div class="p-3 overflow-x-auto">
                <table class="w-full text-xs border" id="komplikasi-${tab}">
                  <tbody id="komplikasi-${tab}"></tbody>
                </table>
              </div>
            </details>
          `);
        }

        renderTable(`diagnosis-${tab}`, mappedRows.filter(r => r.category === "diagnosis"), "diagnosis", tab);
        renderTable(`komorbid-${tab}`, mappedRows.filter(r => r.category === "komorbid"), "komorbid", tab);
        renderTable(`komplikasi-${tab}`, mappedRows.filter(r => r.category === "komplikasi"), "komplikasi", tab);

        return;
      }
    }
  }

  function renderValue(val) {
    if (val && String(val).trim()) {
      return `<span class="block w-full truncate overflow-hidden">${val}</span>`;
    }
    return '<span class="block w-full text-center text-gray-400">-</span>';
  }

  function renderMappingSelect(item, tab, type) {
    const disabled = (window.claimState?.role !== 'doctor') ? 'disabled' : '';
    return `
      <select onchange="onMappingChange(event, '${tab}', '${type}', ${item.id})"
              class="border px-2 py-1 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-200 max-w-[120px] truncate"
              ${disabled}>
        <option value="" ${!item.mapping ? "selected" : ""}>Pilih</option>
        <option value="Diagnosis Utama" ${item.mapping==="Diagnosis Utama"?"selected":""}>Diagnosis Utama</option>
        <option value="Komorbid" ${item.mapping==="Komorbid"?"selected":""}>Komorbid</option>
        <option value="Komplikasi" ${item.mapping==="Komplikasi"?"selected":""}>Komplikasi</option>
        <option value="None" ${item.mapping==="None"?"selected":""}>None</option>
      </select>
    `;
  }  

  function renderTable(targetId, items, type, tab, dayId = null, skipManualRow = false) {
    const state = Alpine.$data(document.getElementById("claimRoot"));

    if (!state.simulasi[tab]) state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [] };

    // Filter AI vs Manual
    const oldItems = state.simulasi[tab][type] || [];
    const oldAiItems = oldItems.filter(it => !it.isManual);
    const manualItems = oldItems.filter(it => it.isManual);

    const newAiItems = (items || []).filter(it => !it.isManual);
    const aiItems = newAiItems.length > 0 ? newAiItems : oldAiItems;

    let merged;
    if (type === "tindakan") {
      merged = [...aiItems]; // manual tindakan terpisah
    } else {
      merged = [...aiItems, ...manualItems];
    }

    // Dedup
    const seen = new Set();
    merged = merged.filter(it => {
      const key = `${it.id}-${(it.nama_kategori || it.kategori || "").trim()}-${it.icd10_code || it.icd9_code || ""}-${it.tindakan || it.procedure_text || ""}-${it.child ? "child" : "parent"}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    state.simulasi[tab][type] = merged;

    const target = document.getElementById(targetId);
    if (!target) return;
    target.innerHTML = "";

    // Group parent/child
    let grouped = [];
    
    // 🔥 Handle both formats: core_engine (with children array) and legacy (with child flag)
    merged.forEach(it => {
      const name = (it.nama_kategori || it.kategori || "").trim();
      if (!name) return;
      
      // 🔥 Core_engine format: parent already has children array
      if (it.children && Array.isArray(it.children)) {
        grouped.push({
          ...it,
          kategori: name,
          nama_kategori: name,
          children: it.children || []
        });
      }
      // 🔥 Legacy format: child flag
      else if (it.child !== true) {
        grouped.push({
          ...it,
          kategori: name,
          nama_kategori: name,
          children: []
        });
      }
    });

    // Header (sekali per table)
    const table = target.closest("table");
    if (table && !table.querySelector("thead")) {
      const thead = document.createElement("thead");
      thead.className = "bg-gray-100 dark:bg-gray-800";
      thead.innerHTML = `
        <tr>
          <th class="border px-3 py-2 w-[20%]">Kategori</th>
          <th class="border px-3 py-2 w-[25%]">Klinis</th>
          <th class="border px-3 py-2 w-[10%]">ICD</th>
          <th class="border px-3 py-2 w-[25%]">Tindakan</th>
          <th class="border px-3 py-2 w-[10%]">Score</th>
          ${state.role === "doctor" ? `<th class="border px-3 py-2 w-[10%]">Mapping</th>` : ``}
        </tr>`;
      table.insertBefore(thead, table.firstChild);
    }

    // Render rows
    grouped.forEach((parent, idx) => {
      const counter = 1 + (parent.children ? parent.children.length : 0);
      const tbody = document.createElement("tbody");
      tbody.setAttribute("x-data", "{ open:true }");

      const tindakanText = parent.tindakan || parent.procedure_text || "";
      const klinisText = parent.klinis || "";
      const icdText = parent.icd10_code || parent.icd9_code || "";
      const titleTindakan = tindakanText;
      const titleKlinis = klinisText;

      tbody.insertAdjacentHTML("beforeend", `
        <tr class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 font-medium text-sm"
          data-id="${dayId || tab}-${type}-${idx}"
          data-db-id="${parent.id || ''}"
          data-row='${parent.rowData ? JSON.stringify(parent.rowData) : ""}'>
            <td class="border px-5 py-2 whitespace-nowrap overflow-hidden text-ellipsis">
              <span @click="open=!open" class="mr-1 cursor-pointer">
                <span x-show="!open" x-cloak>▶</span>
                <span x-show="open" x-cloak>▼</span>
              </span>
              <span onclick="window.openModalFromAttr && window.openModalFromAttr(this, '${type}')" class="text-blue-600 underline">${parent.kategori || parent.nama_kategori || ""}</span>
              <span class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">${counter}</span>
            </td>
            <td class="col-klinis border px-3 py-2 w-[25%]">
              <span class="block w-full truncate" title="${titleKlinis}">${renderValue(klinisText)}</span>
            </td>
            <td class="col-icd border px-3 py-2 w-[10%] text-center">${renderValue(icdText)}</td>
            <td class="col-tindakan border px-3 py-2">
              <span class="block w-full truncate" title="${titleTindakan}">${renderValue(tindakanText)}</span>
            </td>
            <td class="border px-3 py-2 text-center">
              <span class="block w-full truncate">${renderValue(parent.score)}</span>
            </td>
            ${state.role === "doctor" ? `
            <td class="border px-3 py-2 text-center">
              ${renderMappingSelect(parent, tab, type)}
            </td>` : ``}
          </tr>
      `);

      parent.children.forEach((child, cIdx) => {
        const tText = child.tindakan || child.procedure_text || "";
        const kText = child.klinis || "";
        const iText = child.icd10_code || child.icd9_code || "";

        tbody.insertAdjacentHTML("beforeend", `
          <tr x-show="open" x-cloak
            class="bg-gray-50 dark:bg-gray-800 italic text-sm"
            data-id="child-${dayId || tab}-${type}-${idx}-${cIdx}"
            data-db-id="${child.id || ''}"
            data-row='${child.rowData ? JSON.stringify(child.rowData) : ""}'>
            <td class="border px-5 py-2 cursor-pointer whitespace-nowrap overflow-hidden text-ellipsis"
                onclick="window.openModalFromAttr && window.openModalFromAttr(this, '${type}')">
              ${child.nama_kategori || child.kategori || "-"}
            </td>
            <td class="col-klinis border px-6 py-2 whitespace-nowrap">
              <span class="block w-full truncate">${renderValue(kText)}</span>
            </td>
            <td class="col-icd border px-3 py-2 text-center">
              <span class="block w-full truncate">${renderValue(iText)}</span>
            </td>
            <td class="col-tindakan border px-6 py-2 whitespace-nowrap overflow-hidden text-ellipsis" title="${tText}">
              <span class="block w-full truncate">${renderValue(tText)}</span>
            </td>
            <td class="border px-3 py-2 text-center">
              <span class="block w-full truncate">${renderValue(child.score)}</span>
            </td>
            ${state.role === "doctor" ? `
            <td class="border px-3 py-2 text-center">
              ${renderMappingSelect(child, tab, type)}
            </td>` : ``}
          </tr>
        `);
      });

      target.appendChild(tbody);
      Alpine.initTree(tbody);
    });

    // Counter badge
    const counterId = dayId ? `count-${type}-${dayId}` : `count-${type}-${tab}`;
    const countEl = document.getElementById(counterId);
    if (countEl) {
      let total = grouped.reduce((sum, p) => sum + 1 + p.children.length, 0);
      countEl.textContent = total;
    }
    if (dayId) {
      const dailyCounter = document.getElementById(`count-daily-${dayId}`);
      if (dailyCounter) {
        const totalDaily =
          (parseInt(document.getElementById(`count-diagnosis-${dayId}`)?.textContent) || 0) +
          (parseInt(document.getElementById(`count-komorbid-${dayId}`)?.textContent) || 0) +
          (parseInt(document.getElementById(`count-komplikasi-${dayId}`)?.textContent) || 0);
        dailyCounter.textContent = totalDaily;
      }
    }

    // Manual row (input) untuk doctor
    if (!skipManualRow && (Alpine.$data(document.getElementById("claimRoot")).role === "doctor")) {
      if (tab === "admission" || tab === "discharge" || String(tab).startsWith("daily-")) {
        const manualTbody = document.createElement("tbody");
        if (!state.manualInput) state.manualInput = {};
        if (!state.manualInput.daily) state.manualInput.daily = {};
        if (!state.manualInput.daily[tab]) {
          state.manualInput.daily[tab] = { diagnosis: {}, komorbid: {}, komplikasi: {} };
        }
       const tabPath = String(tab).startsWith("daily-")
        ? `manualInput.daily[\`${tab}\`].${type}`
        : `manualInput.${tab}.${type}`;

        manualTbody.insertAdjacentHTML("beforeend", `
          <tr class="manual-row bg-gray-50 dark:bg-gray-800">
            <td class="border px-3 py-2 whitespace-nowrap relative overflow-visible max-w-[180px]">
              <div x-data="diagnosisAutocomplete('${tab}', '${tabPath}', '${type}')" class="relative">
                <input type="text"
                      x-model="query"
                      @input.debounce.300ms="search"
                      @keydown.enter.prevent="results.length ? select(results[0]) : addManualIfNotFound()"
                      placeholder="Cari diagnosis..."
                      class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900
                              text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600">

                <!-- dropdown suggestion -->
                <ul x-show="results.length > 0"
                    class="absolute left-0 top-full mt-1 z-[9999] bg-white dark:bg-gray-800 border w-full rounded max-h-40 overflow-y-auto shadow-lg">
                  <template x-for="item in results" :key="item.code">
                    <li @click="select(item)"
                        class="px-2 py-1 cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700"
                        x-text="item.code + ' - ' + item.name"></li>
                  </template>
                </ul>
              </div>
            </td>
            <td class="col-klinis border px-6 py-2 whitespace-nowrap overflow-hidden text-ellipsis max-w-[200px]">
              <input x-model="${tabPath}.klinis" placeholder="Klinis" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600">
            </td>
            <td class="col-icd border px-3 py-2">
              <input x-model="${tabPath}.icd10_code" placeholder="ICD-10" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600">
            </td>
            <td class="col-tindakan border px-3 py-2 whitespace-nowrap overflow-hidden text-ellipsis max-w-[180px]">
              <input x-model="${tabPath}.procedure_text" placeholder="Tindakan" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600">
            </td>
            <td class="border px-3 py-2">
              <input x-model="${tabPath}.score" placeholder="Score" readonly class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600">
            </td>
            <td class="border px-3 py-2 text-center">
              <button type="button" @click="addManualIfNotFound('${tab}', '${type}')" class="bg-green-600 text-white px-2 py-1 rounded">➕</button>
            </td>
          </tr>
        `);

        target.appendChild(manualTbody);
        Alpine.initTree(manualTbody);
      }
    }
  }

  // export
  window.diagnosisAutocomplete = diagnosisAutocomplete;
  window.renderAI = renderAI;
  window.renderTable = renderTable;
  window.addManualIfNotFound = addManualIfNotFound;
  window.renderValue = renderValue;
  window.renderMappingSelect = renderMappingSelect;
})();
