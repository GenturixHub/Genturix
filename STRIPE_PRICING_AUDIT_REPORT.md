# 💳 AUDITORÍA SISTEMA DE PRECIOS Y PREPARACIÓN STRIPE - GENTURIX

## Fecha: 2026-02-24
## Estado General: ⚠️ 75% LISTO PARA PRODUCCIÓN

---

## 1️⃣ FUENTE ÚNICA DE PRECIO

### ✅ Almacenamiento en Base de Datos
```javascript
// Colección: system_config
{
  "id": "global_pricing",
  "default_seat_price": 2.99,  // Precio actual configurado
  "currency": "USD",
  "updated_at": "2026-02-22T23:55:26.501302+00:00"
}
```

### ✅ Función Centralizada de Obtención de Precio
**Archivo:** `server.py:9858`
```python
async def get_effective_seat_price(condominium_id: str) -> float:
    # 1. Busca override del condominio
    # 2. Si no existe → usa precio global
    # 3. Fallback seguro → $1.50
```

### ⚠️ Valores Hardcodeados (Fallbacks)
| Constante | Valor | Uso |
|-----------|-------|-----|
| `FALLBACK_PRICE_PER_SEAT` | $1.50 | Solo si DB no tiene config |
| `DEFAULT_CURRENCY` | "USD" | Solo si DB no tiene config |
| `GENTURIX_PRICE_PER_USER` | $1.00 | ⚠️ DEPRECATED pero aún referenciado |

### 🔴 INCONSISTENCIA ENCONTRADA
**Archivo:** `server.py:10021, 10034`
```python
# En create_checkout():
metadata={
    ...
    "price_per_user": str(GENTURIX_PRICE_PER_USER)  # ❌ Usa constante deprecated
}
transaction = {
    ...
    "price_per_user": GENTURIX_PRICE_PER_USER,  # ❌ Usa constante deprecated
}
```
**Impacto:** Bajo - solo afecta metadata, no el monto cobrado.

---

## 2️⃣ MÓDULOS Y CONSISTENCIA

### ✅ Módulos que Usan Precio Dinámico Correctamente

| Endpoint | Función Usada | Estado |
|----------|---------------|--------|
| `GET /payments/pricing` | `get_condominium_pricing_info()` | ✅ |
| `POST /payments/calculate` | `calculate_subscription_price_dynamic()` | ✅ |
| `POST /payments/checkout` | `calculate_subscription_price_dynamic()` | ✅ |
| `POST /billing/upgrade-seats` | `calculate_subscription_price_dynamic()` | ✅ |
| `GET /billing/info` | `get_effective_seat_price()` | ✅ |
| `GET /super-admin/billing/overview` | `get_effective_seat_price()` | ✅ |

### ✅ Sistema de Override por Condominio
```python
# Condominios pueden tener precio especial
condo.seat_price_override = 5.00  # Precio personalizado
# Si no tiene override → usa global_pricing.default_seat_price
```

### Condominios con Override Actual
| Condominio | Precio Override |
|------------|-----------------|
| Bariloche | $1.00/seat |
| Romero | $1.00/seat |
| Terrazas | $1.00/seat |
| Cotsi | $5.00/seat |

---

## 3️⃣ PREPARACIÓN STRIPE

### ✅ Backend Calcula Monto Total
```python
# server.py:9998
pricing = await calculate_subscription_price_dynamic(user_count, condo_id)
total_amount = pricing["total"]  # ✅ Backend calcula
```

### ✅ Frontend NO Envía Monto Arbitrario
```javascript
// api.js:394
upgradeSeats = (additionalSeats, originUrl) => {
    return this.post(`/billing/upgrade-seats`, { additional_seats: additionalSeats });
    // ✅ Solo envía cantidad de seats, no precio
};
```

### ✅ Checkout Session se Crea desde Backend
```python
# server.py:10025
session = await stripe_checkout.create_checkout_session(checkout_request)
# ✅ Stripe SDK maneja la creación
```

### ⚠️ Riesgo de Manipulación
| Vector | Estado | Notas |
|--------|--------|-------|
| Monto en request | ✅ Seguro | Backend calcula |
| User count falso | ⚠️ Parcial | Se valida > 0, pero no límites máximos |
| Condo_id manipulado | ✅ Seguro | Se toma del token JWT |

---

## 4️⃣ WEBHOOK READINESS

### ✅ Endpoints de Webhook Existentes
| Endpoint | Uso |
|----------|-----|
| `POST /api/webhook/stripe` | Pagos generales |
| `POST /api/webhook/stripe-subscription` | Upgrade de seats |

### ⚠️ Validación de Firma
```python
# server.py:10114
webhook_response = await stripe_checkout.handle_webhook(body, signature)
```
**Estado:** Delegado al SDK `emergentintegrations.payments.stripe.checkout`
- El SDK recibe `signature` del header `Stripe-Signature`
- **PERO:** `STRIPE_WEBHOOK_SECRET` está VACÍO en .env

### 🔴 PROBLEMA CRÍTICO: Webhook Secret
```bash
# backend/.env
STRIPE_WEBHOOK_SECRET=   # ❌ VACÍO
```
**Impacto:** Sin webhook secret, no se puede validar que los webhooks realmente vienen de Stripe. Esto es un RIESGO DE SEGURIDAD CRÍTICO.

### ✅ Actualización de Estado Correcta
```python
# server.py:10316-10325
if webhook_response.payment_status == "paid":
    await db.condominiums.update_one(
        {"id": condo_id},
        {"$set": {"paid_seats": new_total_seats, "billing_status": "active"}}
    )
```

