/**
 * GENTURIX - Update Available Modal
 * 
 * Professional modal for PWA update notifications.
 * Displays when a new service worker version is detected.
 * Works in both web browser and installed PWA.
 */

import React from 'react';
import { RefreshCw, Sparkles, X } from 'lucide-react';
import { Button } from './ui/button';

const UpdateAvailableModal = ({ 
  isOpen, 
  onUpdate, 
  onDismiss, 
  isUpdating = false 
}) => {
  if (!isOpen) return null;

  // Prevent closing while updating
  const handleBackdropClick = () => {
    if (!isUpdating && onDismiss) {
      onDismiss();
    }
  };

  const handleCloseClick = () => {
    if (!isUpdating && onDismiss) {
      onDismiss();
    }
  };

  return (
    <>
      {/* Backdrop - Prevent closing while updating */}
      <div 
        className="fixed inset-0 z-[200] bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={handleBackdropClick}
        data-testid="update-modal-backdrop"
      />
      
      {/* Modal */}
      <div 
        className="fixed left-1/2 top-1/2 z-[201] -translate-x-1/2 -translate-y-1/2 w-[calc(100%-2rem)] max-w-sm animate-in fade-in zoom-in-95 duration-200"
        data-testid="update-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="update-modal-title"
      >
        <div className="relative overflow-hidden rounded-2xl bg-[#0F111A] border border-[#1E293B] shadow-2xl shadow-black/50">
          {/* Gradient accent top */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary via-cyan-500 to-primary" />
          
          {/* Close button - Hidden while updating */}
          {onDismiss && !isUpdating && (
            <button
              onClick={handleCloseClick}
              className="absolute top-3 right-3 p-1.5 rounded-lg text-muted-foreground hover:text-white hover:bg-white/10 transition-colors"
              data-testid="update-modal-close"
              aria-label="Cerrar"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          
          {/* Content */}
          <div className="p-6 pt-8 text-center">
            {/* Icon */}
            <div className="relative mx-auto w-16 h-16 mb-5">
              <div className="absolute inset-0 rounded-full bg-primary/20 animate-pulse" />
              <div className="relative w-full h-full rounded-full bg-gradient-to-br from-primary/30 to-cyan-500/30 border border-primary/30 flex items-center justify-center">
                {isUpdating ? (
                  <RefreshCw className="w-7 h-7 text-primary animate-spin" />
                ) : (
                  <Sparkles className="w-7 h-7 text-primary" />
                )}
              </div>
            </div>
            
            {/* Title */}
            <h2 id="update-modal-title" className="text-xl font-bold text-white mb-2">
              {isUpdating ? 'Actualizando...' : 'Nueva versión disponible'}
            </h2>
            
            {/* Description */}
            <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
              {isUpdating 
                ? 'Por favor espera mientras se aplica la actualización.'
                : 'Actualiza para continuar con la mejor experiencia y las últimas mejoras de seguridad.'
              }
            </p>
            
            {/* Buttons */}
            <div className="space-y-2.5">
              <Button
                onClick={onUpdate}
                disabled={isUpdating}
                className="w-full h-12 text-sm font-semibold bg-primary hover:bg-primary/90 transition-all disabled:opacity-70"
                data-testid="update-modal-confirm"
              >
                {isUpdating ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Aplicando actualización...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Actualizar ahora
                  </>
                )}
              </Button>
              
              {onDismiss && !isUpdating && (
                <Button
                  onClick={handleCloseClick}
                  variant="ghost"
                  className="w-full h-10 text-sm text-muted-foreground hover:text-white"
                  data-testid="update-modal-dismiss"
                >
                  Más tarde
                </Button>
              )}
            </div>
          </div>
          
          {/* Version info footer */}
          <div className="px-6 py-3 bg-[#0A0A0F] border-t border-[#1E293B]">
            <p className="text-[10px] text-muted-foreground text-center">
              {isUpdating 
                ? 'No cierres esta ventana'
                : 'La actualización se aplicará instantáneamente'
              }
            </p>
          </div>
        </div>
      </div>
    </>
  );
};

export default UpdateAvailableModal;
