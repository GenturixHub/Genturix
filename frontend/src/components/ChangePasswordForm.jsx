/**
 * GENTURIX - Change Password Component
 * 
 * Secure password change functionality for all authenticated users.
 * Features:
 * - Real-time password validation
 * - Password strength requirements (8+ chars, 1 uppercase, 1 number)
 * - Confirm password match validation
 * - Invalidates all previous sessions after change
 */

import React, { useState, useEffect, useMemo } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { toast } from 'sonner';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import {
  Lock,
  Eye,
  EyeOff,
  Check,
  X,
  Loader2,
  Shield,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';

// Password validation requirements
const PASSWORD_REQUIREMENTS = [
  { id: 'length', label: 'Al menos 8 caracteres', test: (pwd) => pwd.length >= 8 },
  { id: 'uppercase', label: 'Una letra mayúscula', test: (pwd) => /[A-Z]/.test(pwd) },
  { id: 'number', label: 'Un número', test: (pwd) => /\d/.test(pwd) },
];

const ChangePasswordForm = ({ onSuccess }) => {
  const { logout } = useAuth();
  const [formData, setFormData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [touched, setTouched] = useState({
    currentPassword: false,
    newPassword: false,
    confirmPassword: false
  });

  // Validate password requirements
  const passwordValidation = useMemo(() => {
    return PASSWORD_REQUIREMENTS.map(req => ({
      ...req,
      passed: req.test(formData.newPassword)
    }));
  }, [formData.newPassword]);

  // Check if all requirements are met
  const allRequirementsMet = passwordValidation.every(req => req.passed);

  // Check if passwords match
  const passwordsMatch = formData.newPassword === formData.confirmPassword && formData.confirmPassword.length > 0;

  // Check if new password is different from current
  const passwordIsDifferent = formData.currentPassword !== formData.newPassword && formData.newPassword.length > 0;

  // Form is valid when all conditions are met
  const isFormValid = 
    formData.currentPassword.length > 0 &&
    allRequirementsMet &&
    passwordsMatch &&
    passwordIsDifferent;

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (!touched[field]) {
      setTouched(prev => ({ ...prev, [field]: true }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!isFormValid) return;

    setIsSubmitting(true);
    
    try {
      const response = await api.changePassword(
        formData.currentPassword,
        formData.newPassword,
        formData.confirmPassword
      );
      
      toast.success('Contraseña actualizada exitosamente', {
        description: 'Tu sesión actual se mantendrá activa. Las sesiones en otros dispositivos serán cerradas.'
      });
      
      // Clear form
      setFormData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
      setTouched({
        currentPassword: false,
        newPassword: false,
        confirmPassword: false
      });
      
      if (onSuccess) {
        onSuccess(response);
      }
      
    } catch (error) {
      console.error('Password change error:', error);
      
      // Handle specific error messages
      const errorMessage = error.message || 'Error al cambiar la contraseña';
      
      if (errorMessage.includes('incorrecta')) {
        toast.error('Contraseña actual incorrecta', {
          description: 'Verifica tu contraseña actual e intenta de nuevo.'
        });
      } else if (errorMessage.includes('diferente')) {
        toast.error('Contraseña inválida', {
          description: 'La nueva contraseña debe ser diferente a la actual.'
        });
      } else if (errorMessage.includes('mayúscula') || errorMessage.includes('número')) {
        toast.error('Contraseña no cumple requisitos', {
          description: errorMessage
        });
      } else {
        toast.error('Error al cambiar contraseña', {
          description: errorMessage
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const togglePasswordVisibility = (field) => {
    setShowPasswords(prev => ({ ...prev, [field]: !prev[field] }));
  };

  return (
    <Card className="bg-[#0F111A] border-[#1E293B]">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Shield className="w-5 h-5 text-primary" />
          Cambiar Contraseña
        </CardTitle>
        <CardDescription>
          Actualiza tu contraseña para mantener tu cuenta segura
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Current Password */}
          <div className="space-y-2">
            <Label htmlFor="currentPassword" className="text-sm">
              Contraseña Actual
            </Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                id="currentPassword"
                type={showPasswords.current ? 'text' : 'password'}
                value={formData.currentPassword}
                onChange={(e) => handleInputChange('currentPassword', e.target.value)}
                placeholder="Tu contraseña actual"
                className="bg-[#0A0A0F] border-[#1E293B] pl-10 pr-10"
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => togglePasswordVisibility('current')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white transition-colors"
              >
                {showPasswords.current ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* New Password */}
          <div className="space-y-2">
            <Label htmlFor="newPassword" className="text-sm">
              Nueva Contraseña
            </Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                id="newPassword"
                type={showPasswords.new ? 'text' : 'password'}
                value={formData.newPassword}
                onChange={(e) => handleInputChange('newPassword', e.target.value)}
                placeholder="Tu nueva contraseña"
                className={`bg-[#0A0A0F] border-[#1E293B] pl-10 pr-10 ${
                  touched.newPassword && !allRequirementsMet ? 'border-yellow-500/50' : ''
                } ${touched.newPassword && allRequirementsMet ? 'border-green-500/50' : ''}`}
                autoComplete="new-password"
              />
              <button
                type="button"
                onClick={() => togglePasswordVisibility('new')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white transition-colors"
              >
                {showPasswords.new ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            
            {/* Password Requirements */}
            {touched.newPassword && (
              <div className="mt-3 p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B] space-y-2">
                <p className="text-xs text-muted-foreground mb-2">Requisitos de contraseña:</p>
                {passwordValidation.map(req => (
                  <div key={req.id} className="flex items-center gap-2 text-xs">
                    {req.passed ? (
                      <Check className="w-3.5 h-3.5 text-green-400" />
                    ) : (
                      <X className="w-3.5 h-3.5 text-red-400" />
                    )}
                    <span className={req.passed ? 'text-green-400' : 'text-muted-foreground'}>
                      {req.label}
                    </span>
                  </div>
                ))}
                
                {/* Different from current warning */}
                {formData.currentPassword && formData.newPassword && !passwordIsDifferent && (
                  <div className="flex items-center gap-2 text-xs mt-2 pt-2 border-t border-[#1E293B]">
                    <AlertTriangle className="w-3.5 h-3.5 text-yellow-400" />
                    <span className="text-yellow-400">Debe ser diferente a la actual</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Confirm Password */}
          <div className="space-y-2">
            <Label htmlFor="confirmPassword" className="text-sm">
              Confirmar Nueva Contraseña
            </Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                id="confirmPassword"
                type={showPasswords.confirm ? 'text' : 'password'}
                value={formData.confirmPassword}
                onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                placeholder="Confirma tu nueva contraseña"
                className={`bg-[#0A0A0F] border-[#1E293B] pl-10 pr-10 ${
                  touched.confirmPassword && formData.confirmPassword && !passwordsMatch ? 'border-red-500/50' : ''
                } ${touched.confirmPassword && passwordsMatch ? 'border-green-500/50' : ''}`}
                autoComplete="new-password"
              />
              <button
                type="button"
                onClick={() => togglePasswordVisibility('confirm')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white transition-colors"
              >
                {showPasswords.confirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            
            {/* Match indicator */}
            {touched.confirmPassword && formData.confirmPassword && (
              <div className="flex items-center gap-2 text-xs mt-1">
                {passwordsMatch ? (
                  <>
                    <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                    <span className="text-green-400">Las contraseñas coinciden</span>
                  </>
                ) : (
                  <>
                    <X className="w-3.5 h-3.5 text-red-400" />
                    <span className="text-red-400">Las contraseñas no coinciden</span>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Security Notice */}
          <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-start gap-2">
            <Shield className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-blue-400">
              <strong>Nota de seguridad:</strong> Al cambiar tu contraseña, todas las sesiones activas en otros dispositivos serán cerradas automáticamente.
            </div>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            disabled={!isFormValid || isSubmitting}
            className="w-full"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Actualizando...
              </>
            ) : (
              <>
                <Shield className="w-4 h-4 mr-2" />
                Cambiar Contraseña
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};

export default ChangePasswordForm;
