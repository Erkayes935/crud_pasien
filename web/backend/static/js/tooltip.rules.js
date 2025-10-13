// =============== Tooltip Hover System (Point G) ===============
// Implementasi tooltip untuk menampilkan rules ringkas saat hover di form fields

(function () {
    
    // Global tooltip configuration
    const TOOLTIP_CONFIG = {
        delay: 800,              // Delay before showing tooltip (ms)
        hideDelay: 200,         // Delay before hiding tooltip (ms)
        maxWidth: 400,          // Maximum tooltip width (px)
        position: 'top',        // Default position: top, bottom, left, right
        className: 'rules-tooltip'
    };

    let tooltipElement = null;
    let showTimeout = null;
    let hideTimeout = null;
    let currentField = null;

    // ============================================================
    // 🔧 Tooltip Creation and Management
    // ============================================================
    
    function createTooltipElement() {
        if (tooltipElement) return tooltipElement;

        tooltipElement = document.createElement('div');
        tooltipElement.className = `${TOOLTIP_CONFIG.className} fixed z-50 px-4 py-3 text-sm bg-white border border-gray-300 rounded-lg shadow-xl max-w-sm opacity-0 pointer-events-none transition-opacity duration-200`;
        tooltipElement.style.maxWidth = TOOLTIP_CONFIG.maxWidth + 'px';
        document.body.appendChild(tooltipElement);
        
        return tooltipElement;
    }

    function showTooltip(element, content, diagnosis = null) {
        clearTimeout(hideTimeout);
        
        const tooltip = createTooltipElement();
        tooltip.innerHTML = content;
        
        // Position tooltip
        positionTooltip(tooltip, element);
        
        // Show tooltip with fade in
        tooltip.style.opacity = '0';
        tooltip.style.pointerEvents = 'none';
        
        setTimeout(() => {
            tooltip.style.opacity = '1';
        }, 10);
    }

    function hideTooltip() {
        if (!tooltipElement) return;
        
        tooltipElement.style.opacity = '0';
        setTimeout(() => {
            if (tooltipElement && tooltipElement.style.opacity === '0') {
                tooltipElement.style.pointerEvents = 'none';
            }
        }, 200);
    }

    function positionTooltip(tooltip, element) {
        const rect = element.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        const viewport = {
            width: window.innerWidth,
            height: window.innerHeight
        };

        let top, left;

        // Try to position above the element
        top = rect.top - tooltipRect.height - 8;
        left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);

        // If tooltip goes above viewport, position below
        if (top < 8) {
            top = rect.bottom + 8;
        }

        // If tooltip goes beyond right edge, adjust left
        if (left + tooltipRect.width > viewport.width - 8) {
            left = viewport.width - tooltipRect.width - 8;
        }

        // If tooltip goes beyond left edge, adjust left
        if (left < 8) {
            left = 8;
        }

        tooltip.style.top = top + 'px';
        tooltip.style.left = left + 'px';
    }

    // ============================================================
    // 🌐 API Communication
    // ============================================================
    
    async function fetchTooltipData(fieldPath, diagnosis = null) {
        try {
            let url = `/claims/tooltip/rules/${encodeURIComponent(fieldPath)}`;
            if (diagnosis) {
                url += `?diagnosis=${encodeURIComponent(diagnosis)}`;
            }

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await response.json();
            
        } catch (error) {
            console.error('[TOOLTIP] API Error:', error);
            return {
                status: 'error',
                summary: 'Gagal memuat tooltip',
                tooltip_sections: [],
                has_rules: false
            };
        }
    }

    // ============================================================
    // 🎨 Tooltip Content Generation
    // ============================================================
    
    function generateTooltipHTML(data) {
        if (!data.has_rules) {
            return `
                <div class="text-gray-500 italic">
                    <div class="flex items-center mb-1">
                        <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                        </svg>
                        <span class="font-medium">Info Field</span>
                    </div>
                    <p>Tidak ada aturan khusus untuk field ini.</p>
                </div>
            `;
        }

        let html = `
            <div class="space-y-3">
                <div class="flex items-center mb-2">
                    <svg class="w-4 h-4 mr-2 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 4a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1V8zm8 0a1 1 0 011-1h6a1 1 0 011 1v2a1 1 0 01-1 1h-6a1 1 0 01-1-1V8zm0 4a1 1 0 011-1h6a1 1 0 011 1v2a1 1 0 01-1 1h-6a1 1 0 01-1-1v-2z" clip-rule="evenodd"/>
                    </svg>
                    <span class="font-semibold text-gray-900">Aturan Multilayer</span>
                </div>
                <p class="text-xs text-gray-600 mb-3">${data.summary}</p>
        `;

        data.tooltip_sections.forEach(section => {
            html += `
                <div class="border-l-3 border-gray-200 pl-3 py-1">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-xs font-bold ${section.color_class} uppercase tracking-wide">
                            ${section.layer}
                        </span>
                        ${section.source ? `<span class="text-xs text-gray-500">${section.source}</span>` : ''}
                    </div>
                    <p class="text-sm text-gray-700 leading-relaxed">${section.text}</p>
                </div>
            `;
        });

        if (data.total_rules > 3) {
            html += `
                <div class="mt-3 pt-2 border-t border-gray-200">
                    <p class="text-xs text-gray-500 italic">
                        +${data.total_rules - 3} aturan lainnya. Klik field untuk detail lengkap.
                    </p>
                </div>
            `;
        }

        html += '</div>';
        return html;
    }

    // ============================================================
    // 🎯 Field Detection and Event Handling
    // ============================================================
    
    function getFieldPathFromElement(element) {
        // Try to get field path from data attribute
        if (element.dataset.tooltipField) {
            return element.dataset.tooltipField;
        }

        // Try to detect from name/id attributes
        const nameAttr = element.getAttribute('name') || element.getAttribute('id') || '';
        
        // Map common form field names to rule field paths
        const fieldMappings = {
            // Diagnosis fields
            'justifikasi': 'diagnosis.justifikasi',
            'bukti_klinis': 'diagnosis.bukti_klinis', 
            'syarat_klinis': 'diagnosis.syarat_klinis',
            'kode_icd': 'diagnosis.kode_icd',
            
            // Rawat Inap fields
            'lama_rawat': 'rawat_inap.lama_rawat',
            'indikasi': 'rawat_inap.indikasi',
            'kriteria': 'rawat_inap.kriteria',
            'monitoring': 'rawat_inap.monitoring',
            
            // Tindakan fields
            'syarat_klinis_tindakan': 'tindakan.syarat_klinis',
            'status_tindakan': 'tindakan.status',
            
            // Faskes fields
            'tingkat': 'faskes.tingkat',
            'kompetensi': 'faskes.kompetensi',
            
            // Rujukan fields
            'indikasi_rujukan': 'rujukan.indikasi',
            'tujuan': 'rujukan.tujuan',
            
            // INA-CBG fields
            'tarif': 'inacbg.tarif',
            'kode_inacbg': 'inacbg.kode'
        };

        // Check for direct match
        if (fieldMappings[nameAttr]) {
            return fieldMappings[nameAttr];
        }

        // Check for partial match in longer field names
        for (const [key, value] of Object.entries(fieldMappings)) {
            if (nameAttr.includes(key)) {
                return value;
            }
        }

        return null;
    }

    function getCurrentDiagnosis() {
        // Try to get current diagnosis from page context
        // Look for diagnosis code in various possible locations
        
        // From Alpine.js data if available
        if (typeof window.claimData !== 'undefined' && window.claimData.currentDiagnosis) {
            return window.claimData.currentDiagnosis;
        }
        
        // From form fields
        const diagnosisFields = [
            'input[name*="diagnosis"]',
            'input[name*="kode_icd"]', 
            'select[name*="diagnosis"]'
        ];
        
        for (const selector of diagnosisFields) {
            const element = document.querySelector(selector);
            if (element && element.value) {
                return element.value;
            }
        }
        
        // From URL or page context
        if (window.location.pathname.includes('/claims/')) {
            const matches = window.location.pathname.match(/\/claims\/(\d+)/);
            if (matches) {
                // Could potentially fetch diagnosis for this claim ID
                // For now, return null to get general rules
            }
        }
        
        return null;
    }

    // ============================================================
    // 🚀 Event Handlers
    // ============================================================
    
    function handleMouseEnter(event) {
        const element = event.target;
        const fieldPath = getFieldPathFromElement(element);
        
        if (!fieldPath) return;
        
        clearTimeout(showTimeout);
        clearTimeout(hideTimeout);
        
        showTimeout = setTimeout(async () => {
            if (currentField === fieldPath) return; // Avoid duplicate requests
            
            currentField = fieldPath;
            const diagnosis = getCurrentDiagnosis();
            
            // Show loading tooltip first
            showTooltip(element, `
                <div class="flex items-center">
                    <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Memuat aturan...</span>
                </div>
            `, diagnosis);
            
            // Fetch tooltip data
            const data = await fetchTooltipData(fieldPath, diagnosis);
            const content = generateTooltipHTML(data);
            
            // Update tooltip with actual content
            if (currentField === fieldPath) { // Make sure we're still on the same field
                showTooltip(element, content, diagnosis);
            }
            
        }, TOOLTIP_CONFIG.delay);
    }

    function handleMouseLeave(event) {
        clearTimeout(showTimeout);
        currentField = null;
        
        hideTimeout = setTimeout(() => {
            hideTooltip();
        }, TOOLTIP_CONFIG.hideDelay);
    }

    // ============================================================
    // 🎬 Initialization
    // ============================================================
    
    function initializeTooltips() {
        // Auto-detect tooltip-enabled fields
        const tooltipSelectors = [
            'input[data-tooltip-field]',           // Explicitly marked fields
            'textarea[data-tooltip-field]',
            'select[data-tooltip-field]',
            'input[name*="justifikasi"]',          // Auto-detect common fields
            'textarea[name*="justifikasi"]',
            'input[name*="syarat_klinis"]',
            'textarea[name*="syarat_klinis"]',
            'input[name*="lama_rawat"]',
            'input[name*="indikasi"]',
            'textarea[name*="indikasi"]',
            'input[name*="kriteria"]',
            'textarea[name*="kriteria"]',
            'input[name*="monitoring"]',
            'textarea[name*="monitoring"]'
        ];

        tooltipSelectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                element.addEventListener('mouseenter', handleMouseEnter);
                element.addEventListener('mouseleave', handleMouseLeave);
                
                // Add visual indicator that tooltip is available
                if (!element.classList.contains('tooltip-enabled')) {
                    element.classList.add('tooltip-enabled');
                    element.style.borderColor = '#3b82f6'; // Blue border hint
                }
            });
        });
        
        console.log(`[TOOLTIP] Initialized tooltips for ${document.querySelectorAll(tooltipSelectors.join(', ')).length} fields`);
    }

    // ============================================================
    // 🌍 Global API
    // ============================================================
    
    // Expose tooltip functions globally for manual usage
    window.RulesTooltip = {
        init: initializeTooltips,
        show: showTooltip,
        hide: hideTooltip,
        addToField: function(selector, fieldPath) {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                element.dataset.tooltipField = fieldPath;
                element.addEventListener('mouseenter', handleMouseEnter);
                element.addEventListener('mouseleave', handleMouseLeave);
            });
        }
    };

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeTooltips);
    } else {
        initializeTooltips();
    }

})();

// =============== End of Tooltip System ===============