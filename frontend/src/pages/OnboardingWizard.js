/**
 * GENTURIX - Onboarding Wizard for New Condominiums
 * Full-screen, step-based wizard for Super Admins
 * 
 * Steps:
 * 1. Condominium Info (name, address, country, timezone)
 * 2. Create Admin (name, email - password auto-generated)
 * 3. Enable Modules (security mandatory, others optional)
 * 4. Billing & Plan (initial_units, billing_cycle, billing_provider) - NEW
 * 5. Create Areas (if Reservations enabled)
 * 6. Summary & Confirm
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Slider } from '../components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
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
import { toast } from 'sonner';
import api from '../services/api';
import {
  Building2,
  MapPin,
  Globe,
  Clock,
  User,
  Mail,
  Shield,
  Users,
  Calendar,
  GraduationCap,
  CreditCard,
  Video,
  ChevronRight,
  ChevronLeft,
  Check,
  AlertTriangle,
  Copy,
  Loader2,
  Plus,
  Trash2,
  X,
  CheckCircle,
  Lock,
  DollarSign,
  Percent,
  Calculator,
  TrendingUp
} from 'lucide-react';

// ============================================
// CONFIGURATION
// ============================================
const STEPS = [
  { id: 1, title: 'Información', icon: Building2 },
  { id: 2, title: 'Administrador', icon: User },
  { id: 3, title: 'Módulos', icon: Shield },
  { id: 4, title: 'Plan y Facturación', icon: CreditCard },  // BILLING ENGINE INTEGRATION
  { id: 5, title: 'Áreas', icon: Calendar },
  { id: 6, title: 'Confirmar', icon: Check }
];

const BILLING_PROVIDERS = [
  { value: 'sinpe', label: 'SINPE Móvil', description: 'Pago manual via SINPE (Costa Rica)' },
  { value: 'stripe', label: 'Tarjeta de Crédito', description: 'Pago automático con Stripe' },
  { value: 'manual', label: 'Facturación Manual', description: 'El SuperAdmin gestiona los pagos' }
];

const MODULES_CONFIG = {
  security: { 
    label: 'Seguridad', 
    icon: Shield, 
    description: 'Alertas de pánico, guardias, visitantes',
    mandatory: true,
    color: 'text-green-400'
  },
  hr: { 
    label: 'Recursos Humanos', 
    icon: Users, 
    description: 'Turnos, fichaje, evaluaciones',
    mandatory: false,
    color: 'text-blue-400'
  },
  reservations: { 
    label: 'Reservaciones', 
    icon: Calendar, 
    description: 'Áreas comunes, amenidades',
    mandatory: false,
    color: 'text-cyan-400'
  },
  school: { 
    label: 'Escuela', 
    icon: GraduationCap, 
    description: 'Cursos, certificaciones',
    mandatory: false,
    color: 'text-cyan-400'
  },
  payments: { 
    label: 'Pagos', 
    icon: CreditCard, 
    description: 'Facturación, suscripciones',
    mandatory: false,
    color: 'text-yellow-400'
  },
  cctv: { 
    label: 'CCTV', 
    icon: Video, 
    description: 'Cámaras de vigilancia',
    mandatory: false,
    color: 'text-gray-400',
    comingSoon: true
  }
};

const DAYS_OF_WEEK = [
  'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'
];

const DEFAULT_AREAS = [
  { name: 'Piscina', capacity: 30 },
  { name: 'Salón de Eventos', capacity: 50 },
  { name: 'Cancha de Tenis', capacity: 4 },
  { name: 'Gimnasio', capacity: 20 },
  { name: 'Área BBQ', capacity: 15 }
];

// ============================================
// STEP COMPONENTS
// ============================================

// Country to timezone mapping for auto-selection
const COUNTRY_TIMEZONE_MAP = {
  'Costa Rica': 'America/Costa_Rica',
  'Guatemala': 'America/Guatemala',
  'Honduras': 'America/Tegucigalpa',
  'El Salvador': 'America/El_Salvador',
  'Nicaragua': 'America/Managua',
  'Panama': 'America/Panama',
  'Mexico': 'America/Mexico_City',
  'Estados Unidos': 'America/New_York',
  'Argentina': 'America/Argentina/Buenos_Aires',
  'Bolivia': 'America/La_Paz',
  'Brasil': 'America/Sao_Paulo',
  'Chile': 'America/Santiago',
  'Colombia': 'America/Bogota',
  'Ecuador': 'America/Guayaquil',
  'Paraguay': 'America/Asuncion',
  'Peru': 'America/Lima',
  'Uruguay': 'America/Montevideo',
  'Venezuela': 'America/Caracas',
  'Puerto Rico': 'America/Puerto_Rico',
  'Republica Dominicana': 'America/Santo_Domingo',
  'Cuba': 'America/Havana',
  'España': 'Europe/Madrid',
  'Portugal': 'Europe/Lisbon'
};

// Step 1: Condominium Info
const Step1CondoInfo = ({ data, onChange, timezones }) => {
  // Auto-select timezone when country changes
  const handleCountryChange = (country) => {
    const defaultTimezone = COUNTRY_TIMEZONE_MAP[country] || data.timezone;
    onChange({ ...data, country, timezone: defaultTimezone });
  };

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="name" className="text-sm font-medium flex items-center gap-2">
          <Building2 className="w-4 h-4" />
          Nombre del Condominio *
        </Label>
        <Input
          id="name"
          value={data.name}
          onChange={(e) => onChange({ ...data, name: e.target.value })}
          placeholder="Residencial Las Palmas"
          className="bg-[#0A0A0F] border-[#1E293B] h-12"
          data-testid="condo-name-input"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="address" className="text-sm font-medium flex items-center gap-2">
          <MapPin className="w-4 h-4" />
          Dirección *
        </Label>
        <Input
          id="address"
          value={data.address}
          onChange={(e) => onChange({ ...data, address: e.target.value })}
          placeholder="Av. Principal #123, Ciudad"
          className="bg-[#0A0A0F] border-[#1E293B] h-12"
          data-testid="condo-address-input"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="country" className="text-sm font-medium flex items-center gap-2">
            <Globe className="w-4 h-4" />
            País
          </Label>
          <Select value={data.country} onValueChange={handleCountryChange}>
            <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] h-12" data-testid="condo-country-select">
              <SelectValue placeholder="Seleccionar país" />
            </SelectTrigger>
            <SelectContent className="max-h-[300px]">
              {/* Centroamérica */}
              <SelectItem value="Costa Rica">Costa Rica</SelectItem>
              <SelectItem value="Guatemala">Guatemala</SelectItem>
              <SelectItem value="Honduras">Honduras</SelectItem>
              <SelectItem value="El Salvador">El Salvador</SelectItem>
              <SelectItem value="Nicaragua">Nicaragua</SelectItem>
              <SelectItem value="Panama">Panamá</SelectItem>
              {/* Norteamérica */}
              <SelectItem value="Mexico">México</SelectItem>
              <SelectItem value="Estados Unidos">Estados Unidos</SelectItem>
              {/* Sudamérica */}
              <SelectItem value="Argentina">Argentina</SelectItem>
              <SelectItem value="Bolivia">Bolivia</SelectItem>
              <SelectItem value="Brasil">Brasil</SelectItem>
              <SelectItem value="Chile">Chile</SelectItem>
              <SelectItem value="Colombia">Colombia</SelectItem>
              <SelectItem value="Ecuador">Ecuador</SelectItem>
              <SelectItem value="Paraguay">Paraguay</SelectItem>
              <SelectItem value="Peru">Perú</SelectItem>
              <SelectItem value="Uruguay">Uruguay</SelectItem>
              <SelectItem value="Venezuela">Venezuela</SelectItem>
              {/* Caribe */}
              <SelectItem value="Puerto Rico">Puerto Rico</SelectItem>
              <SelectItem value="Republica Dominicana">República Dominicana</SelectItem>
              <SelectItem value="Cuba">Cuba</SelectItem>
              {/* Europa */}
              <SelectItem value="España">España</SelectItem>
              <SelectItem value="Portugal">Portugal</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="timezone" className="text-sm font-medium flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Zona Horaria
          </Label>
          <Select value={data.timezone} onValueChange={(value) => onChange({ ...data, timezone: value })}>
            <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] h-12" data-testid="condo-timezone-select">
              <SelectValue placeholder="Seleccionar zona" />
            </SelectTrigger>
            <SelectContent>
              {timezones.map((tz) => (
                <SelectItem key={tz.value} value={tz.value}>
                  {tz.label} ({tz.offset})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
};

// Step 2: Admin Info
const Step2AdminInfo = ({ data, onChange }) => {
  return (
    <div className="space-y-6">
      <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
        <p className="text-sm text-blue-300">
          El administrador recibirá una contraseña temporal generada automáticamente.
          Deberá cambiarla en su primer inicio de sesión.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="adminName" className="text-sm font-medium flex items-center gap-2">
          <User className="w-4 h-4" />
          Nombre Completo *
        </Label>
        <Input
          id="adminName"
          value={data.full_name}
          onChange={(e) => onChange({ ...data, full_name: e.target.value })}
          placeholder="Carlos García López"
          className="bg-[#0A0A0F] border-[#1E293B] h-12"
          data-testid="admin-name-input"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="adminEmail" className="text-sm font-medium flex items-center gap-2">
          <Mail className="w-4 h-4" />
          Email *
        </Label>
        <Input
          id="adminEmail"
          type="email"
          value={data.email}
          onChange={(e) => onChange({ ...data, email: e.target.value })}
          placeholder="admin@condominio.com"
          className="bg-[#0A0A0F] border-[#1E293B] h-12"
          data-testid="admin-email-input"
        />
        <p className="text-xs text-muted-foreground">
          Este será el email de acceso y contacto principal
        </p>
      </div>
    </div>
  );
};

// Step 3: Modules
const Step3Modules = ({ data, onChange }) => {
  const toggleModule = (moduleKey) => {
    if (MODULES_CONFIG[moduleKey].mandatory || MODULES_CONFIG[moduleKey].comingSoon) return;
    onChange({ ...data, [moduleKey]: !data[moduleKey] });
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground mb-4">
        Selecciona los módulos que estarán disponibles para este condominio.
        Los módulos deshabilitados no aparecerán en la interfaz.
      </p>

      {Object.entries(MODULES_CONFIG).map(([key, config]) => {
        const IconComponent = config.icon;
        const isEnabled = data[key];
        const isMandatory = config.mandatory;
        const isComingSoon = config.comingSoon;

        return (
          <div
            key={key}
            className={`p-4 rounded-lg border transition-all ${
              isEnabled 
                ? 'bg-[#0F111A] border-primary/50' 
                : 'bg-[#0A0A0F] border-[#1E293B]'
            } ${isComingSoon ? 'opacity-50' : ''}`}
            data-testid={`module-${key}`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${isEnabled ? 'bg-primary/20' : 'bg-[#1E293B]'}`}>
                  <IconComponent className={`w-5 h-5 ${config.color}`} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{config.label}</span>
                    {isMandatory && (
                      <Badge className="bg-green-500/20 text-green-400 text-[10px]">
                        <Lock className="w-3 h-3 mr-1" />
                        Obligatorio
                      </Badge>
                    )}
                    {isComingSoon && (
                      <Badge className="bg-gray-500/20 text-gray-400 text-[10px]">
                        Próximamente
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">{config.description}</p>
                </div>
              </div>
              <Switch
                checked={isEnabled}
                onCheckedChange={() => toggleModule(key)}
                disabled={isMandatory || isComingSoon}
                data-testid={`module-switch-${key}`}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};

// Step 4: Billing & Plan (BILLING ENGINE INTEGRATION)
const Step4Billing = ({ data, onChange, billingPreview, isLoadingPreview }) => {
  return (
    <div className="space-y-6">
      {/* Explanation Banner */}
      <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
        <div className="flex items-start gap-3">
          <Calculator className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-blue-300">Modelo de Facturación por Asientos</p>
            <p className="text-xs text-blue-200/70 mt-1">
              Cada unidad habitacional o residente cuenta como un asiento facturable. 
              Define cuántos asientos necesitas para comenzar.
            </p>
          </div>
        </div>
      </div>

      {/* Initial Units (Seats) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Label className="text-sm font-medium flex items-center gap-2">
            <Users className="w-4 h-4" />
            Asientos Iniciales (Unidades) *
          </Label>
          <span className="text-2xl font-bold text-primary">{data.initial_units}</span>
        </div>
        
        <Slider
          value={[Math.min(data.initial_units, 10000)]}
          onValueChange={(value) => onChange({ ...data, initial_units: value[0] })}
          min={5}
          max={10000}
          step={5}
          className="py-4"
          data-testid="billing-units-slider"
        />
        
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>5 asientos</span>
          <span>10,000 asientos</span>
        </div>
        
        <Input
          type="number"
          value={data.initial_units}
          onChange={(e) => {
            const val = Math.min(10000, Math.max(1, parseInt(e.target.value) || 5));
            onChange({ ...data, initial_units: val });
          }}
          min={1}
          max={10000}
          className="bg-[#0A0A0F] border-[#1E293B] h-12 text-center text-lg font-bold"
          data-testid="billing-units-input"
        />
        <p className="text-xs text-muted-foreground text-center">
          Ingresa un número personalizado (1-10,000) o usa el slider
        </p>
      </div>

      {/* Custom Price Override (SuperAdmin only) */}
      <div className="space-y-2">
        <Label className="text-sm font-medium flex items-center gap-2">
          <DollarSign className="w-4 h-4" />
          Precio por Asiento (Opcional)
        </Label>
        <div className="flex items-center gap-3">
          <span className="text-muted-foreground">$</span>
          <Input
            type="number"
            step="0.01"
            min="0.01"
            max="1000"
            value={data.seat_price_override || ''}
            onChange={(e) => {
              const val = e.target.value ? parseFloat(e.target.value) : null;
              onChange({ ...data, seat_price_override: val });
            }}
            placeholder="Dejar vacío = precio global ($2.99)"
            className="bg-[#0A0A0F] border-[#1E293B] h-10 flex-1"
            data-testid="billing-price-override"
          />
          <span className="text-muted-foreground text-sm">/mes</span>
        </div>
        <p className="text-xs text-muted-foreground">
          Si está vacío, se usará el precio global. Útil para ofertas especiales.
        </p>
      </div>

      {/* Billing Cycle */}
      <div className="space-y-2">
        <Label className="text-sm font-medium flex items-center gap-2">
          <Calendar className="w-4 h-4" />
          Ciclo de Facturación
        </Label>
        <div className="grid grid-cols-2 gap-4">
          <button
            type="button"
            onClick={() => onChange({ ...data, billing_cycle: 'monthly' })}
            className={`p-4 rounded-lg border transition-all ${
              data.billing_cycle === 'monthly'
                ? 'bg-primary/20 border-primary'
                : 'bg-[#0A0A0F] border-[#1E293B] hover:border-[#3E495B]'
            }`}
            data-testid="billing-cycle-monthly"
          >
            <div className="text-sm font-medium">Mensual</div>
            <div className="text-xs text-muted-foreground mt-1">Pago cada mes</div>
          </button>
          <button
            type="button"
            onClick={() => onChange({ ...data, billing_cycle: 'yearly' })}
            className={`p-4 rounded-lg border transition-all relative ${
              data.billing_cycle === 'yearly'
                ? 'bg-green-500/20 border-green-500'
                : 'bg-[#0A0A0F] border-[#1E293B] hover:border-[#3E495B]'
            }`}
            data-testid="billing-cycle-yearly"
          >
            {data.yearly_discount_percent > 0 && (
              <Badge className="absolute -top-2 -right-2 bg-green-500 text-white text-[10px]">
                <Percent className="w-3 h-3 mr-1" />
                -{data.yearly_discount_percent}%
              </Badge>
            )}
            <div className="text-sm font-medium">Anual</div>
            <div className="text-xs text-muted-foreground mt-1">
              {data.yearly_discount_percent > 0 ? `Ahorra ${data.yearly_discount_percent}%` : 'Pago anual'}
            </div>
          </button>
        </div>
      </div>

      {/* Custom Yearly Discount (only visible when yearly selected) */}
      {data.billing_cycle === 'yearly' && (
        <div className="space-y-2">
          <Label className="text-sm font-medium flex items-center gap-2">
            <Percent className="w-4 h-4" />
            Descuento Anual Personalizado
          </Label>
          <div className="flex items-center gap-3">
            <Slider
              value={[data.yearly_discount_percent || 10]}
              onValueChange={(value) => onChange({ ...data, yearly_discount_percent: value[0] })}
              min={0}
              max={50}
              step={1}
              className="flex-1"
              data-testid="billing-discount-slider"
            />
            <span className="text-lg font-bold text-green-400 min-w-[60px] text-right">
              {data.yearly_discount_percent || 10}%
            </span>
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>0% (sin descuento)</span>
            <span>50% (máximo)</span>
          </div>
        </div>
      )}

      {/* Billing Provider */}
      <div className="space-y-2">
        <Label className="text-sm font-medium flex items-center gap-2">
          <CreditCard className="w-4 h-4" />
          Método de Pago
        </Label>
        <Select 
          value={data.billing_provider} 
          onValueChange={(value) => onChange({ ...data, billing_provider: value })}
        >
          <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] h-12" data-testid="billing-provider-select">
            <SelectValue placeholder="Seleccionar método de pago" />
          </SelectTrigger>
          <SelectContent>
            {BILLING_PROVIDERS.map((provider) => (
              <SelectItem key={provider.value} value={provider.value}>
                <div className="flex flex-col">
                  <span>{provider.label}</span>
                  <span className="text-xs text-muted-foreground">{provider.description}</span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Billing Preview Card */}
      {billingPreview && (
        <Card className="bg-gradient-to-br from-[#0F111A] to-[#1a1f2e] border-primary/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-green-400" />
              Resumen de Facturación
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {isLoadingPreview ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
              </div>
            ) : (
              <>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Precio por asiento</span>
                  <span className="font-medium">${billingPreview.price_per_seat}/mes</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Asientos</span>
                  <span className="font-medium">{billingPreview.seats}</span>
                </div>
                {billingPreview.yearly_discount_percent > 0 && billingPreview.billing_cycle === 'yearly' && (
                  <div className="flex justify-between items-center text-green-400">
                    <span className="text-sm">Descuento anual</span>
                    <span className="font-medium">-{billingPreview.yearly_discount_percent}%</span>
                  </div>
                )}
                <div className="h-px bg-[#1E293B]" />
                <div className="flex justify-between items-center">
                  <span className="font-medium">Total a pagar</span>
                  <div className="text-right">
                    <span className="text-2xl font-bold text-primary">
                      ${billingPreview.effective_amount?.toLocaleString()}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      /{billingPreview.billing_cycle === 'yearly' ? 'año' : 'mes'}
                    </span>
                  </div>
                </div>
                {billingPreview.billing_cycle === 'yearly' && billingPreview.monthly_amount && (
                  <div className="flex items-center justify-end gap-2 text-green-400">
                    <TrendingUp className="w-4 h-4" />
                    <span className="text-sm">
                      Ahorras ${((billingPreview.monthly_amount * 12) - billingPreview.effective_amount).toLocaleString()}/año
                    </span>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

// Step 5: Areas
const Step5Areas = ({ data, onChange, reservationsEnabled }) => {
  const addArea = () => {
    onChange([...data, {
      name: '',
      capacity: 10,
      requires_approval: false,
      available_days: [...DAYS_OF_WEEK],
      open_time: '08:00',
      close_time: '22:00'
    }]);
  };

  const removeArea = (index) => {
    onChange(data.filter((_, i) => i !== index));
  };

  const updateArea = (index, field, value) => {
    const updated = [...data];
    updated[index] = { ...updated[index], [field]: value };
    onChange(updated);
  };

  const addQuickArea = (preset) => {
    onChange([...data, {
      name: preset.name,
      capacity: preset.capacity,
      requires_approval: false,
      available_days: [...DAYS_OF_WEEK],
      open_time: '08:00',
      close_time: '22:00'
    }]);
  };

  if (!reservationsEnabled) {
    return (
      <div className="text-center py-12">
        <Calendar className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-30" />
        <h3 className="text-lg font-semibold mb-2">Módulo de Reservaciones no habilitado</h3>
        <p className="text-muted-foreground text-sm">
          Puedes habilitar el módulo de Reservaciones en el paso anterior para crear áreas comunes.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Crea las áreas comunes del condominio o hazlo después.
        </p>
        <Button size="sm" onClick={addArea} data-testid="add-area-btn">
          <Plus className="w-4 h-4 mr-1" />
          Agregar
        </Button>
      </div>

      {/* Quick add presets */}
      {data.length === 0 && (
        <div className="p-4 bg-[#0F111A] rounded-lg border border-[#1E293B]">
          <p className="text-sm font-medium mb-3">Agregar rápido:</p>
          <div className="flex flex-wrap gap-2">
            {DEFAULT_AREAS.map((preset) => (
              <Button
                key={preset.name}
                variant="outline"
                size="sm"
                onClick={() => addQuickArea(preset)}
                className="text-xs"
              >
                <Plus className="w-3 h-3 mr-1" />
                {preset.name}
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Areas list */}
      <div className="space-y-3 max-h-[400px] overflow-y-auto">
        {data.map((area, index) => (
          <Card key={index} className="bg-[#0F111A] border-[#1E293B]">
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">Nombre *</Label>
                    <Input
                      value={area.name}
                      onChange={(e) => updateArea(index, 'name', e.target.value)}
                      placeholder="Nombre del área"
                      className="bg-[#0A0A0F] border-[#1E293B] h-10 mt-1"
                      data-testid={`area-name-${index}`}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Capacidad *</Label>
                    <Input
                      type="number"
                      value={area.capacity}
                      onChange={(e) => updateArea(index, 'capacity', parseInt(e.target.value) || 1)}
                      min={1}
                      max={1000}
                      className="bg-[#0A0A0F] border-[#1E293B] h-10 mt-1"
                      data-testid={`area-capacity-${index}`}
                    />
                  </div>
                  <div className="flex items-center gap-2 sm:col-span-2">
                    <Switch
                      checked={area.requires_approval}
                      onCheckedChange={(checked) => updateArea(index, 'requires_approval', checked)}
                      data-testid={`area-approval-${index}`}
                    />
                    <Label className="text-xs">Requiere aprobación del admin</Label>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removeArea(index)}
                  className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                  data-testid={`remove-area-${index}`}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {data.length === 0 && (
        <p className="text-center text-sm text-muted-foreground py-4">
          No hay áreas creadas. Puedes crearlas ahora o hacerlo después desde el panel de administración.
        </p>
      )}
    </div>
  );
};

// Step 6: Summary (includes Billing info)
const Step6Summary = ({ condoData, adminData, modulesData, billingData, billingPreview, areasData }) => {
  const enabledModules = Object.entries(modulesData)
    .filter(([_, enabled]) => enabled)
    .map(([key]) => MODULES_CONFIG[key]?.label || key);

  const getBillingProviderLabel = (provider) => {
    const found = BILLING_PROVIDERS.find(p => p.value === provider);
    return found ? found.label : provider;
  };

  return (
    <div className="space-y-4">
      <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
        <div className="flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-300">Verifica la información</p>
            <p className="text-xs text-amber-200/70">
              Una vez confirmado, se creará el condominio con toda la configuración.
              Las credenciales del administrador se mostrarán una sola vez.
            </p>
          </div>
        </div>
      </div>

      {/* Condominium Info */}
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Building2 className="w-4 h-4" />
            Condominio
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Nombre:</span>
            <span className="font-medium">{condoData.name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Dirección:</span>
            <span>{condoData.address}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">País:</span>
            <span>{condoData.country}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Zona horaria:</span>
            <span>{condoData.timezone}</span>
          </div>
        </CardContent>
      </Card>

      {/* Admin Info */}
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <User className="w-4 h-4" />
            Administrador
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Nombre:</span>
            <span className="font-medium">{adminData.full_name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Email:</span>
            <span>{adminData.email}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Contraseña:</span>
            <span className="text-amber-400">Se generará automáticamente</span>
          </div>
        </CardContent>
      </Card>

      {/* Billing Info - BILLING ENGINE */}
      <Card className="bg-gradient-to-br from-[#0F111A] to-[#1a1f2e] border-green-500/30">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <CreditCard className="w-4 h-4 text-green-400" />
            Plan y Facturación
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Asientos contratados:</span>
            <span className="font-bold text-primary">{billingData.initial_units} unidades</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Ciclo de facturación:</span>
            <span className="font-medium">{billingData.billing_cycle === 'yearly' ? 'Anual' : 'Mensual'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Método de pago:</span>
            <span>{getBillingProviderLabel(billingData.billing_provider)}</span>
          </div>
          {billingPreview && (
            <>
              <div className="h-px bg-[#1E293B] my-2" />
              <div className="flex justify-between items-center">
                <span className="font-medium">Total a pagar:</span>
                <span className="text-xl font-bold text-green-400">
                  ${billingPreview.effective_amount?.toLocaleString() || '0'}
                  <span className="text-sm text-muted-foreground">
                    /{billingData.billing_cycle === 'yearly' ? 'año' : 'mes'}
                  </span>
                </span>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Modules */}
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Shield className="w-4 h-4" />
            Módulos Habilitados
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {enabledModules.map((module) => (
              <Badge key={module} className="bg-primary/20 text-primary">
                {module}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Areas */}
      {modulesData.reservations && (
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Áreas Comunes ({areasData.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {areasData.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {areasData.map((area, i) => (
                  <Badge key={i} variant="outline" className="text-xs">
                    {area.name} (Cap. {area.capacity})
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Se crearán después</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

// ============================================
// CREDENTIALS DIALOG
// ============================================
const CredentialsDialog = ({ credentials, condoName, onClose }) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    const text = `Condominio: ${condoName}\nEmail: ${credentials.email}\nContraseña: ${credentials.password}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success('Credenciales copiadas al portapapeles');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <Card className="bg-[#0F111A] border-[#1E293B] w-full max-w-md">
        <CardHeader className="text-center pb-2">
          <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>
          <CardTitle className="text-xl">¡Condominio Creado!</CardTitle>
          <CardDescription>
            {condoName} ha sido configurado exitosamente
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-bold text-red-300">
                  ¡GUARDA ESTAS CREDENCIALES AHORA!
                </p>
                <p className="text-xs text-red-200/70">
                  No se mostrarán de nuevo. El administrador deberá cambiar la contraseña en su primer acceso.
                </p>
              </div>
            </div>
          </div>

          <div className="p-4 bg-[#0A0A0F] rounded-lg border border-[#1E293B] space-y-3">
            <div>
              <Label className="text-xs text-muted-foreground">Email</Label>
              <p className="font-mono text-sm" data-testid="creds-email">{credentials.email}</p>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Contraseña Temporal</Label>
              <p className="font-mono text-sm text-amber-400" data-testid="creds-password">{credentials.password}</p>
            </div>
          </div>

          <Button
            className="w-full"
            onClick={copyToClipboard}
            data-testid="copy-credentials-btn"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 mr-2" />
                ¡Copiado!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 mr-2" />
                Copiar Credenciales
              </>
            )}
          </Button>

          <Button
            variant="outline"
            className="w-full"
            onClick={onClose}
            data-testid="close-credentials-btn"
          >
            Ir al Dashboard del Condominio
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

// ============================================
// MAIN WIZARD COMPONENT
// ============================================
const OnboardingWizard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [showCredentials, setShowCredentials] = useState(false);
  const [createdCredentials, setCreatedCredentials] = useState(null);
  const [createdCondoId, setCreatedCondoId] = useState(null);
  const [createdCondoName, setCreatedCondoName] = useState('');
  
  const [timezones, setTimezones] = useState([
    { value: 'America/Mexico_City', label: 'México (Ciudad de México)', offset: 'UTC-6' }
  ]);

  // Form state
  const [condoData, setCondoData] = useState({
    name: '',
    address: '',
    country: 'Mexico',
    timezone: 'America/Mexico_City'
  });

  const [adminData, setAdminData] = useState({
    full_name: '',
    email: ''
  });

  const [modulesData, setModulesData] = useState({
    security: true,
    hr: false,
    reservations: false,
    school: false,
    payments: false,
    cctv: false
  });

  const [areasData, setAreasData] = useState([]);

  // BILLING ENGINE: Billing state
  const [billingData, setBillingData] = useState({
    initial_units: 10,
    billing_cycle: 'monthly',
    billing_provider: 'sinpe',
    seat_price_override: null,  // Custom price per seat (optional)
    yearly_discount_percent: 10  // Default 10%, editable 0-50%
  });
  const [billingPreview, setBillingPreview] = useState(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [showEmailPreview, setShowEmailPreview] = useState(false);  // Email preview modal

  // Load timezones
  useEffect(() => {
    const loadTimezones = async () => {
      try {
        const response = await api.getOnboardingTimezones();
        setTimezones(response.timezones);
      } catch (error) {
        console.error('Error loading timezones:', error);
      }
    };
    loadTimezones();
  }, []);

  // Persist wizard state to localStorage
  useEffect(() => {
    const savedState = localStorage.getItem('onboarding_wizard_state');
    if (savedState) {
      try {
        const parsed = JSON.parse(savedState);
        setCondoData(parsed.condoData || condoData);
        setAdminData(parsed.adminData || adminData);
        setModulesData(parsed.modulesData || modulesData);
        setAreasData(parsed.areasData || areasData);
        setBillingData(parsed.billingData || billingData);
        setCurrentStep(parsed.currentStep || 1);
      } catch (e) {
        console.error('Error loading wizard state:', e);
      }
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('onboarding_wizard_state', JSON.stringify({
      condoData,
      adminData,
      modulesData,
      areasData,
      billingData,
      currentStep
    }));
  }, [condoData, adminData, modulesData, areasData, billingData, currentStep]);

  // BILLING ENGINE: Load billing preview when billing data changes
  useEffect(() => {
    const loadBillingPreview = async () => {
      if (currentStep < 4) return; // Only load when on or past billing step
      
      setIsLoadingPreview(true);
      try {
        const response = await api.getBillingPreview(billingData.initial_units, billingData.billing_cycle);
        setBillingPreview(response);
      } catch (error) {
        console.error('Error loading billing preview:', error);
        // Calculate fallback locally
        const basePrice = 1.0;
        const discount = billingData.billing_cycle === 'yearly' ? 0.15 : 0;
        const monthlyAmount = billingData.initial_units * basePrice;
        const effectiveAmount = billingData.billing_cycle === 'yearly'
          ? monthlyAmount * 12 * (1 - discount)
          : monthlyAmount;
        setBillingPreview({
          seats: billingData.initial_units,
          price_per_seat: basePrice,
          billing_cycle: billingData.billing_cycle,
          monthly_amount: monthlyAmount,
          effective_amount: effectiveAmount,
          discount_percent: discount * 100,
          savings: billingData.billing_cycle === 'yearly' ? monthlyAmount * 12 * discount : 0
        });
      } finally {
        setIsLoadingPreview(false);
      }
    };
    
    const debounceTimer = setTimeout(loadBillingPreview, 300);
    return () => clearTimeout(debounceTimer);
  }, [billingData.initial_units, billingData.billing_cycle, currentStep]);

  // Block navigation
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (currentStep > 1 && !showCredentials) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [currentStep, showCredentials]);

  // Validation
  const isStepValid = useCallback(() => {
    switch (currentStep) {
      case 1:
        return condoData.name.trim().length >= 2 && condoData.address.trim().length >= 5;
      case 2:
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return adminData.full_name.trim().length >= 2 && emailRegex.test(adminData.email);
      case 3:
        return true; // Modules always valid (security is mandatory and always on)
      case 4:
        // BILLING ENGINE: Validate billing data
        return billingData.initial_units >= 1 && billingData.initial_units <= 10000;
      case 5:
        // Areas are optional, but if added, must have valid name and capacity
        return areasData.every(area => area.name.trim().length >= 2 && area.capacity > 0);
      case 6:
        return true; // Summary step - always valid
      default:
        return false;
    }
  }, [currentStep, condoData, adminData, billingData, areasData]);

  const handleNext = () => {
    if (!isStepValid()) {
      toast.error('Por favor completa todos los campos requeridos');
      return;
    }
    
    // Skip areas step (5) if reservations not enabled, go directly to summary (6)
    if (currentStep === 4 && !modulesData.reservations) {
      setCurrentStep(6);
    } else {
      setCurrentStep(prev => Math.min(prev + 1, 6));
    }
  };

  const handleBack = () => {
    // Skip areas step (5) if reservations not enabled
    if (currentStep === 6 && !modulesData.reservations) {
      setCurrentStep(4);
    } else {
      setCurrentStep(prev => Math.max(prev - 1, 1));
    }
  };

  const handleCancel = () => {
    setShowCancelDialog(true);
  };

  const confirmCancel = () => {
    localStorage.removeItem('onboarding_wizard_state');
    navigate('/super-admin');
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    
    try {
      // Pre-validation: Check if name and email are available
      const [nameCheck, emailCheck] = await Promise.all([
        api.validateOnboardingField('name', condoData.name),
        api.validateOnboardingField('email', adminData.email)
      ]);
      
      // Handle name validation error
      if (!nameCheck.valid) {
        toast.error(nameCheck.message, { duration: 6000 });
        setCurrentStep(1); // Go back to condo info step
        setIsSubmitting(false);
        return;
      }
      
      // Handle email validation error
      if (!emailCheck.valid) {
        toast.error(emailCheck.message, { duration: 6000 });
        setCurrentStep(2); // Go back to admin step
        setIsSubmitting(false);
        return;
      }
      
      // BILLING ENGINE: All validations passed, proceed with creation including billing
      const response = await api.createCondominiumOnboarding({
        condominium: condoData,
        admin: adminData,
        modules: modulesData,
        areas: areasData,
        billing: billingData  // Include billing data
      });

      if (response.success) {
        setCreatedCredentials(response.admin_credentials);
        setCreatedCondoId(response.condominium.id);
        setCreatedCondoName(response.condominium.name);
        setShowCredentials(true);
        localStorage.removeItem('onboarding_wizard_state');
        toast.success('Condominio creado exitosamente');
      }
    } catch (error) {
      // Fallback error handling for unexpected errors
      const errorMessage = error.data?.detail || error.message || 'Error inesperado al crear el condominio';
      toast.error(errorMessage, { duration: 5000 });
      console.error('Onboarding error:', { error, condoData, adminData });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCredentialsClose = () => {
    setShowCredentials(false);
    navigate('/super-admin');
  };

  // Render current step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return <Step1CondoInfo data={condoData} onChange={setCondoData} timezones={timezones} />;
      case 2:
        return <Step2AdminInfo data={adminData} onChange={setAdminData} />;
      case 3:
        return <Step3Modules data={modulesData} onChange={setModulesData} />;
      case 4:
        return <Step4Billing data={billingData} onChange={setBillingData} billingPreview={billingPreview} isLoadingPreview={isLoadingPreview} />;
      case 5:
        return <Step5Areas data={areasData} onChange={setAreasData} reservationsEnabled={modulesData.reservations} />;
      case 6:
        return <Step6Summary condoData={condoData} adminData={adminData} modulesData={modulesData} billingData={billingData} billingPreview={billingPreview} areasData={areasData} />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-[#05050A] flex flex-col" data-testid="onboarding-wizard">
      {/* Header */}
      <header className="flex-shrink-0 p-4 border-b border-[#1E293B] bg-[#0A0A0F]">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold">Nuevo Condominio</h1>
            <p className="text-xs text-muted-foreground">Paso {currentStep} de 6</p>
          </div>
          <Button variant="ghost" size="sm" onClick={handleCancel} data-testid="cancel-wizard-btn">
            <X className="w-4 h-4 mr-1" />
            Cancelar
          </Button>
        </div>
      </header>

      {/* Progress Steps */}
      <div className="flex-shrink-0 p-4 border-b border-[#1E293B] bg-[#0A0A0F]/50">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center justify-between">
            {STEPS.map((step, index) => {
              const StepIcon = step.icon;
              const isActive = step.id === currentStep;
              const isCompleted = step.id < currentStep;
              const isSkipped = step.id === 5 && !modulesData.reservations;  // Skip Areas step if no reservations

              return (
                <React.Fragment key={step.id}>
                  <div className={`flex flex-col items-center ${isSkipped ? 'opacity-30' : ''}`}>
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                        isCompleted
                          ? 'bg-green-500 text-white'
                          : isActive
                          ? 'bg-primary text-white'
                          : 'bg-[#1E293B] text-muted-foreground'
                      }`}
                    >
                      {isCompleted ? (
                        <Check className="w-5 h-5" />
                      ) : (
                        <StepIcon className="w-5 h-5" />
                      )}
                    </div>
                    <span className={`text-[10px] mt-1 hidden sm:block ${isActive ? 'text-white' : 'text-muted-foreground'}`}>
                      {step.title}
                    </span>
                  </div>
                  {index < STEPS.length - 1 && (
                    <div
                      className={`flex-1 h-0.5 mx-2 ${
                        step.id < currentStep ? 'bg-green-500' : 'bg-[#1E293B]'
                      }`}
                    />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="flex-1 overflow-auto p-4">
        <div className="max-w-2xl mx-auto">
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {React.createElement(STEPS[currentStep - 1].icon, { className: 'w-5 h-5' })}
                {STEPS[currentStep - 1].title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {renderStepContent()}
            </CardContent>
          </Card>
        </div>
      </main>

      {/* Footer Navigation */}
      <footer className="flex-shrink-0 p-4 border-t border-[#1E293B] bg-[#0A0A0F]">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <Button
            variant="outline"
            onClick={handleBack}
            disabled={currentStep === 1}
            data-testid="wizard-back-btn"
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Anterior
          </Button>

          {currentStep < 6 ? (
            <Button
              onClick={handleNext}
              disabled={!isStepValid()}
              data-testid="wizard-next-btn"
            >
              Siguiente
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="bg-green-600 hover:bg-green-700"
              data-testid="wizard-submit-btn"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creando...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4 mr-2" />
                  Crear Condominio
                </>
              )}
            </Button>
          )}
        </div>
      </footer>

      {/* Cancel Confirmation Dialog */}
      <AlertDialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <AlertDialogContent className="bg-[#0F111A] border-[#1E293B]">
          <AlertDialogHeader>
            <AlertDialogTitle>¿Cancelar onboarding?</AlertDialogTitle>
            <AlertDialogDescription>
              Si cancelas ahora, perderás todo el progreso del wizard.
              El condominio no será creado.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Continuar Editando</AlertDialogCancel>
            <AlertDialogAction onClick={confirmCancel} className="bg-red-600 hover:bg-red-700">
              Sí, Cancelar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Credentials Dialog */}
      {showCredentials && createdCredentials && (
        <CredentialsDialog
          credentials={createdCredentials}
          condoName={createdCondoName}
          onClose={handleCredentialsClose}
        />
      )}
    </div>
  );
};

export default OnboardingWizard;
