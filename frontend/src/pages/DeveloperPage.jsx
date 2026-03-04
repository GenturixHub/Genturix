/**
 * GENTURIX - Developer Profile Page
 * 
 * Public page displaying developer information.
 * Accessible without authentication.
 */
import React from 'react';
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
  Loader2
} from 'lucide-react';
import { Button } from '../components/ui/button';
import api from '../services/api';

const DeveloperPage = () => {
  // Fetch developer profile
  const { data: profile, isLoading, error } = useQuery({
    queryKey: ['developer-profile'],
    queryFn: () => api.get('/developer-profile'),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#030712] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#030712] flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">Error al cargar el perfil del desarrollador</p>
          <Link to="/">
            <Button variant="outline">Volver al inicio</Button>
          </Link>
        </div>
      </div>
    );
  }

  const hasProfile = profile?.name || profile?.bio;

  return (
    <div className="min-h-screen bg-[#030712] text-white">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-[#030712]/95 backdrop-blur-lg border-b border-white/5">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link 
            to="/" 
            className="flex items-center gap-2 text-white/70 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm">Volver</span>
          </Link>
          <div className="flex items-center gap-2">
            <Code2 className="w-5 h-5 text-primary" />
            <span className="font-semibold">Desarrollador</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-12">
        {!hasProfile ? (
          // No profile set yet
          <div className="text-center py-20">
            <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-white/5 flex items-center justify-center">
              <User className="w-12 h-12 text-white/30" />
            </div>
            <h1 className="text-2xl font-bold mb-2">Perfil del Desarrollador</h1>
            <p className="text-white/50">
              La información del desarrollador aún no ha sido configurada.
            </p>
          </div>
        ) : (
          // Profile content
          <div className="space-y-8">
            {/* Profile Header */}
            <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6 sm:gap-8">
              {/* Photo */}
              <div className="flex-shrink-0">
                {profile.photo_url ? (
                  <img
                    src={profile.photo_url}
                    alt={profile.name}
                    className="w-32 h-32 sm:w-40 sm:h-40 rounded-2xl object-cover border-2 border-white/10"
                  />
                ) : (
                  <div className="w-32 h-32 sm:w-40 sm:h-40 rounded-2xl bg-gradient-to-br from-primary/20 to-purple-500/20 flex items-center justify-center border-2 border-white/10">
                    <User className="w-16 h-16 text-white/40" />
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="text-center sm:text-left flex-1">
                <h1 className="text-3xl sm:text-4xl font-bold mb-2">
                  {profile.name || 'Desarrollador'}
                </h1>
                {profile.title && (
                  <p className="text-lg sm:text-xl text-primary mb-4">
                    {profile.title}
                  </p>
                )}
                
                {/* Social Links */}
                <div className="flex flex-wrap justify-center sm:justify-start gap-3 mt-4">
                  {profile.email && (
                    <a
                      href={`mailto:${profile.email}`}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition-all text-sm"
                      data-testid="developer-email-link"
                    >
                      <Mail className="w-4 h-4" />
                      <span>Email</span>
                    </a>
                  )}
                  {profile.website && (
                    <a
                      href={profile.website.startsWith('http') ? profile.website : `https://${profile.website}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition-all text-sm"
                      data-testid="developer-website-link"
                    >
                      <Globe className="w-4 h-4" />
                      <span>Website</span>
                    </a>
                  )}
                  {profile.linkedin && (
                    <a
                      href={profile.linkedin.startsWith('http') ? profile.linkedin : `https://linkedin.com/in/${profile.linkedin}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#0A66C2]/20 hover:bg-[#0A66C2]/30 border border-[#0A66C2]/30 transition-all text-sm text-[#0A66C2]"
                      data-testid="developer-linkedin-link"
                    >
                      <Linkedin className="w-4 h-4" />
                      <span>LinkedIn</span>
                    </a>
                  )}
                  {profile.github && (
                    <a
                      href={profile.github.startsWith('http') ? profile.github : `https://github.com/${profile.github}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition-all text-sm"
                      data-testid="developer-github-link"
                    >
                      <Github className="w-4 h-4" />
                      <span>GitHub</span>
                    </a>
                  )}
                </div>
              </div>
            </div>

            {/* Bio Section */}
            {profile.bio && (
              <div className="mt-8 p-6 rounded-2xl bg-white/[0.02] border border-white/5">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Code2 className="w-5 h-5 text-primary" />
                  Acerca del Desarrollador
                </h2>
                <div className="prose prose-invert max-w-none">
                  <p className="text-white/70 whitespace-pre-wrap leading-relaxed">
                    {profile.bio}
                  </p>
                </div>
              </div>
            )}

            {/* Footer Links */}
            <div className="pt-8 border-t border-white/5">
              <div className="flex flex-wrap justify-center gap-4 text-sm text-white/40">
                <Link to="/privacy" className="hover:text-white transition-colors">
                  Política de Privacidad
                </Link>
                <span>•</span>
                <Link to="/terms" className="hover:text-white transition-colors">
                  Términos de Servicio
                </Link>
                <span>•</span>
                <Link to="/login" className="hover:text-white transition-colors">
                  Iniciar Sesión
                </Link>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Platform Footer */}
      <footer className="border-t border-white/5 py-6">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <p className="text-xs text-white/30">
            GENTURIX Platform • Sistema de Gestión de Condominios
          </p>
        </div>
      </footer>
    </div>
  );
};

export default DeveloperPage;
