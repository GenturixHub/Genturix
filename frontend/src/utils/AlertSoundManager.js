/**
 * AlertSoundManager - Centralized alert sound control
 * 
 * Provides a single point of control for panic alert sounds.
 * Prevents multiple audio instances and ensures sound stops
 * immediately when any interaction occurs.
 * 
 * Usage:
 *   import AlertSoundManager from '../utils/AlertSoundManager';
 *   AlertSoundManager.play();   // Start alert sound loop
 *   AlertSoundManager.stop();   // Stop immediately
 *   AlertSoundManager.reset();  // Stop and reset state
 */

class AlertSoundManagerClass {
  constructor() {
    this.audioContext = null;
    this.soundInterval = null;
    this.isPlaying = false;
    this.currentOscillator = null;
    this.currentGain = null;
  }

  /**
   * Initialize audio context (must be called after user interaction)
   */
  initContext() {
    if (!this.audioContext) {
      try {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      } catch (e) {
        console.warn('[AlertSoundManager] Could not create AudioContext:', e);
      }
    }
    return this.audioContext;
  }

  /**
   * Play a single alert sound burst
   */
  playSingleBurst() {
    try {
      const ctx = this.initContext();
      if (!ctx) return;

      // Resume if suspended (browser autoplay policy)
      if (ctx.state === 'suspended') {
        ctx.resume();
      }

      // Create oscillator for alert sound
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);

      // Alert-like sound pattern (high-low-high-low)
      oscillator.frequency.setValueAtTime(880, ctx.currentTime);      // A5
      oscillator.frequency.setValueAtTime(660, ctx.currentTime + 0.15); // E5
      oscillator.frequency.setValueAtTime(880, ctx.currentTime + 0.3);  // A5
      oscillator.frequency.setValueAtTime(660, ctx.currentTime + 0.45); // E5

      // Volume envelope
      gainNode.gain.setValueAtTime(0.5, ctx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.6);

      oscillator.type = 'square';
      oscillator.start(ctx.currentTime);
      oscillator.stop(ctx.currentTime + 0.6);

      // Store references for potential immediate stop
      this.currentOscillator = oscillator;
      this.currentGain = gainNode;
    } catch (e) {
      console.warn('[AlertSoundManager] Could not play sound:', e);
    }
  }

  /**
   * Start the repeating alert sound loop
   */
  play() {
    if (this.isPlaying) {
      console.log('[AlertSoundManager] Already playing, ignoring play request');
      return;
    }

    console.log('[AlertSoundManager] Starting panic sound loop');
    this.isPlaying = true;

    // Play immediately
    this.playSingleBurst();

    // Repeat every 2 seconds
    this.soundInterval = setInterval(() => {
      if (this.isPlaying) {
        this.playSingleBurst();
      }
    }, 2000);
  }

  /**
   * Stop all alert sounds immediately
   */
  stop() {
    console.log('[AlertSoundManager] Stopping panic sound');
    
    // Clear the interval
    if (this.soundInterval) {
      clearInterval(this.soundInterval);
      this.soundInterval = null;
    }

    // Stop current oscillator if playing
    if (this.currentOscillator) {
      try {
        this.currentOscillator.stop();
      } catch (e) {
        // Oscillator may have already stopped
      }
      this.currentOscillator = null;
    }

    // Mute gain immediately
    if (this.currentGain && this.audioContext) {
      try {
        this.currentGain.gain.setValueAtTime(0, this.audioContext.currentTime);
      } catch (e) {
        // Ignore errors
      }
      this.currentGain = null;
    }

    this.isPlaying = false;
  }

  /**
   * Reset the manager to initial state
   */
  reset() {
    this.stop();
    // Optionally close audio context to free resources
    // Note: We keep it open for faster subsequent plays
  }

  /**
   * Check if sound is currently playing
   */
  getIsPlaying() {
    return this.isPlaying;
  }
}

// Create singleton instance
const AlertSoundManager = new AlertSoundManagerClass();

// Expose to window for global access (backward compatibility)
if (typeof window !== 'undefined') {
  window.AlertSoundManager = AlertSoundManager;
  // Legacy support
  window.stopPanicSound = () => AlertSoundManager.stop();
}

export default AlertSoundManager;
