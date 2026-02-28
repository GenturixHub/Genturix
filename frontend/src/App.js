import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { QueryClient } from '@tanstack/react-query';
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import { createQueryPersister, persistOptions } from './config/queryPersister';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ModulesProvider, useModules } from './contexts/ModulesContext';
import { Toaster } from './components/ui/sonner';
import { toast } from 'sonner';
import LoginPage from './pages/LoginPage';
import PanelSelectionPage from './pages/PanelSelectionPage';
import DashboardPage from './pages/DashboardPage';
import SecurityModule from './pages/SecurityModule';
import RRHHModule from './pages/RRHHModule';
import SchoolModule from './pages/SchoolModule';
import AdminBillingPage from './pages/AdminBillingPage';
import AuditModule from './pages/AuditModule';
import ReservationsModule from './pages/ReservationsModule';
// Resident module - independent mobile-first layout
import { ResidentHome } from './features/resident';
import GuardUI from './pages/GuardUI';
import StudentUI from './pages/StudentUI';
import SuperAdminDashboard from './pages/SuperAdminDashboard';
import OnboardingWizard from './pages/OnboardingWizard';
import FinancialPortfolioPage from './pages/FinancialPortfolioPage';
import UserManagementPage from './pages/UserManagementPage';
import ProfilePage from './pages/ProfilePage';
import JoinPage from './pages/JoinPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import CondominiumSettingsPage from './pages/CondominiumSettingsPage';
import UpdateAvailableModal from './components/UpdateAvailableModal';
import InstallChoiceScreen from './components/InstallChoiceScreen';
import useServiceWorkerUpdate from './hooks/useServiceWorkerUpdate';
import usePWAInstall from './hooks/usePWAInstall';
import './App.css';

// TanStack Query Client Configuration
// Keys that should NOT be persisted (real-time critical data)
const shouldDehydrateQuery = (query) => {
  const queryKey = query.queryKey;
  if (!queryKey || !Array.isArray(queryKey)) return true;
  
  const keyString = queryKey.join('.');
  // Exclude guard data, alerts, and real-time status from persistence
  const excludePatterns = ['guard', 'alerts', 'clockStatus', 'unreadCount'];
  return !excludePatterns.some(pattern => keyString.includes(pattern));
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60_000,      // Data considered fresh for 5 minutes
      gcTime: 7 * 24 * 60 * 60_000, // Garbage collection after 7 days (match persist maxAge)
      refetchOnWindowFocus: true, // Refetch when user returns to app
      retry: 1,
      refetchOnMount: 'always',   // Always check for fresh data on mount (background refetch)
    },
    dehydrate: {
      shouldDehydrateQuery,      // Filter which queries get persisted
    },
  },
});

// Create persister for localStorage cache
const persister = createQueryPersister();

// Suppress PostHog errors in development
if (typeof window !== 'undefined') {
  const originalPostMessage = window.postMessage;
  window.postMessage = function(...args) {
    try {
      return originalPostMessage.apply(this, args);
    } catch (e) {
      if (e.name === 'DataCloneError') {
        console.warn('PostMessage DataCloneError suppressed');
        return;
      }
      throw e;
    }
  };
}

// Role-based redirect component
const RoleBasedRedirect = () => {
  const { user, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isLoading) return;
    
    if (!user) {
      navigate('/login');
      return;
    }

    const roles = user.roles || [];
    
    // Check for Super Admin first
    if (roles.includes('SuperAdmin')) {
      navigate('/super-admin');
      return;
    }
    
    // Check for specific single roles first - direct to their dedicated UI
    if (roles.length === 1) {
      const role = roles[0];
      switch (role) {
        case 'Residente':
          navigate('/resident');
          return;
        case 'Guarda':
          navigate('/guard');
          return;
        case 'Estudiante':
          navigate('/student');
          return;
        case 'Administrador':
          navigate('/admin/dashboard');
          return;
        case 'Supervisor':
          navigate('/rrhh');
          return;
        case 'HR':
          navigate('/rrhh');
          return;
        default:
          navigate('/select-panel');
      }
    } else if (roles.length > 1) {
      // Multiple roles - show panel selection
      navigate('/select-panel');
    }
  }, [user, isLoading, navigate]);

  return (
    <div className="min-h-screen bg-[#05050A] flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children, allowedRoles = [] }) => {
  const { isAuthenticated, isLoading, user, hasAnyRole } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles.length > 0 && !hasAnyRole(...allowedRoles)) {
    return <Navigate to="/" replace />;
  }

  return children;
};

