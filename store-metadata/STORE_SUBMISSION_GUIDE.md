# GENTURIX - Guía de Envío a Tiendas

Esta guía explica paso a paso cómo subir GENTURIX a Google Play Store y Apple App Store.

---

## 📱 GOOGLE PLAY CONSOLE

### Paso 1: Acceder a Play Console
1. Ir a https://play.google.com/console
2. Iniciar sesión con cuenta de desarrollador ($25 USD único)

### Paso 2: Crear Nueva Aplicación
1. Click en "Crear app"
2. Nombre: `GENTURIX`
3. Idioma predeterminado: `Español (Latinoamérica)`
4. Tipo: `App`
5. Gratuita/De pago: `Gratuita` (con compras in-app)

### Paso 3: Store Listing (Ficha de Play Store)

#### Información Básica
| Campo | Qué copiar |
|-------|-----------|
| Nombre de la app | `GENTURIX` |
| Descripción breve | Copiar de `/store-metadata/short-description.txt` |
| Descripción completa | Copiar contenido de `/store-metadata/playstore-description.md` (sección Long Description) |

#### Assets Gráficos
| Asset | Archivo | Ubicación |
|-------|---------|-----------|
| Icono de la app | `playstore-icon.png` | `/store-assets/icons/` |
| Gráfico de funciones | Crear 1024x500px | - |
| Screenshots teléfono | 5 imágenes | `/store-assets/screenshots/playstore/` |

#### Categorización
- **Categoría:** Tools (Herramientas)
- **Tags:** seguridad, condominio, visitantes, emergencias

### Paso 4: Política de Privacidad
1. Ir a "Contenido de la app" > "Política de privacidad"
2. URL: `https://genturix.com/privacy`

### Paso 5: Clasificación de Contenido
1. Ir a "Contenido de la app" > "Clasificación del contenido"
2. Completar cuestionario (sin violencia, sin contenido adulto)
3. Rating esperado: **Everyone (Para todos)**

### Paso 6: Configuración de la App
1. **Público objetivo:** Todos (13+)
2. **Anuncios:** No contiene anuncios
3. **Acceso a la app:** Acceso restringido (requiere cuenta)

### Paso 7: Precios y Distribución
1. **Gratuita** con suscripción in-app
2. Países: Seleccionar todos los disponibles
3. Dispositivos: Teléfonos y tablets

### Paso 8: Subir APK/AAB
1. Ir a "Producción" > "Crear nueva versión"
2. Subir archivo `.aab` (Android App Bundle)
3. Notas de la versión: Copiar de "What's New"

---

## 🍎 APP STORE CONNECT

### Paso 1: Acceder a App Store Connect
1. Ir a https://appstoreconnect.apple.com
2. Iniciar sesión con Apple Developer Account ($99 USD/año)

### Paso 2: Crear Nueva App
1. Click en "+" > "Nueva app"
2. Plataformas: `iOS`
3. Nombre: `GENTURIX`
4. Idioma principal: `Spanish (Mexico)`
5. Bundle ID: Seleccionar el registrado
6. SKU: `genturix-ios-001`

### Paso 3: App Information

#### Información General
| Campo | Qué copiar |
|-------|-----------|
| Nombre | `GENTURIX` |
| Subtítulo | `Smart Condominium Management` |
| Categoría primaria | `Utilities` |
| Categoría secundaria | `Lifestyle` |

#### URLs
| Campo | URL |
|-------|-----|
| Privacy Policy URL | `https://genturix.com/privacy` |
| Support URL | `https://genturix.com/support` |
| Marketing URL | `https://genturix.com` |

### Paso 4: Pricing and Availability
1. **Precio:** Free (Gratuita)
2. **Disponibilidad:** Todos los países
3. **Compras in-app:** Configurar suscripción mensual

### Paso 5: App Privacy
1. Ir a "App Privacy"
2. Completar cuestionario de datos recolectados:
   - ✅ Contact Info (email, phone)
   - ✅ Identifiers (user ID)
   - ✅ Location (para emergencias)
   - ✅ Usage Data (analytics)

### Paso 6: Version Information

#### Descripción
| Campo | Contenido |
|-------|-----------|
| Promotional Text | Copiar de `/store-metadata/appstore-description.md` |
| Description | Copiar sección Description del mismo archivo |
| Keywords | `condominium,security,residents,visitors,gated,community,access,control,emergency,management` |
| What's New | Copiar sección "What's New" |

#### Screenshots
| Dispositivo | Resolución | Archivos |
|-------------|------------|----------|
| iPhone 6.7" | 1290x2796 | `/store-assets/screenshots/appstore/*.png` |
| iPhone 6.5" | 1284x2778 | Mismos archivos (escalados) |
| iPhone 5.5" | 1242x2208 | Mismos archivos (escalados) |

#### App Icon
- El icono se incluye en el build de la app
- Archivo de referencia: `/store-assets/icons/ios-app-icon.png`

### Paso 7: Build
1. Subir build desde Xcode o Transporter
2. Seleccionar build en App Store Connect
3. Agregar información de cifrado (usa HTTPS estándar)

### Paso 8: App Review Information
```
Nombre: Carlos Admin
Email: support@genturix.com
Teléfono: +1 (555) 123-4567

Credenciales de prueba:
Usuario: admin@genturix.com
Contraseña: Admin123!

Notas para el revisor:
Esta app requiere una cuenta de condominio activa.
Use las credenciales de prueba proporcionadas para
acceder a todas las funcionalidades.
```

---

## ✅ CHECKLIST FINAL

### Google Play Store
- [ ] Cuenta de desarrollador creada ($25)
- [ ] Icono 1024x1024 subido
- [ ] 5 screenshots subidos
- [ ] Gráfico de funciones 1024x500 creado
- [ ] Descripción breve (80 chars) añadida
- [ ] Descripción larga añadida
- [ ] Política de privacidad URL configurada
- [ ] Clasificación de contenido completada
- [ ] AAB/APK firmado y subido
- [ ] Precios y distribución configurados

### Apple App Store
- [ ] Apple Developer Account activa ($99/año)
- [ ] App creada en App Store Connect
- [ ] Información de la app completa
- [ ] Screenshots para todos los tamaños
- [ ] Keywords optimizados (100 chars)
- [ ] App Privacy completado
- [ ] Build subido desde Xcode
- [ ] Información de revisión añadida
- [ ] Enviado para revisión

---

## 📁 ARCHIVOS DE REFERENCIA

```
/store-metadata/
├── playstore-description.md    → Textos para Google Play
├── appstore-description.md     → Textos para App Store
├── keywords.txt                → Lista de keywords
├── short-description.txt       → Descripción corta (80 chars)
├── privacy-url.txt            → URL política de privacidad
└── terms-url.txt              → URL términos de servicio

/store-assets/
├── icons/
│   ├── playstore-icon.png     → 1024x1024 (Play Store)
│   ├── ios-app-icon.png       → 1024x1024 (App Store)
│   └── apple-touch-icon.png   → 180x180 (iOS Safari)
└── screenshots/
    ├── playstore/             → 1080x1920 (5 imágenes)
    └── appstore/              → 1290x2796 (5 imágenes)
```

---

## ⏱️ TIEMPOS DE REVISIÓN ESTIMADOS

| Tienda | Tiempo de Revisión |
|--------|-------------------|
| Google Play | 1-3 días |
| App Store | 1-7 días |

---

## 🆘 SOPORTE

Si tienes problemas durante el envío:
- Google Play: https://support.google.com/googleplay/android-developer
- App Store: https://developer.apple.com/contact/

---

Documento generado: Marzo 2026
Versión: 1.0
