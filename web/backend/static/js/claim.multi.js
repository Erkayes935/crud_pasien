// claim.multi.js
// Final combined multi-role helpers & compatibility layer
// - Ensure generateAI / generateSummary rendering matches doctor renderer
// - Persist mapping dropdowns across re-renders
// - Autosave before finalize using FormData
// - Provide safe fallbacks for openRulesModal / openNoteModal

(function () {
  if (window.__CLAIM_MULTI_INSTALLED) return;
  window.__CLAIM_MULTI_INSTALLED = true;

  // --------------------------
  // Mapping cache helpers
  // --------------------------
  window.claimState = window.claimState || {};
  window.claimState.mappingCache = window.claimState.mappingCache || {}; // { tableId: {rowIndex: value, ...}, ... }

  window.claimState = window.claimState || {};
    if (!window.claimState.roles) {
    // fallback: multi-role user, misal punya semua role
    window.claimState.roles = ['doctor', 'coder', 'verifikator'];
    }
  function saveAllMappings() {
    const cache = {};
    document.querySelectorAll("table.diagnosis-table, table.komorbid-table, table.komplikasi-table").forEach((table) => {
      const tid = table.id || `table-${Math.random().toString(36).slice(2,8)}`;
      const rows = table.querySelectorAll("tbody tr");
      if (!rows || rows.length === 0) return;
      cache[tid] = {};
      rows.forEach((row, idx) => {
        const sel = row.querySelector("select");
        if (sel) cache[tid][idx] = sel.value;
      });
    });
    window.claimState.mappingCache = cache;
    // Persist short-term (per session) so page reload doesn't persist; comment out if undesired:
    try { sessionStorage.setItem(`claim_mapping_${getClaimId()}`, JSON.stringify(cache)); } catch(e) {}
  }

  function restoreAllMappings() {
    // Try read from sessionStorage first if cache empty
    try {
      const st = sessionStorage.getItem(`claim_mapping_${getClaimId()}`);
      if ((!window.claimState.mappingCache || Object.keys(window.claimState.mappingCache).length === 0) && st) {
        window.claimState.mappingCache = JSON.parse(st);
      }
    } catch (e) {}
    const cache = window.claimState.mappingCache || {};
    Object.keys(cache).forEach((tableId) => {
      const map = cache[tableId] || {};
      const table = document.getElementById(tableId);
      if (!table) return;
      const rows = table.querySelectorAll("tbody tr");
      rows.forEach((row, idx) => {
        const sel = row.querySelector("select");
        if (sel && (map[idx] !== undefined)) {
          try { sel.value = map[idx]; } catch (e) {}
          // optionally dispatch change so Alpine/other listeners update
          sel.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });
    });
  }

  // For compatibility: if render replaces tbody id or uses different ids, copy mapping by position
  function restoreMappingsBestEffort() {
    try {
      const cache = window.claimState.mappingCache || {};
      if (!Object.keys(cache).length) return;
      // iterate current tables and try to apply mapping by index if table ids differ
      document.querySelectorAll("table.diagnosis-table, table.komorbid-table, table.komplikasi-table").forEach((table) => {
        const rows = table.querySelectorAll("tbody tr");
        rows.forEach((row, idx) => {
          const sel = row.querySelector("select");
          if (!sel) return;
          // find any cache entry that has idx
          for (const tid of Object.keys(cache)) {
            if (cache[tid] && cache[tid][idx] !== undefined) {
              try { sel.value = cache[tid][idx]; } catch (e) {}
              sel.dispatchEvent(new Event('change', { bubbles: true }));
              break;
            }
          }
        });
      });
    } catch (e) {
      console.error("[claim.multi] restoreMappingsBestEffort failed:", e);
    }
  }

  // --------------------------
  // Utility helpers
  // --------------------------
  function getClaimId() {
    try {
      const el = document.querySelector('[data-claim-id]') || document.getElementById('claimForm');
      if (!el) return null;
      return el.getAttribute('data-claim-id') || el.dataset.claimId;
    } catch (e) { return null; }
  }

  function dispatchRenderComplete() {
    document.dispatchEvent(new CustomEvent('renderComplete'));
  }

  // --------------------------
  // Wrap generateAI & generateSummary to ensure consistent rendering
  // --------------------------
  const originalGenerateAI = window.generateAI;
  const originalGenerateSummary = window.generateSummary;

  async function invokeAndRenderDoctorRenderer(originalFn, label) {
    try {
      // Save mapping before heavy operations
      saveAllMappings();
      if (typeof originalFn === 'function') {
        await originalFn();
      } else {
        console.warn(`[claim.multi] ${label} original function not found; continuing.`);
      }

      // If doctor's renderer is exposed, call it to rebuild tables consistently
      if (typeof window.renderClaimTabs === 'function') {
        try {
          // renderClaimTabs may accept simulasi data; if not, call without args
          const simulasiData = window.claimState && window.claimState.simulasi ? window.claimState.simulasi : undefined;
          if (simulasiData !== undefined) {
            window.renderClaimTabs(simulasiData);
          } else {
            window.renderClaimTabs();
          }
        } catch (e) {
          // fallback: attempt calling global render functions if available
          console.debug('[claim.multi] renderClaimTabs threw, attempting fallback render functions', e);
          if (typeof window.renderAllTables === 'function') window.renderAllTables();
        }
      } else {
        // If not available, try more generic fallback: trigger an event so claim.render.js can listen
        document.dispatchEvent(new CustomEvent('requestDoctorRender'));
      }

      // After render, restore mappings
      // Use best effort: exact id restore + fallback by index
      restoreAllMappings();
      restoreMappingsBestEffort();

      // notify listeners
      dispatchRenderComplete();
      console.log(`[claim.multi] ${label} completed and doctor renderer invoked.`);
    } catch (err) {
      console.error(`[claim.multi] Error while wrapping ${label}:`, err);
    }
  }

  // Install wrappers
  window.generateAI = async function(...args) {
    return invokeAndRenderDoctorRenderer(originalGenerateAI, 'generateAI');
  };

  window.generateSummary = async function(...args) {
    return invokeAndRenderDoctorRenderer(originalGenerateSummary, 'generateSummary');
  };

  // If other parts of code call generateSummary via different names, ensure compatibility
  if (!window.generate_summary && window.generateSummary) window.generate_summary = window.generateSummary;

  // --------------------------
  // Autosave before finalize (using FormData)
  // --------------------------
  async function autosaveBeforeFinalize() {
    try {
      const claimId = getClaimId();
      if (!claimId) return;

      // Try to gather payload data from Alpine or DOM fields
      let payload = {};
      // If alpine state exists, prefer it
      const root = document.getElementById('claimRoot');
      if (root && root._x_dataStack && root._x_dataStack[0]) {
        const alpine = root._x_dataStack[0];
        // try to shallow-copy relevant fields
        payload = {
          simulasi: alpine.simulasi || alpine.simulation || null,
          summary: alpine.summary || null,
          notes: alpine.notes || alpine.notes || null,
          tab: alpine.tab || null,
          role: alpine.role || 'multi',
        };
      } else {
        // fallback: read hidden fields if available
        const simulasiField = document.getElementById('simulasiField');
        const summaryField = document.getElementById('summaryField');
        payload.simulasi = simulasiField ? simulasiField.value : null;
        payload.summary = summaryField ? summaryField.value : null;
      }

      // Build FormData
      const formData = new FormData();
      formData.append('payload', JSON.stringify(payload));
      // append CSRF if present
      const csrfInput = document.querySelector('input[name="csrf_token"], input[name="csrf"]');
      if (csrfInput) formData.append('csrf_token', csrfInput.value);

      const resp = await fetch(`/claims/${claimId}/update-draft`, {
        method: 'POST',
        credentials: 'include',
        body: formData
      });

      if (!resp.ok) {
        // not fatal; just log
        console.warn('[claim.multi] autosaveBeforeFinalize response not OK:', resp.status, resp.statusText);
      } else {
        console.log('[claim.multi] autosaveBeforeFinalize saved draft.');
      }
    } catch (e) {
      console.error('[claim.multi] autosaveBeforeFinalize failed:', e);
    }
  }

  // Hook into form submit to run autosave then allow submit
  (function attachFormSubmitHook() {
    const form = document.getElementById('claimForm');
    if (!form) return;
    // If already wrapped, skip
    if (form.__CLAIM_MULTI_SUBMIT_WRAPPED) return;
    form.__CLAIM_MULTI_SUBMIT_WRAPPED = true;

    form.addEventListener('submit', function (ev) {
      // We'll perform autosave asynchronously but do not block submit (server will handle finalize).
      // However to be safe, we can wait a short moment to allow autosave to start.
      try {
        autosaveBeforeFinalize(); // fire-and-forget
      } catch (err) {
        console.error('[claim.multi] autosave trigger failed', err);
      }
      // allow the normal submit to proceed
    }, { capture: true });
  })();

  // --------------------------
  // Fallback helpers: openRulesModal / openNoteModal
  // --------------------------
  window.openRulesModal = window.openRulesModal || window.showRulesModal || async function(diagnosis) {
    if (!diagnosis) return alert('⚠️ Diagnosis tidak valid');
    const root = document.getElementById('claimRoot');
    if (!root || !root._x_dataStack) return alert('Alpine not ready');
    const alpine = root._x_dataStack[0];
    alpine.rulesModalOpen = true;
    alpine.selectedDiagnosis = diagnosis;
    alpine.loading = true;
    try {
      const resp = await fetch(`/claims/rules/load?diagnosis=${encodeURIComponent(diagnosis)}`, { credentials: 'include' });
      const data = await resp.json();
      alpine.rulesData = data;
      // build rulesByLayer for template convenience
      alpine.rulesByLayer = (function(rulesData){
        const map = {};
        if(!rulesData || !rulesData.rules) return map;
        Object.values(rulesData.rules).flat().forEach(r=>{
          map[r.layer] = map[r.layer]||[];
          map[r.layer].push(r);
        });
        return map;
      })(data);
      const layers = Object.keys(alpine.rulesByLayer).sort((a,b)=>{
        const pr = {'permenkes':1,'nasional':2,'ppk':3,'regional':4,'rs':5,'bridging':6,'fraud':7,'temporary':8};
        return (pr[a]||99)-(pr[b]||99);
      });
      alpine.activeTab = layers[0]||'';
      alpine.loading = false;
    } catch(e) {
      alpine.loading = false;
      alpine.rulesData = null;
      console.error('[claim.multi] openRulesModal failed:', e);
      alert('Gagal memuat aturan: ' + (e.message || e));
    }
  };

  window.openNoteModal = window.openNoteModal || function(title, key, context) {
    const root = document.getElementById('claimRoot');
    if (!root || !root._x_dataStack) return;
    const alpine = root._x_dataStack[0];
    alpine.modalTitle = title || 'Catatan';
    // Basic formatted JSON preview if context provided
    alpine.modalContent = context ? `<pre class="whitespace-pre-wrap text-sm">${JSON.stringify(context, null, 2)}</pre>` : '<p>Tidak ada konten</p>';
    alpine.modalOpen = true;
    alpine.hideDefaultClose = false;
  };

  // --------------------------
  // onComboSelect helper (used by combined template)
  // --------------------------
  window.onComboSelect = window.onComboSelect || function(e) {
    const idx = e.target.value;
    if (!idx && idx !== 0) return;
    const root = document.getElementById('claimRoot');
    if (!root || !root._x_dataStack) return;
    const alpine = root._x_dataStack[0];
    const alt = (alpine.alternatif && alpine.alternatif[idx]) ? alpine.alternatif[idx] : null;
    if (!alt) return;
    // Map chosen alternative to simulasi primary fields (best effort)
    try {
      if (!alpine.simulasi) alpine.simulasi = alpine.simulasi || {};
      const tab = alpine.tab || 'admission';
      alpine.simulasi[tab] = alpine.simulasi[tab] || {};
      if (alt.utama) alpine.simulasi[tab].utama = alt.utama;
      if (alt.tindakanUtama) alpine.simulasi[tab].tindakanUtama = alt.tindakanUtama;
      // allow downstream observers to react
      if (typeof alpine.onAlternativeApplied === 'function') alpine.onAlternativeApplied(alt, tab);
    } catch (e) {
      console.error('[claim.multi] onComboSelect apply failed', e);
    }
  };

  // --------------------------
  // Init: try restore mapping cache from session & wire renderComplete -> restore
  // --------------------------
  (function initRestoreHooks() {
    try {
      const claimId = getClaimId();
      if (!claimId) return;
      const st = sessionStorage.getItem(`claim_mapping_${claimId}`);
      if (st) {
        window.claimState.mappingCache = JSON.parse(st);
      }
    } catch (e) {}
    // When other scripts finish render, they dispatch 'renderComplete' -> restore mappings
    document.addEventListener('renderComplete', () => {
      restoreAllMappings();
      restoreMappingsBestEffort();
    });
    // Also attempt a restore after a small delay on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', function() {
      setTimeout(()=> { restoreAllMappings(); restoreMappingsBestEffort(); }, 200);
    });
  })();

  // --------------------------
  // Optional: expose helpers for debugging
  // --------------------------
  window.__claim_multi_debug = {
    saveAllMappings,
    restoreAllMappings,
    restoreMappingsBestEffort,
    getMappingCache: () => window.claimState.mappingCache || {},
    clearMappingCache: () => { window.claimState.mappingCache = {}; sessionStorage.removeItem(`claim_mapping_${getClaimId()}`); }
  };

  console.log('[claim.multi] installed: multi-role compatibility & mapping persistence active.');
})();
