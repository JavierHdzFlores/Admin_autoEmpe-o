from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

# Importamos nuestros módulos (sin puntos, gracias al PYTHONPATH de Docker)
from database import engine, get_db
import models, schemas, crud, security

# --- 1. CREACIÓN DE TABLAS ---
models.Base.metadata.create_all(bind=engine)

# --- 2. CONFIGURACIÓN APP ---
app = FastAPI(title="Auto Empeño Luna API", version="1.0.0")

# Configuración de CORS (Para que tu HTML pueda hablar con esto)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción cambia esto por tu dominio real
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. SEGURIDAD ---
# Esto le dice a Swagger que la URL para loguearse es "/token"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- 4. ENDPOINTS (RUTAS) ---

@app.get("/")
def read_root():
    return {"mensaje": "Sistema Auto Empeño Luna - API Operativa 🚀"}

# --- RUTA PARA CREAR EL PRIMER USUARIO (ADMIN) ---
# Úsala una vez para crear tu cuenta y luego puedes borrarla o protegerla
@app.post("/registrar-usuario", response_model=schemas.Usuario)
def registrar_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    # 1. Verificar si el usuario ya existe
    db_user = crud.get_user_by_username(db, username=usuario.usuario)
    if db_user:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    
    # 2. Crear nuevo usuario
    return crud.create_user(db=db, user=usuario)

# --- RUTA DE LOGIN (Obtener Token) ---
@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Buscar usuario en la BD
    user = crud.get_user_by_username(db, username=form_data.username)
    
    # 2. Validar usuario y contraseña
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Generar el Token de Acceso
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.usuario}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# --- RUTA DE PRUEBA PROTEGIDA ---
# Solo podrás entrar aquí si envías el token correcto
@app.get("/usuarios/me", response_model=schemas.Usuario)
def read_users_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Decodificamos el token para saber quién es
    # (Aquí simplificamos, en producción validamos más cosas)
    return crud.get_user_by_username(db, username=token) # Ojo: esto requiere lógica de decodificación en security.py