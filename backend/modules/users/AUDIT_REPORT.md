# USERS DOMAIN - PRE-MIGRATION AUDIT REPORT
## Fecha: 2025-02-26

---

## 1️⃣ FUNCIONES IDENTIFICADAS EN server.py

### FUNCIONES CORE DE USUARIOS (A MIGRAR)

| # | Función | Línea | Async | Dependencias | Usado Por |
|---|---------|-------|-------|--------------|-----------|
| 1 | `count_active_users()` | 3042 | ✅ | db.users | `get_billing_info()`, `update_active_user_count()` |
| 2 | `count_active_residents()` | 3055 | ✅ | db.users | `can_create_user()`, `check_can_create_user()`, endpoints de billing |
| 3 | `update_active_user_count()` | 3106 | ✅ | `count_active_users()`, db.condominiums | `create_user_by_admin()`, `delete_user()`, status updates |
| 4 | `can_create_user()` | 3119 | ✅ | `count_active_residents()`, db.condominiums | `create_user_by_admin()`, `check_can_create_user()` |

### ENDPOINTS DE USUARIOS (A MIGRAR)

| # | Endpoint | Línea | Método | Roles Permitidos |
|---|----------|-------|--------|------------------|
| 1 | `/admin/users` POST | 8561 | `create_user_by_admin()` | Administrador, SuperAdmin |
| 2 | `/admin/users` GET | 8834 | `get_users_by_admin()` | Administrador, SuperAdmin |
| 3 | `/users` GET | 12609 | `get_users()` | Administrador |
| 4 | `/users/{id}/roles` PUT | 12620 | `update_user_roles()` | Administrador |
| 5 | `/admin/seat-usage` GET | 12649 | `get_seat_usage()` | Administrador, SuperAdmin |
| 6 | `/admin/validate-seat-reduction` POST | 12711 | `validate_seat_reduction()` | Administrador, SuperAdmin |
| 7 | `/admin/users/{id}/status-v2` PATCH | 12752 | `update_user_status_v2()` | Administrador, SuperAdmin |
| 8 | `/admin/users/{id}` DELETE | 12866 | `delete_user()` | Administrador, SuperAdmin |
| 9 | `/admin/users/{id}/status` PATCH | 12933 | `update_user_status()` | Administrador, SuperAdmin (legacy) |
| 10 | `/admin/users/{id}/reset-password` POST | 12993 | `admin_reset_user_password()` | Administrador, SuperAdmin |
| 11 | `/admin/users/{id}/status` PATCH | 13208 | `update_user_status_legacy()` | Administrador (deprecated) |

### FUNCIONES DE SOPORTE (A EVALUAR)

| # | Función | Línea | Descripción | Migrar? |
|---|---------|-------|-------------|---------|
| 1 | `get_billing_info()` | 3068 | Info de billing con `count_active_users()` | ❌ Pertenece a billing |
| 2 | `log_billing_event()` | 3169 | Log de eventos de billing | ❌ Pertenece a billing |
| 3 | `check_can_create_user()` | 11604 | Wrapper de `can_create_user()` para frontend | ✅ Sí |
| 4 | `send_credentials_email()` | 1378 | Envía email con credenciales | 🔶 Compartida |
| 5 | `generate_temporary_password()` | (inline) | Genera password temporal | ✅ Sí |

---

## 2️⃣ DEPENDENCIAS

### Billing → Users (CRÍTICO)
```
billing/models.py:167 → can_create_users: bool  (solo campo, no import)
billing/models.py:177 → can_create_users: bool  (solo campo, no import)
```

**El módulo billing NO importa funciones de users directamente.**
La lógica de `can_create_users` se calcula en `get_billing_info()` de server.py.

### Users → Billing
```
create_user_by_admin() → log_billing_event()
update_user_status() → log_billing_event()
can_create_user() → accede a billing_status de condominium
```

### Users → Auth (Compartido)
```
create_user_by_admin() → hash_password()
create_user_by_admin() → generate_temporary_password()
create_user_by_admin() → send_credentials_email()
```

### Users → Audit
```
Todos los endpoints → log_audit_event()
```

### DEPENDENCIAS CIRCULARES POTENCIALES
| Riesgo | Descripción | Solución |
|--------|-------------|----------|
| 🟡 Medio | `get_billing_info()` usa `count_active_users()` | Mantener `count_active_users()` en users y exponer función |
| 🟢 Bajo | `log_billing_event()` usado en users | Importar desde billing module |
| 🟢 Bajo | `send_credentials_email()` compartido | Mantener en utils/email o módulo compartido |

---

