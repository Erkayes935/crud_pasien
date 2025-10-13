# 🧪 DUMMY DATA UNTUK TEST ADMIN RS RULES MANAGEMENT

## Login Credentials
- **Admin RS**: newacc@mail.com
- **Password**: DAL4T8kauKW7BQu

## URL Test
- Dashboard: http://localhost:8001/dashboard
- Rules Management: http://localhost:8001/admin-rs/rules

---

## 📋 TEST CASE 1: PPK RS - Hipertensi

### Form Data:
- **Jenis Aturan**: ☑️ PPK RS (Override Priority)  
- **Diagnosis**: `Hipertensi Esensial`
- **Field Aturan**: `rawat_inap.lama_rawat` (dari dropdown)
- **Isi Aturan**: `LOS maksimal 5 hari untuk hipertensi krisis tanpa komplikasi organ target. Jika ada komplikasi jantung/ginjal, LOS dapat diperpanjang hingga 10 hari.`
- **Sumber Referensi**: `PPK RS Kardiologi - Guideline Hipertensi 2024`

---

## 📋 TEST CASE 2: RS Lokal - Gastritis

### Form Data:
- **Jenis Aturan**: ☑️ RS Lokal (BA/SOP)
- **Diagnosis**: `Gastritis Akut`
- **Field Aturan**: `obat.analgesik` (dari dropdown)
- **Isi Aturan**: `Hindari NSAID. Gunakan Paracetamol maksimal 3g/hari. PPI (Omeprazole 20mg 2x1) wajib diberikan minimal 7 hari.`
- **Sumber Referensi**: `SOP RS Gastroenterologi Rev.2 2024`

---

## 📋 TEST CASE 3: PPK RS - Demam Berdarah

### Form Data:
- **Jenis Aturan**: ☑️ PPK RS (Override Priority)
- **Diagnosis**: `Demam Berdarah Dengue`
- **Field Aturan**: `lab.hematologi` (dari dropdown)
- **Isi Aturan**: `Monitoring Hb, Ht, Trombosit setiap 6 jam. Jika trombosit <100rb atau Ht naik >20%, segera konsul ke intensivis.`
- **Sumber Referensi**: `PPK RS Tropik - Protokol DBD WHO 2024`

---

## 📋 TEST CASE 4: RS Lokal - Typhoid

### Form Data:
- **Jenis Aturan**: ☑️ RS Lokal (BA/SOP)
- **Diagnosis**: `Typhoid Fever`
- **Field Aturan**: `obat.antibiotik` (dari dropdown)
- **Isi Aturan**: `First line: Ceftriaxone 2g 1x1 IV selama 7 hari. Alternatif: Chloramphenicol 500mg 4x1 PO. Hindari Ciprofloxacin untuk anak <18 tahun.`
- **Sumber Referensi**: `Formularium RS - Antibiotik Infeksi Sistemik 2024`

---

## 📋 TEST CASE 5: PPK RS - Asma Bronkial

### Form Data:
- **Jenis Aturan**: ☑️ PPK RS (Override Priority)
- **Diagnosis**: `Asma Bronkial Eksaserbasi Akut`
- **Field Aturan**: `tindakan.non_bedah` (dari dropdown)
- **Isi Aturan**: `Nebulisasi Salbutamol 2.5mg + Ipratropium 500mcg setiap 20 menit x3. Jika tidak respon, berikan Methylprednisolone 125mg IV.`
- **Sumber Referensi**: `PPK RS Pulmonologi - GINA Guidelines 2024`

---

## 📋 TEST CASE 6: RS Lokal - Diabetes Ketoasidosis

### Form Data:
- **Jenis Aturan**: ☑️ RS Lokal (BA/SOP)
- **Diagnosis**: `Diabetic Ketoacidosis`
- **Field Aturan**: `lab.kimia_darah` (dari dropdown)
- **Isi Aturan**: `Monitoring GDS, elektrolit, AGD setiap 2 jam. Target penurunan GDS 50-75 mg/dL/jam. Koreksi kalium sebelum insulin jika K+ <3.3 mEq/L.`
- **Sumber Referensi**: `SOP ICU - Manajemen DKA Dewasa 2024`

---

## 📋 TEST CASE 7: PPK RS - Infark Miokard

### Form Data:
- **Jenis Aturan**: ☑️ PPK RS (Override Priority)
- **Diagnosis**: `ST Elevation Myocardial Infarction`
- **Field Aturan**: `tindakan.bedah` (dari dropdown)
- **Isi Aturan**: `Primary PCI dalam door-to-balloon time <90 menit. Jika tidak tersedia fasilitas PCI, berikan fibrinolitik dalam 30 menit dan transfer ke PCVC.`
- **Sumber Referensi**: `PPK RS Jantung - ESC STEMI Guidelines 2024`

---

## 📋 TEST CASE 8: RS Lokal - Appendicitis

### Form Data:
- **Jenis Aturan**: ☑️ RS Lokal (BA/SOP)
- **Diagnosis**: `Appendicitis Akut`
- **Field Aturan**: `rawat_inap.lama_rawat` (dari dropdown)
- **Isi Aturan**: `Post appendectomy: LOS 2-3 hari untuk kasus simple, 5-7 hari untuk complicated appendicitis. Mobilisasi dini 6 jam post op.`
- **Sumber Referensi**: `SOP Bedah Digestif - Appendectomy Protocol 2024`

---

## 🎯 EXPECTED RESULTS

Setelah submit, rules harus:

1. **Masuk ke database** dengan status = `"unverified"`
2. **Muncul di tabel** pada tab "Menunggu" 
3. **Counter berubah** di summary cards
4. **Dapat dilihat** di endpoint `/claims/rules/my_rules`

---

## 🔍 VERIFICATION STEPS

### Step 1: Test via Browser
1. Login ke http://localhost:8001 dengan credentials admin_rs
2. Dashboard → klik "📋 Rules Management"
3. Klik "+ Tambah Aturan" 
4. Input salah satu test case di atas
5. Submit dan cek hasilnya

### Step 2: Test via API (Optional)
```bash
# Test endpoint langsung
curl -X GET "http://localhost:8001/claims/rules/my_rules" \
  -H "Cookie: session=<session_cookie>"
```

### Step 3: Database Check (Optional)
```sql
-- Check rules yang baru ditambahkan
SELECT id, diagnosis, field, layer, isi, status, created_at 
FROM rules_master 
WHERE layer IN ('ppk', 'rs') 
ORDER BY created_at DESC 
LIMIT 5;
```

---

## 🚨 TROUBLESHOOTING

**Jika form tidak submit:**
- Check browser console untuk JavaScript errors
- Pastikan endpoint `/claims/rules/add` accessible
- Verify CSRF token issues

**Jika data tidak muncul:**
- Check database connection
- Verify rs_id mapping
- Check user hospital association

**Jika authentication gagal:**
- Clear browser cookies
- Re-login dengan credentials yang benar
- Check session middleware

---

## 📊 SUCCESS METRICS

✅ **Form validation bekerja** (required fields)  
✅ **Submit berhasil** (status 200 response)  
✅ **Data tersimpan** di database  
✅ **UI update** (counter + table refresh)  
✅ **Status filtering** (tabs berfungsi)  

Selamat testing! 🎉