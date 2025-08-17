"""Simple DB health check script used during development.

Run: python -m backend.check_db
"""
from .database import engine

def check_connection():
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("DB OK", result.scalar())
            return True
    except Exception as e:
        print("DB connection failed:", e)
        return False

if __name__ == "__main__":
    ok = check_connection()
    raise SystemExit(0 if ok else 2)