## 3️⃣ SEAT LIMIT FLOW (FLUJO COMPLETO)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CREAR USUARIO (create_user_by_admin)              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 1. VALIDAR EMAIL ÚNICO                                               │
│    → db.users.find_one({"email": normalized_email})                  │
│    → Línea: 8571                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. DETERMINAR CONDOMINIUM_ID                                         │
│    → Admin: current_user.condominium_id                              │
│    → SuperAdmin: user_data.condominium_id                            │
│    → Líneas: 8581-8589                                               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. BILLING ENFORCEMENT - can_create_user()                           │
│    → Línea: 8593                                                     │
│    │                                                                 │
│    ├─► Verificar condominio existe y activo (3133-3138)              │
│    │                                                                 │
│    ├─► Verificar billing_status NO es suspended/cancelled (3144-3149)│
│    │                                                                 │
│    └─► Si role == "Residente":                                       │
│        → count_active_residents() (3159)                             │
│        → Comparar con paid_seats (3161)                              │
│        → Bloquear si active_residents >= paid_seats                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. CREAR USUARIO EN DB                                               │
│    → Crear user_doc con todos los campos                             │
│    → db.users.insert_one(user_doc)                                   │
│    → Líneas: 8704-8722                                               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. ACTUALIZAR CONTEO DE SEATS                                        │
│    → update_active_user_count(condominium_id)                        │
│    → Línea: 8725                                                     │
│    │                                                                 │
│    └─► count_active_users() → actualiza condo.active_users           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. AUDIT LOG                                                         │
│    → log_audit_event(USER_CREATED, ...)                              │
│    → Líneas: 8764-8775                                               │
└─────────────────────────────────────────────────────────────────────┘
```

### FLUJO DE ELIMINACIÓN/BLOQUEO
```
delete_user() / update_user_status_v2()
        │
        ▼
Validar permisos (mismo condo, no self, no SuperAdmin)
        │
        ▼
Ejecutar operación (delete/update)
        │
        ▼
update_active_user_count(condo_id)  ← LIBERA SEAT
        │
        ▼
log_audit_event() / log_billing_event()
```

---

## 4️⃣ MODELOS

### En server.py (DUPLICADOS - A ELIMINAR EN FASE 3)
| Modelo | Línea | Migrado a modules/users? |
|--------|-------|--------------------------|
| `RoleEnum` | 547 | ✅ Sí |
| `UserStatus` | 632 | ✅ Sí |
| `UserCreate` | 638 | ✅ Sí |
| `UserLogin` | 645 | ❌ No (pertenece a auth) |
| `UserResponse` | 649 | ✅ Sí |
| `CreateUserByAdmin` | 833 | ❌ **FALTA MIGRAR** |
| `UserStatusUpdateV2` | 12640 | ❌ **FALTA MIGRAR** |
| `UserStatusUpdate` | 12930 | ✅ Sí |

### Modelos FALTANTES en modules/users/models.py
1. **`CreateUserByAdmin`** - Modelo complejo con campos role-specific
2. **`UserStatusUpdateV2`** - Modelo para status con reason
3. **`UserLogin`** - Pertenece a módulo auth (no migrar aquí)

---

## 5️⃣ REPORTE FINAL

### LISTA TOTAL DE FUNCIONES A MIGRAR

#### Funciones Core (Prioridad Alta)
1. `count_active_users()` - L:3042
2. `count_active_residents()` - L:3055
3. `update_active_user_count()` - L:3106
4. `can_create_user()` - L:3119

#### Endpoints (Prioridad Alta)
1. `create_user_by_admin()` - L:8561
2. `get_users_by_admin()` - L:8834
3. `get_users()` - L:12609
4. `update_user_roles()` - L:12620
5. `get_seat_usage()` - L:12649
6. `validate_seat_reduction()` - L:12711
7. `update_user_status_v2()` - L:12752
8. `delete_user()` - L:12866
9. `update_user_status()` - L:12933 (legacy)
10. `admin_reset_user_password()` - L:12993

#### Funciones Auxiliares (Prioridad Media)
1. `check_can_create_user()` - L:11604

### NIVEL DE RIESGO: 🟡 MEDIO

| Factor | Riesgo | Razón |
|--------|--------|-------|
| Complejidad | 🟡 | Muchas funciones interconectadas |
| Dependencias | 🟢 | No hay imports circulares con billing |
| Impacto | 🔴 | Afecta creación/gestión de usuarios (core) |
| Testing | 🟡 | Requiere tests de seat limits |

### IMPORTS CIRCULARES
**Riesgo: BAJO**

No se detectaron imports circulares. El módulo billing NO importa funciones de users directamente. La comunicación es unidireccional:
- `users` → `billing` (log events)
- `users` → `condominiums` (seat info)

### RECOMENDACIÓN TÉCNICA ANTES DE FASE 2

1. **AGREGAR MODELOS FALTANTES** a `modules/users/models.py`:
   - `CreateUserByAdmin`
   - `UserStatusUpdateV2`

2. **CREAR FUNCIÓN DE INICIALIZACIÓN** en `service.py`:
   - Patrón similar a billing: `init_service(db, logger)`

3. **ORDEN DE MIGRACIÓN SUGERIDO**:
   ```
   Paso 1: Funciones core (count_*, update_*, can_create_*)
   Paso 2: Modelos faltantes
   Paso 3: Endpoints simples (get_users, update_roles)
   Paso 4: Endpoints complejos (create_user_by_admin)
   Paso 5: Endpoints de seat management
   ```

4. **MANTENER TEMPORALMENTE** en server.py:
   - `send_credentials_email()` - Compartida con onboarding
   - `generate_temporary_password()` - Mover a utils/security

5. **TESTS CRÍTICOS ANTES DE FASE 3**:
   - Crear usuario con seat limit
   - Bloquear usuario y verificar seat liberado
   - Validar seat reduction
   - Reset password flow

---

## CHECKLIST PRE-FASE 2

- [ ] Agregar `CreateUserByAdmin` a models.py
- [ ] Agregar `UserStatusUpdateV2` a models.py
- [ ] Crear `init_service()` en service.py
- [ ] Documentar dependencias de `log_billing_event()`
- [ ] Preparar tests de seat management