// Module Protected Route - Validates both role AND module availability
const ModuleProtectedRoute = ({ children, allowedRoles = [], moduleId }) => {
  const { isAuthenticated, isLoading, user, hasAnyRole } = useAuth();
  const { isModuleEnabled, isLoading: modulesLoading } = useModules();
  const location = useLocation();

  if (isLoading || modulesLoading) {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles.length > 0 && !hasAnyRole(...allowedRoles)) {
    return <Navigate to="/" replace />;
  }

  // Check if module is enabled
  if (moduleId && !isModuleEnabled(moduleId)) {
    // Show toast notification
    toast.error('Módulo no disponible', {
      description: 'Este módulo está desactivado para tu condominio.',
    });
    return <Navigate to="/admin/dashboard" replace state={{ from: location }} />;
  }

  return children;
};

// Public Route Component
const PublicRoute = ({ children }) => {
  const { isAuthenticated, isLoading, passwordResetRequired } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // CRITICAL: If password reset is required, keep user on login page
  // This allows the PasswordChangeDialog to appear
  if (isAuthenticated && passwordResetRequired) {
    return children;
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return children;
};

// Profile Page with Guard Redirect
// Guards should NEVER access the global ProfilePage - they have embedded profile in GuardUI
const ProfilePageOrRedirect = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const roles = user?.roles || [];
  
  // If user is a Guard (and ONLY a Guard), redirect to GuardUI with profile tab
  // Guards have their own embedded profile and should never see the global ProfilePage
  useEffect(() => {
    if (roles.length === 1 && roles[0] === 'Guarda') {
      // Redirect to guard panel - the guard can use the bottom nav to access profile
      navigate('/guard?tab=profile', { replace: true });
    }
  }, [roles, navigate]);
  
  // If Guard, show loading while redirecting
  if (roles.length === 1 && roles[0] === 'Guarda') {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Redirigiendo al panel de guardia...</p>
        </div>
      </div>
    );
  }
  
  // For all other roles, show the normal ProfilePage
  return <ProfilePage />;
};

