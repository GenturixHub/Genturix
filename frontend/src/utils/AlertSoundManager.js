/**
 * AlertSoundManager - Centralized alert sound control
 * 
 * Provides a single point of control for panic alert sounds.
 * Prevents multiple audio instances and ensures sound stops
 * immediately when any interaction occurs.
 * 
 * Uses BroadcastChannel + localStorage to coordinate across tabs.
 * Only ONE tab plays sound at a time.
 * 
 * Usage:
 *   import AlertSoundManager from '../utils/AlertSoundManager';
 *   AlertSoundManager.play();   // Start alert sound loop
 *   AlertSoundManager.stop();   // Stop immediately
 *   AlertSoundManager.reset();  // Stop and reset state
 */

const SOUND_LOCK_KEY = 'genturix_panic_sound_lock';
const SOUND_LOCK_TIMEOUT = 5000; // 5 seconds max lock
const BROADCAST_CHANNEL_NAME = 'genturix_alert_sound';

class AlertSoundManagerClass {
  constructor() {
    this.audioContext = null;
    this.soundInterval = null;
    this.isPlaying = false;
    this.currentOscillator = null;
    this.currentGain = null;
    this.tabId = Math.random().toString(36).substring(7);
    this.broadcastChannel = null;
    
    // Setup cross-tab communication
    if (typeof window !== 'undefined') {
      // BroadcastChannel for instant cross-tab communication
      try {
        this.broadcastChannel = new BroadcastChannel(BROADCAST_CHANNEL_NAME);
        this.broadcastChannel.onmessage = (event) => {
          if (event.data.type === 'STOP_ALL_SOUNDS') {
            console.log('[AlertSoundManager] Received stop broadcast from another tab');
            this._stopInternal();
          }
        };
      } catch (e) {
        console.warn('[AlertSoundManager] BroadcastChannel not supported');
      }
      
      // Fallback: Listen for storage events
      window.addEventListener('storage', (e) => {
        if (e.key === SOUND_LOCK_KEY) {
          const lockData = e.newValue ? JSON.parse(e.newValue) : null;
          if (!lockData || lockData.tabId !== this.tabId) {
            this._stopInternal();
          }
        }
      });
    }
  }

  /**
   * Try to acquire the sound lock (only one tab can play)
   */
  _acquireLock() {
    try {
      const existingLock = localStorage.getItem(SOUND_LOCK_KEY);
      if (existingLock) {
        const lockData = JSON.parse(existingLock);
        // Check if lock is stale (older than timeout)
        if (Date.now() - lockData.timestamp < SOUND_LOCK_TIMEOUT) {
          // Another tab has the lock and it's not stale
          console.log('[AlertSoundManager] Another tab is already playing sound');
          return false;
        }
      }
      // Acquire the lock
      localStorage.setItem(SOUND_LOCK_KEY, JSON.stringify({
        tabId: this.tabId,
        timestamp: Date.now()
      }));
      return true;
    } catch (e) {
      // localStorage might be unavailable
      return true;
    }
  }

  /**
   * Release the sound lock
   */
  _releaseLock() {
    try {
      const existingLock = localStorage.getItem(SOUND_LOCK_KEY);
      if (existingLock) {
        const lockData = JSON.parse(existingLock);
        // Only release if we own the lock
        if (lockData.tabId === this.tabId) {
          localStorage.removeItem(SOUND_LOCK_KEY);
        }
      }
    } catch (e) {
      // Ignore errors
    }
  }

  /**
   * Refresh lock timestamp to keep it alive
   */
  _refreshLock() {
    try {
      localStorage.setItem(SOUND_LOCK_KEY, JSON.stringify({
        tabId: this.tabId,
        timestamp: Date.now()
      }));
    } catch (e) {
      // Ignore errors
    }
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
      
      // Refresh lock to show we're still active
      this._refreshLock();
    } catch (e) {
      console.warn('[AlertSoundManager] Could not play sound:', e);
    }
  }

  /**
   * Start the repeating alert sound loop
   * @param {boolean} forceRestart - If true, stop and restart even if already playing
   */
  play(forceRestart = false) {
    console.log('[AlertSoundManager] play() called, forceRestart:', forceRestart, 'isPlaying:', this.isPlaying);
    
    // If force restart, stop first then continue
    if (forceRestart && this.isPlaying) {
      console.log('[AlertSoundManager] Force restart - stopping current sound');
      this._stopInternal();
      this._releaseLock();
    }
    
    // Try to acquire lock - only one tab should play
    if (!this._acquireLock()) {
      console.log('[AlertSoundManager] Skipping play - another tab has the lock');
      return;
    }
    
    if (this.isPlaying && !forceRestart) {
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
   * Internal stop without releasing lock (for cross-tab coordination)
   */
  _stopInternal() {
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
   * Stop all alert sounds immediately (across all tabs)
   */
  stop() {
    console.log('[AlertSoundManager] Stopping panic sound');
    
    this._stopInternal();
    this._releaseLock();
    
    // Broadcast stop to all other tabs via BroadcastChannel
    if (this.broadcastChannel) {
      try {
        this.broadcastChannel.postMessage({ type: 'STOP_ALL_SOUNDS' });
      } catch (e) {
        // Ignore
      }
    }
    
    // Also clear lock from localStorage to signal other tabs (fallback)
    try {
      localStorage.removeItem(SOUND_LOCK_KEY);
    } catch (e) {
      // Ignore
    }
  }

  /**
   * Reset the manager to initial state
   */
  reset() {
    this.stop();
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
