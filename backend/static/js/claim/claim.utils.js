// =============== Utils (global, tanpa dependency khusus) ===============

(function () {
  // Badge status untuk panel evaluasi (HTML string)
  function statusIcon(val) {
    if (!val) return `<span class="text-gray-400">-</span>`;
    const v = String(val).toLowerCase();
    if (v.includes("valid")) return `<span class="text-green-600 font-bold">✔️ ${val}</span>`;
    if (v.includes("invalid")) return `<span class="text-red-600 font-bold">❌ ${val}</span>`;
    if (v.includes("warning") || v.includes("butuh")) return `<span class="text-yellow-600 font-bold">⚠️ ${val}</span>`;
    return val;
  }

  function truncateText(text, max) {
    return (text && text.length > max) ? text.substring(0, 20) + "…" : (text || "");
  }

  function formatRupiah(num) {
    if (!num && num !== 0) return "-";
    return "Rp " + Number(num).toLocaleString("id-ID");
  }

  function confidenceBadge(val) {
    val = parseInt(val);
    let c = val >= 80 ? 'bg-green-600' : val >= 60 ? 'bg-yellow-500' : 'bg-red-600';
    return `<span class="px-2 py-0.5 rounded text-white text-xs ${c}">${val}%</span>`;
  }

  // Sinkronkan hidden inputs sebelum submit
  function syncHiddenInputs() {
    const simInput = document.getElementById("simulasiField");
    const summInput = document.getElementById("summaryField");
    const state = window.claimState || {};

    if (simInput) simInput.value = JSON.stringify(state.simulasi || {});
    if (summInput) summInput.value = JSON.stringify(state.summary || {});
  }

  // Export ke window
  window.statusIcon = statusIcon;
  window.truncateText = truncateText;
  window.formatRupiah = formatRupiah;
  window.confidenceBadge = confidenceBadge;
  window.syncHiddenInputs = syncHiddenInputs;
})();
