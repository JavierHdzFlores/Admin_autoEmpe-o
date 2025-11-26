from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

# ==========================================
# 1. ENUMS
# ==========================================
class RolUsuario(str, Enum):
    admin = "admin"
    empleado = "empleado"

class EstadoEmpeno(str, Enum):
    vigente = "Vigente"
    vencido = "Vencido"
    desempenado = "Desempeñado"
    rematado = "Rematado"
    vendido = "Vendido"
    perdido = "Perdido"

class TipoMovimiento(str, Enum):
    refrendo = "Refrendo"
    desempeno = "Desempeño"
    abono = "Abono Capital"
    venta = "Venta Remate"
    reevaluo = "Reevaluo"

# ==========================================
# 2. MOVIMIENTOS DE CAJA (Independientes)
# ==========================================
class MovimientoCajaBase(BaseModel):
    tipo_movimiento: TipoMovimiento
    monto: Decimal = Field(..., max_digits=10, decimal_places=2)
    nota: Optional[str] = None

class MovimientoCajaCreate(MovimientoCajaBase):
    empeno_id: int

class MovimientoCaja(MovimientoCajaBase):
    id: int
    usuario_id: int
    fecha_movimiento: datetime
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# 3. CLIENTE BASE (El Padre de todos)
# ==========================================
# ¡IMPORTANTE! Este va PRIMERO para que los demás puedan usarlo
class ClienteBase(BaseModel):
    nombre: str
    apellidos: str
    telefono: Optional[str] = Field(None, max_length=20)
    ine: Optional[str] = Field(None, max_length=20)
    direccion: Optional[str] = None

class ClienteCreate(ClienteBase):
    pass

# ==========================================
# 4. CLIENTE SIMPLE (Hijo de ClienteBase)
# ==========================================
# Versión ligera sin lista de empeños (para romper bucles)
class ClienteSimple(ClienteBase):
    id: int
    fecha_registro: datetime
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# 5. EMPEÑOS (Usan ClienteSimple)
# ==========================================
class EmpenoBase(BaseModel):
    categoria: str
    marca_modelo: str
    descripcion: Optional[str] = None
    num_serie_peso: Optional[str] = None
    observaciones: Optional[str] = None
    
    valor_valuo: Decimal = Field(..., gt=0) 
    monto_prestamo: Decimal = Field(..., gt=0)
    interes_mensual_pct: Optional[Decimal] = Decimal("10.0")
    
    fecha_empeno: date
    fecha_vencimiento: date

class EmpenoCreate(EmpenoBase):
    pass 

class EmpenoUpdate(BaseModel):
    estado: Optional[EstadoEmpeno] = None
    fecha_vencimiento: Optional[date] = None

class Empeno(EmpenoBase):
    id: int
    cliente_id: int
    estado: EstadoEmpeno
    
    # Aquí usamos al ClienteSimple (que ya fue definido arriba)
    cliente: Optional[ClienteSimple] = None 
    
    monto_refrendo: Optional[Decimal] = None 
    total_desempeno: Optional[Decimal] = None 
    movimientos: List[MovimientoCaja] = []

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# 6. CLIENTE COMPLETO (Usa Empeno)
# ==========================================
# Este va al final porque necesita que 'Empeno' ya exista
class Cliente(ClienteSimple):
    empenos: List[Empeno] = [] 
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# 7. OTROS ESQUEMAS (Requests y Usuarios)
# ==========================================
class NuevoEmpenoRequest(BaseModel):
    cliente: ClienteCreate
    empeno: EmpenoCreate

class UsuarioBase(BaseModel):
    usuario: str
    nombre_completo: str
    rol: Optional[RolUsuario] = RolUsuario.empleado

class UsuarioCreate(UsuarioBase):
    password: str

class Usuario(UsuarioBase):
    id: int
    activo: bool
    fecha_creacion: datetime
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ReevaluoRequest(BaseModel):
    nuevo_prestamo: float
    nuevo_valuo: float
    nuevo_interes: float
    
class VentaRequest(BaseModel):
    precio_venta: float

# --- SCHEMA PARA EDICIÓN COMPLETA ---
class EdicionCompletaRequest(BaseModel):
    # Datos Cliente
    nombre: str
    apellidos: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    
    # Datos Empeño
    categoria: str
    marca_modelo: str
    estado: EstadoEmpeno
    fecha_empeno: date
    fecha_vencimiento: date