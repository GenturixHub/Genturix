/**
 * GENTURIX - Resident Visits Module
 * 
 * Wrapper component that includes:
 * - Autorizaciones (existing component)
 * - Historial (new visit history component)
 */

import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Badge } from './ui/badge';
import { Shield, History, Users } from 'lucide-react';
import VisitorAuthorizationsResident from './VisitorAuthorizationsResident';
import ResidentVisitHistory from './ResidentVisitHistory';

const ResidentVisitsModule = () => {
  const [activeSubTab, setActiveSubTab] = useState('authorizations');
  
  return (
    <div className="min-h-0 flex-1 flex flex-col overflow-hidden">
      {/* Sub-tabs navigation */}
      <Tabs value={activeSubTab} onValueChange={setActiveSubTab} className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <TabsList className="grid grid-cols-2 mx-4 mt-3 bg-[#0A0A0F] flex-shrink-0">
          <TabsTrigger 
            value="authorizations" 
            className="flex items-center gap-2 data-[state=active]:bg-primary/20"
            data-testid="visits-tab-authorizations"
          >
            <Shield className="w-4 h-4" />
            <span className="hidden sm:inline">Autorizaciones</span>
            <span className="sm:hidden">Visitas</span>
          </TabsTrigger>
          <TabsTrigger 
            value="history" 
            className="flex items-center gap-2 data-[state=active]:bg-primary/20"
            data-testid="visits-tab-history"
          >
            <History className="w-4 h-4" />
            Historial
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="authorizations" className="flex-1 mt-0 overflow-hidden">
          <VisitorAuthorizationsResident />
        </TabsContent>
        
        <TabsContent value="history" className="flex-1 mt-0 overflow-hidden">
          <ResidentVisitHistory />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ResidentVisitsModule;
