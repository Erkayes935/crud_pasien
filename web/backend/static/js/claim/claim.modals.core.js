// ============================================================
// claim.modals.core.js (Lossless Refactor)
// ============================================================
// Refactor penuh dari bagian core modal di claim.modals.js
// Semua logika dipertahankan 100%, hanya gaya & struktur yang diperbaiki.
// ============================================================

export let modalClosing = false;
export let modalStack = [];
export let claimState = (window.claimState = window.claimState || {});

// ======================================================
// 🪟 OPEN MODAL
// ======================================================
export function openModal(title, content, options = {}) {
  // pastikan claimState tersedia
  window.claimState = window.claimState || {};
  const state = window.claimState;

  // 🧹 Prevent modal duplication (gepeng / dua tampilan)
  const existingContents = document.querySelectorAll("#modalContainer .modal-content");
  if (existingContents.length > 0) {
    existingContents.forEach((el) => el.remove());
    console.log("♻️ [CLEANUP] Old modal-content removed before opening new one");
  }

  state.modalStack = state.modalStack || [];

  // pastikan elemen dasar modal tersedia
  let modalContainer = document.getElementById("modalContainer");
  let modalContent = document.querySelector(".modal-content");
  let modalTitle = document.querySelector(".modal-title");

  if (!modalContainer) {
    modalContainer = document.createElement("div");
    modalContainer.id = "modalContainer";
    modalContainer.className =
      "fixed inset-0 bg-black/40 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 hidden";
    document.body.appendChild(modalContainer);
  }

  if (!modalContent) {
    modalContent = document.createElement("div");
    modalContent.className =
      "modal-content relative bg-gray-50 dark:bg-slate-800 text-slate-900 dark:text-white p-6 rounded-2xl max-h-[90vh] overflow-y-auto shadow-2xl w-[90%] max-w-4xl border border-slate-200 dark:border-slate-700";
    modalContainer.appendChild(modalContent);
  }

  if (!modalTitle) {
    modalTitle = document.createElement("div");
    modalTitle.className =
      "modal-title mb-4 text-center text-xl font-bold text-slate-800 dark:text-white";
    modalContent.prepend(modalTitle);
  }

  // simpan modal lama ke stack (restore system)
  if (!window.__suppressModalStack) {
    const oldTitle = modalTitle.innerHTML?.trim();
    const oldHTML = modalContent.innerHTML?.trim();
    if (oldHTML && oldTitle) {
      state.modalStack.push({ title: oldTitle, content: oldHTML });
      if (state.modalStack.length > 10) state.modalStack.shift();
    }
  }

  console.log("🔍 Opening modal with title:", title);
  console.log("🔍 Modal content length:", content?.length || 0);

  // Clear existing content
  modalContent.innerHTML = "";

  // tampilkan modal
  modalContainer.classList.remove("hidden");
  modalContainer.classList.add("flex");

  const closeButton = options.hideDefaultClose
    ? ""
    : `<button type="button"
                class="absolute top-3 right-4 text-white bg-red-500 hover:bg-red-600 px-4 py-2 rounded-lg shadow-md hover:shadow-lg transition-all transform hover:-translate-y-0.5"
                onclick="closeNestedModal()">✕</button>`;

  if (!options.disableAutoTitle) {
    modalTitle.innerHTML = `
      <div class="relative w-full bg-blue-600/90 dark:bg-blue-700 text-white rounded-t-xl py-2">
        <h2 class="text-xl font-bold text-center">${title || "(Untitled Modal)"}</h2>
        ${closeButton}
      </div>
    `;
  }

  modalContent.innerHTML = options.disableAutoTitle
    ? content || "<p>Tidak ada konten.</p>"
    : `
      ${modalTitle.outerHTML}
      <div class="modal-body pt-3">${content || "<p>Tidak ada konten.</p>"}</div>
    `;

  // animasi fade-in
  modalContent.classList.add("modal-fade-enter");
  setTimeout(() => {
    modalContent.classList.add("modal-fade-enter-active");
    modalContent.classList.remove("modal-fade-enter");
  }, 10);

  state.modalOpen = true;
  console.log("🔍 Modal container display:", getComputedStyle(modalContainer).display);

  // Alpine init & regulation events
  setTimeout(() => {
    if (window.Alpine) Alpine.initTree(modalContent);

    document.querySelectorAll(".regulation-field").forEach((el) => {
      el.addEventListener("click", function () {
        const field = this.getAttribute("data-field");
        const diagnosisId = this.getAttribute("data-diagnosis-id");
        const procedureId = this.getAttribute("data-procedure-id");
        console.log("🔍 Regulation field clicked:", field, diagnosisId, procedureId);
        if (window.openRegulationDetailModal)
          window.openRegulationDetailModal(field, diagnosisId, procedureId);
      });
    });

    console.log("🔍 Event handlers attached to regulation fields");
  }, 50);

  // reset suppress flag
  if (window.__suppressModalStack) {
    console.log("🔧 Reset suppress flag setelah modal dibuka");
    window.__suppressModalStack = false;
  }
}

