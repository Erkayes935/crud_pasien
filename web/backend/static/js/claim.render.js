// =============== Rendering simulasi, tabel, dan mapping select ===============
(function () {
  // =============== Updated hasRole Function (Multi-Role Support) ===============
  /**
   * Cek apakah user memiliki role tertentu (mendukung multi-role)
   * @param {string} roleName - Nama role yang dicek (case-insensitive)
   * @returns {boolean} - true jika user memiliki role tersebut
   */
  function hasRole(roleName) {
    try {
      const state = window.claimState || {};
      let userRoles = [];

      // Prioritas 1: Ambil dari roles array (multi-role system)
      if (Array.isArray(state.roles) && state.roles.length > 0) {
        userRoles = state.roles.map(r => {
          // Handle jika roles berupa object {id, name}
          if (typeof r === 'object' && r.name) {
            return r.name.toLowerCase();
          }
          // Handle jika roles berupa string
          return String(r).toLowerCase();
        });
      }
      // Prioritas 2: Fallback ke role_names array
      else if (Array.isArray(state.role_names) && state.role_names.length > 0) {
        userRoles = state.role_names.map(r => String(r).toLowerCase());
      }
      // Prioritas 3: Fallback ke single role (legacy)
      else if (state.role) {
        userRoles = [String(state.role).toLowerCase()];
      }
      // Prioritas 4: Fallback ke backend context window.roles
      else if (Array.isArray(window.roles) && window.roles.length > 0) {
        userRoles = window.roles.map(r => {
          if (typeof r === 'object' && r.name) {
            return r.name.toLowerCase();
          }
          return String(r).toLowerCase();
        });
      }

      // Normalize input role name
      const normalizedRoleName = String(roleName).toLowerCase().trim();

      // Cek apakah user memiliki role yang dicari
      const hasTheRole = userRoles.includes(normalizedRoleName);

      // Debug log (opsional, bisa dihapus di production)
      if (window.DEBUG_ROLES) {
        console.log('[hasRole] Check:', {
          searching: normalizedRoleName,
          userRoles: userRoles,
          result: hasTheRole
        });
      }

      return hasTheRole;

    } catch (e) {
      console.warn("[hasRole] Error checking role:", e);
      return false;
    }
  }

  /**
   * Cek apakah user memiliki salah satu dari beberapa role
   * @param {string[]} roleNames - Array nama role yang dicek
   * @returns {boolean} - true jika user memiliki minimal 1 role
   */
  function hasAnyRole(roleNames) {
    if (!Array.isArray(roleNames)) {
      return false;
    }
    return roleNames.some(roleName => hasRole(roleName));
  }

  /**
   * Cek apakah user memiliki semua role yang disebutkan
   * @param {string[]} roleNames - Array nama role yang dicek
   * @returns {boolean} - true jika user memiliki semua role
   */
  function hasAllRoles(roleNames) {
    if (!Array.isArray(roleNames)) {
      return false;
    }
    return roleNames.every(roleName => hasRole(roleName));
  }

  /**
   * Get semua role yang dimiliki user (untuk debugging/display)
   * @returns {string[]} - Array nama role user
   */
  function getUserRoles() {
    try {
      const state = window.claimState || {};
      
      if (Array.isArray(state.roles) && state.roles.length > 0) {
        return state.roles.map(r => {
          if (typeof r === 'object' && r.name) return r.name;
          return String(r);
        });
      }
      
      if (Array.isArray(state.role_names) && state.role_names.length > 0) {
        return state.role_names;
      }
      
      if (state.role) {
        return [state.role];
      }
      
      if (Array.isArray(window.roles) && window.roles.length > 0) {
        return window.roles.map(r => {
          if (typeof r === 'object' && r.name) return r.name;
          return String(r);
        });
      }
      
      return [];
    } catch (e) {
      console.warn("[getUserRoles] Error:", e);
      return [];
    }
  }

  // =============== Utility Functions ===============
  // Hilangkan "-" dari data AI sebelum render
  function cleanValue(val) {
    if (val === "-" || val === " - " || val === "—") return "";
    if (typeof val === "string") return val.trim() === "-" ? "" : val.trim();
    return val;
  }

  function cleanObject(obj) {
    if (Array.isArray(obj)) return obj.map(cleanObject);
    if (obj && typeof obj === "object") {
      const cleaned = {};
      for (const [key, value] of Object.entries(obj)) {
        cleaned[key] = cleanObject(value);
      }
      return cleaned;
    }
    return cleanValue(obj);
  }

  function attachTindakan(rows) {
    const tindakanAll = rows.filter(r => r.category === "tindakan");
    rows.forEach(d => {
      const arr = tindakanAll.filter(
        t => t.stage === d.stage &&
          (t.diagnosis_id === d.id || t.diagnosis_code === d.icd10_code)
      );
      d.tindakan = arr.length ? cleanObject(arr) : "";
    });
  }

  // ================= Diagnosis Autocomplete =================
  function diagnosisAutocomplete(tab, tabPath, type = "diagnosis") {
    // 🧩 fix: redirect tab daily -> daily-global sejak awal
    if (tab === "daily") tab = "daily-global";

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

  async function addManualIfNotFound(tab, type = "diagnosis") {
    // 🧩 fix: redirect tab daily -> daily-global sejak awal
    if (tab === "daily") tab = "daily-global";

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
      const confirmAdd = await showConfirmModal(
        `${type.charAt(0).toUpperCase() + type.slice(1)} tidak ditemukan`,
        `${type.charAt(0).toUpperCase() + type.slice(1)} "${text}" tidak ditemukan di database.<br>Tambahkan sebagai input manual baru?`
      );
      if (!confirmAdd) return;

      await window.addManualFromAutocomplete(tab, { name: text, code: null }, type);
      ctx.query = "";
      ctx.results = [];
    }
  }

  // ================= Render AI =================
  function renderAI(rows) {
    if (!Array.isArray(rows)) return;

    rows = cleanObject(rows);   // bersihkan data
    attachTindakan(rows);

    const admission = rows.filter(r => r.stage === "admission");
    const daily = rows.filter(r => r.stage && r.stage.startsWith("daily"));
    const discharge = rows.filter(r => r.stage === "discharge");

    // ====================== ADMISSION ======================
    renderTable(
      "diagnosis-admission",
      admission.filter(r => r.category === "diagnosis"),
      "diagnosis",
      "admission"
    );
    renderTable(
      "komorbid-admission",
      admission.filter(r => r.category === "komorbid"),
      "komorbid",
      "admission"
    );
    renderTable(
      "komplikasi-admission",
      admission.filter(r => r.category === "komplikasi"),
      "komplikasi",
      "admission"
    );

    // ====================== DAILY (GLOBAL) ======================
    renderTable(
      "diagnosis-daily",
      daily.filter(r => r.category === "diagnosis"),
      "diagnosis",
      "daily-global"   // ✅ was "daily"
    );
    renderTable(
      "komorbid-daily",
      daily.filter(r => r.category === "komorbid"),
      "komorbid",
      "daily-global"
    );
    renderTable(
      "komplikasi-daily",
      daily.filter(r => r.category === "komplikasi"),
      "komplikasi",
      "daily-global"
    );

    // 📢 Hitung total global Daily (Diagnosis + Komorbid + Komplikasi)
    const dailyCounter = document.getElementById("count-daily-global");
    if (dailyCounter) {
      const totalDaily =
        (parseInt(document.getElementById("count-diagnosis-daily")?.textContent || 0)) +
        (parseInt(document.getElementById("count-komorbid-daily")?.textContent || 0)) +
        (parseInt(document.getElementById("count-komplikasi-daily")?.textContent || 0));
      dailyCounter.textContent = totalDaily;
    }

    // ====================== DISCHARGE ======================
    renderTable(
      "diagnosis-discharge",
      discharge.filter(r => r.category === "diagnosis"),
      "diagnosis",
      "discharge"
    );
    renderTable(
      "komorbid-discharge",
      discharge.filter(r => r.category === "komorbid"),
      "komorbid",
      "discharge"
    );
    renderTable(
      "komplikasi-discharge",
      discharge.filter(r => r.category === "komplikasi"),
      "komplikasi",
      "discharge"
    );

    // ====================== AUTO-OPEN SEMUA SECTION ======================
    document
      .querySelectorAll(
        "#diagnosis-admission, #komorbid-admission, #komplikasi-admission, \
        #diagnosis-daily, #komorbid-daily, #komplikasi-daily, \
        #diagnosis-discharge, #komorbid-discharge, #komplikasi-discharge"
      )
      .forEach(el => {
        const details = el.closest("details");
        if (details) details.setAttribute("open", "true");
      });

    // ====================== SIMPAN KE STATE ======================
    const state = Alpine.$data(document.getElementById("claimRoot"));
    if (!state.simulasi.daily) state.simulasi.daily = {};
    state.simulasi.daily.global = {
      diagnosis: daily.filter(r => r.category === "diagnosis"),
      komorbid: daily.filter(r => r.category === "komorbid"),
      komplikasi: daily.filter(r => r.category === "komplikasi")
    };

    // 🧩 sinkron ke root supaya ikut dibaca backend & simulasi
    const s = Alpine.$data(document.getElementById("claimRoot"));
    if (s) {
      if (!s.simulasi.daily) s.simulasi.daily = {};
      s.simulasi.daily.global = state.simulasi.daily.global;

      // 🩹 jangan replace keseluruhan state daily
      if (!s.simulasi["daily-global"]) s.simulasi["daily-global"] = {};
      ["diagnosis","komorbid","komplikasi"].forEach(tp=>{
        s.simulasi["daily-global"][tp] = daily.filter(r=>r.category===tp);
      });

      // sinkron ringan: isi daily.days terakhir
      if (Array.isArray(s.simulasi.daily?.days) && s.simulasi.daily.days.length>0) {
        const lastIdx = s.simulasi.daily.days.length-1;
        const lastDay = s.simulasi.daily.days[lastIdx];
        ["diagnosis","komorbid","komplikasi"].forEach(tp=>{
          if (!Array.isArray(lastDay[tp])) lastDay[tp]=[];
          const aiOnly = daily.filter(r=>r.category===tp).map(r=>({...r,isManual:false}));
          // jangan hapus manual
          const manuals = (lastDay[tp]||[]).filter(x=>x.isManual);
          lastDay[tp] = [...aiOnly,...manuals];
        });
        s.simulasi[`daily-${lastIdx}`] = lastDay;
      }
    }
  }

  // ================= Render Mapping Select =================
  function renderMappingSelect(item, tab, type, index = null) {
    // ✅ Cek multi-role: doctor atau multi memiliki akses edit
    const canEdit = hasAnyRole(['doctor', 'multi']) || hasRole('doctor');
    const disabled = canEdit ? '' : 'disabled';
    
    // Debug log
    if (window.DEBUG_ROLES) {
      console.log('[renderMappingSelect]', {
        canEdit,
        userRoles: getUserRoles(),
        item: item.kategori || item.nama_kategori
      });
    }

    // ✅ fallback pakai index kalau item.id tidak ada
    // ✅ Kirim key unik berdasarkan kategori + tab
    const key = encodeURIComponent(`${tab}-${type}-${item.kategori || item.nama_kategori}`);
    return `
      <select onchange="onMappingChange(event, '${tab}', '${type}', '${key}')"
              class="border px-2 py-1 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-200 max-w-[200px] truncate" ${disabled}>
        <option value="" ${!item.mapping ? "selected" : ""}>Pilih</option>
        <option value="Diagnosis Utama" ${item.mapping==="Diagnosis Utama"?"selected":""}>Diagnosis Utama</option>
        <option value="Komorbid" ${item.mapping==="Komorbid"?"selected":""}>Komorbid</option>
        <option value="Komplikasi" ${item.mapping==="Komplikasi"?"selected":""}>Komplikasi</option>
        <option value="None" ${item.mapping==="None"?"selected":""}>None</option>
      </select>
    `;
  }

  // ================= Render Value =================
  function renderValue(val) {
    if (val === undefined || val === null) return `<span class="block w-full text-center text-gray-400"></span>`;
    const clean = cleanValue(val);
    if (clean && String(clean).trim()) {
      return `<span class="block w-full truncate overflow-hidden">${clean}</span>`;
    }
    return `<span class="block w-full text-center text-gray-400"></span>`;
  }

  // ================= Render Tabel =================
  function renderTable(targetId, items, type, tab, dayId = null, skipManualRow = false) {
    if (tab === "daily") tab = "daily-global";
    const state = Alpine.$data(document.getElementById("claimRoot"));
    
    console.groupCollapsed("🧩 renderTable DEBUG");
    console.log("targetId:", targetId);
    console.log("tab:", tab, "type:", type);
    console.log("state.simulasi[tab][type] sebelum render:", state.simulasi?.[tab]?.[type]);
    console.groupEnd();

    if (!state.simulasi[tab]) state.simulasi[tab] = { diagnosis: [], komorbid: [], komplikasi: [] };

    // Filter AI vs Manual
    const oldItems = state.simulasi[tab][type] || [];
    const oldAiItems = oldItems.filter(it => !it.isManual);
    const manualItems = oldItems.filter(it => it.isManual);

    const newAiItems = (items || []).filter(it => !it.isManual);
    const aiItems = newAiItems.length > 0 ? newAiItems : oldAiItems;

    if (aiItems.length === 0 && type === "tindakan") {
      const tbody = document.getElementById(targetId);
      if (tbody) {
        tbody.innerHTML = `
          <tr>
            <td colspan="3" class="text-center italic text-gray-500 py-2">
              Menunggu hasil AI...
            </td>
          </tr>`;
      }
      return;
    }

    let merged;
    if (type === "tindakan") {
      merged = aiItems.filter(it => it.procedure_text && it.procedure_text !== "-");
    } else {
      merged = [...aiItems, ...manualItems];
    }

    // ✅ Dedup fix - buat ID unik untuk manual & biarkan tampil
    const seen = new Set();
    merged = merged.filter(it => {
      let key =
        `${it.id || it._index || (it.isManual ? 'manual-' + (it.kategori || it.nama_kategori) : '')}` +
        `-${(it.nama_kategori || it.kategori || "").trim()}` +
        `-${it.icd10_code || it.icd9_code || ""}` +
        `-${it.tindakan || it.procedure_text || ""}` +
        `-${it.child ? "child" : "parent"}`;

      // kalau manual tanpa id → selalu dianggap unik
      if (it.isManual) key += `-${Math.random()}`;

      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    // Store parent items and flatten children into the main array for mapping
    const flatItems = [...merged];

    // ✅ gabungkan AI & Manual dua arah TANPA redeclare variabel
    if (!state.simulasi[tab]) state.simulasi[tab] = {};
    const existing = Array.isArray(state.simulasi[tab][type]) ? state.simulasi[tab][type] : [];

    const keepManuals = existing.filter(it => it.isManual);
    const newAIs = flatItems.filter(it => !it.isManual);

    // merge: manual disimpan, AI terbaru ditambahkan
    const mergedItems = [...keepManuals, ...newAIs];

    // 🧩 Simpan hasil merge AI + manual (jangan sentuh grouped di sini)
    if (tab !== "daily-global") {
      state.simulasi[tab][type] = JSON.parse(JSON.stringify(mergedItems));
    } else {
      const existingManuals = state.simulasi["daily-global"][type] || [];
      const mergedFinal = [
        ...mergedItems,
        ...existingManuals.filter(
          m => !mergedItems.some(ai => ai.kategori === m.kategori)
        ),
      ];
      state.simulasi["daily-global"][type] = JSON.parse(JSON.stringify(mergedFinal));
    }

    // 🩹 UNIVERSAL PATCH – simpan children ke state.simulasi terpisah (aman semua tab)
    if (Array.isArray(state.simulasi[tab]?.[type])) {
      const parents = state.simulasi[tab][type].filter(p => Array.isArray(p.children) && p.children.length > 0);
      const allChildren = parents.flatMap(p =>
        p.children.map(ch => ({
          ...ch,
          parentRef: p.id || p.kategori,
          isChildClone: true
        }))
      );
    }

    // 🔍 log tambahan
    console.groupCollapsed("🧩 renderTable MERGE DEBUG");
    console.log("tab:", tab, "type:", type);
    console.log("manuals:", keepManuals);
    console.log("aiItems(new):", newAIs);
    console.groupEnd();

    let target = document.getElementById(targetId);
    if (!target && targetId.includes("daily-global")) {
      const fallbackId = targetId.replace("daily-global", "daily");
      target = document.getElementById(fallbackId);
    }

    if (!target) {
      console.warn("⚠️ renderTable: target element not found for", targetId);
      return;
    }

    target.innerHTML = "";
    console.log("🧾 Rendering into target:", targetId, "data:", state.simulasi[tab][type]);

    // 🧩 Group parent/child for rendering - rebuild hierarchy (fix manual)
    let grouped = [];
    let parentMap = {};
    let lastParentKey = null;

    const allItems = state.simulasi?.[tab]?.[type] || merged;

    [...allItems].forEach(it => {
      const name = (it.nama_kategori || it.kategori || "").trim();
      if (!name) return;
      const itemType = it.type || type || "diagnosis";

      // ✅ kalau manual tanpa anak → langsung jadi baris sendiri
      if (it.isManual && !it.children && !it.child) {
        grouped.push({
          ...it,
          kategori: name,
          nama_kategori: name,
          children: []
        });
        return;
      }

      // 🔥 Core_engine format: parent sudah punya children
      if (it.children && Array.isArray(it.children)) {
        const parentWithChildren = {
          ...it,
          kategori: name,
          nama_kategori: name,
          children: it.children.map((child, idx) => ({
            ...child,
            kategori: child.nama_kategori || child.kategori || "-",
            nama_kategori: child.nama_kategori || child.kategori || "-",
            klinis: child.klinis || "-",
            icd10_code: child.icd10_code || child.icd || "-",
            procedure_text: child.tindakan || child.procedure_text || "-",
            score: child.score || child.confidence || "-",
            id: child.id || `${it.id || "parent"}-child-${idx}`
          }))
        };
        grouped.push(parentWithChildren);
        return;
      }

      // 🔥 Development branch format: child flag
      if (it.child === true && lastParentKey && parentMap[lastParentKey]) {
        const childWithId = {
          ...it,
          kategori: `${name} ${String.fromCharCode(
            97 + parentMap[lastParentKey].children.length
          )}`,
          nama_kategori: name,
          id:
            it.id ||
            `${parentMap[lastParentKey].id}-child-${parentMap[lastParentKey].children.length}`
        };
        parentMap[lastParentKey].children.push(childWithId);
        return;
      }

      // default parent (AI biasa)
      const parentKey = `${itemType}:${name}`;
      parentMap[parentKey] = {
        ...it,
        kategori: name,
        nama_kategori: name,
        children: []
      };
      grouped.push(parentMap[parentKey]);
      lastParentKey = parentKey;
    });

    // 🩹 Simpan hasil grouped (parent + children) ke simulasi
    if (Array.isArray(grouped) && grouped.length > 0) {
      state.simulasi[tab][type] = JSON.parse(JSON.stringify(grouped));
    }

    // 🩹 tambahan khusus daily-global agar children ikut tersimpan di simulasi
    if (tab === "daily-global") {
      const parents = grouped.filter(p => Array.isArray(p.children) && p.children.length > 0);
      const allChildren = parents.flatMap(p =>
        p.children.map(ch => ({
          ...ch,
          parentRef: p.id || p.kategori,
          isChildClone: true
        }))
      );

      state.simulasi["daily-global"][type] = [
        ...(state.simulasi["daily-global"][type] || []),
        ...allChildren.filter(
          c => !state.simulasi["daily-global"][type].some(e => e.nama_kategori === c.nama_kategori)
        )
      ];
    }

    // Header (sekali per table)
    const table = target.closest("table");
    if (table && !table.querySelector("thead")) {
      const thead = document.createElement("thead");
      thead.className = "bg-gray-100 dark:bg-gray-800";
      
      // ✅ Cek apakah user memiliki akses mapping (doctor atau multi-role)
      const showMapping = hasAnyRole(['doctor', 'multi']) || hasRole('doctor');
      
      thead.innerHTML = `
        <tr>
          <th class="border px-3 py-2 w-[20%]">Kategori</th>
          <th class="border px-3 py-2 w-[25%]">Klinis</th>
          <th class="border px-3 py-2 w-[10%]">ICD</th>
          <th class="border px-3 py-2 w-[25%]">Tindakan</th>
          <th class="border px-3 py-2 w-[10%]">Score</th>
          ${showMapping ? `<th class="border px-3 py-2 w-[10%]">Mapping</th>` : ``}
        </tr>`;
      table.insertBefore(thead, table.firstChild);
    }

    // Clean up data
    grouped = grouped.map(it => {
      for (const key of ["kategori", "nama_kategori", "klinis", "icd10_code", "icd9_code", "tindakan", "procedure_text", "score"]) {
        if (it[key] === undefined || it[key] === null || it[key] === "-") it[key] = "";
      }
      if (Array.isArray(it.children)) {
        it.children = it.children.map(ch => {
          for (const key of ["kategori", "nama_kategori", "klinis", "icd10_code", "icd9_code", "tindakan", "procedure_text", "score"]) {
            if (ch[key] === undefined || ch[key] === null || ch[key] === "-") ch[key] = "";
          }
          return ch;
        });
      }
      return it;
    });

    // Render rows
    grouped.forEach((parent, idx) => {
      const counter = 1 + (parent.children ? parent.children.length : 0);
      const tbody = document.createElement("tbody");
      tbody.setAttribute("x-data", "{ open:true }");

      const tindakanText = parent.tindakan || parent.procedure_text;
      const klinisText = parent.klinis;
      const icdText = parent.icd10_code || parent.icd9_code;
      const titleTindakan = tindakanText;
      const titleICD = icdText;
      const titleKlinis = klinisText;

      // ✅ Cek apakah user memiliki akses mapping
      const showMapping = hasAnyRole(['doctor', 'multi']) || hasRole('doctor');

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
            <td class="col-klinis border px-3 py-2 w-[25%]" title="${titleKlinis}">
              <span class="block w-full truncate">${renderValue(klinisText)}</span>
            </td>
            <td class="col-icd border px-3 py-2 w-[10%] text-center" title="${titleICD}">
              <span class="block w-full truncate">${renderValue(icdText)}</span>
            </td>
            <td class="col-tindakan border px-3 py-2 w-[25%]" title="${titleTindakan}">
              <span class="block w-full truncate">${renderValue(tindakanText)}</span>
            </td>
            <td class="border px-3 py-2 w-[10%] text-center">
              <span class="block w-full truncate">${renderValue(parent.score)}</span>
            </td>
            ${showMapping ? `<td class="border px-3 py-2 text-center">${renderMappingSelect(parent, tab, type, idx)}</td>` : ``}
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
            ${hasRole('doctor') ? `<td class="border px-3 py-2 text-center">${renderMappingSelect(child, tab, type, `${idx}-child-${cIdx}`)}</td>` : ``}
          </tr>
        `);
      });

      target.appendChild(tbody);
      Alpine.initTree(tbody);
    });

    // util: normalisasi & buat key unik
    const makeKey = (it = {}) => {
      const norm = v => (v || "").toString().trim().toLowerCase();
      const name = norm(it.nama_kategori || it.kategori || it.name);
      const icd  = norm(it.icd10_code || it.icd9_code);
      return `${name}|${icd}`;
    };

    // ========== Counter badge per-section ==========
    const counterId = dayId ? `count-${type}-${dayId}` : `count-${type}-${tab}`;
    const countEl = document.getElementById(counterId);
    if (countEl) {
      const seen = new Set();
      let total = 0;
      grouped.forEach(p => {
        if (!p.isChildClone && !p.hidden) {
          const k = makeKey(p);
          if (k && !seen.has(k)) { seen.add(k); total += 1; }
        }
        (p.children || []).forEach(ch => {
          if (!ch.isChildClone && !ch.hidden) {
            const k = makeKey(ch);
            if (k && !seen.has(k)) { seen.add(k); total += 1; }
          }
        });
      });
      countEl.textContent = total;
    }

    // Total harian (diagnosis+komorbid+komplikasi)
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

    // ========== Counter utama (badge biru header tab) ==========
    let mainCounter = document.querySelector(`#count-${type}-${tab}`);
    if (!mainCounter && tab === "daily-global") {
      mainCounter = document.querySelector(`#count-${type}-daily`);
    }
    if (mainCounter) {
      const arr = Array.isArray(state.simulasi?.[tab]?.[type]) ? state.simulasi[tab][type] : [];
      const seen = new Set();
      let total = 0;
      arr.forEach(p => {
        if (!p.isChildClone && !p.hidden) {
          const k = makeKey(p);
          if (k && !seen.has(k)) { seen.add(k); total += 1; }
        }
        (p.children || []).forEach(ch => {
          if (!ch.isChildClone && !ch.hidden) {
            const k = makeKey(ch);
            if (k && !seen.has(k)) { seen.add(k); total += 1; }
          }
        });
      });
      mainCounter.textContent = total;
    }

    // === Manual input row untuk doctor ===
    if (!skipManualRow && hasAnyRole(['doctor', 'coder'])) {
      if (
        tab === "admission" ||
        tab === "discharge" ||
        tab === "daily" ||
        tab === "daily-global" ||
        String(tab).startsWith("daily-")
      ) {
        const manualTbody = document.createElement("tbody");
        const tabPath = String(tab).startsWith("daily-")
          ? `manualInput.daily[\`${tab}\`].${type}`
          : `manualInput.${tab}.${type}`;
        const manualRowId = `manual-${tab}-${type}-${Date.now()}`;

        manualTbody.insertAdjacentHTML(
          "beforeend",
          `
          <tr id="${manualRowId}" class="manual-row bg-gray-50 dark:bg-gray-800">
            <td class="border px-3 py-2 whitespace-nowrap relative overflow-visible max-w-[180px]">
              <div x-data="diagnosisAutocomplete('${tab}', '${tabPath}', '${type}')" class="relative">
                <input type="text"
                      x-model="query"
                      @input.debounce.300ms="search"
                      @keydown.enter.prevent="results.length ? select(results[0]) : addManualIfNotFound()"
                      placeholder="Cari penyakit..."
                      class="w-full px-2 py-1 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600">
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
        `
        );

        target.appendChild(manualTbody);
        Alpine.initTree(manualTbody);
      }
    }

    // === Sinkron render list tindakan manual di modal ===
    if (type === "diagnosis" && typeof window.renderManualTindakanList === "function") {
      setTimeout(() => window.renderManualTindakanList(tab), 0);
    }
  }

  // =============== Export Functions ===============
  window.hasRole = hasRole;
  window.hasAnyRole = hasAnyRole;
  window.hasAllRoles = hasAllRoles;
  window.getUserRoles = getUserRoles;
  window.diagnosisAutocomplete = diagnosisAutocomplete;
  window.renderAI = renderAI;
  window.renderTable = renderTable;
  window.addManualIfNotFound = addManualIfNotFound;

  // Optional: Enable debug mode
  if (typeof window.DEBUG_ROLES === 'undefined') {
    window.DEBUG_ROLES = false;
  }

  // Log initialization
  console.log("✅ claim.render.js loaded - Multi-role support enabled");
  console.log("📋 Available functions:", {
    hasRole: "Check single role",
    hasAnyRole: "Check multiple roles (OR)",
    hasAllRoles: "Check multiple roles (AND)",
    getUserRoles: "Get all user roles",
    renderAI: "Render AI recommendations",
    renderTable: "Render diagnosis/procedure tables"
  });
})();