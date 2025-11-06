// ============================================================
// 🧩 AI-Claim Modal Entry Point (Universal Loader - Safe Version)
// ============================================================
// Aman di semua environment (ESM, browser biasa, Docker, dll)
// ============================================================

(function () {
  const MODULE_LIST = [
    "claim.modals.core.js",
    "claim.modals.diagnosis.js",
    "claim.modals.procedure.js",
    "claim.modals.idrg.js",
    "claim.modals.manual.js",
    "claim.modals.notes.js",
    "claim.modals.regulation.js",
    "claim.modals.verifikator.js"
  ];

  (async () => {
    for (const file of MODULE_LIST) {
      try {
        await import(`/static/js/claim/${file}?v=${Date.now()}`);
        console.log(`✅ [AI-Claim] Loaded ${file}`);
      } catch (err) {
        console.error(`❌ [AI-Claim] Gagal load ${file}`, err);
      }
    }
    console.log("✅ Semua modul modal dimuat (ESM).");
  })();

  // ============================================================
  // 🪟 WINDOW SHIM UNTUK DEBUG
  // ============================================================
  if (typeof window !== "undefined") {
    window.AIClaim = window.AIClaim || {};
    window.AIClaim.loadedModals = MODULE_LIST;
    console.log("🧩 [AI-Claim] Window shim aktif:", MODULE_LIST);
  }
})();