// ======================================================
// 🤖 AI Loading Modal
// ======================================================
export function showAiLoadingModal(
  steps = ["Mengambil data...", "Menganalisis hasil...", "Menyiapkan tampilan..."]
) {
  const modal = document.getElementById("aiLoadingModal");
  const container = document.getElementById("aiLoadingMessages");
  if (!modal || !container) return;

  modal.classList.remove("hidden");
  container.innerHTML = "";
  let i = 0;
  (function loop() {
    if (i < steps.length) {
      const p = document.createElement("p");
      p.textContent = steps[i];
      container.appendChild(p);
      i++;
      setTimeout(loop, 900);
    }
  })();
}

export function hideAiLoadingModal() {
  const modal = document.getElementById("aiLoadingModal");
  if (modal) modal.classList.add("hidden");
}

// ======================================================
// 🧩 Overlay Modal (Regulasi / iDRG)
// ======================================================
export function openOverlayModal(title, htmlContent, sourceType = null, sourceId = null) {
  document.body.classList.remove("text-xl", "text-yellow-500", "font-bold");

  window.claimState = window.claimState || {};
  window.claimState.regulationSource = { type: sourceType, id: sourceId };

  let overlay = document.getElementById("overlayRegulasi");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = "overlayRegulasi";
    overlay.className =
      "fixed inset-0 bg-black/40 dark:bg-black/70 flex items-center justify-center z-[9999]";
    document.body.appendChild(overlay);
  }

  overlay.innerHTML = `
    <div class="bg-white dark:bg-slate-800 text-gray-900 dark:text-white 
                p-6 rounded-2xl max-w-4xl w-[90%] shadow-2xl relative 
                animate-fade-in border border-slate-200 dark:border-slate-700 
                max-h-[90vh] overflow-y-auto">
      <button type="button"
              class="absolute top-3 right-4 text-white bg-red-500 hover:bg-red-600 
                    px-4 py-2 rounded-lg shadow-md hover:shadow-lg transition-all 
                    transform hover:-translate-y-0.5"
              onclick="closeOverlayModal()">✕</button>
      <h2 class="text-lg font-semibold mb-4 text-center text-slate-800 dark:text-white">${title}</h2>
      ${htmlContent}
    </div>
  `;

  requestAnimationFrame(() => overlay.classList.add("visible"));
  document.body.classList.add("modal-open");
}

export function closeOverlayModal() {
  const overlay = document.getElementById("overlayRegulasi");
  if (!overlay) return;

  console.log("🧩 [CLOSE OVERLAY] Mulai tutup overlay regulasi…");

  // 🩹 Pastikan flag modalOpen dimatikan lebih awal
  window.claimState.modalOpen = false;
  document.body.classList.remove("modal-open");

  overlay.classList.remove("visible");

  setTimeout(() => {
    overlay.remove();

    // Pastikan modal utama terlihat lagi
    const modalContainer = document.querySelector("#modalContainer");
    if (modalContainer) modalContainer.classList.remove("hidden");

    // Reset flag lagi sesudah overlay benar-benar hilang
    window.claimState.modalOpen = false;

    const src = window.claimState?.regulationSource || {};
    const lastType = src.type;
    console.log("🔻 closeOverlayModal triggered:", src);

    // Bersihkan sumber supaya gak ketarik ulang
    window.claimState.regulationSource = null;
    window.claimState.pendingRestoreDiagnosis = false;

    // ⚙️ Tambah sedikit delay biar DOM settle
    setTimeout(() => {
      if (lastType === "procedure" && window.claimState?.currentProcedure?.id) {
        console.log("🩵 [RESTORE] Modal tindakan:", window.claimState.currentProcedure);
        window.openProcedureModal(
          window.claimState.currentProcedure.id,
          window.claimState.currentProcedure.name
        );
      } else if (lastType === "diagnosis" && window.claimState?.currentDiagnosis) {
        console.log("🩵 [RESTORE] Modal diagnosis (force-open):", window.claimState.currentDiagnosis);
        const diag = window.claimState.currentDiagnosis;
        const title = window.claimState.currentDiagnosisTitle || "Diagnosis";
        openModal(
          `<div class="flex flex-col items-center">
            <span class="text-lg font-bold">Detail Diagnosis</span>
            <span class="font-bold text-2xl mb-2 text-yellow-500">${title}</span>
          </div>`,
          window.renderDiagnosisDetail
            ? window.renderDiagnosisDetail(diag)
            : "<p>Diagnosis detail tidak tersedia.</p>",
          { hideDefaultClose: false }
        );
      } else {
        console.log("ℹ️ Tidak ada modal untuk direstore.");
      }
    }, 150); // 150ms delay cukup
  }, 150);
}

