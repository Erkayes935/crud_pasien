// ============================================================
// claim.modals.notes.js (Lossless Refactor)
// ============================================================
// Menangani sistem catatan dokter / coder / verifikator.
// ============================================================

function normalizeFieldKey(key) {
  if (!key) return key;
  key = key.toLowerCase();
  const mapping = {
    diagnosis: "primary_diagnosis",
    utama_diagnosis: "primary_diagnosis",
    komorbid: "secondary_diagnosis",
    komplikasi: "secondary_diagnosis",
    tindakan: "primary_action",
    utama_tindakan: "primary_action",
    prosedur: "primary_action",
    prosedur_sekunder: "secondary_action",
  };
  return mapping[key] || key;
}

function getStableItemId(claimId, stage, fieldKey, itemName = "") {
  const key = (fieldKey || "").toLowerCase();
  if (["primary_diagnosis", "diagnosis", "utama_diagnosis"].includes(key)) return 1;
  if (["secondary_diagnosis", "komorbid", "komplikasi"].includes(key)) return 2;
  if (["primary_action", "tindakan", "utama_tindakan", "prosedur"].includes(key)) return 3;
  if (["secondary_action", "prosedur_sekunder"].includes(key)) return 4;
  return 9999;
}

function getOriginItemId(item) {
  if (item && item.diagnosis_id) return item.diagnosis_id;
  if (item && item.procedure_id) return item.procedure_id;
  return item?.id || null;
}

export async function openNoteModal(title, fieldKey, item = null) {
  const root = document.getElementById("claimRoot");
  let state = null;
  try {
    state = Alpine.$data(root);
  } catch {
    console.warn("⚠️ fallback ke window.claimState karena Alpine belum aktif");
    state = window.claimState || {};
  }

  const claimId = root.dataset.claimId;
  const currentStage = state.tab || window.claimState?.tab || "admission";

  fieldKey = normalizeFieldKey(fieldKey);
  state.currentNoteItem = item;
  state.currentNoteField = fieldKey;
  state.currentNoteStage = currentStage;

  const itemName = item?.name || "primary";
  let itemId = item?.id || null;

  if (state.role === "coder") {
    const originId = getOriginItemId(item);
    itemId = originId || getStableItemId(claimId, currentStage, fieldKey, itemName);
  } else if (!itemId) {
    itemId = getStableItemId(claimId, currentStage, fieldKey, itemName);
  }

  console.log("📝 openNoteModal context:", { stage: currentStage, fieldKey, itemId, itemName });

  let notes = [];
  try {
    const url = `/claims/${claimId}/notes?stage=${currentStage}&field_key=${fieldKey}&item_id=${itemId}`;
    const res = await fetch(url);
    const json = await res.json();
    if (res.ok) {
      const oldIds = [804880226, 2184760293, 32548051, 1, 2];
      notes = (json.data || []).filter(
        (n) =>
          n.stage === currentStage &&
          n.field_key === fieldKey &&
          (String(n.item_id) === String(itemId) || oldIds.includes(Number(n.item_id)))
      );
    }
  } catch (err) {
    console.error("❌ Gagal fetch notes:", err);
  }

  const logs = notes.map((n) => {
    const utcString = n.timestamp?.endsWith("Z") ? n.timestamp : n.timestamp + "Z";
    const time = new Date(utcString).toLocaleString("id-ID", {
      timeZone: "Asia/Jakarta",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
    return `[${n.role} ${time} WIB] ${n.note_text}`;
  });

  const currentText = logs.join("\n");
  state.modalTitle = `${title} - ${currentStage.toUpperCase()}`;
  state.modalContent = `
    <div class="space-y-4">
      <label class="block text-sm font-medium">Tambahkan Catatan:</label>
      <textarea id="noteField"
                class="w-full border rounded p-2 text-sm bg-white text-gray-800
                      focus:outline-none focus:ring-2 focus:ring-blue-400
                      dark:bg-gray-100 dark:text-gray-900"
                rows="4"
                placeholder="Tulis catatan..."></textarea>

      <div class="flex justify-end gap-2">
        <button type="button"
                class="px-4 py-2 rounded bg-gray-600 hover:bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-white"
                onclick="Alpine.$data(document.getElementById('claimRoot')).modalOpen=false">
          Close
        </button>
        <button type="button"
                class="px-4 py-2 rounded bg-blue-600 text-white"
                onclick="saveNote('${fieldKey}', '${currentStage}', ${itemId})">
          Save & Close
        </button>
      </div>

      <hr class="my-4 border-gray-300 dark:border-gray-700">
      <h4 class="font-semibold text-sm">Riwayat Catatan (${notes.length}):</h4>
      <pre class="bg-gray-100 dark:bg-white text-gray-900 dark:bg-gray-800 dark:text-white p-2 rounded text-xs whitespace-pre-wrap max-h-60 overflow-y-auto text-gray-800 dark:text-gray-100">
        ${currentText || 'Belum ada catatan.'}
      </pre>
    </div>
  `;
  state.modalOpen = true;
}

export async function saveNote(fieldKey, stage, itemId) {
  const root = document.getElementById("claimRoot");
  const state = Alpine.$data(root);
  const textarea = document.getElementById("noteField");
  const val = textarea.value.trim();
  if (!val) {
    state.modalOpen = false;
    return;
  }

  fieldKey = normalizeFieldKey(fieldKey);
  const claimId = root.dataset.claimId;

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
        stage: stage,
      }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    // Tambahkan ke local state agar langsung tampil tanpa reload
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    const role = state.role || "User";
    const log = `[${role} ${hh}:${mm}] ${val}`;


    if (!state.notes) state.notes = {};
    if (!state.notes[stage]) state.notes[stage] = {};
    if (!state.notes[stage][fieldKey]) state.notes[stage][fieldKey] = {};
    if (!state.notes[stage][fieldKey][itemId]) state.notes[stage][fieldKey][itemId] = [];
    state.notes[stage][fieldKey][itemId].push(log);


    console.log("✅ Note saved successfully", { stage, fieldKey, itemId });
  } catch (e) {
    console.error("❌ saveNote error:", e);
    alert("Gagal menyimpan catatan: " + e.message);
  }

  state.modalOpen = false;
}

// ============================================================
// 🪟 WINDOW SHIM
// ============================================================
if (typeof window !== "undefined") {
  window.openNoteModal = openNoteModal;
  window.saveNote = saveNote;
}
