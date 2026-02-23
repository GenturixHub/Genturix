/**
 * GENTURIX - Embedded Profile Component
 * Profile editor that can be embedded in any UI (Guard, Resident, etc.)
 * Does NOT use DashboardLayout - designed for tab-based UIs
 * 
 * Design: Minimal premium style inspired by Linear/Stripe
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Textarea } from './ui/textarea';
import { ScrollArea } from './ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from './ui/dialog';
import api from '../services/api';
import { PushNotificationToggle } from './PushNotificationBanner';
import LanguageSelector from './LanguageSelector';
import ChangePasswordForm from './ChangePasswordForm';
import { 
  User,
  Phone,
  Building2,
  Shield,
  Home,
  Briefcase,
  GraduationCap,
  UserCheck,
  Camera,
  Save,
  Loader2,
  CheckCircle,
  XCircle,
  FileText,
  X,
  ZoomIn,
  LogOut,
  ArrowLeft,
  Key,
  Pencil
} from 'lucide-react';

// Role configuration with i18n keys
const ROLE_CONFIG = {
  'Administrador': { icon: Shield, color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20', key: 'admin' },
  'Residente': { icon: Home, color: 'bg-blue-500/10 text-blue-400 border-blue-500/20', key: 'resident' },
  'Guarda': { icon: Shield, color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20', key: 'guard' },
  'HR': { icon: Briefcase, color: 'bg-amber-500/10 text-amber-400 border-amber-500/20', key: 'hr' },
  'Supervisor': { icon: UserCheck, color: 'bg-violet-500/10 text-violet-400 border-violet-500/20', key: 'supervisor' },
  'Estudiante': { icon: GraduationCap, color: 'bg-pink-500/10 text-pink-400 border-pink-500/20', key: 'student' },
  'SuperAdmin': { icon: Shield, color: 'bg-red-500/10 text-red-400 border-red-500/20', key: 'superadmin' },
};

// Minimal Section Component
const ProfileSection = ({ icon: Icon, title, description, children, className = '' }) => (
  <div className={`rounded-2xl bg-white/[0.02] p-4 space-y-3 ${className}`}>
    <div className="flex items-center gap-2.5">
      {Icon && <Icon className="w-4 h-4 text-white/40" />}
      <div>
        <h3 className="text-sm font-semibold text-white/90">{title}</h3>
        {description && (
          <p className="text-xs text-white/40 mt-0.5">{description}</p>
        )}
      </div>
    </div>
    {children}
  </div>
);

// Minimal Input Style
const minimalInputClass = `
  bg-transparent 
  border border-white/10 
  rounded-xl 
  h-10 
  px-3 
  text-sm 
  text-white/90
  placeholder:text-white/30
  focus:border-blue-500/50 
  focus:ring-1 
  focus:ring-blue-500/20
  focus:outline-none
  transition-all
  duration-200
`;

const EmbeddedProfile = ({ userId = null, onBack = null }) => {
  const { t } = useTranslation();
  const { user, refreshUser, logout } = useAuth();
  const navigate = useNavigate();
  
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [photoModalOpen, setPhotoModalOpen] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [formData, setFormData] = useState({
    full_name: '',
    phone: '',
    profile_photo: '',
    public_description: ''
  });

  const isOwnProfile = !userId || userId === user?.id;
  const currentPhoto = editMode ? formData.profile_photo : profile?.profile_photo;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      navigate(-1);
    }
  };

  useEffect(() => {
    const fetchProfile = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        let data;
        if (isOwnProfile) {
          data = await api.get('/profile');
          setFormData({
            full_name: data.full_name || '',
            phone: data.phone || '',
            profile_photo: data.profile_photo || '',
            public_description: data.public_description || ''
          });
        } else {
          data = await api.getPublicProfile(userId);
        }
        setProfile(data);
      } catch (err) {
        console.error('Error fetching profile:', err);
        setError(err.message || 'Error al cargar perfil');
        if (isOwnProfile && user) {
          setProfile(user);
          setFormData({
            full_name: user.full_name || '',
            phone: user.phone || '',
            profile_photo: user.profile_photo || '',
            public_description: user.public_description || ''
          });
        }
      } finally {
        setIsLoading(false);
      }
    };

    if (user) {
      fetchProfile();
    }
  }, [user, userId, isOwnProfile]);

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setSuccess(null);

    try {
      await api.patch('/profile', formData);
      setSuccess('Perfil actualizado correctamente');
      setEditMode(false);
      if (refreshUser) await refreshUser();
      setProfile(prev => ({ ...prev, ...formData }));
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.message || 'Error al actualizar perfil');
    } finally {
      setIsSaving(false);
    }
  };

  const handlePhotoUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      setError('La imagen no puede ser mayor a 2MB');
      return;
    }
    const reader = new FileReader();
    reader.onloadend = () => {
      setFormData(prev => ({ ...prev, profile_photo: reader.result }));
    };
    reader.readAsDataURL(file);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-white/40" />
      </div>
    );
  }

  const primaryRole = profile?.roles?.[0] || 'Usuario';
  const roleConfig = ROLE_CONFIG[primaryRole] || { icon: User, color: 'bg-white/5 text-white/60 border-white/10', label: primaryRole };

  return (
    <ScrollArea className="h-full">
      <div className="px-4 py-6 space-y-5 max-w-lg mx-auto">
        
        {/* Back Button */}
        {onBack && (
          <button
            onClick={handleBack}
            className="flex items-center gap-1.5 text-sm text-white/40 hover:text-white/70 transition-colors mb-2"
            data-testid="profile-back-btn"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Volver</span>
          </button>
        )}

        {/* Toast Messages */}
        {success && (
          <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
            <span>{success}</span>
          </div>
        )}
        {error && (
          <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <XCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Profile Header - Centered, Minimal */}
        <div className="flex flex-col items-center text-center pt-2 pb-4">
          {/* Avatar */}
          <div 
            className="relative group cursor-pointer mb-4"
            onClick={() => currentPhoto && setPhotoModalOpen(true)}
          >
            <Avatar className="w-[88px] h-[88px] ring-2 ring-white/10 ring-offset-2 ring-offset-[#05050A]">
              <AvatarImage src={currentPhoto} className="object-cover" />
              <AvatarFallback className="bg-gradient-to-br from-blue-500/20 to-violet-500/20 text-white/80 text-2xl font-medium">
                {profile?.full_name?.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            
            {/* Zoom overlay */}
            {currentPhoto && !editMode && (
              <div className="absolute inset-0 rounded-full bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <ZoomIn className="w-5 h-5 text-white/90" />
              </div>
            )}
            
            {/* Photo upload button */}
            {editMode && isOwnProfile && (
              <label className="absolute -bottom-1 -right-1 p-2 bg-blue-500 rounded-full cursor-pointer hover:bg-blue-600 transition-colors shadow-lg shadow-blue-500/25">
                <Camera className="w-3.5 h-3.5 text-white" />
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handlePhotoUpload}
                />
              </label>
            )}
          </div>

          {/* Name */}
          {editMode && isOwnProfile ? (
            <input
              value={formData.full_name}
              onChange={(e) => setFormData(prev => ({ ...prev, full_name: e.target.value }))}
              className="text-xl font-bold text-white bg-transparent border-b border-white/20 focus:border-blue-500/50 outline-none text-center px-2 py-1 mb-1 w-full max-w-[250px]"
              placeholder="Nombre completo"
            />
          ) : (
            <h1 className="text-xl font-bold text-white mb-1">{profile?.full_name}</h1>
          )}

          {/* Email */}
          {isOwnProfile && (
            <p className="text-sm text-white/40 mb-3">{profile?.email}</p>
          )}

          {/* Role Badges - Minimal Pills */}
          <div className="flex items-center gap-1.5 flex-wrap justify-center">
            {profile?.roles?.map((role, index) => {
              const config = ROLE_CONFIG[role] || { color: 'bg-white/5 text-white/60 border-white/10', key: 'other' };
              const roleLabel = t(`roles.${config.key}`, role);
              return (
                <span 
                  key={index} 
                  className={`px-2.5 py-1 text-xs font-medium rounded-full border ${config.color}`}
                >
                  {roleLabel}
                </span>
              );
            })}
          </div>

          {/* Edit Toggle */}
          {isOwnProfile && (
            <div className="mt-4">
              {editMode ? (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setEditMode(false)}
                    className="px-3 py-1.5 text-xs text-white/60 hover:text-white/90 transition-colors"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors disabled:opacity-50"
                  >
                    {isSaving ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <Save className="w-3 h-3" />
                    )}
                    <span>Guardar</span>
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setEditMode(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-white/50 hover:text-white/80 border border-white/10 hover:border-white/20 rounded-lg transition-all"
                  data-testid="embedded-edit-btn"
                >
                  <Pencil className="w-3 h-3" />
                  <span>Editar perfil</span>
                </button>
              )}
            </div>
          )}
        </div>

        {/* Contact Section */}
        <ProfileSection icon={Phone} title={t('profile.contact')}>
          {editMode && isOwnProfile ? (
            <input
              value={formData.phone}
              onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
              className={minimalInputClass}
              placeholder="+52 555 123 4567"
            />
          ) : (
            <p className="text-sm text-white/60">{profile?.phone || t('profile.notSpecified')}</p>
          )}
        </ProfileSection>

        {/* Condominium Section */}
        <ProfileSection icon={Building2} title={t('profile.condominium')}>
          <p className="text-sm text-white/80">{profile?.condominium_name || t('profile.notSpecified')}</p>
        </ProfileSection>

        {/* Description Section */}
        <ProfileSection 
          icon={FileText} 
          title={isOwnProfile ? t('profile.publicDescription') : t('profile.about', 'About')}
          description={isOwnProfile && !editMode ? t('profile.publicDescriptionHint') : null}
        >
          {editMode && isOwnProfile ? (
            <textarea
              value={formData.public_description}
              onChange={(e) => setFormData(prev => ({ ...prev, public_description: e.target.value }))}
              className={`${minimalInputClass} min-h-[80px] resize-none py-2.5`}
              placeholder={t('profile.publicDescriptionPlaceholder', 'Write a brief description about yourself...')}
            />
          ) : (
            <p className="text-sm text-white/50 leading-relaxed">
              {profile?.public_description || t('profile.noDescription', 'No description')}
            </p>
          )}
        </ProfileSection>

        {/* Security Section */}
        {isOwnProfile && (
          <ProfileSection 
            icon={Key} 
            title={t('profile.security', 'Seguridad')}
            description={t('profile.securityDescription', 'Administra tu contraseña')}
          >
            <ChangePasswordForm 
              embedded={true}
              onSuccess={() => {
                setSuccess(t('profile.passwordChanged', 'Contraseña actualizada. Tu sesión será cerrada.'));
              }}
            />
          </ProfileSection>
        )}

        {/* Push Notifications - Only for security roles */}
        {isOwnProfile && profile?.roles?.some(role => ['Guarda', 'Guardia', 'Administrador', 'Supervisor', 'SuperAdmin'].includes(role)) && (
          <ProfileSection 
            icon={Shield} 
            title={t('security.panicAlerts')}
            description={t('profile.alertNotificationsHint', 'Receive panic alerts in real time')}
          >
            <PushNotificationToggle />
          </ProfileSection>
        )}

        {/* Language Selector */}
        {isOwnProfile && (
          <LanguageSelector />
        )}

        {/* Logout Button */}
        {isOwnProfile && (
          <div className="pt-4">
            <button
              onClick={() => setShowLogoutConfirm(true)}
              className="w-full flex items-center justify-center gap-2 py-3 text-sm text-red-400/80 hover:text-red-400 border border-red-500/20 hover:border-red-500/30 rounded-xl transition-all"
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4" />
              <span>Cerrar Sesión</span>
            </button>
          </div>
        )}

        {/* Photo Modal */}
        <Dialog open={photoModalOpen} onOpenChange={setPhotoModalOpen}>
          <DialogContent className="max-w-2xl bg-black/95 border-white/10 p-0 overflow-hidden">
            <div className="relative flex items-center justify-center min-h-[300px] max-h-[70vh]">
              <button
                className="absolute top-3 right-3 z-10 p-2 bg-white/10 hover:bg-white/20 rounded-full transition-colors"
                onClick={() => setPhotoModalOpen(false)}
              >
                <X className="w-4 h-4 text-white" />
              </button>
              {currentPhoto && (
                <img src={currentPhoto} alt={profile?.full_name} className="max-w-full max-h-[70vh] object-contain" />
              )}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent p-4">
                <h3 className="text-white text-lg font-semibold">{profile?.full_name}</h3>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Logout Confirmation Dialog */}
        <Dialog open={showLogoutConfirm} onOpenChange={setShowLogoutConfirm}>
          <DialogContent className="bg-[#0A0A0F] border-white/10 max-w-sm rounded-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-white">
                <LogOut className="w-4 h-4 text-red-400" />
                Cerrar Sesión
              </DialogTitle>
              <DialogDescription className="text-white/50">
                ¿Estás seguro de que deseas cerrar sesión?
              </DialogDescription>
            </DialogHeader>
            <DialogFooter className="flex-col sm:flex-row gap-2 mt-4">
              <button 
                onClick={() => setShowLogoutConfirm(false)}
                className="px-4 py-2 text-sm text-white/60 hover:text-white/90 border border-white/10 hover:border-white/20 rounded-xl transition-all"
              >
                Cancelar
              </button>
              <button 
                onClick={handleLogout}
                className="px-4 py-2 text-sm font-medium text-white bg-red-500/90 hover:bg-red-500 rounded-xl transition-colors flex items-center justify-center gap-2"
              >
                <LogOut className="w-3.5 h-3.5" />
                Cerrar Sesión
              </button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

      </div>
    </ScrollArea>
  );
};

export default EmbeddedProfile;
