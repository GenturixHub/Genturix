/**
 * GENTURIX - Developer Profile Page
 * 
 * Public page displaying developer information.
 * Accessible without authentication.
 */
import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  Mail, 
  Globe, 
  Linkedin, 
  Github,
  Code2,
  User,
  Loader2,
  RefreshCw
} from 'lucide-react';
import { Button } from '../components/ui/button';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const DeveloperPage = () => {
  const [profileData, setProfileData] = useState(null);

  // Fetch developer profile - using direct fetch for public endpoint
  const { data: profile, isLoading, error, refetch } = useQuery({
    queryKey: ['developer-profile-public'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/developer-profile`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error('Error fetching developer profile');
      }
      
      return response.json();
    },
    staleTime: 0,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
    retry: 2,
  });

  // Sync profile data when fetched
  useEffect(() => {
    if (profile) {
      setProfileData(profile);
    }
  }, [profile]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#030712] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <p className="text-white/50 text-sm">Cargando perfil...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#030712] flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-red-400 mb-4">Error al cargar el perfil del desarrollador</p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Reintentar
            </Button>
            <Link to="/">
              <Button variant="ghost">Volver al inicio</Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Use profileData or profile, whichever is available
  const displayProfile = profileData || profile || {};
  const hasProfile = displayProfile?.name || displayProfile?.bio;

  return (
    <div className="min-h-screen min-h-[100dvh] bg-[#030712] text-white overflow-x-hidden">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-[#030712]/95 backdrop-blur-lg border-b border-white/5">
        <div className="max-w-4xl mx-auto px-4 py-3 sm:py-4 flex items-center justify-between">
          <Link 
            to="/" 
            className="flex items-center gap-2 text-white/70 hover:text-white transition-colors min-h-[44px]"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm">Volver</span>
          </Link>
          <div className="flex items-center gap-2">
            <Code2 className="w-5 h-5 text-primary" />
            <span className="font-semibold text-sm sm:text-base">Desarrollador</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-8 sm:py-12">
        {!hasProfile ? (
          // No profile set yet
          <div className="text-center py-12 sm:py-20">
            <div className="w-20 h-20 sm:w-24 sm:h-24 mx-auto mb-4 sm:mb-6 rounded-full bg-white/5 flex items-center justify-center">
              <User className="w-10 h-10 sm:w-12 sm:h-12 text-white/30" />
            </div>
            <h1 className="text-xl sm:text-2xl font-bold mb-2">Perfil del Desarrollador</h1>
            <p className="text-white/50 text-sm sm:text-base px-4">
              La información del desarrollador aún no ha sido configurada.
            </p>
          </div>
        ) : (
          // Profile content
          <div className="space-y-6 sm:space-y-8">
            {/* Profile Header */}
            <div className="flex flex-col items-center gap-4 sm:gap-6 sm:flex-row sm:items-start sm:gap-8">
              {/* Photo */}
              <div className="flex-shrink-0">
                {displayProfile.photo_url ? (
                  <img
                    src={displayProfile.photo_url}
                    alt={displayProfile.name || 'Desarrollador'}
                    className="w-28 h-28 sm:w-32 sm:h-32 md:w-40 md:h-40 rounded-2xl object-cover border-2 border-white/10"
                  />
                ) : (
                  <div className="w-28 h-28 sm:w-32 sm:h-32 md:w-40 md:h-40 rounded-2xl bg-gradient-to-br from-primary/20 to-purple-500/20 flex items-center justify-center border-2 border-white/10">
                    <User className="w-12 h-12 sm:w-14 sm:h-14 md:w-16 md:h-16 text-white/40" />
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="text-center sm:text-left flex-1 w-full">
                <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-1 sm:mb-2 break-words">
                  {displayProfile.name || 'Desarrollador'}
                </h1>
                {displayProfile.title && (
                  <p className="text-base sm:text-lg md:text-xl text-primary mb-3 sm:mb-4 break-words">
                    {displayProfile.title}
                  </p>
                )}
                
                {/* Social Links */}
                <div className="flex flex-wrap justify-center sm:justify-start gap-2 sm:gap-3 mt-3 sm:mt-4">
                  {displayProfile.email && (
                    <a
                      href={`mailto:${displayProfile.email}`}
                      className="inline-flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 active:bg-white/15 border border-white/10 transition-all text-xs sm:text-sm"
                      data-testid="developer-email-link"
                    >
                      <Mail className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                      <span>Email</span>
                    </a>
                  )}
                  {displayProfile.website && (
                    <a
                      href={displayProfile.website.startsWith('http') ? displayProfile.website : `https://${displayProfile.website}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 active:bg-white/15 border border-white/10 transition-all text-xs sm:text-sm"
                      data-testid="developer-website-link"
                    >
                      <Globe className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                      <span>Website</span>
                    </a>
                  )}
                  {displayProfile.linkedin && (
                    <a
                      href={displayProfile.linkedin.startsWith('http') ? displayProfile.linkedin : `https://linkedin.com/in/${displayProfile.linkedin}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-xl bg-[#0A66C2]/20 hover:bg-[#0A66C2]/30 active:bg-[#0A66C2]/40 border border-[#0A66C2]/30 transition-all text-xs sm:text-sm text-[#0A66C2]"
                      data-testid="developer-linkedin-link"
                    >
                      <Linkedin className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                      <span>LinkedIn</span>
                    </a>
                  )}
                  {displayProfile.github && (
                    <a
                      href={displayProfile.github.startsWith('http') ? displayProfile.github : `https://github.com/${displayProfile.github}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 active:bg-white/15 border border-white/10 transition-all text-xs sm:text-sm"
                      data-testid="developer-github-link"
                    >
                      <Github className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                      <span>GitHub</span>
                    </a>
                  )}
                </div>
              </div>
            </div>

            {/* Bio Section */}
            {displayProfile.bio && (
              <div className="mt-6 sm:mt-8 p-4 sm:p-6 rounded-2xl bg-white/[0.02] border border-white/5">
                <h2 className="text-base sm:text-lg font-semibold mb-3 sm:mb-4 flex items-center gap-2">
                  <Code2 className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
                  Acerca del Desarrollador
                </h2>
                <div className="prose prose-invert max-w-none">
                  <p className="text-white/70 whitespace-pre-wrap leading-relaxed text-sm sm:text-base">
                    {displayProfile.bio}
                  </p>
                </div>
              </div>
            )}

            {/* Footer Links */}
            <div className="pt-6 sm:pt-8 border-t border-white/5">
              <div className="flex flex-wrap justify-center gap-3 sm:gap-4 text-xs sm:text-sm text-white/40">
                <Link to="/privacy" className="hover:text-white active:text-white/80 transition-colors py-1">
                  Política de Privacidad
                </Link>
                <span className="hidden sm:inline">•</span>
                <Link to="/terms" className="hover:text-white active:text-white/80 transition-colors py-1">
                  Términos de Servicio
                </Link>
                <span className="hidden sm:inline">•</span>
                <Link to="/login" className="hover:text-white active:text-white/80 transition-colors py-1">
                  Iniciar Sesión
                </Link>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Platform Footer */}
      <footer className="border-t border-white/5 py-4 sm:py-6">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <p className="text-[10px] sm:text-xs text-white/30">
            GENTURIX Platform • Sistema de Gestión de Condominios
          </p>
        </div>
      </footer>
    </div>
  );
};

export default DeveloperPage;
