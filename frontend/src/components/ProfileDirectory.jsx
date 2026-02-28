/**
 * GENTURIX - Profile Directory Component (TanStack Query v5)
 * Shows all users in the same condominium grouped by role
 * Can be embedded in any role's UI (Guard, Resident, Admin, HR)
 * 
 * When embedded=true, clicking a profile shows it in a modal (no navigation)
 * This prevents users from getting stuck in isolated profile pages
 * 
 * Uses TanStack Query for data fetching with caching.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
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
import { useCondominiumDirectory } from '../hooks/queries/useResidentQueries';
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

// Role configuration - icons and colors only
const ROLE_CONFIG = {
  'Administrador': { icon: Shield, color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30' },
  'Supervisor': { icon: UserCheck, color: 'bg-teal-500/10 text-teal-400 border-teal-500/30' },
  'HR': { icon: Briefcase, color: 'bg-orange-500/10 text-orange-400 border-orange-500/30' },
  'Guarda': { icon: Shield, color: 'bg-green-500/10 text-green-400 border-green-500/30' },
  'Residente': { icon: Home, color: 'bg-blue-500/10 text-blue-400 border-blue-500/30' },
  'Estudiante': { icon: GraduationCap, color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30' },
};

const ProfileDirectory = ({ onViewProfile, embedded = false, maxHeight = "100%" }) => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { user } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [photoModalOpen, setPhotoModalOpen] = useState(false);
  
  // State for embedded profile modal
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [profileModalUser, setProfileModalUser] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);

  // TanStack Query: Directory data with caching
  const { 
    data: directory, 
    isLoading, 
    error: queryError 
  } = useCondominiumDirectory();
  
  const error = queryError?.message || null;

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
    <div className="flex flex-col w-full" style={{ height: maxHeight }}>
      {/* Header - Full width */}
      <div className={`flex-shrink-0 ${embedded ? 'px-1 py-3 border-b border-[#1E293B]/50' : ''}`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-bold">
              {t('directory.title')}
            </h2>
          </div>
          {hasUsers && (
            <Badge variant="outline" className="text-[10px] px-2 py-0.5">
              {directory.total_count}
            </Badge>
          )}
        </div>
        
        {/* Search - Full width */}
        {hasUsers && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder={t('directory.searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-11 bg-[#0A0A0F] border-[#1E293B] rounded-xl text-sm"
              data-testid="directory-search"
            />
          </div>
        )}
      </div>

      {/* Directory Content - Native scroll */}
      <div 
        className="flex-1 min-h-0 overflow-y-auto"
        style={{ WebkitOverflowScrolling: 'touch', paddingBottom: '112px' }}
      >
        <div className={`space-y-4 ${embedded ? 'py-3' : ''}`}>
          {!hasUsers ? (
            <div className="bg-[#0F111A] border border-[#1E293B] rounded-2xl p-8 text-center">
              <Users className="w-12 h-12 text-muted-foreground/50 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">{t('directory.noUsers')}</p>
            </div>
          ) : (
            Object.entries(directory.grouped_by_role).map(([role, users]) => {
              const filteredUsers = filterUsers(users);
              if (filteredUsers.length === 0) return null;
              
              const config = ROLE_CONFIG[role] || { icon: User, color: 'bg-gray-500/10 text-gray-400 border-gray-500/30' };
              const RoleIcon = config.icon;
              const roleLabel = t(`directory.roleLabels.${role}`, role);
              
              return (
                <div key={role} className="space-y-2">
                  {/* Role Header */}
                  <div className="flex items-center gap-2 px-1">
                    <RoleIcon className="w-4 h-4 text-muted-foreground" />
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{roleLabel}</span>
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 ml-auto">
                      {filteredUsers.length}
                    </Badge>
                  </div>
                  
                  {/* Users List - Full width cards */}
                  <div className="space-y-2">
                    {filteredUsers.map((dirUser) => (
                      <div 
                        key={dirUser.id}
                        className="bg-[#0F111A] border border-[#1E293B] rounded-2xl p-3 active:scale-[0.99] transition-all cursor-pointer"
                        onClick={() => handleViewProfile(dirUser.id, dirUser)}
                        data-testid={`user-card-${dirUser.id}`}
                      >
                        <div className="flex items-center gap-3">
                          {/* Avatar */}
                          <div 
                            className="relative"
                            onClick={(e) => handlePhotoClick(dirUser, e)}
                          >
                            <Avatar className="w-11 h-11 border-2 border-[#1E293B]">
                              <AvatarImage src={dirUser.profile_photo} />
                              <AvatarFallback className={`${config.color} text-sm font-bold`}>
                                {dirUser.full_name?.charAt(0).toUpperCase()}
                              </AvatarFallback>
                            </Avatar>
                          </div>
                          
                          {/* Info */}
                          <div className="flex-1 min-w-0">
                            <h3 className="font-semibold text-sm text-white truncate">{dirUser.full_name}</h3>
                            <div className="flex items-center gap-2 mt-0.5">
                              <Badge className={`${config.color} text-[10px] px-1.5 py-0`}>
                                {t(`roles.labels.${role}`, role)}
                              </Badge>
                              {dirUser.phone && (
                                <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                                  <Phone className="w-3 h-3" />
                                  {dirUser.phone}
                                </span>
                              )}
                            </div>
                          </div>
                          
                          {/* Arrow */}
                          <ChevronRight className="w-5 h-5 text-muted-foreground/50 flex-shrink-0" />
                        </div>
                      </div>
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
                <DialogTitle className="text-base">{t('directory.profile')}</DialogTitle>
                <DialogDescription className="text-xs">
                  {t('directory.contactInfo')}
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
                    const config = ROLE_CONFIG[role] || { color: 'bg-gray-500/10 text-gray-400 border-gray-500/30' };
                    return (
                      <Badge key={index} className={config.color}>
                        {t(`roles.labels.${role}`, role)}
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
                        <p className="text-xs text-muted-foreground">{t('directory.phone')}</p>
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
                        <p className="text-xs text-muted-foreground">{t('directory.email')}</p>
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
                        <p className="text-xs text-muted-foreground">{t('directory.unit')}</p>
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
                    <p className="text-xs text-muted-foreground mb-2">{t('directory.description')}</p>
                    <p className="text-sm">{profileModalUser.public_description}</p>
                  </CardContent>
                </Card>
              )}
              
              {/* Loading indicator */}
              {loadingProfile && (
                <div className="flex items-center justify-center py-2">
                  <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                  <span className="text-xs text-muted-foreground ml-2">{t('directory.loadingMore')}</span>
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
