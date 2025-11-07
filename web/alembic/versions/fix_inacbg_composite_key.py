"""fix inacbg composite key - kode_cbg bisa duplikat

Revision ID: fix_inacbg_composite
Revises: create_inacbg_tariff
Create Date: 2025-11-07 11:30:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fix_inacbg_composite'
down_revision: Union[str, None] = 'create_inacbg_tariff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cek dan drop constraint unique pada kode_cbg jika ada (karena kode bisa sama tapi tarif beda per regional/tipe_rs/kelas)
    # Gunakan conditional drop untuk avoid error jika constraint tidak ada
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'inacbg_tariff_kode_cbg_key'
            ) THEN
                ALTER TABLE inacbg_tariff DROP CONSTRAINT inacbg_tariff_kode_cbg_key;
            END IF;
        END $$;
    """)
    
    # Drop index unique jika ada
    op.execute("""
        DROP INDEX IF EXISTS inacbg_tariff_kode_cbg_key;
    """)
    
    # Tambah composite index untuk query yang sering dipakai
    # Query: "cari tarif untuk kode X di regional Y, tipe RS Z, kelas K, layanan L"
    op.create_index(
        'idx_cbg_composite_lookup', 
        'inacbg_tariff', 
        ['kode_cbg', 'regional', 'tipe_rs', 'kelas_rs', 'layanan']
    )
    
    # Index untuk query pattern matching
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_cbg_pattern 
        ON inacbg_tariff (kode_cbg text_pattern_ops);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_cbg_pattern CASCADE;")
    op.drop_index('idx_cbg_composite_lookup', table_name='inacbg_tariff')
    
    # Re-create unique constraint (jika rollback)
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'inacbg_tariff_kode_cbg_key'
            ) THEN
                ALTER TABLE inacbg_tariff ADD CONSTRAINT inacbg_tariff_kode_cbg_key UNIQUE (kode_cbg);
            END IF;
        END $$;
    """)
