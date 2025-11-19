from sqlalchemy import Column, Integer, String, Text, DECIMAL, Date, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
import enum
from database import Base 

# ... (Tus Enums siguen igual) ...
class RolUsuario(str, enum.Enum):
    admin = "admin"
    empleado = "empleado"

class EstadoEmpeno(str, enum.Enum):
    vigente = "Vigente"
    vencido = "Vencido"
    desempenado = "Desempeñado"
    rematado = "Rematado"
    perdido = "Perdido"

class TipoMovimiento(str, enum.Enum):
    refrendo = "Refrendo"
    desempeno = "Desempeño"
    abono = "Abono Capital"
    venta = "Venta Remate"

# --- 1. Tabla Usuarios ---
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    nombre_completo = Column(String(100), nullable=False)
    rol = Column(Enum(RolUsuario), default=RolUsuario.empleado)
    activo = Column(Boolean, default=True)
    
    # CORRECCIÓN 2: pylint: disable=not-callable
    # Esto le dice al editor que ignore el falso error de func.now()
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now()) # pylint: disable=not-callable

    movimientos = relationship("MovimientoCaja", back_populates="usuario_registra")

    def __repr__(self):
        return f"<Usuario(id={self.id}, usuario='{self.usuario}', rol='{self.rol}')>"


# --- 2. Tabla Clientes ---
class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellidos = Column(String(100), nullable=False)
    telefono = Column(String(20), index=True)
    ine = Column(String(20), unique=True, index=True)
    direccion = Column(Text)
    
    # CORRECCIÓN 2: pylint: disable=not-callable
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now()) # pylint: disable=not-callable

    empenos = relationship("Empeno", back_populates="cliente")

    @hybrid_property
    def nombre_completo_cliente(self):
        return f"{self.nombre} {self.apellidos}"

    def __repr__(self):
        return f"<Cliente(id={self.id}, nombre='{self.nombre} {self.apellidos}')>"


# --- 3. Tabla Empeños ---
class Empeno(Base):
    __tablename__ = "empenos"

    id = Column(Integer, primary_key=True, index=True) 
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    categoria = Column(String(50))
    marca_modelo = Column(String(100))
    descripcion = Column(Text)
    num_serie_peso = Column(String(100))
    observaciones = Column(Text)
    valor_valuo = Column(DECIMAL(10, 2), nullable=False)
    monto_prestamo = Column(DECIMAL(10, 2), nullable=False)
    interes_mensual_pct = Column(DECIMAL(5, 2), default=10.00)
    fecha_empeno = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False) 
    estado = Column(Enum(EstadoEmpeno), default=EstadoEmpeno.vigente)

    cliente = relationship("Cliente", back_populates="empenos")
    movimientos = relationship("MovimientoCaja", back_populates="empeno")

    def __repr__(self):
        return f"<Empeno(id={self.id}, articulo='{self.marca_modelo}', estado='{self.estado}')>"


# --- 4. Tabla Movimientos Caja ---
class MovimientoCaja(Base):
    __tablename__ = "movimientos_caja"

    id = Column(Integer, primary_key=True, index=True)
    empeno_id = Column(Integer, ForeignKey("empenos.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo_movimiento = Column(Enum(TipoMovimiento), nullable=False)
    monto = Column(DECIMAL(10, 2), nullable=False)
    
    # CORRECCIÓN 2: pylint: disable=not-callable
    fecha_movimiento = Column(DateTime(timezone=True), server_default=func.now()) # pylint: disable=not-callable
    
    nota = Column(Text, nullable=True)

    empeno = relationship("Empeno", back_populates="movimientos")
    usuario_registra = relationship("Usuario", back_populates="movimientos")