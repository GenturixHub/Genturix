import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Checkbox } from '../components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { Eye, EyeOff, Loader2, AlertTriangle, Shield, CheckCircle } from 'lucide-react';
import GenturixLogo from '../components/GenturixLogo';
import api from '../services/api';

// Password Change Dialog Component
const PasswordChangeDialog = ({ open, onClose, onSuccess, tempPassword }) => {
  const { changePassword } = useAuth();
  const [currentPassword, setCurrentPassword] = useState(tempPassword || '');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswords, setShowPasswords] = useState(false);
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const validatePassword = (pwd) => {
    if (pwd.length < 8) return 'La contraseña debe tener al menos 8 caracteres';
    if (!/[A-Z]/.test(pwd)) return 'Debe incluir al menos una mayúscula';
    if (!/[a-z]/.test(pwd)) return 'Debe incluir al menos una minúscula';
    if (!/[0-9]/.test(pwd)) return 'Debe incluir al menos un número';
    return null;
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    
    // Validate new password
    const passwordError = validatePassword(newPassword);
    if (passwordError) {
      setError(passwordError);
      return;
    }
    
    if (newPassword !== confirmPassword) {
      setError('Las contraseñas no coinciden');
      return;
    }
    
    if (currentPassword === newPassword) {
      setError('La nueva contraseña debe ser diferente a la temporal');
      return;
    }
    
    setIsSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      onSuccess();
    } catch (err) {
      setError(err.message || 'Error al cambiar la contraseña');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md" onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary" />
            Cambio de Contraseña Requerido
          </DialogTitle>
          <DialogDescription>
            Por seguridad, debes establecer una nueva contraseña antes de continuar.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <Alert variant="destructive" className="bg-red-500/10 border-red-500/20">
              <AlertTriangle className="w-4 h-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          
          <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
            <p className="text-xs text-yellow-400 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              Tu contraseña temporal expirará después de este cambio. Guarda tu nueva contraseña en un lugar seguro.
            </p>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="currentPassword">Contraseña Temporal</Label>
            <Input
              id="currentPassword"
              type={showPasswords ? 'text' : 'password'}
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="Contraseña recibida por email"
              required
              className="bg-[#0A0A0F] border-[#1E293B]"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="newPassword">Nueva Contraseña</Label>
            <Input
              id="newPassword"
              type={showPasswords ? 'text' : 'password'}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Mínimo 8 caracteres"
              required
              className="bg-[#0A0A0F] border-[#1E293B]"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="confirmPassword">Confirmar Nueva Contraseña</Label>
            <Input
              id="confirmPassword"
              type={showPasswords ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repite la nueva contraseña"
              required
              className="bg-[#0A0A0F] border-[#1E293B]"
            />
          </div>
          
          <div className="flex items-center gap-2">
            <Checkbox
              id="showPwd"
              checked={showPasswords}
              onCheckedChange={setShowPasswords}
            />
            <Label htmlFor="showPwd" className="text-sm text-muted-foreground cursor-pointer">
              Mostrar contraseñas
            </Label>
          </div>
          
          <div className="text-xs text-muted-foreground space-y-1">
            <p>La contraseña debe tener:</p>
            <ul className="list-disc list-inside pl-2">
              <li className={newPassword.length >= 8 ? 'text-green-400' : ''}>Al menos 8 caracteres</li>
              <li className={/[A-Z]/.test(newPassword) ? 'text-green-400' : ''}>Una letra mayúscula</li>
              <li className={/[a-z]/.test(newPassword) ? 'text-green-400' : ''}>Una letra minúscula</li>
              <li className={/[0-9]/.test(newPassword) ? 'text-green-400' : ''}>Un número</li>
            </ul>
          </div>
          
          <DialogFooter>
            <Button type="submit" disabled={isSubmitting} className="w-full">
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Cambiando...
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Establecer Nueva Contraseña
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

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
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [loggedInUser, setLoggedInUser] = useState(null);
  const [tempPassword, setTempPassword] = useState('');
  const navigateBasedOnRole = useCallback((user) => {
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
  }, [navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setShowPasswordChange(false);

    try {
      const result = await login(email, password);
      
      if (rememberMe) {
        localStorage.setItem('rememberedEmail', email);
      } else {
        localStorage.removeItem('rememberedEmail');
      }

      // Check if password reset is required FIRST
      if (result.passwordResetRequired) {
        setLoggedInUser(result.user);
        setTempPassword(password);
        setIsLoading(false);
        setShowPasswordChange(true);
        // Return early - DO NOT navigate
        return;
      }

      // Normal login - navigate to dashboard
      setIsLoading(false);
      navigateBasedOnRole(result.user);
    } catch (err) {
      setError(err.message || 'Email o contraseña incorrectos');
      setIsLoading(false);
    }
  };

  const handlePasswordChangeSuccess = () => {
    setShowPasswordChange(false);
    // Navigate after password change
    if (loggedInUser) {
      navigateBasedOnRole(loggedInUser);
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
            <GenturixLogo size={100} className="mb-4" />
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

      {/* Password Change Modal */}
      <PasswordChangeDialog
        open={showPasswordChange}
        onClose={() => {}}
        onSuccess={handlePasswordChangeSuccess}
        tempPassword={tempPassword}
      />
    </div>
  );
};

export default LoginPage;
