/**
 * GENTURIX - Reservations Module
 * Common areas booking system
 * 
 * Features:
 * - Admin: CRUD areas, approve/reject reservations
 * - Resident: View areas, create reservations, see status
 * - Guard: View today's reservations (read-only)
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Textarea } from '../components/ui/textarea';
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
import {
  Calendar,
  Clock,
  Users,
  MapPin,
  Plus,
  CheckCircle,
  XCircle,
  Loader2,
  Waves,
  Dumbbell,
  CircleDot,
  Flame,
  Building,
  Film,
  TreePine,
  MoreHorizontal,
  Edit,
  Trash2,
  AlertCircle
} from 'lucide-react';

// Area type icons
const AREA_ICONS = {
  pool: Waves,
  gym: Dumbbell,
  tennis: CircleDot,
  bbq: Flame,
  salon: Building,
  cinema: Film,
  playground: TreePine,
  other: MoreHorizontal
};

const AREA_LABELS = {
  pool: 'Piscina',
  gym: 'Gimnasio',
  tennis: 'Cancha de Tenis',
  bbq: 'Área BBQ',
  salon: 'Salón de Eventos',
  cinema: 'Sala de Cine',
  playground: 'Área de Juegos',
  other: 'Otro'
};

const STATUS_CONFIG = {
  pending: { label: 'Pendiente', color: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30' },
  approved: { label: 'Aprobada', color: 'bg-green-500/10 text-green-400 border-green-500/30' },
  rejected: { label: 'Rechazada', color: 'bg-red-500/10 text-red-400 border-red-500/30' },
  cancelled: { label: 'Cancelada', color: 'bg-gray-500/10 text-gray-400 border-gray-500/30' },
  completed: { label: 'Completada', color: 'bg-blue-500/10 text-blue-400 border-blue-500/30' }
};

const ReservationsModule = () => {
  const { user, hasRole } = useAuth();
  const isAdmin = hasRole('Administrador');
  const isGuard = hasRole('Guarda');
  
  const [areas, setAreas] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState(isAdmin ? 'areas' : 'reserve');
  
  // Dialogs
  const [showAreaDialog, setShowAreaDialog] = useState(false);
  const [showReservationDialog, setShowReservationDialog] = useState(false);
  const [editingArea, setEditingArea] = useState(null);
  const [selectedArea, setSelectedArea] = useState(null);
  
  // Form states
  const [areaForm, setAreaForm] = useState({
    name: '',
    area_type: 'pool',
    capacity: 10,
    description: '',
    rules: '',
    available_from: '06:00',
    available_until: '22:00',
    requires_approval: false,
    max_hours_per_reservation: 2
  });
  
  const [reservationForm, setReservationForm] = useState({
    area_id: '',
    date: '',
    start_time: '',
    end_time: '',
    purpose: '',
    guests_count: 1
  });
  
  const [isSaving, setIsSaving] = useState(false);

  // Fetch data
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [areasData, reservationsData] = await Promise.all([
          api.getAreas(),
          isGuard ? api.getTodayReservations() : api.getReservations()
        ]);
        setAreas(areasData);
        setReservations(reservationsData);
      } catch (err) {
        console.error('Error fetching reservations data:', err);
        if (err.status === 403) {
          setError('El módulo de Reservaciones no está habilitado para este condominio');
        } else {
          setError(err.message || 'Error al cargar datos');
        }
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchData();
  }, [isGuard]);

  // Area CRUD
  const handleSaveArea = async () => {
    setIsSaving(true);
    try {
      if (editingArea) {
        await api.updateArea(editingArea.id, areaForm);
      } else {
        await api.createArea(areaForm);
      }
      const areasData = await api.getAreas();
      setAreas(areasData);
      setShowAreaDialog(false);
      resetAreaForm();
    } catch (err) {
      setError(err.message || 'Error al guardar área');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteArea = async (areaId) => {
    if (!confirm('¿Estás seguro de eliminar esta área?')) return;
    try {
      await api.deleteArea(areaId);
      setAreas(areas.filter(a => a.id !== areaId));
    } catch (err) {
      setError(err.message || 'Error al eliminar área');
    }
  };

  const resetAreaForm = () => {
    setAreaForm({
      name: '',
      area_type: 'pool',
      capacity: 10,
      description: '',
      rules: '',
      available_from: '06:00',
      available_until: '22:00',
      requires_approval: false,
      max_hours_per_reservation: 2
    });
    setEditingArea(null);
  };

  // Reservation CRUD
  const handleCreateReservation = async () => {
    setIsSaving(true);
    try {
      await api.createReservation(reservationForm);
      const reservationsData = await api.getReservations();
      setReservations(reservationsData);
      setShowReservationDialog(false);
      setReservationForm({
        area_id: '',
        date: '',
        start_time: '',
        end_time: '',
        purpose: '',
        guests_count: 1
      });
    } catch (err) {
      setError(err.message || 'Error al crear reservación');
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateReservationStatus = async (reservationId, status, adminNotes = '') => {
    try {
      await api.updateReservationStatus(reservationId, { status, admin_notes: adminNotes });
      const reservationsData = await api.getReservations();
      setReservations(reservationsData);
    } catch (err) {
      setError(err.message || 'Error al actualizar reservación');
    }
  };

  if (isLoading) {
    return (
      <DashboardLayout title="Reservaciones">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  if (error && error.includes('no está habilitado')) {
    return (
      <DashboardLayout title="Reservaciones">
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-8 text-center">
            <AlertCircle className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Módulo No Disponible</h3>
            <p className="text-muted-foreground">{error}</p>
          </CardContent>
        </Card>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Reservaciones - Áreas Comunes">
      <div className="space-y-6">
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-2">
            <XCircle className="w-4 h-4" />
            {error}
            <Button variant="ghost" size="sm" className="ml-auto" onClick={() => setError(null)}>
              Cerrar
            </Button>
          </div>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-[#0F111A] border border-[#1E293B]">
            {isAdmin && (
              <TabsTrigger value="areas" data-testid="tab-areas">
                <MapPin className="w-4 h-4 mr-2" />
                Áreas
              </TabsTrigger>
            )}
            {!isGuard && (
              <TabsTrigger value="reserve" data-testid="tab-reserve">
                <Calendar className="w-4 h-4 mr-2" />
                Reservar
              </TabsTrigger>
            )}
            <TabsTrigger value="my-reservations" data-testid="tab-my-reservations">
              <Clock className="w-4 h-4 mr-2" />
              {isGuard ? 'Hoy' : 'Mis Reservaciones'}
            </TabsTrigger>
            {isAdmin && (
              <TabsTrigger value="pending" data-testid="tab-pending">
                <AlertCircle className="w-4 h-4 mr-2" />
                Pendientes
              </TabsTrigger>
            )}
          </TabsList>

          {/* AREAS TAB (Admin) */}
          {isAdmin && (
            <TabsContent value="areas" className="mt-4">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold">Gestionar Áreas</h2>
                <Button onClick={() => { resetAreaForm(); setShowAreaDialog(true); }} data-testid="create-area-btn">
                  <Plus className="w-4 h-4 mr-2" />
                  Nueva Área
                </Button>
              </div>
              
              {areas.length === 0 ? (
                <Card className="bg-[#0F111A] border-[#1E293B]">
                  <CardContent className="p-8 text-center">
                    <MapPin className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">No hay áreas configuradas</p>
                    <p className="text-sm text-muted-foreground mt-1">Crea la primera área común</p>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {areas.map((area) => {
                    const AreaIcon = AREA_ICONS[area.area_type] || MoreHorizontal;
                    return (
                      <Card key={area.id} className="bg-[#0F111A] border-[#1E293B]">
                        <CardHeader className="pb-2">
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-2">
                              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                                <AreaIcon className="w-5 h-5 text-primary" />
                              </div>
                              <div>
                                <CardTitle className="text-base">{area.name}</CardTitle>
                                <CardDescription>{AREA_LABELS[area.area_type]}</CardDescription>
                              </div>
                            </div>
                            <div className="flex gap-1">
                              <Button 
                                variant="ghost" 
                                size="icon"
                                onClick={() => { setEditingArea(area); setAreaForm(area); setShowAreaDialog(true); }}
                              >
                                <Edit className="w-4 h-4" />
                              </Button>
                              <Button variant="ghost" size="icon" onClick={() => handleDeleteArea(area.id)}>
                                <Trash2 className="w-4 h-4 text-red-400" />
                              </Button>
                            </div>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Capacidad</span>
                              <span>{area.capacity} personas</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Horario</span>
                              <span>{area.available_from} - {area.available_until}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Aprobación</span>
                              <Badge variant="outline" className={area.requires_approval ? 'border-yellow-500 text-yellow-400' : 'border-green-500 text-green-400'}>
                                {area.requires_approval ? 'Requerida' : 'Automática'}
                              </Badge>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              )}
            </TabsContent>
          )}

          {/* RESERVE TAB (Resident) */}
          {!isGuard && (
            <TabsContent value="reserve" className="mt-4">
              <h2 className="text-lg font-semibold mb-4">Reservar Área Común</h2>
              
              {areas.length === 0 ? (
                <Card className="bg-[#0F111A] border-[#1E293B]">
                  <CardContent className="p-8 text-center">
                    <MapPin className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">No hay áreas disponibles para reservar</p>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {areas.map((area) => {
                    const AreaIcon = AREA_ICONS[area.area_type] || MoreHorizontal;
                    return (
                      <Card 
                        key={area.id} 
                        className="bg-[#0F111A] border-[#1E293B] hover:border-primary/50 transition-colors cursor-pointer"
                        onClick={() => { setSelectedArea(area); setReservationForm({ ...reservationForm, area_id: area.id }); setShowReservationDialog(true); }}
                        data-testid={`area-card-${area.id}`}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                              <AreaIcon className="w-6 h-6 text-primary" />
                            </div>
                            <div className="flex-1">
                              <h3 className="font-medium">{area.name}</h3>
                              <p className="text-sm text-muted-foreground">{AREA_LABELS[area.area_type]}</p>
                              <div className="flex items-center gap-2 mt-1">
                                <Badge variant="outline" className="text-xs">
                                  <Users className="w-3 h-3 mr-1" />
                                  {area.capacity}
                                </Badge>
                                <Badge variant="outline" className="text-xs">
                                  <Clock className="w-3 h-3 mr-1" />
                                  {area.available_from}-{area.available_until}
                                </Badge>
                              </div>
                            </div>
                          </div>
                          {area.description && (
                            <p className="text-sm text-muted-foreground mt-3 line-clamp-2">{area.description}</p>
                          )}
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              )}
            </TabsContent>
          )}

          {/* MY RESERVATIONS / TODAY TAB */}
          <TabsContent value="my-reservations" className="mt-4">
            <h2 className="text-lg font-semibold mb-4">
              {isGuard ? 'Reservaciones de Hoy' : 'Mis Reservaciones'}
            </h2>
            
            {reservations.length === 0 ? (
              <Card className="bg-[#0F111A] border-[#1E293B]">
                <CardContent className="p-8 text-center">
                  <Calendar className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">
                    {isGuard ? 'No hay reservaciones para hoy' : 'No tienes reservaciones'}
                  </p>
                </CardContent>
              </Card>
            ) : (
              <ScrollArea className="h-[500px]">
                <div className="space-y-3">
                  {reservations.map((res) => {
                    const statusConfig = STATUS_CONFIG[res.status] || STATUS_CONFIG.pending;
                    const AreaIcon = AREA_ICONS[res.area_type] || MoreHorizontal;
                    return (
                      <Card key={res.id} className="bg-[#0F111A] border-[#1E293B]">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                                <AreaIcon className="w-5 h-5 text-primary" />
                              </div>
                              <div>
                                <h3 className="font-medium">{res.area_name}</h3>
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                  <Calendar className="w-3 h-3" />
                                  {res.date}
                                  <Clock className="w-3 h-3 ml-2" />
                                  {res.start_time} - {res.end_time}
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge className={statusConfig.color}>
                                {statusConfig.label}
                              </Badge>
                              {!isGuard && res.status === 'pending' && (
                                <Button 
                                  variant="ghost" 
                                  size="sm"
                                  className="text-red-400"
                                  onClick={() => handleUpdateReservationStatus(res.id, 'cancelled')}
                                >
                                  Cancelar
                                </Button>
                              )}
                            </div>
                          </div>
                          {isGuard && res.resident_name && (
                            <div className="flex items-center gap-2 mt-3 pt-3 border-t border-[#1E293B]">
                              <Avatar className="w-6 h-6">
                                <AvatarImage src={res.resident_photo} />
                                <AvatarFallback className="text-xs">{res.resident_name?.charAt(0)}</AvatarFallback>
                              </Avatar>
                              <span className="text-sm">{res.resident_name}</span>
                              <Badge variant="outline" className="ml-auto text-xs">
                                <Users className="w-3 h-3 mr-1" />
                                {res.guests_count} personas
                              </Badge>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              </ScrollArea>
            )}
          </TabsContent>

          {/* PENDING TAB (Admin) */}
          {isAdmin && (
            <TabsContent value="pending" className="mt-4">
              <h2 className="text-lg font-semibold mb-4">Reservaciones Pendientes</h2>
              
              {reservations.filter(r => r.status === 'pending').length === 0 ? (
                <Card className="bg-[#0F111A] border-[#1E293B]">
                  <CardContent className="p-8 text-center">
                    <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
                    <p className="text-muted-foreground">No hay reservaciones pendientes</p>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-3">
                  {reservations.filter(r => r.status === 'pending').map((res) => {
                    const AreaIcon = AREA_ICONS[res.area_type] || MoreHorizontal;
                    return (
                      <Card key={res.id} className="bg-[#0F111A] border-[#1E293B]">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <Avatar className="w-10 h-10">
                                <AvatarImage src={res.resident_photo} />
                                <AvatarFallback>{res.resident_name?.charAt(0)}</AvatarFallback>
                              </Avatar>
                              <div>
                                <h3 className="font-medium">{res.resident_name}</h3>
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                  <AreaIcon className="w-3 h-3" />
                                  {res.area_name}
                                  <Calendar className="w-3 h-3 ml-2" />
                                  {res.date}
                                  <Clock className="w-3 h-3 ml-2" />
                                  {res.start_time}-{res.end_time}
                                </div>
                              </div>
                            </div>
                            <div className="flex gap-2">
                              <Button 
                                size="sm" 
                                variant="outline"
                                className="border-red-500 text-red-400 hover:bg-red-500/10"
                                onClick={() => handleUpdateReservationStatus(res.id, 'rejected')}
                              >
                                <XCircle className="w-4 h-4 mr-1" />
                                Rechazar
                              </Button>
                              <Button 
                                size="sm"
                                className="bg-green-600 hover:bg-green-700"
                                onClick={() => handleUpdateReservationStatus(res.id, 'approved')}
                              >
                                <CheckCircle className="w-4 h-4 mr-1" />
                                Aprobar
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              )}
            </TabsContent>
          )}
        </Tabs>
      </div>

      {/* Area Dialog */}
      <Dialog open={showAreaDialog} onOpenChange={setShowAreaDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B]">
          <DialogHeader>
            <DialogTitle>{editingArea ? 'Editar Área' : 'Nueva Área'}</DialogTitle>
            <DialogDescription>Configure los detalles del área común</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Nombre</Label>
                <Input 
                  value={areaForm.name}
                  onChange={(e) => setAreaForm({ ...areaForm, name: e.target.value })}
                  placeholder="Ej: Piscina Principal"
                  className="bg-[#0A0A0F] border-[#1E293B]"
                />
              </div>
              <div className="space-y-2">
                <Label>Tipo</Label>
                <Select value={areaForm.area_type} onValueChange={(v) => setAreaForm({ ...areaForm, area_type: v })}>
                  <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(AREA_LABELS).map(([key, label]) => (
                      <SelectItem key={key} value={key}>{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Capacidad</Label>
                <Input 
                  type="number"
                  value={areaForm.capacity}
                  onChange={(e) => setAreaForm({ ...areaForm, capacity: parseInt(e.target.value) || 1 })}
                  className="bg-[#0A0A0F] border-[#1E293B]"
                />
              </div>
              <div className="space-y-2">
                <Label>Desde</Label>
                <Input 
                  type="time"
                  value={areaForm.available_from}
                  onChange={(e) => setAreaForm({ ...areaForm, available_from: e.target.value })}
                  className="bg-[#0A0A0F] border-[#1E293B]"
                />
              </div>
              <div className="space-y-2">
                <Label>Hasta</Label>
                <Input 
                  type="time"
                  value={areaForm.available_until}
                  onChange={(e) => setAreaForm({ ...areaForm, available_until: e.target.value })}
                  className="bg-[#0A0A0F] border-[#1E293B]"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Descripción</Label>
              <Textarea 
                value={areaForm.description || ''}
                onChange={(e) => setAreaForm({ ...areaForm, description: e.target.value })}
                placeholder="Descripción del área..."
                className="bg-[#0A0A0F] border-[#1E293B]"
              />
            </div>
            <div className="flex items-center gap-2">
              <input 
                type="checkbox"
                checked={areaForm.requires_approval}
                onChange={(e) => setAreaForm({ ...areaForm, requires_approval: e.target.checked })}
                className="rounded border-[#1E293B]"
              />
              <Label>Requiere aprobación del administrador</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAreaDialog(false)}>Cancelar</Button>
            <Button onClick={handleSaveArea} disabled={isSaving || !areaForm.name}>
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : (editingArea ? 'Guardar' : 'Crear')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reservation Dialog */}
      <Dialog open={showReservationDialog} onOpenChange={setShowReservationDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B]">
          <DialogHeader>
            <DialogTitle>Reservar: {selectedArea?.name}</DialogTitle>
            <DialogDescription>
              {selectedArea?.description || `${AREA_LABELS[selectedArea?.area_type]} - Capacidad: ${selectedArea?.capacity} personas`}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Fecha</Label>
              <Input 
                type="date"
                value={reservationForm.date}
                onChange={(e) => setReservationForm({ ...reservationForm, date: e.target.value })}
                min={new Date().toISOString().split('T')[0]}
                className="bg-[#0A0A0F] border-[#1E293B]"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Hora Inicio</Label>
                <Input 
                  type="time"
                  value={reservationForm.start_time}
                  onChange={(e) => setReservationForm({ ...reservationForm, start_time: e.target.value })}
                  min={selectedArea?.available_from}
                  max={selectedArea?.available_until}
                  className="bg-[#0A0A0F] border-[#1E293B]"
                />
              </div>
              <div className="space-y-2">
                <Label>Hora Fin</Label>
                <Input 
                  type="time"
                  value={reservationForm.end_time}
                  onChange={(e) => setReservationForm({ ...reservationForm, end_time: e.target.value })}
                  min={reservationForm.start_time || selectedArea?.available_from}
                  max={selectedArea?.available_until}
                  className="bg-[#0A0A0F] border-[#1E293B]"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Número de Invitados</Label>
              <Input 
                type="number"
                value={reservationForm.guests_count}
                onChange={(e) => setReservationForm({ ...reservationForm, guests_count: parseInt(e.target.value) || 1 })}
                min={1}
                max={selectedArea?.capacity || 50}
                className="bg-[#0A0A0F] border-[#1E293B]"
              />
            </div>
            <div className="space-y-2">
              <Label>Propósito (opcional)</Label>
              <Input 
                value={reservationForm.purpose || ''}
                onChange={(e) => setReservationForm({ ...reservationForm, purpose: e.target.value })}
                placeholder="Ej: Fiesta de cumpleaños"
                className="bg-[#0A0A0F] border-[#1E293B]"
              />
            </div>
            {selectedArea?.requires_approval && (
              <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-sm">
                <AlertCircle className="w-4 h-4 inline mr-2" />
                Esta área requiere aprobación del administrador
              </div>
            )}
            {selectedArea?.rules && (
              <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-sm">
                <p className="font-medium mb-1">Reglas del área:</p>
                <p className="text-muted-foreground">{selectedArea.rules}</p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowReservationDialog(false)}>Cancelar</Button>
            <Button 
              onClick={handleCreateReservation} 
              disabled={isSaving || !reservationForm.date || !reservationForm.start_time || !reservationForm.end_time}
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Reservar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
};

export default ReservationsModule;
