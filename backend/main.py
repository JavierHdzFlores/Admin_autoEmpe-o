from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List # ¡IMPORTANTE! Para las listas
import pydantic
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

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

# --- CONFIGURACIÓN PARA SERVIR FRONTEND (PRODUCCIÓN) ---

# 1. Montar la carpeta "frontend" para que CSS y JS funcionen
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# 2. Ruta para la página de inicio (Login)
@app.get("/")
async def read_index():
    return FileResponse('frontend/login.html')

# 3. Truco para que al abrir "dash.html" funcione sin poner /frontend/
@app.get("/{filename}")
async def read_html(filename: str):
    file_path = f"frontend/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "Archivo no encontrado"}

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
def obtener_tabla_dashboard(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    # Llamamos a la nueva función que mezcla todo
    datos = crud.get_actividad_reciente(db, limite=30)
    return datos

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

    # B. Validación de negocio: No permitir refrendo si el empeño está en 'Vigente'
    # (UX/Seguridad: el frontend ya deshabilita la opción, pero reforzamos en backend)
    if hasattr(models, 'EstadoEmpeno') and empeno.estado == models.EstadoEmpeno.vigente:
        raise HTTPException(status_code=400, detail="No se puede registrar refrendo para un empeño en estado Vigente")


    # C. Calculamos monto (Por ahora fijo o calculado simple)
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

# --- Agrega esto al final de main.py ---

@app.post("/empenos/{id}/reevaluo")
def registrar_reevaluo(
    id: int, 
    datos: schemas.ReevaluoRequest, 
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
):
    """
    Ruta para procesar el Reevalúo.
    """
    # Llamamos a la función del CRUD
    resultado = crud.procesar_reevaluo(
        db, 
        empeno_id=id, 
        nuevo_prestamo=datos.nuevo_prestamo, 
        nuevo_valuo=datos.nuevo_valuo, 
        nuevo_interes=datos.nuevo_interes
    )
    
    if not resultado:
        raise HTTPException(status_code=404, detail="No se pudo procesar el reevalúo (¿Empeño no existe?)")
    
    return {"mensaje": "Reevalúo exitoso", "nuevo_monto": resultado.monto_prestamo}


# --- RUTA PARA DESEMPEÑO (LIQUIDACIÓN) ---
@app.post("/empenos/{id}/desempeno")
def registrar_desempeno(id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    """
    Endpoint para registrar que el cliente pagó todo y se llevó la prenda.
    """
    resultado = crud.procesar_desempeno(db, empeno_id=id)
    
    if not resultado:
        raise HTTPException(status_code=404, detail="Empeño no encontrado")
    
    return {"mensaje": "Prenda liberada exitosamente", "estado": resultado.estado}

class VentaRequest(pydantic.BaseModel):
    precio_venta: float

@app.post("/empenos/{id}/venta")
def registrar_venta(id: int, datos: VentaRequest, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    resultado = crud.procesar_venta_remate(db, id, datos.precio_venta)
    if not resultado:
        raise HTTPException(status_code=400, detail="El artículo no está disponible para venta")
    return {"mensaje": "Artículo vendido", "estado": resultado.estado}

# --- RUTA PARA ENVIAR A REMATE (Faltaba esta) ---
@app.post("/empenos/{id}/rematar")
def rematar_empeno(id: int, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    resultado = crud.mover_a_remate(db, id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Empeño no encontrado")
    return {"mensaje": "Artículo enviado a remate", "estado": resultado.estado}


@app.get("/empenos/remates")
def obtener_remates(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    """Devuelve los empeños que están en remate o vendidos, con el precio de venta si existe."""
    return crud.get_empenos_remates_con_precio(db)


# Endpoint temporal para depuración: listar movimientos de caja recientes
@app.get("/movimientos/recientes")
def obtener_movimientos_recientes(limit: int = 20, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    """Devuelve los últimos movimientos de caja con información del empeño y cliente (si existe).
    Útil para depurar por qué el dashboard no muestra Refrendos/Desempeños/Ventas/Nuevo empeño .
    """
    movimientos = db.query(models.MovimientoCaja).order_by(models.MovimientoCaja.fecha_movimiento.desc()).limit(limit).all()
    resultado = []
    for m in movimientos:
        empeno = db.query(models.Empeno).filter(models.Empeno.id == m.empeno_id).first()
        cliente_nombre = 'Desconocido'
        articulo = 'N/A'
        if empeno and empeno.cliente:
            cliente_nombre = f"{empeno.cliente.nombre} {empeno.cliente.apellidos}"
            articulo = empeno.marca_modelo or articulo

        resultado.append({
            'tipo': m.tipo_movimiento.value if hasattr(m.tipo_movimiento, 'value') else str(m.tipo_movimiento),
            'accion': m.tipo_movimiento.value if hasattr(m.tipo_movimiento, 'value') else str(m.tipo_movimiento),
            'cliente': cliente_nombre,
            'articulo': articulo,
            'monto': float(m.monto),
            'fecha_obj': m.fecha_movimiento.date(),
            'fecha': str(m.fecha_movimiento.date())
        })

    return resultado

# --- RUTA PARA EDITAR CLIENTE Y EMPEÑO ---
@app.put("/empenos/{id}/editar")
def editar_empeno(
    id: int, 
    datos: schemas.EdicionCompletaRequest, 
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
):
    resultado = crud.editar_empeno_completo(db, empeno_id=id, datos=datos)
    if not resultado:
        raise HTTPException(status_code=404, detail="Empeño no encontrado")
    return {"mensaje": "Datos actualizados correctamente", "data": resultado}

# --- RUTA PARA REGISTRAR EMPLEADO (CON SEGURIDAD) ---
@app.post("/registrar-empleado-seguro")
def registrar_empleado_seguro(
    datos: schemas.RegistroEmpleadoRequest, 
    db: Session = Depends(get_db)
):
    # 1. Buscar al "Jefe" (Usuario admin) para verificar su firma
    # Asumimos que el usuario principal se llama 'admin'
    admin_user = crud.get_user_by_username(db, "admin")
    
    if not admin_user:
        raise HTTPException(
            status_code=400, 
            detail="Error crítico: No existe el usuario 'admin' para autorizar."
        )

    # 2. Verificar si la contraseña maestra es correcta
    # Usamos la función de security que ya tienes importada
    if not security.verify_password(datos.admin_password, admin_user.hashed_password):
        raise HTTPException(
            status_code=401, 
            detail="⛔ Autorización denegada: Contraseña de Admin incorrecta."
        )

    # 3. Verificar que el nuevo usuario no exista ya
    if crud.get_user_by_username(db, datos.nuevo_usuario.usuario):
        raise HTTPException(
            status_code=400, 
            detail="El nombre de usuario ya está ocupado."
        )

    # 4. Si todo está bien, creamos al empleado
    nuevo_empleado = crud.create_user(db, datos.nuevo_usuario)
    
    return {
        "mensaje": f"Empleado '{nuevo_empleado.usuario}' registrado exitosamente.",
        "id": nuevo_empleado.id
    }