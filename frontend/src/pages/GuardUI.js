import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
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
  User,
  Phone,
  Loader2,
  RefreshCw,
  Heart,
  Search,
  Siren,
  Bell
} from 'lucide-react';

const PANIC_TYPE_CONFIG = {
  emergencia_medica: { icon: Heart, color: 'bg-red-500', label: 'MÉDICA' },
  actividad_sospechosa: { icon: Search, color: 'bg-yellow-500', label: 'SOSPECHOSO' },
  emergencia_general: { icon: Siren, color: 'bg-purple-500', label: 'GENERAL' }
};

const GuardUI = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [activeEmergencies, setActiveEmergencies] = useState([]);
  const [resolvedEmergencies, setResolvedEmergencies] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

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
    // Poll for new emergencies every 10 seconds
    const interval = setInterval(fetchEmergencies, 10000);
    return () => clearInterval(interval);
  }, [fetchEmergencies]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchEmergencies();
  };

  const handleResolve = async (eventId) => {
    try {
      await api.resolvePanic(eventId);
      fetchEmergencies();
    } catch (error) {
      console.error('Error resolving:', error);
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
    
    if (diffMins < 1) return 'Hace segundos';
    if (diffMins < 60) return `Hace ${diffMins} min`;
    return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  };

  const openInMaps = (lat, lng) => {
    if (lat && lng) {
      window.open(`https://www.google.com/maps?q=${lat},${lng}`, '_blank');
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#05050A] flex flex-col">
      {/* Header */}
      <header className="p-4 flex items-center justify-between border-b border-[#1E293B] bg-[#0F111A]">
        <div className="flex items-center gap-3">
          <Shield className="w-8 h-8 text-primary" />
          <div>
            <h1 className="text-lg font-bold font-['Outfit']">GENTURIX GUARD</h1>
            <p className="text-xs text-muted-foreground">{user?.full_name}</p>
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

      {/* Active Emergencies Count */}
      <div className={`p-4 ${activeEmergencies.length > 0 ? 'bg-red-500/10 border-b border-red-500/20' : 'bg-green-500/10 border-b border-green-500/20'}`}>
        <div className="flex items-center justify-center gap-3">
          {activeEmergencies.length > 0 ? (
            <>
              <Bell className="w-6 h-6 text-red-400 animate-pulse" />
              <span className="text-xl font-bold text-red-400">
                {activeEmergencies.length} EMERGENCIA{activeEmergencies.length > 1 ? 'S' : ''} ACTIVA{activeEmergencies.length > 1 ? 'S' : ''}
              </span>
            </>
          ) : (
            <>
              <CheckCircle className="w-6 h-6 text-green-400" />
              <span className="text-xl font-bold text-green-400">SIN EMERGENCIAS ACTIVAS</span>
            </>
          )}
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 p-4 overflow-auto">
        {/* Active Emergencies */}
        {activeEmergencies.length > 0 && (
          <div className="space-y-4 mb-8">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              Emergencias Activas
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
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-12 h-12 rounded-full ${config.color} flex items-center justify-center animate-pulse`}>
                          <IconComponent className="w-6 h-6 text-white" />
                        </div>
                        <div>
                          <Badge className={`${config.color} text-white mb-1`}>
                            {emergency.panic_type_label || config.label}
                          </Badge>
                          <CardTitle className="text-lg">{emergency.user_name}</CardTitle>
                        </div>
                      </div>
                      <span className="text-sm text-muted-foreground">
                        {formatTime(emergency.created_at)}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {/* Location */}
                    <div className="flex items-center gap-2 text-sm">
                      <MapPin className="w-4 h-4 text-muted-foreground" />
                      <span>{emergency.location}</span>
                    </div>
                    
                    {/* GPS Coordinates */}
                    {emergency.latitude && (
                      <button
                        onClick={() => openInMaps(emergency.latitude, emergency.longitude)}
                        className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        <Navigation className="w-4 h-4" />
                        <span className="font-mono">
                          {emergency.latitude.toFixed(6)}, {emergency.longitude.toFixed(6)}
                        </span>
                        <span className="text-xs">(Abrir mapa)</span>
                      </button>
                    )}

                    {/* Description */}
                    {emergency.description && (
                      <p className="text-sm text-muted-foreground">{emergency.description}</p>
                    )}

                    {/* Actions */}
                    <div className="flex gap-2 pt-2">
                      {emergency.latitude && (
                        <Button
                          variant="outline"
                          className="flex-1 border-blue-500/30 text-blue-400 hover:bg-blue-500/10"
                          onClick={() => openInMaps(emergency.latitude, emergency.longitude)}
                        >
                          <Navigation className="w-4 h-4 mr-2" />
                          Ver en Mapa
                        </Button>
                      )}
                      <Button
                        className="flex-1 bg-green-600 hover:bg-green-700"
                        onClick={() => handleResolve(emergency.id)}
                        data-testid={`resolve-${emergency.id}`}
                      >
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Resolver
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Recent Resolved */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold flex items-center gap-2 text-muted-foreground">
            <Clock className="w-5 h-5" />
            Resueltos Recientemente
          </h2>
          {resolvedEmergencies.length > 0 ? (
            <div className="space-y-2">
              {resolvedEmergencies.map((emergency) => {
                const config = PANIC_TYPE_CONFIG[emergency.panic_type] || PANIC_TYPE_CONFIG.emergencia_general;
                
                return (
                  <div 
                    key={emergency.id}
                    className="flex items-center gap-3 p-3 rounded-lg bg-muted/20 border border-[#1E293B]"
                  >
                    <CheckCircle className="w-5 h-5 text-green-400" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium truncate">{emergency.user_name}</span>
                        <Badge variant="outline" className="text-xs">{config.label}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">{emergency.location}</p>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {formatTime(emergency.resolved_at || emergency.created_at)}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">
              No hay eventos resueltos recientes
            </p>
          )}
        </div>
      </main>
    </div>
  );
};

export default GuardUI;