### ✅ Protección Demo Environment
```python
# server.py:10300-10312
if condo_environment == "demo" or condo.get("is_demo"):
    # No procesa pagos para demos
    return {"status": "success", "note": "Demo condominium - no changes applied"}
```

---

## 5️⃣ ANÁLISIS DE RIESGOS

### 🔴 RIESGOS CRÍTICOS

| # | Riesgo | Severidad | Impacto Financiero |
|---|--------|-----------|-------------------|
| 1 | Webhook sin validación de firma | 🔴 CRÍTICA | Alto - webhooks falsos podrían activar seats sin pago |
| 2 | Constante deprecated en metadata | 🟡 BAJA | Bajo - solo afecta logs |

### 🟡 RIESGOS MODERADOS

| # | Riesgo | Severidad | Mitigación |
|---|--------|-----------|------------|
| 3 | Sin límite máximo de seats por upgrade | 🟡 MEDIA | Stripe tiene límites propios |
| 4 | Transacciones billing pendientes | 🟡 MEDIA | Necesitan limpieza periódica |

### 🟢 RIESGOS BAJOS

| # | Riesgo | Severidad | Notas |
|---|--------|-----------|-------|
| 5 | Fallback hardcodeado | 🟢 BAJA | Solo si DB falla |
| 6 | Múltiples webhooks endpoints | 🟢 BAJA | Cada uno tiene propósito específico |

---

## 6️⃣ INCONSISTENCIAS ENCONTRADAS

### 1. Metadata usa constante deprecated
**Ubicación:** `server.py:10021, 10034`
```python
# Actual:
"price_per_user": str(GENTURIX_PRICE_PER_USER)  # $1.00 fijo

# Debería ser:
"price_per_user": str(pricing["price_per_seat"])  # Precio dinámico
```

### 2. Transacciones pendientes sin cleanup
```
billing_transactions con payment_status="pending" desde hace días
```

### 3. Webhook Secret no configurado
```bash
STRIPE_WEBHOOK_SECRET=  # Vacío
```

---

## 7️⃣ RECOMENDACIONES ANTES DE PRODUCCIÓN

### 🔴 CRÍTICAS (Bloquean deploy)

1. **Configurar STRIPE_WEBHOOK_SECRET**
   ```bash
   # En Stripe Dashboard > Webhooks > Endpoint > Signing secret
   STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
   ```

2. **Verificar que SDK valide firma**
   - Confirmar que `StripeCheckout.handle_webhook()` usa el secret
   - Si no, implementar validación manual con `stripe.Webhook.construct_event()`

### 🟡 IMPORTANTES (Antes de ir a producción)

3. **Corregir metadata en checkout**
   ```python
   # Cambiar línea 10021 de:
   "price_per_user": str(GENTURIX_PRICE_PER_USER)
   # A:
   "price_per_user": str(pricing["price_per_seat"])
   ```

4. **Agregar límite máximo de seats por upgrade**
   ```python
   if upgrade.additional_seats > 100:
       raise HTTPException(status_code=400, detail="Maximum 100 seats per upgrade")
   ```

5. **Limpiar transacciones pendientes antiguas**
   - Crear job para marcar como "expired" después de 24h

### 🟢 MEJORAS (Post-lanzamiento)

6. **Agregar idempotency keys** para prevenir duplicados
7. **Implementar reintentos de webhook** con backoff exponencial
8. **Dashboard de métricas de pagos** para SuperAdmin

---

## 8️⃣ PREPARACIÓN PARA STRIPE REAL

### Checklist Pre-Producción

| Item | Estado | Acción Requerida |
|------|--------|------------------|
| API Key test vs live | ⚠️ | Cambiar a `sk_live_xxx` |
| Webhook Secret | ❌ | Configurar en .env |
| Webhook endpoints registrados en Stripe | ⚠️ | Verificar en Dashboard |
| Dominio verificado en Stripe | ⚠️ | Verificar |
| Precios sincronizados | ✅ | N/A |
| Validación de firma | ❌ | Implementar/verificar |
| Logs de auditoría | ✅ | N/A |
| Demo environment protegido | ✅ | N/A |
| Backend calcula montos | ✅ | N/A |
| Frontend no envía precios | ✅ | N/A |

---

## 📊 NIVEL DE PREPARACIÓN

### Score: **75/100**

| Categoría | Puntos | Máximo |
|-----------|--------|--------|
| Arquitectura de precios | 18 | 20 |
| Seguridad webhook | 5 | 20 |
| Cálculo de montos | 20 | 20 |
| Protección demo | 15 | 15 |
| Consistencia código | 10 | 15 |
| Logging/auditoría | 7 | 10 |

### Bloqueadores para Producción:
1. ❌ **STRIPE_WEBHOOK_SECRET** no configurado
2. ❌ Verificar validación de firma en SDK

### Listo con cambios menores:
- Corregir metadata deprecated
- Agregar límites de seats

---

## 📋 CONCLUSIÓN

**El sistema de precios está bien arquitecturado** con fuente única de verdad en la base de datos y funciones centralizadas para cálculos. La integración con Stripe está parcialmente implementada.

**BLOQUEADOR PRINCIPAL:** El webhook secret no está configurado, lo que significa que cualquiera podría enviar webhooks falsos y activar seats sin pago real.

**Antes de activar Stripe real:**
1. Configurar `STRIPE_WEBHOOK_SECRET`
2. Verificar que el SDK valide firmas
3. Cambiar API key de test a live
4. Probar flujo completo con pago real de prueba

---

*Reporte generado: 2026-02-24*
*Auditoría: Sistema de Precios y Stripe*
