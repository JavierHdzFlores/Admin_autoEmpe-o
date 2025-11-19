from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import  jwt
from passlib.context import CryptContext

# --- CONFIGURACIÓN ---
# En producción, esto debería venir de tu archivo .env usando os.getenv()
SECRET_KEY = "clave_secreta_super_segura_para_tu_proyecto_luna"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Contexto para hashing de contraseñas (usa bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Verifica si una contraseña plana coincide con el hash guardado."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Genera un hash seguro a partir de una contraseña plana."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un Token JWT con tiempo de expiración."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    
    # Generamos el token codificado
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt