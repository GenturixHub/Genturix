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
      className="bg-[#05050A] flex flex-col w-full"
      style={{ 
        height: '100dvh',
        maxHeight: '100dvh',
        overflow: 'hidden'
      }}
    >
      {/* Header - Compact, fixed height */}
      <header 
        className="z-40 bg-[#0A0A0F]/95 backdrop-blur-lg border-b border-[#1E293B]/60 flex-shrink-0"
        style={{ height: '56px', minHeight: '56px' }}
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

      {/* Content - Flex grow, controlled overflow */}
      <main 
        className="flex-1 w-full"
        style={{ 
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0
        }}
      >
        <div 
          style={{
            flex: 1,
            overflowX: 'hidden',
            overflowY: 'auto',
            WebkitOverflowScrolling: 'touch',
            paddingBottom: 'calc(72px + env(safe-area-inset-bottom, 0px))'
          }}
        >
          {children}
        </div>
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
