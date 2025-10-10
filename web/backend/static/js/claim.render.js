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

  // ================= Diagnosis Autocomplete =================
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



  // Pure renderer untuk data pecahan
  function renderAI(rows) {
    attachTindakan(rows);

    const admission = rows.filter(r => r.stage === "admission");
    const daily = rows.filter(r => r.stage && r.stage.startsWith("daily"));
    const discharge = rows.filter(r => r.stage === "discharge");

    // Admission
    renderTable("diagnosis-admission", admission.filter(r => r.category==="diagnosis"), "diagnosis", "admission");
    renderTable("komorbid-admission", admission.filter(r => r.category==="komorbid"), "komorbid", "admission");
    renderTable("komplikasi-admission", admission.filter(r => r.category==="komplikasi"), "komplikasi", "admission");

    // Daily (accordion per hari)
    const dailyContainer = document.getElementById("daily-accordion");
    if (dailyContainer) dailyContainer.innerHTML = "";

    const groupedDaily = {};
    daily.forEach(r => {
      if (!groupedDaily[r.stage]) groupedDaily[r.stage] = [];
      groupedDaily[r.stage].push(r);
    });

    Object.keys(groupedDaily).forEach((stage, idx) => {
      const hari = groupedDaily[stage];
      const dayId = `daily-${idx}`;

      window.ensureDaily && window.ensureDaily(dayId);

      dailyContainer && dailyContainer.insertAdjacentHTML("beforeend", `
        <div class="bg-white dark:bg-gray-700 rounded shadow-sm mb-2" x-data="{open:false}">
          <button type="button" @click="open=!open"
            class="w-full flex justify-between px-4 py-2 bg-gray-200 dark:bg-gray-600 font-semibold">
            <span>Hari ${idx+1} </span>
            <div class="flex items-center gap-3">
              <span id="count-daily-${dayId}" class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">0</span>
              <span x-show="open">⬆</span>
              <span x-show="!open">⬇</span>
            </div>
          </button>
          <div x-show="open" class="p-2 space-y-2">
            ${["diagnosis","komorbid","komplikasi"].map(k => `
              <details class="border rounded">
                <summary class="cursor-pointer px-3 py-2 bg-gray-200 dark:bg-gray-700 flex items-center justify-between">
                  <span class="font-semibold">${k[0].toUpperCase() + k.slice(1)}</span>
                  <span id="count-${k}-${dayId}"
                        class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">0</span>
                </summary>
                <div class="p-3 overflow-x-auto">
                  <table class="w-full text-xs border" id="${k}-${dayId}">
                    <tbody id="${k}-${dayId}"></tbody>
                  </table>
                </div>
              </details>
            `).join("")}
          </div>
        </div>
      `);

      renderTable(`diagnosis-${dayId}`, hari.filter(r => r.category==="diagnosis"), "diagnosis", dayId);
      renderTable(`komorbid-${dayId}`, hari.filter(r => r.category==="komorbid"), "komorbid", dayId);
      renderTable(`komplikasi-${dayId}`, hari.filter(r => r.category==="komplikasi"), "komplikasi", dayId);

      const dailyCounter = document.getElementById(`count-daily-${dayId}`);
      if (dailyCounter) {
        const totalDaily =
          (parseInt(document.getElementById(`count-diagnosis-${dayId}`)?.textContent || 0)) +
          (parseInt(document.getElementById(`count-komorbid-${dayId}`)?.textContent || 0)) +
          (parseInt(document.getElementById(`count-komplikasi-${dayId}`)?.textContent || 0));
        dailyCounter.textContent = totalDaily;
      }
    });

    // Discharge
    renderTable("diagnosis-discharge", discharge.filter(r => r.category==="diagnosis"), "diagnosis", "discharge");
    renderTable("komorbid-discharge", discharge.filter(r => r.category==="komorbid"), "komorbid", "discharge");
    renderTable("komplikasi-discharge", discharge.filter(r => r.category==="komplikasi"), "komplikasi", "discharge");
  }

  function renderMappingSelect(item, tab, type) {
    const disabled = (window.claimState?.role !== 'doctor') ? 'disabled' : '';
    return `
      <select onchange="onMappingChange(event, '${tab}', '${type}', '${item.id}')"
              class="border px-2 py-1 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-200 max-w-[200px] truncate"
              ${disabled}>
        <option value="" ${!item.mapping ? "selected" : ""}>Pilih</option>
        <option value="Diagnosis Utama" ${item.mapping==="Diagnosis Utama"?"selected":""}>Diagnosis Utama</option>
        <option value="Komorbid" ${item.mapping==="Komorbid"?"selected":""}>Komorbid</option>
        <option value="Komplikasi" ${item.mapping==="Komplikasi"?"selected":""}>Komplikasi</option>
        <option value="None" ${item.mapping==="None"?"selected":""}>None</option>
      </select>
    `;
  }

  function renderValue(val) {
    if (val && String(val).trim()) {
      return `<span class="block w-full truncate overflow-hidden">${val}</span>`;
    }
    return '<span class="block w-full text-center text-gray-400">-</span>';
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

    if (aiItems.length === 0 && type === "tindakan") {
      if (tbody) {
        tbody.innerHTML = `
          <tr>
            <td colspan="3" class="text-center italic text-gray-500 py-2">
              Menunggu hasil AI...
            </td>
          </tr>`;
      }
      return; // jangan lanjut render tabel kosong
    }

    let merged;
    if (type === "tindakan") {
      merged = aiItems.filter(it => it.procedure_text && it.procedure_text !== "-");
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

    // Store parent items and flatten children into the main array for mapping
    const flatItems = [];
    merged.forEach(item => {
      flatItems.push(item);
      if (item.children && Array.isArray(item.children)) {
        item.children.forEach((child, childIdx) => {
          // Give each child a unique ID for mapping
          child.id = child.id || `${item.id || 'parent'}-child-${childIdx}`;
          child.parentId = item.id;
          flatItems.push(child);
        });
      }
    });
    state.simulasi[tab][type] = flatItems;

    const target = document.getElementById(targetId);
    if (!target) return;
    target.innerHTML = "";

    // Group parent/child for rendering - rebuild hierarchy
    let grouped = [];
    let parentMap = {};
    let lastParentKey = null;

    merged.forEach(it => {
      const name = (it.nama_kategori || it.kategori || "").trim();
      if (!name) return;
      const itemType = it.type || type || "diagnosis";

      // 🔥 Core_engine format: parent already has children array
      if (it.children && Array.isArray(it.children)) {
        const parentWithChildren = {
          ...it,
          kategori: name,
          nama_kategori: name,
          children: it.children.map(child => ({
            ...child,
            kategori: child.nama_kategori || child.kategori || child.name || '-',
            nama_kategori: child.nama_kategori || child.kategori || child.name || '-',
            klinis: child.klinis || '-',
            icd10_code: child.icd10_code || child.icd || '-',
            procedure_text: child.tindakan || child.procedure_text || '-',
            score: child.score || child.confidence || '-',
            id: child.id || `${it.id || 'parent'}-child-${child.name}` // ensure child has ID
          }))
        };
        grouped.push(parentWithChildren);
      }
      // 🔥 Development branch format: child flag
      else if (it.child === true) {
        if (lastParentKey && parentMap[lastParentKey]) {
          const childWithId = {
            ...it,
            kategori: `${name} ${String.fromCharCode(97 + parentMap[lastParentKey].children.length)}`,
            nama_kategori: name,
            id: it.id || `${parentMap[lastParentKey].id}-child-${parentMap[lastParentKey].children.length}`
          };
          parentMap[lastParentKey].children.push(childWithId);
        }
      } else {
        const parentKey = `${itemType}:${name}`;
        parentMap[parentKey] = { ...it, kategori: name, nama_kategori: name, children: [] };
        grouped.push(parentMap[parentKey]);
        lastParentKey = parentKey;
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
      tbody.setAttribute("x-data", "{ open:false }");

      const tindakanText = parent.tindakan || parent.procedure_text;
      const klinisText = parent.klinis;
      const icdText = parent.icd10_code || parent.icd9_code;
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
              <span onclick="window.openModalFromAttr && window.openModalFromAttr(this, '${type}')" class="text-blue-600 underline">${parent.kategori || parent.nama_kategori}</span>
              <span class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">${counter}</span>
            </td>
            <td class="col-klinis border px-3 py-2 w-[25%]">
              <span class="block w-full truncate">${renderValue(klinisText)}</span>
            </td>
            <td class="col-icd border px-3 py-2 w-[10%] text-center">
              <span class="block w-full truncate">${renderValue(icdText)}</span>
            </td>
            <td class="col-tindakan border px-3 py-2 w-[25%]">
              <span class="block w-full truncate">${renderValue(tindakanText)}</span>
            </td>
            <td class="border px-3 py-2 w-[10%] text-center">
              <span class="block w-full truncate">${renderValue(parent.score)}</span>
            </td>
            ${state.role === "doctor" ? `
            <td class="border px-3 py-2 text-center">
              ${renderMappingSelect(parent, tab, type)}
            </td>` : ``}
          </tr>
      `);

      parent.children.forEach((child, cIdx) => {
        const tText = child.tindakan || child.procedure_text;
        const kText = child.klinis;
        const iText = child.icd10_code || child.icd9_code;

        tbody.insertAdjacentHTML("beforeend", `
          <tr x-show="open" x-cloak
            class="bg-gray-50 dark:bg-gray-800 italic text-sm"
            data-id="child-${dayId || tab}-${type}-${idx}-${cIdx}"
            data-db-id="${child.id || ''}"
            data-row='${child.rowData ? JSON.stringify(child.rowData) : ""}'>
            <td class="border px-5 py-2 cursor-pointer whitespace-nowrap overflow-hidden text-ellipsis"
                onclick="window.openModalFromAttr && window.openModalFromAttr(this, '${type}')">
              ${child.nama_kategori || child.kategori}
            </td>
            <td class="col-klinis border px-3 py-2 w-[25%] italic" title="${kText}">
              <span class="block w-full truncate">${renderValue(kText)}</span>
            </td>
            <td class="col-icd border px-3 py-2 w-[10%] text-center" title="${iText}">
              <span class="block w-full truncate">${renderValue(iText)}</span>
            </td>
            <td class="col-tindakan border px-3 py-2 w-[25%] italic" title="${tText}">
              <span class="block w-full truncate">${renderValue(tText)}</span>
            </td>
            <td class="border px-3 py-2 text-center w-[10%]">
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
                      placeholder="Cari penyakit..."
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
    // === Sinkron render list tindakan manual di modal ===
    if (type === "diagnosis" && typeof window.renderManualTindakanList === "function") {
      setTimeout(() => window.renderManualTindakanList(tab), 0);
    }
  }


  // export
  window.diagnosisAutocomplete = diagnosisAutocomplete;
  window.renderAI = renderAI;
  window.renderTable = renderTable;
  window.addManualIfNotFound = addManualIfNotFound;
})();