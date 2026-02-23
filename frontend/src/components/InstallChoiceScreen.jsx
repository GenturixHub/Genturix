/**
 * GENTURIX - Install Choice Screen
 * PWA install gate shown on initial load
 * 
 * Design: Minimal, dark theme matching app aesthetic
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, Globe, Shield, Zap, Bell, Smartphone } from 'lucide-react';

const InstallChoiceScreen = ({ onInstall, onContinueWeb, isInstallable }) => {
  const navigate = useNavigate();
  const [isInstalling, setIsInstalling] = useState(false);

  const handleInstall = async () => {
    setIsInstalling(true);
    try {
      const result = await onInstall();
      if (result.outcome === 'accepted') {
        // App will be installed, user may be redirected
        // Wait a moment then navigate to login
        setTimeout(() => navigate('/login'), 1500);
      } else {
        // User dismissed or error, go to login anyway
        setIsInstalling(false);
        navigate('/login');
      }
    } catch (error) {
      console.error('Install error:', error);
      setIsInstalling(false);
      navigate('/login');
    }
  };

  const handleContinueWeb = () => {
    onContinueWeb();
    navigate('/login');
  };

  return (
    <div 
      className="min-h-screen bg-[#05050A] flex flex-col items-center justify-center px-6 py-12"
      style={{ minHeight: '100dvh' }}
    >
      {/* Logo */}
      <div className="mb-8">
        <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 flex items-center justify-center shadow-2xl shadow-cyan-500/10">
          <Shield className="w-12 h-12 text-cyan-400" />
        </div>
      </div>

      {/* Title */}
      <h1 className="text-2xl font-bold text-white text-center mb-2">
        Usar Genturix como App
      </h1>
      
      {/* Subtitle */}
      <p className="text-white/50 text-center text-sm mb-8 max-w-xs leading-relaxed">
        Instala la aplicación para una experiencia más rápida y acceso instantáneo
      </p>

      {/* Benefits */}
      <div className="w-full max-w-sm space-y-3 mb-10">
        <BenefitItem 
          icon={Zap} 
          text="Acceso instantáneo desde tu pantalla de inicio" 
        />
        <BenefitItem 
          icon={Bell} 
          text="Notificaciones push de alertas en tiempo real" 
        />
        <BenefitItem 
          icon={Smartphone} 
          text="Funciona sin conexión para emergencias" 
        />
      </div>

      {/* Buttons */}
      <div className="w-full max-w-sm space-y-3">
        {/* Primary Button - Install */}
        <button
          onClick={handleInstall}
          disabled={isInstalling || !isInstallable}
          className="w-full flex items-center justify-center gap-2.5 py-4 px-6 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold text-base shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="install-app-btn"
        >
          {isInstalling ? (
            <>
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Instalando...</span>
            </>
          ) : (
            <>
              <Download className="w-5 h-5" />
              <span>Descargar App</span>
            </>
          )}
        </button>

        {/* Secondary Button - Continue Web */}
        <button
          onClick={handleContinueWeb}
          className="w-full flex items-center justify-center gap-2.5 py-4 px-6 rounded-2xl bg-white/5 border border-white/10 text-white/70 font-medium text-base hover:bg-white/10 hover:text-white transition-all duration-300"
          data-testid="continue-web-btn"
        >
          <Globe className="w-5 h-5" />
          <span>Continuar en Web</span>
        </button>
      </div>

      {/* Footer note */}
      <p className="mt-8 text-white/30 text-xs text-center max-w-xs">
        Puedes instalar la app más tarde desde el menú de tu navegador
      </p>
    </div>
  );
};

// Benefit item component
const BenefitItem = ({ icon: Icon, text }) => (
  <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/[0.03] border border-white/5">
    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center">
      <Icon className="w-4 h-4 text-cyan-400" />
    </div>
    <span className="text-sm text-white/70">{text}</span>
  </div>
);

export default InstallChoiceScreen;
