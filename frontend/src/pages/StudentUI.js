/**
 * GENTURIX - StudentUI (Tab-Based Layout)
 * 
 * REFACTORED: Clean tab-based UX similar to Admin UI
 * 
 * Tabs:
 * - Cursos: Available and enrolled courses
 * - Suscripción: Subscription & Payments with clear cost explanation
 * - Notificaciones: Student notifications
 * - Perfil: User profile settings
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import api from '../services/api';
import { 
  GraduationCap, 
  BookOpen,
  Award,
  Clock,
  Play,
  CheckCircle,
  Loader2,
  LogOut,
  CreditCard,
  Bell,
  User,
  ChevronRight,
  DollarSign,
  Zap,
  Shield,
  Star,
  Info,
  ExternalLink
} from 'lucide-react';

// ============================================
// SUBSCRIPTION PLANS
// ============================================
const SUBSCRIPTION_PLANS = [
  {
    id: 'basic',
    name: 'Básico',
    price: 1,
    description: 'Acceso a cursos básicos',
    features: [
      'Cursos de seguridad básicos',
      'Certificados digitales',
      'Acceso desde cualquier dispositivo'
    ],
    recommended: false
  },
  {
    id: 'pro',
    name: 'Profesional',
    price: 3,
    description: 'Acceso completo a Genturix School',
    features: [
      'Todos los cursos disponibles',
      'Certificados digitales verificables',
      'Soporte prioritario',
      'Recursos descargables',
      'Evaluaciones avanzadas'
    ],
    recommended: true
  }
];

// ============================================
// COURSES TAB
// ============================================
const CoursesTab = ({ courses, enrollments, onEnroll, isEnrolled }) => {
  const [activeFilter, setActiveFilter] = useState('all');

  const filteredCourses = activeFilter === 'enrolled' 
    ? courses.filter(c => isEnrolled(c.id))
    : activeFilter === 'available'
    ? courses.filter(c => !isEnrolled(c.id))
    : courses;

  return (
    <div className="space-y-4 p-4">
      {/* Filters */}
      <div className="flex gap-2">
        {['all', 'enrolled', 'available'].map((filter) => (
          <Button
            key={filter}
            variant={activeFilter === filter ? 'default' : 'outline'}
            size="sm"
            onClick={() => setActiveFilter(filter)}
            className={activeFilter !== filter ? 'border-[#1E293B]' : ''}
          >
            {filter === 'all' ? 'Todos' : filter === 'enrolled' ? 'Inscritos' : 'Disponibles'}
          </Button>
        ))}
      </div>

      {/* Course Grid */}
      <div className="space-y-3">
        {filteredCourses.map((course) => {
          const enrollment = enrollments.find(e => e.course_id === course.id);
          
          return (
            <Card key={course.id} className="bg-[#0F111A] border-[#1E293B]">
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <Badge variant="outline" className="text-xs">
                    {course.category}
                  </Badge>
                  {isEnrolled(course.id) && (
                    <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                      Inscrito
                    </Badge>
                  )}
                </div>
                
                <h3 className="font-semibold text-white mb-1">{course.title}</h3>
                <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                  {course.description}
                </p>

                <div className="flex items-center gap-4 text-xs text-muted-foreground mb-3">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {course.duration_hours}h
                  </span>
                  <span>{course.instructor}</span>
                </div>

                {enrollment && (
                  <div className="mb-3 space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">Progreso</span>
                      <span>{enrollment.progress}%</span>
                    </div>
                    <Progress value={enrollment.progress} className="h-1.5" />
                  </div>
                )}

                <Button
                  size="sm"
                  className="w-full"
                  variant={isEnrolled(course.id) ? "outline" : "default"}
                  onClick={() => !isEnrolled(course.id) && onEnroll(course.id)}
                  disabled={isEnrolled(course.id)}
                  data-testid={`enroll-btn-${course.id}`}
                >
                  {isEnrolled(course.id) ? (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      Continuar
                    </>
                  ) : (
                    <>
                      <BookOpen className="w-4 h-4 mr-2" />
                      Inscribirse
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {filteredCourses.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <BookOpen className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No hay cursos para mostrar</p>
        </div>
      )}
    </div>
  );
};

// ============================================
// SUBSCRIPTION TAB
// ============================================
const SubscriptionTab = ({ user }) => {
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState(false);
  const [currentSubscription, setCurrentSubscription] = useState({
    plan: 'basic',
    status: 'active',
    next_billing: '2026-02-28'
  });

  const handleSubscribe = async () => {
    if (!selectedPlan) return;
    
    setIsLoading(true);
    try {
      const response = await api.createCheckout({
        user_count: 1,
        origin_url: window.location.origin
      });
      
      if (response.checkout_url) {
        window.location.href = response.checkout_url;
      }
    } catch (error) {
      console.error('Error creating checkout:', error);
      alert('Error al procesar el pago. Intenta de nuevo.');
    } finally {
      setIsLoading(false);
      setConfirmDialog(false);
    }
  };

  const currentPlan = SUBSCRIPTION_PLANS.find(p => p.id === currentSubscription.plan);

  return (
    <div className="space-y-6 p-4">
      {/* Current Plan Card */}
      <Card className="bg-gradient-to-br from-primary/10 to-cyan-500/10 border-primary/30">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-primary" />
              Tu Plan Actual
            </CardTitle>
            <Badge className={currentSubscription.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}>
              {currentSubscription.status === 'active' ? 'Activo' : 'Pendiente'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-baseline gap-1 mb-2">
            <span className="text-3xl font-bold text-white">${currentPlan?.price || 1}</span>
            <span className="text-muted-foreground">/mes</span>
          </div>
          <p className="text-sm text-muted-foreground mb-3">{currentPlan?.name || 'Básico'}</p>
          
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock className="w-3 h-3" />
            Próximo cobro: {new Date(currentSubscription.next_billing).toLocaleDateString('es-ES')}
          </div>
        </CardContent>
      </Card>

      {/* Cost Explanation */}
      <Card className="bg-blue-500/10 border-blue-500/30">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-blue-400">Modelo de Precios GENTURIX</p>
              <p className="text-xs text-muted-foreground">
                GENTURIX School opera con un modelo simple: <strong className="text-white">$1 USD por usuario al mes</strong> para el plan básico. 
                Los cursos premium tienen un costo adicional de $2 USD/mes.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Available Plans */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground">Planes Disponibles</h3>
        
        {SUBSCRIPTION_PLANS.map((plan) => (
          <Card 
            key={plan.id}
            className={`bg-[#0F111A] border-[#1E293B] cursor-pointer transition-all ${
              selectedPlan?.id === plan.id ? 'ring-2 ring-primary border-primary' : ''
            } ${plan.recommended ? 'relative overflow-hidden' : ''}`}
            onClick={() => setSelectedPlan(plan)}
            data-testid={`plan-card-${plan.id}`}
          >
            {plan.recommended && (
              <div className="absolute top-0 right-0 bg-primary text-white text-[10px] px-3 py-1 rounded-bl-lg font-medium">
                Recomendado
              </div>
            )}
            <CardContent className="p-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h4 className="font-semibold text-white">{plan.name}</h4>
                  <p className="text-xs text-muted-foreground">{plan.description}</p>
                </div>
                <div className="text-right">
                  <div className="flex items-baseline gap-0.5">
                    <span className="text-2xl font-bold text-white">${plan.price}</span>
                    <span className="text-xs text-muted-foreground">/mes</span>
                  </div>
                </div>
              </div>

              <ul className="space-y-2">
                {plan.features.map((feature, idx) => (
                  <li key={idx} className="flex items-center gap-2 text-xs text-muted-foreground">
                    <CheckCircle className="w-3 h-3 text-green-400 flex-shrink-0" />
                    {feature}
                  </li>
                ))}
              </ul>

              {currentSubscription.plan === plan.id && (
                <Badge className="mt-3 bg-green-500/20 text-green-400 border-green-500/30">
                  Plan Actual
                </Badge>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Subscribe Button */}
      {selectedPlan && selectedPlan.id !== currentSubscription.plan && (
        <Button 
          className="w-full" 
          size="lg"
          onClick={() => setConfirmDialog(true)}
          data-testid="subscribe-btn"
        >
          <Zap className="w-4 h-4 mr-2" />
          Cambiar a {selectedPlan.name} - ${selectedPlan.price}/mes
        </Button>
      )}

      {/* Confirm Dialog */}
      <Dialog open={confirmDialog} onOpenChange={setConfirmDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B]">
          <DialogHeader>
            <DialogTitle>Confirmar Suscripción</DialogTitle>
            <DialogDescription>
              Estás a punto de suscribirte al plan {selectedPlan?.name}
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4 space-y-4">
            <div className="p-4 rounded-lg bg-[#181B25] border border-[#1E293B]">
              <div className="flex items-center justify-between mb-2">
                <span className="text-muted-foreground">Plan</span>
                <span className="font-medium">{selectedPlan?.name}</span>
              </div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-muted-foreground">Costo mensual</span>
                <span className="font-bold text-white">${selectedPlan?.price} USD</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Cobro</span>
                <span>Inmediato</span>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              Al suscribirte, aceptas los términos y condiciones de GENTURIX. 
              Puedes cancelar en cualquier momento.
            </p>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDialog(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSubscribe} disabled={isLoading}>
              {isLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CreditCard className="w-4 h-4 mr-2" />}
              Pagar ${selectedPlan?.price} USD
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ============================================
// NOTIFICATIONS TAB
// ============================================
const NotificationsTab = () => {
  const [notifications] = useState([
    { id: '1', type: 'course', title: 'Nuevo curso disponible', message: 'Seguridad Avanzada ya está disponible', time: '2h', read: false },
    { id: '2', type: 'payment', title: 'Pago exitoso', message: 'Tu suscripción ha sido renovada', time: '1d', read: true },
    { id: '3', type: 'certificate', title: '¡Felicidades!', message: 'Has obtenido un nuevo certificado', time: '3d', read: true },
  ]);

  const getIcon = (type) => {
    switch (type) {
      case 'course': return <BookOpen className="w-5 h-5 text-cyan-400" />;
      case 'payment': return <CreditCard className="w-5 h-5 text-green-400" />;
      case 'certificate': return <Award className="w-5 h-5 text-yellow-400" />;
      default: return <Bell className="w-5 h-5 text-primary" />;
    }
  };

  return (
    <div className="p-4 space-y-3">
      {notifications.length > 0 ? (
        notifications.map((notif) => (
          <div 
            key={notif.id}
            className={`p-4 rounded-xl border ${
              notif.read 
                ? 'bg-[#0F111A] border-[#1E293B]' 
                : 'bg-primary/5 border-primary/20'
            }`}
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-full bg-[#181B25] flex items-center justify-center flex-shrink-0">
                {getIcon(notif.type)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium text-white text-sm">{notif.title}</h4>
                  {!notif.read && (
                    <div className="w-2 h-2 rounded-full bg-primary" />
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{notif.message}</p>
                <span className="text-[10px] text-muted-foreground mt-1 block">{notif.time}</span>
              </div>
            </div>
          </div>
        ))
      ) : (
        <div className="text-center py-12 text-muted-foreground">
          <Bell className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No hay notificaciones</p>
        </div>
      )}
    </div>
  );
};

// ============================================
// PROFILE TAB
// ============================================
const ProfileTab = ({ user, onLogout }) => {
  return (
    <div className="p-4 space-y-4">
      {/* Profile Card */}
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardContent className="p-6">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <span className="text-2xl font-bold text-white">
                {user?.full_name?.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">{user?.full_name}</h3>
              <p className="text-sm text-muted-foreground">{user?.email}</p>
              <Badge variant="outline" className="mt-1 text-xs">Estudiante</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="p-3 rounded-xl bg-[#0F111A] border border-[#1E293B] text-center">
          <BookOpen className="w-5 h-5 mx-auto mb-1 text-cyan-400" />
          <p className="text-lg font-bold text-white">3</p>
          <p className="text-[10px] text-muted-foreground">Cursos</p>
        </div>
        <div className="p-3 rounded-xl bg-[#0F111A] border border-[#1E293B] text-center">
          <Award className="w-5 h-5 mx-auto mb-1 text-yellow-400" />
          <p className="text-lg font-bold text-white">1</p>
          <p className="text-[10px] text-muted-foreground">Certificados</p>
        </div>
        <div className="p-3 rounded-xl bg-[#0F111A] border border-[#1E293B] text-center">
          <Star className="w-5 h-5 mx-auto mb-1 text-purple-400" />
          <p className="text-lg font-bold text-white">85%</p>
          <p className="text-[10px] text-muted-foreground">Promedio</p>
        </div>
      </div>

      {/* Actions */}
      <div className="space-y-2">
        <Button variant="outline" className="w-full justify-between border-[#1E293B]">
          Configuración
          <ChevronRight className="w-4 h-4" />
        </Button>
        <Button variant="outline" className="w-full justify-between border-[#1E293B]">
          Ayuda y Soporte
          <ChevronRight className="w-4 h-4" />
        </Button>
        <Button 
          variant="outline" 
          className="w-full justify-between border-red-500/30 text-red-400 hover:bg-red-500/10"
          onClick={onLogout}
          data-testid="student-logout-btn"
        >
          Cerrar Sesión
          <LogOut className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
};

// ============================================
// MAIN STUDENT UI COMPONENT
// ============================================
const StudentUI = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [courses, setCourses] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('courses');

  const fetchData = async () => {
    try {
      const [coursesData, enrollmentsData, certificatesData] = await Promise.all([
        api.getCourses(),
        api.getEnrollments(),
        api.getCertificates()
      ]);
      setCourses(coursesData);
      setEnrollments(enrollmentsData);
      setCertificates(certificatesData);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleEnroll = async (courseId) => {
    try {
      await api.enrollCourse({ course_id: courseId, student_id: user.id });
      fetchData();
    } catch (error) {
      console.error('Error enrolling:', error);
      if (error.message.includes('Already enrolled')) {
        alert('Ya estás inscrito en este curso');
      }
    }
  };

  const isEnrolled = (courseId) => {
    return enrollments.some(e => e.course_id === courseId);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#05050A] flex flex-col safe-area">
      {/* Header */}
      <header className="p-4 flex items-center justify-between border-b border-[#1E293B] bg-[#0F111A]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center">
            <GraduationCap className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h1 className="text-base font-bold font-['Outfit']">GENTURIX SCHOOL</h1>
            <p className="text-xs text-muted-foreground truncate max-w-[140px]">
              {user?.full_name}
            </p>
          </div>
        </div>
      </header>

      {/* Stats Bar */}
      <div className="grid grid-cols-3 gap-2 p-3 border-b border-[#1E293B] bg-[#0A0A0F]">
        <div className="text-center">
          <p className="text-xl font-bold text-cyan-400">{enrollments.length}</p>
          <p className="text-[10px] text-muted-foreground">Inscritos</p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-green-400">
            {enrollments.filter(e => e.completed_at).length}
          </p>
          <p className="text-[10px] text-muted-foreground">Completados</p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-yellow-400">{certificates.length}</p>
          <p className="text-[10px] text-muted-foreground">Certificados</p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <TabsList className="grid grid-cols-4 bg-[#0F111A] border-b border-[#1E293B] rounded-none h-12">
          <TabsTrigger 
            value="courses" 
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-cyan-400 rounded-none text-xs"
            data-testid="tab-courses"
          >
            <BookOpen className="w-4 h-4 mr-1" />
            Cursos
          </TabsTrigger>
          <TabsTrigger 
            value="subscription" 
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-cyan-400 rounded-none text-xs"
            data-testid="tab-subscription"
          >
            <CreditCard className="w-4 h-4 mr-1" />
            Plan
          </TabsTrigger>
          <TabsTrigger 
            value="notifications" 
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-cyan-400 rounded-none text-xs"
            data-testid="tab-notifications"
          >
            <Bell className="w-4 h-4 mr-1" />
            Avisos
          </TabsTrigger>
          <TabsTrigger 
            value="profile" 
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-cyan-400 rounded-none text-xs"
            data-testid="tab-profile"
          >
            <User className="w-4 h-4 mr-1" />
            Perfil
          </TabsTrigger>
        </TabsList>

        <ScrollArea className="flex-1">
          <TabsContent value="courses" className="mt-0">
            <CoursesTab 
              courses={courses}
              enrollments={enrollments}
              onEnroll={handleEnroll}
              isEnrolled={isEnrolled}
            />
          </TabsContent>

          <TabsContent value="subscription" className="mt-0">
            <SubscriptionTab user={user} />
          </TabsContent>

          <TabsContent value="notifications" className="mt-0">
            <NotificationsTab />
          </TabsContent>

          <TabsContent value="profile" className="mt-0">
            <ProfileTab user={user} onLogout={handleLogout} />
          </TabsContent>
        </ScrollArea>
      </Tabs>
    </div>
  );
};

export default StudentUI;
