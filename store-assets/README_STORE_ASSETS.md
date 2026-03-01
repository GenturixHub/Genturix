# GENTURIX - Store Assets

Este directorio contiene todos los assets necesarios para publicar Genturix en Google Play Store y Apple App Store.

## Estructura de Directorios

```
/store-assets
├── /icons                    # Iconos de la aplicación
├── /screenshots
│   ├── /playstore           # Screenshots para Google Play (1080x1920)
│   └── /appstore            # Screenshots para Apple App Store (1290x2796)
├── /playstore               # Assets específicos de Play Store
├── /appstore                # Assets específicos de App Store
└── README_STORE_ASSETS.md   # Este archivo
```

---

## ICONOS

### Ubicación: `/store-assets/icons/`

| Archivo | Tamaño | Uso |
|---------|--------|-----|
| `playstore-icon.png` | 1024x1024 | Google Play Store - Icono principal |
| `ios-app-icon.png` | 1024x1024 | Apple App Store - Icono principal |
| `icon-512.png` | 512x512 | PWA / Play Store |
| `icon-192.png` | 192x192 | PWA manifest |
| `apple-touch-icon.png` | 180x180 | iOS Safari / Home screen |
| `notification-icon.png` | 96x96 | Push notifications |
| `notification-badge.png` | 72x72 | Badge de notificación |

### Cómo subir iconos:

**Google Play Console:**
1. Ve a `Store presence > Main store listing`
2. En `App icon`, sube `playstore-icon.png` (1024x1024)

**App Store Connect:**
1. Ve a `App Information > App Icon`
2. Sube `ios-app-icon.png` (1024x1024)

---

## SCREENSHOTS

### Google Play Store
**Resolución:** 1080x1920 (Phone)
**Ubicación:** `/store-assets/screenshots/playstore/`

Capturas recomendadas:
1. `01-login.png` - Pantalla de inicio de sesión
2. `02-emergencia.png` - Botón de pánico (característica principal)
3. `03-dashboard.png` - Dashboard de administrador
4. `04-usuarios.png` - Gestión de usuarios
5. `05-guardia.png` - Panel de guardia con alertas

### Apple App Store
**Resolución:** 1290x2796 (iPhone 14 Pro Max)
**Ubicación:** `/store-assets/screenshots/appstore/`

Capturas recomendadas:
1. `01-login.png` - Pantalla de login
2. `02-emergencia.png` - Sistema de emergencia
3. `03-dashboard.png` - Panel de control
4. `04-usuarios.png` - Administración de usuarios
5. `05-seguridad.png` - Panel de seguridad (guardia)

### Cómo capturar screenshots:

```bash
# Usando la app en vivo, navegar a:
# Login: /login
# Residente (Pánico): /resident
# Dashboard Admin: /admin/dashboard
# Usuarios: /admin/users
# Guardia: /guard

# Credenciales de prueba:
# Residente: test-resident@genturix.com / Admin123!
# Admin: admin@genturix.com / Admin123!
# Guardia: guarda1@genturix.com / Guard123!
```

---

## MANIFEST.JSON ACTUALIZADO

El archivo `/frontend/public/manifest.json` ha sido actualizado con:

- ✅ Icono 192x192
- ✅ Icono 512x512
- ✅ Icono maskable (para Android adaptive icons)
- ✅ Icono monochrome (72x72 para badges)
- ✅ Apple-touch-icon (180x180)
- ✅ Shortcuts para acceso rápido (Emergencia, Dashboard)

---

## CHECKLIST PARA PUBLICACIÓN

### Google Play Store
- [ ] Subir icono 1024x1024 (`playstore-icon.png`)
- [ ] Subir 5 screenshots (1080x1920)
- [ ] Completar Store Listing (descripción, categoría)
- [ ] Configurar contenido del juego/app
- [ ] Firmar APK/AAB
- [ ] Configurar precios y distribución

### Apple App Store
- [ ] Subir icono 1024x1024 (`ios-app-icon.png`)
- [ ] Subir screenshots para iPhone 14 Pro Max (1290x2796)
- [ ] Completar App Information
- [ ] Configurar App Privacy
- [ ] Subir build firmado
- [ ] Completar revisión de la app

---

## TEXTOS PARA LAS TIENDAS

### Nombre de la App
`GENTURIX`

### Subtítulo (App Store) / Descripción corta (Play Store)
`Seguridad y gestión de emergencias para condominios`

### Descripción Larga

```
GENTURIX es la plataforma líder de seguridad para condominios y comunidades residenciales.

CARACTERÍSTICAS PRINCIPALES:

🚨 BOTÓN DE PÁNICO
- Alerta instantánea a guardias y administración
- Geolocalización automática
- Múltiples tipos de emergencia (médica, seguridad, general)

👥 GESTIÓN DE VISITANTES
- Pre-autorización de visitantes
- Códigos QR de acceso
- Historial completo de visitas

🔐 CONTROL DE ACCESO
- Registro de entradas y salidas
- Verificación de identidad
- Alertas en tiempo real

📊 PANEL DE ADMINISTRACIÓN
- Gestión de usuarios por roles
- Métricas y estadísticas
- Auditoría de eventos

💼 PARA ADMINISTRADORES
- Multi-condominio
- Facturación integrada
- Reportes personalizados

ROLES SOPORTADOS:
• SuperAdmin - Gestión global
• Administrador - Control del condominio
• Guardia - Seguridad y accesos
• Residente - Emergencias y visitantes

$1 USD por usuario/mes
Prueba gratuita disponible
```

### Palabras clave
`seguridad, condominio, emergencias, pánico, visitantes, guardias, acceso, residencial`

### Categoría
- **Play Store:** Tools / Business
- **App Store:** Utilities / Lifestyle

---

## NOTAS IMPORTANTES

1. **PWA ya funcional**: La app ya funciona como PWA y puede instalarse desde el navegador.

2. **Íconos existentes**: Los iconos en `/frontend/public/icons/` son los que usa la PWA actualmente. Los nuevos iconos en `/store-assets/icons/` son para las tiendas.

3. **No modificar backend**: Estos assets son solo para publicación. No se requieren cambios en la lógica de la aplicación.

4. **Privacidad y Términos**: Las páginas `/privacy` y `/terms` ya están creadas y son accesibles públicamente como lo requieren las tiendas.

---

Generado: Marzo 2026
Versión: 1.0
