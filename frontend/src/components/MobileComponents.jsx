/**
 * GENTURIX - Responsive Table/Card Component
 * 
 * Muestra tablas en desktop y cards en mobile (≤1023px)
 * NO modifica la experiencia desktop
 */

import React from 'react';
import { useIsMobile } from './layout/BottomNav';
import { cn } from '../lib/utils';
import { MoreVertical, ChevronRight } from 'lucide-react';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';

/**
 * MobileCard - Card component for mobile data display
 * 
 * @param {string} title - Main title of the card
 * @param {string} subtitle - Secondary text
 * @param {string} status - Status badge text
 * @param {string} statusColor - Color variant for status (green, red, yellow, blue, gray)
 * @param {React.ReactNode} icon - Icon component to display
 * @param {Array} details - Array of {label, value} objects for additional info
 * @param {Array} actions - Array of {label, onClick, variant, icon} for action buttons
 * @param {function} onClick - Click handler for the entire card
 * @param {string} testId - data-testid attribute
 */
export const MobileCard = ({
  title,
  subtitle,
  status,
  statusColor = 'gray',
  icon: Icon,
  details = [],
  actions = [],
  onClick,
  testId,
  children,
  className
}) => {
  const statusColors = {
    green: 'bg-green-500/20 text-green-400 border-green-500/30',
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
    yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    gray: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  };

  return (
    <div 
      className={cn(
        'p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]',
        'transition-all duration-200',
        onClick && 'cursor-pointer active:scale-[0.98] hover:border-[#2D3B4F]',
        className
      )}
      onClick={onClick}
      data-testid={testId}
    >
      {/* Header Row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          {Icon && (
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
              <Icon className="w-5 h-5 text-primary" />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-white truncate">{title}</h3>
            {subtitle && (
              <p className="text-sm text-muted-foreground truncate">{subtitle}</p>
            )}
          </div>
        </div>
        
        {/* Status Badge or Actions Menu */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {status && (
            <span className={cn(
              'px-2 py-1 text-xs font-medium rounded-full border',
              statusColors[statusColor]
            )}>
              {status}
            </span>
          )}
          
          {actions.length > 0 && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="h-8 w-8"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreVertical className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bg-[#0F111A] border-[#1E293B]">
                {actions.map((action, idx) => (
                  <DropdownMenuItem
                    key={idx}
                    onClick={(e) => {
                      e.stopPropagation();
                      action.onClick?.();
                    }}
                    className={cn(
                      'cursor-pointer',
                      action.variant === 'destructive' && 'text-red-400 focus:text-red-400'
                    )}
                  >
                    {action.icon && <action.icon className="w-4 h-4 mr-2" />}
                    {action.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          
          {onClick && !actions.length && (
            <ChevronRight className="w-5 h-5 text-muted-foreground" />
          )}
        </div>
      </div>

      {/* Details Grid */}
      {details.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[#1E293B] grid grid-cols-2 gap-2">
          {details.map((detail, idx) => (
            <div key={idx} className="min-w-0">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wide">{detail.label}</p>
              <p className="text-sm text-white truncate">{detail.value || '-'}</p>
            </div>
          ))}
        </div>
      )}

      {/* Custom Children */}
      {children}
    </div>
  );
};

/**
 * MobileCardList - Container for mobile cards with proper spacing
 */
export const MobileCardList = ({ children, className }) => (
  <div className={cn('space-y-3', className)}>
    {children}
  </div>
);

/**
 * ResponsiveDataDisplay - Shows table on desktop, cards on mobile
 * 
 * @param {React.ReactNode} table - Table component for desktop
 * @param {React.ReactNode} cards - Cards component for mobile
 * @param {boolean} forceCards - Force card view regardless of screen size
 */
export const ResponsiveDataDisplay = ({ table, cards, forceCards = false }) => {
  const isMobile = useIsMobile();
  
  if (forceCards || isMobile) {
    return <div className="mobile-cards">{cards}</div>;
  }
  
  return <div className="desktop-table">{table}</div>;
};

/**
 * MobileActionBar - Fixed action bar at bottom of screen (above BottomNav)
 * Use for primary actions in mobile forms
 */
export const MobileActionBar = ({ children, className }) => {
  const isMobile = useIsMobile();
  
  if (!isMobile) return null;
  
  return (
    <div className={cn(
      'fixed bottom-20 left-0 right-0 z-40',
      'p-4 bg-[#0A0A0F]/95 backdrop-blur-lg',
      'border-t border-[#1E293B]',
      'safe-area-bottom',
      className
    )}>
      {children}
    </div>
  );
};

/**
 * MobileFullScreenModal - Full screen modal for mobile
 * Regular centered modal on desktop
 */
export const useMobileModalClasses = () => {
  const isMobile = useIsMobile();
  
  return {
    content: isMobile 
      ? 'fixed inset-0 w-full h-full max-w-none max-h-none rounded-none m-0 p-0 border-0'
      : '',
    overlay: isMobile ? 'bg-[#05050A]' : '',
  };
};

export default MobileCard;
