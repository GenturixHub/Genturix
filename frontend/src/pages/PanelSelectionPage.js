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
  ChevronRight 
} from 'lucide-react';

const ROLE_CONFIGS = {
  'Administrador': {
    icon: Shield,
    title: 'Panel Administrador',
    description: 'Acceso completo al sistema, gestión de usuarios, configuración y reportes.',
    color: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    iconBg: 'bg-purple-500/20',
  },
  'Supervisor': {
    icon: Users,
    title: 'Panel Supervisor',
    description: 'Gestión de guardas, turnos, monitoreo de seguridad y reportes.',
    color: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    iconBg: 'bg-blue-500/20',
  },
  'Guarda': {
    icon: UserCheck,
    title: 'Panel Guarda',
    description: 'Control de accesos, registro de eventos y botón de pánico.',
    color: 'bg-green-500/10 text-green-400 border-green-500/20',
    iconBg: 'bg-green-500/20',
  },
  'Residente': {
    icon: Home,
    title: 'Panel Residente',
    description: 'Acceso a servicios del condominio, alertas y comunicaciones.',
    color: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    iconBg: 'bg-orange-500/20',
  },
  'Estudiante': {
    icon: GraduationCap,
    title: 'Panel Estudiante',
    description: 'Acceso a cursos, certificaciones y progreso académico.',
    color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    iconBg: 'bg-cyan-500/20',
  },
};

const PanelSelectionPage = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleSelectPanel = (role) => {
    sessionStorage.setItem('activeRole', role);
    navigate('/dashboard');
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
          <div>
            <h1 className="text-2xl font-bold font-['Outfit']">Seleccionar Panel</h1>
            <p className="text-muted-foreground">
              Bienvenido, <span className="text-foreground">{user.full_name}</span>
            </p>
          </div>
          <Button
            variant="outline"
            onClick={handleLogout}
            className="border-[#1E293B] hover:bg-muted"
            data-testid="logout-btn"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Cerrar Sesión
          </Button>
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
                className={`grid-card cursor-pointer hover:border-primary transition-all duration-200 ${config.color}`}
                onClick={() => handleSelectPanel(role)}
                data-testid={`panel-card-${role.toLowerCase()}`}
              >
                <CardHeader className="flex flex-row items-center gap-4">
                  <div className={`w-12 h-12 rounded-lg ${config.iconBg} flex items-center justify-center`}>
                    <IconComponent className="w-6 h-6" />
                  </div>
                  <div className="flex-1">
                    <CardTitle className="text-lg">{config.title}</CardTitle>
                    <CardDescription className="text-sm mt-1">
                      {config.description}
                    </CardDescription>
                  </div>
                  <ChevronRight className="w-5 h-5 text-muted-foreground" />
                </CardHeader>
              </Card>
            );
          })}
        </div>

        {/* Info */}
        <div className="mt-8 p-4 rounded-lg bg-muted/30 border border-border">
          <p className="text-sm text-muted-foreground text-center">
            Tienes acceso a <span className="text-foreground font-medium">{user.roles.length}</span> panel(es). 
            Selecciona el que deseas usar en esta sesión.
          </p>
        </div>
      </div>
    </div>
  );
};

export default PanelSelectionPage;
