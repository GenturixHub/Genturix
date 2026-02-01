/**
 * GENTURIX - Guard History Visual Component
 * 
 * Visual analytics dashboard for guard check-in activity:
 * - Bar chart showing activity by hour
 * - Summary stats (today, week, peak hours)
 * - Recent entries list
 * - Authorization type breakdown
 */

import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie
} from 'recharts';
import api from '../services/api';
import { 
  Clock, 
  UserPlus, 
  UserMinus,
  TrendingUp,
  Calendar,
  Loader2,
  RefreshCw,
  Users,
  Shield,
  Timer,
  Infinity as InfinityIcon,
  Repeat,
  ArrowUp,
  ArrowDown,
  Activity
} from 'lucide-react';

// ============================================
// HELPER FUNCTIONS
// ============================================

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
};

const formatDate = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short' });
};

// Generate hourly activity data from entries
const generateHourlyData = (entries) => {
  // Initialize all hours with 0
  const hourlyData = Array.from({ length: 24 }, (_, i) => ({
    hour: i,
    label: `${i.toString().padStart(2, '0')}:00`,
    entries: 0,
    exits: 0,
    total: 0
  }));

  entries.forEach(entry => {
    const hour = new Date(entry.timestamp).getHours();
    if (entry.type === 'visit_entry') {
      hourlyData[hour].entries++;
      hourlyData[hour].total++;
    } else if (entry.type === 'visit_exit') {
      hourlyData[hour].exits++;
      hourlyData[hour].total++;
    }
  });

  return hourlyData;
};

// Get authorization type distribution
const getAuthTypeDistribution = (entries) => {
  const distribution = {
    permanent: 0,
    recurring: 0,
    temporary: 0,
    extended: 0,
    manual: 0
  };

  entries.filter(e => e.type === 'visit_entry').forEach(entry => {
    const type = entry.authorization_type || 'manual';
    if (distribution.hasOwnProperty(type)) {
      distribution[type]++;
    } else {
      distribution.manual++;
    }
  });

  return Object.entries(distribution)
    .filter(([_, count]) => count > 0)
    .map(([type, count]) => ({
      name: type,
      value: count,
      color: {
        permanent: '#22c55e',
        recurring: '#3b82f6',
        temporary: '#eab308',
        extended: '#a855f7',
        manual: '#6b7280'
      }[type]
    }));
};

// Find peak hour
const findPeakHour = (hourlyData) => {
  const peak = hourlyData.reduce((max, current) => 
    current.total > max.total ? current : max
  , hourlyData[0]);
  return peak;
};

