# AUDITORÍA COMPLETA GENTURIX - PRE-PILOTO
## Fecha: 2025-02-27

---

# RESUMEN EJECUTIVO

| Área | Estado | Nivel |
|------|--------|-------|
| Backend Architecture | ✅ Bueno | Verde |
| Billing Engine | ⚠️ Parcial | Amarillo |
| Seat Engine | ✅ Funcional | Verde |
| Database | ⚠️ Mejoras necesarias | Amarillo |
| Security | ✅ Correcto | Verde |
| Frontend | ⚠️ Componentes grandes | Amarillo |
| Mobile UX | 🔴 Bug detectado | Rojo |
| Performance | ⚠️ Riesgos a escala | Amarillo |

## ¿LISTO PARA PILOTO?
**CASI** - Requiere corrección del bug móvil antes de piloto con residentes.

---

# 1. AUDITORÍA BACKEND ARCHITECTURE

## Métricas
| Archivo/Módulo | Líneas | % del Total |
|----------------|--------|-------------|
| server.py | 16,561 | 91.1% |
| modules/billing/* | ~700 | 3.9% |
| modules/users/* | ~913 | 5.0% |
| **TOTAL** | ~18,174 | 100% |

## Modularización
- ✅ **billing**: Completamente desacoplado
  - router.py: Documentación de endpoints migrados
  - service.py: Toda la lógica de billing
  - scheduler.py: Jobs de facturación
  - models.py: Modelos Pydantic

- ✅ **users**: Parcialmente modularizado
  - service.py: Funciones core del seat engine
  - models.py: Modelos de usuario
  - permissions.py: Lógica RBAC
  - router.py: Preparado para migración futura

## Verificaciones
- ✅ NO hay imports circulares
- ✅ NO hay funciones duplicadas (count_active_users, can_create_user, etc.)
- ✅ NO hay modelos duplicados (CreateUserByAdmin, UserStatusUpdateV2)
- ⚠️ server.py aún contiene 91% del código

---

# 2. AUDITORÍA BILLING ENGINE

## Campos en Condominios
| Campo | Estado | Detalle |
|-------|--------|---------|
| paid_seats | ⚠️ | Algunos condos sin configurar |
| active_users | ✅ | Funcionando |
| billing_status | ⚠️ | Algunos condos sin estado |
| next_invoice_amount | ⚠️ | No configurado en todos |
| balance_due | ⚠️ | No configurado en todos |
| next_billing_date | ⚠️ | No configurado en todos |
| billing_cycle | ⚠️ | No configurado en todos |

## Muestra de Condominios
```
Bariloche            | status: N/A    | seats: N/A | users: 7
Residencial Las Palmas | status: active | seats: 50  | users: 29
Romero              | status: N/A    | seats: N/A | users: N/A
```

## Colecciones de Billing
- billing_payments: 26 documentos ✅
- billing_events: 59 documentos ✅

## 🔴 CRÍTICO PARA PILOTO
Los condominios que entren al piloto **DEBEN** tener configurados:
- `paid_seats`
- `billing_status` 
- `billing_cycle`
- `next_billing_date`

---

# 3. AUDITORÍA SEAT ENGINE

## Funciones Core
| Función | Estado | Test |
|---------|--------|------|
| `count_active_users()` | ✅ | Devuelve 11 |
| `count_active_residents()` | ✅ | Devuelve 5 |
| `can_create_user()` | ✅ | Protección activa |
| `update_active_user_count()` | ✅ | Actualiza condo |

## Protección de Seats
- ✅ Protección funciona cuando `active_residents >= paid_seats`
- ✅ Mensajes de error apropiados
- ✅ Logging de intentos bloqueados

---

# 4. AUDITORÍA BASE DE DATOS

## Índices Existentes
| Colección | Índices | Estado |
|-----------|---------|--------|
| billing_payments | `{condominium_id: 1, created_at: -1}` | ✅ |
| billing_events | `{condominium_id: 1, created_at: -1}` | ✅ |
| condominiums | `{billing_status: 1}`, `{id: 1}` | ✅ |
| users | `{condominium_id: 1}`, `{email: 1}` | ✅ |
| guards | `{condominium_id: 1}` | ✅ |
| shifts | `{condominium_id: 1, guard_id: 1}`, `{condominium_id: 1, start_time: -1}` | ✅ |
| visits | ⚠️ Sin índices personalizados | |
| alerts | ⚠️ Sin índices personalizados | |
| reservations | `{condominium_id: 1}`, `{start_time: 1}` | ✅ |

## Tamaños de Colecciones
```
condominiums: 61 docs
users: 90 docs
guards: 13 docs
shifts: 30 docs
reservations: 46 docs
billing_payments: 26 docs
billing_events: 59 docs
visits: 0 docs
alerts: 0 docs
```

## 🔴 ÍNDICES FALTANTES (CRÍTICO)
```javascript
// visits - Alta frecuencia en piloto
db.visits.createIndex({ "condominium_id": 1, "created_at": -1 })
db.visits.createIndex({ "resident_id": 1, "status": 1 })

// alerts - Crítico para seguridad
db.alerts.createIndex({ "condominium_id": 1, "created_at": -1 })
db.alerts.createIndex({ "type": 1, "status": 1 })
```

## ⚠️ QUERIES SIN LÍMITE (PERFORMANCE)
Se encontraron múltiples `to_list(None)` que pueden causar problemas:
- push_subscriptions queries
- users queries en notificaciones
- guards queries

---

# 5. AUDITORÍA SEGURIDAD

## Stripe Webhooks
- ✅ `STRIPE_WEBHOOK_SECRET` configurado
- ✅ `construct_event()` verifica firmas
- ✅ Fail-closed en producción
- ⚠️ Warning si no está configurado (desarrollo)

## Protección de Endpoints Críticos
| Endpoint | Roles Requeridos | Estado |
|----------|------------------|--------|
| `/billing/confirm-payment` | Administrador | ✅ |
| `/billing/seats` | SuperAdmin | ✅ |
| `/super-admin/billing/*` | SuperAdmin | ✅ |
| `/admin/users` | Administrador, SuperAdmin | ✅ |

## Verificaciones
- ✅ Roles protegidos con `require_role()`
- ✅ Multi-tenancy por `condominium_id`
- ✅ SuperAdmin override funcional

---

# 6. AUDITORÍA FRONTEND

## Componentes Grandes (>2000 líneas)
| Componente | Líneas | Prioridad Refactor |
|------------|--------|-------------------|
| SuperAdminDashboard.js | 3,637 | 🔴 Alta |
| GuardUI.js | 2,654 | 🔴 Alta |
| UserManagementPage.js | 2,366 | 🟡 Media |
| RRHHModule.js | 2,235 | 🟡 Media |

## Componentes Medianos (1000-2000 líneas)
| Componente | Líneas |
|------------|--------|
| OnboardingWizard.js | 1,661 |
| VisitorCheckInGuard.jsx | 1,568 |
| ReservationsModule.js | 1,475 |
| ResidentUI.js | 1,332 |

## Total Frontend
- **40,203 líneas** en componentes principales
- 4 componentes superan 2,000 líneas

---

# 7. AUDITORÍA MOBILE UX - BUG DETECTADO 🔴

## Problema
**Pantalla**: Resident Visits / Authorizations
**Síntoma**: No permite scroll vertical
**Impacto**: CRÍTICO para piloto

## Análisis Técnico

### Archivo Afectado
`/app/frontend/src/components/VisitorAuthorizationsResident.jsx`

### Línea del Bug
```jsx
// Línea 958
<div className="min-h-0 flex-1 flex flex-col overflow-hidden">
```

### Problema
El contenedor principal tiene `overflow-hidden` que bloquea completamente el scroll, incluso aunque el hijo (`ScrollArea`) tenga `overflowY: auto`.

### Estructura Actual
```
ResidentLayout (overflow: hidden, 100dvh)
  └── main (overflow: hidden)
      └── div (overflowY: auto) ← Scroll debería funcionar aquí
          └── VisitorAuthorizationsResident
              └── div (overflow-hidden) ← BUG: Bloquea scroll
                  └── ScrollArea (flex-1 h-full) ← No puede scrollear
```

### Solución Propuesta
```jsx
// ANTES (línea 958)
<div className="min-h-0 flex-1 flex flex-col overflow-hidden">

// DESPUÉS
<div className="min-h-0 flex-1 flex flex-col">
```

O alternativamente, mantener `overflow-hidden` pero asegurarse de que el ScrollArea tenga altura explícita:
```jsx
<ScrollArea className="flex-1 min-h-0">
```

---

# 8. AUDITORÍA PERFORMANCE

## Simulación de Carga
```
Escenario Piloto:
- 25 condominios
- 300 usuarios promedio
- 7,500 usuarios totales
```

## Endpoints Pesados
| Endpoint | Operación | Riesgo |
|----------|-----------|--------|
| `/super-admin/billing/overview` | Lista todos los condos | 🟡 Medio |
| `/admin/users` | Lista usuarios | 🟢 Bajo (tiene índice) |
| `/authorizations/history` | Historial visitas | 🟡 Medio |
| `/guard/history` | Historial guardia | 🟡 Medio |

## Queries Sin Límite Detectadas
```python
# ⚠️ RIESGO: Pueden crecer indefinidamente
guards = await db.users.find(guard_query).to_list(None)
subscriptions = await db.push_subscriptions.find({}).to_list(None)
matching_users = await db.users.find(user_query).to_list(None)
```

## Recomendaciones
1. Agregar `.limit()` a queries con `to_list(None)`
2. Implementar paginación en endpoints de listado
3. Agregar índices a `visits` y `alerts`

---

# 9. AUDITORÍA PILOTO (128 RESIDENTES)

## Flujos Críticos

| Flujo | Backend | Frontend | Estado |
|-------|---------|----------|--------|
| Creación usuarios | ✅ | ✅ | Funcional |
| Visitas/Autorizaciones | ✅ | 🔴 Bug scroll | **BLOQUEADO** |
| Alertas/Emergencias | ✅ | ✅ | Funcional |
| Reservas | ✅ | ✅ | Funcional |
| Pagos | ✅ | ✅ | Funcional (Admin) |

## Checklist Pre-Piloto

### 🔴 BLOQUEADORES
- [ ] Corregir bug scroll en VisitorAuthorizationsResident
- [ ] Configurar billing fields en condominio piloto

### 🟡 IMPORTANTES
- [ ] Crear índices para `visits` y `alerts`
- [ ] Agregar límites a queries sin límite
- [ ] Verificar usuario residente de prueba

### 🟢 MEJORAS
- [ ] Refactorizar componentes >2000 líneas
- [ ] Implementar paginación en listados
- [ ] Optimizar queries de notificaciones push

---

# 10. RESULTADO FINAL

## Clasificación de Hallazgos

### 🔴 CRÍTICO (Bloquea piloto)
1. **Bug scroll móvil** en pantalla de visitas de residentes
2. **Campos billing** no configurados en algunos condominios

### 🟡 IMPORTANTE (Debe resolverse pronto)
1. Índices faltantes en `visits` y `alerts`
2. Queries sin límite (`to_list(None)`)
3. Componentes frontend >2000 líneas

### 🟢 MEJORA (No bloquea)
1. server.py aún tiene 91% del código
2. Paginación en endpoints de listado
3. Optimización de queries de push notifications

## Veredicto Final

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ¿ESTÁ LISTO EL SISTEMA PARA PILOTO REAL?                   ║
║                                                               ║
║   RESPUESTA: NO - Requiere 2 correcciones críticas           ║
║                                                               ║
║   1. Corregir bug de scroll en visitas (móvil)               ║
║   2. Configurar campos billing en condominio piloto          ║
║                                                               ║
║   Tiempo estimado: 1-2 horas de trabajo                       ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

## Acciones Inmediatas Recomendadas

1. **URGENTE**: Corregir `overflow-hidden` en VisitorAuthorizationsResident.jsx
2. **URGENTE**: Ejecutar script para configurar billing en condos del piloto
3. **PRIORITARIO**: Crear índices en `visits` y `alerts`
4. **PRIORITARIO**: Agregar `.limit()` a queries con `to_list(None)`

---

*Auditoría generada automáticamente - GENTURIX v1.0*
*Fecha: 2025-02-27*
