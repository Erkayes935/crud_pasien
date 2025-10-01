// =============== Bootstrap kecil: expose & listener form ===============

(function () {
  // Panel evaluasi (fungsi render) — tetap di window seperti versi lama
  function renderEvaluasiDiagnosis(data) {
    const target = document.getElementById("evaluasi-diagnosis");
    if (!target) return;
    target.innerHTML = "";

    if (!data || Object.keys(data).length === 0) {
      target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada evaluasi diagnosis</div>`;
      return;
    }

    const validitasIcon = window.statusIcon(data.validitas);
    const validitasText = data.validitas_detail || "-";

    target.innerHTML = `
      <h3 class="font-bold text-lg mb-2 text-yellow-500">Evaluasi Kombinasi Diagnosis</h3>
      <table class="w-full border border-gray-300 dark:border-gray-600 text-sm">
        <tr>
          <th class="border px-4 py-2">Validitas Klinis Kombinasi</th>
          <td class="border px-4 py-2">
            ${validitasIcon} - <span class="cursor-pointer" title="PNPK Evaluasi Diagnosis 2020"
               onclick="openRegulationModal(${data.id}, 'diagnosis_eval')">${validitasText}</span>
          </td>
        </tr>
        <tr>
          <th class="border px-4 py-2">Severity</th>
          <td class="border px-4 py-2">
            <span class="cursor-pointer" onclick="openRegulationModal(${data.id}, 'diagnosis_eval')">${data.severity || "-"}</span>
          </td>
        </tr>
        <tr>
          <th class="border px-4 py-2">Kode INA-CBG</th>
          <td class="border px-4 py-2">
            <span class="cursor-pointer" onclick="openRegulationModal(${data.id}, 'diagnosis_eval')">${data.kode_ina_cbg || "-"}</span>
          </td>
        </tr>
        <tr>
          <th class="border px-4 py-2">Estimasi Tarif</th>
          <td class="border px-4 py-2">${window.formatRupiah(data.estimasi_tarif) || "-"}</td>
        </tr>
        <tr>
          <th class="border px-4 py-2">Syarat Klinis (Kombinasi)</th>
          <td class="border px-4 py-2">
            <span class="cursor-pointer" onclick="openRegulationModal(${data.id}, 'diagnosis_eval')">${data.syarat || "-"}</span>
          </td>
        </tr>
        <tr>
          <th class="border px-4 py-2">Evaluasi Faskes</th>
          <td class="border px-4 py-2">
            <span class="cursor-pointer" onclick="openRegulationModal(${data.id}, 'diagnosis_eval')">${data.evaluasi_faskes || "-"}</span>
          </td>
        </tr>
        <tr>
          <th class="border px-4 py-2">Rawat Inap</th>
          <td class="border px-4 py-2">
            <span class="cursor-pointer" onclick="openRegulationModal(${data.id}, 'diagnosis_eval')">${data.rawat_inap || "-"}</span>
          </td>
        </tr>
      </table>
    `;
  }

  function renderEvaluasiProcedure(rows) {
    const target = document.getElementById("evaluasi-procedure");
    if (!target) return;
    target.innerHTML = "";

    if (!rows || rows.length === 0) {
      target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada evaluasi tindakan</div>`;
      return;
    }

    const wajib = [], validasi = [], dampak = [], konflik = [];
    rows.forEach(p => {
      const icon = window.statusIcon(p.validitas);
      const tindakan = p.tindakan || p.validitas_detail || p.status_tindakan || "-";

      if (p.status_tindakan && ["wajib","mandatory"].includes(String(p.status_tindakan).toLowerCase())) {
        wajib.push(`${icon} - <span class="cursor-pointer" onclick="openRegulationModal(${p.id}, 'procedure_eval')">${tindakan}</span>`);
      }
      if (p.status_tindakan && !["wajib","mandatory"].includes(String(p.status_tindakan).toLowerCase())) {
        validasi.push(`${icon} - ${tindakan}`);
      }
      if (p.tarif_impact && p.tarif_impact !== "-") {
        dampak.push(`${icon} <span class="cursor-pointer" onclick="openRegulationModal(${p.id}, 'procedure_eval')">${tindakan} → ${p.tarif_impact}</span>`);
      }
      if (p.syarat_klinis && p.syarat_klinis !== "-") {
        konflik.push(`${icon} - ${p.syarat_klinis}`);
      }
    });

    const listify = arr => arr.length ? arr.map(v => `<div>${v}</div>`).join("") : "-";

    target.innerHTML = `
      <h3 class="font-bold text-lg mb-2 text-yellow-500">Evaluasi Kombinasi Tindakan</h3>
      <table class="w-full border border-gray-300 dark:border-gray-600 text-sm">
        <tr><th class="border px-4 py-2">Tindakan Wajib Kombinasi</th><td class="border px-4 py-2">${listify(wajib)}</td></tr>
        <tr><th class="border px-4 py-2">Validasi Pilihan Verifikator</th><td class="border px-4 py-2">${listify(validasi)}</td></tr>
        <tr><th class="border px-4 py-2">Dampak INA-CBG / Tarif</th><td class="border px-4 py-2">${listify(dampak)}</td></tr>
        <tr><th class="border px-4 py-2">Konflik / Duplikasi</th><td class="border px-4 py-2">${listify(konflik)}</td></tr>
      </table>
    `;
  }

  function renderAlternatifKombinasi(items) {
    const target = document.getElementById("alternatif");
    if (!target) return;
    target.innerHTML = "";

    if (!items || items.length === 0) {
      target.innerHTML = `<div class="p-2 italic text-gray-500">Tidak ada alternatif kombinasi</div>`;
      return;
    }

    target.insertAdjacentHTML("beforeend", `
      <h3 class="font-bold text-lg mb-2 text-yellow-500">Alternatif Kombinasi (${items.length})</h3>
    `);

    items.forEach((alt, i) => {
      target.insertAdjacentHTML("beforeend", `
        <div class="border rounded-lg shadow mb-3 bg-white dark:bg-gray-800 p-3">
          <h4 class="font-bold text-blue-600 mb-2">Alternatif ${i + 1}: ${window.statusIcon(alt.nama) || "-"}</h4>
          <div class="text-sm">
            <div><b>Severity:</b> ${alt.severity_detail || "-"}</div>
            <div><b>INA-CBG:</b> ${alt.ina_cbg || "-"}</div>
            <div><b>Tarif:</b> ${window.formatRupiah(alt.tarif)}</div>
            <div><b>Syarat Klinis:</b> ${alt.syarat || "-"}</div>
            <div><b>Evaluasi Faskes:</b> ${alt.faskes || "-"}</div>
            <div><b>Rawat Inap:</b> ${alt.rawat_inap || "-"}</div>
            <div><b>Tindakan Wajib:</b> ${alt.tindakan_wajib || "-"}</div>
          </div>
        </div>
      `);
    });
  }

  // Expose renderer (nama sama persis dg versi lama)
  window.renderEvaluasiDiagnosis = renderEvaluasiDiagnosis;
  window.renderEvaluasiProcedure = renderEvaluasiProcedure;
  window.renderAlternatifKombinasi = renderAlternatifKombinasi;

  // Listener submit form → pastikan hidden input tersync
  document.querySelector("#claimForm")?.addEventListener("submit", () => {
    window.syncHiddenInputs && window.syncHiddenInputs();
  });
})();
