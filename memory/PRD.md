# GENTURIX Enterprise Platform - PRD

## Fecha: 10 de Enero, 2026

## Problem Statement Original
Construir la interfaz (frontend) de una plataforma empresarial llamada GENTURIX. GENTURIX es el sistema central (el cerebro). Incluye módulos para: Seguridad, Recursos Humanos, Genturix School, Pagos y Auditoría.

## ADN de GENTURIX

### Botón de Pánico (3 Tipos)
- 🚑 **Emergencia Médica**: Emergencia de salud que requiere atención médica inmediata
- 👁️ **Actividad Sospechosa**: Comportamiento o persona sospechosa que requiere verificación  
- 🚨 **Emergencia General**: Otra emergencia que requiere respuesta inmediata

Cada alerta:
- Envía ubicación GPS del residente automáticamente
- Registra tipo de evento
- Notifica a TODOS los guardas activos
- Queda registrado en auditoría legal

### Modelo de Precios
**$1 por usuario al mes** - Modelo masivo, sin planes corporativos
- Sin SaaS caro
- Sin planes complicados
- Accesible para todos

Módulos premium opcionales (futuros):
- Genturix School Pro: +$2/usuario
- Monitoreo CCTV: +$3/usuario
- API Access: +$5/usuario

## User Personas
1. **Administrador** - Acceso completo al sistema
2. **Supervisor** - Gestión de guardas y monitoreo
3. **Guarda** - Control de accesos y seguridad
4. **Residente** - Servicios del condominio, botón de pánico
5. **Estudiante** - Acceso a cursos y certificaciones

## Tech Stack
- Backend: FastAPI + MongoDB + Motor (async)
- Frontend: React + Tailwind + Shadcn/UI
- Auth: JWT (custom implementation)
- Payments: Stripe Integration ($1/user model)

## What's Been Implemented ✅
- [x] Login/Register con JWT
- [x] Dashboard con estadísticas
- [x] **Botón de Pánico con 3 tipos de emergencia**
  - [x] Emergencia Médica
  - [x] Actividad Sospechosa
  - [x] Emergencia General
  - [x] Captura GPS automática
  - [x] Notificación a guardas
  - [x] Registro en auditoría
- [x] Módulo Seguridad (eventos, logs acceso, monitoreo)
- [x] Módulo RH (guardas, turnos, nómina)
- [x] Módulo Genturix School (cursos, inscripciones)
- [x] **Módulo Pagos ($1/usuario/mes)**
  - [x] Calculadora de usuarios
  - [x] Checkout con Stripe
  - [x] Historial de pagos
  - [x] Módulos premium definidos
- [x] Módulo Auditoría (logs con filtros)
- [x] Dark mode elegante
- [x] Datos de demostración

## Demo Credentials
- admin@genturix.com / Admin123!
- supervisor@genturix.com / Super123!
- guarda1@genturix.com / Guard123!
- residente@genturix.com / Resi123!
- estudiante@genturix.com / Stud123!

## Next Tasks
1. Notificaciones push en tiempo real para guardas
2. Sistema de certificados descargable PDF
3. Integración con cámaras IP reales
4. App móvil para residentes (botón de pánico rápido)
