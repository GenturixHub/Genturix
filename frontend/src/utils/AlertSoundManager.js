/**
 * AlertSoundManager - Sistema Definitivo de Audio para Alertas de Pánico
 * 
 * CARACTERÍSTICAS:
 * - Singleton: Una única instancia en toda la aplicación
 * - Pre-carga: Audio cargado al inicio para reproducción instantánea
 * - Loop: Reproduce en bucle hasta que se detenga manualmente
 * - Sin errores de consola: Todos los errores son silenciosos
 * - Sin múltiples instancias: Evita reproducción simultánea
 * - Independiente del Service Worker: No depende de visibilityState
 * 
 * USO:
 *   AlertSoundManager.unlock()  - Desbloquear audio (requiere gesto de usuario)
 *   AlertSoundManager.play()    - Iniciar reproducción
 *   AlertSoundManager.stop()    - Detener reproducción
 * 
 * IMPORTANTE:
 * - Solo debe usarse en el rol Guarda
 * - Llamar unlock() en el primer click/touch del usuario
 */

class AlertSoundManagerSingleton {
  constructor() {
    // Singleton check
    if (AlertSoundManagerSingleton.instance) {
      return AlertSoundManagerSingleton.instance;
    }
    
    // State
    this.isPlaying = false;
    this.isUnlocked = false;
    this.audio = null;
    
    // Initialize audio element
    this._initAudio();
    
    // Store singleton instance
    AlertSoundManagerSingleton.instance = this;
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
        // Silent error handling - do not log
      };
      
      // Track when audio ends (shouldn't happen with loop=true, but safety)
      this.audio.onended = () => {
        this.isPlaying = false;
      };
      
      // Track when audio is paused externally
      this.audio.onpause = () => {
        if (this.isPlaying) {
          this.isPlaying = false;
        }
      };
      
    } catch (e) {
      // Silent error - audio not available
      this.audio = null;
    }
  }

  /**
   * Unlock audio playback (must be called from user gesture)
   * Browsers require user interaction before allowing audio playback.
   * Call this on first click/touch event.
   * 
   * @returns {boolean} True if unlock was successful
   */
  unlock() {
    if (this.isUnlocked) {
      return true;
    }
    
    if (!this.audio) {
      return false;
    }
    
    try {
      // Play and immediately pause to unlock audio context
      const playPromise = this.audio.play();
      
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            this.audio.pause();
            this.audio.currentTime = 0;
            this.isUnlocked = true;
          })
          .catch(() => {
            // Silent catch - autoplay not allowed yet
          });
      }
      
      return true;
    } catch (e) {
      // Silent error
      return false;
    }
  }

  /**
   * Start playing the alert sound
   * Will loop until stop() is called
   * 
   * @returns {boolean} True if playback started successfully
   */
  play() {
    // Already playing - do nothing
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
            // Silent catch - autoplay blocked
            // User needs to click unlock banner
            this.isPlaying = false;
          });
      }
      
      return true;
    } catch (e) {
      // Silent error
      return false;
    }
  }

  /**
   * Stop playing the alert sound
   */
  stop() {
    if (!this.audio) {
      return;
    }
    
    try {
      this.audio.pause();
      this.audio.currentTime = 0;
      this.isPlaying = false;
    } catch (e) {
      // Silent error
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
   * Force re-initialization of audio (use if audio gets corrupted)
   */
  reset() {
    this.stop();
    this._initAudio();
    this.isUnlocked = false;
  }
}

// Create and export the singleton instance
const AlertSoundManager = new AlertSoundManagerSingleton();

// Expose to window for debugging (optional, can be removed in production)
if (typeof window !== 'undefined') {
  window.AlertSoundManager = AlertSoundManager;
}

export default AlertSoundManager;
