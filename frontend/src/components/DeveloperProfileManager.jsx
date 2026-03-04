/**
 * GENTURIX - Developer Profile Manager
 * 
 * SuperAdmin component to manage the platform developer profile.
 */
import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { 
  User,
  Mail,
  Globe,
  Linkedin,
  Github,
  Camera,
  Save,
  Loader2,
  Code2,
  ExternalLink,
  Trash2
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import api from '../services/api';

const DeveloperProfileManager = () => {
  const queryClient = useQueryClient();
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    title: '',
    bio: '',
    email: '',
    website: '',
    linkedin: '',
    github: '',
    photo_url: null
  });

  // Fetch current profile
  const { data: profile, isLoading } = useQuery({
    queryKey: ['developer-profile'],
    queryFn: () => api.get('/developer-profile'),
    onSuccess: (data) => {
      if (data) {
        setFormData({
          name: data.name || '',
          title: data.title || '',
          bio: data.bio || '',
          email: data.email || '',
          website: data.website || '',
          linkedin: data.linkedin || '',
          github: data.github || '',
          photo_url: data.photo_url || null
        });
      }
    }
  });

  // Update profile mutation
  const updateMutation = useMutation({
    mutationFn: (data) => api.put('/super-admin/developer-profile', data),
    onSuccess: () => {
      queryClient.invalidateQueries(['developer-profile']);
      toast.success('Perfil del desarrollador actualizado');
    },
    onError: (error) => {
      toast.error(error.message || 'Error al actualizar el perfil');
    }
  });

  // Handle form field change
  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  // Handle photo upload
  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      toast.error('Por favor selecciona una imagen válida');
      return;
    }

    // Validate file size (max 2MB)
    if (file.size > 2 * 1024 * 1024) {
      toast.error('La imagen no debe superar los 2MB');
      return;
    }

    setIsUploading(true);

    try {
      // Convert to base64
      const reader = new FileReader();
      reader.onload = async (event) => {
        const base64Data = event.target?.result;
        
        // Upload to backend
        await api.post('/super-admin/developer-profile/photo', {
          photo_data: base64Data
        });

        setFormData(prev => ({ ...prev, photo_url: base64Data }));
        queryClient.invalidateQueries(['developer-profile']);
        toast.success('Foto actualizada');
        setIsUploading(false);
      };
      reader.readAsDataURL(file);
    } catch (error) {
      toast.error('Error al subir la foto');
      setIsUploading(false);
    }
  };

  // Remove photo
  const handleRemovePhoto = async () => {
    try {
      await api.put('/super-admin/developer-profile', { photo_url: null });
      setFormData(prev => ({ ...prev, photo_url: null }));
      queryClient.invalidateQueries(['developer-profile']);
      toast.success('Foto eliminada');
    } catch (error) {
      toast.error('Error al eliminar la foto');
    }
  };

  // Handle form submit
  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Validate required fields
    if (!formData.name.trim()) {
      toast.error('El nombre es requerido');
      return;
    }

    updateMutation.mutate({
      name: formData.name.trim(),
      title: formData.title.trim(),
      bio: formData.bio.trim(),
      email: formData.email.trim() || null,
      website: formData.website.trim() || null,
      linkedin: formData.linkedin.trim() || null,
      github: formData.github.trim() || null
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Code2 className="w-5 h-5 text-primary" />
            Perfil del Desarrollador
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Gestiona la información pública del desarrollador de la plataforma
          </p>
        </div>
        <a
          href="/developer"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
        >
          <ExternalLink className="w-4 h-4" />
          Ver página pública
        </a>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="grid gap-6 md:grid-cols-[280px_1fr]">
          {/* Photo Section */}
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardHeader>
              <CardTitle className="text-sm">Foto de Perfil</CardTitle>
              <CardDescription>
                Imagen visible en la página pública
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Photo Preview */}
              <div className="flex flex-col items-center">
                {formData.photo_url ? (
                  <img
                    src={formData.photo_url}
                    alt="Developer"
                    className="w-40 h-40 rounded-2xl object-cover border-2 border-white/10"
                  />
                ) : (
                  <div className="w-40 h-40 rounded-2xl bg-white/5 flex items-center justify-center border-2 border-dashed border-white/10">
                    <User className="w-16 h-16 text-white/20" />
                  </div>
                )}
              </div>

              {/* Upload Button */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handlePhotoUpload}
                className="hidden"
              />
              <div className="flex flex-col gap-2">
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                >
                  {isUploading ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Camera className="w-4 h-4 mr-2" />
                  )}
                  {isUploading ? 'Subiendo...' : 'Cambiar foto'}
                </Button>
                {formData.photo_url && (
                  <Button
                    type="button"
                    variant="ghost"
                    className="w-full text-red-400 hover:text-red-300 hover:bg-red-500/10"
                    onClick={handleRemovePhoto}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Eliminar foto
                  </Button>
                )}
              </div>
              <p className="text-xs text-muted-foreground text-center">
                JPG, PNG o WebP. Máximo 2MB.
              </p>
            </CardContent>
          </Card>

          {/* Info Section */}
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardHeader>
              <CardTitle className="text-sm">Información Personal</CardTitle>
              <CardDescription>
                Datos que se mostrarán en la página del desarrollador
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Name */}
              <div className="space-y-2">
                <label className="text-sm font-medium flex items-center gap-2">
                  <User className="w-4 h-4 text-muted-foreground" />
                  Nombre *
                </label>
                <Input
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  placeholder="Tu nombre completo"
                  className="bg-white/5 border-white/10"
                  data-testid="developer-name-input"
                />
              </div>

              {/* Title */}
              <div className="space-y-2">
                <label className="text-sm font-medium flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-muted-foreground" />
                  Título / Rol
                </label>
                <Input
                  value={formData.title}
                  onChange={(e) => handleChange('title', e.target.value)}
                  placeholder="Ej: Full Stack Developer, CTO, Founder..."
                  className="bg-white/5 border-white/10"
                  data-testid="developer-title-input"
                />
              </div>

              {/* Bio */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Biografía</label>
                <Textarea
                  value={formData.bio}
                  onChange={(e) => handleChange('bio', e.target.value)}
                  placeholder="Cuéntale al mundo sobre ti, tu experiencia y tu pasión por el desarrollo..."
                  className="bg-white/5 border-white/10 min-h-[120px] resize-none"
                  data-testid="developer-bio-input"
                />
                <p className="text-xs text-muted-foreground">
                  {formData.bio.length}/2000 caracteres
                </p>
              </div>

              {/* Contact Links */}
              <div className="pt-4 border-t border-white/10">
                <h3 className="text-sm font-medium mb-4">Enlaces de Contacto</h3>
                <div className="grid gap-4 sm:grid-cols-2">
                  {/* Email */}
                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground flex items-center gap-2">
                      <Mail className="w-4 h-4" />
                      Email
                    </label>
                    <Input
                      type="email"
                      value={formData.email}
                      onChange={(e) => handleChange('email', e.target.value)}
                      placeholder="tu@email.com"
                      className="bg-white/5 border-white/10"
                      data-testid="developer-email-input"
                    />
                  </div>

                  {/* Website */}
                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground flex items-center gap-2">
                      <Globe className="w-4 h-4" />
                      Sitio Web
                    </label>
                    <Input
                      value={formData.website}
                      onChange={(e) => handleChange('website', e.target.value)}
                      placeholder="https://tusitio.com"
                      className="bg-white/5 border-white/10"
                      data-testid="developer-website-input"
                    />
                  </div>

                  {/* LinkedIn */}
                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground flex items-center gap-2">
                      <Linkedin className="w-4 h-4" />
                      LinkedIn
                    </label>
                    <Input
                      value={formData.linkedin}
                      onChange={(e) => handleChange('linkedin', e.target.value)}
                      placeholder="https://linkedin.com/in/usuario"
                      className="bg-white/5 border-white/10"
                      data-testid="developer-linkedin-input"
                    />
                  </div>

                  {/* GitHub */}
                  <div className="space-y-2">
                    <label className="text-sm text-muted-foreground flex items-center gap-2">
                      <Github className="w-4 h-4" />
                      GitHub
                    </label>
                    <Input
                      value={formData.github}
                      onChange={(e) => handleChange('github', e.target.value)}
                      placeholder="https://github.com/usuario"
                      className="bg-white/5 border-white/10"
                      data-testid="developer-github-input"
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Save Button */}
        <div className="flex justify-end mt-6">
          <Button 
            type="submit" 
            disabled={updateMutation.isPending}
            className="min-w-[150px]"
            data-testid="save-developer-profile-btn"
          >
            {updateMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Guardando...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Guardar Cambios
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default DeveloperProfileManager;
