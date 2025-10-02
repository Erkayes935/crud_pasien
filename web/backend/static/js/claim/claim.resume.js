// =============== Resume Medis Feature ===============

(function() {
    let resumeModal = null;
    let currentClaimId = null;
    let currentResumeData = null;

    function initResumeFeature() {
        console.log("🚀 Resume feature initialized");
        
        // ✅ Check if button exists and assign event handler
        const existingBtn = document.getElementById('generateResumeBtn');
        if (existingBtn) {
            // Remove inline onclick to avoid conflict
            existingBtn.removeAttribute('onclick');
            existingBtn.addEventListener('click', openResumeModal);
            console.log("✅ Resume button event handler assigned");
        } else {
            console.warn("❌ Generate Resume button not found in template");
        }
    }

    async function openResumeModal() {
        // Get claim ID dari claimRoot (sama seperti claim.api.js)
        currentClaimId = document.getElementById("claimRoot")?.dataset.claimId;
        
        if (!currentClaimId) {
            alert("❌ Claim ID tidak ditemukan");
            console.error("claimRoot element or data-claim-id not found");
            return;
        }

        console.log(`📋 Opening resume modal for claim ${currentClaimId}`);

        if (!resumeModal) {
            createResumeModal();
        }

        resumeModal.style.display = 'block';
        document.body.style.overflow = 'hidden';
        
        await generateResume();
    }

    function createResumeModal() {
        const modalHTML = `
            <div id="resumeModal" class="resume-modal" style="
                display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100%; height: 100%; 
                background-color: rgba(0,0,0,0.7); overflow: auto;
            ">
                <div class="resume-modal-content" style="
                    position: relative; margin: 2% auto; width: 95%; max-width: 1000px; 
                    background: var(--modal-bg, white); color: var(--modal-text, #333);
                    border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); max-height: 95vh; 
                    overflow: hidden; display: flex; flex-direction: column;
                ">
                
                    <!-- Header -->
                    <div class="resume-modal-header" style="
                        padding: 20px; border-bottom: 2px solid #007bff; 
                        background: var(--modal-header-bg, #f8f9fa); flex-shrink: 0;
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h4 style="margin: 0; color: #007bff; font-weight: 600;">📄 Resume Medis Generator</h4>
                            <button onclick="closeResumeModal()" style="
                                background: none; border: none; font-size: 28px; cursor: pointer; 
                                color: var(--modal-text, #666); padding: 0; width: 32px; height: 32px; 
                                display: flex; align-items: center; justify-content: center;
                            ">&times;</button>
                        </div>
                    
                        <!-- Mode Switch -->
                        <div style="margin-top: 15px; color: var(--modal-text, #333);">
                            <strong>Mode:</strong>
                            <label style="margin-left: 15px; cursor: pointer;">
                                <input type="radio" name="resumeMode" value="list" checked style="margin-right: 5px;"> List Mode
                            </label>
                            <label style="margin-left: 15px; cursor: pointer;">
                                <input type="radio" name="resumeMode" value="naratif" style="margin-right: 5px;"> Naratif AI Mode
                            </label>
                        </div>
                    </div>

                    <!-- Body -->
                    <div class="resume-modal-body" style="
                        padding: 20px; flex: 1; overflow: hidden; display: flex; flex-direction: column;
                        background: var(--modal-bg, white);
                    ">
                        <!-- Preview Area -->
                        <div id="resumePreview" style="
                            border: 2px solid var(--border-color, #dee2e6); padding: 20px; 
                            background: var(--preview-bg, #f8f9fa); color: var(--modal-text, #333);
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                            font-size: 14px; line-height: 1.6; overflow-y: auto; flex: 1; 
                            margin-bottom: 20px; border-radius: 4px;
                        ">
                            <div style="text-align: center; padding: 60px 20px; color: var(--muted-text, #666);">
                                <div style="font-size: 24px; margin-bottom: 15px;">⏳</div>
                                <div style="font-size: 16px; margin-bottom: 10px;">Generating resume with OpenAI...</div>
                                <div style="font-size: 12px;">This may take 10-30 seconds</div>
                            </div>
                        </div>
                
                        <!-- Settings -->
                        <div style="
                            padding: 15px; background: var(--settings-bg, #e9ecef); 
                            border-radius: 4px; flex-shrink: 0; color: var(--modal-text, #333);
                        ">
                            <strong>⚙️ Settings:</strong>
                            <label style="margin-left: 15px; cursor: pointer;">
                                <input type="checkbox" id="includeRegulasi" checked style="margin-right: 5px;"> Sertakan Regulasi
                            </label>
                            <label style="margin-left: 15px; cursor: pointer;">
                                <input type="checkbox" id="includeObat" checked style="margin-right: 5px;"> Sertakan Obat
                            </label>
                            <label style="margin-left: 15px; cursor: pointer;">
                                <input type="checkbox" id="formatRingkas" style="margin-right: 5px;"> Format Ringkas
                            </label>
                        </div>
                    </div>

                    <!-- Footer -->
                    <div class="resume-modal-footer" style="
                        padding: 20px; border-top: 1px solid var(--border-color, #dee2e6); 
                        background: var(--modal-header-bg, #f8f9fa); flex-shrink: 0; text-align: center;
                    ">
                        <button onclick="copyResumeText()" style="
                            background: #28a745; color: white; border: none; padding: 10px 20px; margin-right: 10px; 
                            border-radius: 4px; cursor: pointer; font-size: 14px;
                        ">Copy Text</button>
                        <button onclick="exportResumePDF()" style="
                            background: #dc3545; color: white; border: none; padding: 10px 20px; margin-right: 10px; 
                            border-radius: 4px; cursor: pointer; font-size: 14px;
                        ">Export PDF</button>
                        <button onclick="closeResumeModal()" style="
                            background: #6c757d; color: white; border: none; padding: 10px 20px; 
                            border-radius: 4px; cursor: pointer; font-size: 14px;
                        ">Close</button>
                    </div>
                </div>
            </div>
        
            <!-- CSS Variables for Dark Mode -->
            <style>
                .resume-modal {
                    --modal-bg: white;
                    --modal-text: #333;
                    --modal-header-bg: #f8f9fa;
                    --preview-bg: #f8f9fa;
                    --settings-bg: #e9ecef;
                    --border-color: #dee2e6;
                    --muted-text: #666;
                }
            
                /* Dark mode detection */
                @media (prefers-color-scheme: dark) {
                    .resume-modal {
                        --modal-bg: #1f2937;
                        --modal-text: #f9fafb;
                        --modal-header-bg: #374151;
                        --preview-bg: #374151;
                        --settings-bg: #4b5563;
                        --border-color: #6b7280;
                        --muted-text: #d1d5db;
                    }
                }
            
                /* Force dark mode for dark class */
                .dark .resume-modal {
                    --modal-bg: #1f2937;
                    --modal-text: #f9fafb;
                    --modal-header-bg: #374151;
                    --preview-bg: #374151;
                    --settings-bg: #4b5563;
                    --border-color: #6b7280;
                    --muted-text: #d1d5db;
                }
            </style>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        resumeModal = document.getElementById('resumeModal');

        // Event listeners for real-time updates
        document.querySelectorAll('input[name="resumeMode"]').forEach(radio => {
            radio.addEventListener('change', generateResume);
        });

        document.querySelectorAll('#resumeModal input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', generateResume);
        });

        console.log("✅ Resume modal created");
    }

    async function generateResume() {
        try {
            const mode = document.querySelector('input[name="resumeMode"]:checked').value;
            const settings = {
                regulasi: document.getElementById('includeRegulasi').checked,
                obat: document.getElementById('includeObat').checked,
                ringkas: document.getElementById('formatRingkas').checked
            };

            console.log(`🚀 Generating resume - Mode: ${mode}, Claim: ${currentClaimId}`);

            // Show loading
            document.getElementById('resumePreview').innerHTML = `
                <div style="text-align: center; padding: 60px 20px; color: #666;">
                    <div style="font-size: 32px; margin-bottom: 20px;">🤖</div>
                    <div style="font-size: 18px; margin-bottom: 10px; color: #007bff;">
                        Generating ${mode.toUpperCase()} resume with OpenAI...
                    </div>
                    <div style="font-size: 14px; margin-bottom: 20px;">Claim ID: ${currentClaimId}</div>
                    <div style="font-size: 12px; color: #999;">Please wait...</div>
                    <div style="margin-top: 20px;">
                        <div style="display: inline-block; width: 20px; height: 20px; border: 2px solid #007bff; border-top: 2px solid transparent; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                    </div>
                </div>
                <style>
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                </style>
            `;

            // Call web backend API (sama pattern dengan claim.api.js generateAI)
            const response = await fetch(`/claims/${currentClaimId}/generate_resume`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode, settings })
            });

            console.log(`📡 API Response status: ${response.status}`);

            if (!response.ok) {
                const errorText = await response.text();
                console.error("❌ API Error:", errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log("✅ Resume generated:", result);
            
            currentResumeData = result;
            renderResumePreview(result, mode, settings);

        } catch (error) {
            console.error('❌ Error generating resume:', error);
            
            document.getElementById('resumePreview').innerHTML = `
                <div style="color: #dc3545; padding: 30px; text-align: center; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px;">
                    <div style="font-size: 24px; margin-bottom: 15px;">❌</div>
                    <div style="font-size: 16px; font-weight: bold; margin-bottom: 10px;">Error generating resume</div>
                    <div style="font-size: 14px; margin-bottom: 15px;">${error.message}</div>
                    <div style="font-size: 12px; color: #721c24;">
                        • Check if core_engine is running<br>
                        • Verify OpenAI API key is configured<br>
                        • Try refreshing the page
                    </div>
                    <button onclick="generateResume()" style="
                        margin-top: 15px; background: #007bff; color: white; border: none; 
                        padding: 8px 16px; border-radius: 4px; cursor: pointer;
                    ">🔄 Retry</button>
                </div>
            `;
        }
    }

    function renderResumePreview(data, mode, settings) {
        const preview = document.getElementById('resumePreview');
        
        let content = `
            <div style="margin-bottom: 25px;">
                <h3 style="
                    color: #007bff; border-bottom: 3px solid #007bff; padding-bottom: 8px; 
                    margin-bottom: 15px; font-weight: 600;
                ">
                    📄 Resume Medis - ${data.identitas?.nama || 'Unknown'} (${data.identitas?.no_rm || 'Unknown'})
                </h3>
                <div style="font-size: 12px; color: #666; margin-bottom: 10px;">
                    <strong>Mode:</strong> ${data.mode?.toUpperCase() || mode.toUpperCase()} | 
                    <strong>Generated:</strong> ${data.created_at ? new Date(data.created_at).toLocaleString() : new Date().toLocaleString()} |
                    <strong>AI:</strong> OpenAI GPT
                </div>
            </div>
            
            <div style="
                white-space: pre-line; line-height: 1.8; color: #333; background: white; 
                padding: 20px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px;
            ">
                ${data.naratif || 'Resume tidak tersedia'}
            </div>
        `;
        
        // Add medications if enabled
        if (settings.obat && data.obat && data.obat.length > 0) {
            content += `
                <div style="
                    margin-top: 25px; padding: 15px; background: #e8f4fd; 
                    border-left: 4px solid #007bff; border-radius: 0 4px 4px 0;
                ">
                    <h6 style="color: #007bff; margin-bottom: 10px; font-weight: 600;">💊 OBAT</h6>
                    <ul style="margin: 0; padding-left: 20px;">
                        ${data.obat.map(o => `<li style="margin-bottom: 5px;">${o.nama}${o.dosis ? ` <span style="color: #666;">(${o.dosis})</span>` : ''}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        // Add regulations if enabled
        if (settings.regulasi && data.regulasi && data.regulasi.length > 0) {
            content += `
                <div style="
                    margin-top: 20px; padding: 15px; background: #fff3cd; 
                    border-left: 4px solid #ffc107; border-radius: 0 4px 4px 0;
                ">
                    <h6 style="color: #856404; margin-bottom: 10px; font-weight: 600;">📜 REGULASI</h6>
                    <ul style="margin: 0; padding-left: 20px;">
                        ${data.regulasi.map(r => `<li style="margin-bottom: 5px;">${r.judul}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        preview.innerHTML = content;
        console.log("✅ Resume preview rendered");
    }

    function copyResumeText() {
        if (!currentResumeData) {
            alert("❌ Tidak ada data resume untuk disalin");
            return;
        }
        
        // ✅ BUILD CLEAN TEXT dari data object, bukan dari HTML
        let copyText = buildCleanResumeText(currentResumeData);
        
        if (navigator.clipboard && window.isSecureContext) {
            // Modern API
            navigator.clipboard.writeText(copyText).then(() => {
                alert('✅ Resume berhasil disalin ke clipboard');
                console.log("✅ Resume copied using Clipboard API");
            }).catch((err) => {
                console.warn("❌ Clipboard API failed:", err);
                fallbackCopy(copyText);
            });
        } else {
            // Fallback method
            fallbackCopy(copyText);
        }
    }

    function buildCleanResumeText(data) {
        const mode = document.querySelector('input[name="resumeMode"]:checked').value;
        const settings = {
            regulasi: document.getElementById('includeRegulasi').checked,
            obat: document.getElementById('includeObat').checked,
            ringkas: document.getElementById('formatRingkas').checked
        };
        
        let text = `RESUME MEDIS - ${data.identitas?.nama || 'Unknown'} (${data.identitas?.no_rm || 'Unknown'})\n`;
        text += `Mode: ${data.mode?.toUpperCase() || mode.toUpperCase()} | `;
        text += `Generated: ${data.created_at ? new Date(data.created_at).toLocaleString() : new Date().toLocaleString()} | `;
        text += `AI: OpenAI GPT\n`;
        text += `${'='.repeat(80)}\n\n`;
        
        // Main resume content - clean dari HTML tags
        const cleanContent = data.naratif ? data.naratif.replace(/<[^>]*>/g, '').trim() : 'Resume tidak tersedia';
        text += cleanContent + '\n\n';
        
        // Add medications if enabled
        if (settings.obat && data.obat && data.obat.length > 0) {
            text += `${'='.repeat(30)} OBAT ${'='.repeat(30)}\n`;
            data.obat.forEach((obat, index) => {
                text += `${index + 1}. ${obat.nama}`;
                if (obat.dosis) text += ` (${obat.dosis})`;
                text += '\n';
            });
            text += '\n';
        }
        
        // Add regulations if enabled
        if (settings.regulasi && data.regulasi && data.regulasi.length > 0) {
            text += `${'='.repeat(28)} REGULASI ${'='.repeat(28)}\n`;
            data.regulasi.forEach((reg, index) => {
                text += `${index + 1}. ${reg.judul}`;
                if (reg.keterangan) text += ` - ${reg.keterangan}`;
                text += '\n';
            });
            text += '\n';
        }
        
        text += `${'='.repeat(80)}\n`;
        text += `Generated by CRUD Pasien Resume AI - ${new Date().toLocaleString()}`;
        
        return text;
    }

    function fallbackCopy(text) {
        // Create temporary textarea
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        textArea.style.opacity = "0";
        textArea.style.pointerEvents = "none";
        textArea.style.tabIndex = "-1";
        
        document.body.appendChild(textArea);
        
        try {
            // Focus and select
            textArea.focus();
            textArea.select();
            textArea.setSelectionRange(0, textArea.value.length);
            
            // Try execCommand
            const successful = document.execCommand('copy');
            
            if (successful) {
                alert('✅ Resume berhasil disalin ke clipboard');
                console.log("✅ Resume copied using execCommand fallback");
            } else {
                throw new Error('execCommand failed');
            }
            
        } catch (err) {
            console.error('❌ All copy methods failed:', err);
            
            // Last resort - show text in modal for manual copy
            showCopyModal(text);
        } finally {
            document.body.removeChild(textArea);
        }
    }

    function showCopyModal(text) {
        // Create manual copy modal
        const copyModal = document.createElement('div');
        copyModal.innerHTML = `
            <div style="
                position: fixed; z-index: 10000; left: 0; top: 0; width: 100%; height: 100%; 
                background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center;
            ">
                <div style="
                    background: white; padding: 30px; border-radius: 8px; max-width: 90%; max-height: 80%; 
                    overflow: hidden; display: flex; flex-direction: column;
                ">
                    <h3 style="margin-top: 0; color: #007bff;">📋 Copy Resume Text</h3>
                    <p style="margin-bottom: 15px; color: #666;">
                        Silakan copy text di bawah ini secara manual:
                    </p>
                    <textarea readonly style="
                        width: 600px; height: 400px; font-family: monospace; font-size: 12px; 
                        border: 1px solid #ddd; padding: 10px; resize: none; margin-bottom: 15px;
                    ">${text}</textarea>
                    <div style="text-align: center;">
                        <button onclick="this.closest('div').parentElement.remove()" style="
                            background: #007bff; color: white; border: none; padding: 10px 20px; 
                            border-radius: 4px; cursor: pointer;
                        ">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(copyModal);
        
        // Auto-select text in textarea
        const textarea = copyModal.querySelector('textarea');
        setTimeout(() => {
            textarea.focus();
            textarea.select();
        }, 100);
    }

    function exportResumePDF() {
        if (!currentResumeData) {
            alert("❌ Tidak ada data resume untuk diexport");
            return;
        }
        
        const printWindow = window.open('', '_blank');
        const content = document.getElementById('resumePreview').innerHTML;
        const patientName = currentResumeData.identitas?.nama?.replace(/[^\w\s]/gi, '') || 'Unknown';
        
        printWindow.document.write(`
            <!DOCTYPE html>
            <html>
                <head>
                    <title>Resume Medis - ${patientName}</title>
                    <style>
                        body { 
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                            margin: 40px; line-height: 1.6; color: #333; font-size: 14px;
                        }
                        h3 { color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 5px; }
                        .resume-content { max-width: 800px; margin: 0 auto; }
                        @media print {
                            body { margin: 20px; font-size: 12px; }
                            h3 { font-size: 16px; }
                        }
                        @page { margin: 2cm; }
                    </style>
                </head>
                <body>
                    <div class="resume-content">${content}</div>
                    <div style="margin-top: 40px; font-size: 10px; color: #666; text-align: center; border-top: 1px solid #ddd; padding-top: 10px;">
                        Generated on ${new Date().toLocaleString()} by CRUD Pasien Resume AI
                    </div>
                </body>
            </html>
        `);
        
        printWindow.document.close();
        setTimeout(() => printWindow.print(), 500);
    }

    function closeResumeModal() {
        if (resumeModal) {
            resumeModal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    }

    // ✅ EXPORT GLOBAL FUNCTIONS
    window.openResumeModal = openResumeModal;
    window.closeResumeModal = closeResumeModal;
    window.copyResumeText = copyResumeText;
    window.exportResumePDF = exportResumePDF;
    window.generateResume = generateResume;

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initResumeFeature);
    } else {
        initResumeFeature();
    }
    
    setTimeout(initResumeFeature, 1000);

    console.log("📋 Resume feature script loaded");
})();