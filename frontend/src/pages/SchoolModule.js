import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import api from '../services/api';
import { 
  GraduationCap, 
  BookOpen,
  Award,
  Clock,
  Users,
  Play,
  CheckCircle,
  Loader2,
  Star
} from 'lucide-react';

const SchoolModule = () => {
  const { user } = useAuth();
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
      console.error('Error fetching school data:', error);
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
      alert(error.message || 'Error al inscribirse');
    }
  };

  const isEnrolled = (courseId) => {
    return enrollments.some(e => e.course_id === courseId);
  };

  const getCategoryColor = (category) => {
    const colors = {
      'Seguridad': 'bg-red-500/20 text-red-400 border-red-500/20',
      'Salud': 'bg-green-500/20 text-green-400 border-green-500/20',
      'Administración': 'bg-blue-500/20 text-blue-400 border-blue-500/20',
      'default': 'bg-purple-500/20 text-purple-400 border-purple-500/20'
    };
    return colors[category] || colors.default;
  };

  if (isLoading) {
    return (
      <DashboardLayout title="Genturix School">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Genturix School">
      <div className="space-y-6">
        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-purple-500/20 text-purple-400 flex items-center justify-center">
                  <BookOpen className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Cursos Disponibles</p>
                  <p className="text-2xl font-bold">{courses.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-blue-500/20 text-blue-400 flex items-center justify-center">
                  <GraduationCap className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Mis Inscripciones</p>
                  <p className="text-2xl font-bold">{enrollments.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-green-500/20 text-green-400 flex items-center justify-center">
                  <CheckCircle className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Completados</p>
                  <p className="text-2xl font-bold">{enrollments.filter(e => e.completed_at).length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="grid-card">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-yellow-500/20 text-yellow-400 flex items-center justify-center">
                  <Award className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Certificados</p>
                  <p className="text-2xl font-bold">{certificates.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-[#0F111A] border border-[#1E293B]">
            <TabsTrigger value="courses" data-testid="tab-courses">Cursos</TabsTrigger>
            <TabsTrigger value="my-learning" data-testid="tab-my-learning">Mi Aprendizaje</TabsTrigger>
            <TabsTrigger value="certificates" data-testid="tab-certificates">Certificados</TabsTrigger>
          </TabsList>

          {/* Courses Tab */}
          <TabsContent value="courses">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {courses.map((course) => (
                <Card key={course.id} className="grid-card" data-testid={`course-card-${course.id}`}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <Badge className={getCategoryColor(course.category)}>
                        {course.category}
                      </Badge>
                      {isEnrolled(course.id) && (
                        <Badge className="badge-success">Inscrito</Badge>
                      )}
                    </div>
                    <CardTitle className="mt-4">{course.title}</CardTitle>
                    <CardDescription className="line-clamp-2">
                      {course.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Clock className="w-4 h-4" />
                          {course.duration_hours}h
                        </div>
                        <div className="flex items-center gap-1">
                          <Users className="w-4 h-4" />
                          {course.enrolled_count} estudiantes
                        </div>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-muted-foreground">Instructor:</span>
                        <span>{course.instructor}</span>
                      </div>
                      <Button
                        className="w-full"
                        variant={isEnrolled(course.id) ? "outline" : "default"}
                        onClick={() => !isEnrolled(course.id) && handleEnroll(course.id)}
                        disabled={isEnrolled(course.id)}
                        data-testid={`enroll-btn-${course.id}`}
                      >
                        {isEnrolled(course.id) ? (
                          <>
                            <CheckCircle className="w-4 h-4 mr-2" />
                            Ya inscrito
                          </>
                        ) : (
                          <>
                            <Play className="w-4 h-4 mr-2" />
                            Inscribirse
                          </>
                        )}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
              
              {courses.length === 0 && (
                <div className="col-span-full flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <BookOpen className="w-12 h-12 mb-4" />
                  <p>No hay cursos disponibles</p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* My Learning Tab */}
          <TabsContent value="my-learning">
            <Card className="grid-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <GraduationCap className="w-5 h-5 text-blue-400" />
                  Mi Progreso
                </CardTitle>
                <CardDescription>Cursos en los que estás inscrito</CardDescription>
              </CardHeader>
              <CardContent>
                {enrollments.length > 0 ? (
                  <div className="space-y-4">
                    {enrollments.map((enrollment) => (
                      <div 
                        key={enrollment.id}
                        className="p-4 rounded-lg bg-muted/30 border border-[#1E293B]"
                        data-testid={`enrollment-${enrollment.id}`}
                      >
                        <div className="flex items-start justify-between mb-4">
                          <div>
                            <h3 className="font-semibold">{enrollment.course_title}</h3>
                            <p className="text-sm text-muted-foreground">
                              Inscrito: {new Date(enrollment.enrolled_at).toLocaleDateString('es-ES')}
                            </p>
                          </div>
                          {enrollment.completed_at ? (
                            <Badge className="badge-success">Completado</Badge>
                          ) : (
                            <Badge className="badge-info">En progreso</Badge>
                          )}
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">Progreso</span>
                            <span className="font-medium">{enrollment.progress}%</span>
                          </div>
                          <Progress value={enrollment.progress} className="h-2" />
                        </div>
                        <div className="mt-4 flex gap-2">
                          <Button size="sm" className="flex-1" data-testid={`continue-btn-${enrollment.id}`}>
                            <Play className="w-4 h-4 mr-2" />
                            Continuar
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <GraduationCap className="w-12 h-12 mb-4" />
                    <p>No tienes cursos en progreso</p>
                    <Button 
                      variant="outline" 
                      className="mt-4"
                      onClick={() => setActiveTab('courses')}
                    >
                      Explorar cursos
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Certificates Tab */}
          <TabsContent value="certificates">
            <Card className="grid-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Award className="w-5 h-5 text-yellow-400" />
                  Mis Certificados
                </CardTitle>
                <CardDescription>Certificaciones obtenidas</CardDescription>
              </CardHeader>
              <CardContent>
                {certificates.length > 0 ? (
                  <div className="grid gap-4 md:grid-cols-2">
                    {certificates.map((cert) => (
                      <div 
                        key={cert.id}
                        className="p-6 rounded-lg bg-gradient-to-br from-yellow-500/10 to-orange-500/10 border border-yellow-500/20"
                        data-testid={`certificate-${cert.id}`}
                      >
                        <div className="flex items-center gap-4">
                          <div className="w-16 h-16 rounded-full bg-yellow-500/20 flex items-center justify-center">
                            <Award className="w-8 h-8 text-yellow-400" />
                          </div>
                          <div>
                            <h3 className="font-semibold">{cert.course_title}</h3>
                            <p className="text-sm text-muted-foreground">
                              Emitido: {new Date(cert.issued_at).toLocaleDateString('es-ES')}
                            </p>
                            <p className="text-xs font-mono text-muted-foreground mt-1">
                              ID: {cert.id.slice(0, 8)}
                            </p>
                          </div>
                        </div>
                        <Button variant="outline" className="w-full mt-4 border-yellow-500/20">
                          Descargar Certificado
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                    <Award className="w-12 h-12 mb-4" />
                    <p>Aún no tienes certificados</p>
                    <p className="text-sm mt-2">Completa cursos para obtener certificaciones</p>
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

export default SchoolModule;
