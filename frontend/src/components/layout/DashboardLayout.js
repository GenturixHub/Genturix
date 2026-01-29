import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useIsMobile } from './BottomNav';
import Sidebar from './Sidebar';
import Header from './Header';
import { 
  LayoutDashboard, 
  Users, 
  Briefcase, 
  Calendar, 
  User,
  Menu
} from 'lucide-react';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';

// Generic Admin/Dashboard Mobile Navigation
const AdminMobileNav = ({ activeRoute }) => {
  const navigate = useNavigate();
  
  const items = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
    { id: 'users', label: 'Usuarios', icon: Users, href: '/admin/users' },
    { id: 'rrhh', label: 'RRHH', icon: Briefcase, href: '/rrhh' },
    { id: 'reservations', label: 'Reservas', icon: Calendar, href: '/reservations' },
    { id: 'profile', label: 'Perfil', icon: User, href: '/profile' },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-[#0A0A0F]/95 backdrop-blur-lg border-t border-[#1E293B] safe-area-bottom">
      <div className="flex items-center justify-around px-2 py-1">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = activeRoute?.startsWith(item.href) || 
            (item.id === 'dashboard' && activeRoute === '/admin/dashboard');
          
          return (
            <button
              key={item.id}
              onClick={() => navigate(item.href)}
              className={cn(
                'flex flex-col items-center justify-center gap-1 py-2 px-3 min-w-[60px]',
                'transition-all duration-200 active:scale-95',
                isActive ? 'text-primary' : 'text-muted-foreground hover:text-white'
              )}
            >
              <div className={cn(
                'w-10 h-10 rounded-xl flex items-center justify-center',
                isActive ? 'bg-primary/20' : 'bg-transparent'
              )}>
                <Icon className={cn('w-5 h-5', isActive ? 'text-primary' : '')} />
              </div>
              <span className="text-[10px] font-medium">{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};

const DashboardLayout = ({ children, title = 'Dashboard' }) => {
  const isMobile = useIsMobile();
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Mobile layout
  if (isMobile) {
    return (
      <div className="min-h-screen bg-[#05050A] pb-20">
        {/* Mobile Header */}
        <header className="sticky top-0 z-40 bg-[#0F111A] border-b border-[#1E293B] px-4 h-14 flex items-center justify-between safe-area-top">
          <h1 className="text-lg font-semibold font-['Outfit']">{title}</h1>
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
            <Menu className="w-5 h-5" />
          </Button>
        </header>
        
        {/* Content */}
        <main className="p-4">
          {children}
        </main>
        
        {/* Bottom Navigation */}
        <AdminMobileNav activeRoute={location.pathname} />
      </div>
    );
  }

  // Desktop layout
  return (
    <div className="min-h-screen bg-[#05050A]">
      <Sidebar 
        collapsed={sidebarCollapsed} 
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} 
      />

      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      <div className={`transition-all duration-300 ${sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'}`}>
        <Header 
          onMenuClick={() => setMobileMenuOpen(!mobileMenuOpen)} 
          title={title}
        />
        
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
