/**
 * GENTURIX - Dynamic Emergency Buttons (i18n)
 * 
 * Hierarchical emergency button system with dynamic priority selection.
 * Features:
 * - Dynamic active type switching (general/medical/security)
 * - Primary button: 150px circular with breathing animation
 * - Secondary buttons: 70px square with hover effects
 * - Smooth transitions (300ms ease)
 * - Confirmation modal for all types
 * - 8-second post-send state
 * - Full i18n support
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, Heart, Eye, ShieldCheck, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// ============================================
// EMERGENCY TYPE CONFIGURATIONS
// ============================================
const getEmergencyConfig = (t) => ({
  general: {
    id: 'emergencia_general',
    label: t('emergency.general'),
    fullLabel: t('emergency.generalFull'),
    confirmText: t('emergency.confirmGeneral'),
    icon: AlertTriangle,
    color: '#dc2626',
    gradient: 'linear-gradient(145deg, #7f1d1d, #dc2626)',
    glow: 'rgba(220, 38, 38, 0.3)',
    glowIntense: 'rgba(220, 38, 38, 0.5)',
  },
  medical: {
    id: 'emergencia_medica',
    label: t('emergency.medical'),
    fullLabel: t('emergency.medicalFull'),
    confirmText: t('emergency.confirmMedical'),
    icon: Heart,
    color: '#16a34a',
    gradient: 'linear-gradient(145deg, #14532d, #16a34a)',
    glow: 'rgba(22, 163, 74, 0.3)',
    glowIntense: 'rgba(22, 163, 74, 0.5)',
  },
  security: {
    id: 'actividad_sospechosa',
    label: t('emergency.security'),
    fullLabel: t('emergency.securityFull'),
    confirmText: t('emergency.confirmSecurity'),
    icon: Eye,
    color: '#2563eb',
    gradient: 'linear-gradient(145deg, #1e3a8a, #2563eb)',
    glow: 'rgba(37, 99, 235, 0.3)',
    glowIntense: 'rgba(37, 99, 235, 0.5)',
  },
});

// ============================================
// CONFIRMATION MODAL
// ============================================
const ConfirmationModal = ({ isOpen, onConfirm, onCancel, isLoading, config, t }) => {
  if (!config) return null;
  
  const IconComponent = config.icon;

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
          data-testid="confirmation-modal-backdrop"
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
              <div 
                className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4"
                style={{ 
                  backgroundColor: `${config.color}15`,
                  border: `1px solid ${config.color}30`
                }}
              >
                <IconComponent className="w-7 h-7" style={{ color: config.color }} />
              </div>
              <h3 className="text-lg font-semibold text-white text-center mb-2">
                {t('emergency.confirmAlert')}
              </h3>
              <p className="text-sm text-white/50 text-center leading-relaxed">
                {config.confirmText}
              </p>
            </div>

            {/* Buttons */}
            <div className="p-4 pt-2 flex gap-3">
              <button
                onClick={onCancel}
                disabled={isLoading}
                data-testid="modal-cancel-btn"
                className="flex-1 py-3 px-4 rounded-xl text-sm font-medium text-white/70 bg-white/5 border border-white/10 hover:bg-white/10 transition-all disabled:opacity-50"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={onConfirm}
                disabled={isLoading}
                data-testid="modal-confirm-btn"
                className="flex-1 py-3 px-4 rounded-xl text-sm font-semibold text-white transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                style={{
                  background: config.gradient,
                  boxShadow: `0 4px 15px ${config.glow}`
                }}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>{t('emergency.sending')}</span>
                  </>
                ) : (
                  <span>{t('common.confirm')}</span>
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
// PRIMARY BUTTON (150px circular with breathing)
// ============================================
const PrimaryButton = ({ config, onClick, disabled, isActivated, ripples }) => {
  const IconComponent = config.icon;
  const buttonRef = useRef(null);

  return (
    <motion.button
      ref={buttonRef}
      onClick={onClick}
      disabled={disabled}
      animate={{
        scale: isActivated ? 1 : [1, 1.04, 1],
      }}
      transition={
        isActivated
          ? { duration: 0 }
          : { duration: 3, repeat: Infinity, ease: 'easeInOut' }
      }
      className="relative rounded-full flex items-center justify-center overflow-hidden cursor-pointer disabled:cursor-not-allowed focus:outline-none"
      style={{
        width: '150px',
        height: '150px',
        background: isActivated ? config.color : config.gradient,
        boxShadow: isActivated
          ? `0 0 60px ${config.glowIntense}, 0 0 100px ${config.glow}`
          : `0 0 40px ${config.glow}, 0 0 80px ${config.glow}`,
        border: '3px solid rgba(255,255,255,0.15)',
      }}
      data-testid="primary-emergency-btn"
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
        <ShieldCheck className="w-10 h-10 text-white drop-shadow-lg" strokeWidth={2} />
      ) : (
        <IconComponent className="w-10 h-10 text-white drop-shadow-lg" strokeWidth={2} />
      )}
    </motion.button>
  );
};

