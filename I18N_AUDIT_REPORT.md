# GENTURIX - i18n Architecture Audit Report

**Version:** 1.0  
**Date:** February 2026  
**Scope:** Frontend Internationalization System  
**Status:** PARTIAL IMPLEMENTATION - Requires Migration

---

## Executive Summary

The GENTURIX frontend has a **partially implemented** i18n system. While the infrastructure (i18next, language persistence, LanguageSelector) exists and functions correctly, **only 18% of UI components** actually use the translation system. The remaining **82% contain hardcoded Spanish strings**.

This creates a fragmented user experience where changing the language only affects a small portion of the interface.

---

## 1. Current System State

### 1.1 Infrastructure Assessment

| Component | Status | Notes |
|-----------|--------|-------|
| i18next library | ✅ Installed | `react-i18next` properly configured |
| i18n configuration | ✅ Correct | `/src/i18n/index.js` - proper setup |
| Translation files | ✅ Exist | `es.json` (420 keys), `en.json` (420 keys) |
| Language persistence (localStorage) | ✅ Working | `userLanguage` key |
| Language persistence (Backend) | ✅ Working | `PATCH /api/profile/language` |
| LanguageSelector component | ✅ Working | Updates both localStorage and DB |
| Re-render on language change | ✅ Working | `bindI18n: 'languageChanged loaded'` |

### 1.2 Translation File Structure

**Current Namespaces:**
```
common, auth, nav, profile, settings, users, rrhh, 
reservations, security, audit, dashboard, errors, roles, time
```

**Assessment:** Structure is logical but incomplete. Missing namespaces for:
- `guard` (GuardUI module)
- `resident` (ResidentUI module)
- `superadmin` (SuperAdminDashboard)
- `visitors` (Visitor management)
- `payments` (Payment module)
- `emergency` (Panic button, alerts)
- `forms` (Common form fields)
- `validation` (Form validation messages)

### 1.3 Component Coverage Analysis

| Category | With i18n | Without i18n | Coverage |
|----------|-----------|--------------|----------|
| Pages | 4 | 13 | **24%** |
| Components | 4 | 32+ | **11%** |
| Features | 0 | 4 | **0%** |
| **Total** | **8** | **36+** | **18%** |

---

## 2. Files with Hardcoded Strings

### 2.1 Critical Pages (High User Traffic)

| File | Strings Found | Priority |
|------|---------------|----------|
| `/pages/GuardUI.js` | 150+ | P0 |
| `/pages/ResidentUI.js` | 100+ | P0 |
| `/pages/SuperAdminDashboard.js` | 200+ | P0 |
| `/pages/UserManagementPage.js` | 80+ | P1 |
| `/pages/SecurityModule.js` | 60+ | P1 |
| `/pages/AuditModule.js` | 40+ | P1 |
| `/pages/PaymentsModule.js` | 30+ | P1 |
| `/pages/DashboardPage.js` | 25+ | P1 |
| `/pages/ProfilePage.js` | 40+ | P1 |
| `/pages/OnboardingWizard.js` | 50+ | P2 |
| `/pages/PanelSelectionPage.js` | 15+ | P2 |
| `/pages/JoinPage.js` | 20+ | P2 |
| `/pages/ResetPasswordPage.jsx` | 15+ | P2 |

### 2.2 Critical Components

| File | Strings Found | Priority |
|------|---------------|----------|
| `/components/VisitorCheckInGuard.jsx` | 100+ | P0 |
| `/components/VisitorAuthorizationsResident.jsx` | 60+ | P0 |
| `/components/ResidentVisitHistory.jsx` | 40+ | P1 |
| `/components/ProfileDirectory.jsx` | 20+ | P1 |
| `/components/GuardHistoryVisual.jsx` | 30+ | P1 |
| `/components/InstallChoiceScreen.jsx` | 15+ | P2 |
| `/components/ChangePasswordForm.jsx` | 20+ | P2 |
| `/components/PushNotificationBanner.js` | 10+ | P2 |

### 2.3 Feature Modules

