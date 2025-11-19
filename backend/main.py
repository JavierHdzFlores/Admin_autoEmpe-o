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

# En backend/main.py
# --- RUTA DE BÚSQUEDA DE CLIENTES ---
@app.get("/clientes/buscar", response_model=List[schemas.Cliente])
def buscar_clientes(q: str, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    return crud.buscar_clientes_general(db, q)

# --- RUTA PARA REGISTRAR REFRENDO (PAGO) ---
@app.post("/empenos/{id}/refrendo")
def registrar_refrendo(id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    """
    1. Cobra el refrendo.
    2. Extiende la fecha de vencimiento 30 días.
    3. Reactiva el empeño a 'Vigente'.
    """
    # A. Buscamos el empeño
    empeno = crud.get_empeno(db, empeno_id=id)
    if not empeno:
        raise HTTPException(status_code=404, detail="Empeño no encontrado")


    # B. Calculamos monto (Por ahora fijo o calculado simple)
    # En un sistema real, recibiríamos el monto exacto del frontend.
    monto_cobrado = empeno.monto_prestamo * empeno.interes_mensual_pct / 100
    
    # C. Registramos el movimiento de dinero
    movimiento = schemas.MovimientoCajaCreate(
        tipo_movimiento=schemas.TipoMovimiento.refrendo,
        monto=monto_cobrado,
        empeno_id=id,
        nota="Pago de Refrendo Mensual"
    )
    # Usamos un usuario ID fijo por ahora (o decodifica el token si quieres ser estricto)
    # Para simplificar, asumiremos que el usuario ID 1 es el cajero.
    crud.create_movimiento(db, movimiento, usuario_id=1)

    # D. Extendemos la fecha y actualizamos estado
    empeno_actualizado = crud.refrendar_empeno(db, empeno_id=id)
    
    return {"mensaje": "Refrendo aplicado exitosamente", "nueva_fecha": empeno_actualizado.fecha_vencimiento}