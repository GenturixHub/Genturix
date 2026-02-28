/**
 * GENTURIX - Unified User Profile Module
 * Supports viewing own profile (editable) and viewing other users' profiles (read-only)
 * Multi-tenant: Users can only view profiles within their condominium
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useParams, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog,
  DialogContent,
} from '../components/ui/dialog';
import api from '../services/api';
import { profileKeys } from '../hooks/queries/useProfileQueries';
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
  ArrowLeft,
  FileText,
  X,
  ZoomIn,
  LogOut
} from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog';
import ChangePasswordForm from '../components/ChangePasswordForm';
import { PushNotificationToggle } from '../components/PushNotificationBanner';

// Role configuration for display
const ROLE_CONFIG = {
  'Administrador': { icon: Shield, color: 'bg-cyan-500/10 text-cyan-400', label: 'Administrador' },
  'Residente': { icon: Home, color: 'bg-blue-500/10 text-blue-400', label: 'Residente' },
  'Guarda': { icon: Shield, color: 'bg-green-500/10 text-green-400', label: 'Guardia' },
  'HR': { icon: Briefcase, color: 'bg-orange-500/10 text-orange-400', label: 'Recursos Humanos' },
  'Supervisor': { icon: UserCheck, color: 'bg-cyan-500/10 text-cyan-400', label: 'Supervisor' },
  'Estudiante': { icon: GraduationCap, color: 'bg-cyan-500/10 text-cyan-400', label: 'Estudiante' },
  'SuperAdmin': { icon: Shield, color: 'bg-red-500/10 text-red-400', label: 'Super Admin' },
};

const ProfilePage = () => {
  const { user, refreshUser, logout } = useAuth();
  const { userId } = useParams(); // If userId is present, we're viewing someone else's profile
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

  // Determine if viewing own profile or another user's profile
  const isOwnProfile = !userId || userId === user?.id;
  const pageTitle = isOwnProfile ? 'Mi Perfil' : 'Perfil de Usuario';

  // Get the current photo to display (considering edit mode)
  const currentPhoto = editMode ? formData.profile_photo : profile?.profile_photo;

  // Fetch profile data
  useEffect(() => {
    const fetchProfile = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        let data;
        
        if (isOwnProfile) {
          // Fetch own profile (full data)
          data = await api.get('/profile');
          setFormData({
            full_name: data.full_name || '',
            phone: data.phone || '',
            profile_photo: data.profile_photo || '',
            public_description: data.public_description || ''
          });
        } else {
          // Fetch public profile (limited data)
          data = await api.getPublicProfile(userId);
        }
        
        setProfile(data);
      } catch (err) {
        console.error('Error fetching profile:', err);
        if (err.status === 403) {
          setError('No tienes permiso para ver este perfil');
        } else if (err.status === 404) {
          setError('Usuario no encontrado');
        } else {
          setError(err.message || 'Error al cargar perfil');
        }
        
        // Use local user data as fallback only for own profile
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
      // Refresh user data
      if (refreshUser) {
        await refreshUser();
      }
      // Update local profile state
      setProfile(prev => ({ ...prev, ...formData }));
    } catch (err) {
      setError(err.message || 'Error al actualizar perfil');
    } finally {
      setIsSaving(false);
    }
  };

  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file size (max 2MB for base64)
    if (file.size > 2 * 1024 * 1024) {
      setError('La imagen no puede ser mayor a 2MB');
      return;
    }

    // Convert to base64 for simple storage
    const reader = new FileReader();
    reader.onloadend = () => {
      setFormData(prev => ({ ...prev, profile_photo: reader.result }));
    };
    reader.readAsDataURL(file);
  };

  const getRoleSpecificInfo = () => {
    // Only show role-specific info for own profile (where we have full data)
    if (!isOwnProfile) return null;
    
    const roleData = profile?.role_data || {};
    const roles = profile?.roles || [];
    const primaryRole = roles[0];

    switch (primaryRole) {
      case 'Residente':
        return (
          <Card className="bg-[#0F111A] border-[#1E293B] rounded-2xl">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Home className="w-4 h-4 text-blue-400" />
                Información de Residencia
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Apartamento / Casa</span>
                <span className="font-medium">{roleData.apartment_number || 'No especificado'}</span>
              </div>
              {roleData.tower_block && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Torre / Bloque</span>
                  <span className="font-medium">{roleData.tower_block}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">Tipo</span>
                <Badge variant="outline">
                  {roleData.resident_type === 'owner' ? 'Propietario' : 'Arrendatario'}
                </Badge>
              </div>
            </CardContent>
          </Card>
        );

      case 'Guarda':
        return (
          <Card className="bg-[#0F111A] border-[#1E293B] rounded-2xl">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Shield className="w-4 h-4 text-green-400" />
                Información de Guardia
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Número de Placa</span>
                <Badge className="bg-green-500/10 text-green-400">
                  {roleData.badge_number || 'No asignado'}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Ubicación Principal</span>
                <span className="font-medium">{roleData.main_location || 'No asignado'}</span>
              </div>
              {roleData.initial_shift && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Turno</span>
                  <span className="font-medium capitalize">{roleData.initial_shift}</span>
                </div>
              )}
            </CardContent>
          </Card>
        );

      case 'HR':
        return (
          <Card className="bg-[#0F111A] border-[#1E293B] rounded-2xl">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-orange-400" />
                Información de RRHH
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Departamento</span>
                <span className="font-medium">{roleData.department || 'Recursos Humanos'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Nivel de Permisos</span>
                <Badge variant="outline">
                  {roleData.permission_level === 'HR_SUPERVISOR' ? 'HR + Supervisor' : 'Solo HR'}
                </Badge>
              </div>
            </CardContent>
          </Card>
        );

      case 'Estudiante':
        return (
          <Card className="bg-[#0F111A] border-[#1E293B] rounded-2xl">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <GraduationCap className="w-4 h-4 text-cyan-400" />
                Información Académica
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Plan</span>
                <Badge className="bg-cyan-500/10 text-cyan-400">
                  {roleData.subscription_plan === 'pro' ? 'Pro' : 'Básico'}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Estado</span>
                <Badge variant="outline" className={roleData.subscription_status === 'active' ? 'border-green-500 text-green-400' : 'border-yellow-500 text-yellow-400'}>
                  {roleData.subscription_status === 'active' ? 'Activo' : 'Prueba'}
                </Badge>
              </div>
            </CardContent>
          </Card>
        );

      case 'Supervisor':
        return (
          <Card className="bg-[#0F111A] border-[#1E293B] rounded-2xl">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-cyan-400" />
                Información de Supervisor
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Área Supervisada</span>
                <span className="font-medium">{roleData.supervised_area || 'General'}</span>
              </div>
            </CardContent>
          </Card>
        );

      default:
        return null;
    }
  };

  if (isLoading) {
    return (
      <DashboardLayout title={pageTitle}>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  // Error state for viewing other profiles
  if (!isOwnProfile && error) {
    return (
      <DashboardLayout title={pageTitle}>
        <div className="w-full space-y-4 lg:max-w-4xl lg:mx-auto">
          <Button 
            variant="ghost" 
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 -ml-2"
            data-testid="back-btn"
          >
            <ArrowLeft className="w-4 h-4" />
            Volver
          </Button>
          <Card className="bg-[#0F111A] border-[#1E293B] rounded-2xl">
            <CardContent className="p-8 text-center">
              <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Error</h3>
              <p className="text-muted-foreground">{error}</p>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  const primaryRole = profile?.roles?.[0] || 'Usuario';
  const roleConfig = ROLE_CONFIG[primaryRole] || { icon: User, color: 'bg-gray-500/10 text-gray-400', label: primaryRole };
  const RoleIcon = roleConfig.icon;

  // Determine the correct dashboard URL based on user role
  const getDashboardUrl = () => {
    if (!profile?.roles?.length) return '/';
    const role = profile.roles[0];
    switch (role) {
      case 'SuperAdmin': return '/super-admin';
      case 'Administrador': return '/admin/dashboard';
      case 'Guardia': return '/guard';
      case 'Residente': return '/resident';
      case 'RRHH': return '/hr';
      case 'Supervisor': return '/hr';
      case 'Estudiante': return '/student';
      default: return '/';
    }
  };

  return (
    <DashboardLayout title={pageTitle}>
      {/* Mobile-first: full width, no max-width constraints */}
      <div className="w-full space-y-4 lg:max-w-4xl lg:mx-auto">
        {/* Back button - Always show with appropriate destination */}
        <div className="flex items-center justify-between">
          <Button 
            variant="ghost" 
            onClick={() => isOwnProfile ? navigate(getDashboardUrl()) : navigate(-1)}
            className="flex items-center gap-2 -ml-2"
            data-testid="back-btn"
          >
            <ArrowLeft className="w-4 h-4" />
            {isOwnProfile ? 'Volver' : 'Volver'}
          </Button>
        </div>

        {/* Success/Error Messages */}
        {success && (
          <div className="p-3 rounded-2xl bg-green-500/10 border border-green-500/20 text-green-400 flex items-center gap-2 text-sm">
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
            {success}
          </div>
        )}
        {error && isOwnProfile && (
          <div className="p-3 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-2 text-sm">
            <XCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Profile Header - Full width card */}
        <Card className="bg-[#0F111A] border-[#1E293B] rounded-2xl overflow-hidden">
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row items-center gap-6">
              {/* Avatar - Clickable to expand */}
              <div className="relative group">
                <div 
                  className={`relative ${currentPhoto ? 'cursor-pointer' : ''}`}
                  onClick={() => currentPhoto && setPhotoModalOpen(true)}
                  data-testid="profile-avatar-container"
                >
                  <Avatar className="w-24 h-24 border-4 border-[#1E293B] transition-transform group-hover:scale-105">
                    <AvatarImage src={currentPhoto} />
                    <AvatarFallback className="bg-primary/20 text-primary text-2xl">
                      {profile?.full_name?.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  {/* Zoom indicator on hover (only if photo exists) */}
                  {currentPhoto && !editMode && (
                    <div className="absolute inset-0 bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <ZoomIn className="w-6 h-6 text-white" />
                    </div>
                  )}
                </div>
                {editMode && isOwnProfile && (
                  <label className="absolute bottom-0 right-0 p-2 bg-primary rounded-full cursor-pointer hover:bg-primary/80 transition-colors z-10">
                    <Camera className="w-4 h-4 text-white" />
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handlePhotoUpload}
                      data-testid="photo-upload-input"
                    />
                  </label>
                )}
              </div>

              {/* User Info */}
              <div className="flex-1 text-center md:text-left">
                {editMode && isOwnProfile ? (
                  <Input
                    value={formData.full_name}
                    onChange={(e) => setFormData(prev => ({ ...prev, full_name: e.target.value }))}
                    className="bg-[#0A0A0F] border-[#1E293B] text-xl font-bold mb-2"
                    placeholder="Nombre completo"
                    data-testid="name-input"
                  />
                ) : (
                  <h2 className="text-2xl font-bold" data-testid="profile-name">{profile?.full_name}</h2>
                )}
                {isOwnProfile && <p className="text-muted-foreground">{profile?.email}</p>}
                <div className="flex items-center justify-center md:justify-start gap-2 mt-2 flex-wrap">
                  {profile?.roles?.map((role, index) => {
                    const config = ROLE_CONFIG[role] || { icon: User, color: 'bg-gray-500/10 text-gray-400', label: role };
                    const Icon = config.icon;
                    return (
                      <Badge key={index} className={config.color}>
                        <Icon className="w-3 h-3 mr-1" />
                        {config.label}
                      </Badge>
                    );
                  })}
                </div>
              </div>

              {/* Edit Button (only for own profile) */}
              {isOwnProfile && (
                <div className="flex gap-2">
                  {editMode ? (
                    <>
                      <Button variant="outline" onClick={() => setEditMode(false)} data-testid="cancel-btn">
                        Cancelar
                      </Button>
                      <Button onClick={handleSave} disabled={isSaving} data-testid="save-btn">
                        {isSaving ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <>
                            <Save className="w-4 h-4 mr-2" />
                            Guardar
                          </>
                        )}
                      </Button>
                    </>
                  ) : (
                    <Button onClick={() => setEditMode(true)} data-testid="edit-profile-btn">
                      Editar Perfil
                    </Button>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Contact Information */}
          <Card className="bg-[#0F111A] border-[#1E293B] rounded-2xl">
            <CardHeader>
              <CardTitle className="text-base">Información de Contacto</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {isOwnProfile && (
                <div className="space-y-2">
                  <Label className="flex items-center gap-2 text-muted-foreground">
                    <Mail className="w-4 h-4" />
                    Email
                  </Label>
                  <Input
                    value={profile?.email}
                    disabled
                    className="bg-[#0A0A0F] border-[#1E293B]"
                  />
                </div>
              )}
              <div className="space-y-2">
                <Label className="flex items-center gap-2 text-muted-foreground">
                  <Phone className="w-4 h-4" />
                  Teléfono
                </Label>
                {editMode && isOwnProfile ? (
                  <Input
                    value={formData.phone}
                    onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                    className="bg-[#0A0A0F] border-[#1E293B]"
                    placeholder="+52 555 123 4567"
                    data-testid="phone-input"
                  />
                ) : (
                  <Input
                    value={profile?.phone || 'No especificado'}
                    disabled
                    className="bg-[#0A0A0F] border-[#1E293B]"
                  />
                )}
              </div>
            </CardContent>
          </Card>

          {/* Organization Info */}
          <Card className="bg-[#0F111A] border-[#1E293B] rounded-2xl">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Building2 className="w-4 h-4" />
                Organización
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Condominio</span>
                <span className="font-medium">{profile?.condominium_name || 'No asignado'}</span>
              </div>
              {isOwnProfile && (
                <>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Estado</span>
                    <Badge className={profile?.is_active !== false ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}>
                      {profile?.is_active !== false ? 'Activo' : 'Inactivo'}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Miembro desde</span>
                    <span className="text-sm">
                      {profile?.created_at ? new Date(profile.created_at).toLocaleDateString('es-MX', { year: 'numeric', month: 'long' }) : 'N/A'}
                    </span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Public Description */}
        <Card className="bg-[#0F111A] border-[#1E293B] rounded-2xl">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="w-4 h-4" />
              {isOwnProfile ? 'Descripción Pública' : 'Acerca de'}
            </CardTitle>
            {isOwnProfile && !editMode && (
              <CardDescription>
                Esta descripción será visible para otros usuarios de tu condominio
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            {editMode && isOwnProfile ? (
              <Textarea
                value={formData.public_description}
                onChange={(e) => setFormData(prev => ({ ...prev, public_description: e.target.value }))}
                className="bg-[#0A0A0F] border-[#1E293B] min-h-[100px]"
                placeholder="Escribe una breve descripción sobre ti..."
                data-testid="description-input"
              />
            ) : (
              <p className="text-muted-foreground">
                {profile?.public_description || 'Sin descripción'}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Role-specific Information (only for own profile) */}
        {getRoleSpecificInfo()}

        {/* Push Notifications Toggle (only for own profile) */}
        {isOwnProfile && (
          <PushNotificationToggle />
        )}

        {/* Security Section - Change Password (only for own profile) */}
        {isOwnProfile && (
          <ChangePasswordForm 
            onSuccess={() => {
              setSuccess('Contraseña actualizada exitosamente');
              setTimeout(() => setSuccess(null), 3000);
            }}
          />
        )}

        {/* Photo Lightbox Modal */}
        <Dialog open={photoModalOpen} onOpenChange={setPhotoModalOpen}>
          <DialogContent className="max-w-3xl bg-black/95 border-[#1E293B] p-0 overflow-hidden">
            <div className="relative flex items-center justify-center min-h-[400px] max-h-[80vh]">
              {/* Close button */}
              <Button
                variant="ghost"
                size="icon"
                className="absolute top-2 right-2 z-10 bg-black/50 hover:bg-black/70 rounded-full"
                onClick={() => setPhotoModalOpen(false)}
                data-testid="photo-modal-close-btn"
              >
                <X className="w-5 h-5 text-white" />
              </Button>
              
              {/* Profile photo full size */}
              {currentPhoto ? (
                <img 
                  src={currentPhoto} 
                  alt={profile?.full_name || 'Foto de perfil'}
                  className="max-w-full max-h-[80vh] object-contain"
                  data-testid="photo-modal-image"
                />
              ) : (
                <div className="w-64 h-64 bg-primary/20 rounded-full flex items-center justify-center">
                  <span className="text-6xl text-primary font-bold">
                    {profile?.full_name?.charAt(0).toUpperCase()}
                  </span>
                </div>
              )}
              
              {/* User info overlay at bottom */}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                <h3 className="text-white text-xl font-semibold">{profile?.full_name}</h3>
                <div className="flex items-center gap-2 mt-1">
                  {profile?.roles?.map((role, index) => {
                    const config = ROLE_CONFIG[role] || { color: 'bg-gray-500/10 text-gray-400', label: role };
                    return (
                      <Badge key={index} className={config.color}>
                        {config.label}
                      </Badge>
                    );
                  })}
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* Logout Section - Mobile visible, always show for own profile */}
        {isOwnProfile && (
          <Card className="bg-[#0F111A] border-[#1E293B] lg:hidden">
            <CardContent className="p-4">
              <Button
                variant="destructive"
                className="w-full flex items-center justify-center gap-2"
                onClick={() => setShowLogoutConfirm(true)}
                data-testid="mobile-logout-btn"
              >
                <LogOut className="w-4 h-4" />
                Cerrar Sesión
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Logout Confirmation Dialog */}
        <AlertDialog open={showLogoutConfirm} onOpenChange={setShowLogoutConfirm}>
          <AlertDialogContent className="bg-[#0F111A] border-[#1E293B]">
            <AlertDialogHeader>
              <AlertDialogTitle>¿Cerrar sesión?</AlertDialogTitle>
              <AlertDialogDescription>
                ¿Estás seguro de que deseas cerrar tu sesión? Tendrás que volver a iniciar sesión para acceder a tu cuenta.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="bg-[#1E293B] border-[#2D3B4F] hover:bg-[#2D3B4F]">
                Cancelar
              </AlertDialogCancel>
              <AlertDialogAction
                className="bg-red-600 hover:bg-red-700"
                onClick={() => {
                  logout();
                  navigate('/login');
                }}
                data-testid="confirm-logout-btn"
              >
                Cerrar Sesión
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </DashboardLayout>
  );
};

export default ProfilePage;
