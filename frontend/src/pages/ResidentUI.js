import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import api from '../services/api';
import { 
  Heart, 
  Search, 
  Siren,
  Navigation,
  Loader2,
  LogOut,
  Shield,
  MapPin,
  Phone,
  CheckCircle
} from 'lucide-react';

const PANIC_TYPES = {
  emergencia_medica: {
    label: 'EMERGENCIA MÉDICA',
    icon: Heart,
    color: 'from-red-600 to-red-700',
    hoverColor: 'hover:from-red-500 hover:to-red-600',
    description: 'Necesito atención médica'
  },
  actividad_sospechosa: {
    label: 'ACTIVIDAD SOSPECHOSA',
    icon: Search,
    color: 'from-yellow-600 to-orange-600',
    hoverColor: 'hover:from-yellow-500 hover:to-orange-500',
    description: 'Veo algo sospechoso'
  },
  emergencia_general: {
    label: 'EMERGENCIA GENERAL',
    icon: Siren,
    color: 'from-purple-600 to-pink-600',
    hoverColor: 'hover:from-purple-500 hover:to-pink-500',
    description: 'Otra emergencia'
  }
};

const ResidentUI = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [location, setLocation] = useState(null);
  const [isGettingLocation, setIsGettingLocation] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [sentAlert, setSentAlert] = useState(null);
  const [locationError, setLocationError] = useState(null);

  useEffect(() => {
    // Get location on mount
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
          });
          setIsGettingLocation(false);
        },
        (error) => {
          console.error('Location error:', error);
          setLocationError('No se pudo obtener ubicación');
          setIsGettingLocation(false);
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    } else {
      setLocationError('GPS no disponible');
      setIsGettingLocation(false);
    }

    // Keep updating location
    const watchId = navigator.geolocation?.watchPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        });
      },
      () => {},
      { enableHighAccuracy: true }
    );

    return () => {
      if (watchId) navigator.geolocation.clearWatch(watchId);
    };
  }, []);

  const handlePanic = async (panicType) => {
    if (isSending) return;
    
    setIsSending(true);
    try {
      const result = await api.triggerPanic({
        panic_type: panicType,
        location: `Residencia de ${user.full_name}`,
        latitude: location?.latitude,
        longitude: location?.longitude,
        description: `Alerta activada por ${user.full_name}`
      });
      
      setSentAlert({
        type: panicType,
        guards: result.notified_guards,
        time: new Date().toLocaleTimeString('es-ES')
      });

      // Reset after 10 seconds
      setTimeout(() => setSentAlert(null), 10000);
    } catch (error) {
      console.error('Error sending panic:', error);
      alert('Error al enviar alerta. Intenta de nuevo.');
    } finally {
      setIsSending(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Success screen after sending alert
  if (sentAlert) {
    const config = PANIC_TYPES[sentAlert.type];
    return (
      <div className="min-h-screen bg-[#05050A] flex flex-col items-center justify-center p-6">
        <div className="text-center space-y-6 animate-pulse">
          <div className="w-24 h-24 mx-auto rounded-full bg-green-500/20 flex items-center justify-center">
            <CheckCircle className="w-12 h-12 text-green-400" />
          </div>
          <h1 className="text-3xl font-bold text-green-400">ALERTA ENVIADA</h1>
          <p className="text-xl text-white">{config.label}</p>
          <div className="p-4 rounded-lg bg-muted/30 border border-green-500/20">
            <p className="text-lg">
              <span className="text-green-400 font-bold">{sentAlert.guards}</span> guardas notificados
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Mantente en un lugar seguro. Ayuda en camino.
            </p>
          </div>
          <p className="text-sm text-muted-foreground">{sentAlert.time}</p>
        </div>
        <Button
          variant="outline"
          className="mt-8 border-[#1E293B]"
          onClick={() => setSentAlert(null)}
        >
          Volver
        </Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#05050A] flex flex-col">
      {/* Header - Minimal */}
      <header className="p-4 flex items-center justify-between border-b border-[#1E293B]">
        <div className="flex items-center gap-3">
          <Shield className="w-8 h-8 text-primary" />
          <div>
            <h1 className="text-lg font-bold font-['Outfit']">GENTURIX</h1>
            <p className="text-xs text-muted-foreground">{user?.full_name}</p>
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

      {/* GPS Status */}
      <div className="px-4 py-3 bg-[#0F111A] border-b border-[#1E293B]">
        <div className="flex items-center justify-center gap-2">
          {isGettingLocation ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
              <span className="text-sm text-muted-foreground">Obteniendo ubicación...</span>
            </>
          ) : location ? (
            <>
              <Navigation className="w-4 h-4 text-green-400" />
              <span className="text-sm text-green-400">GPS Activo</span>
              <span className="text-xs font-mono text-muted-foreground ml-2">
                {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
              </span>
            </>
          ) : (
            <>
              <MapPin className="w-4 h-4 text-yellow-400" />
              <span className="text-sm text-yellow-400">{locationError || 'Sin GPS'}</span>
            </>
          )}
        </div>
      </div>

      {/* Main - Emergency Buttons */}
      <main className="flex-1 flex flex-col justify-center p-4 gap-4">
        <p className="text-center text-muted-foreground mb-2">
          Presiona el botón de emergencia
        </p>

        {Object.entries(PANIC_TYPES).map(([type, config]) => {
          const IconComponent = config.icon;
          return (
            <Button
              key={type}
              className={`h-32 md:h-40 w-full rounded-2xl bg-gradient-to-br ${config.color} ${config.hoverColor} 
                text-white font-bold text-xl md:text-2xl transition-all duration-300 
                hover:scale-[1.02] active:scale-[0.98] shadow-lg
                disabled:opacity-50 disabled:cursor-not-allowed`}
              onClick={() => handlePanic(type)}
              disabled={isSending}
              data-testid={`panic-btn-${type}`}
            >
              <div className="flex flex-col items-center gap-3">
                {isSending ? (
                  <Loader2 className="w-12 h-12 animate-spin" />
                ) : (
                  <IconComponent className="w-12 h-12" />
                )}
                <span>{config.label}</span>
                <span className="text-sm font-normal opacity-80">{config.description}</span>
              </div>
            </Button>
          );
        })}
      </main>

      {/* Footer */}
      <footer className="p-4 border-t border-[#1E293B] bg-[#0F111A]">
        <div className="flex items-center justify-center gap-2 text-muted-foreground">
          <Phone className="w-4 h-4" />
          <span className="text-sm">Emergencias: 911</span>
        </div>
      </footer>
    </div>
  );
};

export default ResidentUI;
