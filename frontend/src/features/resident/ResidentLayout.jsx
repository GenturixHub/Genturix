/**
 * GENTURIX - Resident Layout (i18n)
 * 
 * Independent mobile-first layout for Resident role.
 * Completely decoupled from DashboardLayout.
 * Designed as native app experience.
 * Full i18n support.
 */

import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Shield, LogOut, Users, Calendar, User, AlertTriangle } from 'lucide-react';
import MobileBottomNav from '../../components/layout/BottomNav.js';

const ResidentLayout = ({ 
  children, 
  activeTab, 
  onTabChange, 
  title = 'GENTURIX',
  showIndicators = false,
  indicatorCount = 5,
  activeIndex = 0
}) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  // Tab IDs for indicator click navigation
  const TAB_IDS = ['emergency', 'visits', 'reservations', 'directory', 'profile'];

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

      {/* Content - Full height container for carousel */}
      <main 
        className="flex-1 min-h-0 flex flex-col relative"
        style={{ overflow: 'hidden' }}
      >
        {children}
        
        {/* Carousel Page Indicators */}
        {showIndicators && (
          <div 
            style={{ 
              position: 'absolute',
              bottom: '8px',
              left: '50%',
              transform: 'translateX(-50%)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              zIndex: 20
            }}
            data-testid="carousel-indicators"
          >
            {Array.from({ length: indicatorCount }).map((_, index) => (
              <div
                key={index}
                onClick={() => onTabChange(TAB_IDS[index])}
                style={{
                  width: index === activeIndex ? '6px' : '4px',
                  height: index === activeIndex ? '6px' : '4px',
                  borderRadius: '50%',
                  backgroundColor: index === activeIndex ? '#22d3ee' : 'rgba(255,255,255,0.25)',
                  transition: 'all 0.2s ease',
                  cursor: 'pointer'
                }}
                role="button"
                aria-label={`Go to ${TAB_IDS[index]} module`}
                data-testid={`carousel-dot-${TAB_IDS[index]}`}
              />
            ))}
          </div>
        )}
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
