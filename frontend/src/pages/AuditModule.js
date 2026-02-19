import React, { useState, useEffect } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import { useIsMobile } from '../components/layout/BottomNav';
import { MobileCard, MobileCardList } from '../components/MobileComponents';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { ScrollArea } from '../components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import api from '../services/api';
import { toast } from 'sonner';
import { 
  FileText, 
  Search,
  Filter,
  Clock,
  User,
  Activity,
  AlertTriangle,
  LogIn,
  LogOut,
  Loader2,
  Download,
  Globe
} from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AuditModule = () => {
  const isMobile = useIsMobile();
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [filters, setFilters] = useState({
    module: '',
    event_type: '',
    search: ''
  });

  const fetchData = async () => {
    try {
      const [logsData, statsData] = await Promise.all([
        api.getAuditLogs(filters.module || filters.event_type ? {
          module: filters.module || undefined,
          event_type: filters.event_type || undefined
        } : {}),
        api.getAuditStats()
      ]);
      setLogs(logsData);
      setStats(statsData);
    } catch (error) {
      console.error('Error fetching audit data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const applyFilters = () => {
    setIsLoading(true);
    fetchData();
  };

  const clearFilters = () => {
    setFilters({ module: '', event_type: '', search: '' });
    setIsLoading(true);
    fetchData();
  };

  // Export audit logs to PDF
  const handleExportPDF = async () => {
    setIsExporting(true);
    try {
      const accessToken = localStorage.getItem('access_token');
      if (!accessToken) {
        toast.error('No se encontró token de autenticación');
        return;
      }

      // Build query params from current filters
      const params = new URLSearchParams();
      if (filters.event_type) {
        params.append('event_type', filters.event_type);
      }

      const url = `${API_URL}/api/audit/export${params.toString() ? '?' + params.toString() : ''}`;
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Error al exportar');
      }

      // Get the blob from response
      const blob = await response.blob();
      
      // Create download link
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `audit-report-${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
      
      toast.success('Reporte PDF descargado exitosamente');
    } catch (error) {
      console.error('Error exporting PDF:', error);
      toast.error('Error al exportar el reporte PDF');
    } finally {
      setIsExporting(false);
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString('es-ES', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getEventIcon = (eventType) => {
    switch (eventType) {
      case 'login_success':
        return <LogIn className="w-4 h-4 text-green-400" />;
      case 'login_failure':
        return <LogIn className="w-4 h-4 text-red-400" />;
      case 'logout':
        return <LogOut className="w-4 h-4 text-blue-400" />;
      case 'panic_button':
        return <AlertTriangle className="w-4 h-4 text-red-400" />;
      case 'access_granted':
      case 'access_entry':
        return <LogIn className="w-4 h-4 text-cyan-400" />;
      case 'access_denied':
      case 'access_exit':
        return <LogOut className="w-4 h-4 text-orange-400" />;
      case 'payment_initiated':
      case 'payment_completed':
        return <Activity className="w-4 h-4 text-green-400" />;
      case 'course_enrolled':
        return <Activity className="w-4 h-4 text-cyan-400" />;
      default:
        return <Activity className="w-4 h-4 text-cyan-400" />;
    }
  };

  const getEventBadgeColor = (eventType) => {
    if (eventType.includes('success') || eventType.includes('granted')) return 'badge-success';
    if (eventType.includes('failure') || eventType.includes('denied') || eventType.includes('panic')) return 'badge-error';
    if (eventType.includes('created') || eventType.includes('updated')) return 'badge-info';
    return 'badge-warning';
  };

  // Helper function to get icon component for MobileCard
  const getEventIconComponent = (eventType) => {
    switch (eventType) {
      case 'login_success':
      case 'access_granted':
      case 'access_entry':
        return LogIn;
      case 'login_failure':
      case 'panic_button':
        return AlertTriangle;
      case 'logout':
      case 'access_denied':
      case 'access_exit':
        return LogOut;
      default:
        return Activity;
    }
  };

  // Helper function to get status color for MobileCard
  const getEventStatusColor = (eventType) => {
    if (eventType.includes('success') || eventType.includes('granted') || eventType.includes('completed')) return 'green';
    if (eventType.includes('failure') || eventType.includes('denied') || eventType.includes('panic')) return 'red';
    if (eventType.includes('created') || eventType.includes('enrolled')) return 'blue';
    return 'yellow';
  };

  const filteredLogs = logs.filter(log => {
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      return (
        log.event_type.toLowerCase().includes(searchLower) ||
        log.module.toLowerCase().includes(searchLower) ||
        log.user_id?.toLowerCase().includes(searchLower) ||
        JSON.stringify(log.details).toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  if (isLoading) {
    return (
      <DashboardLayout title="Auditoría">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Auditoría">
      <div className="space-y-6">
        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-cyan-500/20 text-cyan-400 flex items-center justify-center">
                  <FileText className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Eventos</p>
                  <p className="text-2xl font-bold">{stats?.total_events || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-blue-500/20 text-blue-400 flex items-center justify-center">
                  <Clock className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Eventos Hoy</p>
                  <p className="text-2xl font-bold">{stats?.today_events || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-red-500/20 text-red-400 flex items-center justify-center">
                  <LogIn className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Login Fallidos</p>
                  <p className="text-2xl font-bold">{stats?.login_failures || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-yellow-500/20 text-yellow-400 flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Eventos Pánico</p>
                  <p className="text-2xl font-bold">{stats?.panic_events || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="grid-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="w-5 h-5" />
              Filtros
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    placeholder="Buscar eventos..."
                    value={filters.search}
                    onChange={(e) => setFilters({...filters, search: e.target.value})}
                    className="pl-10 bg-[#181B25] border-[#1E293B]"
                    data-testid="audit-search"
                  />
                </div>
              </div>
              <Select 
                value={filters.module || "all"} 
                onValueChange={(v) => setFilters({...filters, module: v === "all" ? "" : v})}
              >
                <SelectTrigger className="w-[180px] bg-[#181B25] border-[#1E293B]" data-testid="module-filter">
                  <SelectValue placeholder="Módulo" />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="auth">Autenticación</SelectItem>
                  <SelectItem value="security">Seguridad</SelectItem>
                  <SelectItem value="access">Control de Acceso</SelectItem>
                  <SelectItem value="hr">Recursos Humanos</SelectItem>
                  <SelectItem value="school">Escuela</SelectItem>
                  <SelectItem value="payments">Pagos</SelectItem>
                </SelectContent>
              </Select>
              <Select 
                value={filters.event_type || "all"} 
                onValueChange={(v) => setFilters({...filters, event_type: v === "all" ? "" : v})}
              >
                <SelectTrigger className="w-[180px] bg-[#181B25] border-[#1E293B]" data-testid="event-type-filter">
                  <SelectValue placeholder="Tipo de evento" />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="login_success">Login Exitoso</SelectItem>
                  <SelectItem value="login_failure">Login Fallido</SelectItem>
                  <SelectItem value="logout">Logout</SelectItem>
                  <SelectItem value="panic_button">Botón Pánico</SelectItem>
                  <SelectItem value="access_granted">Entrada Visitante</SelectItem>
                  <SelectItem value="access_denied">Salida Visitante</SelectItem>
                  <SelectItem value="payment_completed">Pago Completado</SelectItem>
                  <SelectItem value="course_enrolled">Inscripción Curso</SelectItem>
                  <SelectItem value="user_created">Usuario Creado</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" onClick={applyFilters} className="border-[#1E293B]">
                Aplicar
              </Button>
              <Button variant="ghost" onClick={clearFilters}>
                Limpiar
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Logs Table/Cards */}
        <Card className="grid-card">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-400" />
                Registro de Auditoría
              </CardTitle>
              <CardDescription>
                {filteredLogs.length} eventos encontrados
              </CardDescription>
            </div>
            <Button 
              variant="outline" 
              className="border-[#1E293B]" 
              data-testid="export-logs-btn"
              onClick={handleExportPDF}
              disabled={isExporting}
            >
              {isExporting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Download className="w-4 h-4 mr-2" />
              )}
              <span className="hidden sm:inline">{isExporting ? 'Exportando...' : 'Exportar PDF'}</span>
            </Button>
          </CardHeader>
          <CardContent>
            {filteredLogs.length > 0 ? (
              <>
                {/* Desktop Table View - hidden on mobile */}
                <div className="hidden lg:block">
                  <ScrollArea className="h-[500px]">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-[#1E293B]">
                          <TableHead className="w-[180px]">Timestamp</TableHead>
                          <TableHead>Evento</TableHead>
                          <TableHead>Módulo</TableHead>
                          <TableHead>Usuario</TableHead>
                          <TableHead>IP</TableHead>
                          <TableHead>Detalles</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredLogs.map((log) => (
                          <TableRow key={log.id} className="border-[#1E293B]" data-testid={`audit-row-${log.id}`}>
                            <TableCell className="font-mono text-xs text-muted-foreground">
                              {formatTimestamp(log.timestamp)}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                {getEventIcon(log.event_type)}
                                <Badge className={getEventBadgeColor(log.event_type)}>
                                  {log.event_type.replace(/_/g, ' ')}
                                </Badge>
                              </div>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">{log.module}</Badge>
                            </TableCell>
                            <TableCell className="font-mono text-xs text-muted-foreground">
                              {log.user_id?.slice(0, 8) || 'N/A'}
                            </TableCell>
                            <TableCell className="font-mono text-xs text-muted-foreground">
                              {log.ip_address}
                            </TableCell>
                            <TableCell className="max-w-[200px] truncate text-xs text-muted-foreground">
                              {JSON.stringify(log.details)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                </div>

                {/* Mobile Card View */}
                <div className="block lg:hidden">
                  <ScrollArea className="h-[500px]">
                    <MobileCardList>
                      {filteredLogs.map((log) => (
                        <MobileCard
                          key={log.id}
                          testId={`audit-card-${log.id}`}
                          title={log.event_type.replace(/_/g, ' ')}
                          subtitle={formatTimestamp(log.timestamp)}
                          icon={getEventIconComponent(log.event_type)}
                          status={log.module}
                          statusColor={getEventStatusColor(log.event_type)}
                          details={[
                            { label: 'Usuario', value: log.user_id?.slice(0, 8) || 'N/A' },
                            { label: 'IP', value: log.ip_address || '-' },
                          ]}
                        >
                          {log.details && Object.keys(log.details).length > 0 && (
                            <div className="mt-3 pt-3 border-t border-[#1E293B]">
                              <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Detalles</p>
                              <p className="text-xs text-muted-foreground line-clamp-2">
                                {JSON.stringify(log.details)}
                              </p>
                            </div>
                          )}
                        </MobileCard>
                      ))}
                    </MobileCardList>
                  </ScrollArea>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <FileText className="w-12 h-12 mb-4" />
                <p>No hay eventos de auditoría</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default AuditModule;