// Install Gate Route - decides whether to show install screen
const InstallGateRoute = () => {
  const { 
    shouldShowInstallGate, 
    isInstallable, 
    promptInstall, 
    chooseWeb 
  } = usePWAInstall();
  const { isAuthenticated } = useAuth();

  // If user is already authenticated, go to role-based redirect
  if (isAuthenticated) {
    return <RoleBasedRedirect />;
  }

  // If should show install gate (not installed, no previous choice, installable)
  if (shouldShowInstallGate) {
    return (
      <InstallChoiceScreen 
        onInstall={promptInstall}
        onContinueWeb={chooseWeb}
        isInstallable={isInstallable}
      />
    );
  }

  // Otherwise, redirect to login or role-based redirect
  return <RoleBasedRedirect />;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Install Gate - shown on root if conditions met */}
      <Route path="/install" element={<InstallGateRoute />} />
      
      {/* Public Routes */}
      <Route path="/login" element={
        <PublicRoute>
          <LoginPage />
        </PublicRoute>
      } />
      
      {/* Public Join/Access Request Page */}
      <Route path="/join/:token" element={<JoinPage />} />
      
      {/* Password Reset Page (Public - accessed via email link) */}
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      {/* Role-based entry point - also checks install gate */}
      <Route path="/" element={<InstallGateRoute />} />

      {/* Panel Selection for multi-role users */}
      <Route path="/select-panel" element={
        <ProtectedRoute>
          <PanelSelectionPage />
        </ProtectedRoute>
      } />

      {/* === ROLE-SPECIFIC UIs === */}
      
      {/* Resident UI - Emergency First (Independent mobile-first layout) */}
      <Route path="/resident" element={
        <ProtectedRoute allowedRoles={['Residente', 'Administrador']}>
          <ResidentHome />
        </ProtectedRoute>
      } />

      {/* Guard UI - Emergency Response */}
      <Route path="/guard" element={
        <ProtectedRoute allowedRoles={['Guarda', 'Supervisor', 'Administrador']}>
          <GuardUI />
        </ProtectedRoute>
      } />

      {/* Student UI - Learning */}
      <Route path="/student" element={
        <ProtectedRoute allowedRoles={['Estudiante', 'Administrador']}>
          <StudentUI />
        </ProtectedRoute>
      } />

      {/* === ADMIN/SUPERVISOR DASHBOARD === */}
      
      <Route path="/admin/dashboard" element={
        <ProtectedRoute allowedRoles={['Administrador', 'Supervisor']}>
          <DashboardPage />
        </ProtectedRoute>
      } />

      <Route path="/admin/users" element={
        <ProtectedRoute allowedRoles={['Administrador']}>
          <UserManagementPage />
        </ProtectedRoute>
      } />

      <Route path="/admin/settings" element={
        <ProtectedRoute allowedRoles={['Administrador']}>
          <CondominiumSettingsPage />
        </ProtectedRoute>
      } />

      <Route path="/dashboard" element={
        <ProtectedRoute>
          <DashboardPage />
        </ProtectedRoute>
      } />

      <Route path="/security" element={
        <ModuleProtectedRoute allowedRoles={['Administrador', 'Supervisor', 'Guarda']} moduleId="security">
          <SecurityModule />
        </ModuleProtectedRoute>
      } />

      {/* RRHH - Módulo Central de Recursos Humanos (incluye Turnos) */}
      <Route path="/rrhh" element={
        <ModuleProtectedRoute allowedRoles={['Administrador', 'Supervisor', 'Guarda', 'HR']} moduleId="hr">
          <RRHHModule />
        </ModuleProtectedRoute>
      } />

      {/* Redirect legacy /hr and /shifts to /rrhh */}
      <Route path="/hr" element={<Navigate to="/rrhh" replace />} />
      <Route path="/shifts" element={<Navigate to="/rrhh" replace />} />

      <Route path="/school" element={
        <ModuleProtectedRoute allowedRoles={['Administrador', 'Estudiante', 'Guarda']} moduleId="school">
          <SchoolModule />
        </ModuleProtectedRoute>
      } />

      <Route path="/payments" element={
        <ModuleProtectedRoute allowedRoles={['Administrador', 'Residente', 'Estudiante']} moduleId="payments">
          <AdminBillingPage />
        </ModuleProtectedRoute>
      } />

      <Route path="/reservations" element={
        <ModuleProtectedRoute allowedRoles={['Administrador', 'Residente', 'Guarda']} moduleId="reservations">
          <ReservationsModule />
        </ModuleProtectedRoute>
      } />

      <Route path="/audit" element={
        <ModuleProtectedRoute allowedRoles={['Administrador', 'SuperAdmin']} moduleId="audit">
          <AuditModule />
        </ModuleProtectedRoute>
      } />

      {/* Super Admin Dashboard */}
      <Route path="/super-admin" element={
        <ProtectedRoute allowedRoles={['SuperAdmin', 'Administrador']}>
          <SuperAdminDashboard />
        </ProtectedRoute>
      } />

      {/* Super Admin Onboarding Wizard */}
      <Route path="/super-admin/onboarding" element={
        <ProtectedRoute allowedRoles={['SuperAdmin']}>
          <OnboardingWizard />
        </ProtectedRoute>
      } />

      {/* Super Admin Financial Portfolio - Cartera */}
      <Route path="/super-admin/finanzas/cartera" element={
        <ProtectedRoute allowedRoles={['SuperAdmin']}>
          <FinancialPortfolioPage />
        </ProtectedRoute>
      } />

      {/* Redirect old settings to new admin settings */}
      <Route path="/settings" element={<Navigate to="/admin/settings" replace />} />

      {/* Profile - Available to all authenticated users EXCEPT Guards */}
      {/* Guards have their own embedded profile in GuardUI */}
      <Route path="/profile" element={
        <ProtectedRoute>
          <ProfilePageOrRedirect />
        </ProtectedRoute>
      } />
      
      {/* View other user's profile */}
      <Route path="/profile/:userId" element={
        <ProtectedRoute>
          <ProfilePageOrRedirect />
        </ProtectedRoute>
      } />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  const { showUpdate, isUpdating, triggerUpdate, dismissUpdate } = useServiceWorkerUpdate();

  return (
    <PersistQueryClientProvider 
      client={queryClient} 
      persistOptions={{
        persister,
        maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days - native app experience
        buster: 'v2', // Increment to invalidate all cached data
      }}
    >
      <BrowserRouter>
        <AuthProvider>
          <ModulesProvider>
            <AppRoutes />
            <Toaster position="top-right" />
            {/* Service Worker Update Modal */}
            <UpdateAvailableModal 
              isOpen={showUpdate} 
              onUpdate={triggerUpdate} 
              onDismiss={dismissUpdate}
              isUpdating={isUpdating} 
            />
          </ModulesProvider>
        </AuthProvider>
      </BrowserRouter>
    </PersistQueryClientProvider>
  );
}

export default App;
