/**
 * GENTURIX - Visitor Authorizations for Residents
 * 
 * Allows residents to create and manage visitor authorizations:
 * - Temporary (single date or range)
 * - Permanent (always allowed, e.g., family)
 * - Recurring (specific days of week)
 * - Extended (date range + time windows)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent } from './ui/card';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { ScrollArea } from './ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Checkbox } from './ui/checkbox';
import { toast } from 'sonner';
import api from '../services/api';
import { 
  UserPlus,
  Users,
  Car,
  Calendar,
  Clock,
  Loader2,
  Trash2,
  Edit,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Shield,
  Bell,
  ChevronRight,
  RefreshCw,
  Star,
  Repeat,
  Timer,
  Infinity as InfinityIcon
} from 'lucide-react';

// ============================================
// CONFIGURATION - Functions that return translated config
// ============================================
const getAuthorizationTypes = (t) => ({
  temporary: {
    label: t('visitors.authTypes.temporary'),
    description: t('visitors.authTypes.temporaryDesc'),
    icon: Timer,
    color: 'yellow',
    bgColor: 'bg-yellow-500/20',
    borderColor: 'border-yellow-500/30',
    textColor: 'text-yellow-400'
  },
  permanent: {
    label: t('visitors.authTypes.permanent'),
    description: t('visitors.authTypes.permanentDesc'),
    icon: InfinityIcon,
    color: 'green',
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500/30',
    textColor: 'text-green-400'
  },
  recurring: {
    label: t('visitors.authTypes.recurring'),
    description: t('visitors.authTypes.recurringDesc'),
    icon: Repeat,
    color: 'blue',
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/30',
    textColor: 'text-blue-400'
  },
  extended: {
    label: t('visitors.authTypes.extended'),
    description: t('visitors.authTypes.extendedDesc'),
    icon: Calendar,
    color: 'cyan',
    bgColor: 'bg-cyan-500/20',
    borderColor: 'border-cyan-500/30',
    textColor: 'text-cyan-400'
  }
});

const getDaysOfWeek = (t) => [
  { value: 'Lunes', label: t('visitors.days.monShort') },
  { value: 'Martes', label: t('visitors.days.tueShort') },
  { value: 'Miércoles', label: t('visitors.days.wedShort') },
  { value: 'Jueves', label: t('visitors.days.thuShort') },
  { value: 'Viernes', label: t('visitors.days.friShort') },
  { value: 'Sábado', label: t('visitors.days.satShort') },
  { value: 'Domingo', label: t('visitors.days.sunShort') }
];

const COLOR_CONFIG = {
  green: { bg: 'bg-green-500', light: 'bg-green-500/20', border: 'border-green-500/30', text: 'text-green-400' },
  blue: { bg: 'bg-blue-500', light: 'bg-blue-500/20', border: 'border-blue-500/30', text: 'text-blue-400' },
  yellow: { bg: 'bg-yellow-500', light: 'bg-yellow-500/20', border: 'border-yellow-500/30', text: 'text-yellow-400' },
  cyan: { bg: 'bg-cyan-500', light: 'bg-cyan-500/20', border: 'border-cyan-500/30', text: 'text-cyan-400' },
  purple: { bg: 'bg-cyan-500', light: 'bg-cyan-500/20', border: 'border-cyan-500/30', text: 'text-cyan-400' },
  gray: { bg: 'bg-gray-500', light: 'bg-gray-500/20', border: 'border-gray-500/30', text: 'text-gray-400' }
};

// ============================================
// VISITOR TYPE CONFIGURATION (same as Guard)
// ============================================
import { 
  Package,
  Wrench,
  Cpu,
  Sparkles,
  MoreHorizontal
} from 'lucide-react';

const getVisitorTypes = (t) => ({
  visitor: {
    label: t('visitors.visitorTypes.visitor'),
    description: t('visitors.visitorTypes.visitorDesc'),
    icon: Users,
    bgColor: 'bg-gray-500/20',
    borderColor: 'border-gray-500/30',
    textColor: 'text-gray-400'
  },
  delivery: {
    label: t('visitors.visitorTypes.delivery'),
    description: t('visitors.visitorTypes.deliveryDesc'),
    icon: Package,
    bgColor: 'bg-yellow-500/20',
    borderColor: 'border-yellow-500/30',
    textColor: 'text-yellow-400'
  },
  maintenance: {
    label: t('visitors.visitorTypes.maintenance'),
    description: t('visitors.visitorTypes.maintenanceDesc'),
    icon: Wrench,
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/30',
    textColor: 'text-blue-400'
  },
  technical: {
    label: t('visitors.visitorTypes.technical'),
    description: t('visitors.visitorTypes.technicalDesc'),
    icon: Cpu,
    bgColor: 'bg-purple-500/20',
    borderColor: 'border-purple-500/30',
    textColor: 'text-purple-400'
  },
  cleaning: {
    label: t('visitors.visitorTypes.cleaning'),
    description: t('visitors.visitorTypes.cleaningDesc'),
    icon: Sparkles,
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500/30',
    textColor: 'text-green-400'
  },
  other: {
    label: t('visitors.visitorTypes.other'),
    description: t('visitors.visitorTypes.otherDesc'),
    icon: MoreHorizontal,
    bgColor: 'bg-orange-500/20',
    borderColor: 'border-orange-500/30',
    textColor: 'text-orange-400'
  }
});

const getDeliveryCompanies = (t) => [
  { value: 'Uber Eats', label: t('visitors.deliveryCompanies.uberEats') },
  { value: 'Rappi', label: t('visitors.deliveryCompanies.rappi') },
  { value: 'DHL', label: t('visitors.deliveryCompanies.dhl') },
  { value: 'FedEx', label: t('visitors.deliveryCompanies.fedex') },
  { value: 'Amazon', label: t('visitors.deliveryCompanies.amazon') },
  { value: 'PedidosYa', label: t('visitors.deliveryCompanies.pedidosYa') },
  { value: 'Otro', label: t('visitors.deliveryCompanies.other') }
];

const getServiceTypes = (t) => ({
  delivery: [
    { value: 'Paquete', label: t('visitors.serviceTypes.package') },
    { value: 'Comida', label: t('visitors.serviceTypes.food') },
    { value: 'Documentos', label: t('visitors.serviceTypes.documents') },
    { value: 'Otro', label: t('visitors.serviceTypes.other') }
  ],
  maintenance: [
    { value: 'Plomería', label: t('visitors.serviceTypes.plumbing') },
    { value: 'Electricidad', label: t('visitors.serviceTypes.electricity') },
    { value: 'Aires Acondicionados', label: t('visitors.serviceTypes.airConditioning') },
    { value: 'Pintura', label: t('visitors.serviceTypes.painting') },
    { value: 'Otro', label: t('visitors.serviceTypes.other') }
  ],
  technical: [
    { value: 'Internet/Cable', label: t('visitors.serviceTypes.internetCable') },
    { value: 'Electrodomésticos', label: t('visitors.serviceTypes.appliances') },
    { value: 'Cerrajería', label: t('visitors.serviceTypes.locksmith') },
    { value: 'Fumigación', label: t('visitors.serviceTypes.fumigation') },
    { value: 'Otro', label: t('visitors.serviceTypes.other') }
  ],
  cleaning: [
    { value: 'Apartamento', label: t('visitors.serviceTypes.apartment') },
    { value: 'Oficina', label: t('visitors.serviceTypes.office') },
    { value: 'Otro', label: t('visitors.serviceTypes.other') }
  ]
});

// ============================================
// AUTHORIZATION CARD
// ============================================
const AuthorizationCard = ({ auth, onEdit, onDelete }) => {
  const typeConfig = AUTHORIZATION_TYPES[auth.authorization_type] || AUTHORIZATION_TYPES.temporary;
  const colorConfig = COLOR_CONFIG[auth.color_code] || COLOR_CONFIG.yellow;
  const IconComponent = typeConfig.icon;
  const visitorTypeConfig = VISITOR_TYPES[auth.visitor_type] || VISITOR_TYPES.visitor;
  const VisitorTypeIcon = visitorTypeConfig.icon;
  
  // P0 FIX: Check if visitor is currently inside (cannot delete)
  const hasVisitorInside = auth.has_visitor_inside === true;
  // Can delete if NOT inside and authorization is active
  const canDelete = !hasVisitorInside;
  
  // Check if this is a service type (not regular visitor)
  const isServiceType = auth.visitor_type && auth.visitor_type !== 'visitor';

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
  };

  return (
    <Card className={`bg-[#0F111A] border-2 ${auth.is_currently_valid ? colorConfig.border : 'border-gray-700'}`}>
      <CardContent className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg ${isServiceType ? visitorTypeConfig.bgColor?.replace('/20', '') : colorConfig.bg} flex items-center justify-center`}
                 style={isServiceType ? {
                   backgroundColor: auth.visitor_type === 'delivery' ? '#eab308' : 
                                   auth.visitor_type === 'maintenance' ? '#3b82f6' :
                                   auth.visitor_type === 'technical' ? '#a855f7' :
                                   auth.visitor_type === 'cleaning' ? '#22c55e' :
                                   auth.visitor_type === 'other' ? '#f97316' : undefined
                 } : {}}>
              {isServiceType ? (
                <VisitorTypeIcon className="w-5 h-5 text-white" />
              ) : (
                <IconComponent className="w-5 h-5 text-white" />
              )}
            </div>
            <div>
              <p className="font-bold text-white">{auth.visitor_name}</p>
              <div className="flex flex-wrap gap-1">
                {/* Visitor Type Badge */}
                {isServiceType && (
                  <Badge className={`${visitorTypeConfig.bgColor} ${visitorTypeConfig.textColor} border ${visitorTypeConfig.borderColor} text-[10px]`}>
                    {visitorTypeConfig.label}
                  </Badge>
                )}
                {/* Authorization Type Badge */}
                <Badge className={`${colorConfig.light} ${colorConfig.text} border ${colorConfig.border} text-[10px]`}>
                  {typeConfig.label}
                </Badge>
              </div>
            </div>
          </div>
          
          {/* Status Badge */}
          <div className="flex flex-col items-end gap-1">
            {auth.is_currently_valid ? (
              <Badge className="bg-green-500/20 text-green-400 border border-green-500/30">
                <CheckCircle className="w-3 h-3 mr-1" />
                Válida
              </Badge>
            ) : (
              <Badge className="bg-red-500/20 text-red-400 border border-red-500/30">
                <XCircle className="w-3 h-3 mr-1" />
                {auth.validity_message || 'Inválida'}
              </Badge>
            )}
          </div>
        </div>

        {/* Details */}
        <div className="grid grid-cols-2 gap-2 text-sm mb-3">
          {/* Company info for service types */}
          {auth.company && (
            <div className="flex items-center gap-1 text-muted-foreground col-span-2">
              <VisitorTypeIcon className="w-3 h-3" />
              <span className="font-medium">{auth.company}</span>
              {auth.service_type && <span className="text-xs">• {auth.service_type}</span>}
            </div>
          )}
          {auth.identification_number && (
            <div className="flex items-center gap-1 text-muted-foreground">
              <Shield className="w-3 h-3" />
              <span>{auth.identification_number}</span>
            </div>
          )}
          {auth.vehicle_plate && (
            <div className="flex items-center gap-1 text-muted-foreground">
              <Car className="w-3 h-3" />
              <span className="font-mono">{auth.vehicle_plate}</span>
            </div>
          )}
        </div>

        {/* Type-specific info */}
        <div className="text-xs text-muted-foreground space-y-1">
          {auth.authorization_type === 'temporary' && auth.valid_from && (
            <p><Calendar className="w-3 h-3 inline mr-1" />
              {auth.valid_from === auth.valid_to 
                ? formatDate(auth.valid_from) 
                : `${formatDate(auth.valid_from)} - ${formatDate(auth.valid_to)}`}
            </p>
          )}
          {auth.authorization_type === 'recurring' && auth.allowed_days?.length > 0 && (
            <p><Repeat className="w-3 h-3 inline mr-1" />
              {auth.allowed_days.join(', ')}
            </p>
          )}
          {auth.authorization_type === 'extended' && (
            <>
              {auth.valid_from && (
                <p><Calendar className="w-3 h-3 inline mr-1" />
                  {formatDate(auth.valid_from)} - {formatDate(auth.valid_to)}
                </p>
              )}
              {auth.allowed_hours_from && (
                <p><Clock className="w-3 h-3 inline mr-1" />
                  {auth.allowed_hours_from} - {auth.allowed_hours_to}
                </p>
              )}
            </>
          )}
          {auth.total_visits > 0 && (
            <p className="text-primary">✓ {auth.total_visits} visita{auth.total_visits > 1 ? 's' : ''}</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 mt-3 pt-3 border-t border-[#1E293B]">
          <Button 
            variant="outline" 
            size="sm" 
            className="flex-1"
            onClick={() => onEdit(auth)}
            data-testid={`edit-auth-${auth.id}`}
          >
            <Edit className="w-4 h-4 mr-1" />
            Editar
          </Button>
          
          {/* P0 FIX: Conditional delete button based on visitor status */}
          {canDelete ? (
            <Button 
              variant="outline" 
              size="sm" 
              className="text-red-400 hover:bg-red-500/10"
              onClick={() => onDelete(auth)}
              data-testid={`delete-auth-${auth.id}`}
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          ) : (
            <div 
              className="h-9 px-3 flex items-center rounded-md text-xs text-yellow-400 bg-yellow-500/10 border border-yellow-500/20"
              title="No puedes eliminar mientras la persona está dentro del condominio"
              data-testid={`inside-indicator-${auth.id}`}
            >
              <Shield className="w-3.5 h-3.5 mr-1.5" />
              Dentro
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

// ============================================
// CREATE/EDIT AUTHORIZATION DIALOG
// ============================================
const AuthorizationFormDialog = ({ open, onClose, authorization, onSave }) => {
  const isEdit = !!authorization;
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    visitor_name: '',
    identification_number: '',
    vehicle_plate: '',
    authorization_type: 'temporary',
    valid_from: new Date().toISOString().split('T')[0],
    valid_to: new Date().toISOString().split('T')[0],
    allowed_days: [],
    allowed_hours_from: '08:00',
    allowed_hours_to: '20:00',
    notes: '',
    // New visitor type fields
    visitor_type: 'visitor',
    company: '',
    service_type: ''
  });

  useEffect(() => {
    if (authorization) {
      setFormData({
        visitor_name: authorization.visitor_name || '',
        identification_number: authorization.identification_number || '',
        vehicle_plate: authorization.vehicle_plate || '',
        authorization_type: authorization.authorization_type || 'temporary',
        valid_from: authorization.valid_from || new Date().toISOString().split('T')[0],
        valid_to: authorization.valid_to || new Date().toISOString().split('T')[0],
        allowed_days: authorization.allowed_days || [],
        allowed_hours_from: authorization.allowed_hours_from || '08:00',
        allowed_hours_to: authorization.allowed_hours_to || '20:00',
        notes: authorization.notes || '',
        visitor_type: authorization.visitor_type || 'visitor',
        company: authorization.company || '',
        service_type: authorization.service_type || ''
      });
    } else {
      setFormData({
        visitor_name: '',
        identification_number: '',
        vehicle_plate: '',
        authorization_type: 'temporary',
        valid_from: new Date().toISOString().split('T')[0],
        valid_to: new Date().toISOString().split('T')[0],
        allowed_days: [],
        allowed_hours_from: '08:00',
        allowed_hours_to: '20:00',
        notes: '',
        visitor_type: 'visitor',
        company: '',
        service_type: ''
      });
    }
  }, [authorization, open]);

  const toggleDay = (day) => {
    setFormData(prev => ({
      ...prev,
      allowed_days: prev.allowed_days.includes(day)
        ? prev.allowed_days.filter(d => d !== day)
        : [...prev.allowed_days, day]
    }));
  };

  // Get the required name field label based on visitor type
  const getNameFieldLabel = () => {
    switch (formData.visitor_type) {
      case 'delivery': return 'Nombre del Repartidor';
      case 'maintenance':
      case 'technical': return 'Nombre del Técnico';
      case 'cleaning': return 'Nombre del Personal';
      default: return 'Nombre del Visitante';
    }
  };

  // Validation for required fields
  const getRequiredFieldsMissing = () => {
    // For service types, company is required
    if (['delivery', 'maintenance', 'technical', 'cleaning'].includes(formData.visitor_type)) {
      if (!formData.company.trim()) return true;
    }
    // Visitor name is always required
    if (!formData.visitor_name.trim()) return true;
    return false;
  };

  const handleSubmit = async () => {
    if (getRequiredFieldsMissing()) {
      toast.error('Completa los campos requeridos');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        visitor_name: formData.visitor_name.trim(),
        identification_number: formData.identification_number.trim() || null,
        vehicle_plate: formData.vehicle_plate.trim().toUpperCase() || null,
        authorization_type: formData.authorization_type,
        notes: formData.notes.trim() || null,
        // New visitor type fields
        visitor_type: formData.visitor_type,
        company: formData.company.trim() || null,
        service_type: formData.service_type || null
      };

      // Add type-specific fields
      if (formData.authorization_type === 'temporary') {
        payload.valid_from = formData.valid_from;
        payload.valid_to = formData.valid_to || formData.valid_from;
      } else if (formData.authorization_type === 'recurring') {
        payload.allowed_days = formData.allowed_days;
      } else if (formData.authorization_type === 'extended') {
        payload.valid_from = formData.valid_from;
        payload.valid_to = formData.valid_to;
        payload.allowed_hours_from = formData.allowed_hours_from;
        payload.allowed_hours_to = formData.allowed_hours_to;
      }

      if (isEdit) {
        await api.updateAuthorization(authorization.id, payload);
        toast.success('Autorización actualizada');
      } else {
        await api.createAuthorization(payload);
        toast.success('Autorización creada exitosamente');
      }
      
      onSave();
      onClose();
    } catch (error) {
      toast.error(error.message || 'Error al guardar autorización');
    } finally {
      setIsSubmitting(false);
    }
  };

  const typeConfig = AUTHORIZATION_TYPES[formData.authorization_type];
  const visitorTypeConfig = VISITOR_TYPES[formData.visitor_type];
  const VisitorTypeIcon = visitorTypeConfig?.icon || Users;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0A0A0F] border-[#1E293B] max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <VisitorTypeIcon className={`w-5 h-5 ${visitorTypeConfig?.textColor || 'text-primary'}`} />
            {isEdit ? 'Editar Autorización' : 'Nueva Autorización'}
          </DialogTitle>
          <DialogDescription>
            {isEdit ? 'Modifica los datos de la autorización' : 'Crea una autorización para tu visitante'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Visitor Type Selector */}
          <div>
            <Label className="text-sm text-muted-foreground mb-2 block">Tipo de Persona</Label>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(VISITOR_TYPES).map(([key, config]) => {
                const Icon = config.icon;
                const isSelected = formData.visitor_type === key;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setFormData({...formData, visitor_type: key, company: '', service_type: ''})}
                    className={`p-2.5 rounded-lg border-2 transition-all flex flex-col items-center gap-1 ${
                      isSelected 
                        ? `${config.bgColor} ${config.borderColor} ${config.textColor}` 
                        : 'bg-[#0F111A] border-[#1E293B] text-muted-foreground hover:border-[#2E3B4B]'
                    }`}
                    data-testid={`visitor-type-${key}`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="text-xs font-medium">{config.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Company Field - For service types */}
          {['delivery', 'maintenance', 'technical', 'cleaning'].includes(formData.visitor_type) && (
            <div>
              <Label className="text-sm text-muted-foreground">
                {formData.visitor_type === 'delivery' ? 'Empresa de Delivery *' : 'Empresa / Proveedor *'}
              </Label>
              {formData.visitor_type === 'delivery' ? (
                <Select value={formData.company} onValueChange={(v) => setFormData({...formData, company: v})}>
                  <SelectTrigger className="bg-[#0F111A] border-[#1E293B] mt-1">
                    <SelectValue placeholder="Selecciona empresa" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                    {DELIVERY_COMPANIES.map(c => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  placeholder="Nombre de la empresa"
                  value={formData.company}
                  onChange={(e) => setFormData({...formData, company: e.target.value})}
                  className="bg-[#0F111A] border-[#1E293B] mt-1"
                />
              )}
            </div>
          )}

          {/* Visitor Name */}
          <div>
            <Label className="text-sm text-muted-foreground">{getNameFieldLabel()} *</Label>
            <Input
              placeholder="Nombre completo"
              value={formData.visitor_name}
              onChange={(e) => setFormData({...formData, visitor_name: e.target.value})}
              className="bg-[#0F111A] border-[#1E293B] mt-1"
              data-testid="auth-visitor-name"
            />
          </div>

          {/* Service Type - For service types */}
          {['delivery', 'maintenance', 'technical', 'cleaning'].includes(formData.visitor_type) && 
           SERVICE_TYPES[formData.visitor_type] && (
            <div>
              <Label className="text-sm text-muted-foreground">Tipo de Servicio</Label>
              <Select value={formData.service_type} onValueChange={(v) => setFormData({...formData, service_type: v})}>
                <SelectTrigger className="bg-[#0F111A] border-[#1E293B] mt-1">
                  <SelectValue placeholder="Selecciona tipo" />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  {SERVICE_TYPES[formData.visitor_type].map(t => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* ID and Vehicle */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-sm text-muted-foreground">Cédula / ID</Label>
              <Input
                placeholder="Documento"
                value={formData.identification_number}
                onChange={(e) => setFormData({...formData, identification_number: e.target.value})}
                className="bg-[#0F111A] border-[#1E293B] mt-1"
              />
            </div>
            <div>
              <Label className="text-sm text-muted-foreground">Placa Vehículo</Label>
              <Input
                placeholder="ABC-123"
                value={formData.vehicle_plate}
                onChange={(e) => setFormData({...formData, vehicle_plate: e.target.value.toUpperCase()})}
                className="bg-[#0F111A] border-[#1E293B] mt-1 font-mono"
              />
            </div>
          </div>

          {/* Authorization Type */}
          <div>
            <Label className="text-sm text-muted-foreground">Tipo de Autorización *</Label>
            <Select 
              value={formData.authorization_type} 
              onValueChange={(v) => setFormData({...formData, authorization_type: v})}
            >
              <SelectTrigger className="bg-[#0F111A] border-[#1E293B] mt-1" data-testid="auth-type-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                {Object.entries(AUTHORIZATION_TYPES).map(([key, config]) => (
                  <SelectItem key={key} value={key}>
                    <div className="flex items-center gap-2">
                      <config.icon className={`w-4 h-4 ${config.textColor}`} />
                      <span>{config.label}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground mt-1">{typeConfig.description}</p>
          </div>

          {/* Type-specific fields */}
          {formData.authorization_type === 'temporary' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-sm text-muted-foreground">Fecha Desde</Label>
                <Input
                  type="date"
                  value={formData.valid_from}
                  onChange={(e) => setFormData({...formData, valid_from: e.target.value})}
                  className="bg-[#0F111A] border-[#1E293B] mt-1"
                />
              </div>
              <div>
                <Label className="text-sm text-muted-foreground">Fecha Hasta</Label>
                <Input
                  type="date"
                  value={formData.valid_to}
                  min={formData.valid_from}
                  onChange={(e) => setFormData({...formData, valid_to: e.target.value})}
                  className="bg-[#0F111A] border-[#1E293B] mt-1"
                />
              </div>
            </div>
          )}

          {formData.authorization_type === 'recurring' && (
            <div>
              <Label className="text-sm text-muted-foreground">Días Permitidos</Label>
              <div className="flex flex-wrap gap-2 mt-2">
                {DAYS_OF_WEEK.map((day) => (
                  <Button
                    key={day.value}
                    type="button"
                    variant="outline"
                    size="sm"
                    className={`${formData.allowed_days.includes(day.value) 
                      ? 'bg-blue-500/30 border-blue-500 text-blue-400' 
                      : 'bg-[#0F111A] border-[#1E293B]'}`}
                    onClick={() => toggleDay(day.value)}
                  >
                    {day.label}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {formData.authorization_type === 'extended' && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-sm text-muted-foreground">Fecha Desde</Label>
                  <Input
                    type="date"
                    value={formData.valid_from}
                    onChange={(e) => setFormData({...formData, valid_from: e.target.value})}
                    className="bg-[#0F111A] border-[#1E293B] mt-1"
                  />
                </div>
                <div>
                  <Label className="text-sm text-muted-foreground">Fecha Hasta</Label>
                  <Input
                    type="date"
                    value={formData.valid_to}
                    min={formData.valid_from}
                    onChange={(e) => setFormData({...formData, valid_to: e.target.value})}
                    className="bg-[#0F111A] border-[#1E293B] mt-1"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-sm text-muted-foreground">Hora Desde</Label>
                  <Input
                    type="time"
                    value={formData.allowed_hours_from}
                    onChange={(e) => setFormData({...formData, allowed_hours_from: e.target.value})}
                    className="bg-[#0F111A] border-[#1E293B] mt-1"
                  />
                </div>
                <div>
                  <Label className="text-sm text-muted-foreground">Hora Hasta</Label>
                  <Input
                    type="time"
                    value={formData.allowed_hours_to}
                    onChange={(e) => setFormData({...formData, allowed_hours_to: e.target.value})}
                    className="bg-[#0F111A] border-[#1E293B] mt-1"
                  />
                </div>
              </div>
            </>
          )}

          {/* Notes */}
          <div>
            <Label className="text-sm text-muted-foreground">Notas (opcional)</Label>
            <Textarea
              placeholder="Información adicional para el guardia..."
              value={formData.notes}
              onChange={(e) => setFormData({...formData, notes: e.target.value})}
              className="bg-[#0F111A] border-[#1E293B] mt-1 min-h-[60px]"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancelar
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={!formData.visitor_name.trim() || isSubmitting}
            data-testid="submit-authorization-btn"
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <UserPlus className="w-4 h-4 mr-2" />
            )}
            {isEdit ? 'Guardar Cambios' : 'Crear Autorización'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ============================================
// NOTIFICATIONS PANEL
// ============================================
const NotificationsPanel = ({ notifications, onMarkRead, onMarkAllRead, onRefresh }) => {
  if (notifications.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Bell className="w-12 h-12 mx-auto mb-4 opacity-30" />
        <p className="text-sm">No hay notificaciones</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs text-muted-foreground">{notifications.length} notificaciones</span>
        <Button variant="ghost" size="sm" onClick={onMarkAllRead}>
          Marcar todas leídas
        </Button>
      </div>
      {notifications.map((notif) => (
        <div 
          key={notif.id}
          className={`p-3 rounded-lg border ${notif.read ? 'bg-[#0A0A0F] border-[#1E293B]' : 'bg-primary/10 border-primary/30'}`}
          onClick={() => !notif.read && onMarkRead(notif.id)}
        >
          <div className="flex items-start gap-2">
            {notif.type === 'visitor_arrival' ? (
              <div className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center">
                <UserPlus className="w-4 h-4 text-green-400" />
              </div>
            ) : (
              <div className="w-8 h-8 rounded-lg bg-orange-500/20 flex items-center justify-center">
                <Users className="w-4 h-4 text-orange-400" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm">{notif.title}</p>
              <p className="text-xs text-muted-foreground">{notif.message}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {new Date(notif.created_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>
            {!notif.read && (
              <div className="w-2 h-2 rounded-full bg-primary" />
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

// ============================================
// MAIN COMPONENT
// ============================================
const VisitorAuthorizationsResident = () => {
  const [authorizations, setAuthorizations] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingAuth, setEditingAuth] = useState(null);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [authData, notifData] = await Promise.all([
        api.getMyAuthorizations(),
        api.getVisitorNotifications()
      ]);
      setAuthorizations(authData);
      setNotifications(notifData);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Error al cargar datos');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    // Poll for notifications every 30 seconds
    const interval = setInterval(() => {
      api.getVisitorNotifications().then(setNotifications).catch(console.error);
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleEdit = (auth) => {
    setEditingAuth(auth);
    setShowForm(true);
  };

  const handleDelete = async () => {
    if (!showDeleteConfirm) return;
    setIsDeleting(true);
    try {
      await api.deleteAuthorization(showDeleteConfirm.id);
      toast.success('Autorización eliminada');
      setShowDeleteConfirm(null);
      fetchData();
    } catch (error) {
      toast.error(error.message || 'Error al eliminar');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleMarkNotificationRead = async (notifId) => {
    try {
      await api.markNotificationRead(notifId);
      setNotifications(prev => prev.map(n => n.id === notifId ? {...n, read: true} : n));
    } catch (error) {
      console.error('Error marking notification read:', error);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({...n, read: true})));
    } catch (error) {
      console.error('Error marking all read:', error);
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  // Separate authorizations by status
  const pendingAuths = authorizations.filter(a => a.is_active && a.status !== 'used' && !a.was_used);
  const usedAuths = authorizations.filter(a => a.status === 'used' || a.was_used);
  const inactiveAuths = authorizations.filter(a => !a.is_active && a.status !== 'used' && !a.was_used);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-0 flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-[#1E293B] bg-[#0A0A0F] flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary" />
            <h2 className="font-bold text-white">Autorizaciones</h2>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="ghost" 
              size="icon"
              className="relative"
              onClick={() => setShowNotifications(!showNotifications)}
              data-testid="notifications-btn"
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-500 text-white text-xs flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </Button>
            <Button onClick={fetchData} variant="ghost" size="icon">
              <RefreshCw className="w-5 h-5" />
            </Button>
          </div>
        </div>
        
        {/* Add New Button */}
        <Button 
          className="w-full" 
          onClick={() => { setEditingAuth(null); setShowForm(true); }}
          data-testid="add-authorization-btn"
        >
          <UserPlus className="w-4 h-4 mr-2" />
          Nueva Autorización
        </Button>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1 h-full">
        <div className="p-4 pb-24 space-y-4">
          {/* Notifications Panel (collapsible) */}
          {showNotifications && (
            <Card className="bg-[#0F111A] border-[#1E293B]">
              <CardContent className="p-4">
                <NotificationsPanel 
                  notifications={notifications}
                  onMarkRead={handleMarkNotificationRead}
                  onMarkAllRead={handleMarkAllRead}
                  onRefresh={fetchData}
                />
              </CardContent>
            </Card>
          )}

          {/* Pending (Active, Not Used) Authorizations */}
          {pendingAuths.length > 0 ? (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-400" />
                Autorizaciones Pendientes ({pendingAuths.length})
              </h3>
              {pendingAuths.map((auth) => (
                <AuthorizationCard 
                  key={auth.id} 
                  auth={auth}
                  onEdit={handleEdit}
                  onDelete={(a) => setShowDeleteConfirm(a)}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Users className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
              <p className="text-muted-foreground">No tienes autorizaciones pendientes</p>
              <p className="text-xs text-muted-foreground mt-1">
                Crea una autorización para tus visitantes frecuentes
              </p>
            </div>
          )}

          {/* Used Authorizations (Check-ins completed) */}
          {usedAuths.length > 0 && (
            <div className="space-y-3 pt-4 border-t border-[#1E293B]">
              <h3 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-blue-400" />
                Utilizadas ({usedAuths.length})
              </h3>
              {usedAuths.slice(0, 5).map((auth) => (
                <div 
                  key={auth.id}
                  className="p-3 rounded-lg bg-blue-500/5 border border-blue-500/20"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-blue-400">{auth.visitor_name}</p>
                      <p className="text-xs text-muted-foreground">
                        {auth.authorization_type === 'temporary' ? 'Temporal' : 
                         auth.authorization_type === 'extended' ? 'Extendido' : 
                         auth.authorization_type}
                      </p>
                    </div>
                    <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">
                      ✓ Ingresó
                    </Badge>
                  </div>
                  {auth.used_at && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Entrada: {new Date(auth.used_at).toLocaleString('es-ES', { 
                        day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' 
                      })}
                      {auth.used_by_guard && ` • Guardia: ${auth.used_by_guard}`}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Inactive/Expired Authorizations */}
          {inactiveAuths.length > 0 && (
            <div className="space-y-3 pt-4 border-t border-[#1E293B]">
              <h3 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                <XCircle className="w-4 h-4 text-gray-400" />
                Expiradas ({inactiveAuths.length})
              </h3>
              {inactiveAuths.slice(0, 3).map((auth) => (
                <AuthorizationCard 
                  key={auth.id} 
                  auth={auth}
                  onEdit={handleEdit}
                  onDelete={(a) => setShowDeleteConfirm(a)}
                />
              ))}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Create/Edit Dialog */}
      <AuthorizationFormDialog
        open={showForm}
        onClose={() => { setShowForm(false); setEditingAuth(null); }}
        authorization={editingAuth}
        onSave={fetchData}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!showDeleteConfirm} onOpenChange={() => setShowDeleteConfirm(null)}>
        <DialogContent className="bg-[#0A0A0F] border-[#1E293B] max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-400">
              <AlertTriangle className="w-5 h-5" />
              Eliminar Autorización
            </DialogTitle>
            <DialogDescription>
              ¿Estás seguro de eliminar la autorización de <strong>{showDeleteConfirm?.visitor_name}</strong>?
              Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteConfirm(null)} disabled={isDeleting}>
              Cancelar
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleDelete}
              disabled={isDeleting}
              data-testid="confirm-delete-btn"
            >
              {isDeleting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Trash2 className="w-4 h-4 mr-2" />}
              Eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default VisitorAuthorizationsResident;
