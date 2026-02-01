import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { 
  Shield, 
  Users, 
  UserCheck, 
  Home, 
  GraduationCap, 
  LogOut,
  ChevronRight,
  Briefcase
} from 'lucide-react';

const ROLE_CONFIGS = {
  'Administrador': {
    icon: Shield,
    title: 'Panel Administrador',
    description: 'Acceso completo: usuarios, pagos, auditoría, todos los módulos.',
    color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    iconBg: 'bg-cyan-500/20',
    route: '/admin/dashboard'
  },
  'HR': {
    icon: Briefcase,
    title: 'Panel Recursos Humanos',
    description: 'Gestión de personal, reclutamiento, turnos, ausencias.',
    color: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    iconBg: 'bg-orange-500/20',
    route: '/rrhh'
  },
  'Supervisor': {
    icon: Users,
    title: 'Panel Supervisor',
    description: 'Gestión de guardas, turnos, monitoreo de seguridad.',
    color: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    iconBg: 'bg-blue-500/20',
    route: '/rrhh'
  },
  'Guarda': {
    icon: UserCheck,
    title: 'Panel Guarda',
    description: 'Ver emergencias activas, responder alertas, ubicaciones.',
    color: 'bg-green-500/10 text-green-400 border-green-500/20',
    iconBg: 'bg-green-500/20',
    route: '/guard'
  },
  'Residente': {
    icon: Home,
    title: 'Panel Residente',
    description: 'Botón de pánico, reportar emergencias, contactar seguridad.',
    color: 'bg-red-500/10 text-red-400 border-red-500/20',
    iconBg: 'bg-red-500/20',
    route: '/resident'
  },
  'Estudiante': {
    icon: GraduationCap,
    title: 'Panel Estudiante',
    description: 'Cursos, certificaciones, progreso académico.',
    color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    iconBg: 'bg-cyan-500/20',
    route: '/student'
  },
};

const PanelSelectionPage = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleSelectPanel = (role) => {
    const config = ROLE_CONFIGS[role];
    if (config) {
      sessionStorage.setItem('activeRole', role);
      navigate(config.route);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (!user) {
    navigate('/login');
    return null;
  }

  return (
    <div className="min-h-screen bg-[#05050A] p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Shield className="w-10 h-10 text-primary" />
            <div>
              <h1 className="text-2xl font-bold font-['Outfit']">GENTURIX</h1>
              <p className="text-muted-foreground">
                Bienvenido, <span className="text-foreground">{user.full_name}</span>
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            onClick={handleLogout}
            className="border-[#1E293B] hover:bg-muted"
            data-testid="logout-btn"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Salir
          </Button>
        </div>

        {/* Title */}
        <div className="text-center mb-8">
          <h2 className="text-xl font-semibold">Selecciona tu panel</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Tienes acceso a {user.roles.length} panel{user.roles.length > 1 ? 'es' : ''}
          </p>
        </div>

        {/* Role Cards */}
        <div className="grid gap-4 md:grid-cols-2">
          {user.roles.map((role) => {
            const config = ROLE_CONFIGS[role];
            if (!config) return null;

            const IconComponent = config.icon;

            return (
              <Card
                key={role}
                className={`cursor-pointer transition-all duration-200 hover:scale-[1.02] ${config.color} border-2`}
                onClick={() => handleSelectPanel(role)}
                data-testid={`panel-card-${role.toLowerCase()}`}
              >
                <CardHeader className="flex flex-row items-center gap-4">
                  <div className={`w-14 h-14 rounded-xl ${config.iconBg} flex items-center justify-center`}>
                    <IconComponent className="w-7 h-7" />
                  </div>
                  <div className="flex-1">
                    <CardTitle className="text-lg">{config.title}</CardTitle>
                    <CardDescription className="text-sm mt-1">
                      {config.description}
                    </CardDescription>
                  </div>
                  <ChevronRight className="w-6 h-6 text-muted-foreground" />
                </CardHeader>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default PanelSelectionPage;
