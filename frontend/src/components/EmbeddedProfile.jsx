/**
 * GENTURIX - Embedded Profile Component
 * Profile editor that can be embedded in any UI (Guard, Resident, etc.)
 * Does NOT use DashboardLayout - designed for tab-based UIs
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
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
import { 
  User,
  Mail,
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
  ArrowLeft
} from 'lucide-react';

// Role configuration with i18n keys
const ROLE_CONFIG = {
  'Administrador': { icon: Shield, color: 'bg-cyan-500/10 text-cyan-400', key: 'admin' },
  'Residente': { icon: Home, color: 'bg-blue-500/10 text-blue-400', key: 'resident' },
  'Guarda': { icon: Shield, color: 'bg-green-500/10 text-green-400', key: 'guard' },
  'HR': { icon: Briefcase, color: 'bg-orange-500/10 text-orange-400', key: 'hr' },
  'Supervisor': { icon: UserCheck, color: 'bg-cyan-500/10 text-cyan-400', key: 'supervisor' },
  'Estudiante': { icon: GraduationCap, color: 'bg-cyan-500/10 text-cyan-400', key: 'student' },
  'SuperAdmin': { icon: Shield, color: 'bg-red-500/10 text-red-400', key: 'superadmin' },
};

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

  // Handle back navigation - either use provided callback or navigate
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
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const primaryRole = profile?.roles?.[0] || 'Usuario';
  const roleConfig = ROLE_CONFIG[primaryRole] || { icon: User, color: 'bg-gray-500/10 text-gray-400', label: primaryRole };

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4 max-w-2xl mx-auto">
        {/* Back Button - Always visible when onBack is provided */}
        {onBack && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
            className="mb-2 -ml-2 text-muted-foreground hover:text-white"
            data-testid="profile-back-btn"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Volver al Panel
          </Button>
        )}

        {/* Messages */}
        {success && (
          <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 flex items-center gap-2 text-sm">
            <CheckCircle className="w-4 h-4" />
            {success}
          </div>
        )}
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-2 text-sm">
            <XCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {/* Profile Header */}
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <div className="flex items-center gap-4">
              {/* Avatar */}
              <div 
                className="relative group cursor-pointer"
                onClick={() => currentPhoto && setPhotoModalOpen(true)}
              >
                <Avatar className="w-20 h-20 border-4 border-[#1E293B] transition-transform group-hover:scale-105">
                  <AvatarImage src={currentPhoto} />
                  <AvatarFallback className="bg-primary/20 text-primary text-xl">
                    {profile?.full_name?.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                {currentPhoto && !editMode && (
                  <div className="absolute inset-0 bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <ZoomIn className="w-5 h-5 text-white" />
                  </div>
                )}
                {editMode && isOwnProfile && (
                  <label className="absolute bottom-0 right-0 p-1.5 bg-primary rounded-full cursor-pointer hover:bg-primary/80 transition-colors z-10">
                    <Camera className="w-3 h-3 text-white" />
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handlePhotoUpload}
                    />
                  </label>
                )}
              </div>

              {/* Info */}
              <div className="flex-1">
                {editMode && isOwnProfile ? (
                  <Input
                    value={formData.full_name}
                    onChange={(e) => setFormData(prev => ({ ...prev, full_name: e.target.value }))}
                    className="bg-[#0A0A0F] border-[#1E293B] font-bold mb-1"
                    placeholder="Nombre completo"
                  />
                ) : (
                  <h2 className="text-lg font-bold">{profile?.full_name}</h2>
                )}
                {isOwnProfile && <p className="text-sm text-muted-foreground">{profile?.email}</p>}
                <div className="flex items-center gap-1 mt-1 flex-wrap">
                  {profile?.roles?.map((role, index) => {
                    const config = ROLE_CONFIG[role] || { color: 'bg-gray-500/10 text-gray-400', label: role };
                    return (
                      <Badge key={index} className={`${config.color} text-xs`}>
                        {config.label}
                      </Badge>
                    );
                  })}
                </div>
              </div>

              {/* Actions */}
              {isOwnProfile && (
                <div className="flex flex-col gap-2">
                  {editMode ? (
                    <>
                      <Button size="sm" variant="outline" onClick={() => setEditMode(false)}>
                        {t('common.cancel')}
                      </Button>
                      <Button size="sm" onClick={handleSave} disabled={isSaving}>
                        {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Save className="w-3 h-3 mr-1" />{t('common.save')}</>}
                      </Button>
                    </>
                  ) : (
                    <Button size="sm" onClick={() => setEditMode(true)} data-testid="embedded-edit-btn">
                      {t('common.edit')}
                    </Button>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Contact & Organization */}
        <div className="grid grid-cols-2 gap-3">
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardHeader className="p-3 pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Phone className="w-4 h-4" />
                {t('profile.contact')}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-3 pt-0">
              {editMode && isOwnProfile ? (
                <Input
                  value={formData.phone}
                  onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                  className="bg-[#0A0A0F] border-[#1E293B] text-sm"
                  placeholder="+52 555 123 4567"
                />
              ) : (
                <p className="text-sm text-muted-foreground">{profile?.phone || t('profile.notSpecified')}</p>
              )}
            </CardContent>
          </Card>

          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardHeader className="p-3 pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Building2 className="w-4 h-4" />
                {t('profile.condominium')}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-3 pt-0">
              <p className="text-sm">{profile?.condominium_name || t('profile.notSpecified')}</p>
            </CardContent>
          </Card>
        </div>

        {/* Description */}
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardHeader className="p-3 pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <FileText className="w-4 h-4" />
              {isOwnProfile ? t('profile.publicDescription') : t('profile.about', 'About')}
            </CardTitle>
            {isOwnProfile && !editMode && (
              <CardDescription className="text-xs">
                {t('profile.publicDescriptionHint')}
              </CardDescription>
            )}
          </CardHeader>
          <CardContent className="p-3 pt-0">
            {editMode && isOwnProfile ? (
              <Textarea
                value={formData.public_description}
                onChange={(e) => setFormData(prev => ({ ...prev, public_description: e.target.value }))}
                className="bg-[#0A0A0F] border-[#1E293B] min-h-[80px] text-sm"
                placeholder={t('profile.publicDescriptionPlaceholder', 'Write a brief description about yourself...')}
              />
            ) : (
              <p className="text-sm text-muted-foreground">
                {profile?.public_description || t('profile.noDescription', 'No description')}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Push Notifications - Only for security roles */}
        {isOwnProfile && profile?.roles?.some(role => ['Guarda', 'Guardia', 'Administrador', 'Supervisor', 'SuperAdmin'].includes(role)) && (
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardHeader className="p-3 pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Shield className="w-4 h-4" />
                {t('security.panicAlerts')}
              </CardTitle>
              <CardDescription className="text-xs">
                {t('profile.alertNotificationsHint', 'Receive panic alerts in real time')}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-3 pt-0">
              <PushNotificationToggle />
            </CardContent>
          </Card>
        )}

        {/* Language Selector - Available for all users on their own profile */}
        {isOwnProfile && (
          <LanguageSelector />
        )}

        {/* Photo Modal */}
        <Dialog open={photoModalOpen} onOpenChange={setPhotoModalOpen}>
          <DialogContent className="max-w-2xl bg-black/95 border-[#1E293B] p-0 overflow-hidden">
            <div className="relative flex items-center justify-center min-h-[300px] max-h-[70vh]">
              <Button
                variant="ghost"
                size="icon"
                className="absolute top-2 right-2 z-10 bg-black/50 hover:bg-black/70 rounded-full"
                onClick={() => setPhotoModalOpen(false)}
              >
                <X className="w-5 h-5 text-white" />
              </Button>
              {currentPhoto && (
                <img src={currentPhoto} alt={profile?.full_name} className="max-w-full max-h-[70vh] object-contain" />
              )}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                <h3 className="text-white text-lg font-semibold">{profile?.full_name}</h3>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Logout Section - Mobile friendly */}
        {isOwnProfile && (
          <Card className="bg-[#0F111A] border-[#1E293B] mt-4">
            <CardContent className="p-3">
              <Button
                variant="outline"
                className="w-full border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300"
                onClick={() => setShowLogoutConfirm(true)}
                data-testid="logout-btn"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Cerrar Sesión
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Logout Confirmation Dialog */}
        <Dialog open={showLogoutConfirm} onOpenChange={setShowLogoutConfirm}>
          <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-sm">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <LogOut className="w-5 h-5 text-red-400" />
                Cerrar Sesión
              </DialogTitle>
              <DialogDescription>
                ¿Estás seguro de que deseas cerrar sesión?
              </DialogDescription>
            </DialogHeader>
            <DialogFooter className="flex-col sm:flex-row gap-2 mt-4">
              <Button variant="outline" onClick={() => setShowLogoutConfirm(false)}>
                Cancelar
              </Button>
              <Button 
                variant="destructive"
                onClick={handleLogout}
                className="bg-red-600 hover:bg-red-700"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Cerrar Sesión
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </ScrollArea>
  );
};

export default EmbeddedProfile;
