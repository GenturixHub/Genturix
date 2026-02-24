/**
 * GENTURIX - Premium Panic Button Component
 * 
 * A premium SaaS-style panic button with:
 * - Breathing animation
 * - Haptic feedback
 * - Sound feedback
 * - Ripple effect
 * - Confirmation modal
 * - Visual state changes
 */

import React, { useState, useRef, useCallback } from 'react';
import { AlertTriangle, ShieldCheck, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// ============================================
// CONFIRMATION MODAL
// ============================================
const ConfirmationModal = ({ isOpen, onConfirm, onCancel, isLoading }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ backdropFilter: 'blur(8px)', backgroundColor: 'rgba(0,0,0,0.6)' }}
          onClick={onCancel}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="w-full max-w-sm rounded-2xl overflow-hidden"
            style={{
              background: 'linear-gradient(180deg, #1a1a1f 0%, #0f0f12 100%)',
              border: '1px solid rgba(255,255,255,0.1)',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="p-6 pb-4">
              <div className="w-14 h-14 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4">
                <AlertTriangle className="w-7 h-7 text-red-400" />
              </div>
              <h3 className="text-lg font-semibold text-white text-center mb-2">
                Confirmar Alerta
              </h3>
              <p className="text-sm text-white/50 text-center leading-relaxed">
                ¿Deseas enviar una alerta de emergencia a seguridad?
              </p>
            </div>

            {/* Buttons */}
            <div className="p-4 pt-2 flex gap-3">
              <button
                onClick={onCancel}
                disabled={isLoading}
                className="flex-1 py-3 px-4 rounded-xl text-sm font-medium text-white/70 bg-white/5 border border-white/10 hover:bg-white/10 transition-all disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={onConfirm}
                disabled={isLoading}
                className="flex-1 py-3 px-4 rounded-xl text-sm font-semibold text-white transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                style={{
                  background: 'linear-gradient(135deg, #dc2626 0%, #991b1b 100%)',
                  boxShadow: '0 4px 15px rgba(220, 38, 38, 0.3)'
                }}
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Enviando...</span>
                  </>
                ) : (
                  <span>Confirmar Alerta</span>
                )}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

// ============================================
// PREMIUM PANIC BUTTON
// ============================================
const PremiumPanicButton = ({ onTrigger, disabled = false }) => {
  const [isPressed, setIsPressed] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isActivated, setIsActivated] = useState(false);
  const [ripples, setRipples] = useState([]);
  const audioRef = useRef(null);
  const buttonRef = useRef(null);

  // Preload audio
  React.useEffect(() => {
    audioRef.current = new Audio('/soft-alert.wav');
    audioRef.current.volume = 0.3;
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  // Auto reset after activation
  React.useEffect(() => {
    if (isActivated) {
      const timer = setTimeout(() => {
        setIsActivated(false);
      }, 8000);
      return () => clearTimeout(timer);
    }
  }, [isActivated]);

  const playSound = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current.play().catch(() => {});
    }
  }, []);

  const triggerHaptic = useCallback(() => {
    if (navigator.vibrate) {
      navigator.vibrate(80);
    }
  }, []);

  const createRipple = useCallback((e) => {
    const button = buttonRef.current;
    if (!button) return;

    const rect = button.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const rippleId = Date.now();

    setRipples(prev => [...prev, { id: rippleId, x, y }]);
    setTimeout(() => {
      setRipples(prev => prev.filter(r => r.id !== rippleId));
    }, 700);
  }, []);

  const handlePress = useCallback((e) => {
    if (disabled || isLoading || isActivated) return;

    // Visual feedback
    setIsPressed(true);
    setTimeout(() => setIsPressed(false), 150);

    // Create ripple
    createRipple(e);

    // Haptic feedback
    triggerHaptic();

    // Play sound
    playSound();

    // Show confirmation modal
    setShowModal(true);
  }, [disabled, isLoading, isActivated, createRipple, triggerHaptic, playSound]);

  const handleConfirm = useCallback(async () => {
    setIsLoading(true);
    try {
      await onTrigger();
      setIsActivated(true);
      setShowModal(false);
    } catch (error) {
      console.error('Failed to send alert:', error);
    } finally {
      setIsLoading(false);
    }
  }, [onTrigger]);

  const handleCancel = useCallback(() => {
    if (!isLoading) {
      setShowModal(false);
    }
  }, [isLoading]);

  return (
    <>
      <div className="flex flex-col items-center">
        {/* Main Button */}
        <motion.button
          ref={buttonRef}
          onClick={handlePress}
          disabled={disabled || isLoading}
          animate={{
            scale: isPressed ? 0.96 : isActivated ? 1 : [1, 1.04, 1],
          }}
          transition={
            isPressed
              ? { duration: 0.1 }
              : isActivated
              ? { duration: 0 }
              : { duration: 3, repeat: Infinity, ease: 'easeInOut' }
          }
          className="relative rounded-full flex items-center justify-center overflow-hidden cursor-pointer disabled:cursor-not-allowed focus:outline-none"
          style={{
            width: 'clamp(150px, 40vw, 180px)',
            height: 'clamp(150px, 40vw, 180px)',
            background: isActivated
              ? '#dc2626'
              : 'linear-gradient(145deg, #7f1d1d, #dc2626)',
            boxShadow: isActivated
              ? '0 0 60px rgba(220, 38, 38, 0.5), 0 0 100px rgba(220, 38, 38, 0.25)'
              : '0 0 40px rgba(220, 38, 38, 0.25), 0 0 80px rgba(220, 38, 38, 0.1)',
            border: '3px solid rgba(255,255,255,0.15)',
          }}
          data-testid="premium-panic-btn"
        >
          {/* Ripple effects */}
          {ripples.map(ripple => (
            <span
              key={ripple.id}
              className="absolute rounded-full pointer-events-none"
              style={{
                left: ripple.x,
                top: ripple.y,
                width: '300px',
                height: '300px',
                marginLeft: '-150px',
                marginTop: '-150px',
                background: 'radial-gradient(circle, rgba(255,255,255,0.4) 0%, transparent 70%)',
                animation: 'ripple-expand 0.7s ease-out forwards',
              }}
            />
          ))}

          {/* Inner glow overlay */}
          <div
            className="absolute inset-0 rounded-full pointer-events-none"
            style={{
              background: 'radial-gradient(circle at 30% 30%, rgba(255,255,255,0.15) 0%, transparent 60%)',
            }}
          />

          {/* Icon */}
          {isActivated ? (
            <ShieldCheck className="w-12 h-12 text-white drop-shadow-lg" strokeWidth={2} />
          ) : (
            <AlertTriangle className="w-12 h-12 text-white drop-shadow-lg" strokeWidth={2} />
          )}
        </motion.button>

        {/* Label */}
        <motion.p
          initial={{ opacity: 0.7 }}
          animate={{ opacity: isActivated ? 1 : 0.7 }}
          className="mt-4 text-sm font-medium text-center max-w-[200px]"
          style={{ color: isActivated ? '#22c55e' : 'rgba(255,255,255,0.7)' }}
        >
          {isActivated ? 'Alerta enviada a seguridad' : 'Activar alerta de emergencia'}
        </motion.p>
      </div>

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={showModal}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
        isLoading={isLoading}
      />

      {/* Ripple animation keyframes */}
      <style>{`
        @keyframes ripple-expand {
          0% {
            transform: scale(0);
            opacity: 1;
          }
          100% {
            transform: scale(1);
            opacity: 0;
          }
        }
      `}</style>
    </>
  );
};

export default PremiumPanicButton;
