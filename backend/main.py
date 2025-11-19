from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List # ¡IMPORTANTE! Para las listas

# Imports sin puntos para Docker
from database import engine, get_db
import models, schemas, crud, security

# Crear tablas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auto Empeño Luna API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- RUTAS ---

@app.get("/")
def read_root():
    return {"mensaje": "API Operativa 🚀"}

# LOGIN
@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.usuario}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# REGISTRO DE USUARIO ADMIN
@app.post("/registrar-usuario", response_model=schemas.Usuario)
def registrar_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=usuario.usuario)
    if db_user:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    return crud.create_user(db=db, user=usuario)

# --- RUTAS DEL SISTEMA DE EMPEÑOS ---

# 1. Registrar Nuevo Empeño (Cliente + Artículo)
@app.post("/empenos/nuevo", response_model=schemas.Empeno)
def registrar_nuevo_empeno(
    solicitud: schemas.NuevoEmpenoRequest, 
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    try:
        return crud.procesar_nuevo_empeno(db, solicitud)
    except Exception as e:
        print(f"ERROR EN BACKEND: {e}") # Esto saldrá en los logs de Docker
        raise HTTPException(status_code=500, detail=str(e))

# 2. Ver todos los empeños (Para clientes.html)
@app.get("/empenos/todos", response_model=List[schemas.Empeno])
def leer_todos_los_empenos(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    return crud.get_todos_los_empenos(db)

# 3. Dashboard Stats
@app.get("/dashboard/resumen")
def obtener_resumen(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    return crud.get_dashboard_stats(db)

# 4. Dashboard Tabla
@app.get("/dashboard/tabla")
def obtener_tabla_reciente(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    return crud.get_empenos_recientes_tabla(db)