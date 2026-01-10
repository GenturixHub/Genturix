# GENTURIX Enterprise Platform - PRD

## Fecha: 10 de Enero, 2026

## Problem Statement Original
Construir la interfaz (frontend) de una plataforma empresarial llamada GENTURIX. GENTURIX es el sistema central (el cerebro). Incluye módulos para: Seguridad, Recursos Humanos, Genturix School, Pagos y Auditoría.

## User Personas
1. **Administrador** - Acceso completo al sistema
2. **Supervisor** - Gestión de guardas y monitoreo
3. **Guarda** - Control de accesos y seguridad
4. **Residente** - Servicios del condominio
5. **Estudiante** - Acceso a cursos y certificaciones

## Core Requirements
- Login JWT con email/contraseña
- Selección de panel por rol
- Dashboard principal con estadísticas
- Módulo Seguridad (botón pánico, eventos, accesos, monitoreo)
- Módulo RH (guardas, turnos, salarios, nómina)
- Módulo Genturix School (cursos, inscripciones, certificados)
- Módulo Pagos (planes Stripe, historial)
- Módulo Auditoría (logs, filtros)

## Tech Stack
- Backend: FastAPI + MongoDB + Motor (async)
- Frontend: React + Tailwind + Shadcn/UI
- Auth: JWT (custom implementation)
- Payments: Stripe Integration

## What's Been Implemented ✅
- [x] Backend completo con todas las APIs
- [x] Login/Register con JWT
- [x] Dashboard con estadísticas en tiempo real
- [x] Módulo Seguridad (eventos pánico, logs acceso, monitoreo CCTV)
- [x] Módulo RH (guardas, turnos, nómina)
- [x] Módulo Genturix School (cursos, inscripciones)
- [x] Módulo Pagos (3 planes, integración Stripe)
- [x] Módulo Auditoría (logs con filtros)
- [x] Dark mode elegante estilo Twitch
- [x] Datos de demostración
- [x] Diseño responsive

## Demo Credentials
- admin@genturix.com / Admin123!
- supervisor@genturix.com / Super123!
- guarda1@genturix.com / Guard123!
- residente@genturix.com / Resi123!
- estudiante@genturix.com / Stud123!

## Prioritized Backlog

### P0 (Crítico)
- ✅ Completado

### P1 (Alta Prioridad)
- [ ] Sistema de certificados descargable
- [ ] Notificaciones push en tiempo real
- [ ] Exportación de reportes PDF

### P2 (Media Prioridad)
- [ ] Light mode opcional
- [ ] Panel de configuración avanzada
- [ ] Integración con cámaras IP reales
- [ ] Sistema de mensajería interna

### P3 (Baja Prioridad)
- [ ] App móvil nativa
- [ ] Biometría
- [ ] Multi-idioma

## Next Tasks
1. Implementar descarga de certificados
2. Sistema de notificaciones en tiempo real
3. Reportes exportables en PDF
4. Integración con cámaras IP