// ============================================
// SECONDARY BUTTON (70px square)
// ============================================
const SecondaryButton = ({ config, onClick, disabled }) => {
  const IconComponent = config.icon;

  return (
    <motion.button
      onClick={onClick}
      disabled={disabled}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      className="flex flex-col items-center gap-2 cursor-pointer disabled:cursor-not-allowed focus:outline-none"
      data-testid={`secondary-btn-${config.id}`}
    >
      <motion.div
        layout
        className="rounded-xl flex items-center justify-center overflow-hidden transition-all duration-300"
        style={{
          width: '70px',
          height: '70px',
          background: `linear-gradient(135deg, ${config.color}20 0%, ${config.color}10 100%)`,
          border: `2px solid ${config.color}40`,
          boxShadow: `0 0 20px ${config.glow}`,
        }}
      >
        <IconComponent 
          className="w-6 h-6 transition-all duration-300" 
          style={{ color: config.color }} 
          strokeWidth={2} 
        />
      </motion.div>
      <span 
        className="text-xs font-medium transition-all duration-300"
        style={{ color: config.color }}
      >
        {config.label}
      </span>
    </motion.button>
  );
};

// ============================================
// MAIN COMPONENT
// ============================================
const DynamicEmergencyButtons = ({ onTrigger, disabled = false }) => {
  const { t } = useTranslation();
  const [activeType, setActiveType] = useState('general');
  const [showModal, setShowModal] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isActivated, setIsActivated] = useState(false);
  const [ripples, setRipples] = useState([]);
  const [pendingType, setPendingType] = useState(null);
  const audioRef = useRef(null);

  // Get translated config
  const EMERGENCY_CONFIG = getEmergencyConfig(t);

  // Preload audio
  useEffect(() => {
    audioRef.current = new Audio('/soft-alert.wav');
    audioRef.current.volume = 0.3;
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  // Auto reset after activation (8 seconds)
  useEffect(() => {
    if (isActivated) {
      const timer = setTimeout(() => {
        setIsActivated(false);
        setActiveType('general'); // Reset to default
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
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const rippleId = Date.now();

    setRipples(prev => [...prev, { id: rippleId, x, y }]);
    setTimeout(() => {
      setRipples(prev => prev.filter(r => r.id !== rippleId));
    }, 700);
  }, []);

  // Handle primary button click
  const handlePrimaryClick = useCallback((e) => {
    if (disabled || isLoading || isActivated) return;

    createRipple(e);
    triggerHaptic();
    playSound();
    
    setPendingType(activeType);
    setShowModal(true);
  }, [disabled, isLoading, isActivated, activeType, createRipple, triggerHaptic, playSound]);

  // Handle secondary button click - switch active type
  const handleSecondaryClick = useCallback((type) => {
    if (disabled || isLoading || isActivated) return;
    if (type === activeType) return;

    triggerHaptic();
    setActiveType(type);
  }, [disabled, isLoading, isActivated, activeType, triggerHaptic]);

  // Handle confirm
  const handleConfirm = useCallback(async () => {
    if (!pendingType) return;
    
    setIsLoading(true);
    try {
      const config = EMERGENCY_CONFIG[pendingType];
      await onTrigger(config.id);
      setIsActivated(true);
      setShowModal(false);
    } catch (error) {
      console.error('Failed to send alert:', error);
    } finally {
      setIsLoading(false);
      setPendingType(null);
    }
  }, [pendingType, onTrigger, EMERGENCY_CONFIG]);

  // Handle cancel
  const handleCancel = useCallback(() => {
    if (!isLoading) {
      setShowModal(false);
      setPendingType(null);
    }
  }, [isLoading]);

  // Get current config and secondary types
  const activeConfig = EMERGENCY_CONFIG[activeType];
  const secondaryTypes = Object.keys(EMERGENCY_CONFIG).filter(type => type !== activeType);

  return (
    <>
      <div className="flex flex-col items-center gap-6">
        {/* Primary Button with AnimatePresence for smooth transitions */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeType}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="flex flex-col items-center"
          >
            <PrimaryButton
              config={activeConfig}
              onClick={handlePrimaryClick}
              disabled={disabled || isLoading}
              isActivated={isActivated}
              ripples={ripples}
            />
            
            {/* Label */}
            <motion.p
              initial={{ opacity: 0.7 }}
              animate={{ opacity: isActivated ? 1 : 0.7 }}
              className="mt-4 text-sm font-medium text-center"
              style={{ color: isActivated ? '#22c55e' : 'rgba(255,255,255,0.7)' }}
            >
              {isActivated ? t('emergency.alertSent') : activeConfig.fullLabel}
            </motion.p>
          </motion.div>
        </AnimatePresence>

        {/* Secondary Buttons */}
        <motion.div 
          className="flex items-center justify-center gap-6"
          layout
        >
          {secondaryTypes.map((type) => (
            <SecondaryButton
              key={type}
              config={EMERGENCY_CONFIG[type]}
              onClick={() => handleSecondaryClick(type)}
              disabled={disabled || isLoading || isActivated}
            />
          ))}
        </motion.div>

        {/* Help Text */}
        <p className="text-xs text-center text-white/40 max-w-[280px]">
          {t('emergency.switchTypeHint')}
        </p>
      </div>

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={showModal}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
        isLoading={isLoading}
        config={pendingType ? EMERGENCY_CONFIG[pendingType] : null}
        t={t}
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

export default DynamicEmergencyButtons;
