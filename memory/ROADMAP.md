# GENTURIX - Roadmap de Desarrollo

## Last Updated: February 26, 2026

## Modularización Backend

### ✅ FASE 1 - Estructura del Módulo Billing (Completada)
- Creada estructura `/backend/modules/billing/`
- Copiados modelos, servicios y scheduler
- 941 líneas de código modularizado

### ✅ FASE 2 - Migración de Endpoints (Completada - Feb 26, 2026)
- billing_router: 19 endpoints migrados
- billing_super_admin_router: 2 endpoints migrados
- Paths preservados: /api/billing/*, /api/super-admin/billing/*
- Testing: 26/26 tests pasados

### 🔄 FASE 3 - Integración de Servicios (Próxima)
- Mover lógica de negocio de server.py a billing/service.py
- Endpoints llamarán a service.py en lugar de código inline
- Eliminar duplicación de código

### 📋 FASE 4 - Extracción Completa (Futura)
- Mover endpoints de server.py a billing/router.py
- Resolver dependencias circulares
- server.py como application factory puro

---

## Integraciones Pendientes

### P1 - Alta Prioridad
1. **Stripe Subscriptions API** - Pagos recurrentes automáticos
2. **Stripe Webhook Handlers** - Eventos de suscripción
3. **UI Pre-registros** - Eliminar pre-registros "usados"

### P2 - Media Prioridad
1. **Resend Production** - Configurar dominio verificado
2. **Stripe Webhook Verification** - Firma de seguridad
3. **Módulo CCTV**
4. **Reportes HR para guardias**

---

## Modularización Frontend (Futuro)

### Componentes a Modularizar
- `SuperAdminDashboard.js` - Dividir en componentes más pequeños
- `GuardUI.js` - Separar funcionalidades
- `VisitorCheckInGuard.jsx` - Extraer componentes reutilizables

---

## Notas Técnicas

### Dependencias Actuales
- APScheduler para jobs programados
- Resend (sandbox) para emails
- Stripe (parcialmente integrado)
- Firebase Cloud Messaging para push notifications

### Credenciales de Prueba
- SuperAdmin: superadmin@genturix.com / Admin123!
- Resident: test-resident@genturix.com / Admin123!
- Guard: guarda1@genturix.com / Guard123!
