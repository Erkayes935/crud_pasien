"""
Script untuk import data tarif INA-CBG dari Excel ke Database PostgreSQL

⚡ OPTIMIZED untuk 48,000+ rows dengan batch processing

CARA PAKAI:
1. Install pandas: pip install pandas openpyxl
2. Pastikan database sudah ada (cek config di backend/config.py)
3. Jalankan migration dulu: alembic upgrade head
4. Jalankan script ini: python tools/import_inacbg_tariff.py path/to/excel.xlsx
5. Atau pakai default path: python tools/import_inacbg_tariff.py

ESTIMASI WAKTU:
- 5,000 rows: ~30 detik
- 48,000 rows: ~3-5 menit (tergantung spec komputer)

STRUKTUR EXCEL YANG DIHARAPKAN (sesuai screenshot):
- Kolom A: kode_ina_cbg
- Kolom B: deskripsi
- Kolom C: tarif_kelas_3
- Kolom D: tarif_kelas_2
- Kolom E: tarif_kelas_1
- Kolom F: tarif (default)
- Kolom G: regional
- Kolom H: kelas_rs
- Kolom I: tipe_rs
- Kolom J: layanan
- Kolom K: no
- Kolom M: page_number_pdf
"""

import pandas as pd
import sys
import os

# Add parent directory to path untuk import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web.backend.database import SessionLocal
from web.backend.models import INACBGTariff
from sqlalchemy.exc import IntegrityError


def clean_numeric(value):
    """Convert value ke numeric, handle NaN dan string"""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return int(value) if not pd.isna(value) else None
    # Remove separator ribuan jika ada
    if isinstance(value, str):
        cleaned = value.replace(',', '').replace('.', '').strip()
        try:
            return int(cleaned) if cleaned else None
        except:
            return None
    return None


