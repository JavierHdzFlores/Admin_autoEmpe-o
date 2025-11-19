from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# CORRECCIÓN: Quitamos el punto (.) para usar importación absoluta
from database import engine 
import models 

# --- 1. CREACIÓN DE TABLAS AUTOMÁTICA ---
models.Base.metadata.create_all(bind=engine)

# --- 2. INICIALIZAR APP ---
app = FastAPI(
    title="Auto Empeño Luna API",
    description="Backend para gestión de empeños, clientes y caja.",
    version="1.0.0"
)

# --- 3. CONFIGURACIÓN DE CORS ---
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 4. RUTAS (Endpoints) ---

@app.get("/")
def read_root():
    return {"mensaje": "¡Bienvenido al sistema Auto Empeño Luna! API Activa."}

# (Aquí abajo iremos pegando las rutas de login y demás en el futuro)