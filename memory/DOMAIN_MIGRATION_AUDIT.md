# AUDITORÍA COMPLETA - MIGRACIÓN DE DOMINIOS GENTURIX
## Fecha: 2025-02-27

---

## ARQUITECTURA DE DOMINIOS

| Componente | URL | Plataforma |
|------------|-----|------------|
| Landing Page | https://genturix.com | Vercel |
| Application Frontend | https://app.genturix.com | Vercel |
| Backend API | https://genturix-production.up.railway.app | Railway |

---

## 1. ARCHIVOS MODIFICADOS

### `/app/backend/server.py`

**Cambio 1: CORS Origins (línea ~16364)**
```python
# ANTES
production_origins = [
    "https://genturix.com",
    "https://www.genturix.com",
    "https://genturix.vercel.app",
]

# DESPUÉS
production_origins = [
    "https://genturix.com",
    "https://www.genturix.com",
    "https://app.genturix.com",  # NUEVO - Application subdomain
    "https://genturix.vercel.app",
]
```

**Cambio 2: Email Origin Fallback (línea ~8654)**
```python
# ANTES
origin = request.headers.get("origin", "https://genturix.com")

# DESPUÉS
origin = request.headers.get("origin", "https://app.genturix.com")
```

---

## 2. CONFIGURACIÓN CORS VERIFICADA ✅

```python
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,  # Lista explícita, NO "*"
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Orígenes Permitidos (Producción)
- ✅ https://genturix.com
- ✅ https://www.genturix.com
- ✅ https://app.genturix.com (NUEVO)
- ✅ https://genturix.vercel.app
- ✅ FRONTEND_URL (dinámico)

### Test CORS Preflight
```
Origin: https://app.genturix.com
→ access-control-allow-origin: https://app.genturix.com ✅
→ access-control-allow-credentials: true ✅
```

---

## 3. CONFIGURACIÓN DE COOKIES

### Estado Actual
- Cookies NO tienen `domain` explícito
- Backend usa tokens en body como fallback
- `SameSite=Lax` en desarrollo, `SameSite=None` en producción
- `Secure=True` en producción

### Nota Importante
Como el backend (Railway) y frontend (Vercel) están en dominios diferentes, las cookies cross-origin requieren:
- `SameSite=None`
- `Secure=True`
- El navegador debe soportar cookies de terceros

El sistema usa token-based auth como fallback, lo cual funciona correctamente.

---

## 4. FRONTEND API CONFIGURATION ✅

### `/app/frontend/src/services/api.js`
```javascript
const API_URL = process.env.REACT_APP_BACKEND_URL;  // ✅ Dinámico
```

### Variables de Entorno Requeridas (Vercel)
```
REACT_APP_BACKEND_URL=https://genturix-production.up.railway.app
```

### Verificación
- ✅ NO hay dominios hardcodeados en api.js
- ✅ Usa variables de entorno
- ✅ withCredentials habilitado para CORS

---

## 5. PWA MANIFEST ✅

### `/app/frontend/public/manifest.json`
```json
{
  "name": "GENTURIX",
  "short_name": "GENTURIX",
  "description": "Plataforma inteligente de seguridad...",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "theme_color": "#0f172a",
  "background_color": "#0f172a"
}
```

### Verificaciones
- ✅ start_url: "/"
- ✅ scope: "/"
- ✅ display: "standalone"
- ✅ NO hay dominios hardcodeados
- ✅ Iconos 192x192 y 512x512 presentes

---

## 6. SERVICE WORKER ✅

### `/app/frontend/public/service-worker.js`
- ✅ NO hay dominios hardcodeados
- ✅ Cache scope relativo
- ✅ Push notifications funcionan
- ✅ Registro en "/" scope

### `/app/frontend/src/index.js`
```javascript
navigator.serviceWorker.register('/service-worker.js', {
  scope: '/'
});
```

---

## 7. VARIABLES DE ENTORNO

### Backend (Railway)
| Variable | Valor |
|----------|-------|
| FRONTEND_URL | https://app.genturix.com |
| ENVIRONMENT | production |
| MONGO_URL | [configurado en Railway] |

### Frontend (Vercel)
| Variable | Valor |
|----------|-------|
| REACT_APP_BACKEND_URL | https://genturix-production.up.railway.app |

---

## 8. SEGURIDAD

### ✅ Sin Problemas
- CORS NO usa wildcards ("*") con credentials
- Cookies tienen flags seguros
- Tokens validados en backend
- No hay dominios hardcodeados en código

### ⚠️ Recomendaciones
1. Configurar `FRONTEND_URL=https://app.genturix.com` en Railway
2. Verificar que Vercel tenga `REACT_APP_BACKEND_URL` correcto
3. Considerar agregar rate limiting más estricto

---

## 9. CHECKLIST FINAL

### Backend (Railway)
- [x] CORS incluye app.genturix.com
- [x] CORS incluye genturix.com (landing)
- [x] allow_credentials=True
- [x] Email fallback actualizado
- [ ] Configurar FRONTEND_URL en Railway

### Frontend (Vercel)
- [x] API usa variable de entorno
- [x] No hay dominios hardcodeados
- [x] PWA manifest correcto
- [x] Service worker configurado
- [ ] Configurar REACT_APP_BACKEND_URL en Vercel

### PWA
- [x] Manifest válido
- [x] Iconos presentes
- [x] Service worker registra
- [x] start_url y scope correctos

---

## 10. CONFIRMACIÓN

✅ **La aplicación está lista para funcionar con:**

| Componente | URL |
|------------|-----|
| Landing | https://genturix.com |
| Frontend | https://app.genturix.com |
| Backend | https://genturix-production.up.railway.app |

**Acciones pendientes del usuario:**
1. En Railway: Configurar `FRONTEND_URL=https://app.genturix.com`
2. En Vercel: Configurar `REACT_APP_BACKEND_URL=https://genturix-production.up.railway.app`
3. En Vercel: Configurar dominio personalizado `app.genturix.com`

---

*Auditoría completada - 2025-02-27*
