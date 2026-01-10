import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { ScrollArea } from '../components/ui/scroll-area';
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
  Shield
} from 'lucide-react';

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
    <div className="min-h-screen bg-[#05050A] flex flex-col">
      {/* Header */}
      <header className="p-4 flex items-center justify-between border-b border-[#1E293B] bg-[#0F111A]">
        <div className="flex items-center gap-3">
          <GraduationCap className="w-8 h-8 text-cyan-400" />
          <div>
            <h1 className="text-lg font-bold font-['Outfit']">GENTURIX SCHOOL</h1>
            <p className="text-xs text-muted-foreground">{user?.full_name}</p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={handleLogout}
          className="text-muted-foreground hover:text-white"
        >
          <LogOut className="w-5 h-5" />
        </Button>
      </header>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 p-4 border-b border-[#1E293B]">
        <div className="text-center p-3 rounded-lg bg-[#0F111A]">
          <p className="text-2xl font-bold text-cyan-400">{enrollments.length}</p>
          <p className="text-xs text-muted-foreground">Inscritos</p>
        </div>
        <div className="text-center p-3 rounded-lg bg-[#0F111A]">
          <p className="text-2xl font-bold text-green-400">
            {enrollments.filter(e => e.completed_at).length}
          </p>
          <p className="text-xs text-muted-foreground">Completados</p>
        </div>
        <div className="text-center p-3 rounded-lg bg-[#0F111A]">
          <p className="text-2xl font-bold text-yellow-400">{certificates.length}</p>
          <p className="text-xs text-muted-foreground">Certificados</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#1E293B]">
        {['courses', 'progress', 'certificates'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              activeTab === tab 
                ? 'text-cyan-400 border-b-2 border-cyan-400' 
                : 'text-muted-foreground'
            }`}
          >
            {tab === 'courses' ? 'Cursos' : tab === 'progress' ? 'Mi Progreso' : 'Certificados'}
          </button>
        ))}
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {activeTab === 'courses' && (
            <>
              {courses.map((course) => (
                <Card key={course.id} className="bg-[#0F111A] border-[#1E293B]">
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <Badge variant="outline" className="text-xs">
                        {course.category}
                      </Badge>
                      {isEnrolled(course.id) && (
                        <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                          Inscrito
                        </Badge>
                      )}
                    </div>
                    <CardTitle className="text-base mt-2">{course.title}</CardTitle>
                    <CardDescription className="text-xs line-clamp-2">
                      {course.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground mb-3">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {course.duration_hours}h
                      </span>
                      <span>{course.instructor}</span>
                    </div>
                    <Button
                      size="sm"
                      className="w-full"
                      variant={isEnrolled(course.id) ? "outline" : "default"}
                      onClick={() => !isEnrolled(course.id) && handleEnroll(course.id)}
                      disabled={isEnrolled(course.id)}
                    >
                      {isEnrolled(course.id) ? (
                        <>
                          <CheckCircle className="w-4 h-4 mr-2" />
                          Inscrito
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4 mr-2" />
                          Inscribirse
                        </>
                      )}
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </>
          )}

          {activeTab === 'progress' && (
            <>
              {enrollments.length > 0 ? (
                enrollments.map((enrollment) => (
                  <Card key={enrollment.id} className="bg-[#0F111A] border-[#1E293B]">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-medium">{enrollment.course_title}</h3>
                        {enrollment.completed_at ? (
                          <Badge className="bg-green-500/20 text-green-400">Completado</Badge>
                        ) : (
                          <Badge className="bg-blue-500/20 text-blue-400">En progreso</Badge>
                        )}
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground">Progreso</span>
                          <span>{enrollment.progress}%</span>
                        </div>
                        <Progress value={enrollment.progress} className="h-2" />
                      </div>
                      <Button size="sm" className="w-full mt-3">
                        <Play className="w-4 h-4 mr-2" />
                        Continuar
                      </Button>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <BookOpen className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No tienes cursos en progreso</p>
                </div>
              )}
            </>
          )}

          {activeTab === 'certificates' && (
            <>
              {certificates.length > 0 ? (
                certificates.map((cert) => (
                  <Card key={cert.id} className="bg-gradient-to-br from-yellow-500/10 to-orange-500/10 border-yellow-500/20">
                    <CardContent className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-full bg-yellow-500/20 flex items-center justify-center">
                          <Award className="w-6 h-6 text-yellow-400" />
                        </div>
                        <div>
                          <h3 className="font-medium">{cert.course_title}</h3>
                          <p className="text-xs text-muted-foreground">
                            {new Date(cert.issued_at).toLocaleDateString('es-ES')}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <Award className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Completa cursos para obtener certificados</p>
                </div>
              )}
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  );
};

export default StudentUI;