// ============================================
// STAT CARD COMPONENT
// ============================================
const StatCard = ({ title, value, subtitle, icon: Icon, color = 'blue', trend }) => (
  <Card className="bg-[#0A0A0F] border-[#1E293B]">
    <CardContent className="p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wider">{title}</p>
          <p className={`text-2xl font-bold text-${color}-400`}>{value}</p>
          {subtitle && (
            <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
          )}
        </div>
        <div className={`w-12 h-12 rounded-xl bg-${color}-500/20 flex items-center justify-center`}>
          <Icon className={`w-6 h-6 text-${color}-400`} />
        </div>
      </div>
      {trend !== undefined && (
        <div className={`flex items-center gap-1 mt-2 text-xs ${trend >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {trend >= 0 ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
          <span>{Math.abs(trend)}% vs ayer</span>
        </div>
      )}
    </CardContent>
  </Card>
);

// ============================================
// CHART TOOLTIP COMPONENT
// ============================================
const ChartTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#0A0A0F] border border-[#1E293B] rounded-lg p-3 shadow-xl">
        <p className="font-bold text-white">{label}</p>
        <p className="text-green-400 text-sm">
          Entradas: {payload[0]?.payload?.entries || 0}
        </p>
        <p className="text-orange-400 text-sm">
          Salidas: {payload[0]?.payload?.exits || 0}
        </p>
      </div>
    );
  }
  return null;
};

// ============================================
// HOURLY CHART COMPONENT
// ============================================
const HourlyActivityChart = ({ data, currentHour }) => {
  return (
    <Card className="bg-[#0A0A0F] border-[#1E293B]">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary" />
          Actividad por Hora
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
              <XAxis 
                dataKey="label" 
                tick={{ fill: '#64748b', fontSize: 10 }}
                tickLine={{ stroke: '#1E293B' }}
                axisLine={{ stroke: '#1E293B' }}
                interval={2}
              />
              <YAxis 
                tick={{ fill: '#64748b', fontSize: 10 }}
                tickLine={{ stroke: '#1E293B' }}
                axisLine={{ stroke: '#1E293B' }}
                allowDecimals={false}
              />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="total" radius={[4, 4, 0, 0]}>
                {data.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`}
                    fill={index === currentHour ? '#22c55e' : entry.total > 0 ? '#3b82f6' : '#1E293B'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="flex items-center justify-center gap-4 mt-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-green-500" />
            <span>Hora actual</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded bg-blue-500" />
            <span>Con actividad</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// ============================================
// AUTH TYPE PIE CHART
// ============================================
const AuthTypeChart = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <Card className="bg-[#0A0A0F] border-[#1E293B]">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Shield className="w-4 h-4 text-primary" />
            Por Tipo de Autorización
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-32 flex items-center justify-center text-muted-foreground text-sm">
            Sin datos
          </div>
        </CardContent>
      </Card>
    );
  }

  const typeLabels = {
    permanent: 'Permanente',
    recurring: 'Recurrente',
    temporary: 'Temporal',
    extended: 'Extendido',
    manual: 'Manual'
  };

  const typeIcons = {
    permanent: InfinityIcon,
    recurring: Repeat,
    temporary: Timer,
    extended: Calendar,
    manual: UserPlus
  };

  return (
    <Card className="bg-[#0A0A0F] border-[#1E293B]">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Shield className="w-4 h-4 text-primary" />
          Por Tipo de Autorización
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4">
          <div className="w-24 h-24">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={25}
                  outerRadius={40}
                  dataKey="value"
                  stroke="none"
                >
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex-1 space-y-1">
            {data.map((item, index) => {
              const Icon = typeIcons[item.name] || UserPlus;
              return (
                <div key={index} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                    <Icon className="w-3 h-3" style={{ color: item.color }} />
                    <span className="text-muted-foreground">{typeLabels[item.name]}</span>
                  </div>
                  <span className="font-medium">{item.value}</span>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// ============================================
// RECENT ENTRIES LIST
// ============================================
const RecentEntriesList = ({ entries, maxItems = 10 }) => {
  const recentEntries = entries
    .filter(e => e.type === 'visit_entry')
    .slice(0, maxItems);

  if (recentEntries.length === 0) {
    return (
      <Card className="bg-[#0A0A0F] border-[#1E293B]">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <UserPlus className="w-4 h-4 text-green-400" />
            Entradas Recientes
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground text-sm">
            No hay entradas registradas
          </div>
        </CardContent>
      </Card>
    );
  }

  const getAuthColor = (type) => {
    const colors = {
      permanent: 'green',
      recurring: 'blue',
      temporary: 'yellow',
      extended: 'purple',
      manual: 'gray'
    };
    return colors[type] || 'gray';
  };

  return (
    <Card className="bg-[#0A0A0F] border-[#1E293B]">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <UserPlus className="w-4 h-4 text-green-400" />
          Entradas Recientes ({recentEntries.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-64">
          <div className="p-4 pt-0 space-y-2">
            {recentEntries.map((entry, index) => {
              const color = getAuthColor(entry.authorization_type);
              return (
                <div 
                  key={entry.id || index}
                  className={`p-3 rounded-lg bg-${color}-500/5 border border-${color}-500/20 flex items-center gap-3`}
                >
                  <div className={`w-8 h-8 rounded-lg bg-${color}-500/20 flex items-center justify-center flex-shrink-0`}>
                    <UserPlus className={`w-4 h-4 text-${color}-400`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{entry.visitor_name}</p>
                    <p className="text-xs text-muted-foreground truncate">
                      {entry.destination || 'Sin destino'}
                      {entry.vehicle_plate && ` • 🚗 ${entry.vehicle_plate}`}
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className={`text-xs text-${color}-400 font-medium`}>
                      {formatTime(entry.timestamp)}
                    </p>
                    <Badge 
                      variant="outline" 
                      className={`text-[10px] border-${color}-500/30 text-${color}-400`}
                    >
                      {entry.is_authorized ? '✓' : '○'} {entry.authorization_type || 'manual'}
                    </Badge>
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

// ============================================
// MAIN COMPONENT
// ============================================
const GuardHistoryVisual = () => {
  const [filter, setFilter] = useState('today');
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const currentHour = new Date().getHours();

  const fetchHistory = async (showToast = false) => {
    if (showToast) setRefreshing(true);
    else setLoading(true);
    
    try {
      const data = await api.getGuardHistory();
      
      // Filter by date range
      const now = new Date();
      const filterDate = filter === 'today' 
        ? new Date(now.getFullYear(), now.getMonth(), now.getDate())
        : filter === 'week'
          ? new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
          : new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

      const filteredHistory = data.filter(h => new Date(h.timestamp) >= filterDate);
      setHistory(filteredHistory);
      
      if (showToast) {
        const entries = filteredHistory.filter(h => h.type === 'visit_entry').length;
        const exits = filteredHistory.filter(h => h.type === 'visit_exit').length;
        // toast.success(`✓ ${entries} entradas, ${exits} salidas`);
      }
    } catch (error) {
      console.error('Error fetching history:', error);
      setHistory([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [filter]);

  // Computed values
  const hourlyData = useMemo(() => generateHourlyData(history), [history]);
  const authTypeData = useMemo(() => getAuthTypeDistribution(history), [history]);
  const peakHour = useMemo(() => findPeakHour(hourlyData), [hourlyData]);
  
  const totalEntries = history.filter(h => h.type === 'visit_entry').length;
  const totalExits = history.filter(h => h.type === 'visit_exit').length;
  const authorizedCount = history.filter(h => h.type === 'visit_entry' && h.is_authorized).length;
  const authRate = totalEntries > 0 ? Math.round((authorizedCount / totalEntries) * 100) : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-3 space-y-4">
        {/* Header with filter */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-5 h-5 text-primary" />
            <Select value={filter} onValueChange={setFilter}>
              <SelectTrigger className="w-36 bg-[#0A0A0F] border-[#1E293B]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                <SelectItem value="today">Hoy</SelectItem>
                <SelectItem value="week">Últimos 7 días</SelectItem>
                <SelectItem value="month">Últimos 30 días</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => fetchHistory(true)}
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          <StatCard 
            title="Entradas" 
            value={totalEntries}
            subtitle={`${authRate}% autorizados`}
            icon={UserPlus}
            color="green"
          />
          <StatCard 
            title="Salidas" 
            value={totalExits}
            icon={UserMinus}
            color="orange"
          />
          <StatCard 
            title="Hora Pico" 
            value={peakHour.label}
            subtitle={`${peakHour.total} movimientos`}
            icon={Clock}
            color="blue"
          />
          <StatCard 
            title="Total Hoy" 
            value={totalEntries + totalExits}
            subtitle="movimientos"
            icon={Users}
            color="purple"
          />
        </div>

        {/* Hourly Activity Chart */}
        <HourlyActivityChart data={hourlyData} currentHour={currentHour} />

        {/* Two column layout for pie chart and recent entries */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <AuthTypeChart data={authTypeData} />
          <RecentEntriesList entries={history} maxItems={8} />
        </div>

        {/* Info footer */}
        <div className="text-center text-xs text-muted-foreground py-2">
          <Clock className="w-3 h-3 inline mr-1" />
          Última actualización: {new Date().toLocaleTimeString('es-ES')}
        </div>
      </div>
    </ScrollArea>
  );
};

export default GuardHistoryVisual;
