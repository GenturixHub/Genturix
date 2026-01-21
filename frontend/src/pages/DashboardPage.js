import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import { useIsMobile } from '../components/layout/BottomNav';
import api from '../services/api';
import { 
  Users, 
  Shield, 
  AlertTriangle, 
  GraduationCap,
  CreditCard,
  Activity,
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  ChevronRight
} from 'lucide-react';

const StatCard = ({ title, value, icon: Icon, trend, color = 'primary', onClick }) => {
  const colorClasses = {
    primary: 'bg-primary/10 text-primary',
    success: 'bg-green-500/10 text-green-400',
    warning: 'bg-yellow-500/10 text-yellow-400',
    error: 'bg-red-500/10 text-red-400',
    info: 'bg-blue-500/10 text-blue-400',
  };

  return (
    <Card 
      className={`grid-card ${onClick ? 'cursor-pointer hover:border-primary' : ''}`}
      onClick={onClick}
    >
      <CardContent className="p-4 md:p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 md:block">
            <div className={`w-10 h-10 md:w-12 md:h-12 rounded-lg ${colorClasses[color]} flex items-center justify-center md:mb-3`}>
              <Icon className="w-5 h-5 md:w-6 md:h-6" />
            </div>
            <div>
              <p className="text-xs md:text-sm text-muted-foreground">{title}</p>
              <p className="text-xl md:text-3xl font-bold font-['Outfit']">{value}</p>
            </div>
          </div>
          {trend && (
            <div className="flex items-center gap-1 text-xs text-green-400">
              <TrendingUp className="w-3 h-3" />
              <span>{trend}</span>
            </div>
          )}
          {onClick && (
            <ChevronRight className="w-5 h-5 text-muted-foreground md:hidden" />
          )}
        </div>
      </CardContent>
    </Card>
  );
};

const ActivityItem = ({ activity }) => {
  const getIcon = (type) => {
    switch (type) {
      case 'login_success':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'login_failure':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'panic_button':
        return <AlertTriangle className="w-4 h-4 text-red-400" />;
      default:
        return <Activity className="w-4 h-4 text-blue-400" />;
    }
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Ahora';
    if (diffMins < 60) return `${diffMins}m`;
    if (diffMins < 1440) return `${Math.floor(diffMins/60)}h`;
    return date.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
  };

  return (
    <div className="flex items-center gap-3 py-3 border-b border-[#1E293B] last:border-0">
      <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
        {getIcon(activity.event_type)}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm truncate">{activity.event_type.replace(/_/g, ' ')}</p>
        <p className="text-xs text-muted-foreground">{activity.module}</p>
      </div>
      <span className="text-xs text-muted-foreground whitespace-nowrap">
        {formatTime(activity.timestamp)}
      </span>
    </div>
  );
};

