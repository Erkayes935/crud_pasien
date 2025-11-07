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
  // 🩹 PATCH: pastikan flag modalClosing reset supaya tombol close aktif
  window.modalClosing = false;
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
  window.claimState.modalOpen = true;
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

    // ✨ Tambahkan animasi fade-out
    overlay.classList.remove("visible");

    // Kunci scroll balik normal
    document.body.classList.remove("modal-open");

    // Tunggu 250ms (selama animasi fade-out), lalu hapus overlay
    setTimeout(() => {
      overlay.remove();

      const src = window.claimState?.regulationSource || {};
      console.log("🔻 closeOverlayModal triggered:", src);

      const lastType = src.type;
      window.claimState.regulationSource = null;

      // ❌ Reset flag agar tidak ada restore diagnosis ganda
      window.claimState.pendingRestoreDiagnosis = false;

      if (lastType === "procedure" && window.claimState?.currentProcedure?.id) {
        console.log("🩵 Restore modal tindakan:", window.claimState.currentProcedure);
        if (window.claimState.modalOpen) {
          console.warn("⛔ Skip restore tindakan karena modal masih terbuka");
          return;
        }
        openProcedureModal(
          window.claimState.currentProcedure.id,
          window.claimState.currentProcedure.name
        );
      } 
      else if (lastType === "diagnosis" && window.claimState?.currentDiagnosis) {
        console.log("🩵 Restore modal diagnosis:", window.claimState.currentDiagnosis);
        if (window.claimState.modalOpen) {
          console.warn("⛔ Skip restore diagnosis karena modal masih terbuka");
          return;
        }
        window.__suppressModalStack = true;
        openModal(
          `<div class="flex flex-col items-center">
            <span class="text-lg font-bold">Detail Diagnosis</span>
            <span class="font-bold text-2xl mb-2 text-yellow-500">
              ${window.claimState.currentDiagnosisTitle || "Diagnosis"}
            </span>
          </div>`,
          renderDiagnosisDetail(window.claimState.currentDiagnosis),
          { hideDefaultClose: false }
        );
        window.__suppressModalStack = false;
      }
    }, 250); // delay sesuai durasi animasi CSS
}

