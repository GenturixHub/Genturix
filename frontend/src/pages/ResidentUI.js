import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import api from '../services/api';
import { 
  Heart, 
  Search, 
  Siren,
  Navigation,
  Loader2,
  LogOut,
  Shield,
  Phone,
  CheckCircle,
  Vibrate,
  MapPin
} from 'lucide-react';

const PANIC_TYPES = {
  emergencia_medica: {
    label: 'EMERGENCIA MÉDICA',
    shortLabel: 'MÉDICA',
    icon: Heart,
    gradient: 'from-red-600 via-red-500 to-rose-600',
    shadow: 'shadow-red-500/30',
    description: 'Necesito atención médica urgente'
  },
  actividad_sospechosa: {
    label: 'ACTIVIDAD SOSPECHOSA',
    shortLabel: 'SOSPECHOSO',
    icon: Search,
    gradient: 'from-amber-500 via-yellow-500 to-orange-500',
    shadow: 'shadow-yellow-500/30',
    description: 'Veo algo o alguien sospechoso'
  },
  emergencia_general: {
    label: 'EMERGENCIA GENERAL',
    shortLabel: 'EMERGENCIA',
    icon: Siren,
    gradient: 'from-violet-600 via-purple-500 to-fuchsia-600',
    shadow: 'shadow-purple-500/30',
    description: 'Otra situación de emergencia'
  }
};