| File | Strings Found | Priority |
|------|---------------|----------|
| `/features/resident/ResidentHome.jsx` | 50+ | P0 |
| `/features/resident/ResidentLayout.jsx` | 10+ | P1 |
| `/components/DynamicEmergencyButtons.jsx` | 20+ | P0 |
| `/components/PremiumPanicButton.jsx` | 10+ | P0 |

### 2.4 Sample Hardcoded Strings (Evidence)

```javascript
// GuardUI.js:639
placeholder="Buscar visitante, placa, empresa..."

// SuperAdminDashboard.js:945
title="Crear Administrador"

// VisitorCheckInGuard.jsx:569
placeholder="Nombre completo"

// ResidentHome.jsx (DynamicEmergencyButtons)
confirmText: '¿Deseas enviar una alerta general?'
```

---

## 3. Architectural Issues Detected

### 3.1 Critical Issues

| ID | Issue | Impact |
|----|-------|--------|
| I-001 | **82% of components don't import useTranslation** | Language change has minimal visible effect |
| I-002 | **Backend returns Spanish-only messages** | Error/success messages not translatable |
| I-003 | **Toast messages hardcoded in components** | Notifications ignore language setting |
| I-004 | **Form placeholders hardcoded** | Input hints in Spanish only |
| I-005 | **Alert/Dialog content hardcoded** | Confirmation dialogs in Spanish only |

### 3.2 Backend Message Examples (Spanish-fixed)

```python
# server.py:3427
"message": "Contraseña actualizada exitosamente"

# server.py:3386
detail="Contraseña actual incorrecta"

# server.py:3558
"message": "Suscripción actualizada"

# server.py:1818
detail="Condominio no encontrado"
```

### 3.3 Missing Translation Keys

Categories not covered in current translation files:
- Emergency button labels and confirmations
- Visitor management forms
- Guard check-in/check-out flows
- SuperAdmin condominium management
- Payment/billing messages
- Push notification messages
- Service Worker update prompts

---

## 4. Risk Assessment

### 4.1 Business Risks

| Risk | Severity | Description |
|------|----------|-------------|
| User Experience | HIGH | Foreign residents cannot use the app effectively |
| Market Expansion | HIGH | Cannot sell to non-Spanish markets |
| Support Load | MEDIUM | Increased support tickets from non-Spanish users |
| Brand Perception | MEDIUM | Appears unprofessional/incomplete |

### 4.2 Technical Risks

| Risk | Severity | Description |
|------|----------|-------------|
| Maintenance | MEDIUM | Dual effort needed (code + translation files) |
| Consistency | MEDIUM | Same text may be translated differently in different files |
| Testing | LOW | Language switching tests may pass but UX fails |

---

## 5. Migration Plan

### Phase 1: Infrastructure Preparation (1-2 days)

**Tasks:**
1. Extend translation files with missing namespaces
2. Create translation key naming convention document
3. Add missing common keys (placeholders, validations, etc.)

**New Namespaces to Add:**
```json
{
  "guard": { ... },
  "resident": { ... },
  "visitors": { ... },
  "emergency": { ... },
  "payments": { ... },
  "superadmin": { ... },
  "forms": {
    "placeholders": { ... },
    "validation": { ... },
    "labels": { ... }
  }
}
```

### Phase 2: Critical Path Migration (3-5 days)

**Priority Order:**
1. `DynamicEmergencyButtons.jsx` - Emergency flow
2. `ResidentHome.jsx` - Main resident view
3. `GuardUI.js` - Main guard view
4. `VisitorCheckInGuard.jsx` - Visitor flow
5. `VisitorAuthorizationsResident.jsx` - Authorization flow

**Pattern for each file:**
```javascript
// 1. Add import
import { useTranslation } from 'react-i18next';

// 2. Initialize hook in component
const { t } = useTranslation();

// 3. Replace hardcoded strings
// Before: placeholder="Nombre completo"
// After:  placeholder={t('forms.placeholders.fullName')}
```

### Phase 3: Secondary Modules (3-5 days)

