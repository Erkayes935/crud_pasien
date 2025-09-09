FROM python:3.11-slim

# Set working directory ke dalam container
WORKDIR /app/web

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements dan install dependencies
COPY web/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kode web (hanya folder web)
COPY web .

# Tambahkan PYTHONPATH agar bisa import dengan benar
ENV PYTHONPATH="/app"

# Expose port service web
EXPOSE 8001

# Jalankan aplikasi FastAPI (tanpa --reload di production)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