// ======================================================
// 🔹 Close Nested Modal (Dokter / Verifikator Flow)
// ======================================================
export function closeNestedModal() {
  if (modalClosing) {
    console.log("⚠️ [DEBUG] closeNestedModal double trigger prevented");
    return;
  }
  modalClosing = true;

  document.body.classList.remove("modal-open");

  // 🚫 VERIFIKATOR MODE
  if (window.currentUserRole === "verifikator") {
    const modalContainer = document.getElementById("modalContainer");
    if (modalContainer) {
      modalContainer.classList.add("hidden");
      modalContainer.innerHTML = "";
    }
    window.claimState.modalOpen = false;
    modalClosing = false;
    console.log("✅ [VERIFIKATOR] Modal closed cleanly.");
    return;
  }

  try {
    window.persistManualTindakanBeforeClose &&
      window.persistManualTindakanBeforeClose();
  } catch (e) {
    console.warn("⚠️ Gagal persist manual tindakan sebelum close:", e);
  }

  let modalContainer = document.getElementById("modalContainer");
  let modalContent = document.querySelector(".modal-content");
  let modalTitle = document.querySelector(".modal-title");
  const stack = window.claimState?.modalStack || [];

  if (!modalContainer) {
    modalContainer = document.createElement("div");
    modalContainer.id = "modalContainer";
    document.body.appendChild(modalContainer);
  }
  if (!modalContent) {
    modalContent = document.createElement("div");
    modalContent.className =
      "modal-content relative bg-gray-50 dark:bg-slate-800 text-slate-900 dark:text-white p-6 rounded-2xl max-h-[90vh] overflow-y-auto shadow-2xl w-[90%] max-w-4xl border border-slate-200 dark:border-slate-700";
    modalContainer.appendChild(modalContent);
  }
  if (!modalTitle) {
    modalTitle = document.createElement("div");
    modalTitle.className = "modal-title font-bold text-lg mb-2";
    modalContent.prepend(modalTitle);
  }

  modalContent.classList.add("modal-fade-exit");
  setTimeout(() => modalContent.classList.add("modal-fade-exit-active"), 10);

  setTimeout(() => {
    modalContent.classList.remove("modal-fade-exit", "modal-fade-exit-active");

    // Restore ke diagnosis?
    if (
      window.claimState?.pendingRestoreDiagnosis &&
      window.claimState?.currentDiagnosis
    ) {
        // 🩹 Re-render diagnosis modal dengan data terbaru
        try {
          const stage = window.claimState.tab || "admission";
          const tindakanBaru = window.claimState.simulasi?.[stage]?.tindakan || [];
          if (Array.isArray(tindakanBaru)) {
            window.claimState.currentDiagnosis.tindakan = tindakanBaru;
          }

          const diag = window.claimState.currentDiagnosis;
          const title = window.claimState.currentDiagnosisTitle || "Diagnosis";

          // Bersihkan isi modal lama
          const modalContainer = document.getElementById("modalContainer");
          if (modalContainer) {
            modalContainer.innerHTML = "";
            modalContainer.classList.remove("hidden");
          }

          // 🔁 Render ulang diagnosis dari data terbaru
          if (typeof window.renderDiagnosisDetail === "function") {
            const html = window.renderDiagnosisDetail(diag);
            openModal(
              `<div class="flex flex-col items-center">
                <span class="text-lg font-bold">Detail Diagnosis</span>
                <span class="font-bold text-2xl mb-2 text-yellow-500">${title}</span>
              </div>`,
              html,
              { hideDefaultClose: false }
            );
            console.log("🩵 [RENDER] Modal diagnosis di-refresh dengan tindakan terbaru");
          } else {
            console.warn("⚠️ renderDiagnosisDetail() tidak ditemukan di window.");
          }

          window.claimState.pendingRestoreDiagnosis = false;
          modalClosing = false;
          return;
        } catch (e) {
          console.error("❌ Gagal re-render modal diagnosis:", e);
          modalClosing = false;
          return;
        }
    }

    // Default restore modal
    if (stack.length > 0) {
      const prev = stack.pop();
      console.log("🧩 restore modal:", prev);
      modalTitle.innerHTML = prev.title || "(Untitled)";
      modalContent.innerHTML = prev.content || "<p>Tidak ada konten sebelumnya</p>";
    } else {
      modalContainer.classList.add("hidden");
      window.claimState.modalOpen = false;
      modalContent.innerHTML = "";
      modalTitle.innerHTML = "";
    }

    setTimeout(() => window.Alpine && Alpine.initTree(modalContent), 100);
    modalClosing = false;
  }, 250);
}

// ======================================================
// 🧩 WINDOW SHIM (Compatibility Layer)
// ======================================================
if (typeof window !== "undefined") {
  window.openModal = openModal;
  window.closeNestedModal = closeNestedModal;
  window.openOverlayModal = openOverlayModal;
  window.closeOverlayModal = closeOverlayModal;
  window.showAiLoadingModal = showAiLoadingModal;
  window.hideAiLoadingModal = hideAiLoadingModal;
}
