# AUDITORÍA SISTEMA PUSH NOTIFICATIONS - GENTURIX
## Fecha: 2026-02-28
## Versión del Reporte: 2.0

---

## RESUMEN EJECUTIVO

**Problema reportado:** Usuarios reciben notificaciones vacías con:
- Title: "GENTURIX"
- Body: "Nueva notificación"

**Causa raíz identificada:** El Service Worker NO maneja el flag `silent: true` y muestra TODAS las notificaciones, incluyendo las de validación del sistema.

---

## 1. ARQUITECTURA ACTUAL

### Funciones de envío push (backend/server.py):

| Función | Línea | Propósito |
|---------|-------|-----------|
| `send_push_notification()` | 2231 | Envío directo via webpush |
| `send_push_notification_with_cleanup()` | 2319 | Envío + cleanup en error 404/410 |
| `notify_guards_of_panic()` | 2388 | Notificar pánico a guardias |
| `send_push_to_user()` | 2601 | Enviar a usuario específico |
| `send_push_to_guards()` | 2650 | Enviar a todos los guardias |
| `send_push_to_admins()` | 2712 | Enviar a administradores |
| `send_targeted_push_notification()` | 2768 | Envío dinámico por roles/usuarios |
| `create_and_send_notification()` | 2990 | Crear en DB + enviar push |

---

## 2. TRIGGERS DE PUSH IDENTIFICADOS

### ✅ TRIGGERS CORRECTOS (payload completo):

| Trigger | Línea | Title | Body | Data |
|---------|-------|-------|------|------|
| Pánico | 2447 | "¡ALERTA DE PÁNICO! - {tipo}" | "{residente} - {apto}" | ✅ event_id, panic_type, url |
| Preregistro visitante (v1) | 5235 | "📋 Nuevo visitante preregistrado" | "{nombre} para {residente}" | ✅ visitor_id, url |
| Preregistro visitante (v2) | 5600 | "📋 Nuevo visitante preregistrado" | "{nombre} - autorizado por {residente}" | ✅ authorization_id, url |
| Llegada visitante | 6345 | "🚪 Tu visitante ha llegado" | "{nombre} ha ingresado al condominio" | ✅ entry_id, url |
| Salida visitante | 6504 | "👋 Tu visitante ha salido" | "{nombre} ha salido del condominio" | ✅ entry_id, url |
| Reserva auto-aprobada | 9867 | "✅ Reservación confirmada" | "Tu reserva de {área} para {fecha}" | ✅ reservation_id, url |
| Reserva pendiente | 9885 | "📅 Nueva reservación pendiente" | "{residente} solicitó {área}" | ✅ reservation_id, url |
| Reserva aprobada | 10352 | "✅ Reservación aprobada" | "Tu reservación de {área} fue aprobada" | ✅ reservation_id, url |
| Reserva rechazada | 10388 | "❌ Reservación rechazada" | "Tu reservación fue rechazada" | ✅ reservation_id, reason, url |
| Test push (debug) | 4521 | "Test Push Production" | "Si recibes esto..." | ✅ type: test |

### ⚠️ TRIGGERS PROBLEMÁTICOS (payload vacío o silent):

| Trigger | Línea | Problema |
|---------|-------|----------|
| Validación suscripciones | 4148 | `title: ""`, `body: ""`, `silent: true` |
| Validación usuario | 4317 | `title: ""`, `body: ""`, `silent: true` |
| Validación batch | 4152 | `"title": "GENTURIX System Check"`, `silent: true` |

---

## 3. ANÁLISIS DEL SERVICE WORKER

### Archivo: `/app/frontend/public/service-worker.js` (v16)

**Líneas críticas 142-168:**

```javascript
self.addEventListener('push', (event) => {
  // Default notification data - SIEMPRE SE USA SI PAYLOAD ESTÁ VACÍO
  let data = {
    title: 'GENTURIX',                    // ← FALLBACK
    body: 'Nueva notificación',           // ← FALLBACK
    icon: NOTIFICATION_ICON,
    badge: NOTIFICATION_BADGE,
    tag: 'genturix-notification',
    data: {}
  };

  if (event.data) {
    try {
      const payload = event.data.json();
      data = {
        title: payload.title || data.title,   // ← Si title="" usa fallback
        body: payload.body || data.body,      // ← Si body="" usa fallback
        icon: NOTIFICATION_ICON,
        badge: NOTIFICATION_BADGE,
        tag: payload.tag || `genturix-${Date.now()}`,
        data: payload.data || {}
      };
    } catch (e) {
      console.error(`[SW v${SW_VERSION}] Push data parse error:`, e);
    }
  }
  // ... SIEMPRE muestra notificación
```

