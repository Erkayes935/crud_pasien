// =============== Utils (global, tanpa dependency khusus) ===============

(function () {
  // Badge status untuk panel evaluasi (HTML string)
  function statusIcon(val) {
    if (!val) return `<span class="text-gray-400"></span>`;
    const v = String(val).toLowerCase();
    if (v.includes("valid")) return `<span class="text-green-600 font-bold">✔️ ${val}</span>`;
    if (v.includes("invalid")) return `<span class="text-red-600 font-bold">❌ ${val}</span>`;
    if (v.includes("warning") || v.includes("butuh")) return `<span class="text-yellow-600 font-bold">⚠️ ${val}</span>`;
    return val;
  }

  function truncateText(text, maxLength = 100) {
    if (!text || text.length <= maxLength) return text || "";
    return text.substring(0, maxLength) + "...";
  }


  function formatRupiah(value) {
    if (value === null || value === undefined || value === "") return "-";

    // Jika sudah berawalan "Rp", kembalikan apa adanya
    if (typeof value === "string" && value.trim().startsWith("Rp")) return value;

    // Hapus semua karakter non-digit
    const numeric = Number(String(value).replace(/[^\d]/g, ""));
    if (isNaN(numeric) || numeric === 0) return "-";

    return "Rp " + numeric.toLocaleString("id-ID");
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
    if (!state.simulasi) return;

    // 🧩 buat salinan lengkap utk backend
    const cloned = JSON.parse(JSON.stringify(state.simulasi));

    // flatten semua children agar backend tetap dapat
    for (const [tab, obj] of Object.entries(cloned)) {
      for (const [type, arr] of Object.entries(obj)) {
        if (Array.isArray(arr)) {
          const children = arr
            .filter(p => Array.isArray(p.children) && p.children.length > 0)
            .flatMap(p =>
              p.children.map(ch => ({
                ...ch,
                parentRef: p.id || p.kategori,
              }))
            );
          if (children.length) {
            arr.push(...children); // hanya utk payload yg disimpan
          }
        }
      }
    }

    if (simInput) simInput.value = JSON.stringify(cloned);
    if (summInput) summInput.value = JSON.stringify(state.summary || {});
  }

  function mergeTextAndRules(baseText, rules) {
    if (!rules || !rules.items) return baseText || "-";
    const multilayerHtml = rules.items
      .map(
        (r) =>
          `<li class="ml-5 list-disc text-sm">${r.isi} <span class="text-gray-400 text-xs">(${r.sumber})</span></li>`
      )
      .join("");
    return `
      <div class="space-y-1">
        <div>${baseText || "-"}</div>
        <ul class="list-disc pl-4 text-sm">${multilayerHtml}</ul>
      </div>`;
  }

  // Tambahan utility functions untuk normalisasi data

  // Function untuk normalisasi data array
  window.normalizeArrayData = function(data) {
    if (!data) {
      return [];
    }
    
    if (Array.isArray(data)) {
      return data;
    }
    
    // Jika object dengan rows atau items property
    if (data.rows && Array.isArray(data.rows)) {
      return data.rows;
    }
    
    if (data.items && Array.isArray(data.items)) {
      return data.items;
    }
    
    // Jika object tapi bukan array, bungkus dalam array
    if (typeof data === 'object') {
      return [data];
    }
    
    return [];
  };

  // Utility functions untuk rendering iDRG data

  // Function untuk render rekomendasi sebagai HTML
  window.renderRekomendasi = function(rekomendasi) {
    if (!rekomendasi) return '-';
    
    if (Array.isArray(rekomendasi) && rekomendasi.length > 0) {
      return `<ul class="list-disc pl-5 space-y-1">${rekomendasi.map(item => `<li>${item}</li>`).join('')}</ul>`;
    } else if (typeof rekomendasi === 'string') {
      return rekomendasi;
    }
    
    return '-';
  };

  // Export ke window
  window.statusIcon = statusIcon;
  window.truncateText = truncateText;
  window.formatRupiah = formatRupiah;
  window.confidenceBadge = confidenceBadge;
  window.syncHiddenInputs = syncHiddenInputs;
  window.mergeTextAndRules = mergeTextAndRules;
})();
