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

# En backend/crud.py
def buscar_clientes_general(db: Session, query_str: str):
    """Busca por nombre, apellido, INE o TELÉFONO"""
    busqueda = f"%{query_str}%" 
    return db.query(models.Cliente).filter(
        or_(
            models.Cliente.nombre.ilike(busqueda),
            models.Cliente.apellidos.ilike(busqueda),
            models.Cliente.ine.ilike(busqueda),
            models.Cliente.telefono.ilike(busqueda) # ¡Nuevo!
        )
    ).all()
# ==========================================
# OPERACIONES DE REFRENDO Y CAJA (Faltantes)
# ==========================================

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

def create_movimiento(db: Session, movimiento: schemas.MovimientoCajaCreate, usuario_id: int):
    """
    Registra cualquier entrada de dinero (Refrendo, Desempeño, etc).
    """
    db_movimiento = models.MovimientoCaja(
        **movimiento.model_dump(),
        usuario_id=usuario_id # Viene del token del usuario logueado
    )
    db.add(db_movimiento)
    db.commit()
    db.refresh(db_movimiento)
    return db_movimiento


# --- REEVALÚO (Aumentar Préstamo) ---
def procesar_reevaluo(db: Session, empeno_id: int, nuevo_prestamo: float, nuevo_valuo: float, nuevo_interes: float):
    empeno = get_empeno(db, empeno_id)
    if not empeno:
        return None

    # 1. Calcular la diferencia (Dinero que sale de caja hacia el cliente)
    diferencia_a_entregar = nuevo_prestamo - float(empeno.monto_prestamo)
    
    # 2. Actualizar datos del empeño
    empeno.monto_prestamo = nuevo_prestamo
    empeno.valor_valuo = nuevo_valuo
    empeno.interes_mensual_pct = nuevo_interes
    
    # Al reevaluar, se renueva la fecha de vencimiento a 30 días desde hoy
    empeno.fecha_vencimiento = date.today() + timedelta(days=30)
    empeno.estado = models.EstadoEmpeno.vigente # Se reactiva

    # 3. Registrar Movimiento de Caja (Solo si hubo entrega de dinero)
    if diferencia_a_entregar > 0:
        movimiento = models.MovimientoCaja(
            empeno_id=empeno.id,
            usuario_id=1, # Asignado al admin por ahora
            tipo_movimiento=models.TipoMovimiento.reevaluo,
            monto=diferencia_a_entregar * -1, # Es negativo porque SALE dinero de tu caja
            nota=f"Reevaluo: Aumento de préstamo"
        )
        db.add(movimiento)

    db.commit()
    db.refresh(empeno)
    return empeno

# --- DESEMPEÑO (Liquidar y retirar prenda) ---
def procesar_desempeno(db: Session, empeno_id: int):
    empeno = get_empeno(db, empeno_id)
    if not empeno:
        return None
    
    # 1. Calcular el total a cobrar (Capital + Interés del mes)
    # Para hacerlo simple, cobramos lo que tenga calculado en el frontend o recalcula aquí
    interes = empeno.monto_prestamo * (empeno.interes_mensual_pct / 100)
    total_cobrar = empeno.monto_prestamo + interes

    # 2. Registrar entrada de dinero en Caja
    movimiento = models.MovimientoCaja(
        empeno_id=empeno.id,
        usuario_id=1, # Usuario Admin por defecto
        tipo_movimiento=models.TipoMovimiento.desempeno,
        monto=total_cobrar, # Positivo porque ENTRA dinero
        nota="Liquidación Total (Desempeño)"
    )
    db.add(movimiento)

    # 3. Liberar el empeño (Cambiar estado)
    empeno.estado = models.EstadoEmpeno.desempenado
    # Opcional: Podrías poner la fecha de vencimiento en None o dejarla como registro histórico
    
    db.commit()
    db.refresh(empeno)
    return empeno

# --- VENTA DE ARTÍCULO REMATADO ---
def procesar_venta_remate(db: Session, empeno_id: int, precio_venta: float):
    empeno = get_empeno(db, empeno_id)
    if not empeno or empeno.estado != models.EstadoEmpeno.rematado:
        return None # Solo se puede vender lo que está rematado

    # 1. Registrar entrada de dinero
    movimiento = models.MovimientoCaja(
        empeno_id=empeno.id,
        usuario_id=1,
        tipo_movimiento=models.TipoMovimiento.venta,
        monto=precio_venta,
        nota=f"Venta de artículo de remate"
    )
    db.add(movimiento)

    # 2. Cambiar estado a Vendido
    empeno.estado = models.EstadoEmpeno.vendido
    
    db.commit()
    db.refresh(empeno)
    return empeno

# --- MOVER A REMATE (Función Faltante) ---
def mover_a_remate(db: Session, empeno_id: int):
    """
    Cambia el estado del empeño a 'Rematado' para que aparezca en la tabla de ventas.
    """
    empeno = get_empeno(db, empeno_id)
    if empeno:
        empeno.estado = models.EstadoEmpeno.rematado
        db.commit()
        db.refresh(empeno)
    return empeno