import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
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
  Loader2
} from 'lucide-react';

const StatCard = ({ title, value, icon: Icon, trend, color = 'primary' }) => {
  const colorClasses = {
    primary: 'bg-primary/10 text-primary',
    success: 'bg-green-500/10 text-green-400',
    warning: 'bg-yellow-500/10 text-yellow-400',
    error: 'bg-red-500/10 text-red-400',
    info: 'bg-blue-500/10 text-blue-400',
  };

  return (
    <Card className="grid-card">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold font-['Outfit'] mt-1">{value}</p>
            {trend && (
              <div className="flex items-center gap-1 mt-2 text-xs">
                <TrendingUp className="w-3 h-3 text-green-400" />
                <span className="text-green-400">{trend}</span>
              </div>
            )}
          </div>
          <div className={`w-12 h-12 rounded-lg ${colorClasses[color]} flex items-center justify-center`}>
            <Icon className="w-6 h-6" />
          </div>
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
    return date.toLocaleString('es-ES', { 
      hour: '2-digit', 
      minute: '2-digit',
      day: '2-digit',
      month: 'short'
    });
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
      <div className="text-xs text-muted-foreground flex items-center gap-1">
        <Clock className="w-3 h-3" />
        {formatTime(activity.timestamp)}
      </div>
    </div>
  );
};

const DashboardPage = () => {
  const navigate = useNavigate();
  const { user, hasRole } = useAuth();
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
        location: 'Dashboard - Emergency',
        description: 'Emergency panic button pressed from dashboard'
      });
      alert('Alerta de pánico enviada. El equipo de seguridad ha sido notificado.');
    } catch (error) {
      console.error('Error triggering panic:', error);
      alert('Error al enviar alerta. Por favor intente de nuevo.');
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
      <div className="space-y-6">
        {/* Welcome Section */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold font-['Outfit']">
              Bienvenido, {user?.full_name}
            </h2>
            <p className="text-muted-foreground">
              Panel de control de GENTURIX Enterprise
            </p>
          </div>
          
          {/* Panic Button */}
          {(hasRole('Residente') || hasRole('Guarda')) && (
            <Button
              className="panic-button text-white font-semibold px-8 py-6 text-lg"
              onClick={handlePanicButton}
              data-testid="panic-button"
            >
              <AlertTriangle className="w-6 h-6 mr-2" />
              BOTÓN DE PÁNICO
            </Button>
          )}
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Usuarios Totales"
            value={stats?.total_users || 0}
            icon={Users}
            color="primary"
          />
          <StatCard
            title="Guardas Activos"
            value={stats?.active_guards || 0}
            icon={Shield}
            trend="+2 esta semana"
            color="success"
          />
          <StatCard
            title="Alertas Activas"
            value={stats?.active_alerts || 0}
            icon={AlertTriangle}
            color={stats?.active_alerts > 0 ? 'error' : 'success'}
          />
          <StatCard
            title="Cursos Disponibles"
            value={stats?.total_courses || 0}
            icon={GraduationCap}
            color="info"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Recent Activity */}
          <Card className="grid-card lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-primary" />
                Actividad Reciente
              </CardTitle>
              <CardDescription>
                Últimos eventos registrados en el sistema
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                {activities.length > 0 ? (
                  activities.map((activity, index) => (
                    <ActivityItem key={activity.id || index} activity={activity} />
                  ))
                ) : (
                  <p className="text-center text-muted-foreground py-8">
                    No hay actividad reciente
                  </p>
                )}
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card className="grid-card">
            <CardHeader>
              <CardTitle>Acciones Rápidas</CardTitle>
              <CardDescription>
                Accede rápidamente a las funciones principales
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {hasRole('Administrador') && (
                <>
                  <Button
                    variant="outline"
                    className="w-full justify-start border-[#1E293B] hover:bg-muted"
                    onClick={() => navigate('/security')}
                    data-testid="quick-action-security"
                  >
                    <Shield className="w-4 h-4 mr-3 text-primary" />
                    Centro de Seguridad
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-start border-[#1E293B] hover:bg-muted"
                    onClick={() => navigate('/hr')}
                    data-testid="quick-action-hr"
                  >
                    <Users className="w-4 h-4 mr-3 text-blue-400" />
                    Recursos Humanos
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-start border-[#1E293B] hover:bg-muted"
                    onClick={() => navigate('/audit')}
                    data-testid="quick-action-audit"
                  >
                    <Activity className="w-4 h-4 mr-3 text-yellow-400" />
                    Ver Auditoría
                  </Button>
                </>
              )}
              
              <Button
                variant="outline"
                className="w-full justify-start border-[#1E293B] hover:bg-muted"
                onClick={() => navigate('/school')}
                data-testid="quick-action-school"
              >
                <GraduationCap className="w-4 h-4 mr-3 text-green-400" />
                Genturix School
              </Button>
              
              <Button
                variant="outline"
                className="w-full justify-start border-[#1E293B] hover:bg-muted"
                onClick={() => navigate('/payments')}
                data-testid="quick-action-payments"
              >
                <CreditCard className="w-4 h-4 mr-3 text-cyan-400" />
                Pagos y Suscripciones
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* System Status */}
        <Card className="grid-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-green-400" />
              Estado del Sistema
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-4">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-green-400 animate-pulse" />
                <div>
                  <p className="text-sm font-medium">API Backend</p>
                  <p className="text-xs text-muted-foreground">Operativo</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-green-400 animate-pulse" />
                <div>
                  <p className="text-sm font-medium">Base de Datos</p>
                  <p className="text-xs text-muted-foreground">Operativo</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-green-400 animate-pulse" />
                <div>
                  <p className="text-sm font-medium">Autenticación</p>
                  <p className="text-xs text-muted-foreground">Operativo</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-green-400 animate-pulse" />
                <div>
                  <p className="text-sm font-medium">Pagos</p>
                  <p className="text-xs text-muted-foreground">Stripe Conectado</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default DashboardPage;
