import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base # Actualizado para versiones nuevas de SQLAlchemy
from sqlalchemy.orm import sessionmaker

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---

# Leemos las variables de entorno (útil para Docker). 
# Si no existen, usa los valores predeterminados (útil para pruebas locales).
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "tu_contrasena") # ¡Ojo con esto en prod!
DB_HOST = os.getenv("DB_HOST", "localhost") # En Docker esto cambiará a 'db'
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "auto_empeno_db")

# Construimos la URL dinámicamente
# NOTA: Te cambié 'mysqlclient' por 'pymysql'. 
# ¿Por qué? pymysql es 100% Python y da MENOS problemas al crear el contenedor Docker 
# (no pide instalar compiladores de C++ en Linux).
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# create_engine: El motor que maneja la conexión
# pool_recycle=3600: Evita desconexiones por inactividad
# pool_pre_ping=True: Vital para Docker, reconecta si la BD se reinicia
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_recycle=3600,
    pool_pre_ping=True
)

# SessionLocal: Fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base: Para los modelos
Base = declarative_base()

# Función de utilidad para obtener la BD (Dependency Injection)
# Esto se usa mucho en main.py
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()