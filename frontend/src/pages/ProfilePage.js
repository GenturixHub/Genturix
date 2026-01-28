/**
 * GENTURIX - User Profile Module
 * Basic profile for all roles with role-specific public info
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import api from '../services/api';
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
  XCircle
} from 'lucide-react';

// Role configuration for display
const ROLE_CONFIG = {
  'Administrador': { icon: Shield, color: 'bg-purple-500/10 text-purple-400', label: 'Administrador' },
  'Residente': { icon: Home, color: 'bg-blue-500/10 text-blue-400', label: 'Residente' },
  'Guarda': { icon: Shield, color: 'bg-green-500/10 text-green-400', label: 'Guardia' },
  'HR': { icon: Briefcase, color: 'bg-orange-500/10 text-orange-400', label: 'Recursos Humanos' },
  'Supervisor': { icon: UserCheck, color: 'bg-purple-500/10 text-purple-400', label: 'Supervisor' },
  'Estudiante': { icon: GraduationCap, color: 'bg-cyan-500/10 text-cyan-400', label: 'Estudiante' },
};

const ProfilePage = () => {
  const { user, refreshUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState({
    full_name: '',
    phone: '',
    profile_photo: ''
  });

  // Fetch profile data
  useEffect(() => {
    const fetchProfile = async () => {
      setIsLoading(true);
      try {
        const data = await api.get('/profile');
        setProfile(data);
        setFormData({
          full_name: data.full_name || '',
          phone: data.phone || '',
          profile_photo: data.profile_photo || ''
        });
      } catch (err) {
        console.error('Error fetching profile:', err);
        // Use local user data as fallback
        if (user) {
          setProfile(user);
          setFormData({
            full_name: user.full_name || '',
            phone: user.phone || '',
            profile_photo: user.profile_photo || ''
          });
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchProfile();
  }, [user]);

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

    // Convert to base64 for simple storage
    const reader = new FileReader();
    reader.onloadend = () => {
      setFormData(prev => ({ ...prev, profile_photo: reader.result }));
    };
    reader.readAsDataURL(file);
  };

  const getRoleSpecificInfo = () => {
    const roleData = profile?.role_data || {};
    const roles = profile?.roles || [];
    const primaryRole = roles[0];

    switch (primaryRole) {
      case 'Residente':
        return (
          <Card className="bg-[#0F111A] border-[#1E293B]">
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
          <Card className="bg-[#0F111A] border-[#1E293B]">
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
          <Card className="bg-[#0F111A] border-[#1E293B]">
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
          <Card className="bg-[#0F111A] border-[#1E293B]">
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
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-purple-400" />
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
      <DashboardLayout title="Mi Perfil">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  const primaryRole = profile?.roles?.[0] || 'Usuario';
  const roleConfig = ROLE_CONFIG[primaryRole] || { icon: User, color: 'bg-gray-500/10 text-gray-400', label: primaryRole };
  const RoleIcon = roleConfig.icon;

  return (
    <DashboardLayout title="Mi Perfil">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Success/Error Messages */}
        {success && (
          <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 flex items-center gap-2">
            <CheckCircle className="w-4 h-4" />
            {success}
          </div>
        )}
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-2">
            <XCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {/* Profile Header */}
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row items-center gap-6">
              {/* Avatar */}
              <div className="relative">
                <Avatar className="w-24 h-24 border-4 border-[#1E293B]">
                  <AvatarImage src={formData.profile_photo || profile?.profile_photo} />
                  <AvatarFallback className="bg-primary/20 text-primary text-2xl">
                    {profile?.full_name?.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                {editMode && (
                  <label className="absolute bottom-0 right-0 p-2 bg-primary rounded-full cursor-pointer hover:bg-primary/80 transition-colors">
                    <Camera className="w-4 h-4 text-white" />
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handlePhotoUpload}
                    />
                  </label>
                )}
              </div>

              {/* User Info */}
              <div className="flex-1 text-center md:text-left">
                {editMode ? (
                  <Input
                    value={formData.full_name}
                    onChange={(e) => setFormData(prev => ({ ...prev, full_name: e.target.value }))}
                    className="bg-[#0A0A0F] border-[#1E293B] text-xl font-bold mb-2"
                    placeholder="Nombre completo"
                  />
                ) : (
                  <h2 className="text-2xl font-bold">{profile?.full_name}</h2>
                )}
                <p className="text-muted-foreground">{profile?.email}</p>
                <div className="flex items-center justify-center md:justify-start gap-2 mt-2">
                  <Badge className={roleConfig.color}>
                    <RoleIcon className="w-3 h-3 mr-1" />
                    {roleConfig.label}
                  </Badge>
                </div>
              </div>

              {/* Edit Button */}
              <div className="flex gap-2">
                {editMode ? (
                  <>
                    <Button variant="outline" onClick={() => setEditMode(false)}>
                      Cancelar
                    </Button>
                    <Button onClick={handleSave} disabled={isSaving}>
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
            </div>
          </CardContent>
        </Card>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Contact Information */}
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardHeader>
              <CardTitle className="text-base">Información de Contacto</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
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
              <div className="space-y-2">
                <Label className="flex items-center gap-2 text-muted-foreground">
                  <Phone className="w-4 h-4" />
                  Teléfono
                </Label>
                {editMode ? (
                  <Input
                    value={formData.phone}
                    onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                    className="bg-[#0A0A0F] border-[#1E293B]"
                    placeholder="+52 555 123 4567"
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
          <Card className="bg-[#0F111A] border-[#1E293B]">
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
            </CardContent>
          </Card>
        </div>

        {/* Role-specific Information */}
        {getRoleSpecificInfo()}
      </div>
    </DashboardLayout>
  );
};

export default ProfilePage;
