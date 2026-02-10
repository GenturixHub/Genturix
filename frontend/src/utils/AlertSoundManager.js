/**
 * AlertSoundManager - Centralized alert sound control with User Gesture Unlock
 * 
 * IMPORTANT: Browsers block audio playback without user interaction.
 * This manager requires explicit unlock via user gesture before sounds work.
 * 
 * Usage:
 *   AlertSoundManager.unlock();     // Call on user click/tap (REQUIRED FIRST)
 *   AlertSoundManager.play();       // Play alert sound (only works if unlocked)
 *   AlertSoundManager.stop();       // Stop immediately
 *   AlertSoundManager.isUnlocked(); // Check if audio is available
 */

const SOUND_LOCK_KEY = 'genturix_panic_sound_lock';
const SOUND_LOCK_TIMEOUT = 5000;
const BROADCAST_CHANNEL_NAME = 'genturix_alert_sound';
const AUDIO_UNLOCKED_KEY = 'genturix_audio_unlocked';

class AlertSoundManagerClass {
  constructor() {
    this.audioContext = null;
    this.soundInterval = null;
    this.isPlaying = false;
    this.audioUnlocked = false;
    this.currentOscillator = null;
    this.currentGain = null;
    this.tabId = Math.random().toString(36).substring(7);
    this.broadcastChannel = null;
    this.onUnlockCallbacks = [];
    
    // Check if previously unlocked in this session
    if (typeof window !== 'undefined') {
      const wasUnlocked = sessionStorage.getItem(AUDIO_UNLOCKED_KEY) === 'true';
      if (wasUnlocked) {
        // Will verify on first play attempt
        this.audioUnlocked = true;
      }
      
      // Setup cross-tab communication
      try {
        this.broadcastChannel = new BroadcastChannel(BROADCAST_CHANNEL_NAME);
        this.broadcastChannel.onmessage = (event) => {
          if (event.data.type === 'STOP_ALL_SOUNDS') {
            console.log('[AlertSound] Received stop broadcast from another tab');
            this._stopInternal();
          }
        };
      } catch (e) {
        console.warn('[AlertSound] BroadcastChannel not supported');
      }
      
      // Listen for storage events (cross-tab)
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
   * Check if audio is unlocked and ready
   */
  isUnlocked() {
    return this.audioUnlocked && this.audioContext !== null;
  }

  /**
   * Register callback for when audio gets unlocked
   */
  onUnlock(callback) {
    if (this.isUnlocked()) {
      callback();
    } else {
      this.onUnlockCallbacks.push(callback);
    }
  }

  /**
   * MUST be called from a user gesture (click/tap) to enable audio
   * Returns true if successfully unlocked
   */
  async unlock() {
    console.log('[AlertSound] unlock() called');
    
    try {
      // Create AudioContext if needed
      if (!this.audioContext) {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        console.log('[AlertSound] AudioContext created, state:', this.audioContext.state);
      }
      
      // Resume if suspended (this MUST happen during user gesture)
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
        console.log('[AlertSound] AudioContext resumed, state:', this.audioContext.state);
      }
      
      // Play a silent sound to fully unlock
      const oscillator = this.audioContext.createOscillator();
      const gainNode = this.audioContext.createGain();
      gainNode.gain.setValueAtTime(0, this.audioContext.currentTime); // Silent
      oscillator.connect(gainNode);
      gainNode.connect(this.audioContext.destination);
      oscillator.start();
      oscillator.stop(this.audioContext.currentTime + 0.001);
      
      this.audioUnlocked = true;
      sessionStorage.setItem(AUDIO_UNLOCKED_KEY, 'true');
      console.log('[AlertSound] audioUnlocked = true');
      
      // Notify callbacks
      this.onUnlockCallbacks.forEach(cb => cb());
      this.onUnlockCallbacks = [];
      
      return true;
    } catch (e) {
      console.error('[AlertSound] Failed to unlock audio:', e);
      this.audioUnlocked = false;
      return false;
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
        if (Date.now() - lockData.timestamp < SOUND_LOCK_TIMEOUT) {
          console.log('[AlertSound] Another tab is already playing');
          return false;
        }
      }
      localStorage.setItem(SOUND_LOCK_KEY, JSON.stringify({
        tabId: this.tabId,
        timestamp: Date.now()
      }));
      return true;
    } catch (e) {
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
        if (lockData.tabId === this.tabId) {
          localStorage.removeItem(SOUND_LOCK_KEY);
        }
      }
    } catch (e) {}
  }

  /**
   * Refresh lock timestamp
   */
  _refreshLock() {
    try {
      localStorage.setItem(SOUND_LOCK_KEY, JSON.stringify({
        tabId: this.tabId,
        timestamp: Date.now()
      }));
    } catch (e) {}
  }

  /**
   * Play a single alert sound burst
   */
  _playSingleBurst() {
    if (!this.audioContext || !this.audioUnlocked) {
      console.log('[AlertSound] Cannot play burst - audio not unlocked');
      return false;
    }

    try {
      // Resume if suspended
      if (this.audioContext.state === 'suspended') {
        this.audioContext.resume();
      }

      const oscillator = this.audioContext.createOscillator();
      const gainNode = this.audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(this.audioContext.destination);

      // Alert sound pattern (high-low-high-low)
      const now = this.audioContext.currentTime;
      oscillator.frequency.setValueAtTime(880, now);       // A5
      oscillator.frequency.setValueAtTime(660, now + 0.15); // E5
      oscillator.frequency.setValueAtTime(880, now + 0.3);  // A5
      oscillator.frequency.setValueAtTime(660, now + 0.45); // E5

      // Volume envelope
      gainNode.gain.setValueAtTime(0.5, now);
      gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.6);

      oscillator.type = 'square';
      oscillator.start(now);
      oscillator.stop(now + 0.6);

      this.currentOscillator = oscillator;
      this.currentGain = gainNode;
      this._refreshLock();
      
      return true;
    } catch (e) {
      console.error('[AlertSound] Error playing burst:', e);
      return false;
    }
  }

  /**
   * Start the repeating alert sound loop
   * Returns: { success: boolean, blocked: boolean }
   */
  play() {
    console.log('[AlertSound] play() called, unlocked:', this.audioUnlocked, 'isPlaying:', this.isPlaying);
    
    // Check if audio is unlocked
    if (!this.audioUnlocked || !this.audioContext) {
      console.log('[AlertSound] audio blocked by browser - needs unlock');
      return { success: false, blocked: true };
    }

    // Check tab lock
    if (!this._acquireLock()) {
      return { success: false, blocked: false };
    }
    
    if (this.isPlaying) {
      console.log('[AlertSound] Already playing');
      return { success: true, blocked: false };
    }

    console.log('[AlertSound] Starting panic sound loop');
    this.isPlaying = true;

    // Play immediately
    const firstBurst = this._playSingleBurst();
    if (!firstBurst) {
      this.isPlaying = false;
      this._releaseLock();
      return { success: false, blocked: true };
    }

    // Repeat every 2 seconds
    this.soundInterval = setInterval(() => {
      if (this.isPlaying) {
        this._playSingleBurst();
      }
    }, 2000);

    return { success: true, blocked: false };
  }

  /**
   * Internal stop without releasing lock
   */
  _stopInternal() {
    if (this.soundInterval) {
      clearInterval(this.soundInterval);
      this.soundInterval = null;
    }

    if (this.currentOscillator) {
      try {
        this.currentOscillator.stop();
      } catch (e) {}
      this.currentOscillator = null;
    }

    if (this.currentGain && this.audioContext) {
      try {
        this.currentGain.gain.setValueAtTime(0, this.audioContext.currentTime);
      } catch (e) {}
      this.currentGain = null;
    }

    this.isPlaying = false;
  }

  /**
   * Stop all alert sounds immediately
   */
  stop() {
    console.log('[AlertSound] stop() called');
    
    this._stopInternal();
    this._releaseLock();
    
    // Broadcast stop to other tabs
    if (this.broadcastChannel) {
      try {
        this.broadcastChannel.postMessage({ type: 'STOP_ALL_SOUNDS' });
      } catch (e) {}
    }
    
    try {
      localStorage.removeItem(SOUND_LOCK_KEY);
    } catch (e) {}
  }

  /**
   * Reset the manager
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

// Create singleton
const AlertSoundManager = new AlertSoundManagerClass();

// Expose globally
if (typeof window !== 'undefined') {
  window.AlertSoundManager = AlertSoundManager;
  window.stopPanicSound = () => AlertSoundManager.stop();
}

export default AlertSoundManager;
