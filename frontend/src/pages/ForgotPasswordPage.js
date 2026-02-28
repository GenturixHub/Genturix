/**
 * GENTURIX - Forgot Password Page
 * 
 * Allows users to reset their password via email verification code.
 * Flow: Enter email → Receive code → Enter new password
 */

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { 
  Mail, 
  KeyRound, 
  Lock, 
  ArrowLeft, 
  Loader2, 
  CheckCircle,
  Shield
} from 'lucide-react';
import api from '../services/api';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const ForgotPasswordPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  
  // Step: 'email' | 'code' | 'success'
  const [step, setStep] = useState('email');
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');

  // Step 1: Request password reset code
  const handleRequestCode = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!email.trim()) {
      setError('Por favor ingresa tu correo electrónico');
      return;
    }
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('Por favor ingresa un correo electrónico válido');
      return;
    }
    
    setIsLoading(true);
    
    try {
      const response = await fetch(`${API_URL}/api/auth/request-password-reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase() })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        toast.success('Código enviado a tu correo electrónico');
        setStep('code');
      } else {
        setError(data.detail || 'Error al enviar el código');
      }
    } catch (err) {
      setError('Error de conexión. Intenta nuevamente.');
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2: Verify code and set new password
  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!code.trim()) {
      setError('Por favor ingresa el código de verificación');
      return;
    }
    
    if (code.length !== 6) {
      setError('El código debe tener 6 dígitos');
      return;
    }
    
    if (!newPassword || newPassword.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres');
      return;
    }
    
    if (newPassword !== confirmPassword) {
      setError('Las contraseñas no coinciden');
      return;
    }
    
    // Password strength validation
    const hasUppercase = /[A-Z]/.test(newPassword);
    const hasNumber = /[0-9]/.test(newPassword);
    if (!hasUppercase || !hasNumber) {
      setError('La contraseña debe contener al menos una mayúscula y un número');
      return;
    }
    
    setIsLoading(true);
    
    try {
      const response = await fetch(`${API_URL}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          code: code.trim(),
          new_password: newPassword
        })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        toast.success('Contraseña actualizada exitosamente');
        setStep('success');
      } else {
        if (data.detail?.includes('expired')) {
          setError('El código ha expirado. Solicita uno nuevo.');
        } else if (data.detail?.includes('invalid')) {
          setError('Código inválido. Verifica e intenta nuevamente.');
        } else {
          setError(data.detail || 'Error al restablecer la contraseña');
        }
      }
    } catch (err) {
      setError('Error de conexión. Intenta nuevamente.');
    } finally {
      setIsLoading(false);
    }
  };

  // Step 3: Success - redirect to login
  if (step === 'success') {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-[#0F111A] border-[#1E293B]">
          <CardContent className="pt-8 text-center">
            <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="w-8 h-8 text-green-500" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">¡Contraseña Actualizada!</h2>
            <p className="text-muted-foreground mb-6">
              Tu contraseña ha sido restablecida exitosamente. Ya puedes iniciar sesión con tu nueva contraseña.
            </p>
            <Button 
              onClick={() => navigate('/login')} 
              className="w-full"
              data-testid="go-to-login"
            >
              Ir a Iniciar Sesión
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#05050A] flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Header */}
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-primary/20 flex items-center justify-center mx-auto mb-4">
            <Shield className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-2xl font-bold text-white">GENTURIX</h1>
          <p className="text-muted-foreground">Recuperar Contraseña</p>
        </div>

        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {step === 'email' ? (
                <>
                  <Mail className="w-5 h-5 text-primary" />
                  Ingresa tu correo
                </>
              ) : (
                <>
                  <KeyRound className="w-5 h-5 text-primary" />
                  Verifica tu código
                </>
              )}
            </CardTitle>
            <CardDescription>
              {step === 'email' 
                ? 'Te enviaremos un código de verificación'
                : 'Ingresa el código enviado a tu correo y tu nueva contraseña'
              }
            </CardDescription>
          </CardHeader>
          
          <CardContent>
            {step === 'email' ? (
              <form onSubmit={handleRequestCode} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Correo Electrónico</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="tu@correo.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="bg-[#1E293B] border-[#374151]"
                    data-testid="forgot-email-input"
                    autoFocus
                  />
                </div>
                
                {error && (
                  <p className="text-sm text-red-500" data-testid="forgot-error">{error}</p>
                )}
                
                <Button 
                  type="submit" 
                  className="w-full" 
                  disabled={isLoading}
                  data-testid="send-code-btn"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Enviando...
                    </>
                  ) : (
                    <>
                      <Mail className="w-4 h-4 mr-2" />
                      Enviar Código
                    </>
                  )}
                </Button>
              </form>
            ) : (
              <form onSubmit={handleResetPassword} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="code">Código de Verificación</Label>
                  <Input
                    id="code"
                    type="text"
                    placeholder="123456"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    className="bg-[#1E293B] border-[#374151] text-center text-2xl tracking-widest"
                    maxLength={6}
                    data-testid="verification-code-input"
                    autoFocus
                  />
                  <p className="text-xs text-muted-foreground">
                    Código enviado a: {email}
                  </p>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="newPassword">Nueva Contraseña</Label>
                  <Input
                    id="newPassword"
                    type="password"
                    placeholder="Mínimo 8 caracteres"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="bg-[#1E293B] border-[#374151]"
                    data-testid="new-password-input"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirmar Contraseña</Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="Repite la contraseña"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="bg-[#1E293B] border-[#374151]"
                    data-testid="confirm-password-input"
                  />
                </div>
                
                {error && (
                  <p className="text-sm text-red-500" data-testid="reset-error">{error}</p>
                )}
                
                <Button 
                  type="submit" 
                  className="w-full" 
                  disabled={isLoading}
                  data-testid="reset-password-btn"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Procesando...
                    </>
                  ) : (
                    <>
                      <Lock className="w-4 h-4 mr-2" />
                      Restablecer Contraseña
                    </>
                  )}
                </Button>
                
                <Button
                  type="button"
                  variant="ghost"
                  className="w-full text-muted-foreground"
                  onClick={() => {
                    setStep('email');
                    setCode('');
                    setNewPassword('');
                    setConfirmPassword('');
                    setError('');
                  }}
                >
                  Solicitar nuevo código
                </Button>
              </form>
            )}
          </CardContent>
        </Card>

        {/* Back to login link */}
        <div className="text-center">
          <Link 
            to="/login" 
            className="text-sm text-muted-foreground hover:text-primary transition-colors inline-flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Volver al inicio de sesión
          </Link>
        </div>
      </div>
    </div>
  );
};

export default ForgotPasswordPage;
