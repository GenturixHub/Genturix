import React, { useState } from 'react';
import { useIsMobile } from './BottomNav';
import Sidebar from './Sidebar';
import Header from './Header';
import BottomNav from './BottomNav';

const DashboardLayout = ({ children, title = 'Dashboard' }) => {
  const isMobile = useIsMobile();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Mobile layout
  if (isMobile) {
    return (
      <div className="min-h-screen bg-[#05050A] pb-16">
        {/* Mobile Header */}
        <header className="sticky top-0 z-40 bg-[#0F111A] border-b border-[#1E293B] px-4 h-14 flex items-center safe-area-top">
          <h1 className="text-lg font-semibold font-['Outfit']">{title}</h1>
        </header>
        
        {/* Content */}
        <main className="p-4">
          {children}
        </main>
        
        {/* Bottom Navigation */}
        <BottomNav />
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
