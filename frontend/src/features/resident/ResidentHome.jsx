/**
 * GENTURIX - Resident Home (i18n)
 * 
 * Main resident interface with emergency, visits, reservations, directory and profile.
 * Uses independent ResidentLayout for mobile-first experience.
 * Full i18n support.
 * 
 * UI: Simple swipe navigation between modules (react-swipeable)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useSwipeable } from 'react-swipeable';
import { useAuth } from '../../contexts/AuthContext';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../../components/ui/dropdown-menu';
import api from '../../services/api';
import ProfileDirectory from '../../components/ProfileDirectory';
import EmbeddedProfile from '../../components/EmbeddedProfile';
import ResidentVisitsModule from '../../components/ResidentVisitsModule';
import PushPermissionBanner from '../../components/PushPermissionBanner';
import ResidentReservations from '../../components/ResidentReservations';
import DynamicEmergencyButtons from '../../components/DynamicEmergencyButtons';
import ResidentLayout from './ResidentLayout';
import { toast } from 'sonner';
import { 
  Heart, 
  Eye, 
  AlertTriangle,
  Loader2,
  Shield,
  Phone,
  CheckCircle,
  MapPin,
  Wifi,
  WifiOff,
  Bell,
  User,
  Check,
  CheckCheck,
  RefreshCw,
  UserCheck,
  LogOut,
  Calendar,
  Users
} from 'lucide-react';

// Import emergency styles
import '../../styles/emergency-buttons.css';

// ============================================
// GPS STATUS COMPONENT (i18n)
// ============================================
const GPSStatus = ({ location, isLoading, error, t }) => {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-2 px-4 rounded-full bg-[#1E293B]/50 mx-auto w-fit">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        <span className="text-xs text-muted-foreground">{t('emergency.gettingLocation')}</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center gap-2 py-2 px-4 rounded-full bg-red-500/10 border border-red-500/20 mx-auto w-fit">
        <WifiOff className="w-4 h-4 text-red-400" />
        <span className="text-xs text-red-400">{error}</span>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center gap-2 py-2 px-4 rounded-full bg-green-500/10 border border-green-500/20 mx-auto w-fit">
      <MapPin className="w-4 h-4 text-green-400" />
      <span className="text-xs text-green-400">{t('emergency.gpsActive')}</span>
      {location?.accuracy && (
        <span className="text-[10px] text-muted-foreground">±{Math.round(location.accuracy)}m</span>
      )}
    </div>
  );
};

// ============================================
// SUCCESS SCREEN (i18n)
// ============================================
const SuccessScreen = ({ alert, onDismiss, t }) => {
  const getAlertConfig = (type) => {
    const configs = {
      emergencia_general: {
        label: t('emergency.generalFull'),
        icon: AlertTriangle,
        colors: { bg: 'bg-red-500/20', text: 'text-red-400' }
      },
      emergencia_medica: {
        label: t('emergency.medicalFull'),
        icon: Heart,
        colors: { bg: 'bg-green-500/20', text: 'text-green-400' }
      },
      actividad_sospechosa: {
        label: t('emergency.securityFull'),
        icon: Eye,
        colors: { bg: 'bg-blue-500/20', text: 'text-blue-400' }
      }
    };
    return configs[type] || configs.emergencia_general;
  };

  const config = getAlertConfig(alert.type);
  const IconComponent = config.icon;

  return (
    <div className="fixed inset-0 z-50 bg-[#05050A] flex flex-col items-center justify-center p-6">
      <div className="w-24 h-24 rounded-full bg-green-500/20 flex items-center justify-center mb-6 animate-pulse">
        <CheckCircle className="w-12 h-12 text-green-400" />
      </div>
      <h1 className="text-2xl font-bold text-white mb-2 text-center">{t('emergency.alertSent')}</h1>
      <p className="text-muted-foreground text-center mb-6">
        {alert.guards > 0 
          ? t('emergency.guardsNotified', { count: alert.guards })
          : t('emergency.alertRegistered')
        }
      </p>
      <div className="bg-[#0F111A] border border-[#1E293B] rounded-2xl p-4 w-full max-w-sm mb-6">
        <div className="flex items-center gap-3 mb-3">
          <div className={`w-10 h-10 rounded-lg ${config.colors.bg} flex items-center justify-center`}>
            <IconComponent className={`w-5 h-5 ${config.colors.text}`} />
          </div>
          <div>
            <p className="font-semibold text-white">{config.label}</p>
            <p className="text-xs text-muted-foreground">{alert.time}</p>
          </div>
        </div>
        {alert.location && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <MapPin className="w-3 h-3" />
            <span>{t('emergency.locationSent')}</span>
          </div>
        )}
      </div>
      <Button onClick={onDismiss} variant="outline" className="min-h-[48px] px-8">
        {t('common.close')}
      </Button>
    </div>
  );
};

// ============================================
// EMERGENCY TAB (Dynamic Hierarchical Design)
// ============================================
const EmergencyTab = ({ location, locationLoading, locationError, onEmergency, sendingType, t }) => (
  <div 
    style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '16px',
      gap: '16px',
      boxSizing: 'border-box',
      background: 'radial-gradient(ellipse at center top, rgba(220, 38, 38, 0.06) 0%, transparent 50%)'
    }}
    data-testid="emergency-tab"
  >
    {/* GPS Status */}
    <div className="flex-shrink-0">
      <GPSStatus location={location} isLoading={locationLoading} error={locationError} t={t} />
    </div>
    
    {/* Dynamic Emergency Buttons */}
    <div className="flex-1 flex items-center justify-center min-h-0">
      <DynamicEmergencyButtons
        onTrigger={onEmergency}
        disabled={!!sendingType}
      />
    </div>
    
    {/* Info Footer */}
    <p className="flex-shrink-0 text-xs text-center text-white/40 px-4">
      {t('emergency.locationWillBeSent')}
    </p>
  </div>
);

