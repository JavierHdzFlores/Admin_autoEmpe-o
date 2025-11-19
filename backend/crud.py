from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import date, timedelta
# IMPORTANTE: Sin puntos para que Docker lo lea bien
import models, schemas, security 

# ==========================================
# USUARIOS
# ==========================================
def get_user(db: Session, user_id: int):
    return db.query(models.Usuario).filter(models.Usuario.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.Usuario).filter(models.Usuario.usuario == username).first()

def create_user(db: Session, user: schemas.UsuarioCreate):
    hashed_password = security.get_password_hash(user.password)
    db_user = models.Usuario(
        usuario=user.usuario,
        hashed_password=hashed_password,
        nombre_completo=user.nombre_completo,
        rol=user.rol
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# ==========================================
# CLIENTES
# ==========================================
def get_cliente_by_ine(db: Session, ine: str):
    # Limpiamos espacios en blanco por si acaso
    return db.query(models.Cliente).filter(models.Cliente.ine == ine.strip()).first()

def create_cliente(db: Session, cliente: schemas.ClienteCreate):
    # Usamos model_dump() porque estamos en Pydantic V2
    db_cliente = models.Cliente(**cliente.model_dump())
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente

# ==========================================
# EMPEÑOS
# ==========================================
def get_empeno(db: Session, empeno_id: int):
    return db.query(models.Empeno).filter(models.Empeno.id == empeno_id).first()

def create_empeno(db: Session, empeno: schemas.EmpenoCreate, cliente_id: int):
    db_empeno = models.Empeno(
        **empeno.model_dump(), 
        cliente_id=cliente_id,
        estado=models.EstadoEmpeno.vigente
    )
    db.add(db_empeno)
    db.commit()
    db.refresh(db_empeno)
    return db_empeno

def get_todos_los_empenos(db: Session):
    return db.query(models.Empeno).order_by(models.Empeno.fecha_empeno.desc()).all()

# ==========================================
# DASHBOARD Y ESTADÍSTICAS
# ==========================================
def get_dashboard_stats(db: Session):
    return {
        "total_empenos": db.query(models.Empeno).count(),
        "activos": db.query(models.Empeno).filter(models.Empeno.estado == models.EstadoEmpeno.vigente).count(),
        "clientes": db.query(models.Cliente).count(),
        "remate": db.query(models.Empeno).filter(models.Empeno.estado == models.EstadoEmpeno.rematado).count()
    }

def get_empenos_recientes_tabla(db: Session, limite: int = 5):
    empenos = db.query(models.Empeno).order_by(models.Empeno.id.desc()).limit(limite).all()
    resultado = []
    for e in empenos:
        # Unimos nombre con seguridad (por si apellidos viene vacío)
        nombre_completo = f"{e.cliente.nombre} {e.cliente.apellidos}" if e.cliente else "Cliente Desconocido"
        
        resultado.append({
            "cliente": nombre_completo,
            "accion": "Nuevo Empeño",
            "articulo": e.marca_modelo,
            "monto": e.monto_prestamo,
            "fecha": e.fecha_empeno
        })
    return resultado

# ==========================================
# LÓGICA MAESTRA: NUEVO EMPEÑO
# ==========================================
def procesar_nuevo_empeno(db: Session, datos: schemas.NuevoEmpenoRequest):
    # 1. Verificamos si el cliente existe por INE
    cliente_ine = datos.cliente.ine.strip()
    cliente_existente = get_cliente_by_ine(db, ine=cliente_ine)
    
    if cliente_existente:
        print(f"Cliente encontrado: {cliente_existente.nombre}")
        cliente_id = cliente_existente.id
    else:
        print("Creando cliente nuevo...")
        nuevo_cliente = create_cliente(db, datos.cliente)
        cliente_id = nuevo_cliente.id

    # 2. Creamos el empeño vinculado
    print(f"Registrando empeño para cliente ID: {cliente_id}")
    nuevo_empeno = create_empeno(db, datos.empeno, cliente_id=cliente_id)
    
    return nuevo_empeno