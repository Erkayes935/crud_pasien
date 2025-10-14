// Test Modal Functions - Copy dari claim.modals.js yang sudah diupdate

// 🔥 Enhanced Multilayer tab modal renderer (matching showRulesModal UI)
function renderMultilayerRegulationModal(response, fieldName, diagnosisName = '') {
  if (!response || response.status !== 'success' || !response.data || response.data.length === 0) {
    return `<div class="text-center py-8">
      <div class="bg-gray-50 dark:bg-gray-800 p-6 rounded-lg">
        <p class="text-gray-500 dark:text-gray-400 mb-2">📋 Belum ada aturan khusus untuk field: <strong>${fieldName}</strong></p>
        <p class="text-xs text-gray-400 dark:text-gray-500">Sistem akan menggunakan aturan nasional standar</p>
      </div>
    </div>`;
  }

  // Group regulations by layer (same as showRulesModal)
  const rulesByLayer = {};
  const layerPriority = {
    'permenkes': 1,
    'nasional': 2,
    'ppk': 3,
    'regional': 4,
    'rs': 5,
    'bridging': 6,
    'fraud': 7,
    'temporary': 8
  };

  // Group rules by layer
  response.data.forEach(rule => {
    if (!rulesByLayer[rule.layer]) {
      rulesByLayer[rule.layer] = [];
    }
    rulesByLayer[rule.layer].push(rule);
  });

  const sortedLayers = Object.keys(rulesByLayer).sort((a, b) => 
    (layerPriority[a] || 99) - (layerPriority[b] || 99)
  );

  const fieldsCount = 1; // Single field
  const layersCount = sortedLayers.length;

  // 🎯 Build complete modal HTML (matching showRulesModal structure)
  return `
    <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto">
      
      <!-- Header -->
      <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div class="flex flex-col">
          <h3 class="font-bold text-xl text-gray-900 dark:text-gray-100">
            📘 Aturan Multilayer: <span class="text-blue-600">${fieldName}</span>
          </h3>
          ${diagnosisName ? `<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Diagnosis: <span class="text-yellow-600 font-medium">${diagnosisName}</span></p>` : ''}
        </div>
        <button type="button" onclick="closeNestedModal()"
                class="text-gray-400 hover:text-gray-700 dark:hover:text-white text-2xl font-bold">
          ✕
        </button>
      </div>

      <!-- Content -->
      <div class="p-6">
        <!-- Summary (matching showRulesModal) -->
        <div class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg mb-6">
          <h4 class="font-semibold text-blue-900 dark:text-blue-300 mb-2">🎯 Ringkasan Aturan</h4>
          <p class="text-blue-800 dark:text-blue-400 text-sm">
            Ditemukan ${fieldsCount} kategori field dengan ${layersCount} layer aturan aktif
          </p>
        </div>

        <!-- Tabs Navigation (matching showRulesModal) -->
        <div class="border-b border-gray-200 dark:border-gray-700 mb-6">
          <nav class="flex space-x-8" id="regulasiTabsNav">
            ${sortedLayers.map((layer, index) => `
              <button type="button" 
                      class="py-2 px-4 text-sm font-medium border-b-2 ${index === 0 ? 
                        'border-blue-500 text-blue-600' : 
                        'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
                      onclick="switchRegulasiTab('${layer}')"
                      id="regulasi-tab-${layer}">
                ${getLayerLabel(layer)} (${rulesByLayer[layer].length})
              </button>
            `).join('')}
          </nav>
        </div>

        <!-- Tab Content (matching showRulesModal style) -->
        <div id="regulasiTabContent">
          ${sortedLayers.map((layer, index) => `
            <div id="regulasi-content-${layer}" style="display: ${index === 0 ? 'block' : 'none'}">
              ${generateRegulasiLayerContent(layer, rulesByLayer[layer])}
            </div>
          `).join('')}
        </div>
      </div>
    </div>

    <script>
      // Tab switching function (matching showRulesModal)
      function switchRegulasiTab(activeLayer) {
        // Update tab buttons
        document.querySelectorAll('#regulasiTabsNav button').forEach(btn => {
          btn.className = btn.id === \`regulasi-tab-\${activeLayer}\` ?
            'py-2 px-4 text-sm font-medium border-b-2 border-blue-500 text-blue-600' :
            'py-2 px-4 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300';
        });
        
        // Update content
        document.querySelectorAll('#regulasiTabContent > div').forEach(content => {
          content.style.display = content.id === \`regulasi-content-\${activeLayer}\` ? 'block' : 'none';
        });
      }
    </script>
  `;
}

