/**
 * GENTURIX - Mobile Bottom Navigation
 * 
 * Navegación fija inferior para dispositivos móviles (≤1023px)
 * Desktop NO se ve afectado - este componente solo se renderiza en mobile
 * 
 * Uso: Importar y usar con las props de navegación específicas por rol
 */

import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { cn } from '../../lib/utils';

// Hook para detectar si estamos en mobile
export const useIsMobile = (breakpoint = 1023) => {
  const [isMobile, setIsMobile] = React.useState(
    typeof window !== 'undefined' ? window.innerWidth <= breakpoint : false
  );

  React.useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= breakpoint);
    };

    // Check on mount
    checkMobile();

    // Listen for resize
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [breakpoint]);

  return isMobile;
};

// Componente de ítem de navegación
const NavItem = ({ item, isActive, onClick, isCenter }) => {
  const Icon = item.icon;
  
  return (
    <button
      onClick={onClick}
      data-testid={`mobile-nav-${item.id}`}
      className={cn(
        'flex flex-col items-center justify-center gap-1 transition-all duration-200',
        'min-w-[64px] py-2 px-1',
        'active:scale-95',
        isCenter ? 'relative -mt-4' : '',
        isActive 
          ? 'text-primary' 
          : 'text-muted-foreground hover:text-white'
      )}
    >
      {isCenter ? (
        // Botón central destacado (ej: Pánico)
        <div className={cn(
          'w-14 h-14 rounded-full flex items-center justify-center',
          'shadow-lg transition-all duration-200',
          item.bgColor || 'bg-red-600',
          item.glowColor || 'shadow-red-500/50',
          isActive && 'ring-2 ring-white/30 scale-105'
        )}>
          <Icon className="w-7 h-7 text-white" strokeWidth={2.5} />
        </div>
      ) : (
        <div className={cn(
          'w-12 h-12 rounded-xl flex items-center justify-center',
          'transition-all duration-200',
          isActive 
            ? 'bg-primary/20' 
            : 'bg-transparent'
        )}>
          <Icon className={cn(
            'w-6 h-6 transition-all',
            isActive ? 'text-primary' : 'text-muted-foreground'
          )} />
        </div>
      )}
      <span className={cn(
        'text-[10px] font-medium leading-none',
        isCenter && 'mt-1',
        isActive ? 'text-primary' : 'text-muted-foreground'
      )}>
        {item.label}
      </span>
    </button>
  );
};

/**
 * MobileBottomNav - Navegación inferior para móviles
 * 
 * @param {Array} items - Array de items de navegación
 * @param {string} activeTab - Tab actualmente activo
 * @param {function} onTabChange - Callback cuando cambia el tab
 * @param {number} centerIndex - Índice del botón central destacado (opcional)
 */
const MobileBottomNav = ({ 
  items, 
  activeTab, 
  onTabChange,
  centerIndex = -1 // -1 = sin botón central
}) => {
  const isMobile = useIsMobile();

  // No renderizar en desktop
  if (!isMobile) return null;

  return (
    <nav 
      className={cn(
        'fixed bottom-0 left-0 right-0 z-50',
        'bg-[#0A0A0F]/95 backdrop-blur-lg',
        'border-t border-[#1E293B]',
        'safe-area-bottom'
      )}
      data-testid="mobile-bottom-nav"
    >
      <div className="flex items-end justify-around px-2 pb-1 pt-1">
        {items.map((item, index) => (
          <NavItem
            key={item.id}
            item={item}
            isActive={activeTab === item.id}
            onClick={() => onTabChange(item.id)}
            isCenter={index === centerIndex}
          />
        ))}
      </div>
    </nav>
  );
};

export default MobileBottomNav;
