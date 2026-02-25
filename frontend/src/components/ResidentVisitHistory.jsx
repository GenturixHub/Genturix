/**
 * GENTURIX - Resident Visit History (Advanced Module)
 * 
 * Features:
 * - View visits related to resident's house
 * - Filters: Today, 7 days, 30 days, custom range, by type, by status
 * - Search: name, document, plate
 * - Export to PDF
 * - Pagination with lazy loading
 * - Mobile-first responsive design
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent } from './ui/card';
import { Input } from './ui/input';
import { Label } from './ui/label';
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { toast } from 'sonner';
import api from '../services/api';
import {
  History,
  Search,
  Filter,
  Calendar,
  Clock,
  User,
  Car,
  Package,
  Wrench,
  Sparkles,
  Users,
  CheckCircle,
  LogIn,
  LogOut,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  X,
  MoreVertical,
  RefreshCw,
  Timer,
  AlertCircle
} from 'lucide-react';

// ============================================
// CONFIGURATION - Functions that return translated config
// ============================================
const getVisitorTypes = (t) => ({
  visitor: { label: t('visitors.visitorTypes.visitor'), icon: User, color: 'bg-blue-500/20 text-blue-400' },
  delivery: { label: t('visitors.visitorTypes.delivery'), icon: Package, color: 'bg-yellow-500/20 text-yellow-400' },
  maintenance: { label: t('visitors.visitorTypes.maintenance'), icon: Wrench, color: 'bg-orange-500/20 text-orange-400' },
  technical: { label: t('visitors.visitorTypes.technical'), icon: Sparkles, color: 'bg-purple-500/20 text-purple-400' },
  cleaning: { label: t('visitors.visitorTypes.cleaning'), icon: Sparkles, color: 'bg-green-500/20 text-green-400' },
  other: { label: t('visitors.visitorTypes.other'), icon: Users, color: 'bg-gray-500/20 text-gray-400' }
});

const getStatusConfig = (t) => ({
  inside: { 
    label: t('visitors.history.active'), 
    color: 'bg-green-500/20 text-green-400 border-green-500/30',
    icon: LogIn
  },
  completed: { 
    label: t('visitors.history.completed'), 
    color: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    icon: CheckCircle
  }
});

const getFilterPeriods = (t) => [
  { value: 'today', label: t('visitors.history.periodToday') },
  { value: '7days', label: t('visitors.history.period7days') },
  { value: '30days', label: t('visitors.history.period30days') },
  { value: 'custom', label: t('visitors.history.periodCustom') }
];

// ============================================
// VISIT ENTRY CARD
// ============================================
const VisitEntryCard = ({ entry }) => {
  const visitorType = VISITOR_TYPES[entry.display_type] || VISITOR_TYPES.visitor;
  const VisitorIcon = visitorType.icon;
  const statusConfig = STATUS_CONFIG[entry.status] || STATUS_CONFIG.completed;
  const StatusIcon = statusConfig.icon;
  
  // Format duration
  const formatDuration = (minutes) => {
    if (!minutes) return null;
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };
  
  // Format time
  const formatTime = (isoString) => {
    if (!isoString) return '--:--';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '--:--';
    }
  };
  
  // Format date
  const formatDate = (isoString) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
    } catch {
      return '';
    }
  };
  
  return (
    <Card className="bg-[#0F111A] border-[#1E293B] hover:border-primary/30 transition-all">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className={`p-2.5 rounded-lg ${visitorType.color} flex-shrink-0`}>
            <VisitorIcon className="w-4 h-4" />
          </div>
          
          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="font-semibold text-white truncate">{entry.visitor_name || 'Visitante'}</p>
                <p className="text-xs text-muted-foreground">{visitorType.label}</p>
              </div>
              <Badge className={`${statusConfig.color} flex-shrink-0 text-[10px]`}>
                <StatusIcon className="w-3 h-3 mr-1" />
                {statusConfig.label}
              </Badge>
            </div>
            
            {/* Times */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs">
              <span className="flex items-center gap-1 text-muted-foreground">
                <Calendar className="w-3 h-3" />
                {formatDate(entry.entry_at)}
              </span>
              <span className="flex items-center gap-1 text-green-400">
                <LogIn className="w-3 h-3" />
                {formatTime(entry.entry_at)}
              </span>
              <span className="flex items-center gap-1 text-red-400">
                <LogOut className="w-3 h-3" />
                {formatTime(entry.exit_at)}
              </span>
              {entry.duration_minutes && (
                <span className="flex items-center gap-1 text-blue-400">
                  <Timer className="w-3 h-3" />
                  {formatDuration(entry.duration_minutes)}
                </span>
              )}
            </div>
            
            {/* Extra info */}
            {(entry.vehicle_plate || entry.document_number) && (
              <div className="flex flex-wrap gap-2 mt-2">
                {entry.vehicle_plate && (
                  <Badge variant="outline" className="text-[10px] h-5">
                    <Car className="w-3 h-3 mr-1" />
                    {entry.vehicle_plate}
                  </Badge>
                )}
                {entry.document_number && (
                  <Badge variant="outline" className="text-[10px] h-5">
                    <FileText className="w-3 h-3 mr-1" />
                    {entry.document_number}
                  </Badge>
                )}
              </div>
            )}
            
            {/* Notes */}
            {entry.notes && (
              <p className="text-xs text-muted-foreground mt-2 truncate">{entry.notes}</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// ============================================
// FILTER DIALOG
// ============================================
const FilterDialog = ({ open, onClose, filters, onApply }) => {
  const [localFilters, setLocalFilters] = useState(filters);
  
  useEffect(() => {
    setLocalFilters(filters);
  }, [filters, open]);
  
  const handleApply = () => {
    onApply(localFilters);
    onClose();
  };
  
  const handleClear = () => {
    const cleared = {
      period: '7days',
      dateFrom: '',
      dateTo: '',
      visitorType: '',
      status: ''
    };
    setLocalFilters(cleared);
    onApply(cleared);
    onClose();
  };
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-sm max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-primary" />
            Filtros
          </DialogTitle>
          <DialogDescription>
            Filtra el historial de visitas
          </DialogDescription>
        </DialogHeader>
        
        <div className="flex-1 overflow-y-auto space-y-4 py-2">
          {/* Period */}
          <div className="space-y-1.5">
            <Label className="text-xs">Período</Label>
            <Select 
              value={localFilters.period} 
              onValueChange={(v) => setLocalFilters({...localFilters, period: v})}
            >
              <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]">
                <SelectValue placeholder="Seleccionar período" />
              </SelectTrigger>
              <SelectContent>
                {FILTER_PERIODS.map(p => (
                  <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          {/* Custom Date Range */}
          {localFilters.period === 'custom' && (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Desde</Label>
                <Input
                  type="date"
                  value={localFilters.dateFrom}
                  onChange={(e) => setLocalFilters({...localFilters, dateFrom: e.target.value})}
                  className="bg-[#0A0A0F] border-[#1E293B]"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Hasta</Label>
                <Input
                  type="date"
                  value={localFilters.dateTo}
                  onChange={(e) => setLocalFilters({...localFilters, dateTo: e.target.value})}
                  className="bg-[#0A0A0F] border-[#1E293B]"
                />
              </div>
            </div>
          )}
          
          {/* Visitor Type */}
          <div className="space-y-1.5">
            <Label className="text-xs">Tipo de Visita</Label>
            <Select 
              value={localFilters.visitorType || 'all'} 
              onValueChange={(v) => setLocalFilters({...localFilters, visitorType: v === 'all' ? '' : v})}
            >
              <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]">
                <SelectValue placeholder="Todos los tipos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los tipos</SelectItem>
                {Object.entries(VISITOR_TYPES).map(([key, config]) => (
                  <SelectItem key={key} value={key}>{config.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          {/* Status */}
          <div className="space-y-1.5">
            <Label className="text-xs">Estado</Label>
            <Select 
              value={localFilters.status || 'all'} 
              onValueChange={(v) => setLocalFilters({...localFilters, status: v === 'all' ? '' : v})}
            >
              <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]">
                <SelectValue placeholder="Todos los estados" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los estados</SelectItem>
                <SelectItem value="inside">Activo (Adentro)</SelectItem>
                <SelectItem value="completed">Completado</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        
        <DialogFooter className="flex-col sm:flex-row gap-2 pt-4 border-t border-[#1E293B] flex-shrink-0">
          <Button variant="outline" onClick={handleClear} className="w-full sm:w-auto">
            Limpiar Filtros
          </Button>
          <Button onClick={handleApply} className="w-full sm:w-auto">
            <Filter className="w-4 h-4 mr-2" />
            Aplicar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ============================================
// EXPORT PDF FUNCTION
// ============================================
const generatePDF = async (exportData) => {
  // Create printable HTML content
  const visitsHtml = exportData.entries.map(entry => {
    const type = VISITOR_TYPES[entry.visitor_type] || VISITOR_TYPES.visitor;
    const formatTime = (iso) => {
      if (!iso) return '--:--';
      try {
        return new Date(iso).toLocaleString('es-ES', { 
          day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' 
        });
      } catch { return '--:--'; }
    };
    const formatDuration = (mins) => {
      if (!mins) return '-';
      if (mins < 60) return `${mins} min`;
      return `${Math.floor(mins/60)}h ${mins%60}m`;
    };
    
    return `
      <tr>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">${entry.visitor_name || 'N/A'}</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">${type.label}</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">${formatTime(entry.entry_at)}</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">${formatTime(entry.exit_at)}</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">${formatDuration(entry.duration_minutes)}</td>
        <td style="padding: 8px; border-bottom: 1px solid #ddd;">${entry.status === 'inside' ? 'Activo' : 'Completado'}</td>
      </tr>
    `;
  }).join('');
  
  const filterInfo = [];
  if (exportData.filter_applied.period) {
    const periodLabels = { today: 'Hoy', '7days': 'Últimos 7 días', '30days': 'Últimos 30 días', custom: 'Personalizado' };
    filterInfo.push(`Período: ${periodLabels[exportData.filter_applied.period] || exportData.filter_applied.period}`);
  }
  if (exportData.filter_applied.date_from) filterInfo.push(`Desde: ${exportData.filter_applied.date_from}`);
  if (exportData.filter_applied.date_to) filterInfo.push(`Hasta: ${exportData.filter_applied.date_to}`);
  
  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Historial de Visitas - GENTURIX</title>
      <style>
        body { font-family: Arial, sans-serif; padding: 20px; color: #333; }
        h1 { color: #1a1a2e; margin-bottom: 5px; }
        .subtitle { color: #666; margin-bottom: 20px; }
        .info-box { background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .info-box p { margin: 5px 0; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th { background: #1a1a2e; color: white; padding: 12px 8px; text-align: left; }
        tr:nth-child(even) { background: #f9f9f9; }
        .footer { margin-top: 30px; text-align: center; color: #999; font-size: 12px; }
      </style>
    </head>
    <body>
      <h1>📋 Historial de Visitas</h1>
      <p class="subtitle">Generado por GENTURIX</p>
      
      <div class="info-box">
        <p><strong>Residente:</strong> ${exportData.resident_name}</p>
        <p><strong>Apartamento:</strong> ${exportData.apartment}</p>
        <p><strong>Condominio:</strong> ${exportData.condominium_name}</p>
        <p><strong>Fecha de exportación:</strong> ${new Date(exportData.export_date).toLocaleString('es-ES')}</p>
        ${filterInfo.length > 0 ? `<p><strong>Filtros:</strong> ${filterInfo.join(' | ')}</p>` : ''}
        <p><strong>Total de registros:</strong> ${exportData.total_entries}</p>
      </div>
      
      <table>
        <thead>
          <tr>
            <th>Visitante</th>
            <th>Tipo</th>
            <th>Entrada</th>
            <th>Salida</th>
            <th>Duración</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          ${visitsHtml || '<tr><td colspan="6" style="text-align:center; padding: 20px;">No hay registros</td></tr>'}
        </tbody>
      </table>
      
      <div class="footer">
        <p>GENTURIX - Sistema de Gestión de Condominios</p>
      </div>
    </body>
    </html>
  `;
  
  // Open print dialog
  const printWindow = window.open('', '_blank');
  printWindow.document.write(html);
  printWindow.document.close();
  printWindow.focus();
  setTimeout(() => {
    printWindow.print();
  }, 500);
};

// ============================================
// MAIN COMPONENT
// ============================================
const ResidentVisitHistory = () => {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [pagination, setPagination] = useState(null);
  const [summary, setSummary] = useState({ total_visits: 0, visitors_inside: 0 });
  
  // Filters
  const [filters, setFilters] = useState({
    period: '7days',
    dateFrom: '',
    dateTo: '',
    visitorType: '',
    status: ''
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilterDialog, setShowFilterDialog] = useState(false);
  
  // Export
  const [exporting, setExporting] = useState(false);
  
  // Load data
  const loadData = useCallback(async (page = 1, append = false) => {
    if (page === 1) setLoading(true);
    else setLoadingMore(true);
    
    try {
      const params = {
        page,
        page_size: 20,
        filter_period: filters.period,
        search: searchQuery || undefined
      };
      
      if (filters.period === 'custom') {
        params.date_from = filters.dateFrom || undefined;
        params.date_to = filters.dateTo || undefined;
      }
      if (filters.visitorType) params.visitor_type = filters.visitorType;
      if (filters.status) params.status = filters.status;
      
      const response = await api.getResidentVisitHistory(params);
      
      if (append) {
        setEntries(prev => [...prev, ...response.entries]);
      } else {
        setEntries(response.entries);
      }
      setPagination(response.pagination);
      setSummary(response.summary);
    } catch (error) {
      console.error('Error loading visit history:', error);
      if (error.status !== 404) {
        toast.error('Error al cargar historial de visitas');
      }
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [filters, searchQuery]);
  
  // Initial load
  useEffect(() => {
    loadData();
  }, [loadData]);
  
  // Search debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      loadData();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);
  
  // Load more (pagination)
  const handleLoadMore = () => {
    if (pagination?.has_next && !loadingMore) {
      loadData(pagination.page + 1, true);
    }
  };
  
  // Apply filters
  const handleApplyFilters = (newFilters) => {
    setFilters(newFilters);
  };
  
  // Export to PDF
  const handleExport = async () => {
    setExporting(true);
    try {
      const params = {
        filter_period: filters.period
      };
      if (filters.period === 'custom') {
        params.date_from = filters.dateFrom || undefined;
        params.date_to = filters.dateTo || undefined;
      }
      if (filters.visitorType) params.visitor_type = filters.visitorType;
      if (filters.status) params.status = filters.status;
      
      const exportData = await api.exportResidentVisitHistory(params);
      await generatePDF(exportData);
      toast.success('PDF generado correctamente');
    } catch (error) {
      console.error('Error exporting:', error);
      toast.error('Error al exportar historial');
    } finally {
      setExporting(false);
    }
  };
  
  // Count active filters
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.period !== '7days') count++;
    if (filters.visitorType) count++;
    if (filters.status) count++;
    return count;
  }, [filters]);
  
  // Get period label
  const periodLabel = useMemo(() => {
    const period = FILTER_PERIODS.find(p => p.value === filters.period);
    return period?.label || 'Últimos 7 días';
  }, [filters.period]);
  
  return (
    <div className="min-h-0 flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-[#1E293B] flex-shrink-0">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <History className="w-5 h-5 text-primary" />
              Historial
            </h2>
            <p className="text-xs text-muted-foreground mt-1">
              {summary.total_visits} visitas • {summary.visitors_inside} adentro
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Refresh */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => loadData()}
              disabled={loading}
              className="h-9 w-9"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
            
            {/* Export */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={exporting || entries.length === 0}
              className="h-9"
            >
              {exporting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              <span className="hidden sm:inline ml-1.5">PDF</span>
            </Button>
          </div>
        </div>
        
        {/* Search & Filters */}
        <div className="flex items-center gap-2 mt-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Buscar por nombre, documento, placa..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-[#0A0A0F] border-[#1E293B] pl-9 h-9 text-sm"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2"
              >
                <X className="w-4 h-4 text-muted-foreground hover:text-white" />
              </button>
            )}
          </div>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilterDialog(true)}
            className="h-9 relative"
          >
            <Filter className="w-4 h-4" />
            <span className="hidden sm:inline ml-1.5">Filtros</span>
            {activeFilterCount > 0 && (
              <Badge className="absolute -top-1.5 -right-1.5 h-4 w-4 p-0 flex items-center justify-center text-[10px] bg-primary">
                {activeFilterCount}
              </Badge>
            )}
          </Button>
        </div>
        
        {/* Active filter chip */}
        <div className="flex items-center gap-2 mt-2">
          <Badge variant="outline" className="text-xs">
            <Calendar className="w-3 h-3 mr-1" />
            {periodLabel}
          </Badge>
          {filters.visitorType && (
            <Badge variant="outline" className="text-xs">
              {VISITOR_TYPES[filters.visitorType]?.label}
            </Badge>
          )}
          {filters.status && (
            <Badge variant="outline" className="text-xs">
              {STATUS_CONFIG[filters.status]?.label}
            </Badge>
          )}
        </div>
      </div>
      
      {/* Content */}
      <ScrollArea className="flex-1 h-full">
        <div className="p-4 pb-24 space-y-3">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
              <p className="text-sm text-muted-foreground">Cargando historial...</p>
            </div>
          ) : entries.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <History className="w-12 h-12 text-muted-foreground opacity-30 mb-4" />
              <p className="text-sm text-muted-foreground">No hay visitas registradas</p>
              <p className="text-xs text-muted-foreground mt-1">
                {searchQuery ? 'Intenta con otros términos de búsqueda' : 'Las visitas aparecerán aquí'}
              </p>
            </div>
          ) : (
            <>
              {entries.map((entry, index) => (
                <VisitEntryCard key={entry.id || index} entry={entry} />
              ))}
              
              {/* Load More */}
              {pagination?.has_next && (
                <div className="flex justify-center pt-4">
                  <Button
                    variant="outline"
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                    className="w-full sm:w-auto"
                  >
                    {loadingMore ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <ChevronRight className="w-4 h-4 mr-2" />
                    )}
                    Cargar más ({pagination.page}/{pagination.total_pages})
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </ScrollArea>
      
      {/* Filter Dialog */}
      <FilterDialog
        open={showFilterDialog}
        onClose={() => setShowFilterDialog(false)}
        filters={filters}
        onApply={handleApplyFilters}
      />
    </div>
  );
};

export default ResidentVisitHistory;
