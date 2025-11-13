// ============================================================
// claim.modals.manual.js (Lossless Refactor - final fixed version)
// ============================================================
// Menangani autocomplete tindakan & input manual dengan konfirmasi.
// Struktur & gaya mengikuti claim.modals.core.js
// ============================================================

export function showConfirmModal(title, message) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className =
      "fixed inset-0 bg-black/40 backdrop-blur-sm z-[9998] flex items-center justify-center";

    const modal = document.createElement("div");
    modal.className =
      "bg-white dark:bg-slate-800 text-gray-900 dark:text-white p-6 rounded-lg shadow-lg max-w-sm w-full text-center animate-fade-in-up";
    modal.innerHTML = `
      <h2 class="text-lg font-bold mb-3 text-gray-800 dark:text-gray-100">${title}</h2>
      <p class="text-gray-700 dark:text-gray-200 mb-6">${message}</p>
      <div class="flex justify-center gap-4">
        <button id="confirmYes"
          class="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">Tambahkan</button>
        <button id="confirmNo"
          class="px-4 py-2 rounded bg-gray-300 dark:bg-gray-600 text-gray-800 dark:text-gray-100 hover:bg-gray-400 dark:hover:bg-gray-500">Batal</button>
      </div>
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    function cleanup(result) {
      overlay.remove();
      resolve(result);
    }

    modal.querySelector("#confirmYes").addEventListener("click", () => cleanup(true));
    modal.querySelector("#confirmNo").addEventListener("click", () => cleanup(false));
    overlay.addEventListener("keydown", (e) => e.key === "Escape" && cleanup(false));
  });
}

export function tindakanAutocomplete() {
  return {
    query: "",
    results: [],
    async search() {
      if (!this.query) {
        this.results = [];
        return;
      }
      try {
        if (window.searchTindakan) {
          const res = await window.searchTindakan(this.query);
          this.results = res.data || [];
        } else {
          console.warn("searchTindakan() tidak tersedia");
          this.results = [];
        }
      } catch (err) {
        console.error("Error searching tindakan:", err);
        this.results = [];
      }
    },
    async select(item) {
      this.query = item.procedure_text;
      this.results = [];
      if (window.addManualTindakanFromAutocomplete) {
        await window.addManualTindakanFromAutocomplete(
          window.claimState?.tab || "admission",
          item
        );
      }
    },
  };
}

function isTindakanFound(ctx, text) {
  return (ctx.results || []).some(
    (t) =>
      t.procedure_text?.toLowerCase() === text.toLowerCase() ||
      t.nama?.toLowerCase() === text.toLowerCase()
  );
}

export async function addManualTindakanIfNotFound() {
  try {
    const root = document.querySelector('[x-data*="AIClaim.tindakanAutocomplete()"]');
    const ctx = root ? Alpine.$data(root) : null;
    if (!ctx) {
      console.warn("⚠️ Alpine context tidak ditemukan untuk tindakanAutocomplete()");
      return;
    }

    const text = ctx.query?.trim?.();
    if (!text) return;

    const found = isTindakanFound(ctx, text);
    if (!found) {
      const confirmAdd = await showConfirmModal(
        "Tindakan tidak ditemukan",
        `Tindakan "${text}" tidak ditemukan di database.<br>Tambahkan sebagai input manual baru?`
      );
      if (!confirmAdd) return;

      if (typeof addManualTindakanFromAutocomplete === "function") {
        await addManualTindakanFromAutocomplete(
          window.claimState?.tab || "admission",
          { procedure_text: text, isManual: true }
        );
      }

      ctx.query = "";
      ctx.results = [];
    }
  } catch (err) {
    console.error("❌ Gagal addManualTindakanIfNotFound:", err);
  }
}

// ============================================================
// 👉 Export fungsi untuk Node / bundler, atau pasang ke window namespace
// ============================================================
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    showConfirmModal,
    tindakanAutocomplete,
    addManualTindakanIfNotFound,
  };
} else if (typeof window !== "undefined") {
  const ns = (window.AIClaim = window.AIClaim || {});
  ns.showConfirmModal = showConfirmModal;
  ns.tindakanAutocomplete = tindakanAutocomplete;
  ns.addManualTindakanIfNotFound = addManualTindakanIfNotFound;
}

// ============================================================
// ✨ Inject animasi fade-in-up biar konsisten antar modal
// ============================================================
if (typeof document !== "undefined") {
  const style = document.createElement("style");
  style.innerHTML = `
  @keyframes fade-in-up {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .animate-fade-in-up {
    animation: fade-in-up 0.25s ease-out;
  }`;
  document.head.appendChild(style);
}
