from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import timedelta # CORRECCIÓN 2: Quitamos 'date' porque no se usa
import models, schemas, security # CORRECCIÓN 1: Quitamos el punto (.) inicial

# ==========================================
# USUARIOS (Login y Gestión)
# ==========================================

def get_user(db: Session, user_id: int):
    return db.query(models.Usuario).filter(models.Usuario.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.Usuario).filter(models.Usuario.usuario == username).first()

def create_user(db: Session, user: schemas.UsuarioCreate):
    """Crea un nuevo usuario (empleado/admin) en la BD con hash."""
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

def get_cliente(db: Session, cliente_id: int):
    return db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()

# NUEVA FUNCIÓN: Búsqueda general para tu barra de búsqueda
def buscar_clientes_general(db: Session, query_str: str):
    """Busca por nombre, apellido o INE que contenga el texto query_str"""
    busqueda = f"%{query_str}%" # Comodines para búsqueda parcial
    return db.query(models.Cliente).filter(
        or_(
            models.Cliente.nombre.ilike(busqueda),
            models.Cliente.apellidos.ilike(busqueda),
            models.Cliente.ine.ilike(busqueda)
        )
    ).all()

def get_cliente_by_ine(db: Session, ine: str):
    return db.query(models.Cliente).filter(models.Cliente.ine == ine).first()

def create_cliente(db: Session, cliente: schemas.ClienteCreate):
    # CORRECCIÓN 2: Usamos model_dump() en lugar de dict() para Pydantic v2
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

def get_empenos_por_cliente(db: Session, cliente_id: int):
    """Recupera todo el historial de un cliente"""
    return db.query(models.Empeno).filter(models.Empeno.cliente_id == cliente_id).all()

def create_empeno(db: Session, empeno: schemas.EmpenoCreate, cliente_id: int):
    """Registra un nuevo artículo empeñado."""
    db_empeno = models.Empeno(
        **empeno.model_dump(), 
        cliente_id=cliente_id,
        estado=models.EstadoEmpeno.vigente # Siempre nace vigente
    )
    db.add(db_empeno)
    db.commit()
    db.refresh(db_empeno)
    return db_empeno

def update_empeno_estado(db: Session, empeno_id: int, nuevo_estado: models.EstadoEmpeno):
    """Actualiza solo el estado (ej. al Desempeñar o Rematar)."""
    db_empeno = get_empeno(db, empeno_id)
    if db_empeno:
        db_empeno.estado = nuevo_estado
        db.commit()
        db.refresh(db_empeno)
    return db_empeno

def refrendar_empeno(db: Session, empeno_id: int, dias_extension: int = 30):
    """
    1. Extiende la fecha de vencimiento.
    2. Si estaba vencido, lo regresa a 'Vigente'.
    """
    db_empeno = get_empeno(db, empeno_id)
    if db_empeno:
        # Lógica: Sumar días a la fecha que tenía
        db_empeno.fecha_vencimiento = db_empeno.fecha_vencimiento + timedelta(days=dias_extension)
        
        # IMPORTANTE: Si pagan refrendo, el empeño revive a estado Vigente
        db_empeno.estado = models.EstadoEmpeno.vigente
        
        db.commit()
        db.refresh(db_empeno)
    return db_empeno


# ==========================================
# MOVIMIENTOS DE CAJA (Pagos)
# ==========================================

def create_movimiento(db: Session, movimiento: schemas.MovimientoCajaCreate, usuario_id: int):
    """Registra entrada de dinero (Refrendo, Desempeño, etc)."""
    db_movimiento = models.MovimientoCaja(
        **movimiento.model_dump(),
        usuario_id=usuario_id 
    )
    db.add(db_movimiento)
    db.commit()
    db.refresh(db_movimiento)
    return db_movimiento