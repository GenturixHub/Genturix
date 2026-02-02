/**
 * GENTURIX - Profile Directory Component
 * Shows all users in the same condominium grouped by role
 * Can be embedded in any role's UI (Guard, Resident, Admin, HR)
 * 
 * When embedded=true, clicking a profile shows it in a modal (no navigation)
 * This prevents users from getting stuck in isolated profile pages
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from './ui/dialog';
import api from '../services/api';
import {
  Users,
  Search,
  Shield,
  Home,
  Briefcase,
  UserCheck,
  GraduationCap,
  User,
  Phone,
  Mail,
  Loader2,
  X,
  ZoomIn,
  ChevronRight,
  Building2,
  ArrowLeft,
  MapPin,
  Calendar
} from 'lucide-react';

// Role configuration
const ROLE_CONFIG = {
  'Administrador': { icon: Shield, color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30', label: 'Administradores' },
  'Supervisor': { icon: UserCheck, color: 'bg-teal-500/10 text-teal-400 border-teal-500/30', label: 'Supervisores' },
  'HR': { icon: Briefcase, color: 'bg-orange-500/10 text-orange-400 border-orange-500/30', label: 'Recursos Humanos' },
  'Guarda': { icon: Shield, color: 'bg-green-500/10 text-green-400 border-green-500/30', label: 'Guardias' },
  'Residente': { icon: Home, color: 'bg-blue-500/10 text-blue-400 border-blue-500/30', label: 'Residentes' },
  'Estudiante': { icon: GraduationCap, color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30', label: 'Estudiantes' },
};

const ProfileDirectory = ({ onViewProfile, embedded = false, maxHeight = "100%" }) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [directory, setDirectory] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [photoModalOpen, setPhotoModalOpen] = useState(false);
  
  // NEW: State for embedded profile modal
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [profileModalUser, setProfileModalUser] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);

  // Refetch when user profile_photo changes (after profile update)
  const userPhotoKey = user?.profile_photo || 'no-photo';

  useEffect(() => {
    const fetchDirectory = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.getCondominiumDirectory();
        setDirectory(data);
      } catch (err) {
        console.error('Error fetching directory:', err);
        setError(err.message || 'Error al cargar directorio');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDirectory();
  }, [userPhotoKey]); // Refetch when user's photo changes

  const handleViewProfile = async (userId, userBasicInfo) => {
    if (onViewProfile) {
      // If parent provides handler, use it
      onViewProfile(userId);
    } else if (embedded) {
      // EMBEDDED MODE: Show profile in modal (no navigation)
      setProfileModalUser(userBasicInfo); // Show basic info immediately
      setProfileModalOpen(true);
      
      // Optionally fetch full profile data
      try {
        setLoadingProfile(true);
        const fullProfile = await api.getPublicProfile(userId);
        setProfileModalUser(prev => ({ ...prev, ...fullProfile }));
      } catch (err) {
        console.error('Error loading full profile:', err);
        // Keep showing basic info even if full fetch fails
      } finally {
        setLoadingProfile(false);
      }
    } else {
      // Non-embedded mode: navigate to profile page
      navigate(`/profile/${userId}`);
    }
  };

  const closeProfileModal = () => {
    setProfileModalOpen(false);
    setProfileModalUser(null);
  };

  const handlePhotoClick = (user, e) => {
    e.stopPropagation();
    if (user.profile_photo) {
      setSelectedUser(user);
      setPhotoModalOpen(true);
    }
  };

  // Filter users based on search
  const filterUsers = (users) => {
    if (!searchQuery.trim()) return users;
    const query = searchQuery.toLowerCase();
    return users.filter(user => 
      user.full_name?.toLowerCase().includes(query) ||
      user.email?.toLowerCase().includes(query) ||
      user.phone?.includes(query)
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardContent className="p-6 text-center">
          <p className="text-red-400">{error}</p>
        </CardContent>
      </Card>
    );
  }

  const hasUsers = directory?.total_count > 0;

  return (
    <div className={`flex flex-col ${embedded ? '' : 'space-y-4'}`} style={{ height: maxHeight }}>
      {/* Header */}
      <div className={`flex-shrink-0 ${embedded ? 'p-3 border-b border-[#1E293B]' : ''}`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold">
              Personas
              {directory?.condominium_name && (
                <span className="text-sm font-normal text-muted-foreground ml-2">
                  {directory.condominium_name}
                </span>
              )}
            </h2>
          </div>
          {hasUsers && (
            <Badge variant="outline" className="text-xs">
              {directory.total_count} usuarios
            </Badge>
          )}
        </div>
        
        {/* Search */}
        {hasUsers && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por nombre, email o teléfono..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 bg-[#0A0A0F] border-[#1E293B]"
              data-testid="directory-search"
            />
          </div>
        )}
      </div>

      {/* Directory Content */}
      <ScrollArea className="flex-1">
        <div className={`space-y-4 ${embedded ? 'p-3' : ''}`}>
          {!hasUsers ? (
            <Card className="bg-[#0F111A] border-[#1E293B]">
              <CardContent className="p-6 text-center">
                <Users className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
                <p className="text-muted-foreground">No hay usuarios en este condominio</p>
              </CardContent>
            </Card>
          ) : (
            Object.entries(directory.grouped_by_role).map(([role, users]) => {
              const filteredUsers = filterUsers(users);
              if (filteredUsers.length === 0) return null;
              
              const config = ROLE_CONFIG[role] || { icon: User, color: 'bg-gray-500/10 text-gray-400 border-gray-500/30', label: role };
              const RoleIcon = config.icon;
              
              return (
                <div key={role} className="space-y-2">
                  {/* Role Header */}
                  <div className="flex items-center gap-2 px-1">
                    <RoleIcon className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm font-medium text-muted-foreground">{config.label}</span>
                    <Badge variant="outline" className="text-xs ml-auto">
                      {filteredUsers.length}
                    </Badge>
                  </div>
                  
                  {/* Users Grid */}
                  <div className="grid gap-2">
                    {filteredUsers.map((dirUser) => (
                      <Card 
                        key={dirUser.id}
                        className="bg-[#0F111A] border-[#1E293B] hover:border-primary/50 transition-colors cursor-pointer group"
                        onClick={() => handleViewProfile(dirUser.id, dirUser)}
                        data-testid={`user-card-${dirUser.id}`}
                      >
                        <CardContent className="p-3">
                          <div className="flex items-center gap-3">
                            {/* Avatar */}
                            <div 
                              className="relative cursor-pointer"
                              onClick={(e) => handlePhotoClick(dirUser, e)}
                            >
                              <Avatar className="w-12 h-12 border-2 border-[#1E293B] group-hover:border-primary/50 transition-colors">
                                <AvatarImage src={dirUser.profile_photo} />
                                <AvatarFallback className={`${config.color} text-sm font-bold`}>
                                  {dirUser.full_name?.charAt(0).toUpperCase()}
                                </AvatarFallback>
                              </Avatar>
                              {dirUser.profile_photo && (
                                <div className="absolute inset-0 bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                  <ZoomIn className="w-4 h-4 text-white" />
                                </div>
                              )}
                            </div>
                            
                            {/* Info */}
                            <div className="flex-1 min-w-0">
                              <h3 className="font-medium truncate">{dirUser.full_name}</h3>
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <Badge className={`${config.color} text-[10px] px-1.5 py-0`}>
                                  {role}
                                </Badge>
                                {dirUser.phone && (
                                  <span className="flex items-center gap-1">
                                    <Phone className="w-3 h-3" />
                                    {dirUser.phone}
                                  </span>
                                )}
                              </div>
                              {dirUser.public_description && (
                                <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                                  {dirUser.public_description}
                                </p>
                              )}
                            </div>
                            
                            {/* Arrow */}
                            <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </ScrollArea>

      {/* Photo Lightbox Modal */}
      <Dialog open={photoModalOpen} onOpenChange={setPhotoModalOpen}>
        <DialogContent className="max-w-3xl bg-black/95 border-[#1E293B] p-0 overflow-hidden">
          <div className="relative flex items-center justify-center min-h-[400px] max-h-[80vh]">
            <Button
              variant="ghost"
              size="icon"
              className="absolute top-2 right-2 z-10 bg-black/50 hover:bg-black/70 rounded-full"
              onClick={() => setPhotoModalOpen(false)}
              data-testid="directory-photo-modal-close"
            >
              <X className="w-5 h-5 text-white" />
            </Button>
            
            {selectedUser?.profile_photo && (
              <img 
                src={selectedUser.profile_photo} 
                alt={selectedUser.full_name}
                className="max-w-full max-h-[80vh] object-contain"
              />
            )}
            
            {/* User info overlay */}
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
              <h3 className="text-white text-xl font-semibold">{selectedUser?.full_name}</h3>
              <div className="flex items-center gap-2 mt-1">
                {selectedUser?.roles?.map((role, index) => {
                  const config = ROLE_CONFIG[role] || { color: 'bg-gray-500/10 text-gray-400', label: role };
                  return (
                    <Badge key={index} className={config.color}>
                      {role}
                    </Badge>
                  );
                })}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
      
      {/* Embedded Profile Modal - Shows profile without navigation */}
      <Dialog open={profileModalOpen} onOpenChange={closeProfileModal}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md max-h-[85vh] overflow-y-auto p-0">
          <DialogHeader className="p-4 border-b border-[#1E293B] sticky top-0 bg-[#0F111A] z-10">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={closeProfileModal}
                data-testid="profile-modal-back"
              >
                <ArrowLeft className="w-4 h-4" />
              </Button>
              <div>
                <DialogTitle className="text-base">Perfil</DialogTitle>
                <DialogDescription className="text-xs">
                  Información de contacto
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          
          {profileModalUser && (
            <div className="p-4 space-y-4">
              {/* Profile Header */}
              <div className="flex flex-col items-center text-center">
                <Avatar className="w-24 h-24 border-4 border-[#1E293B]">
                  <AvatarImage src={profileModalUser.profile_photo} />
                  <AvatarFallback className="text-2xl font-bold bg-primary/10 text-primary">
                    {profileModalUser.full_name?.charAt(0).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <h2 className="text-xl font-semibold mt-3">{profileModalUser.full_name}</h2>
                
                {/* Roles */}
                <div className="flex flex-wrap justify-center gap-2 mt-2">
                  {(profileModalUser.roles || [profileModalUser.role]).filter(Boolean).map((role, index) => {
                    const config = ROLE_CONFIG[role] || { color: 'bg-gray-500/10 text-gray-400 border-gray-500/30', label: role };
                    return (
                      <Badge key={index} className={config.color}>
                        {role}
                      </Badge>
                    );
                  })}
                </div>
              </div>
              
              {/* Contact Info */}
              <Card className="bg-[#0A0A0F] border-[#1E293B]">
                <CardContent className="p-4 space-y-3">
                  {profileModalUser.phone && (
                    <a 
                      href={`tel:${profileModalUser.phone}`}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-[#1E293B]/50 transition-colors"
                    >
                      <div className="w-10 h-10 rounded-full bg-green-500/10 flex items-center justify-center">
                        <Phone className="w-5 h-5 text-green-400" />
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Teléfono</p>
                        <p className="font-medium">{profileModalUser.phone}</p>
                      </div>
                    </a>
                  )}
                  
                  {profileModalUser.email && (
                    <a 
                      href={`mailto:${profileModalUser.email}`}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-[#1E293B]/50 transition-colors"
                    >
                      <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center">
                        <Mail className="w-5 h-5 text-blue-400" />
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Email</p>
                        <p className="font-medium text-sm truncate">{profileModalUser.email}</p>
                      </div>
                    </a>
                  )}
                  
                  {profileModalUser.unit_number && (
                    <div className="flex items-center gap-3 p-2">
                      <div className="w-10 h-10 rounded-full bg-cyan-500/10 flex items-center justify-center">
                        <MapPin className="w-5 h-5 text-cyan-400" />
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Unidad</p>
                        <p className="font-medium">{profileModalUser.unit_number}</p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
              
              {/* Description */}
              {profileModalUser.public_description && (
                <Card className="bg-[#0A0A0F] border-[#1E293B]">
                  <CardContent className="p-4">
                    <p className="text-xs text-muted-foreground mb-2">Descripción</p>
                    <p className="text-sm">{profileModalUser.public_description}</p>
                  </CardContent>
                </Card>
              )}
              
              {/* Loading indicator */}
              {loadingProfile && (
                <div className="flex items-center justify-center py-2">
                  <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                  <span className="text-xs text-muted-foreground ml-2">Cargando más información...</span>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ProfileDirectory;
