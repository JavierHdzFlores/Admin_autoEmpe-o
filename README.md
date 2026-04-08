# 🏦 Sistema de Administración para Casa de Empeños

Una aplicación web diseñada para digitalizar y administrar el flujo completo de una casa de empeños. Permite el control de clientes, valuación de artículos, cálculo de préstamos, refrendos y remates.

## 🚀 Tecnologías Utilizadas
- **Backend:** Python (Arquitectura basada en CRUD, Models y Schemas)
- **Frontend:** HTML5, CSS3 puro, JavaScript
- **Base de Datos:** MySQL (Relacional)
- **Infraestructura:** Docker (Local) y Railway (Cloud Deployment)

## ⚙️ Características Principales
- **Gestión de Usuarios y Seguridad:** Autenticación con contraseñas encriptadas y control de acceso basado en roles (Admin/Empleado).
- **Control de Inventario y Préstamos:** Registro detallado de artículos (joyería, electrónica), cálculo de intereses mensuales y control de fechas de vencimiento.
- **Transacciones Financieras:** Registro de movimientos de caja (Refrendos, Desempeños, Abonos a Capital y Ventas por Remate).
- **Arquitectura Limpia:** Separación de responsabilidades (`models.py`, `crud.py`, `security.py`) facilitando la escalabilidad del código.

## 🛠️ Instalación y Despliegue Local

1. Clona el repositorio.
2. Configura tus variables de entorno en el archivo `.env` (credenciales de BD).
3. Levanta el contenedor con Docker:
   ```bash
   docker-compose up --build
