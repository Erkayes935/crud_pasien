# seed.py
from backend.database import SessionLocal
from backend import models
from sqlalchemy.exc import IntegrityError

def seed_roles_and_superadmin():
    db = SessionLocal()
    try:
        # Cek apakah superadmin sudah ada
        superadmin = db.query(models.User).filter(models.User.role == "superadmin").first()
        if superadmin:
            print("Superadmin sudah ada, skip seed superadmin.")
        else:
            # Create superadmin default
            superadmin = models.User(
                auth0_sub="superadmin-default-sub",
                email="superadmin@example.com",
                role="superadmin"
            )
            db.add(superadmin)
            db.commit()
            print(f"Superadmin dibuat: {superadmin.email}")

        # Cek roles unik dari User.role (enum-like)
        roles = ["superadmin", "admin_rs", "doctor", "coder", "verifikator"]
        for role in roles:
            exists = db.query(models.User).filter(models.User.role == role).first()
            if not exists:
                # buat dummy user untuk role itu (opsional)
                user = models.User(
                    auth0_sub=f"{role}-dummy-sub",
                    email=f"{role}@example.com",
                    role=role
                )
                db.add(user)
                print(f"User dummy untuk role {role} dibuat: {user.email}")
        db.commit()
        print("Seeder roles & superadmin selesai.")
    except IntegrityError as e:
        db.rollback()
        print(f"Seeder gagal: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_roles_and_superadmin()
