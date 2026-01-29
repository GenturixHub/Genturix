import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Checkbox } from '../components/ui/checkbox';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import GenturixLogo from '../components/GenturixLogo';
import api from '../services/api';

const LoginPage = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const user = await login(email, password);
      
      if (rememberMe) {
        localStorage.setItem('rememberedEmail', email);
      } else {
        localStorage.removeItem('rememberedEmail');
      }

      // Role-based redirect
      const roles = user.roles || [];
      if (roles.length === 1) {
        switch (roles[0]) {
          case 'Residente':
            navigate('/resident');
            return;
          case 'Guarda':
            navigate('/guard');
            return;
          case 'Estudiante':
            navigate('/student');
            return;
          case 'HR':
            navigate('/rrhh');
            return;
          case 'Supervisor':
            navigate('/rrhh');
            return;
          default:
            navigate('/admin/dashboard');
        }
      } else if (roles.length > 1) {
        navigate('/select-panel');
      } else {
        navigate('/dashboard');
      }
    } catch (err) {
      setError(err.message || 'Email o contraseña incorrectos');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSeedDemo = async () => {
    setIsSeeding(true);
    try {
      await api.seedDemoData();
      setError(null);
      alert('✅ Datos de demo creados!\n\nAdmin: admin@genturix.com / Admin123!\nGuarda: guarda1@genturix.com / Guard123!\nResidente: residente@genturix.com / Resi123!');
    } catch (err) {
      if (err.message.includes('already exists')) {
        alert('Los datos de demo ya existen.\n\nPuedes usar:\nadmin@genturix.com / Admin123!');
      } else {
        setError(err.message);
      }
    } finally {
      setIsSeeding(false);
    }
  };

  React.useEffect(() => {
    const remembered = localStorage.getItem('rememberedEmail');
    if (remembered) {
      setEmail(remembered);
      setRememberMe(true);
    }
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-[#05050A] safe-area">
      {/* Background */}
      <div 
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: 'url(https://images.pexels.com/photos/5473960/pexels-photo-5473960.jpeg)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-black/80 via-[#05050A]/90 to-[#05050A]" />
      
      {/* Content */}
      <div className="relative z-10 flex-1 flex flex-col justify-center p-4 md:p-6">
        <div className="w-full max-w-md mx-auto space-y-6 md:space-y-8">
          {/* Logo */}
          <div className="flex flex-col items-center text-center">
            <div className="w-28 h-28 md:w-36 md:h-36 rounded-2xl overflow-hidden mb-4">
              <img 
                src="/genturix-logo.png" 
                alt="Genturix Logo" 
                className="w-full h-full object-cover"
              />
            </div>
            <h1 className="text-3xl md:text-4xl font-bold font-['Outfit'] text-white">GENTURIX</h1>
            <p className="text-sm text-muted-foreground mt-1">Plataforma de Seguridad y Emergencias</p>
          </div>

          {/* Login Card */}
          <Card className="bg-[#0F111A]/90 backdrop-blur-xl border-[#1E293B]">
            <CardHeader className="space-y-1 text-center pb-4">
              <CardTitle className="text-xl font-['Outfit']">Iniciar Sesión</CardTitle>
              <CardDescription className="text-sm">
                Ingresa tus credenciales
              </CardDescription>
            </CardHeader>
            <CardContent>
              {error && (
                <Alert variant="destructive" className="mb-4 bg-red-500/10 border-red-500/20">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Correo Electrónico</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="tu@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={isLoading}
                    required
                    autoComplete="email"
                    data-testid="login-email-input"
                    className="h-12 bg-[#181B25] border-[#1E293B] focus:border-primary"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Contraseña</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      disabled={isLoading}
                      required
                      autoComplete="current-password"
                      data-testid="login-password-input"
                      className="h-12 bg-[#181B25] border-[#1E293B] focus:border-primary pr-12"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1"
                      data-testid="toggle-password-visibility"
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="remember"
                    checked={rememberMe}
                    onCheckedChange={setRememberMe}
                    data-testid="remember-me-checkbox"
                  />
                  <Label htmlFor="remember" className="text-sm text-muted-foreground cursor-pointer">
                    Recordar sesión
                  </Label>
                </div>

                <Button
                  type="submit"
                  className="w-full h-12 bg-primary hover:bg-primary/90 text-base font-semibold"
                  disabled={isLoading}
                  data-testid="login-submit-btn"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      Ingresando...
                    </>
                  ) : (
                    'Ingresar'
                  )}
                </Button>
              </form>

              {/* Demo Data Button */}
              <div className="mt-6 pt-6 border-t border-[#1E293B]">
                <Button
                  type="button"
                  variant="outline"
                  className="w-full h-11 border-[#1E293B] hover:bg-muted text-sm"
                  onClick={handleSeedDemo}
                  disabled={isSeeding}
                  data-testid="seed-demo-btn"
                >
                  {isSeeding ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Creando datos...
                    </>
                  ) : (
                    'Crear Datos de Demo'
                  )}
                </Button>
                <p className="text-xs text-center text-muted-foreground mt-2">
                  Crea usuarios de prueba para explorar
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Footer */}
          <div className="text-center space-y-2">
            <p className="text-xs text-muted-foreground">
              GENTURIX v1.0 • $1/usuario/mes
            </p>
            <p className="text-[10px] text-muted-foreground">
              Plataforma de Seguridad Enterprise
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