// ============================================
// MAIN COMPONENT
// ============================================

// Tab order for animation direction calculation
const TAB_ORDER = ['emergency', 'visits', 'reservations', 'directory', 'profile'];

const ResidentHome = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('emergency');
  
  // Location state
  const [location, setLocation] = useState(null);
  const [locationLoading, setLocationLoading] = useState(true);
  const [locationError, setLocationError] = useState(null);
  
  // Emergency state
  const [sendingType, setSendingType] = useState(null);
  const [sentAlert, setSentAlert] = useState(null);
  
  // Notifications state
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  // GPS Location tracking
  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationError(t('emergency.gpsNotSupported'));
      setLocationLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
        setLocationLoading(false);
      },
      (err) => {
        console.error('GPS Error:', err);
        setLocationError(t('emergency.gpsError'));
        setLocationLoading(false);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        setLocation({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
      },
      () => {},
      { enableHighAccuracy: true, maximumAge: 5000 }
    );

    return () => navigator.geolocation.clearWatch(watchId);
  }, [t]);

  // PWA Shortcuts handler
  useEffect(() => {
    const action = searchParams.get('action');
    if (action === 'medical') {
      handleEmergency('emergencia_medica');
    } else if (action === 'emergency') {
      handleEmergency('emergencia_general');
    }
  }, [searchParams]);

  // Emergency handler
  const handleEmergency = useCallback(async (emergencyType) => {
    if (sendingType) return;
    if (navigator.vibrate) navigator.vibrate([100, 50, 100]);

    setSendingType(emergencyType);

    // Get emergency type label for description
    const typeLabels = {
      emergencia_general: t('emergency.generalFull'),
      emergencia_medica: t('emergency.medicalFull'),
      actividad_sospechosa: t('emergency.securityFull')
    };

    try {
      const result = await api.triggerPanic({
        panic_type: emergencyType,
        location: `Residencia de ${user.full_name}`,
        latitude: location?.latitude,
        longitude: location?.longitude,
        description: `${typeLabels[emergencyType]} activada por ${user.full_name}`,
      });

      if (navigator.vibrate) navigator.vibrate([200, 100, 200, 100, 300]);

      setSentAlert({
        type: emergencyType,
        guards: result.notified_guards,
        location: location,
        time: new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }),
      });

      setTimeout(() => setSentAlert(null), 20000);
    } catch (error) {
      console.error('[Panic] Error:', error);
      if (navigator.vibrate) navigator.vibrate(500);
      
      let errorMessage = t('emergency.errorGeneric');
      const status = error.status || error.response?.status;
      const detail = error.data?.detail || error.message;
      
      if (status === 401) {
        errorMessage = t('emergency.errorSessionExpired');
      } else if (status === 403) {
        errorMessage = detail || t('emergency.errorNoPermission');
      } else if (detail) {
        errorMessage = detail;
      }
      
      toast.error(t('emergency.errorTitle'), { description: errorMessage, duration: 10000 });
    } finally {
      setSendingType(null);
    }
  }, [sendingType, location, user, t]);

  // Get current module index
  const activeIndex = TAB_ORDER.indexOf(activeTab);
  
  // Simple swipe navigation handlers
  const goNextTab = useCallback(() => {
    const nextIndex = Math.min(activeIndex + 1, TAB_ORDER.length - 1);
    if (nextIndex !== activeIndex) {
      setActiveTab(TAB_ORDER[nextIndex]);
    }
  }, [activeIndex]);
  
  const goPrevTab = useCallback(() => {
    const prevIndex = Math.max(activeIndex - 1, 0);
    if (prevIndex !== activeIndex) {
      setActiveTab(TAB_ORDER[prevIndex]);
    }
  }, [activeIndex]);
  
  // react-swipeable handlers - simple swipe only
  const swipeHandlers = useSwipeable({
    onSwipedLeft: goNextTab,
    onSwipedRight: goPrevTab,
    delta: 70,                    // Minimum swipe distance
    preventScrollOnSwipe: false,  // Allow vertical scrolling
    trackTouch: true,
    trackMouse: false,
    swipeDuration: 500,
  });

  // Success Screen - early return AFTER all hooks
  if (sentAlert) {
    return <SuccessScreen alert={sentAlert} onDismiss={() => setSentAlert(null)} t={t} />;
  }

  return (
    <ResidentLayout 
      activeTab={activeTab} 
      onTabChange={setActiveTab}
    >
      {/* Carousel Container - fills all available height */}
      <div 
        ref={containerRef}
        className="flex-1 relative"
        style={{ 
          overflow: 'hidden',
          minHeight: 0 
        }}
      >
        <motion.div
          className="flex h-full"
          drag="x"
          dragConstraints={{ left: 0, right: 0 }}
          dragElastic={0.1}
          dragMomentum={false}
          dragDirectionLock
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          style={{ 
            x,
            width: `${TAB_ORDER.length * 100}%`,
            touchAction: 'pan-y'
          }}
        >
          {/* Emergency Module */}
          <div 
            className="h-full flex-shrink-0 overflow-y-auto"
            style={{ 
              width: `${100 / TAB_ORDER.length}%`,
              WebkitOverflowScrolling: 'touch',
              paddingBottom: 'calc(72px + env(safe-area-inset-bottom, 16px))'
            }}
          >
            <EmergencyTab
              location={location}
              locationLoading={locationLoading}
              locationError={locationError}
              onEmergency={handleEmergency}
              sendingType={sendingType}
              t={t}
            />
          </div>
          
          {/* Visits Module */}
          <div 
            className="h-full flex-shrink-0 overflow-y-auto"
            style={{ 
              width: `${100 / TAB_ORDER.length}%`,
              WebkitOverflowScrolling: 'touch',
              paddingBottom: 'calc(72px + env(safe-area-inset-bottom, 16px))'
            }}
          >
            <div className="px-3 py-4">
              <ResidentVisitsModule />
            </div>
          </div>
          
          {/* Reservations Module */}
          <div 
            className="h-full flex-shrink-0 overflow-y-auto"
            style={{ 
              width: `${100 / TAB_ORDER.length}%`,
              WebkitOverflowScrolling: 'touch',
              paddingBottom: 'calc(72px + env(safe-area-inset-bottom, 16px))'
            }}
          >
            <div className="px-3 py-4">
              <ResidentReservations />
            </div>
          </div>
          
          {/* Directory Module */}
          <div 
            className="h-full flex-shrink-0 overflow-y-auto"
            style={{ 
              width: `${100 / TAB_ORDER.length}%`,
              WebkitOverflowScrolling: 'touch',
              paddingBottom: 'calc(72px + env(safe-area-inset-bottom, 16px))'
            }}
          >
            <ProfileDirectory embedded={true} />
          </div>
          
          {/* Profile Module */}
          <div 
            className="h-full flex-shrink-0 overflow-y-auto"
            style={{ 
              width: `${100 / TAB_ORDER.length}%`,
              WebkitOverflowScrolling: 'touch',
              paddingBottom: 'calc(72px + env(safe-area-inset-bottom, 16px))'
            }}
          >
            <div className="px-3 py-4">
              <EmbeddedProfile />
            </div>
          </div>
        </motion.div>
      </div>
      
      {/* Push Permission Banner */}
      <PushPermissionBanner onSubscribed={() => console.log('Push enabled!')} />
    </ResidentLayout>
  );
};

export default ResidentHome;
