# 🔔 AUDITORÍA PUSH NOTIFICATIONS VAPID - ROL GUARDA

## Fecha: 2026-02-25
## Estado: ⚠️ CONFIGURACIÓN CORRECTA, PROBLEMA DE ADOPCIÓN

---

## 1️⃣ VERIFICACIÓN DE CONFIGURACIÓN VAPID

### Variables de Entorno
| Variable | Estado | Valor |
|----------|--------|-------|
| `VAPID_PUBLIC_KEY` | ✅ Configurada | `BB_Jr5X0KemRHT...` (86 chars) |
| `VAPID_PRIVATE_KEY` | ✅ Configurada | `bSm0TTlrM2...` (43 chars) |
| `VAPID_CLAIMS_EMAIL` | ✅ Configurada | `admin@genturix.com` |

### Verificación de Carga
```python
# server.py líneas 123-125
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "admin@example.com")
```
**Estado:** ✅ Las claves se cargan correctamente desde el entorno.

---

## 2️⃣ ROLES EN BASE DE DATOS

### Verificación de Nomenclatura
| Rol en DB | Ocurrencias | Correcto |
|-----------|-------------|----------|
| `Guarda` | 15 usuarios | ✅ |
| `Guard` | 0 usuarios | N/A |
| `guard` | 0 usuarios | N/A |

**Conclusión:** ✅ No hay mismatch de roles. Todos usan `"Guarda"`.

### Query Utilizado en `notify_guards_of_panic()`
```python
guard_query = {
    "condominium_id": condominium_id,
    "roles": {"$in": ["Guarda"]},  # ✅ Correcto
    "is_active": True,
    "status": {"$in": ["active", None]}
}
```

---

## 3️⃣ ESTADO DE SUSCRIPCIONES PUSH

### Estadísticas Actuales
| Métrica | Valor |
|---------|-------|
| Total suscripciones | 6 |
| Suscripciones de Guardas | **1** |
| Guardas en DB | 15 |
| Guardas SIN suscripción | **14** |

### 🚨 CAUSA RAÍZ IDENTIFICADA
**El problema NO es de código**, sino de **adopción de usuarios**.

De 15 guardias activos, solo 1 tiene suscripción push activa:
- `j@j.com` (Guarda) - ✅ Tiene suscripción activa

Los otros 14 guardias **nunca activaron notificaciones push** en su navegador.

### Suscripción del Guardia Activo
```json
{
  "user_id": "70f09cf3-ec0a-45d9-ad2d-fe65774a0502",
  "role": "Guarda",
  "condominium_id": "9043cd55-8b28-42d5-923e-f30e62b8f35f",
  "is_active": true,
  "endpoint": "https://fcm.googleapis.com/fcm/send/...",
  "p256dh": "✅ Present",
  "auth": "✅ Present"
}
```

---

## 4️⃣ REVISIÓN DE FUNCIONES DE ENVÍO

### `send_push_notification()` (línea 2074)
- ✅ Usa `pywebpush` correctamente
- ✅ Maneja errores 404/410 (suscripciones inválidas)
- ✅ NO elimina suscripciones por otros errores (timeouts, etc.)

### `send_push_notification_with_cleanup()` (línea 2162)
- ✅ Retorna resultado detallado
- ✅ Solo elimina en 404/410 (Gone/Not Found)
- ✅ No elimina en errores temporales

### `notify_guards_of_panic()` (línea 2227)
- ✅ Filtra por `condominium_id` correcto
- ✅ Filtra por rol `"Guarda"` correctamente
- ✅ Excluye al sender si se proporciona
- ✅ Logging detallado agregado (AUDIT tags)

---

## 5️⃣ VERIFICACIÓN FRONTEND

### Registro de Suscripción (AuthContext.js)
```javascript
const response = await fetch(`${API_URL}/api/push/subscribe`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    endpoint: subscriptionJson.endpoint,
    keys: {
      p256dh: subscriptionJson.keys.p256dh,
      auth: subscriptionJson.keys.auth,
    },
    expirationTime: subscriptionJson.expirationTime,
  }),
});
```
**Estado:** ✅ Frontend envía todos los campos requeridos.

