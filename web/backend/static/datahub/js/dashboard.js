function dashboardApp(initialSummary) {
  return {
    // ===== STATE =====
    summary: initialSummary,
    logs: [],
    alert: false,
    alertMsg: '',
    alertType: 'success',
    showManualForm: false,
    isDark: false,
    form: {
      record_id: '',
      hospital_id: '',
      jenis_rawat: 'Rawat Inap',
      tanggal_masuk: '',
      lama_rawat: 1,
      gejala: '',
      diagnosis: '',
      tindakan: '',
      obat: ''
    },

    // ===== INIT =====
    async init() {
      this.isDark = localStorage.getItem('theme') === 'dark';
      this.applyTheme();
      await this.refreshSummary();
      await this.refreshLogs();
    },

    // ===== THEME =====
    toggleTheme() {
      this.isDark = !this.isDark;
      localStorage.setItem('theme', this.isDark ? 'dark' : 'light');
      this.applyTheme();
    },
    applyTheme() {
      document.documentElement.classList.toggle('dark', this.isDark);
    },

    // ===== REFRESH DATA =====
    async refreshSummary() {
      try {
        const res = await fetch('/monitor/summary');
        this.summary = await res.json();
      } catch (e) {
        console.error("❌ Gagal memuat summary:", e);
      }
    },
    async refreshLogs() {
      try {
        const res = await fetch('/monitor/logs');
        this.logs = await res.json();
      } catch (e) {
        console.error("❌ Gagal memuat log:", e);
      }
    },

    // ===== ALERT UTIL =====
    showAlert(msg, type = 'success', timeout = 2500) {
      this.alertMsg = msg;
      this.alertType = type;
      this.alert = true;
      setTimeout(() => (this.alert = false), timeout);
    },

    // ===== ACTIONS =====
    async submitManual() {
      try {
        const res = await fetch('/ingestion/manual', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source: 'manual', ...this.form, status: 'ready_for_ai'
          })
        });
        if (!res.ok) throw new Error(await res.text());
        this.showManualForm = false;
        this.showAlert('✅ Record berhasil disimpan', 'success');
        await this.refreshSummary();
        await this.refreshLogs();
      } catch (err) {
        console.error(err);
        this.showAlert('❌ Gagal menyimpan record', 'error');
      }
    },

    async uploadExcel(e) {
      const file = e.target.files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append('file', file);
      try {
        const res = await fetch('/ingestion/import_excel', {
          method: 'POST',
          body: formData
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        this.showAlert(`✅ ${data.rows || 0} data berhasil diupload`, 'success');
        await this.refreshSummary();
        await this.refreshLogs();
      } catch (err) {
        console.error(err);
        this.showAlert('❌ Upload gagal', 'error');
      } finally {
        this.$refs.fileInput.value = ''; // reset file input
      }
    },

    async syncGateway() {
      try {
        const payload = {
          record_id: "GW_" + Date.now(),
          hospital_id: "RS_DUMMY",
          source: "gateway",
          jenis_rawat: "Rawat Jalan",
          tanggal_masuk: new Date().toISOString().slice(0, 10),
          lama_rawat: 1,
          gejala: "Demam, Batuk",
          diagnosis: "Pneumonia",
          tindakan: "Pemberian antibiotik",
          obat: "Ceftriaxone",
          status: "ready_for_ai"
        };
        const res = await fetch('/ingestion/gateway', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(await res.text());
        this.showAlert('✅ Sinkronisasi Gateway berhasil', 'success');
        await this.refreshSummary();
        await this.refreshLogs();
      } catch (err) {
        console.error(err);
        this.showAlert('❌ Sinkronisasi Gateway gagal', 'error');
      }
    }
  };
}
