FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

# --- CAMBIO AQUÍ ---
# 1. Actualizamos pip (ayuda a evitar errores de instalación)
RUN pip install --upgrade pip

# 2. Aumentamos el 'timeout' a 1000 segundos para que no se corte si tu internet va lento
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt
# -------------------

COPY . .

ENV PYTHONPATH="${PYTHONPATH}:/app/backend"

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]