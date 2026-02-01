import React, { useState, useEffect } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { ScrollArea } from '../components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import api from '../services/api';
import { toast } from 'sonner';
import { 
  AlertTriangle, 
  Shield, 
  Clock, 
  MapPin,
  CheckCircle,
  XCircle,
  Plus,
  Loader2,
  Eye,
  Activity,
  Heart,
  Search as SearchIcon,
  Siren,
  Navigation
} from 'lucide-react';

const PANIC_TYPES = {
  emergencia_medica: {
    label: '🚑 Emergencia Médica',
    icon: Heart,
    color: 'bg-red-600',
    description: 'Emergencia de salud que requiere atención médica inmediata'
  },
  actividad_sospechosa: {
    label: '👁️ Actividad Sospechosa',
    icon: SearchIcon,
    color: 'bg-yellow-600',
    description: 'Comportamiento o persona sospechosa que requiere verificación'
  },
  emergencia_general: {
    label: '🚨 Emergencia General',
    icon: Siren,
    color: 'bg-orange-600',
    description: 'Otra emergencia que requiere respuesta inmediata'
  }
};

const SecurityModule = () => {
  const [panicEvents, setPanicEvents] = useState([]);
  const [accessLogs, setAccessLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [panicDialogOpen, setPanicDialogOpen] = useState(false);
  const [accessDialogOpen, setAccessDialogOpen] = useState(false);
  const [selectedPanicType, setSelectedPanicType] = useState(null);
  const [panicForm, setPanicForm] = useState({
    location: '',
    description: '',
    latitude: null,
    longitude: null
  });
  const [accessForm, setAccessForm] = useState({
    person_name: '',
    access_type: 'entry',
    location: '',
    notes: ''
  });
  const [isGettingLocation, setIsGettingLocation] = useState(false);
  const [isSendingPanic, setIsSendingPanic] = useState(false);

  const fetchData = async () => {
    try {
      const [eventsData, logsData, statsData] = await Promise.all([
        api.getPanicEvents(),
        api.getAccessLogs(),
        api.getSecurityStats()
      ]);
      setPanicEvents(eventsData);
      setAccessLogs(logsData);
      setStats(statsData);
    } catch (error) {
      console.error('Error fetching security data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const getCurrentLocation = () => {
    setIsGettingLocation(true);
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setPanicForm({
            ...panicForm,
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
          });
          setIsGettingLocation(false);
        },
        (error) => {
          console.error('Error getting location:', error);
          setIsGettingLocation(false);
        }
      );
    } else {
      setIsGettingLocation(false);
    }
  };

  const handleSelectPanicType = (type) => {
    setSelectedPanicType(type);
    getCurrentLocation();
  };

  const handleTriggerPanic = async () => {
    if (!selectedPanicType || !panicForm.location) return;
    
    setIsSendingPanic(true);
    try {
      const result = await api.triggerPanic({
        panic_type: selectedPanicType,
        location: panicForm.location,
        latitude: panicForm.latitude,
        longitude: panicForm.longitude,
        description: panicForm.description
      });
      
      alert(`✅ Alerta enviada exitosamente!\n\nTipo: ${PANIC_TYPES[selectedPanicType].label}\nGuardas notificados: ${result.notified_guards}`);
      
      setPanicDialogOpen(false);
      setSelectedPanicType(null);
      setPanicForm({ location: '', description: '', latitude: null, longitude: null });
      fetchData();
    } catch (error) {
      console.error('Error triggering panic:', error);
      alert('Error al enviar alerta. Por favor intente de nuevo.');
    } finally {
      setIsSendingPanic(false);
    }
  };

  const handleResolvePanic = async (eventId) => {
    try {
      await api.resolvePanic(eventId);
      fetchData();
    } catch (error) {
      console.error('Error resolving panic:', error);
    }
  };

  const handleCreateAccessLog = async () => {
    try {
      await api.createAccessLog(accessForm);
      setAccessDialogOpen(false);
      setAccessForm({ person_name: '', access_type: 'entry', location: '', notes: '' });
      fetchData();
    } catch (error) {
      console.error('Error creating access log:', error);
    }
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleString('es-ES', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getPanicTypeInfo = (type) => {
    return PANIC_TYPES[type] || { label: type, color: 'bg-gray-600' };
  };

  if (isLoading) {
    return (
      <DashboardLayout title="Centro de Seguridad">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Centro de Seguridad">
      <div className="space-y-6">
        {/* Panic Button Section - 3 Types */}
        <Card className="grid-card border-2 border-red-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-400">
              <AlertTriangle className="w-6 h-6" />
              Botón de Pánico - GENTURIX
            </CardTitle>
            <CardDescription>
              Selecciona el tipo de emergencia. Tu ubicación será enviada automáticamente a los guardas.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              {Object.entries(PANIC_TYPES).map(([type, config]) => {
                const IconComponent = config.icon;
                return (
                  <Button
                    key={type}
                    className={`h-auto py-6 flex flex-col items-center gap-3 ${config.color} hover:opacity-90 text-white transition-all duration-200 hover:scale-[1.02]`}
                    onClick={() => {
                      handleSelectPanicType(type);
                      setPanicDialogOpen(true);
                    }}
                    data-testid={`panic-btn-${type}`}
                  >
                    <IconComponent className="w-10 h-10" />
                    <span className="text-lg font-bold">{config.label}</span>
                    <span className="text-xs opacity-80 text-center px-2">{config.description}</span>
                  </Button>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Panic Dialog */}
        <Dialog open={panicDialogOpen} onOpenChange={setPanicDialogOpen}>
          <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-red-400">
                <AlertTriangle className="w-5 h-5" />
                {selectedPanicType && PANIC_TYPES[selectedPanicType]?.label}
              </DialogTitle>
              <DialogDescription>
                Completa la información para enviar la alerta. Los guardas serán notificados inmediatamente.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {/* Location Status */}
              <div className="p-3 rounded-lg bg-muted/30 border border-[#1E293B]">
                <div className="flex items-center gap-2 text-sm">
                  <Navigation className="w-4 h-4 text-blue-400" />
                  <span className="text-muted-foreground">Ubicación GPS:</span>
                  {isGettingLocation ? (
                    <span className="flex items-center gap-1">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Obteniendo...
                    </span>
                  ) : panicForm.latitude ? (
                    <span className="text-green-400">✓ Capturada</span>
                  ) : (
                    <span className="text-yellow-400">No disponible</span>
                  )}
                </div>
                {panicForm.latitude && (
                  <p className="text-xs font-mono text-muted-foreground mt-1">
                    {panicForm.latitude.toFixed(6)}, {panicForm.longitude.toFixed(6)}
                  </p>
                )}
              </div>
              
              <div className="space-y-2">
                <Label>Ubicación / Descripción del lugar *</Label>
                <Input
                  placeholder="Ej: Edificio A, Piso 3, Apartamento 301"
                  value={panicForm.location}
                  onChange={(e) => setPanicForm({...panicForm, location: e.target.value})}
                  className="bg-[#181B25] border-[#1E293B]"
                  data-testid="panic-location-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Descripción adicional (opcional)</Label>
                <Textarea
                  placeholder="Describe brevemente la situación..."
                  value={panicForm.description}
                  onChange={(e) => setPanicForm({...panicForm, description: e.target.value})}
                  className="bg-[#181B25] border-[#1E293B]"
                  rows={3}
                  data-testid="panic-description-input"
                />
              </div>
            </div>
            <DialogFooter className="gap-2">
              <Button 
                variant="outline" 
                onClick={() => {
                  setPanicDialogOpen(false);
                  setSelectedPanicType(null);
                }}
              >
                Cancelar
              </Button>
              <Button 
                className="bg-red-600 hover:bg-red-700" 
                onClick={handleTriggerPanic}
                disabled={!panicForm.location || isSendingPanic}
                data-testid="confirm-panic-btn"
              >
                {isSendingPanic ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Enviando...
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-4 h-4 mr-2" />
                    ENVIAR ALERTA
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                  stats?.active_alerts > 0 ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'
                }`}>
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Alertas Activas</p>
                  <p className="text-2xl font-bold">{stats?.active_alerts || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-blue-500/20 text-blue-400 flex items-center justify-center">
                  <Activity className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Accesos Hoy</p>
                  <p className="text-2xl font-bold">{stats?.today_accesses || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-green-500/20 text-green-400 flex items-center justify-center">
                  <Shield className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Guardas Activos</p>
                  <p className="text-2xl font-bold">{stats?.active_guards || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-purple-500/20 text-purple-400 flex items-center justify-center">
                  <Eye className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Eventos</p>
                  <p className="text-2xl font-bold">{stats?.total_events || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Panic Events */}
          <Card className="grid-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-400" />
                Eventos de Pánico Recientes
              </CardTitle>
              <CardDescription>Historial de alertas de emergencia</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                {panicEvents.length > 0 ? (
                  <div className="space-y-3">
                    {panicEvents.map((event) => {
                      const typeInfo = getPanicTypeInfo(event.panic_type);
                      return (
                        <div 
                          key={event.id}
                          className={`p-4 rounded-lg border ${
                            event.status === 'active' 
                              ? 'bg-red-500/10 border-red-500/20' 
                              : 'bg-muted/30 border-[#1E293B]'
                          }`}
                          data-testid={`panic-event-${event.id}`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex items-start gap-3">
                              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                                event.status === 'active' ? 'bg-red-500/20 pulse-alert' : 'bg-green-500/20'
                              }`}>
                                {event.status === 'active' ? (
                                  <AlertTriangle className="w-5 h-5 text-red-400" />
                                ) : (
                                  <CheckCircle className="w-5 h-5 text-green-400" />
                                )}
                              </div>
                              <div>
                                <div className="flex items-center gap-2 flex-wrap">
                                  <Badge className={`${typeInfo.color} text-white`}>
                                    {event.panic_type_label || typeInfo.label}
                                  </Badge>
                                  <Badge variant={event.status === 'active' ? 'destructive' : 'secondary'}>
                                    {event.status === 'active' ? 'ACTIVO' : 'Resuelto'}
                                  </Badge>
                                </div>
                                <p className="font-medium mt-1">{event.user_name}</p>
                                <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                                  <MapPin className="w-3 h-3" />
                                  {event.location}
                                </div>
                                {event.latitude && (
                                  <p className="text-xs font-mono text-muted-foreground">
                                    GPS: {event.latitude.toFixed(4)}, {event.longitude.toFixed(4)}
                                  </p>
                                )}
                                {event.description && (
                                  <p className="text-sm text-muted-foreground mt-2">{event.description}</p>
                                )}
                                <p className="text-xs text-muted-foreground mt-2">
                                  <Clock className="w-3 h-3 inline mr-1" />
                                  {formatTime(event.created_at)}
                                </p>
                              </div>
                            </div>
                            {event.status === 'active' && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="border-green-500/20 text-green-400 hover:bg-green-500/10"
                                onClick={() => handleResolvePanic(event.id)}
                                data-testid={`resolve-panic-${event.id}`}
                              >
                                Resolver
                              </Button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                    <CheckCircle className="w-12 h-12 mb-4 text-green-400" />
                    <p>No hay eventos de pánico</p>
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Access Logs */}
          <Card className="grid-card">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-blue-400" />
                  Registro de Accesos
                </CardTitle>
                <CardDescription>Control de entradas y salidas</CardDescription>
              </div>
              <Dialog open={accessDialogOpen} onOpenChange={setAccessDialogOpen}>
                <Button 
                  variant="outline" 
                  className="border-[#1E293B]" 
                  data-testid="add-access-btn"
                  onClick={() => setAccessDialogOpen(true)}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Registrar
                </Button>
                <DialogContent className="bg-[#0F111A] border-[#1E293B]">
                  <DialogHeader>
                    <DialogTitle>Registrar Acceso</DialogTitle>
                    <DialogDescription>
                      Registra una entrada o salida en el sistema.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label>Nombre de la Persona</Label>
                      <Input
                        placeholder="Nombre completo"
                        value={accessForm.person_name}
                        onChange={(e) => setAccessForm({...accessForm, person_name: e.target.value})}
                        className="bg-[#181B25] border-[#1E293B]"
                        data-testid="access-name-input"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Tipo de Acceso</Label>
                      <Select 
                        value={accessForm.access_type} 
                        onValueChange={(v) => setAccessForm({...accessForm, access_type: v})}
                      >
                        <SelectTrigger className="bg-[#181B25] border-[#1E293B]" data-testid="access-type-select">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                          <SelectItem value="entry">Entrada</SelectItem>
                          <SelectItem value="exit">Salida</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Ubicación</Label>
                      <Input
                        placeholder="Ej: Entrada Principal"
                        value={accessForm.location}
                        onChange={(e) => setAccessForm({...accessForm, location: e.target.value})}
                        className="bg-[#181B25] border-[#1E293B]"
                        data-testid="access-location-input"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Notas (opcional)</Label>
                      <Textarea
                        placeholder="Observaciones adicionales..."
                        value={accessForm.notes}
                        onChange={(e) => setAccessForm({...accessForm, notes: e.target.value})}
                        className="bg-[#181B25] border-[#1E293B]"
                        data-testid="access-notes-input"
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setAccessDialogOpen(false)}>
                      Cancelar
                    </Button>
                    <Button 
                      onClick={handleCreateAccessLog}
                      disabled={!accessForm.person_name || !accessForm.location}
                      data-testid="confirm-access-btn"
                    >
                      Registrar
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                {accessLogs.length > 0 ? (
                  <div className="space-y-2">
                    {accessLogs.map((log) => (
                      <div 
                        key={log.id}
                        className="flex items-center gap-4 p-3 rounded-lg bg-muted/30 border border-[#1E293B]"
                        data-testid={`access-log-${log.id}`}
                      >
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          log.access_type === 'entry' ? 'bg-green-500/20' : 'bg-orange-500/20'
                        }`}>
                          {log.access_type === 'entry' ? (
                            <CheckCircle className="w-5 h-5 text-green-400" />
                          ) : (
                            <XCircle className="w-5 h-5 text-orange-400" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium truncate">{log.person_name}</span>
                            <Badge variant="outline" className="text-xs">
                              {log.access_type === 'entry' ? 'Entrada' : 'Salida'}
                            </Badge>
                            {log.entry_type && log.entry_type !== 'manual' && (
                              <Badge 
                                variant="secondary" 
                                className={`text-[10px] ${
                                  log.entry_type === 'permanent' ? 'bg-green-500/20 text-green-400' :
                                  log.entry_type === 'temporary' ? 'bg-yellow-500/20 text-yellow-400' :
                                  log.entry_type === 'recurring' ? 'bg-blue-500/20 text-blue-400' :
                                  'bg-purple-500/20 text-purple-400'
                                }`}
                              >
                                {log.entry_type === 'permanent' ? 'Permanente' :
                                 log.entry_type === 'temporary' ? 'Temporal' :
                                 log.entry_type === 'recurring' ? 'Recurrente' :
                                 log.entry_type === 'extended' ? 'Extendido' :
                                 log.entry_type}
                              </Badge>
                            )}
                            {log.is_authorized === false && (
                              <Badge variant="destructive" className="text-[10px]">No autorizado</Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1 flex-wrap">
                            <span className="flex items-center gap-1">
                              <MapPin className="w-3 h-3" />
                              {log.location || log.destination || 'Sin ubicación'}
                            </span>
                            {log.guard_name && (
                              <span className="flex items-center gap-1">
                                <Shield className="w-3 h-3" />
                                {log.guard_name}
                              </span>
                            )}
                            {log.resident_name && (
                              <span className="text-primary">Autorizado por: {log.resident_name}</span>
                            )}
                            {log.vehicle_plate && (
                              <span>🚗 {log.vehicle_plate}</span>
                            )}
                          </div>
                        </div>
                        <div className="text-xs text-muted-foreground text-right">
                          <div>{formatTime(log.timestamp)}</div>
                          {log.exit_timestamp && (
                            <div className="text-orange-400">Salió: {formatTime(log.exit_timestamp)}</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                    <Shield className="w-12 h-12 mb-4" />
                    <p>No hay registros de acceso</p>
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Monitoring Section */}
        <Card className="grid-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="w-5 h-5 text-purple-400" />
              Centro de Monitoreo
            </CardTitle>
            <CardDescription>Feeds de cámaras y monitoreo en tiempo real</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-4">
              {[1, 2, 3, 4].map((cam) => (
                <div key={cam} className="aspect-video rounded-lg bg-[#181B25] border border-[#1E293B] overflow-hidden relative">
                  <img 
                    src="https://images.pexels.com/photos/18485666/pexels-photo-18485666.jpeg"
                    alt={`Camera ${cam}`}
                    className="w-full h-full object-cover opacity-60"
                  />
                  <div className="absolute bottom-2 left-2 flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                    <span className="text-xs font-mono">CAM-{String(cam).padStart(2, '0')}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default SecurityModule;
