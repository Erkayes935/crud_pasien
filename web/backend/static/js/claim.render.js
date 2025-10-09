// =============== Rendering simulasi, tabel, dan mapping select (FULL HYBRID VERSION) ===============

(function () {
  // ========================== 🔹 Helper: Hubungkan tindakan ke diagnosis ==========================
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

  // ========================== 🔹 Diagnosis Autocomplete ==========================
  function diagnosisAutocomplete(tab, tabPath, type = "diagnosis") {
    return {
      query: "",
      results: [],
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
      async select(item) {
        this.query = `${item.code} - ${item.name}`;
        this.results = [];
        await window.addManualFromAutocomplete(tab, item, type);
      },
      async addManualIfNotFound() {
        await window.addManualIfNotFound(tab, type);
      },
    };
  }

  // ========================== 🔹 Fungsi Global: Tambah Manual Jika Tidak Ditemukan ==========================
  async function addManualIfNotFound(tab, type = "diagnosis") {
    let el = document.querySelector(
      `[x-data*="diagnosisAutocomplete('${tab}'"][x-data*="'${type}')"]`
    );

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

  // ========================== 🔹 Utility Render Value ==========================
  function renderValue(val) {
    if (val && String(val).trim()) {
      return `<span class="block w-full truncate overflow-hidden">${val}</span>`;
    }
    return '<span class="block w-full text-center text-gray-400">-</span>';
  }

  // ========================== 🔹 Utility Render Mapping Select ==========================
  function renderMappingSelect(item, tab, type) {
    const disabled = (window.claimState?.role !== 'doctor') ? 'disabled' : '';
    return `
      <select onchange="onMappingChange(event, '${tab}', '${type}', '${item.id}')"
              class="border px-2 py-1 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-200 max-w-[200px] truncate text-sm"
              ${disabled}>
        <option value="" ${!item.mapping ? "selected" : ""}>Pilih</option>
        <option value="Diagnosis Utama" ${item.mapping==="Diagnosis Utama"?"selected":""}>Diagnosis Utama</option>
        <option value="Komorbid" ${item.mapping==="Komorbid"?"selected":""}>Komorbid</option>
        <option value="Komplikasi" ${item.mapping==="Komplikasi"?"selected":""}>Komplikasi</option>
        <option value="None" ${item.mapping==="None"?"selected":""}>None</option>
      </select>
    `;
  }

  // ========================== 🔹 Pure Renderer: Render AI (Support both formats) ==========================
  function renderAI(rows, type, tab) {
    if (!Array.isArray(rows) || rows.length === 0) return;

    // Support legacy full array format
    if (!type && !tab) {
      attachTindakan(rows);
      const admission = rows.filter(r => r.stage === "admission");
      const daily = rows.filter(r => r.stage?.startsWith("daily"));
      const discharge = rows.filter(r => r.stage === "discharge");

      // Admission
      renderTable("diagnosis-admission", admission.filter(r => r.category==="diagnosis"), "diagnosis", "admission");
      renderTable("komorbid-admission", admission.filter(r => r.category==="komorbid"), "komorbid", "admission");
      renderTable("komplikasi-admission", admission.filter(r => r.category==="komplikasi"), "komplikasi", "admission");

      // Daily
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
              <span>Hari ${idx+1}</span>
              <div class="flex items-center gap-3">
                <span id="count-daily-${dayId}" class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">0</span>
                <span x-show="open">⬆</span>
                <span x-show="!open">⬇</span>
              </div>
            </button>
            <div x-show="open" class="p-2 space-y-2">
              ${["diagnosis","komorbid","komplikasi"].map(k => `
                <details class="border rounded">
                  <summary class="cursor-pointer px-3 py-2 bg-gray-200 dark:bg-gray-700 flex justify-between">
                    <span class="font-semibold">${k[0].toUpperCase() + k.slice(1)}</span>
                    <span id="count-${k}-${dayId}" class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">0</span>
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
      });

      // Discharge
      renderTable("diagnosis-discharge", discharge.filter(r => r.category==="diagnosis"), "diagnosis", "discharge");
      renderTable("komorbid-discharge", discharge.filter(r => r.category==="komorbid"), "komorbid", "discharge");
      renderTable("komplikasi-discharge", discharge.filter(r => r.category==="komplikasi"), "komplikasi", "discharge");
      return;
    }

    // Support modular renderAI(rows, type, tab)
    const mappedRows = rows.map(item => ({
      kategori: item.parent || item.kategori || "-",
      klinis: item.klinis || "-",
      icd10_code: item.icd10_code || item.icd || "-",
      icd9_code: item.icd9_code || "-",
      procedure_text: item.tindakan || item.procedure_text || "-",
      score: item.confidence || item.score || "-",
      mapping: item.mapping || "",
      children: Array.isArray(item.children)
        ? item.children.map(c => ({
            kategori: c.name || c.kategori || "-",
            klinis: c.klinis || "-",
            icd10_code: c.icd10_code || c.icd || "-",
            procedure_text: c.procedure_text || c.tindakan || "-",
            score: c.confidence || c.score || "-",
            mapping: c.mapping || "",
          }))
        : [],
    }));
    renderTable(`${type}-${tab}`, mappedRows, type, tab);
  }

  // ========================== 🔹 Core Renderer: Render Tabel ==========================
  function renderTable(targetId, items, type, tab, dayId = null, skipManualRow = false) {
    const state = Alpine.$data(document.getElementById("claimRoot"));
    if (!state.simulasi[tab]) state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [] };

    // Filter AI & Manual
    const oldItems = state.simulasi[tab][type] || [];
    const oldAiItems = oldItems.filter(it => !it.isManual);
    const manualItems = oldItems.filter(it => it.isManual);
    const newAiItems = (items || []).filter(it => !it.isManual);
    const aiItems = newAiItems.length > 0 ? newAiItems : oldAiItems;

    let merged = [...aiItems, ...manualItems];

    // Dedup
    const seen = new Set();
    merged = merged.filter(it => {
      const key = `${it.id || ""}-${it.kategori || ""}-${it.icd10_code || ""}-${it.procedure_text || ""}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    // Flatten children
    const flatItems = [];
    merged.forEach(item => {
      flatItems.push(item);
      if (item.children) item.children.forEach(child => flatItems.push(child));
    });
    state.simulasi[tab][type] = flatItems;

    const target = document.getElementById(targetId);
    if (!target) return;
    target.innerHTML = "";

    // Group parent-child
    const grouped = merged.map(it => ({
      ...it,
      children: Array.isArray(it.children) ? it.children : [],
    }));

    // Header
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
          ${state.role === "doctor" ? `<th class="border px-3 py-2 w-[10%]">Mapping</th>` : ""}
        </tr>`;
      table.insertBefore(thead, table.firstChild);
    }

    // Rows
    grouped.forEach((p, idx) => {
      const tbody = document.createElement("tbody");
      tbody.setAttribute("x-data", "{ open:false }");

      tbody.insertAdjacentHTML("beforeend", `
        <tr class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 font-medium text-sm">
          <td class="border px-4 py-2">
            <span @click="open=!open" class="mr-1 cursor-pointer">▶</span>
            <span onclick="window.openModalFromAttr && window.openModalFromAttr(this, '${type}')"
                  class="text-blue-600 underline">${p.kategori || "-"}</span>
            <span class="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded">${1 + (p.children?.length || 0)}</span>
          </td>
          <td class="border px-3 py-2">${renderValue(p.klinis)}</td>
          <td class="border px-3 py-2 text-center">${renderValue(p.icd10_code)}</td>
          <td class="border px-3 py-2">${renderValue(p.procedure_text)}</td>
          <td class="border px-3 py-2 text-center">${renderValue(p.score)}</td>
          ${state.role === "doctor" ? `<td class="border px-3 py-2 text-center">${renderMappingSelect(p, tab, type)}</td>` : ""}
        </tr>
        ${p.children.map((c, i) => `
          <tr x-show="open" x-cloak class="bg-gray-50 dark:bg-gray-800 italic text-sm">
            <td class="border px-5 py-2 cursor-pointer"
                onclick="window.openModalFromAttr && window.openModalFromAttr(this, '${type}')">${c.kategori || "-"}</td>
            <td class="border px-3 py-2">${renderValue(c.klinis)}</td>
            <td class="border px-3 py-2 text-center">${renderValue(c.icd10_code)}</td>
            <td class="border px-3 py-2">${renderValue(c.procedure_text)}</td>
            <td class="border px-3 py-2 text-center">${renderValue(c.score)}</td>
            ${state.role === "doctor" ? `<td class="border px-3 py-2 text-center">${renderMappingSelect(c, tab, type)}</td>` : ""}
          </tr>
        `).join("")}
      `);

      target.appendChild(tbody);
      Alpine.initTree(tbody);
    });

    // Manual input baris bawah (untuk dokter)
    if (!skipManualRow && state.role === "doctor") {
      if (tab === "admission" || tab === "discharge" || String(tab).startsWith("daily-")) {
        const manualTbody = document.createElement("tbody");
        const tabPath = String(tab).startsWith("daily-")
          ? `manualInput.daily[\`${tab}\`].${type}`
          : `manualInput.${tab}.${type}`;

        manualTbody.insertAdjacentHTML("beforeend", `
          <tr class="manual-row bg-gray-50 dark:bg-gray-800">
            <td class="border px-3 py-2 whitespace-nowrap relative overflow-visible max-w-[180px]">
              <div x-data="diagnosisAutocomplete('${tab}', '${tabPath}', '${type}')" class="relative">
                <input type="text" x-model="query" @input.debounce.300ms="search"
                  @keydown.enter.prevent="results.length ? select(results[0]) : addManualIfNotFound()"
                  placeholder="Cari diagnosis..."
                  class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900
                         text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600">
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
            <td class="border px-3 py-2"><input x-model="${tabPath}.klinis" placeholder="Klinis" readonly class="input"/></td>
            <td class="border px-3 py-2"><input x-model="${tabPath}.icd10_code" placeholder="ICD-10" readonly class="input"/></td>
            <td class="border px-3 py-2"><input x-model="${tabPath}.procedure_text" placeholder="Tindakan" readonly class="input"/></td>
            <td class="border px-3 py-2"><input x-model="${tabPath}.score" placeholder="Score" readonly class="input"/></td>
            <td class="border px-3 py-2 text-center"><button type="button" @click="addManualIfNotFound('${tab}', '${type}')" class="bg-green-600 text-white px-2 py-1 rounded">➕</button></td>
          </tr>
        `);
        target.appendChild(manualTbody);
        Alpine.initTree(manualTbody);
      }
    }
  }

  // ========================== 🔹 Exports ==========================
  window.diagnosisAutocomplete = diagnosisAutocomplete;
  window.addManualIfNotFound = addManualIfNotFound;
  window.renderAI = renderAI;
  window.renderTable = renderTable;
  window.renderValue = renderValue;
  window.renderMappingSelect = renderMappingSelect;
})();