### Backend Endpoint `/push/subscribe` (línea 3510)
```python
sub_doc = {
    "id": str(uuid.uuid4()),
    "user_id": user_id,
    "role": primary_role,  # ✅ Se guarda el rol
    "condominium_id": condo_id,  # ✅ Se guarda el condominio
    "endpoint": subscription.endpoint,
    "p256dh": subscription.keys.p256dh,
    "auth": subscription.keys.auth,
    ...
}
```
**Estado:** ✅ El rol se guarda correctamente al registrar suscripción.

---

## 6️⃣ VERIFICACIÓN DE ELIMINACIÓN DE SUSCRIPCIONES

### Política Actual
| Error | Acción | Estado |
|-------|--------|--------|
| 404 Not Found | Eliminar suscripción | ✅ Correcto |
| 410 Gone | Eliminar suscripción | ✅ Correcto |
| Timeout | NO eliminar | ✅ Correcto |
| 5xx Server Error | NO eliminar | ✅ Correcto |
| Otros errores | NO eliminar | ✅ Correcto |

**Conclusión:** ✅ No se están eliminando suscripciones válidas por error.

---

## 7️⃣ LOGGING AGREGADO

Se agregó logging detallado con tag `[PANIC-PUSH-AUDIT]`:

```
[PANIC-PUSH-AUDIT] ======= NOTIFY GUARDS START =======
[PANIC-PUSH-AUDIT] Input | condo_id=XXX | sender_id=YYY
[PANIC-PUSH-AUDIT] Panic data | type=general | resident=John | apt=A-101
[PANIC-PUSH-AUDIT] Condominium found | name=Terrazas | is_active=True
[PANIC-PUSH-AUDIT] Guards found | count=3
[PANIC-PUSH-AUDIT]   - Guard: j@j.com | id=70f09cf3-ec...
[PANIC-PUSH-AUDIT] Subscriptions found | count=1
[PANIC-PUSH-AUDIT]   - Guard j@j.com: 1 active subscription(s)
[PANIC-PUSH-AUDIT] Guards WITHOUT subscriptions: 2
[PANIC-PUSH-AUDIT]   - guarda1@genturix.com has NO push subscription!
[PANIC-PUSH-AUDIT] ======= DELIVERY COMPLETE =======
[PANIC-PUSH-AUDIT] Result | condo=Terrazas | guards=3 | subs=1 | sent=1 | failed=0
[PANIC-PUSH-AUDIT] ======= NOTIFY GUARDS END =======
```

---

## 📊 RESUMEN EJECUTIVO

### Causa Raíz
**NO es un problema de código.** El sistema está correctamente implementado.

El problema es que **14 de 15 guardias nunca activaron notificaciones push** en sus dispositivos.

### Flujo de Activación Requerido
Para que un guardia reciba notificaciones:
1. Iniciar sesión en la app
2. Ir a Perfil/Configuración
3. Activar "Notificaciones Push"
4. Aceptar el permiso del navegador
5. El navegador genera una suscripción
6. El frontend la envía al backend
7. El backend la guarda con rol="Guarda"

### Verificaciones Completadas
| Item | Estado |
|------|--------|
| VAPID keys configuradas | ✅ |
| Roles sin mismatch | ✅ |
| Suscripciones se guardan con rol | ✅ |
| Frontend envía datos completos | ✅ |
| Backend filtra por condominio | ✅ |
| No se eliminan subs válidas | ✅ |
| Logging de auditoría agregado | ✅ |

### Recomendaciones
1. **Comunicar a los guardias** que deben activar notificaciones push
2. **Verificar en Railway** que las variables VAPID estén configuradas
3. **Monitorear logs** con tag `[PANIC-PUSH-AUDIT]` para diagnóstico

---

## 📋 NO SE MODIFICÓ LÓGICA PRINCIPAL

Solo se agregó:
- Logging detallado temporal con tag `[PANIC-PUSH-AUDIT]`
- Detalles de guardias encontrados vs. suscripciones activas
- Alertas de guardias sin suscripción

---

*Reporte generado: 2026-02-25*
*Auditoría: Push Notifications VAPID - Rol Guarda*
