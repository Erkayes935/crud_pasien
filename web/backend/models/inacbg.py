"""
INA-CBG Tariff Model
Tabel master tarif INA-CBG dari Permenkes

PENTING: kode_cbg BUKAN unique key!
Satu kode CBG bisa punya banyak tarif berbeda tergantung:
- regional (1-5)
- tipe_rs (RS Umum, RS Khusus, FKTP, dll)  
- kelas_rs (A, B, C, D)
"""

from sqlalchemy import Column, Integer, String, BigInteger, Text, DateTime, Index
from sqlalchemy.sql import func
from .base import Base

class INACBGTariff(Base):
    """
    Master tarif INA-CBG
    Data diimport dari Excel resmi BPJS/Kemenkes
    
    ⚠️ PERHATIAN: kode_cbg bisa duplikat dengan tarif berbeda!
    Contoh: I-4-10-I bisa punya 20+ row dengan tarif beda per regional/tipe RS
    """
    __tablename__ = "inacbg_tariff"

    id = Column(Integer, primary_key=True, index=True)
    kode_cbg = Column(String(50), nullable=False, index=True)  # Tidak unique!
    deskripsi = Column(Text, nullable=True)
    
    # Tarif per kelas perawatan
    tarif_kelas_1 = Column(BigInteger, nullable=True)  # Kelas 1 / VIP
    tarif_kelas_2 = Column(BigInteger, nullable=True)  # Kelas 2
    tarif_kelas_3 = Column(BigInteger, nullable=True)  # Kelas 3
    tarif = Column(BigInteger, nullable=True)          # Tarif default/rata-rata
    
    # Metadata
    regional = Column(String(10), nullable=True)       # Regional (1-5)
    kelas_rs = Column(String(10), nullable=True)       # Kelas RS (A/B/C/D)
    tipe_rs = Column(String(50), nullable=True)        # Swasta/Pemerintah
    layanan = Column(String(50), nullable=True)        # Inap/Jalan
    no = Column(Integer, nullable=True)                # Nomor urut di Excel
    page_number_pdf = Column(Integer, nullable=True)   # Halaman di PDF sumber
    
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Composite index untuk query cepat
    __table_args__ = (
        Index('idx_cbg_composite_lookup', 'kode_cbg', 'regional', 'tipe_rs', 'kelas_rs', 'layanan'),
    )

    def __repr__(self):
        return f"<INACBGTariff({self.kode_cbg} | {self.regional}-{self.tipe_rs}-{self.kelas_rs})>"
    
    def get_tarif_by_kelas(self, kelas: str) -> int:
        """
        Get tarif sesuai kelas perawatan
        
        Args:
            kelas: "1", "2", "3", "VIP", etc
        
        Returns:
            Tarif dalam Rupiah
        """
        kelas_map = {
            "1": self.tarif_kelas_1,
            "2": self.tarif_kelas_2,
            "3": self.tarif_kelas_3,
            "VIP": self.tarif_kelas_1,
            "VVIP": self.tarif_kelas_1,
        }
        return kelas_map.get(str(kelas), self.tarif_kelas_3 or 0)
