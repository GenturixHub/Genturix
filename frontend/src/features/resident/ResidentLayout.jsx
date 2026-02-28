/**
 * GENTURIX - Resident Layout (i18n)
 * 
 * Independent mobile-first layout for Resident role.
 * Completely decoupled from DashboardLayout.
 * Designed as native app experience.
 * Full i18n support.
 */

import React, { useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useSwipeable } from 'react-swipeable';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Shield, LogOut, Users, Calendar, User, AlertTriangle } from 'lucide-react';
import MobileBottomNav from '../../components/layout/BottomNav.js';

// Tab order for swipe navigation
const TAB_ORDER = ['emergency', 'visits', 'reservations', 'directory', 'profile'];

const ResidentLayout = ({ children, activeTab, onTabChange, title = 'GENTURIX' }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  // Swipe navigation functions
  const goNextTab = useCallback(() => {
    const index = TAB_ORDER.indexOf(activeTab);
    if (index < TAB_ORDER.length - 1) {
      onTabChange(TAB_ORDER[index + 1]);
    }
  }, [activeTab, onTabChange]);

  const goPrevTab = useCallback(() => {
    const index = TAB_ORDER.indexOf(activeTab);
    if (index > 0) {
      onTabChange(TAB_ORDER[index - 1]);
    }
  }, [activeTab, onTabChange]);

  // Swipe handlers attached to main scroll container
  const swipeHandlers = useSwipeable({
    onSwipedLeft: goNextTab,
    onSwipedRight: goPrevTab,
    delta: 40,
    preventScrollOnSwipe: false,
    trackTouch: true,
    trackMouse: false,
    touchEventOptions: { passive: false }
  });

  // Navigation items with translations
  const RESIDENT_NAV_ITEMS = useMemo(() => [
    { 
      id: 'emergency', 
      label: t('resident.emergency'), 
      icon: AlertTriangle,
      bgColor: 'bg-red-600',
      glowColor: 'shadow-red-500/40'
    },
    { id: 'visits', label: t('resident.visits'), icon: Users },
    { id: 'reservations', label: t('resident.reservations'), icon: Calendar },
    { id: 'directory', label: t('resident.directory'), icon: Users },
    { id: 'profile', label: t('resident.profile'), icon: User },
  ], [t]);

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

      {/* Content - Scrollable main area with swipe handlers */}
      <main 
        {...swipeHandlers}
        className="flex-1 w-full overflow-y-auto"
        style={{ 
          WebkitOverflowScrolling: 'touch',
          paddingBottom: 'calc(72px + env(safe-area-inset-bottom, 0px))'
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