### 🔴 PROBLEMAS ENCONTRADOS:

1. **NO MANEJA `silent: true`**: El SW ignora el flag `silent` y muestra TODAS las notificaciones.

2. **Fallback permisivo**: Si `title` o `body` son string vacío (`""`), usa el fallback "GENTURIX" / "Nueva notificación".

3. **No valida payload mínimo**: No verifica que title Y body tengan contenido real antes de mostrar.

---

## 4. FLUJO DEL BUG

```
1. Backend: POST /api/push/validate-user-subscription
      ↓
2. Backend envía push con: {title: "", body: "", silent: true}
      ↓
3. Service Worker recibe event.data.json()
      ↓
4. SW: payload.title = "" → usa fallback "GENTURIX"
   SW: payload.body = "" → usa fallback "Nueva notificación"
      ↓
5. SW: showNotification("GENTURIX", {body: "Nueva notificación"})
      ↓
6. Usuario ve notificación vacía 😔
```

---

## 5. FIXES RECOMENDADOS

### FIX 1: Service Worker - Ignorar notificaciones silentes y vacías

```javascript
self.addEventListener('push', (event) => {
  // Early exit if no data
  if (!event.data) {
    console.log(`[SW v${SW_VERSION}] Push received with no data, ignoring`);
    return;
  }
  
  let payload;
  try {
    payload = event.data.json();
  } catch (e) {
    console.error(`[SW v${SW_VERSION}] Push data parse error:`, e);
    return;
  }
  
  // FIX: Skip silent notifications (validation checks)
  if (payload.silent === true) {
    console.log(`[SW v${SW_VERSION}] Silent notification, skipping display`);
    return;
  }
  
  // FIX: Require valid title AND body (not empty strings)
  if (!payload.title || !payload.body || 
      payload.title.trim() === '' || payload.body.trim() === '') {
    console.log(`[SW v${SW_VERSION}] Empty title/body, skipping display`);
    return;
  }
  
  // Build notification with payload data (no fallbacks needed)
  const data = {
    title: payload.title,
    body: payload.body,
    icon: NOTIFICATION_ICON,
    badge: NOTIFICATION_BADGE,
    tag: payload.tag || `genturix-${Date.now()}`,
    data: payload.data || {}
  };
  
  // ... rest of notification code
```

### FIX 2: Backend - Asegurar payloads completos

En las funciones de validación, usar un flag que el Service Worker pueda reconocer:

```python
# En validate_user_subscription y validate_subscriptions
test_payload = {
    "silent": True,  # ← El SW debe ignorar esto
    "data": {"type": "validation"}
    # NO incluir title ni body
}
```

---

## 6. RESUMEN DE CAMBIOS NECESARIOS

| Archivo | Cambio | Prioridad |
|---------|--------|-----------|
| `service-worker.js` | Agregar check para `silent: true` y salir early | 🔴 CRÍTICO |
| `service-worker.js` | Validar que title/body NO sean vacíos | 🔴 CRÍTICO |
| `service-worker.js` | Eliminar fallbacks "GENTURIX" / "Nueva notificación" | 🟡 ALTO |
| `server.py` | Documentar que silent=true significa "no mostrar" | 🟢 BAJO |

---

## 7. VERIFICACIÓN POST-FIX

1. Ejecutar `POST /api/push/validate-subscriptions?dry_run=false`
2. Verificar que NO aparezcan notificaciones vacías
3. Enviar notificación de prueba: `POST /api/push/test-to-user/{user_id}`
4. Verificar que SI aparezca con título y body correctos
5. Verificar que alertas de pánico sigan funcionando

---

## 8. CONCLUSIÓN

El problema de las notificaciones vacías es causado por:

1. **Notificaciones de validación silentes** enviadas por endpoints de diagnóstico
2. **Service Worker que no respeta el flag `silent`** y muestra TODO
3. **Fallbacks permisivos** que muestran "GENTURIX / Nueva notificación" cuando title/body están vacíos

El fix es sencillo y requiere ~10 líneas de código en el Service Worker.

---

*Reporte generado por auditoría de estabilidad Genturix*
