/**
 * GENTURIX - Resident Layout
 * 
 * Independent mobile-first layout for Resident role.
 * Completely decoupled from DashboardLayout.
 * Designed as native app experience.
 */

import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Shield, LogOut, Users, Calendar, User, AlertTriangle } from 'lucide-react';
import MobileBottomNav from '../../components/layout/BottomNav.js';

// Navigation items for Resident
const RESIDENT_NAV_ITEMS = [
  { 
    id: 'emergency', 
    label: 'Emergencia', 
    icon: AlertTriangle,
    bgColor: 'bg-red-600',
    glowColor: 'shadow-red-500/40'
  },
  { id: 'visits', label: 'Visitas', icon: Users },
  { id: 'reservations', label: 'Reservas', icon: Calendar },
  { id: 'directory', label: 'Personas', icon: Users },
  { id: 'profile', label: 'Perfil', icon: User },
];

const ResidentLayout = ({ children, activeTab, onTabChange, title = 'GENTURIX' }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div 
      className="min-h-screen bg-[#05050A] flex flex-col w-full overflow-x-hidden"
      style={{ 
        minHeight: '100dvh',
        maxWidth: '100%',
        WebkitOverflowScrolling: 'touch'
      }}
    >
      {/* Header - Compact, fixed */}
      <header 
        className="sticky top-0 z-40 bg-[#0A0A0F]/95 backdrop-blur-lg border-b border-[#1E293B]/60 flex-shrink-0"
        style={{ height: '56px' }}
      >
        <div className="flex items-center justify-between h-full px-3">
          {/* Logo & User */}
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            <div className="w-9 h-9 rounded-xl bg-primary/20 flex items-center justify-center flex-shrink-0">
              <Shield className="w-4 h-4 text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-sm font-bold text-white">{title}</h1>
              <p className="text-xs text-muted-foreground truncate">{user?.full_name}</p>
            </div>
          </div>
          
          {/* Logout */}
          <button
            onClick={handleLogout}
            className="p-2.5 min-h-[44px] min-w-[44px] rounded-xl text-muted-foreground hover:text-white hover:bg-white/5 transition-colors flex items-center justify-center"
            data-testid="logout-btn"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Content - Full width, scrollable */}
      <main 
        className="flex-1 overflow-y-auto overflow-x-hidden w-full"
        style={{ 
          paddingBottom: 'calc(80px + env(safe-area-inset-bottom, 0px))',
          WebkitOverflowScrolling: 'touch',
          maxWidth: '100%'
        }}
      >
        {children}
      </main>

      {/* Bottom Navigation - Fixed, app-style */}
      <MobileBottomNav 
        items={RESIDENT_NAV_ITEMS}
        activeTab={activeTab}
        onTabChange={onTabChange}
        centerIndex={0}
      />
    </div>
  );
};

export default ResidentLayout;
