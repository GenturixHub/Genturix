/**
 * GENTURIX - Mobile Bottom Navigation
 * 
 * Fixed bottom nav for mobile (<=1023px).
 * Desktop is unaffected - this component only renders on mobile.
 * Designed for 4 items max with native app feel.
 */

import React from 'react';
import { cn } from '../../lib/utils';

export const useIsMobile = (breakpoint = 1023) => {
  const [isMobile, setIsMobile] = React.useState(
    typeof window !== 'undefined' ? window.innerWidth <= breakpoint : false
  );

  React.useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth <= breakpoint);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [breakpoint]);

  return isMobile;
};

const NavItem = ({ item, isActive, onClick, isCenter }) => {
  const Icon = item.icon;
  
  return (
    <button
      onClick={onClick}
      data-testid={`mobile-nav-${item.id}`}
      className={cn(
        'flex flex-col items-center justify-center transition-all duration-150',
        'flex-1 py-2 min-h-[60px]',
        'active:scale-95 active:opacity-80',
        isCenter ? 'relative -mt-4' : '',
        isActive ? 'text-primary' : 'text-muted-foreground'
      )}
    >
      {isCenter ? (
        <div className={cn(
          'w-14 h-14 rounded-full flex items-center justify-center',
          'shadow-lg transition-all duration-200',
          item.bgColor || 'bg-red-600',
          item.glowColor || 'shadow-red-500/40',
          isActive && 'ring-2 ring-white/30 scale-105'
        )}>
          <Icon className="w-7 h-7 text-white" strokeWidth={2.5} />
        </div>
      ) : (
        <div className={cn(
          'w-11 h-11 rounded-2xl flex items-center justify-center mb-0.5',
          'transition-all duration-150',
          isActive ? 'bg-primary/15' : 'bg-transparent'
        )}>
          <Icon className={cn('w-[22px] h-[22px]', isActive ? 'text-primary' : 'text-muted-foreground')} />
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

const MobileBottomNav = ({ 
  items, 
  activeTab, 
  onTabChange,
  centerIndex = -1
}) => {
  const isMobile = useIsMobile();

  if (!isMobile) return null;

  return (
    <nav 
      className="fixed bottom-0 left-0 right-0 z-50 bg-[#0A0A0F] border-t border-[#1E293B]/60"
      data-testid="mobile-bottom-nav"
      style={{ height: '72px', paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
    >
      <div className="flex items-center justify-around h-full px-2" style={{ maxHeight: '72px' }}>
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