// ======================================================
// 🔹 Close Nested Modal (Dokter / Verifikator Flow)
// ======================================================
export async function closeNestedModal() {
  if (modalClosing) {
      console.log("⚠️ [DEBUG] closeNestedModal double trigger prevented");
      return;
  }
  // 🔒 reset flag otomatis 600 ms biar gak keburu stuck
  setTimeout(() => (modalClosing = false), 600);

  modalClosing = true;

  // ====================================================
  // 🩹 PATCH: Reset & arahkan close sesuai konteks modal
  // ====================================================
  try {
    // Bersihkan event listener lama biar gak double trigger
    document.querySelectorAll(".regulation-field").forEach(el => {
      const clone = el.cloneNode(true);
      el.parentNode.replaceChild(clone, el);
    });
    console.log("♻️ [CLEANUP] regulation-field listeners dibersihkan.");
  } catch (err) {
      console.warn("⚠️ cleanup regulation-field gagal:", err);
  }

  // Tutup regulasi → balik ke tindakan
  if (window.claimState.fromRegulation && typeof window.openProcedureModal === "function") {
    console.log("🔙 [FLOW] Tutup regulasi → kembali ke modal tindakan.");
    window.claimState.fromRegulation = false;
    setTimeout(() => {
      const proc = window.claimState.currentProcedure;
      if (proc) window.openProcedureModal(proc.id, proc.name);
    }, 300);
    return;
  }

  // Tutup tindakan → balik ke diagnosis
  if (window.claimState.fromProcedure && window.claimState.currentDiagnosis) {
    console.log("🔙 [FLOW] Tutup tindakan → kembali ke modal diagnosis.");
    window.claimState.fromProcedure = false;
    setTimeout(() => {
      const diag = window.claimState.currentDiagnosis;
      const title = window.claimState.currentDiagnosisTitle || "Diagnosis";
      if (typeof window.renderDiagnosisDetail === "function") {
        openModal(
          `<div class='flex flex-col items-center'>
            <span class='text-lg font-bold'>Detail Diagnosis</span>
            <span class='font-bold text-2xl mb-2 text-yellow-500'>${title}</span>
          </div>`,
          renderDiagnosisDetail(diag),
          { hideDefaultClose: false }
        );
      }
    }, 300);
    return;
  }

  console.log("🩹 [FLOW] Tutup modal biasa (diagnosis utama).");


  document.body.classList.remove("modal-open");

    // 🚫 MODE VERIFIKATOR: close langsung, tanpa stack restore & Alpine
    if (window.currentUserRole === "verifikator") {
      const modalContainer = document.getElementById("modalContainer");
      if (modalContainer) {
        modalContainer.classList.add("hidden");
        modalContainer.innerHTML = "";
      }
      window.claimState.modalOpen = false;
      modalClosing = false;
      console.log("✅ [VERIFICATOR] Modal closed cleanly.");
      return;
    }


    // 🧩 MODE DOKTER (flow lama utuh)
    try {
      window.persistManualTindakanBeforeClose && window.persistManualTindakanBeforeClose();
    } catch (e) {
      console.warn("⚠️ Gagal persist manual tindakan sebelum close:", e);
    }

    console.log(
      "🧩 [DEBUG] Simulasi tindakan sebelum close:",
      window.claimState?.simulasi?.[window.claimState?.tab || "admission"]?.tindakan
    );

    let modalContainer = document.getElementById("modalContainer");
    let modalContent = document.querySelector(".modal-content");
    let modalTitle = document.querySelector(".modal-title");
    const stack = window.claimState?.modalStack || [];

    if (!modalContainer) {
      console.warn("⚠️ closeNestedModal: modalContainer tidak ditemukan, membuat ulang.");
      modalContainer = document.createElement("div");
      modalContainer.id = "modalContainer";
      document.body.appendChild(modalContainer);
    }
    if (!modalContent) {
      console.warn("⚠️ closeNestedModal: modalContent hilang, membuat ulang.");
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

      document
        .querySelectorAll('ul[x-teleport="body"]')
        .forEach(el => el?._cleanup && el._cleanup());

      setTimeout(() => {
        Alpine.initTree(modalContent);
        setTimeout(() => {
          try {
            if (typeof window.renderManualTindakanList === "function") {
              const tab = window.claimState?.tab || "admission";
              console.log("🧩 Re-render manual tindakan setelah Alpine reinit:", tab);
              window.renderManualTindakanList(tab);
            }
          } catch (e) {
            console.warn("⚠️ Gagal renderManualTindakanList setelah restore:", e);
          }
        }, 150);
      }, 50);

      modalClosing = false;
    }, 250);

    // ✅ Balik ke modal diagnosis hanya jika sebelumnya memang dari tindakan
    // =====================================================
    // 🩹 PATCH: Restore ke diagnosis hanya jika sebelumnya dari tindakan,
    // dan tunggu modal lama benar-benar bersih dulu (500 ms)
    // =====================================================
    if (window.claimState?.pendingRestoreDiagnosis) {
      const fromProcedure = !!window.claimState.fromProcedure;
      const hasDiagnosis = !!window.claimState.currentDiagnosis;

      // matikan flag biar gak dobel
      const shouldRestore = fromProcedure && hasDiagnosis;
      window.claimState.pendingRestoreDiagnosis = false;
      window.claimState.fromProcedure = false;

    if (shouldRestore) {
      console.log("🩵 Balik ke modal diagnosis setelah tindakan ditutup");
       setTimeout(() => {
         if (!modalClosing) {               // 👉 hanya buka kalau modal bener-bener udah bersih
           openModal(
             `<div class="flex flex-col items-center">
               <span class="text-lg font-bold">Detail Diagnosis</span>
               <span class="font-bold text-2xl mb-2 text-yellow-500">
                 ${window.claimState.currentDiagnosisTitle || "Diagnosis"}
              </span>
            </div>`,
            renderDiagnosisDetail(window.claimState.currentDiagnosis),
            { hideDefaultClose: false }
          );
        }
      }, 500);
    } else {
      console.log("ℹ️ Tutup modal biasa, tidak restore diagnosis");
    }
  }
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
