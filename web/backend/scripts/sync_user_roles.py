"""
Script sinkronisasi user lama -> multi-role system.
Tujuan: menyalin kolom `user.role` lama ke tabel `user_roles`.
"""

from backend.database import SessionLocal
from backend import models
from datetime import datetime


def sync_user_roles():
    db = SessionLocal()
    try:
        roles_map = {r.name: r for r in db.query(models.Role).all()}
        users = db.query(models.User).all()
        total_synced = 0

        for u in users:
            # Jika user punya kolom role lama tapi belum ada relasi multi-role
            if u.role and not u.roles:
                role_obj = roles_map.get(u.role)
                if role_obj:
                    print(f"🧩 Menambahkan relasi role '{u.role}' ke user {u.name}")
                    u.roles.append(role_obj)
                    total_synced += 1

        db.commit()
        print(f"✅ Sinkronisasi selesai: {total_synced} user diperbarui.")
    finally:
        db.close()


if __name__ == "__main__":
    sync_user_roles()
