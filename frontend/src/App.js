import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Toaster } from './components/ui/sonner';
import LoginPage from './pages/LoginPage';
import PanelSelectionPage from './pages/PanelSelectionPage';
import DashboardPage from './pages/DashboardPage';
import SecurityModule from './pages/SecurityModule';
import HRModule from './pages/HRModule';
import SchoolModule from './pages/SchoolModule';
import PaymentsModule from './pages/PaymentsModule';
import AuditModule from './pages/AuditModule';
import './App.css';

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
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

// Public Route Component (redirects to dashboard if logged in)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
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

      {/* Protected Routes */}
      <Route path="/select-panel" element={
        <ProtectedRoute>
          <PanelSelectionPage />
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

      <Route path="/hr" element={
        <ProtectedRoute allowedRoles={['Administrador', 'Supervisor']}>
          <HRModule />
        </ProtectedRoute>
      } />

      <Route path="/shifts" element={
        <ProtectedRoute allowedRoles={['Administrador', 'Supervisor', 'Guarda']}>
          <HRModule />
        </ProtectedRoute>
      } />

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

      <Route path="/audit" element={
        <ProtectedRoute allowedRoles={['Administrador']}>
          <AuditModule />
        </ProtectedRoute>
      } />

      <Route path="/settings" element={
        <ProtectedRoute allowedRoles={['Administrador']}>
          <DashboardPage />
        </ProtectedRoute>
      } />

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <Toaster position="top-right" />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
