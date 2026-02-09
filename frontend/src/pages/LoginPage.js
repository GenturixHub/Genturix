import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
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

// Password Change Dialog Component
const PasswordChangeDialog = ({ open, onClose, onSuccess, tempPassword }) => {
  const { t } = useTranslation();
  const { changePassword } = useAuth();
  const [currentPassword, setCurrentPassword] = useState(tempPassword || '');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswords, setShowPasswords] = useState(false);
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const validatePassword = (pwd) => {
    if (pwd.length < 8) return t('auth.passwordMinLength', 'Password must be at least 8 characters');
    if (!/[A-Z]/.test(pwd)) return t('auth.passwordUppercase', 'Must include at least one uppercase letter');
    if (!/[a-z]/.test(pwd)) return t('auth.passwordLowercase', 'Must include at least one lowercase letter');
    if (!/[0-9]/.test(pwd)) return t('auth.passwordNumber', 'Must include at least one number');
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
      setError(t('auth.passwordsNoMatch', 'Passwords do not match'));
      return;
    }
    
    if (currentPassword === newPassword) {
      setError(t('auth.passwordMustBeDifferent', 'New password must be different from temporary'));
      return;
    }
    
    setIsSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      onSuccess();
    } catch (err) {
      setError(err.message || t('auth.changePasswordError', 'Error changing password'));
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
            {t('auth.passwordChangeRequired', 'Password Change Required')}
          </DialogTitle>
          <DialogDescription>
            {t('auth.passwordChangeDescription', 'For security, you must set a new password before continuing.')}
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
              {t('auth.tempPasswordWarning', 'Your temporary password will expire after this change. Save your new password in a safe place.')}
            </p>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="currentPassword">{t('auth.tempPassword', 'Temporary Password')}</Label>
            <Input
              id="currentPassword"
              type={showPasswords ? 'text' : 'password'}
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder={t('auth.tempPasswordPlaceholder', 'Password received by email')}
              required
              className="bg-[#0A0A0F] border-[#1E293B]"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="newPassword">{t('auth.newPassword')}</Label>
            <Input
              id="newPassword"
              type={showPasswords ? 'text' : 'password'}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder={t('auth.minChars', 'Minimum 8 characters')}
              required
              className="bg-[#0A0A0F] border-[#1E293B]"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="confirmPassword">{t('auth.confirmPassword')}</Label>
            <Input
              id="confirmPassword"
              type={showPasswords ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder={t('auth.repeatPassword', 'Repeat new password')}
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
              {t('auth.showPasswords', 'Show passwords')}
            </Label>
          </div>
          
          <div className="text-xs text-muted-foreground space-y-1">
            <p>{t('auth.passwordMustHave', 'Password must have')}:</p>
            <ul className="list-disc list-inside pl-2">
              <li className={newPassword.length >= 8 ? 'text-green-400' : ''}>{t('auth.atLeast8Chars', 'At least 8 characters')}</li>
              <li className={/[A-Z]/.test(newPassword) ? 'text-green-400' : ''}>{t('auth.oneUppercase', 'One uppercase letter')}</li>
              <li className={/[a-z]/.test(newPassword) ? 'text-green-400' : ''}>{t('auth.oneLowercase', 'One lowercase letter')}</li>
              <li className={/[0-9]/.test(newPassword) ? 'text-green-400' : ''}>{t('auth.oneNumber', 'One number')}</li>
            </ul>
          </div>
          
          <DialogFooter>
            <Button type="submit" disabled={isSubmitting} className="w-full">
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {t('auth.changing', 'Changing...')}
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  {t('auth.setNewPassword', 'Set New Password')}
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
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login, user, passwordResetRequired, isAuthenticated } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [loggedInUser, setLoggedInUser] = useState(null);
  const [tempPassword, setTempPassword] = useState('');

  // Handle case when user is already authenticated but needs password reset
  // This happens on page reload or direct access to /login
  useEffect(() => {
    if (isAuthenticated && passwordResetRequired && user) {
      setLoggedInUser(user);
      setShowPasswordChange(true);
    }
  }, [isAuthenticated, passwordResetRequired, user]);
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
      setError(err.message || t('auth.loginError'));
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

  React.useEffect(() => {
    const remembered = localStorage.getItem('rememberedEmail');
    if (remembered) {
      setEmail(remembered);
      setRememberMe(true);
    }
  }, []);

  return (
    <div className="h-screen flex flex-col bg-[#05050A] overflow-hidden">
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
      <div className="relative z-10 flex-1 flex flex-col justify-center items-center p-4">
        <div className="w-full max-w-md space-y-5">
          {/* Logo */}
          <div className="flex flex-col items-center text-center">
            <GenturixLogo size={80} className="mb-3" />
            <h1 className="text-2xl md:text-3xl font-bold font-['Outfit'] text-white">GENTURIX</h1>
            <p className="text-xs text-muted-foreground mt-1">{t('auth.platformTagline', 'Security & Emergency Platform')}</p>
          </div>

          {/* Login Card */}
          <Card className="bg-[#0F111A]/90 backdrop-blur-xl border-[#1E293B]">
            <CardHeader className="space-y-1 text-center pb-3 pt-5">
              <CardTitle className="text-lg font-['Outfit']">{t('auth.login')}</CardTitle>
              <CardDescription className="text-xs">
                {t('auth.enterCredentials')}
              </CardDescription>
            </CardHeader>
            <CardContent className="pb-5">
              {error && (
                <Alert variant="destructive" className="mb-3 bg-red-500/10 border-red-500/20">
                  <AlertDescription className="text-sm">{error}</AlertDescription>
                </Alert>
              )}

              <form onSubmit={handleSubmit} className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="email" className="text-sm">{t('auth.email')}</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder={t('auth.emailPlaceholder', 'your@email.com')}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={isLoading}
                    required
                    autoComplete="email"
                    data-testid="login-email-input"
                    className="h-11 bg-[#181B25] border-[#1E293B] focus:border-primary"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="password" className="text-sm">{t('auth.password')}</Label>
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
                      className="h-11 bg-[#181B25] border-[#1E293B] focus:border-primary pr-12"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1"
                      data-testid="toggle-password-visibility"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
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
                  <Label htmlFor="remember" className="text-xs text-muted-foreground cursor-pointer">
                    {t('auth.rememberMe')}
                  </Label>
                </div>

                <Button
                  type="submit"
                  className="w-full h-11 bg-primary hover:bg-primary/90 text-sm font-semibold"
                  disabled={isLoading}
                  data-testid="login-submit-btn"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      {t('auth.loggingIn', 'Logging in...')}
                    </>
                  ) : (
                    t('auth.loginButton', 'Sign In')
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Footer */}
          <div className="text-center">
            <p className="text-[10px] text-muted-foreground">
              GENTURIX v1.0 • {t('auth.enterprisePlatform', 'Enterprise Security Platform')}
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