const ResidentUI = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, logout } = useAuth();
  const [location, setLocation] = useState(null);
  const [isGettingLocation, setIsGettingLocation] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [sentAlert, setSentAlert] = useState(null);
  const [locationError, setLocationError] = useState(null);
  const [holdProgress, setHoldProgress] = useState({});
  const [activeButton, setActiveButton] = useState(null);

  // Check for action parameter (PWA shortcuts)
  useEffect(() => {
    const action = searchParams.get('action');
    if (action === 'medical') {
      handlePanic('emergencia_medica');
    } else if (action === 'emergency') {
      handlePanic('emergencia_general');
    }
  }, [searchParams]);

  // Get and watch location
  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationError('GPS no disponible');
      setIsGettingLocation(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy
        });
        setIsGettingLocation(false);
      },
      (error) => {
        console.error('Location error:', error);
        setLocationError('No se pudo obtener ubicación');
        setIsGettingLocation(false);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );

    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy
        });
      },
      () => {},
      { enableHighAccuracy: true, maximumAge: 10000 }
    );

    return () => navigator.geolocation.clearWatch(watchId);
  }, []);

  const handlePanic = useCallback(async (panicType) => {
    if (isSending) return;
    
    // Vibrate on press (mobile)
    if (navigator.vibrate) {
      navigator.vibrate([100, 50, 100]);
    }
    
    setIsSending(true);
    try {
      const result = await api.triggerPanic({
        panic_type: panicType,
        location: `Residencia de ${user.full_name}`,
        latitude: location?.latitude,
        longitude: location?.longitude,
        description: `Alerta activada desde app móvil por ${user.full_name}`
      });
      
      // Success vibration
      if (navigator.vibrate) {
        navigator.vibrate([200, 100, 200, 100, 200]);
      }
      
      setSentAlert({
        type: panicType,
        guards: result.notified_guards,
        time: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
      });

      setTimeout(() => setSentAlert(null), 15000);
    } catch (error) {
      console.error('Error sending panic:', error);
      if (navigator.vibrate) {
        navigator.vibrate(500);
      }
      alert('Error al enviar alerta. Intenta de nuevo o llama al 911.');
    } finally {
      setIsSending(false);
    }
  }, [isSending, location, user]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Success screen after sending alert
  if (sentAlert) {
    const config = PANIC_TYPES[sentAlert.type];
    const IconComponent = config.icon;
    
    return (
      <div className="min-h-screen bg-[#05050A] flex flex-col items-center justify-center p-6 safe-area">
        <div className="text-center space-y-6 max-w-sm mx-auto">
          {/* Success Animation */}
          <div className="relative">
            <div className="w-28 h-28 mx-auto rounded-full bg-green-500/20 flex items-center justify-center animate-pulse">
              <CheckCircle className="w-14 h-14 text-green-400" />
            </div>
            <div className="absolute inset-0 w-28 h-28 mx-auto rounded-full border-4 border-green-400/30 animate-ping" />
          </div>
          
          <div className="space-y-2">
            <h1 className="text-2xl font-bold text-green-400">¡ALERTA ENVIADA!</h1>
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r ${config.gradient}`}>
              <IconComponent className="w-5 h-5 text-white" />
              <span className="text-white font-semibold">{config.shortLabel}</span>
            </div>
          </div>
          
          <div className="p-5 rounded-2xl bg-[#0F111A] border border-green-500/20 space-y-3">
            <div className="flex items-center justify-center gap-2 text-2xl font-bold">
              <span className="text-green-400">{sentAlert.guards}</span>
              <span className="text-white">guardas notificados</span>
            </div>
            <p className="text-muted-foreground">
              Mantente en un lugar seguro. Ayuda en camino.
            </p>
            {location && (
              <p className="text-xs font-mono text-muted-foreground">
                📍 {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
              </p>
            )}
          </div>
          
          <p className="text-sm text-muted-foreground">{sentAlert.time}</p>
          
          <Button
            variant="outline"
            size="lg"
            className="w-full border-[#1E293B] h-14"
            onClick={() => setSentAlert(null)}
          >
            Volver al inicio
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#05050A] flex flex-col safe-area">
      {/* Header - Minimal */}
      <header className="flex items-center justify-between p-4 border-b border-[#1E293B]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
            <Shield className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-base font-bold font-['Outfit']">GENTURIX</h1>
            <p className="text-xs text-muted-foreground truncate max-w-[150px]">
              {user?.full_name}
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleLogout}
          className="text-muted-foreground hover:text-white"
          data-testid="logout-btn"
        >
          <LogOut className="w-5 h-5" />
        </Button>
      </header>

      {/* GPS Status Bar */}
      <div className="px-4 py-2.5 bg-[#0F111A] border-b border-[#1E293B]">
        <div className="flex items-center justify-center gap-2">
          {isGettingLocation ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
              <span className="text-xs text-muted-foreground">Obteniendo ubicación GPS...</span>
            </>
          ) : location ? (
            <>
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <Navigation className="w-3.5 h-3.5 text-green-400" />
              <span className="text-xs text-green-400 font-medium">GPS Activo</span>
              <span className="text-[10px] font-mono text-muted-foreground">
                ±{Math.round(location.accuracy || 10)}m
              </span>
            </>
          ) : (
            <>
              <MapPin className="w-4 h-4 text-yellow-400" />
              <span className="text-xs text-yellow-400">{locationError || 'Sin GPS'}</span>
            </>
          )}
        </div>
      </div>

      {/* Main - Emergency Buttons */}
      <main className="flex-1 flex flex-col p-4 gap-4">
        <p className="text-center text-sm text-muted-foreground">
          Presiona para enviar alerta de emergencia
        </p>

        <div className="flex-1 flex flex-col justify-center gap-4 max-w-lg mx-auto w-full">
          {Object.entries(PANIC_TYPES).map(([type, config]) => {
            const IconComponent = config.icon;
            return (
              <Button
                key={type}
                className={`
                  relative overflow-hidden
                  h-[calc((100vh-280px)/3)] min-h-[100px] max-h-[140px]
                  w-full rounded-2xl
                  bg-gradient-to-br ${config.gradient}
                  text-white font-bold text-lg
                  transition-all duration-200
                  hover:scale-[1.02] active:scale-[0.98]
                  shadow-lg ${config.shadow}
                  disabled:opacity-50 disabled:cursor-not-allowed
                  touch-manipulation
                `}
                onClick={() => handlePanic(type)}
                disabled={isSending}
                data-testid={`panic-btn-${type}`}
              >
                <div className="flex flex-col items-center gap-2">
                  {isSending ? (
                    <Loader2 className="w-10 h-10 animate-spin" />
                  ) : (
                    <IconComponent className="w-10 h-10" />
                  )}
                  <span className="text-base sm:text-lg">{config.label}</span>
                  <span className="text-xs font-normal opacity-80 hidden sm:block">
                    {config.description}
                  </span>
                </div>
              </Button>
            );
          })}
        </div>
      </main>

      {/* Footer - Emergency Contact */}
      <footer className="p-4 border-t border-[#1E293B] bg-[#0F111A]">
        <a 
          href="tel:911" 
          className="flex items-center justify-center gap-3 py-3 px-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 transition-colors"
        >
          <Phone className="w-5 h-5" />
          <span className="font-semibold">Llamar al 911</span>
        </a>
      </footer>
    </div>
  );
};

export default ResidentUI;