// Generate layer content (matching showRulesModal generateLayerContent)
function generateRegulasiLayerContent(layer, rules) {
  const isOverride = layer === 'ppk' || layer === 'rs';
  let html = '';
  
  if (isOverride) {
    html += `
      <div class="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded-lg mb-4 border-l-4 border-yellow-500">
        <p class="text-yellow-800 dark:text-yellow-300 text-sm font-medium">
          ⭐ <strong>OVERRIDE PRIORITY:</strong> Aturan layer ini akan menimpa aturan layer di atasnya
        </p>
      </div>
    `;
  }
  
  rules.forEach(rule => {
    const layerColor = getLayerColorClass(layer);
    
    html += `
      <div class="p-4 border border-gray-200 dark:border-gray-700 rounded-lg mb-4">
        <!-- Header -->
        <div class="flex items-center gap-2 mb-3">
          <span class="px-2 py-1 text-xs font-semibold rounded-full ${layerColor}">
            ${getLayerLabel(layer)}
          </span>
          <span class="text-sm font-medium text-gray-900 dark:text-gray-100">
            📋 ${rule.judul_regulasi || rule.field || 'General'}
          </span>
          ${isOverride ? '<span class="px-2 py-1 text-xs font-bold bg-yellow-100 text-yellow-800 rounded-full">⭐ OVERRIDE</span>' : ''}
        </div>
        
        <!-- Meta Information -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-2 mb-3 text-xs text-gray-500 dark:text-gray-400">
          <div><strong>Dasar Hukum:</strong> ${rule.dasar_hukum || '-'}</div>
          <div><strong>Bab/Pasal:</strong> ${rule.bab_pasal || '-'}</div>
          <div><strong>Status:</strong> 
            <span class="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">
              ${rule.status || 'official'}
            </span>
          </div>
          <div><strong>Update:</strong> ${rule.tanggal_update || new Date().toISOString().split('T')[0]}</div>
        </div>
        
        <!-- Content -->
        <div class="text-sm text-gray-800 dark:text-gray-200 mb-3 leading-relaxed">
          ${Array.isArray(rule.isi) ? rule.isi.map(item => `• ${item}`).join('<br>') : rule.isi}
        </div>
        
        <!-- Footer -->
        <div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 border-t pt-2">
          <span><strong>Sumber:</strong> ${rule.sumber || '-'}</span>
        </div>
        
        ${rule.pdf_file ? `
          <div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            <a href="/claims/rules/${rule.id}/pdf" target="_blank" 
               class="inline-flex items-center text-blue-600 hover:text-blue-800 text-sm">
              📎 Lihat Dokumen PDF
            </a>
          </div>
        ` : ''}
        
        <div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <button type="button" 
                  onclick="showFeedbackModalForRegulasi(${rule.id || 0}, '${layer}')" 
                  class="inline-flex items-center text-orange-600 hover:text-orange-800 text-sm font-medium">
            💬 Masukan untuk Regulasi Ini
          </button>
        </div>
      </div>
    `;
  });
  
  return html;
}

// Make switch function globally available
window.switchRegulasiTab = function(activeLayer) {
  // Update tab buttons
  document.querySelectorAll('#regulasiTabsNav button').forEach(btn => {
    btn.className = btn.id === `regulasi-tab-${activeLayer}` ?
      'py-2 px-4 text-sm font-medium border-b-2 border-blue-500 text-blue-600' :
      'py-2 px-4 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300';
  });
  
  // Update content
  document.querySelectorAll('#regulasiTabContent > div').forEach(content => {
    content.style.display = content.id === `regulasi-content-${activeLayer}` ? 'block' : 'none';
  });
};