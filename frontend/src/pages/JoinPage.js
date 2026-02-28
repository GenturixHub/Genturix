/**
 * GENTURIX - Join Page (Public Access Request)
 * Allows potential residents to request access to a condominium
 * via an invitation link or QR code.
 * 
 * This page is PUBLIC - no authentication required.
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import api from '../services/api';
import {
  Shield,
  Loader2,
  CheckCircle,
  XCircle,
  Home,
  Mail,
  Phone,
  User,
  Building,
  Clock,
  AlertTriangle,
  ArrowLeft
} from 'lucide-react';

const JoinPage = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  
  // States
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [inviteInfo, setInviteInfo] = useState(null);
  const [error, setError] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [requestStatus, setRequestStatus] = useState(null);
  const [checkingStatus, setCheckingStatus] = useState(false);
  const [statusEmail, setStatusEmail] = useState('');
  
  // Form state
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    apartment_number: '',
    tower_block: '',
    resident_type: 'owner',
    notes: ''
  });
  
  // Load invitation info
  useEffect(() => {
    const loadInviteInfo = async () => {
      try {
        const info = await api.getInvitationInfo(token);
        setInviteInfo(info);
      } catch (err) {
        setError(err.message || 'Invitación no válida o expirada');
      } finally {
        setLoading(false);
      }
    };
    
    if (token) {
      loadInviteInfo();
    } else {
      setError('Token de invitación no proporcionado');
      setLoading(false);
    }
  }, [token]);
  
  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validation
    if (!form.full_name.trim()) {
      toast.error('El nombre completo es requerido');
      return;
    }
    if (!form.email.trim()) {
      toast.error('El email es requerido');
      return;
    }
    if (!form.apartment_number.trim()) {
      toast.error('El número de apartamento/casa es requerido');
      return;
    }
    
    setSubmitting(true);
    try {
      const result = await api.submitAccessRequest(token, form);
      setSubmitted(true);
      setRequestStatus({
        status: 'pending_approval',
        message: result.message
      });
      toast.success('Solicitud enviada exitosamente');
    } catch (err) {
      toast.error(err.message || 'Error al enviar solicitud');
    } finally {
      setSubmitting(false);
    }
  };
  
  // Check request status
  const handleCheckStatus = async () => {
    if (!statusEmail.trim()) {
      toast.error('Ingresa tu email para verificar el estado');
      return;
    }
    
    setCheckingStatus(true);
    try {
      const status = await api.getAccessRequestStatus(token, statusEmail);
      setRequestStatus(status);
      if (status.status === 'approved') {
        toast.success('¡Tu solicitud ha sido aprobada! Revisa tu email.');
      } else if (status.status === 'rejected') {
        toast.error('Tu solicitud no fue aprobada.');
      }
    } catch (err) {
      toast.error(err.message || 'No se encontró ninguna solicitud con este email');
    } finally {
      setCheckingStatus(false);
    }
  };
  
  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Verificando invitación...</p>
        </div>
      </div>
    );
  }
  
  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center p-4">
        <Card className="bg-[#0F111A] border-[#1E293B] max-w-md w-full">
          <CardContent className="p-8 text-center">
            <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
              <XCircle className="w-8 h-8 text-red-400" />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Invitación No Válida</h2>
            <p className="text-muted-foreground mb-6">{error}</p>
            <Button variant="outline" onClick={() => navigate('/login')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Ir al Inicio
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  // Success / Status check state
  if (submitted || requestStatus) {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center p-4">
        <Card className="bg-[#0F111A] border-[#1E293B] max-w-md w-full">
          <CardContent className="p-8 text-center">
            {requestStatus?.status === 'approved' ? (
              <>
                <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
                  <CheckCircle className="w-8 h-8 text-green-400" />
                </div>
                <h2 className="text-xl font-bold text-green-400 mb-2">¡Solicitud Aprobada!</h2>
                <p className="text-muted-foreground mb-4">
                  Tu acceso a <strong className="text-white">{inviteInfo?.condominium_name}</strong> ha sido aprobado.
                </p>
                <p className="text-sm text-muted-foreground mb-6">
                  Revisa tu email para obtener tus credenciales de acceso.
                </p>
                <Button onClick={() => navigate('/login')} className="w-full">
                  Iniciar Sesión
                </Button>
              </>
            ) : requestStatus?.status === 'rejected' ? (
              <>
                <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center mx-auto mb-4">
                  <XCircle className="w-8 h-8 text-red-400" />
                </div>
                <h2 className="text-xl font-bold text-red-400 mb-2">Solicitud No Aprobada</h2>
                <p className="text-muted-foreground mb-4">
                  Tu solicitud de acceso no fue aprobada.
                </p>
                {requestStatus?.status_message && (
                  <div className="p-3 rounded-lg bg-[#1E293B] text-left mb-6">
                    <p className="text-sm text-muted-foreground">Motivo:</p>
                    <p className="text-white">{requestStatus.status_message}</p>
                  </div>
                )}
                <p className="text-sm text-muted-foreground">
                  Si crees que esto es un error, contacta a la administración del condominio.
                </p>
              </>
            ) : (
              <>
                <div className="w-16 h-16 rounded-full bg-yellow-500/20 flex items-center justify-center mx-auto mb-4">
                  <Clock className="w-8 h-8 text-yellow-400" />
                </div>
                <h2 className="text-xl font-bold text-yellow-400 mb-2">Solicitud Pendiente</h2>
                <p className="text-muted-foreground mb-4">
                  Tu solicitud para unirte a <strong className="text-white">{inviteInfo?.condominium_name}</strong> está siendo revisada.
                </p>
                <p className="text-sm text-muted-foreground mb-6">
                  Recibirás un email cuando tu solicitud sea procesada.
                </p>
                
                {/* Status check form */}
                <div className="border-t border-[#1E293B] pt-6 mt-6">
                  <p className="text-sm text-muted-foreground mb-3">¿Ya enviaste una solicitud? Verifica el estado:</p>
                  <div className="flex gap-2">
                    <Input
                      type="email"
                      placeholder="Tu email"
                      value={statusEmail}
                      onChange={(e) => setStatusEmail(e.target.value)}
                      className="bg-[#0A0A0F] border-[#1E293B]"
                    />
                    <Button onClick={handleCheckStatus} disabled={checkingStatus} variant="outline">
                      {checkingStatus ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Verificar'}
                    </Button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }
  
  // Main form
  return (
    <div className="min-h-screen bg-[#05050A] overflow-y-auto">
      <div className="flex flex-col items-center justify-start py-4 px-4 pb-32">
        <div className="max-w-lg w-full space-y-6">
          {/* Header */}
          <div className="text-center">
            <div className="w-16 h-16 rounded-2xl bg-primary/20 flex items-center justify-center mx-auto mb-4">
              <Shield className="w-8 h-8 text-primary" />
            </div>
            <h1 className="text-2xl font-bold text-white">GENTURIX</h1>
            <p className="text-muted-foreground">Plataforma de Seguridad y Emergencias</p>
          </div>
          
          {/* Request Form Card */}
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Home className="w-5 h-5 text-primary" />
                Solicitar Acceso
              </CardTitle>
              <CardDescription>
                Solicita acceso a <strong className="text-white">{inviteInfo?.condominium_name}</strong>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
              {/* Full Name */}
              <div className="space-y-2">
                <Label htmlFor="full_name" className="flex items-center gap-2">
                  <User className="w-4 h-4" />
                  Nombre Completo *
                </Label>
                <Input
                  id="full_name"
                  value={form.full_name}
                  onChange={(e) => setForm({...form, full_name: e.target.value})}
                  placeholder="Tu nombre completo"
                  className="bg-[#0A0A0F] border-[#1E293B]"
                  required
                  data-testid="join-full-name"
                />
              </div>
              
              {/* Email */}
              <div className="space-y-2">
                <Label htmlFor="email" className="flex items-center gap-2">
                  <Mail className="w-4 h-4" />
                  Email *
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({...form, email: e.target.value})}
                  placeholder="tu@email.com"
                  className="bg-[#0A0A0F] border-[#1E293B]"
                  required
                  data-testid="join-email"
                />
              </div>
              
              {/* Phone */}
              <div className="space-y-2">
                <Label htmlFor="phone" className="flex items-center gap-2">
                  <Phone className="w-4 h-4" />
                  Teléfono (opcional)
                </Label>
                <Input
                  id="phone"
                  type="tel"
                  value={form.phone}
                  onChange={(e) => setForm({...form, phone: e.target.value})}
                  placeholder="+52 555 123 4567"
                  className="bg-[#0A0A0F] border-[#1E293B]"
                  data-testid="join-phone"
                />
              </div>
              
              {/* Apartment Number */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="apartment_number" className="flex items-center gap-2">
                    <Building className="w-4 h-4" />
                    Apartamento/Casa *
                  </Label>
                  <Input
                    id="apartment_number"
                    value={form.apartment_number}
                    onChange={(e) => setForm({...form, apartment_number: e.target.value})}
                    placeholder="Ej: A-101"
                    className="bg-[#0A0A0F] border-[#1E293B]"
                    required
                    data-testid="join-apartment"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tower_block">Torre/Bloque</Label>
                  <Input
                    id="tower_block"
                    value={form.tower_block}
                    onChange={(e) => setForm({...form, tower_block: e.target.value})}
                    placeholder="Ej: Torre A"
                    className="bg-[#0A0A0F] border-[#1E293B]"
                    data-testid="join-tower"
                  />
                </div>
              </div>
              
              {/* Resident Type */}
              <div className="space-y-2">
                <Label>Tipo de Residente</Label>
                <Select 
                  value={form.resident_type} 
                  onValueChange={(v) => setForm({...form, resident_type: v})}
                >
                  <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]" data-testid="join-resident-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                    <SelectItem value="owner">Propietario</SelectItem>
                    <SelectItem value="tenant">Arrendatario</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {/* Notes */}
              <div className="space-y-2">
                <Label htmlFor="notes">Mensaje (opcional)</Label>
                <Textarea
                  id="notes"
                  value={form.notes}
                  onChange={(e) => setForm({...form, notes: e.target.value})}
                  placeholder="Mensaje adicional para el administrador..."
                  className="bg-[#0A0A0F] border-[#1E293B] min-h-[80px]"
                  data-testid="join-notes"
                />
              </div>
              
              {/* Info Banner */}
              <div className="p-3 rounded-lg bg-primary/10 border border-primary/20 flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                <p className="text-sm text-muted-foreground">
                  Tu solicitud será revisada por el administrador del condominio. 
                  Recibirás un email cuando sea procesada.
                </p>
              </div>
              
              {/* Submit Button */}
              <div className="pt-4">
                <Button 
                  type="submit" 
                  className="w-full h-12" 
                  disabled={submitting}
                  data-testid="join-submit"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin mr-2" />
                      Enviando...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-5 h-5 mr-2" />
                      Enviar Solicitud
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
        
        {/* Already have account link */}
        <div className="text-center pb-8">
          <Button variant="link" onClick={() => navigate('/login')} className="text-muted-foreground">
            ¿Ya tienes cuenta? Inicia sesión
          </Button>
        </div>
        </div>
      </div>
    </div>
  );
};

export default JoinPage;
