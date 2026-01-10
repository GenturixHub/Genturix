import React, { useState, useEffect } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import api from '../services/api';
import { 
  AlertTriangle, 
  Shield, 
  Clock, 
  MapPin,
  User,
  CheckCircle,
  XCircle,
  Plus,
  Loader2,
  Eye,
  Activity
} from 'lucide-react';

const SecurityModule = () => {
  const [panicEvents, setPanicEvents] = useState([]);
  const [accessLogs, setAccessLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [panicDialogOpen, setPanicDialogOpen] = useState(false);
  const [accessDialogOpen, setAccessDialogOpen] = useState(false);
  const [panicLocation, setPanicLocation] = useState('');
  const [panicDescription, setPanicDescription] = useState('');
  const [accessForm, setAccessForm] = useState({
    person_name: '',
    access_type: 'entry',
    location: '',
    notes: ''
  });

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

  const handleTriggerPanic = async () => {
    try {
      await api.triggerPanic({
        location: panicLocation,
        description: panicDescription
      });
      setPanicDialogOpen(false);
      setPanicLocation('');
      setPanicDescription('');
      fetchData();
    } catch (error) {
      console.error('Error triggering panic:', error);
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
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-red-400" />
                  Eventos de Pánico
                </CardTitle>
                <CardDescription>Alertas de emergencia del sistema</CardDescription>
              </div>
              <Dialog open={panicDialogOpen} onOpenChange={setPanicDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="panic-button text-white" data-testid="trigger-panic-btn">
                    <AlertTriangle className="w-4 h-4 mr-2" />
                    Alerta
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-[#0F111A] border-[#1E293B]">
                  <DialogHeader>
                    <DialogTitle>Activar Alerta de Pánico</DialogTitle>
                    <DialogDescription>
                      Esta acción enviará una alerta inmediata al equipo de seguridad.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label>Ubicación</Label>
                      <Input
                        placeholder="Ej: Edificio A, Piso 3"
                        value={panicLocation}
                        onChange={(e) => setPanicLocation(e.target.value)}
                        className="bg-[#181B25] border-[#1E293B]"
                        data-testid="panic-location-input"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Descripción (opcional)</Label>
                      <Textarea
                        placeholder="Describe la situación..."
                        value={panicDescription}
                        onChange={(e) => setPanicDescription(e.target.value)}
                        className="bg-[#181B25] border-[#1E293B]"
                        data-testid="panic-description-input"
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setPanicDialogOpen(false)}>
                      Cancelar
                    </Button>
                    <Button 
                      className="bg-red-500 hover:bg-red-600" 
                      onClick={handleTriggerPanic}
                      disabled={!panicLocation}
                      data-testid="confirm-panic-btn"
                    >
                      Enviar Alerta
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                {panicEvents.length > 0 ? (
                  <div className="space-y-3">
                    {panicEvents.map((event) => (
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
                              <div className="flex items-center gap-2">
                                <span className="font-medium">{event.user_name}</span>
                                <Badge variant={event.status === 'active' ? 'destructive' : 'secondary'}>
                                  {event.status === 'active' ? 'ACTIVO' : 'Resuelto'}
                                </Badge>
                              </div>
                              <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                                <MapPin className="w-3 h-3" />
                                {event.location}
                              </div>
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
                    ))}
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
                <DialogTrigger asChild>
                  <Button variant="outline" className="border-[#1E293B]" data-testid="add-access-btn">
                    <Plus className="w-4 h-4 mr-2" />
                    Registrar
                  </Button>
                </DialogTrigger>
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
                          <div className="flex items-center gap-2">
                            <span className="font-medium truncate">{log.person_name}</span>
                            <Badge variant="outline" className="text-xs">
                              {log.access_type === 'entry' ? 'Entrada' : 'Salida'}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                            <MapPin className="w-3 h-3" />
                            {log.location}
                          </div>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {formatTime(log.timestamp)}
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