const DashboardPage = () => {
  const navigate = useNavigate();
  const { user, hasRole } = useAuth();
  const isMobile = useIsMobile();
  const [stats, setStats] = useState(null);
  const [activities, setActivities] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsData, activityData] = await Promise.all([
          api.getDashboardStats(),
          api.getRecentActivity()
        ]);
        setStats(statsData);
        setActivities(activityData);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const handlePanicButton = async () => {
    try {
      await api.triggerPanic({
        location: 'Dashboard - Admin Emergency',
        description: 'Emergency panic button pressed from admin dashboard'
      });
      alert('Alerta de pánico enviada. El equipo de seguridad ha sido notificado.');
    } catch (error) {
      console.error('Error triggering panic:', error);
      alert('Error al enviar alerta.');
    }
  };

  if (isLoading) {
    return (
      <DashboardLayout title="Dashboard">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Dashboard">
      <div className="space-y-4 md:space-y-6">
        {/* Welcome - Mobile compact */}
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-xl md:text-2xl font-bold font-['Outfit']">
              {isMobile ? `Hola, ${user?.full_name?.split(' ')[0]}` : `Bienvenido, ${user?.full_name}`}
            </h2>
            <p className="text-sm text-muted-foreground">
              Panel de control GENTURIX
            </p>
          </div>
          
          {/* Panic Button - Mobile optimized */}
          {(hasRole('Residente') || hasRole('Guarda') || hasRole('Administrador')) && (
            <Button
              className="w-full md:w-auto bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 text-white font-semibold h-12 md:h-auto md:px-6 md:py-3"
              onClick={handlePanicButton}
              data-testid="panic-button"
            >
              <AlertTriangle className="w-5 h-5 mr-2" />
              BOTÓN DE PÁNICO
            </Button>
          )}
        </div>

        {/* Stats Grid - 2 columns on mobile, 4 on desktop */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
          <StatCard
            title="Usuarios"
            value={stats?.total_users || 0}
            icon={Users}
            color="primary"
            onClick={() => navigate('/hr')}
          />
          <StatCard
            title="Guardas"
            value={stats?.active_guards || 0}
            icon={Shield}
            color="success"
            onClick={() => navigate('/hr')}
          />
          <StatCard
            title="Alertas"
            value={stats?.active_alerts || 0}
            icon={AlertTriangle}
            color={stats?.active_alerts > 0 ? 'error' : 'success'}
            onClick={() => navigate('/security')}
          />
          <StatCard
            title="Cursos"
            value={stats?.total_courses || 0}
            icon={GraduationCap}
            color="info"
            onClick={() => navigate('/school')}
          />
        </div>

        {/* Main Content - Stack on mobile */}
        <div className="grid gap-4 md:gap-6 md:grid-cols-3">
          {/* Recent Activity */}
          <Card className="grid-card md:col-span-2">
            <CardHeader className="pb-2 md:pb-4">
              <CardTitle className="text-base md:text-lg flex items-center gap-2">
                <Activity className="w-4 h-4 md:w-5 md:h-5 text-primary" />
                Actividad Reciente
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0 md:p-6 md:pt-0">
              <ScrollArea className={isMobile ? 'h-[250px]' : 'h-[350px]'}>
                <div className="px-4 md:px-0">
                  {activities.length > 0 ? (
                    activities.slice(0, isMobile ? 8 : 15).map((activity, index) => (
                      <ActivityItem key={activity.id || index} activity={activity} />
                    ))
                  ) : (
                    <p className="text-center text-muted-foreground py-8">
                      Sin actividad reciente
                    </p>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card className="grid-card">
            <CardHeader className="pb-2 md:pb-4">
              <CardTitle className="text-base md:text-lg">Accesos Rápidos</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 md:space-y-3">
              {hasRole('Administrador') && (
                <>
                  <Button
                    variant="outline"
                    className="w-full justify-between h-12 border-[#1E293B] hover:bg-muted"
                    onClick={() => navigate('/security')}
                  >
                    <span className="flex items-center gap-3">
                      <Shield className="w-4 h-4 text-primary" />
                      Seguridad
                    </span>
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-between h-12 border-[#1E293B] hover:bg-muted"
                    onClick={() => navigate('/hr')}
                  >
                    <span className="flex items-center gap-3">
                      <Users className="w-4 h-4 text-blue-400" />
                      Recursos Humanos
                    </span>
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-between h-12 border-[#1E293B] hover:bg-muted"
                    onClick={() => navigate('/audit')}
                  >
                    <span className="flex items-center gap-3">
                      <Activity className="w-4 h-4 text-yellow-400" />
                      Auditoría
                    </span>
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </>
              )}
              
              <Button
                variant="outline"
                className="w-full justify-between h-12 border-[#1E293B] hover:bg-muted"
                onClick={() => navigate('/school')}
              >
                <span className="flex items-center gap-3">
                  <GraduationCap className="w-4 h-4 text-green-400" />
                  Genturix School
                </span>
                <ChevronRight className="w-4 h-4" />
              </Button>
              
              <Button
                variant="outline"
                className="w-full justify-between h-12 border-[#1E293B] hover:bg-muted"
                onClick={() => navigate('/payments')}
              >
                <span className="flex items-center gap-3">
                  <CreditCard className="w-4 h-4 text-cyan-400" />
                  Pagos
                </span>
                <ChevronRight className="w-4 h-4" />
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* System Status - Compact on mobile */}
        <Card className="grid-card">
          <CardHeader className="pb-2 md:pb-4">
            <CardTitle className="text-base md:text-lg flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              Estado del Sistema
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
              {[
                { name: 'API', status: 'online' },
                { name: 'Base de Datos', status: 'online' },
                { name: 'Auth', status: 'online' },
                { name: 'Pagos', status: 'online' }
              ].map((service) => (
                <div key={service.name} className="flex items-center gap-2 p-2 md:p-3 rounded-lg bg-muted/30">
                  <div className="w-2 h-2 rounded-full bg-green-400" />
                  <div>
                    <p className="text-xs md:text-sm font-medium">{service.name}</p>
                    <p className="text-[10px] md:text-xs text-muted-foreground">Operativo</p>
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

export default DashboardPage;
