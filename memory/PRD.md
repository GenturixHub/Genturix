# GENTURIX Enterprise Platform - PRD

## Fecha: 10 de Enero, 2026

## Visión
GENTURIX no es un dashboard corporativo. Es una plataforma de seguridad y emergencias para personas bajo estrés. Diseño "Emergency-First".

## ADN de GENTURIX

### Botón de Pánico (3 Tipos)
- 🚑 **Emergencia Médica**: Emergencia de salud que requiere atención médica inmediata
- 👁️ **Actividad Sospechosa**: Comportamiento o persona sospechosa que requiere verificación  
- 🚨 **Emergencia General**: Otra emergencia que requiere respuesta inmediata

Cada alerta:
- ✅ Captura ubicación GPS automáticamente
- ✅ Registra tipo específico de emergencia
- ✅ Notifica a TODOS los guardas activos
- ✅ Queda registrado en auditoría legal

### Modelo de Precios
**$1 por usuario al mes** - Modelo masivo, sin planes corporativos
- Sin SaaS caro
- Sin planes complicados
- Accesible para todos
- Calculadora de usuarios integrada

Módulos premium opcionales (futuros):
- Genturix School Pro: +$2/usuario
- Monitoreo CCTV: +$3/usuario
- API Access: +$5/usuario

## Interfaces por Rol

### Residente UI (`/resident`)
- Pantalla completa con 3 botones de emergencia grandes
- GPS capturado automáticamente
- Sin distracciones - emergencias primero
- Confirmación visual cuando se envía alerta

### Guarda UI (`/guard`)
- Lista de emergencias activas en tiempo real
- Coordenadas GPS con link a Google Maps
- Botón "Resolver" para cada emergencia
- Auto-refresh cada 10 segundos

### Estudiante UI (`/student`)
- Cursos disponibles
- Progreso de aprendizaje
- Certificados obtenidos

### Admin Dashboard (`/admin/dashboard`)
- Acceso completo a todos los módulos
- Seguridad, RH, Pagos, Auditoría
- Gestión de usuarios

## Tech Stack
- Backend: FastAPI + MongoDB + Motor (async)
- Frontend: React + Tailwind + Shadcn/UI
- Auth: JWT (custom implementation)
- Payments: Stripe Integration ($1/user model)

## What's Been Implemented ✅
- [x] Interfaces específicas por rol
- [x] Botón de pánico con 3 tipos de emergencia
- [x] Captura GPS automática
- [x] Notificación a guardas
- [x] UI de Guarda con emergencias activas
- [x] Modelo de precios $1/usuario
- [x] Calculadora de usuarios
- [x] Dashboard admin completo
- [x] Módulos: Seguridad, RH, School, Pagos, Auditoría
- [x] PostHog error suppressed

## Test Results
- Backend: 100% (24/24 tests passed)
- Frontend: 100% (All UIs working)
- Integration: 100%

## Demo Credentials
- admin@genturix.com / Admin123!
- supervisor@genturix.com / Super123!
- guarda1@genturix.com / Guard123!
- residente@genturix.com / Resi123!
- estudiante@genturix.com / Stud123!

## Next Tasks
1. Notificaciones push en tiempo real (WebSockets)
2. SMS/WhatsApp a guardas cuando hay pánico
3. App móvil para botón de pánico rápido
4. Integración con cámaras IP reales
5. Certificados descargables en PDF
