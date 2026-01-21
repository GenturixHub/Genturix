import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent } from '../components/ui/card';
import { ScrollArea } from '../components/ui/scroll-area';
import api from '../services/api';
import { 
  Shield, 
  LogOut,
  AlertTriangle,
  MapPin,
  Clock,
  CheckCircle,
  Navigation,
  Loader2,
  RefreshCw,
  Heart,
  Search,
  Siren,
  Bell,
  ExternalLink,
  Phone
} from 'lucide-react';

const PANIC_TYPE_CONFIG = {
  emergencia_medica: { 
    icon: Heart, 
    color: 'bg-red-500', 
    label: 'MÉDICA',
    textColor: 'text-red-400'
  },
  actividad_sospechosa: { 
    icon: Search, 
    color: 'bg-yellow-500', 
    label: 'SOSPECHOSO',
    textColor: 'text-yellow-400'
  },
  emergencia_general: { 
    icon: Siren, 
    color: 'bg-purple-500', 
    label: 'GENERAL',
    textColor: 'text-purple-400'
  }
};

const GuardUI = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [activeEmergencies, setActiveEmergencies] = useState([]);
  const [resolvedEmergencies, setResolvedEmergencies] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [resolvingId, setResolvingId] = useState(null);

  const fetchEmergencies = useCallback(async () => {
    try {
      const events = await api.getPanicEvents();
      setActiveEmergencies(events.filter(e => e.status === 'active'));
      setResolvedEmergencies(events.filter(e => e.status === 'resolved').slice(0, 10));
    } catch (error) {
      console.error('Error fetching emergencies:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchEmergencies();
    // Poll for new emergencies every 5 seconds
    const interval = setInterval(fetchEmergencies, 5000);
    return () => clearInterval(interval);
  }, [fetchEmergencies]);

  // Vibrate on new emergency
  useEffect(() => {
    if (activeEmergencies.length > 0 && navigator.vibrate) {
      navigator.vibrate([200, 100, 200]);
    }
  }, [activeEmergencies.length]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchEmergencies();
  };

  const handleResolve = async (eventId) => {
    setResolvingId(eventId);
    try {
      await api.resolvePanic(eventId);
      if (navigator.vibrate) navigator.vibrate(100);
      fetchEmergencies();
    } catch (error) {
      console.error('Error resolving:', error);
    } finally {
      setResolvingId(null);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Ahora';
    if (diffMins < 60) return `Hace ${diffMins}m`;
    return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  };

  const openInMaps = (lat, lng) => {
    if (lat && lng) {
      // Use platform-specific maps
      const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
      const url = isIOS 
        ? `maps://maps.apple.com/?q=${lat},${lng}`
        : `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
      window.open(url, '_blank');
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center safe-area">
        <Loader2 className="w-10 h-10 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#05050A] flex flex-col safe-area">
      {/* Header */}
      <header className="sticky top-0 z-40 p-4 flex items-center justify-between border-b border-[#1E293B] bg-[#0F111A]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center">
            <Shield className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <h1 className="text-base font-bold font-['Outfit']">GENTURIX GUARD</h1>
            <p className="text-xs text-muted-foreground truncate max-w-[120px]">
              {user?.full_name}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="text-muted-foreground hover:text-white"
          >
            <RefreshCw className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleLogout}
            className="text-muted-foreground hover:text-white"
          >
            <LogOut className="w-5 h-5" />
          </Button>
        </div>
      </header>

      {/* Active Emergencies Alert Bar */}
      <div className={`p-3 ${
        activeEmergencies.length > 0 
          ? 'bg-red-500/10 border-b-2 border-red-500' 
          : 'bg-green-500/10 border-b border-green-500/20'
      }`}>
        <div className="flex items-center justify-center gap-2">
          {activeEmergencies.length > 0 ? (
            <>
              <Bell className="w-5 h-5 text-red-400 animate-pulse" />
              <span className="text-base font-bold text-red-400">
                {activeEmergencies.length} ALERTA{activeEmergencies.length > 1 ? 'S' : ''} ACTIVA{activeEmergencies.length > 1 ? 'S' : ''}
              </span>
            </>
          ) : (
            <>
              <CheckCircle className="w-5 h-5 text-green-400" />
              <span className="text-base font-bold text-green-400">TODO EN ORDEN</span>
            </>
          )}
        </div>
      </div>

      {/* Main Content */}
      <ScrollArea className="flex-1">
        <main className="p-4 space-y-4 pb-20">
          {/* Active Emergencies */}
          {activeEmergencies.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-400" />
                EMERGENCIAS ACTIVAS
              </h2>
              
              {activeEmergencies.map((emergency) => {
                const config = PANIC_TYPE_CONFIG[emergency.panic_type] || PANIC_TYPE_CONFIG.emergencia_general;
                const IconComponent = config.icon;
                
                return (
                  <Card 
                    key={emergency.id} 
                    className="bg-red-500/10 border-red-500/30 overflow-hidden"
                    data-testid={`emergency-${emergency.id}`}
                  >
                    <CardContent className="p-4 space-y-3">
                      {/* Header */}
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`w-12 h-12 rounded-full ${config.color} flex items-center justify-center animate-pulse`}>
                            <IconComponent className="w-6 h-6 text-white" />
                          </div>
                          <div>
                            <Badge className={`${config.color} text-white text-xs`}>
                              {emergency.panic_type_label || config.label}
                            </Badge>
                            <p className="font-semibold mt-1">{emergency.user_name}</p>
                          </div>
                        </div>
                        <span className="text-xs text-muted-foreground bg-[#1E293B] px-2 py-1 rounded">
                          {formatTime(emergency.created_at)}
                        </span>
                      </div>
                      
                      {/* Location */}
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 text-sm">
                          <MapPin className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                          <span className="truncate">{emergency.location}</span>
                        </div>
                        
                        {/* GPS Coordinates - Clickable */}
                        {emergency.latitude && (
                          <button
                            onClick={() => openInMaps(emergency.latitude, emergency.longitude)}
                            className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 w-full p-2 rounded-lg bg-blue-500/10 border border-blue-500/20"
                          >
                            <Navigation className="w-4 h-4" />
                            <span className="font-mono text-xs">
                              {emergency.latitude.toFixed(6)}, {emergency.longitude.toFixed(6)}
                            </span>
                            <ExternalLink className="w-3 h-3 ml-auto" />
                          </button>
                        )}
                      </div>

                      {/* Description */}
                      {emergency.description && (
                        <p className="text-sm text-muted-foreground bg-[#1E293B] p-2 rounded">
                          {emergency.description}
                        </p>
                      )}

                      {/* Actions */}
                      <div className="flex gap-2 pt-1">
                        {emergency.latitude && (
                          <Button
                            variant="outline"
                            className="flex-1 h-12 border-blue-500/30 text-blue-400 hover:bg-blue-500/10"
                            onClick={() => openInMaps(emergency.latitude, emergency.longitude)}
                          >
                            <Navigation className="w-4 h-4 mr-2" />
                            Mapa
                          </Button>
                        )}
                        <Button
                          className="flex-1 h-12 bg-green-600 hover:bg-green-700"
                          onClick={() => handleResolve(emergency.id)}
                          disabled={resolvingId === emergency.id}
                          data-testid={`resolve-${emergency.id}`}
                        >
                          {resolvingId === emergency.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <>
                              <CheckCircle className="w-4 h-4 mr-2" />
                              Resolver
                            </>
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </section>
          )}

          {/* Recent Resolved */}
          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
              <Clock className="w-4 h-4" />
              RESUELTOS RECIENTEMENTE
            </h2>
            
            {resolvedEmergencies.length > 0 ? (
              <div className="space-y-2">
                {resolvedEmergencies.map((emergency) => {
                  const config = PANIC_TYPE_CONFIG[emergency.panic_type] || PANIC_TYPE_CONFIG.emergencia_general;
                  
                  return (
                    <div 
                      key={emergency.id}
                      className="flex items-center gap-3 p-3 rounded-xl bg-[#0F111A] border border-[#1E293B]"
                    >
                      <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm truncate">{emergency.user_name}</span>
                          <Badge variant="outline" className={`text-[10px] ${config.textColor}`}>
                            {config.label}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground truncate">{emergency.location}</p>
                      </div>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatTime(emergency.resolved_at || emergency.created_at)}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <CheckCircle className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p className="text-sm">Sin eventos recientes</p>
              </div>
            )}
          </section>
        </main>
      </ScrollArea>

      {/* Emergency Call Footer */}
      <footer className="fixed bottom-0 left-0 right-0 p-3 bg-[#0F111A] border-t border-[#1E293B] safe-area-bottom">
        <a 
          href="tel:911" 
          className="flex items-center justify-center gap-2 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400"
        >
          <Phone className="w-5 h-5" />
          <span className="font-semibold">Llamar 911</span>
        </a>
      </footer>
    </div>
  );
};

export default GuardUI;
