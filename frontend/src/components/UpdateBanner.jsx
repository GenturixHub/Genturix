/**
 * GENTURIX - Update Banner Component
 * 
 * Shows a banner when a new Service Worker version is available.
 * Allows user to trigger the update manually.
 */

import React from 'react';
import { RefreshCw } from 'lucide-react';
import { Button } from './ui/button';

const UpdateBanner = ({ show, onUpdate, isUpdating }) => {
  if (!show) return null;

  return (
    <div 
      className="fixed left-4 right-4 z-[100] animate-in slide-in-from-bottom-4 duration-300"
      style={{ bottom: '76px' }} // Above bottom nav (70px + 6px spacing)
      data-testid="update-banner"
    >
      <div className="flex items-center justify-between gap-3 px-4 py-3 bg-[#7C3AED] rounded-xl shadow-lg shadow-purple-500/20">
        <div className="flex items-center gap-2 min-w-0">
          <RefreshCw className={`w-4 h-4 text-white flex-shrink-0 ${isUpdating ? 'animate-spin' : ''}`} />
          <span className="text-sm font-medium text-white truncate">
            Nueva versión disponible
          </span>
        </div>
        <Button
          size="sm"
          variant="secondary"
          onClick={onUpdate}
          disabled={isUpdating}
          className="flex-shrink-0 bg-white/20 hover:bg-white/30 text-white border-0 text-xs px-3 h-8"
          data-testid="update-btn"
        >
          {isUpdating ? 'Actualizando...' : 'Actualizar'}
        </Button>
      </div>
    </div>
  );
};

export default UpdateBanner;
