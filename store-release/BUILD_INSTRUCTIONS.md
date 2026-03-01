# GENTURIX - Build Instructions

Esta guía explica cómo generar los builds nativos para Android e iOS.

---

## Prerrequisitos

### Para Android
- Java JDK 17+
- Android Studio (Arctic Fox o superior)
- Android SDK 33+
- Gradle 8+

### Para iOS
- macOS con Xcode 15+
- CocoaPods
- Apple Developer Account ($99/año)

---

## 1. PREPARACIÓN

### Actualizar web assets
Cada vez que hagas cambios en el frontend:

```bash
cd /app/frontend

# 1. Build del frontend
yarn build

# 2. Sincronizar con plataformas nativas
npx cap sync
```

---

## 2. ANDROID - Generar APK

### Opción A: Usando Android Studio (Recomendado)

1. Abrir proyecto en Android Studio:
```bash
cd /app/frontend
npx cap open android
```

2. En Android Studio:
   - `Build` > `Build Bundle(s) / APK(s)` > `Build APK(s)`
   - El APK se genera en: `android/app/build/outputs/apk/debug/app-debug.apk`

### Opción B: Usando línea de comandos

```bash
cd /app/frontend/android

# APK Debug (para pruebas)
./gradlew assembleDebug

# Ubicación del APK:
# android/app/build/outputs/apk/debug/app-debug.apk
```

---

## 3. ANDROID - Generar AAB (Play Store)

El AAB (Android App Bundle) es el formato requerido por Google Play Store.

### Paso 1: Crear Keystore (solo primera vez)

```bash
keytool -genkey -v -keystore genturix-release.keystore \
  -alias genturix \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000
```

**¡IMPORTANTE!** Guarda el keystore y contraseñas de forma segura. Los necesitarás para todas las actualizaciones futuras.

### Paso 2: Configurar signing en gradle

Crear archivo `android/keystore.properties`:
```properties
storePassword=TU_STORE_PASSWORD
keyPassword=TU_KEY_PASSWORD
keyAlias=genturix
storeFile=../genturix-release.keystore
```

### Paso 3: Actualizar build.gradle

Editar `android/app/build.gradle`, agregar antes de `android {`:
```gradle
def keystorePropertiesFile = rootProject.file("keystore.properties")
def keystoreProperties = new Properties()
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}
```

Dentro de `android {`, agregar:
```gradle
signingConfigs {
    release {
        keyAlias keystoreProperties['keyAlias']
        keyPassword keystoreProperties['keyPassword']
        storeFile file(keystoreProperties['storeFile'])
        storePassword keystoreProperties['storePassword']
    }
}

buildTypes {
    release {
        signingConfig signingConfigs.release
        minifyEnabled true
        proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
    }
}
```

### Paso 4: Generar AAB

```bash
cd /app/frontend/android

# Build release AAB
./gradlew bundleRelease

# Ubicación del AAB:
# android/app/build/outputs/bundle/release/app-release.aab
```

---

## 4. iOS - Generar IPA

### Paso 1: Abrir en Xcode

```bash
cd /app/frontend
npx cap open ios
```

### Paso 2: Configurar Signing

1. En Xcode, selecciona el proyecto "App" en el navegador
2. Ve a "Signing & Capabilities"
3. Selecciona tu Team (Apple Developer Account)
4. Xcode generará automáticamente los certificados

### Paso 3: Configurar Push Notifications (Capabilities)

1. En "Signing & Capabilities", click "+" 
2. Agregar "Push Notifications"
3. Agregar "Background Modes" > Check "Remote notifications"

### Paso 4: Build para Device (Testing)

1. Conecta un iPhone/iPad
2. Selecciónalo como destino en Xcode
3. `Product` > `Build` (⌘B)
4. `Product` > `Run` (⌘R)

### Paso 5: Archive para App Store

1. Selecciona "Any iOS Device" como destino
2. `Product` > `Archive`
3. En Organizer, selecciona el archive
4. Click "Distribute App"
5. Selecciona "App Store Connect"
6. Sigue el wizard para subir a TestFlight/App Store

---

## 5. PUSH NOTIFICATIONS - Configuración

### Android (Firebase Cloud Messaging)

1. Crear proyecto en [Firebase Console](https://console.firebase.google.com)
2. Agregar app Android con package name: `com.genturix.app`
3. Descargar `google-services.json`
4. Copiar a: `android/app/google-services.json`

### iOS (APNs)

1. En [Apple Developer Portal](https://developer.apple.com):
   - Certificates, IDs & Profiles > Keys
   - Crear nueva key con "Apple Push Notifications service (APNs)"
   - Descargar el archivo .p8

2. Configurar en tu backend con:
   - Key ID
   - Team ID
   - Bundle ID: `com.genturix.app`

---

## 6. VERSIONING

### Android
Editar `android/app/build.gradle`:
```gradle
android {
    defaultConfig {
        versionCode 1        // Incrementar con cada release
        versionName "1.0.0"  // Versión visible
    }
}
```

### iOS
En Xcode, editar Info.plist o en General:
- Version: `1.0.0`
- Build: `1`

---

## 7. COMANDOS ÚTILES

```bash
# Sincronizar cambios web con apps nativas
npx cap sync

# Solo copiar web assets (sin actualizar plugins)
npx cap copy

# Abrir Android Studio
npx cap open android

# Abrir Xcode
npx cap open ios

# Ver información de configuración
npx cap doctor

# Actualizar Capacitor
npx cap update
```

---

## 8. ESTRUCTURA DE ARCHIVOS

```
/app/frontend/
├── android/                      # Proyecto Android nativo
│   ├── app/
│   │   ├── build.gradle         # Configuración de build
│   │   ├── google-services.json # Firebase (agregar manualmente)
│   │   └── src/main/
│   │       ├── AndroidManifest.xml
│   │       ├── res/             # Recursos (iconos, splash)
│   │       └── assets/public/   # Web assets (generado)
│   └── keystore.properties      # Credenciales de firma (crear)
│
├── ios/                          # Proyecto iOS nativo
│   └── App/
│       ├── App/
│       │   ├── Assets.xcassets/ # Iconos y splash
│       │   └── public/          # Web assets (generado)
│       └── App.xcodeproj        # Proyecto Xcode
│
├── capacitor.config.json         # Configuración de Capacitor
└── build/                        # Frontend compilado
```

---

## 9. TROUBLESHOOTING

### Android: "SDK location not found"
Crear `android/local.properties`:
```properties
sdk.dir=/Users/USERNAME/Library/Android/sdk
```

### iOS: "No signing certificate"
- Asegúrate de tener Apple Developer Account activa
- En Xcode: Preferences > Accounts > agregar tu Apple ID

### Push no funciona
- Android: Verificar `google-services.json` existe
- iOS: Verificar capability "Push Notifications" está habilitado
- Ambos: Verificar que el backend envía al token correcto

### Web assets desactualizados
```bash
yarn build && npx cap sync
```

---

## 10. CHECKLIST PRE-RELEASE

### Android
- [ ] Version code incrementado
- [ ] Keystore configurado
- [ ] `google-services.json` agregado
- [ ] Proguard configurado
- [ ] AAB generado y firmado
- [ ] Probado en dispositivo real

### iOS
- [ ] Version y Build incrementados
- [ ] Signing configurado
- [ ] Push Notifications capability
- [ ] Archive creado
- [ ] Probado en dispositivo real
- [ ] Screenshots actualizados

---

Documento generado: Marzo 2026
Capacitor version: 6.x