**Files:**
- `SuperAdminDashboard.js`
- `UserManagementPage.js`
- `SecurityModule.js`
- `AuditModule.js`
- `PaymentsModule.js`
- `ProfilePage.js`

### Phase 4: Remaining Components (2-3 days)

**Files:**
- All remaining components in `/components/`
- PWA-related components
- Form components

### Phase 5: Backend Message Codes (2-3 days)

**Approach:** Replace Spanish strings with error codes, handle translation in frontend.

**Before:**
```python
raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
```

**After:**
```python
raise HTTPException(status_code=400, detail="PASSWORD_INCORRECT")
```

**Frontend:**
```javascript
const errorMessages = {
  PASSWORD_INCORRECT: t('errors.passwordIncorrect'),
  // ...
};
```

---

## 6. Recommendations

### 6.1 Immediate Actions

1. **Do NOT add new features** without i18n until migration is complete
2. **Freeze Spanish strings** in all new code
3. **Create i18n linting rule** to flag hardcoded strings in JSX

### 6.2 Scalability for 5+ Languages

**Current structure supports expansion:**
```
/src/i18n/
├── index.js          # Configuration
├── es.json           # Spanish (default)
├── en.json           # English
├── pt.json           # Portuguese (future)
├── fr.json           # French (future)
└── de.json           # German (future)
```

**Required changes for scaling:**
1. Split large JSON files by namespace (optional but recommended)
2. Add lazy loading for non-default languages
3. Consider professional translation service integration

### 6.3 Key Naming Convention

**Recommended pattern:**
```
{namespace}.{section}.{element}

Examples:
guard.visitors.searchPlaceholder
resident.emergency.confirmAlert
forms.validation.required
errors.api.notFound
```

### 6.4 Quality Assurance

1. Add Storybook stories with language toggle
2. Create E2E tests that verify key UI elements in both languages
3. Implement missing translation detection in CI/CD

---

## 7. Effort Estimation

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1 | 8-12 hours | None |
| Phase 2 | 20-30 hours | Phase 1 |
| Phase 3 | 20-30 hours | Phase 1 |
| Phase 4 | 12-16 hours | Phase 1 |
| Phase 5 | 16-24 hours | Phase 1 |
| **Total** | **76-112 hours** | |

---

## 8. Files Inventory

### Files WITHOUT i18n (Need Migration)

```
/pages/
├── SchoolModule.js
├── ProfilePage.js
├── JoinPage.js
├── ResetPasswordPage.jsx
├── SecurityModule.js
├── GuardUI.js
├── AuditModule.js
├── SuperAdminDashboard.js
├── PaymentsModule.js
├── DashboardPage.js
├── ResidentUI.js
├── PanelSelectionPage.js
├── OnboardingWizard.js
├── StudentUI.js
└── UserManagementPage.js

/components/
├── VisitorCheckInGuard.jsx
├── VisitorAuthorizationsResident.jsx
├── ResidentVisitHistory.jsx
├── ProfileDirectory.jsx
├── GuardHistoryVisual.jsx
├── InstallChoiceScreen.jsx
├── ChangePasswordForm.jsx
├── PushNotificationBanner.js
├── DynamicEmergencyButtons.jsx
└── PremiumPanicButton.jsx

/features/resident/
├── ResidentHome.jsx
└── ResidentLayout.jsx
```

### Files WITH i18n (Reference)

```
/pages/
├── CondominiumSettingsPage.js ✅
├── ReservationsModule.js ✅
├── RRHHModule.js ✅
└── LoginPage.js ✅

/components/
├── DashboardLayout.js ✅
├── Sidebar.js ✅
├── EmbeddedProfile.jsx ✅
└── LanguageSelector.jsx ✅
```

---

## Conclusion

The GENTURIX i18n infrastructure is correctly implemented but severely underutilized. A systematic migration is required to achieve full internationalization. The estimated effort is **76-112 hours** spread across 5 phases.

**Recommended approach:** Start with Phase 2 (Critical Path) immediately, as it covers the most user-facing components and will provide immediate visible improvement when users change language.

---

*Document generated: February 2026*  
*Audit scope: Frontend i18n system*
