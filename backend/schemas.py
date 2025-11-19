from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal # IMPORTANTE para dinero exacto
from enum import Enum

# --- ENUMS (Iguales a models.py) ---
class RolUsuario(str, Enum):
    admin = "admin"
    empleado = "empleado"

class EstadoEmpeno(str, Enum):
    vigente = "Vigente"
    vencido = "Vencido"
    desempenado = "Desempeñado"
    rematado = "Rematado"
    perdido = "Perdido"

class TipoMovimiento(str, Enum):
    refrendo = "Refrendo"
    desempeno = "Desempeño"
    abono = "Abono Capital"
    venta = "Venta Remate"

# --- ESQUEMAS DE MOVIMIENTOS DE CAJA ---
class MovimientoCajaBase(BaseModel):
    tipo_movimiento: TipoMovimiento
    monto: Decimal = Field(..., max_digits=10, decimal_places=2) # Validación extra
    nota: Optional[str] = None

class MovimientoCajaCreate(MovimientoCajaBase):
    empeno_id: int
    # El usuario_id viene del token, no del JSON

class MovimientoCaja(MovimientoCajaBase):
    id: int
    usuario_id: int
    fecha_movimiento: datetime

    # Configuración Pydantic V2
    model_config = ConfigDict(from_attributes=True)


# --- ESQUEMAS DE EMPEÑOS ---
class EmpenoBase(BaseModel):
    categoria: str
    marca_modelo: str
    descripcion: Optional[str] = None
    num_serie_peso: Optional[str] = None
    observaciones: Optional[str] = None
    
    # Usamos Decimal en lugar de float para evitar errores de redondeo
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
    
    # Estos campos se calculan en el backend antes de responder
    monto_refrendo: Optional[Decimal] = None 
    total_desempeno: Optional[Decimal] = None 
    
    movimientos: List[MovimientoCaja] = []

    model_config = ConfigDict(from_attributes=True)


# --- ESQUEMAS DE CLIENTES ---
class ClienteBase(BaseModel):
    nombre: str
    apellidos: str
    # Validaciones útiles: max_length asegura que quepa en la BD
    telefono: Optional[str] = Field(None, max_length=20)
    ine: Optional[str] = Field(None, max_length=20)
    direccion: Optional[str] = None

class ClienteCreate(ClienteBase):
    pass

class Cliente(ClienteBase):
    id: int
    fecha_registro: datetime
    # Devuelve la lista de empeños de este cliente
    empenos: List[Empeno] = [] 

    model_config = ConfigDict(from_attributes=True)


# --- ESQUEMAS PARA CREACIÓN COMPUESTA ---
class NuevoEmpenoRequest(BaseModel):
    cliente: ClienteCreate
    empeno: EmpenoCreate


# --- ESQUEMAS DE USUARIOS / LOGIN ---
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