def import_from_excel(excel_path: str, skip_duplicates: bool = True, batch_size: int = 1000):
    """
    Import tarif INA-CBG dari Excel ke database dengan bulk insert
    
    Args:
        excel_path: Path ke file Excel
        skip_duplicates: Jika True, skip row yang kode_cbg sudah ada
                        Jika False, update row yang sudah ada
        batch_size: Jumlah rows per batch insert (default: 1000)
    
    Returns:
        Dict dengan statistik import
    """
    
    print(f"📂 Reading Excel: {excel_path}")
    
    try:
        # Baca Excel
        df = pd.read_excel(excel_path)
        
        print(f"✅ Loaded {len(df)} rows")
        print(f"📋 Columns detected: {list(df.columns)}")
        
        # Detect column names (case-insensitive)
        col_map = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if 'kode' in col_lower and 'cbg' in col_lower:
                col_map['kode_cbg'] = col
            elif 'deskripsi' in col_lower or 'nama' in col_lower:
                col_map['deskripsi'] = col
            elif 'kelas_3' in col_lower or 'kelas 3' in col_lower:
                col_map['tarif_kelas_3'] = col
            elif 'kelas_2' in col_lower or 'kelas 2' in col_lower:
                col_map['tarif_kelas_2'] = col
            elif 'kelas_1' in col_lower or 'kelas 1' in col_lower:
                col_map['tarif_kelas_1'] = col
            elif col_lower == 'tarif' or col_lower == 'tarif ':
                col_map['tarif'] = col
            elif 'regional' in col_lower:
                col_map['regional'] = col
            elif 'kelas_rs' in col_lower or 'kelas rs' in col_lower:
                col_map['kelas_rs'] = col
            elif 'tipe_rs' in col_lower or 'tipe rs' in col_lower:
                col_map['tipe_rs'] = col
            elif 'layanan' in col_lower:
                col_map['layanan'] = col
            elif col_lower == 'no' or col_lower == 'no ':
                col_map['no'] = col
            elif 'page' in col_lower or 'pdf' in col_lower:
                col_map['page_number_pdf'] = col
        
        print(f"\n📊 Column mapping:")
        for key, value in col_map.items():
            print(f"  {key}: {value}")
        
        # Validasi kolom wajib
        if 'kode_cbg' not in col_map:
            print("❌ Error: Kolom 'kode_ina_cbg' tidak ditemukan!")
            return None
        
        # Connect ke database
        db = SessionLocal()
        
        stats = {
            'total_rows': len(df),
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'error_details': []
        }
        
        print(f"\n🔄 Processing {len(df)} rows...")
        print(f"⏱️  Estimated time: ~{int(len(df) / 200)} seconds")
        
        import time
        start_time = time.time()
        
        # Batch processing untuk bulk insert
        batch_data = []
        
        for idx, row in df.iterrows():
            try:
                # Get kode CBG
                kode_cbg = str(row[col_map['kode_cbg']]).strip()
                
                # Skip jika kosong atau header
                if pd.isna(row[col_map['kode_cbg']]) or kode_cbg == "" or kode_cbg == "kode_ina_cbg":
                    stats['skipped'] += 1
                    continue
                
                # Prepare data
                tariff_data = {
                    'kode_cbg': kode_cbg,
                    'deskripsi': str(row[col_map['deskripsi']]) if 'deskripsi' in col_map and not pd.isna(row[col_map['deskripsi']]) else None,
                    'tarif_kelas_3': clean_numeric(row[col_map['tarif_kelas_3']]) if 'tarif_kelas_3' in col_map else None,
                    'tarif_kelas_2': clean_numeric(row[col_map['tarif_kelas_2']]) if 'tarif_kelas_2' in col_map else None,
                    'tarif_kelas_1': clean_numeric(row[col_map['tarif_kelas_1']]) if 'tarif_kelas_1' in col_map else None,
                    'tarif': clean_numeric(row[col_map['tarif']]) if 'tarif' in col_map else None,
                    'regional': str(row[col_map['regional']]) if 'regional' in col_map and not pd.isna(row[col_map['regional']]) else None,
                    'kelas_rs': str(row[col_map['kelas_rs']]) if 'kelas_rs' in col_map and not pd.isna(row[col_map['kelas_rs']]) else None,
                    'tipe_rs': str(row[col_map['tipe_rs']]) if 'tipe_rs' in col_map and not pd.isna(row[col_map['tipe_rs']]) else None,
                    'layanan': str(row[col_map['layanan']]) if 'layanan' in col_map and not pd.isna(row[col_map['layanan']]) else None,
                    'no': clean_numeric(row[col_map['no']]) if 'no' in col_map else None,
                    'page_number_pdf': clean_numeric(row[col_map['page_number_pdf']]) if 'page_number_pdf' in col_map else None,
                }
                
                # Cek apakah sudah ada berdasarkan COMPOSITE KEY
                # PENTING: Kode CBG yang sama bisa punya tarif berbeda per kombinasi:
                # - kode_cbg
                # - regional (1-5)
                # - tipe_rs (RS Umum, RS Khusus, FKTP, dll)
                # - kelas_rs (A, B, C, D)
                # - layanan (Rawat Inap, Rawat Jalan)
                query = db.query(INACBGTariff).filter(INACBGTariff.kode_cbg == kode_cbg)
                
                # Filter by regional jika ada
                if tariff_data['regional']:
                    query = query.filter(INACBGTariff.regional == tariff_data['regional'])
                
                # Filter by tipe_rs jika ada  
                if tariff_data['tipe_rs']:
                    query = query.filter(INACBGTariff.tipe_rs == tariff_data['tipe_rs'])
                
                # Filter by kelas_rs jika ada
                if tariff_data['kelas_rs']:
                    query = query.filter(INACBGTariff.kelas_rs == tariff_data['kelas_rs'])
                
                # Filter by layanan jika ada (Rawat Inap vs Rawat Jalan beda tarif!)
                if tariff_data['layanan']:
                    query = query.filter(INACBGTariff.layanan == tariff_data['layanan'])
                
                existing = query.first()
                
                if existing:
                    if skip_duplicates:
                        stats['skipped'] += 1
                        if stats['skipped'] % 1000 == 0:
                            print(f"  ⏭️ Skipped {stats['skipped']:,} duplicates...")
                        continue  # ← PENTING: Skip row ini, jangan insert!
                    else:
                        # Update existing
                        for key, value in tariff_data.items():
                            if key != 'kode_cbg':  # Don't update primary key
                                setattr(existing, key, value)
                        stats['updated'] += 1
                        if stats['updated'] % 1000 == 0:
                            print(f"  ♻️ Updated {stats['updated']:,} rows...")
                        continue  # ← PENTING: Jangan insert lagi setelah update!
                
                # Add to batch for bulk insert (hanya kalau belum ada di DB)
                batch_data.append(tariff_data)
                stats['inserted'] += 1
                
                # Bulk insert ketika batch penuh
                if len(batch_data) >= batch_size:
                    db.bulk_insert_mappings(INACBGTariff, batch_data)
                    db.commit()
                    print(f"  ➕ Inserted {stats['inserted']:,} rows...")
                    batch_data = []
                
                # Progress indicator setiap 5000 rows
                if (idx + 1) % 5000 == 0:
                    elapsed = time.time() - start_time
                    rate = (idx + 1) / elapsed if elapsed > 0 else 0
                    remaining = (len(df) - idx - 1) / rate if rate > 0 else 0
                    print(f"  � Progress: {idx + 1:,}/{len(df):,} ({(idx+1)/len(df)*100:.1f}%) | ETA: {int(remaining)}s")
                
            except IntegrityError as e:
                db.rollback()
                stats['errors'] += 1
                error_msg = f"Row {idx}: Duplicate kode_cbg={kode_cbg}"
                stats['error_details'].append(error_msg)
                if stats['errors'] <= 10:  # Show first 10 errors only
                    print(f"  ⚠️ {error_msg}")
                continue
            except Exception as e:
                db.rollback()
                stats['errors'] += 1
                error_msg = f"Row {idx}: {str(e)}"
                stats['error_details'].append(error_msg)
                if stats['errors'] <= 10:
                    print(f"  ❌ {error_msg}")
                continue
        
        # Insert remaining batch data
        if batch_data:
            db.bulk_insert_mappings(INACBGTariff, batch_data)
            print(f"  ➕ Inserted remaining {len(batch_data)} rows...")
        
        # Final commit
        db.commit()
        db.close()
        
        # Calculate execution time
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"📊 IMPORT SUMMARY")
        print(f"{'='*60}")
        print(f"Total rows in Excel:  {stats['total_rows']:,}")
        print(f"✅ Inserted:          {stats['inserted']:,}")
        print(f"♻️  Updated:           {stats['updated']:,}")
        print(f"⏭️  Skipped:           {stats['skipped']:,}")
        print(f"❌ Errors:            {stats['errors']:,}")
        print(f"⏱️  Time:              {execution_time:.2f} seconds")
        print(f"⚡ Speed:             ~{int(stats['inserted'] / execution_time if execution_time > 0 else 0)} rows/sec")
        print(f"{'='*60}")
        
        if stats['errors'] > 0:
            print(f"\n⚠️ {stats['errors']} errors occurred. First 10 shown above.")
        
        if stats['inserted'] > 0 or stats['updated'] > 0:
            print(f"\n✅ SUCCESS! Database updated.")
            print(f"\n📝 Next steps:")
            print(f"  1. Verify data: SELECT * FROM inacbg_tariff LIMIT 10;")
            print(f"  2. Test query: SELECT * FROM inacbg_tariff WHERE kode_cbg = 'I-4-10-I';")
            print(f"  3. Integrate with analyze services")
        
        return stats
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Default path ke Excel
    default_path = "data/ina_cbg_tarif.xlsx"
    
    # Ambil path dari argument atau pakai default
    excel_path = sys.argv[1] if len(sys.argv) > 1 else default_path
    
    # Cek apakah file ada
    if not os.path.exists(excel_path):
        print(f"❌ File tidak ditemukan: {excel_path}")
        print(f"\n💡 Cara pakai:")
        print(f"  python tools/import_inacbg_tariff.py path/to/excel.xlsx")
        print(f"\nAtau copy file Excel Anda ke: {default_path}")
        sys.exit(1)
    
    # Tanya mode: skip atau update duplicates
    print(f"\n📋 Import mode:")
    print(f"  1. Skip duplicates (default) - lebih cepat")
    print(f"  2. Update duplicates - lebih lama tapi data ter-update")
    
    try:
        mode = input(f"\nPilih mode (1/2) [1]: ").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        # Auto-select mode 1 if running non-interactive
        mode = "1"
        print("1")  # Echo the selection
    
    skip_duplicates = mode == "1"
    
    # Import
    result = import_from_excel(excel_path, skip_duplicates=skip_duplicates)
    
    if result:
        print(f"\n✅ DONE!")
    else:
        print(f"\n❌ FAILED!")
        sys.exit(1)
