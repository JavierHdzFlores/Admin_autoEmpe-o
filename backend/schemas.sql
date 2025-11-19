-- 1. Crear la Base de Datos (si no existe)
CREATE DATABASE IF NOT EXISTS auto_empeno_db;
USE auto_empeno_db;

-- 2. Tabla de Usuarios (Para el Login)
-- Soporta el formulario de login.html
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL, -- Largo suficiente para hashes seguros
    nombre_completo VARCHAR(100) NOT NULL, -- Para mostrar "Bienvenido, Dueño"
    rol ENUM('admin', 'empleado') DEFAULT 'empleado',
    activo TINYINT(1) DEFAULT 1, -- 1 = Activo, 0 = Bloqueado
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 3. Tabla de Clientes
-- Soporta la sección "Datos del Cliente" en clientes.html
CREATE TABLE clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    telefono VARCHAR(20),      -- Coincide con tu búsqueda por celular
    ine VARCHAR(20) UNIQUE,    -- Coincide con tu búsqueda por INE
    direccion TEXT,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 4. Tabla de Empeños (Artículos)
-- Soporta la tabla "Historial de Empeños"
CREATE TABLE empenos (
    id INT AUTO_INCREMENT PRIMARY KEY, -- Este es tu número de "Folio"
    cliente_id INT NOT NULL,
    
    -- Datos del Artículo
    categoria VARCHAR(50),        -- Ej: Joyería, Electrónica, Herramientas
    marca_modelo VARCHAR(100),    -- Ej: Laptop HP Pavilion
    descripcion TEXT,             -- Detalles visuales
    num_serie_peso VARCHAR(100),  -- Serial o Gramaje (ej. 15gr oro)
    observaciones TEXT,           -- Detalles como "rayones en pantalla"
    
    -- Datos Financieros
    valor_valuo DECIMAL(10, 2) NOT NULL,
    monto_prestamo DECIMAL(10, 2) NOT NULL,
    interes_mensual_pct DECIMAL(5, 2) DEFAULT 10.00, -- Por defecto 10%
    
    -- Fechas
    fecha_empeno DATE NOT NULL,
    fecha_vencimiento DATE NOT NULL, -- Se actualiza al hacer refrendo
    
    -- Estado (Coincide con las etiquetas CSS de tu HTML)
    estado ENUM('Vigente', 'Vencido', 'Desempeñado', 'Rematado', 'Perdido') DEFAULT 'Vigente',
    
    -- Relación
    CONSTRAINT fk_cliente_empeno FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 5. Tabla de Pagos/Movimientos (Vital para Refrendos y Desempeños)
-- Registra el dinero que entra cuando usas las opciones del sidebar
CREATE TABLE movimientos_caja (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empeno_id INT NOT NULL,
    usuario_id INT NOT NULL, -- Quién cobró
    
    tipo_movimiento ENUM('Refrendo', 'Desempeño', 'Abono Capital', 'Venta Remate') NOT NULL,
    monto DECIMAL(10, 2) NOT NULL,
    fecha_movimiento DATETIME DEFAULT CURRENT_TIMESTAMP,
    nota TEXT, -- Para agregar comentarios opcionales
    
    CONSTRAINT fk_movimiento_empeno FOREIGN KEY (empeno_id) REFERENCES empenos(id),
    CONSTRAINT fk_movimiento_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------
-- DATOS DE PRUEBA (Opcional: Para que no inicies en blanco)
-- ---------------------------------------------------------

-- Usuario por defecto (Password simulado, en producción usa hash real)
INSERT INTO usuarios (usuario, hashed_password, nombre_completo, rol) 
VALUES ('admin', '$2y$10$EjemploHashDePassword123456', 'Dueño del Negocio', 'admin');

-- Cliente de ejemplo (Maria Guadalupe de tu HTML)
INSERT INTO clientes (nombre, apellidos, telefono, ine, direccion) 
VALUES ('Maria Guadalupe', 'López García', '953 111 2233', '1234567890123', 'Calle Falsa 123, Col. Centro');

-- Empeño de ejemplo (Anillo de Oro)
INSERT INTO empenos (cliente_id, categoria, marca_modelo, descripcion, valor_valuo, monto_prestamo, fecha_empeno, fecha_vencimiento, estado)
VALUES (1, 'Joyería', 'Anillo de Oro 14k', 'Anillo con piedra pequeña', 7000.00, 5000.00, '2025-09-23', '2025-10-23', 'Vigente');