/**
 * Reset Password Page
 * Allows users to set a new password using the token from admin-initiated reset email
 */
import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import api from '../services/api';
import { 
  Lock, 
  Eye, 
  EyeOff, 
  Loader2, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  ArrowRight,
  KeyRound
} from 'lucide-react';

const ResetPasswordPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');
  
  // Token verification state
  const [verifying, setVerifying] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [tokenError, setTokenError] = useState('');
  const [userInfo, setUserInfo] = useState({ email: '', user_name: '' });
  
  // Form state
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  
  // Password validation
  const hasMinLength = newPassword.length >= 8;
  const hasUppercase = /[A-Z]/.test(newPassword);
  const hasNumber = /\d/.test(newPassword);
  const passwordsMatch = newPassword === confirmPassword && confirmPassword.length > 0;
  const allValid = hasMinLength && hasUppercase && hasNumber && passwordsMatch;

  // Verify token on mount
  useEffect(() => {
    const verifyToken = async () => {
      if (!token) {
        setTokenError('No se proporcionó un token de restablecimiento');
        setVerifying(false);
        return;
      }
      
      try {
        const result = await api.verifyResetToken(token);
        if (result.valid) {
          setTokenValid(true);
          setUserInfo({
            email: result.email,
            user_name: result.user_name
          });
        } else {
          setTokenError(result.reason || 'El enlace es inválido o ha expirado');
        }
      } catch (err) {
        console.error('Error verifying token:', err);
        setTokenError('Error al verificar el enlace. Por favor intenta de nuevo.');
      } finally {
        setVerifying(false);
      }
    };
    
    verifyToken();
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!allValid) {
      toast.error('Por favor corrige los errores en el formulario');
      return;
    }
    
    setSubmitting(true);
    try {
      await api.completePasswordReset(token, newPassword);
      setSuccess(true);
      toast.success('¡Contraseña actualizada exitosamente!');
      
      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (err) {
      console.error('Error resetting password:', err);
      toast.error(err.message || 'Error al restablecer la contraseña');
    } finally {
      setSubmitting(false);
    }
  };

  // Loading state
  if (verifying) {
    return (
      <div className="min-h-screen bg-[#0A0A0F] flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-[#0F111A] border-[#1E293B]">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center justify-center py-8 space-y-4">
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
              <p className="text-muted-foreground">Verificando enlace...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Invalid token state
  if (!tokenValid) {
    return (
      <div className="min-h-screen bg-[#0A0A0F] flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-[#0F111A] border-[#1E293B]">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
              <AlertTriangle className="w-8 h-8 text-red-400" />
            </div>
            <CardTitle className="text-red-400">Enlace Inválido</CardTitle>
            <CardDescription>{tokenError}</CardDescription>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            <p className="text-sm text-muted-foreground">
              El enlace de restablecimiento puede haber expirado o ya fue utilizado.
            </p>
            <p className="text-sm text-muted-foreground">
              Contacta a tu administrador para solicitar un nuevo enlace.
            </p>
            <Button asChild className="mt-4">
              <Link to="/login">
                Volver al Inicio de Sesión
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Success state
  if (success) {
    return (
      <div className="min-h-screen bg-[#0A0A0F] flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-[#0F111A] border-[#1E293B]">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center mb-4">
              <CheckCircle className="w-8 h-8 text-green-400" />
            </div>
            <CardTitle className="text-green-400">¡Contraseña Actualizada!</CardTitle>
            <CardDescription>Tu contraseña ha sido restablecida exitosamente.</CardDescription>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            <p className="text-sm text-muted-foreground">
              Serás redirigido al inicio de sesión en unos segundos...
            </p>
            <Button asChild className="mt-4">
              <Link to="/login" className="inline-flex items-center gap-2">
                Ir a Iniciar Sesión
                <ArrowRight className="w-4 h-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Main form
  return (
    <div className="min-h-screen bg-[#0A0A0F] flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-[#0F111A] border-[#1E293B]">
        <CardHeader className="text-center">
          <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
            <KeyRound className="w-8 h-8 text-primary" />
          </div>
          <CardTitle>Crear Nueva Contraseña</CardTitle>
          <CardDescription>
            Hola <strong className="text-foreground">{userInfo.user_name}</strong>, establece tu nueva contraseña.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* New Password */}
            <div className="space-y-2">
              <Label htmlFor="new-password">Nueva Contraseña</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  id="new-password"
                  type={showNewPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="pl-10 pr-10 bg-[#0A0A0F] border-[#1E293B]"
                  placeholder="Ingresa tu nueva contraseña"
                  autoComplete="new-password"
                  data-testid="new-password-input"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 p-0"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                >
                  {showNewPassword ? (
                    <EyeOff className="w-4 h-4 text-muted-foreground" />
                  ) : (
                    <Eye className="w-4 h-4 text-muted-foreground" />
                  )}
                </Button>
              </div>
            </div>

            {/* Confirm Password */}
            <div className="space-y-2">
              <Label htmlFor="confirm-password">Confirmar Contraseña</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  id="confirm-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="pl-10 pr-10 bg-[#0A0A0F] border-[#1E293B]"
                  placeholder="Confirma tu nueva contraseña"
                  autoComplete="new-password"
                  data-testid="confirm-password-input"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 p-0"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="w-4 h-4 text-muted-foreground" />
                  ) : (
                    <Eye className="w-4 h-4 text-muted-foreground" />
                  )}
                </Button>
              </div>
            </div>

            {/* Validation indicators */}
            <div className="space-y-2 p-3 bg-[#1E293B]/50 rounded-lg">
              <p className="text-xs font-medium text-muted-foreground mb-2">Requisitos de contraseña:</p>
              <div className="grid gap-1">
                <ValidationItem valid={hasMinLength} text="Al menos 8 caracteres" />
                <ValidationItem valid={hasUppercase} text="Al menos una mayúscula" />
                <ValidationItem valid={hasNumber} text="Al menos un número" />
                <ValidationItem valid={passwordsMatch} text="Las contraseñas coinciden" />
              </div>
            </div>

            {/* Submit button */}
            <Button
              type="submit"
              className="w-full"
              disabled={!allValid || submitting}
              data-testid="submit-reset-btn"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Actualizando...
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Actualizar Contraseña
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

// Validation indicator component
const ValidationItem = ({ valid, text }) => (
  <div className={`flex items-center gap-2 text-xs ${valid ? 'text-green-400' : 'text-muted-foreground'}`}>
    {valid ? (
      <CheckCircle className="w-3 h-3" />
    ) : (
      <XCircle className="w-3 h-3" />
    )}
    <span>{text}</span>
  </div>
);

export default ResetPasswordPage;
