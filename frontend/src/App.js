import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ModulesProvider } from './contexts/ModulesContext';
import { Toaster } from './components/ui/sonner';
import LoginPage from './pages/LoginPage';
import PanelSelectionPage from './pages/PanelSelectionPage';
import DashboardPage from './pages/DashboardPage';
import SecurityModule from './pages/SecurityModule';
import RRHHModule from './pages/RRHHModule';
import SchoolModule from './pages/SchoolModule';
import PaymentsModule from './pages/PaymentsModule';
import AuditModule from './pages/AuditModule';
import ReservationsModule from './pages/ReservationsModule';
import ResidentUI from './pages/ResidentUI';
import GuardUI from './pages/GuardUI';
import StudentUI from './pages/StudentUI';
import SuperAdminDashboard from './pages/SuperAdminDashboard';
import OnboardingWizard from './pages/OnboardingWizard';
import UserManagementPage from './pages/UserManagementPage';
import ProfilePage from './pages/ProfilePage';
import AlertSoundManager from './utils/AlertSoundManager';
import './App.css';

// Track auto-stop timeout to prevent multiple timeouts
let panicSoundTimeout = null;

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
  
  // Track if user has manually acknowledged the alert
  let userAcknowledged = false;
  
  // Listen for service worker messages
  navigator.serviceWorker?.addEventListener('message', (event) => {
    if (event.data?.type === 'PLAY_PANIC_SOUND') {
      console.log('[App] Received panic sound request from SW');
      
      // Don't restart sound if user has already acknowledged
      if (userAcknowledged) {
        console.log('[App] User already acknowledged alert, ignoring new sound request');
        return;
      }
      
      // Clear any existing timeout to prevent duplicate stops
      if (panicSoundTimeout) {
        clearTimeout(panicSoundTimeout);
        panicSoundTimeout = null;
      }
      
      AlertSoundManager.play();
      
      // Auto-stop after 30 seconds if not acknowledged (safety net)
      panicSoundTimeout = setTimeout(() => {
        AlertSoundManager.stop();
        panicSoundTimeout = null;
      }, 30000);
    }
    
    if (event.data?.type === 'PANIC_ALERT_CLICK') {
      console.log('[App] Received panic alert click from SW');
      userAcknowledged = true;  // Mark as acknowledged
      if (panicSoundTimeout) {
        clearTimeout(panicSoundTimeout);
        panicSoundTimeout = null;
      }
      AlertSoundManager.stop();
    }
    
    // Stop sound when alert is viewed/acknowledged
    if (event.data?.type === 'STOP_PANIC_SOUND') {
      console.log('[App] Received stop sound request');
      userAcknowledged = true;  // Mark as acknowledged
      if (panicSoundTimeout) {
        clearTimeout(panicSoundTimeout);
        panicSoundTimeout = null;
      }
      AlertSoundManager.stop();
    }
    
    // Also handle NOTIFICATION_CLICKED and NOTIFICATION_CLOSED as backup
    if (event.data?.type === 'NOTIFICATION_CLICKED' || event.data?.type === 'NOTIFICATION_CLOSED') {
      console.log('[App] Notification clicked/closed, stopping sound');
      userAcknowledged = true;  // Mark as acknowledged
      if (panicSoundTimeout) {
        clearTimeout(panicSoundTimeout);
        panicSoundTimeout = null;
      }
      AlertSoundManager.stop();
    }
  });
  
  // Reset acknowledgement flag when a new alert comes in (after some time)
  // This allows new alerts to play sound again after the current one is resolved
  setInterval(() => {
    if (userAcknowledged && !AlertSoundManager.getIsPlaying()) {
      // Check if there are no more active alerts, reset flag
      userAcknowledged = false;
    }
  }, 60000);  // Check every minute
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

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={
        <PublicRoute>
          <LoginPage />
        </PublicRoute>
      } />

      {/* Role-based entry point */}
      <Route path="/" element={<RoleBasedRedirect />} />

      {/* Panel Selection for multi-role users */}
      <Route path="/select-panel" element={
        <ProtectedRoute>
          <PanelSelectionPage />
        </ProtectedRoute>
      } />

      {/* === ROLE-SPECIFIC UIs === */}
      
      {/* Resident UI - Emergency First */}
      <Route path="/resident" element={
        <ProtectedRoute allowedRoles={['Residente', 'Administrador']}>
          <ResidentUI />
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

      <Route path="/dashboard" element={
        <ProtectedRoute>
          <DashboardPage />
        </ProtectedRoute>
      } />

      <Route path="/security" element={
        <ProtectedRoute allowedRoles={['Administrador', 'Supervisor', 'Guarda']}>
          <SecurityModule />
        </ProtectedRoute>
      } />

      {/* RRHH - Módulo Central de Recursos Humanos (incluye Turnos) */}
      <Route path="/rrhh" element={
        <ProtectedRoute allowedRoles={['Administrador', 'Supervisor', 'Guarda', 'HR']}>
          <RRHHModule />
        </ProtectedRoute>
      } />

      {/* Redirect legacy /hr and /shifts to /rrhh */}
      <Route path="/hr" element={<Navigate to="/rrhh" replace />} />
      <Route path="/shifts" element={<Navigate to="/rrhh" replace />} />

      <Route path="/school" element={
        <ProtectedRoute allowedRoles={['Administrador', 'Estudiante', 'Guarda']}>
          <SchoolModule />
        </ProtectedRoute>
      } />

      <Route path="/payments" element={
        <ProtectedRoute allowedRoles={['Administrador', 'Residente', 'Estudiante']}>
          <PaymentsModule />
        </ProtectedRoute>
      } />

      <Route path="/reservations" element={
        <ProtectedRoute allowedRoles={['Administrador', 'Residente', 'Guarda']}>
          <ReservationsModule />
        </ProtectedRoute>
      } />

      <Route path="/audit" element={
        <ProtectedRoute allowedRoles={['Administrador', 'SuperAdmin']}>
          <AuditModule />
        </ProtectedRoute>
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

      <Route path="/settings" element={
        <ProtectedRoute allowedRoles={['Administrador']}>
          <DashboardPage />
        </ProtectedRoute>
      } />

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
  return (
    <BrowserRouter>
      <AuthProvider>
        <ModulesProvider>
          <AppRoutes />
          <Toaster position="top-right" />
        </ModulesProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
