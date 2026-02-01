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
import './App.css';

// ==================== PANIC SOUND UTILITY ====================
// Create audio context and generate alert sound using Web Audio API
let audioContext = null;
let panicSoundInterval = null;

const playPanicSound = () => {
  try {
    // Create audio context if not exists
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    
    // Resume context if suspended (browser autoplay policy)
    if (audioContext.state === 'suspended') {
      audioContext.resume();
    }
    
    // Create oscillator for alert sound
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    // Alert-like sound pattern
    oscillator.frequency.setValueAtTime(880, audioContext.currentTime); // A5
    oscillator.frequency.setValueAtTime(660, audioContext.currentTime + 0.15); // E5
    oscillator.frequency.setValueAtTime(880, audioContext.currentTime + 0.3); // A5
    oscillator.frequency.setValueAtTime(660, audioContext.currentTime + 0.45); // E5
    
    // Volume envelope
    gainNode.gain.setValueAtTime(0.5, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.6);
    
    oscillator.type = 'square';
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.6);
  } catch (e) {
    console.warn('Could not play panic sound:', e);
  }
};

// Start repeating panic sound
const startPanicSoundLoop = () => {
  if (panicSoundInterval) return; // Already playing
  
  playPanicSound(); // Play immediately
  panicSoundInterval = setInterval(playPanicSound, 2000); // Repeat every 2 seconds
};

// Stop panic sound
const stopPanicSound = () => {
  if (panicSoundInterval) {
    clearInterval(panicSoundInterval);
    panicSoundInterval = null;
  }
};

// Expose stop function globally for components to use
if (typeof window !== 'undefined') {
  window.stopPanicSound = stopPanicSound;
}

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
  
  // Listen for service worker messages
  navigator.serviceWorker?.addEventListener('message', (event) => {
    if (event.data?.type === 'PLAY_PANIC_SOUND') {
      console.log('[App] Received panic sound request');
      startPanicSoundLoop();
      
      // Auto-stop after 30 seconds if not acknowledged
      setTimeout(stopPanicSound, 30000);
    }
    
    if (event.data?.type === 'PANIC_ALERT_CLICK') {
      console.log('[App] Received panic alert click');
      stopPanicSound();
    }
  });
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
