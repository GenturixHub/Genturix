import React, { useState, useEffect } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import api from '../services/api';
import { 
  Users, 
  UserPlus,
  Clock,
  DollarSign,
  Calendar,
  Phone,
  Mail,
  BadgeCheck,
  Loader2,
  Plus
} from 'lucide-react';

const HRModule = () => {
  const [guards, setGuards] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [payroll, setPayroll] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('guards');
  const [shiftDialogOpen, setShiftDialogOpen] = useState(false);
  const [shiftForm, setShiftForm] = useState({
    guard_id: '',
    start_time: '',
    end_time: '',
    location: '',
    notes: ''
  });

  const fetchData = async () => {
    try {
      const [guardsData, shiftsData, payrollData] = await Promise.all([
        api.getGuards(),
        api.getShifts(),
        api.getPayroll()
      ]);
      setGuards(guardsData);
      setShifts(shiftsData);
      setPayroll(payrollData);
    } catch (error) {
      console.error('Error fetching HR data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateShift = async () => {
    try {
      await api.createShift(shiftForm);
      setShiftDialogOpen(false);
      setShiftForm({ guard_id: '', start_time: '', end_time: '', location: '', notes: '' });
      fetchData();
    } catch (error) {
      console.error('Error creating shift:', error);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'USD' }).format(amount);
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const formatTime = (dateStr) => {
    return new Date(dateStr).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (isLoading) {
    return (
      <DashboardLayout title="Recursos Humanos">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Recursos Humanos">
      <div className="space-y-6">
        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-blue-500/20 text-blue-400 flex items-center justify-center">
                  <Users className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Guardas</p>
                  <p className="text-2xl font-bold">{guards.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-green-500/20 text-green-400 flex items-center justify-center">
                  <BadgeCheck className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Activos</p>
                  <p className="text-2xl font-bold">{guards.filter(g => g.is_active).length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-purple-500/20 text-purple-400 flex items-center justify-center">
                  <Calendar className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Turnos Programados</p>
                  <p className="text-2xl font-bold">{shifts.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-yellow-500/20 text-yellow-400 flex items-center justify-center">
                  <DollarSign className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Nómina Total</p>
                  <p className="text-2xl font-bold">
                    {formatCurrency(payroll.reduce((sum, p) => sum + p.total_pay, 0))}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-[#0F111A] border border-[#1E293B]">
            <TabsTrigger value="guards" data-testid="tab-guards">Guardas</TabsTrigger>
            <TabsTrigger value="shifts" data-testid="tab-shifts">Turnos</TabsTrigger>
            <TabsTrigger value="payroll" data-testid="tab-payroll">Nómina</TabsTrigger>
          </TabsList>

          {/* Guards Tab */}
          <TabsContent value="guards">
            <Card className="grid-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-blue-400" />
                  Lista de Guardas
                </CardTitle>
                <CardDescription>Gestión del personal de seguridad</CardDescription>
              </CardHeader>
              <CardContent>
                {guards.length > 0 ? (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-[#1E293B]">
                          <TableHead>Nombre</TableHead>
                          <TableHead>Badge</TableHead>
                          <TableHead>Email</TableHead>
                          <TableHead>Teléfono</TableHead>
                          <TableHead>Fecha Ingreso</TableHead>
                          <TableHead>Horas Trabajadas</TableHead>
                          <TableHead>Estado</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {guards.map((guard) => (
                          <TableRow key={guard.id} className="border-[#1E293B]" data-testid={`guard-row-${guard.id}`}>
                            <TableCell className="font-medium">{guard.user_name}</TableCell>
                            <TableCell>
                              <Badge variant="outline" className="font-mono">
                                {guard.badge_number}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-muted-foreground">{guard.email}</TableCell>
                            <TableCell className="text-muted-foreground">{guard.phone}</TableCell>
                            <TableCell className="text-muted-foreground">{formatDate(guard.hire_date)}</TableCell>
                            <TableCell>{guard.total_hours}h</TableCell>
                            <TableCell>
                              <Badge className={guard.is_active ? 'badge-success' : 'badge-error'}>
                                {guard.is_active ? 'Activo' : 'Inactivo'}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <Users className="w-12 h-12 mb-4" />
                    <p>No hay guardas registrados</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Shifts Tab */}
          <TabsContent value="shifts">
            <Card className="grid-card">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-purple-400" />
                    Turnos Programados
                  </CardTitle>
                  <CardDescription>Gestión de horarios y asignaciones</CardDescription>
                </div>
                <Dialog open={shiftDialogOpen} onOpenChange={setShiftDialogOpen}>
                  <DialogTrigger asChild>
                    <Button variant="outline" className="border-[#1E293B]" data-testid="add-shift-btn">
                      <Plus className="w-4 h-4 mr-2" />
                      Nuevo Turno
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="bg-[#0F111A] border-[#1E293B]">
                    <DialogHeader>
                      <DialogTitle>Crear Nuevo Turno</DialogTitle>
                      <DialogDescription>
                        Asigna un turno a un guarda de seguridad.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                      <div className="space-y-2">
                        <Label>Guarda</Label>
                        <select
                          className="w-full p-2 rounded-md bg-[#181B25] border border-[#1E293B]"
                          value={shiftForm.guard_id}
                          onChange={(e) => setShiftForm({...shiftForm, guard_id: e.target.value})}
                          data-testid="shift-guard-select"
                        >
                          <option value="">Seleccionar guarda...</option>
                          {guards.map((guard) => (
                            <option key={guard.id} value={guard.id}>
                              {guard.user_name} ({guard.badge_number})
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>Inicio</Label>
                          <Input
                            type="datetime-local"
                            value={shiftForm.start_time}
                            onChange={(e) => setShiftForm({...shiftForm, start_time: e.target.value})}
                            className="bg-[#181B25] border-[#1E293B]"
                            data-testid="shift-start-input"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Fin</Label>
                          <Input
                            type="datetime-local"
                            value={shiftForm.end_time}
                            onChange={(e) => setShiftForm({...shiftForm, end_time: e.target.value})}
                            className="bg-[#181B25] border-[#1E293B]"
                            data-testid="shift-end-input"
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>Ubicación</Label>
                        <Input
                          placeholder="Ej: Entrada Principal"
                          value={shiftForm.location}
                          onChange={(e) => setShiftForm({...shiftForm, location: e.target.value})}
                          className="bg-[#181B25] border-[#1E293B]"
                          data-testid="shift-location-input"
                        />
                      </div>
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setShiftDialogOpen(false)}>
                        Cancelar
                      </Button>
                      <Button 
                        onClick={handleCreateShift}
                        disabled={!shiftForm.guard_id || !shiftForm.start_time || !shiftForm.end_time || !shiftForm.location}
                        data-testid="confirm-shift-btn"
                      >
                        Crear Turno
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </CardHeader>
              <CardContent>
                {shifts.length > 0 ? (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-[#1E293B]">
                          <TableHead>Guarda</TableHead>
                          <TableHead>Ubicación</TableHead>
                          <TableHead>Inicio</TableHead>
                          <TableHead>Fin</TableHead>
                          <TableHead>Estado</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {shifts.map((shift) => (
                          <TableRow key={shift.id} className="border-[#1E293B]" data-testid={`shift-row-${shift.id}`}>
                            <TableCell className="font-medium">{shift.guard_name}</TableCell>
                            <TableCell className="text-muted-foreground">{shift.location}</TableCell>
                            <TableCell className="text-muted-foreground font-mono text-sm">
                              {formatTime(shift.start_time)}
                            </TableCell>
                            <TableCell className="text-muted-foreground font-mono text-sm">
                              {formatTime(shift.end_time)}
                            </TableCell>
                            <TableCell>
                              <Badge className={shift.status === 'active' ? 'badge-success' : 'badge-info'}>
                                {shift.status}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <Calendar className="w-12 h-12 mb-4" />
                    <p>No hay turnos programados</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Payroll Tab */}
          <TabsContent value="payroll">
            <Card className="grid-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-yellow-400" />
                  Nómina
                </CardTitle>
                <CardDescription>Resumen de pagos y horas trabajadas</CardDescription>
              </CardHeader>
              <CardContent>
                {payroll.length > 0 ? (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-[#1E293B]">
                          <TableHead>Guarda</TableHead>
                          <TableHead>Badge</TableHead>
                          <TableHead>Tarifa/Hora</TableHead>
                          <TableHead>Horas Trabajadas</TableHead>
                          <TableHead>Total a Pagar</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {payroll.map((item) => (
                          <TableRow key={item.guard_id} className="border-[#1E293B]" data-testid={`payroll-row-${item.guard_id}`}>
                            <TableCell className="font-medium">{item.guard_name}</TableCell>
                            <TableCell>
                              <Badge variant="outline" className="font-mono">
                                {item.badge_number}
                              </Badge>
                            </TableCell>
                            <TableCell className="font-mono">{formatCurrency(item.hourly_rate)}</TableCell>
                            <TableCell>{item.total_hours}h</TableCell>
                            <TableCell className="font-bold text-green-400">
                              {formatCurrency(item.total_pay)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <DollarSign className="w-12 h-12 mb-4" />
                    <p>No hay datos de nómina</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
};

export default HRModule;
