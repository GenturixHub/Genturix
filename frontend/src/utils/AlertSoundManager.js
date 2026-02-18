/**
 * AlertSoundManager - Sistema Definitivo de Audio para Alertas de Pánico
 * 
 * CARACTERÍSTICAS:
 * - Singleton: Una única instancia en toda la aplicación
 * - Tab Lock: Solo una pestaña puede reproducir audio a la vez
 * - Pre-carga: Audio cargado al inicio para reproducción instantánea
 * - Loop: Reproduce en bucle hasta que se detenga manualmente
 * - Sin errores de consola: Todos los errores son silenciosos
 * - Sin múltiples instancias: Evita reproducción simultánea
 * - Visibilidad: Solo reproduce si la pestaña está visible
 * 
 * USO:
 *   AlertSoundManager.init()      - Inicializar y adquirir lock (llamar una vez)
 *   AlertSoundManager.unlock()    - Desbloquear audio (requiere gesto de usuario)
 *   AlertSoundManager.play()      - Iniciar reproducción
 *   AlertSoundManager.stop()      - Detener reproducción
 *   AlertSoundManager.cleanup()   - Limpiar al cerrar sesión
 * 
 * IMPORTANTE:
 * - Solo debe usarse en el rol Guarda
 * - Llamar init() al montar GuardUI
 * - Llamar cleanup() al desmontar GuardUI o cerrar sesión
 */

import { acquireLock, releaseLock, hasLock, refreshLock } from './GuardTabLock';

class AlertSoundManagerSingleton {
  constructor() {
    // Singleton check
    if (AlertSoundManagerSingleton.instance) {
      return AlertSoundManagerSingleton.instance;
    }
    
    // State
    this.isPlaying = false;
    this.isUnlocked = false;
    this.isInitialized = false;
    this.tabHasLock = false;
    this.audio = null;
    this.refreshInterval = null;
    
    // Store singleton instance
    AlertSoundManagerSingleton.instance = this;
  }

  /**
   * Initialize the manager and acquire tab lock
   * Call this once when GuardUI mounts
   * @returns {boolean} True if initialization successful
   */
  init() {
    if (this.isInitialized) {
      return this.tabHasLock;
    }
    
    // Try to acquire tab lock
    this.tabHasLock = acquireLock();
    
    if (this.tabHasLock) {
      // Initialize audio element
      this._initAudio();
      
      // Start refresh interval to keep lock alive
      this.refreshInterval = setInterval(() => {
        refreshLock();
      }, 10000); // Refresh every 10 seconds
    }
    
    this.isInitialized = true;
    return this.tabHasLock;
  }

  /**
   * Initialize the audio element with proper settings
   * @private
   */
  _initAudio() {
    try {
      this.audio = new Audio('/sounds/panic-alert.mp3');
      this.audio.loop = true;
      this.audio.preload = 'auto';
      this.audio.volume = 0.8;
      
      // Pre-load the audio
      this.audio.load();
      
      // Handle audio errors silently
      this.audio.onerror = () => {
        // Silent error handling
      };
      
      // Track when audio ends (shouldn't happen with loop=true)
      this.audio.onended = () => {
        this.isPlaying = false;
      };
      
      // Track when audio is paused externally
      this.audio.onpause = () => {
        this.isPlaying = false;
      };
      
    } catch (e) {
      // Silent error - audio not available
      this.audio = null;
    }
  }

  /**
   * Unlock audio playback (must be called from user gesture)
   * @returns {boolean} True if unlock was successful
   */
  unlock() {
    if (this.isUnlocked) {
      return true;
    }
    
    if (!this.audio || !this.tabHasLock) {
      return false;
    }
    
    try {
      const playPromise = this.audio.play();
      
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            this.audio.pause();
            this.audio.currentTime = 0;
            this.isUnlocked = true;
          })
          .catch(() => {
            // Silent catch
          });
      }
      
      return true;
    } catch (e) {
      return false;
    }
  }

  /**
   * Start playing the alert sound
   * Will only play if:
   * - This tab has the lock
   * - Document is visible
   * - Not already playing
   * 
   * @returns {boolean} True if playback started
   */
  play() {
    // Check tab lock
    if (!this.tabHasLock || !hasLock()) {
      this.isPlaying = false;
      return false;
    }
    
    // Check visibility
    if (document.visibilityState !== 'visible') {
      return false;
    }
    
    // Already playing
    if (this.isPlaying) {
      return true;
    }
    
    if (!this.audio) {
      return false;
    }
    
    try {
      // Reset to beginning
      this.audio.currentTime = 0;
      
      // Attempt to play
      const playPromise = this.audio.play();
      
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            this.isPlaying = true;
          })
          .catch(() => {
            this.isPlaying = false;
          });
      }
      
      return true;
    } catch (e) {
      this.isPlaying = false;
      return false;
    }
  }

  /**
   * Stop playing the alert sound
   */
  stop() {
    if (!this.audio) {
      this.isPlaying = false;
      return;
    }
    
    try {
      this.audio.pause();
      this.audio.currentTime = 0;
      this.isPlaying = false;
    } catch (e) {
      this.isPlaying = false;
    }
  }

  /**
   * Cleanup - call on logout or component unmount
   * Releases tab lock and stops audio
   */
  cleanup() {
    // Stop any playing audio
    this.stop();
    
    // Clear refresh interval
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
    
    // Release tab lock
    releaseLock();
    
    // Reset state
    this.tabHasLock = false;
    this.isInitialized = false;
    this.isUnlocked = false;
    
    // Clear audio reference
    if (this.audio) {
      this.audio.src = '';
      this.audio = null;
    }
  }

  /**
   * Check if audio is currently playing
   * @returns {boolean}
   */
  getIsPlaying() {
    return this.isPlaying;
  }

  /**
   * Check if audio has been unlocked by user gesture
   * @returns {boolean}
   */
  getIsUnlocked() {
    return this.isUnlocked;
  }

  /**
   * Check if this tab has the lock
   * @returns {boolean}
   */
  getHasLock() {
    return this.tabHasLock && hasLock();
  }
}

// Create and export the singleton instance
const AlertSoundManager = new AlertSoundManagerSingleton();

// Expose to window for debugging
if (typeof window !== 'undefined') {
  window.AlertSoundManager = AlertSoundManager;
}

export default AlertSoundManager;
