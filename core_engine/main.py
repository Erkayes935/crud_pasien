
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware  # ⬅️ tambahkan ini
from endpoints import router as ai_router
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="AI Core Engine Dummy")

# ✅ Tambahkan GZipMiddleware di sini
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS agar bisa diakses dari frontend (port 8001)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # bisa diganti dengan ["http://localhost:8001"]
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# tambahkan prefix /ai biar sesuai dengan URL  
app.include_router(ai_router, prefix="")

