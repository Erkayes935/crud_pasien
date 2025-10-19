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
        
        // Extract data dari response
        const pasien = data.identitas || {};
        const visit = data.visit || {};
        const diagnosis = data.diagnosis || {};
        const tindakan = data.tindakan || {};
        const obat = data.obat || [];
        const dokter = data.dokter || {};
        
        let content = `
            <div style="
                background: white; color: #333; font-family: 'Segoe UI', Arial, sans-serif;
                border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                margin: 0; padding: 0;
            ">
                <!-- Header dengan Logo -->
                <div style="
                    background: linear-gradient(135deg, #2563EB, #1E40AF); 
                    color: white; padding: 25px; text-align: center; position: relative;
                ">
                    <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 15px;">
                        <div style="
                            background: white; width: 60px; height: 60px; border-radius: 12px; 
                            display: flex; align-items: center; justify-content: center; margin-right: 15px;
                            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                        ">
                            <svg width="36" height="36" viewBox="0 0 100 100" style="fill: #2563EB;">
                                <path d="M50 10 C70 10 85 25 85 45 C85 60 75 72 60 75 L60 85 C60 90 55 95 50 95 C45 95 40 90 40 85 L40 75 C25 72 15 60 15 45 C15 25 30 10 50 10 Z"/>
                                <circle cx="40" cy="40" r="6" fill="white"/>
                                <circle cx="60" cy="40" r="6" fill="white"/>
                                <path d="M35 55 Q50 65 65 55" stroke="white" stroke-width="3" fill="none" stroke-linecap="round"/>
                                <path d="M30 25 L35 30 M65 30 L70 25" stroke="white" stroke-width="2" stroke-linecap="round"/>
                            </svg>
                        </div>
                        <div>
                            <div style="font-size: 24px; font-weight: bold; margin: 0;">AIClaim</div>
                            <div style="font-size: 14px; opacity: 0.9;">AI-Powered Medical Resume</div>
                        </div>
                    </div>
                    
                    <h1 style="
                        font-size: 22px; font-weight: 600; margin: 0; 
                        text-shadow: 0 1px 3px rgba(0,0,0,0.3);
                    ">
                        RESUME MEDIS / DISCHARGE SUMMARY
                    </h1>
                    <div style="font-size: 16px; margin-top: 5px; opacity: 0.95;">
                        ${pasien.nama || 'Pasien'} (${pasien.no_rm || 'RM0000'})
                    </div>
                    <div style="
                        position: absolute; top: 20px; right: 25px; 
                        background: rgba(255,255,255,0.2); padding: 8px 12px; 
                        border-radius: 20px; font-size: 12px;
                    ">
                        ${new Date().toLocaleDateString('id-ID')}
                    </div>
                </div>

                <!-- Body Content -->
                <div style="padding: 0;">
                    
                    <!-- I. Identitas Pasien -->
                    <div style="background: #F8FAFC; border-left: 4px solid #2563EB; margin: 0;">
                        <h2 style="
                            background: #2563EB; color: white; margin: 0; padding: 12px 20px; 
                            font-size: 16px; font-weight: 600;
                        ">
                            I. Identitas Pasien
                        </h2>
                        <div style="padding: 20px; background: white;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr><td style="padding: 8px 0; width: 150px; font-weight: 600;">Nama Pasien</td><td>${pasien.nama || '-'}</td></tr>
                                <tr><td style="padding: 8px 0; font-weight: 600;">No. RM</td><td>${pasien.no_rm || '-'}</td></tr>
                                <tr><td style="padding: 8px 0; font-weight: 600;">Jenis Kelamin</td><td>${pasien.jk || '-'}</td></tr>
                                <tr><td style="padding: 8px 0; font-weight: 600;">Usia</td><td>${pasien.umur || '-'} tahun</td></tr>
                                <tr><td style="padding: 8px 0; font-weight: 600;">Ruang Perawatan</td><td>${visit.ruangan || '-'}</td></tr>
                                <tr><td style="padding: 8px 0; font-weight: 600;">Tanggal Masuk</td><td>${visit.tgl_masuk || '-'}</td></tr>
                            </table>
                        </div>
                    </div>

                    <!-- II. Ringkasan Klinis -->
                    <div style="background: #F8FAFC; border-left: 4px solid #2563EB; margin-top: 1px;">
                        <h2 style="
                            background: #2563EB; color: white; margin: 0; padding: 12px 20px; 
                            font-size: 16px; font-weight: 600;
                        ">
                            II. Ringkasan Klinis
                        </h2>
                        <div style="padding: 20px; background: white;">
                            <div style="margin-bottom: 15px;">
                                <strong>Keluhan Utama:</strong> ${pasien.keluhan || 'Tidak ada keluhan tercatat'}
                            </div>
                            <div style="margin-bottom: 15px;">
                                <strong>Riwayat Penyakit:</strong> ${data.riwayat_penyakit || 'Tidak ada riwayat penyakit'}
                            </div>
                            <div>
                                <strong>TTV / Pemeriksaan:</strong> ${data.ttv || 'Tidak ada data TTV'}
                            </div>
                        </div>
                    </div>

                    <!-- III. Diagnosis -->
                    <div style="background: #F8FAFC; border-left: 4px solid #2563EB; margin-top: 1px;">
                        <h2 style="
                            background: #2563EB; color: white; margin: 0; padding: 12px 20px; 
                            font-size: 16px; font-weight: 600;
                        ">
                            III. Diagnosis
                        </h2>
                        <div style="padding: 20px; background: white;">
                            <div style="margin-bottom: 10px;">
                                <strong>Utama:</strong> ${diagnosis.utama?.nama || 'Belum ada diagnosis utama'} ${diagnosis.utama?.icd ? `(${diagnosis.utama.icd})` : ''}
                            </div>
                            <div>
                                <strong>Sekunder:</strong>
                                ${diagnosis.sekunder && diagnosis.sekunder.length > 0 
                                    ? diagnosis.sekunder.map(d => `<br>• ${d.nama} ${d.icd ? `(${d.icd})` : ''}`).join('')
                                    : '<br>• Tidak ada diagnosis sekunder'
                                }
                            </div>
                        </div>
                    </div>

                    <!-- IV. Tindakan -->
                    <div style="background: #F8FAFC; border-left: 4px solid #2563EB; margin-top: 1px;">
                        <h2 style="
                            background: #2563EB; color: white; margin: 0; padding: 12px 20px; 
                            font-size: 16px; font-weight: 600;
                        ">
                            IV. Tindakan
                        </h2>
                        <div style="padding: 20px; background: white;">
                            <div style="margin-bottom: 10px;">
                                <strong>Utama:</strong> ${tindakan.utama?.nama || 'Belum ada tindakan utama'} ${tindakan.utama?.kode ? `(${tindakan.utama.kode})` : ''}
                            </div>
                            <div>
                                <strong>Sekunder:</strong>
                                ${tindakan.sekunder && tindakan.sekunder.length > 0 
                                    ? tindakan.sekunder.map(t => `<br>• ${t.nama} ${t.kode ? `(${t.kode})` : ''}`).join('')
                                    : '<br>• Tidak ada tindakan sekunder'
                                }
                            </div>
                        </div>
                    </div>

                    <!-- V. Terapi Obat -->
                    <div style="background: #F8FAFC; border-left: 4px solid #2563EB; margin-top: 1px;">
                        <h2 style="
                            background: #2563EB; color: white; margin: 0; padding: 12px 20px; 
                            font-size: 16px; font-weight: 600;
                        ">
                            V. Terapi Obat
                        </h2>
                        <div style="padding: 20px; background: white;">
                            ${obat && obat.length > 0 
                                ? obat.map(o => `<div style="margin-bottom: 8px;"><strong>${o.nama}</strong> ${o.dosis || ''}</div>`).join('')
                                : '<div style="color: #666; font-style: italic;">Tidak ada data obat</div>'
                            }
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <div style="
                    background: #F1F5F9; border-top: 1px solid #E2E8F0; 
                    padding: 20px; text-align: center; color: #64748B; font-size: 12px;
                ">
                    Generated automatically by AI Claim Core | Version 2025.10<br>
                    Tanggal Generate: ${new Date().toLocaleDateString('id-ID', { 
                        day: 'numeric', month: 'long', year: 'numeric', 
                        hour: '2-digit', minute: '2-digit' 
                    })} WIB
                </div>
            </div>
        `;

        
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
        
        // Extract data
        const pasien = data.identitas || {};
        const visit = data.visit || {};
        const diagnosis = data.diagnosis || {};
        const tindakan = data.tindakan || {};
        const obat = data.obat || [];
        const dokter = data.dokter || {};
        
        let text = `RESUME MEDIS / DISCHARGE SUMMARY\n`;
        text += `${pasien.nama || 'Pasien'} (${pasien.no_rm || 'RM0000'})\n`;
        text += `${'='.repeat(80)}\n\n`;
        
        // I. Identitas Pasien
        text += `I. IDENTITAS PASIEN\n`;
        text += `• Nama Pasien      : ${pasien.nama || '-'}\n`;
        text += `• No. RM           : ${pasien.no_rm || '-'}\n`;
        text += `• Jenis Kelamin    : ${pasien.jk || '-'}\n`;
        text += `• Usia             : ${pasien.umur || '-'} tahun\n`;
        text += `• Ruang Perawatan  : ${visit.ruangan || '-'}\n`;
        text += `• Tanggal Masuk    : ${visit.tgl_masuk || '-'}\n\n`;
        
        // II. Ringkasan Klinis  
        text += `II. RINGKASAN KLINIS\n`;
        text += `• Keluhan Utama    : ${pasien.keluhan || 'Tidak ada keluhan tercatat'}\n`;
        text += `• Riwayat Penyakit : ${data.riwayat_penyakit || 'Tidak ada riwayat penyakit'}\n`;
        text += `• TTV / Pemeriksaan: ${data.ttv || 'Tidak ada data TTV'}\n\n`;
        
        // III. Diagnosis
        text += `III. DIAGNOSIS\n`;
        text += `• Utama    : ${diagnosis.utama?.nama || 'Belum ada diagnosis utama'} ${diagnosis.utama?.icd ? `(${diagnosis.utama.icd})` : ''}\n`;
        text += `• Sekunder :\n`;
        if (diagnosis.sekunder && diagnosis.sekunder.length > 0) {
            diagnosis.sekunder.forEach(d => {
                text += `  - ${d.nama} ${d.icd ? `(${d.icd})` : ''}\n`;
            });
        } else {
            text += `  - Tidak ada diagnosis sekunder\n`;
        }
        text += `\n`;
        
        // IV. Tindakan
        text += `IV. TINDAKAN\n`;
        text += `• Utama    : ${tindakan.utama?.nama || 'Belum ada tindakan utama'} ${tindakan.utama?.kode ? `(${tindakan.utama.kode})` : ''}\n`;
        text += `• Sekunder :\n`;
        if (tindakan.sekunder && tindakan.sekunder.length > 0) {
            tindakan.sekunder.forEach(t => {
                text += `  - ${t.nama} ${t.kode ? `(${t.kode})` : ''}\n`;
            });
        } else {
            text += `  - Tidak ada tindakan sekunder\n`;
        }
        text += `\n`;
        
        // V. Terapi Obat
        text += `V. TERAPI OBAT\n`;
        if (obat && obat.length > 0) {
            obat.forEach(o => {
                text += `• ${o.nama} ${o.dosis || ''}\n`;
            });
        } else {
            text += `• Tidak ada data obat\n`;
        }
        text += `\n`;
        
        // Footer
        text += `${'='.repeat(80)}\n`;
        text += `Generated automatically by AI Claim Core | Version 2025.10\n`;
        text += `Tanggal Generate: ${new Date().toLocaleDateString('id-ID', { 
            day: 'numeric', month: 'long', year: 'numeric', 
            hour: '2-digit', minute: '2-digit' 
        })} WIB\n`;
        
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
                    <meta charset="UTF-8">
                    <style>
                        body { 
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                            margin: 0; padding: 20px; line-height: 1.6; color: #333; font-size: 14px; 
                            background: white;
                        }
                        .resume-content { max-width: 210mm; margin: 0 auto; }
                        @media print {
                            body { margin: 0; padding: 10mm; font-size: 12px; }
                            .resume-content { max-width: none; margin: 0; }
                        }
                        @page { 
                            margin: 15mm; 
                            size: A4;
                        }
                        /* Ensure colors print */
                        * { -webkit-print-color-adjust: exact !important; color-adjust: exact !important; }
                    </style>
                </head>
                <body>
                    <div class="resume-content">${content}</div>
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