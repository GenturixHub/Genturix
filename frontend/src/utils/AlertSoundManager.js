/**
 * AlertSoundManager v3 - Reliable Panic Sound with Proper Web Audio API Usage
 * 
 * Key principles:
 * - NEVER reuse AudioBufferSourceNode (Web Audio API requirement)
 * - Create NEW oscillator for EACH play request
 * - Restart sound on new alert (don't block)
 * - Clear state on stop/end
 */

const SOUND_LOCK_KEY = 'genturix_panic_sound_lock';
const SOUND_LOCK_TIMEOUT = 5000;
const BROADCAST_CHANNEL_NAME = 'genturix_alert_sound';
const AUDIO_UNLOCKED_KEY = 'genturix_audio_unlocked';

class AlertSoundManagerClass {
  constructor() {
    this.audioContext = null;
    this.audioUnlocked = false;
    this.isPlaying = false;
    this.soundLoopInterval = null;
    this.currentOscillators = []; // Track all active oscillators
    this.tabId = Math.random().toString(36).substring(7);
    this.broadcastChannel = null;
    this.onUnlockCallbacks = [];
    
    // Check if previously unlocked in this session
    if (typeof window !== 'undefined') {
      const wasUnlocked = sessionStorage.getItem(AUDIO_UNLOCKED_KEY) === 'true';
      if (wasUnlocked) {
        this.audioUnlocked = true;
      }
      
      // Setup cross-tab communication
      try {
        this.broadcastChannel = new BroadcastChannel(BROADCAST_CHANNEL_NAME);
        this.broadcastChannel.onmessage = (event) => {
          if (event.data.type === 'STOP_ALL_SOUNDS') {
            console.log('[AlertSound] Received stop broadcast');
            this._stopInternal();
          }
        };
      } catch (e) {
        console.warn('[AlertSound] BroadcastChannel not supported');
      }
      
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
   * Check if audio is unlocked
   */
  isUnlocked() {
    return this.audioUnlocked && this.audioContext !== null;
  }

  /**
   * Register callback for unlock
   */
  onUnlock(callback) {
    if (this.isUnlocked()) {
      callback();
    } else {
      this.onUnlockCallbacks.push(callback);
    }
  }

  /**
   * Unlock audio - MUST be called from user gesture
   */
  async unlock() {
    console.log('[AlertSound] unlock() called');
    
    try {
      if (!this.audioContext) {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        console.log('[AlertSound] AudioContext created, state:', this.audioContext.state);
      }
      
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
        console.log('[AlertSound] AudioContext resumed');
      }
      
      // Play silent sound to fully unlock
      const osc = this.audioContext.createOscillator();
      const gain = this.audioContext.createGain();
      gain.gain.setValueAtTime(0, this.audioContext.currentTime);
      osc.connect(gain);
      gain.connect(this.audioContext.destination);
      osc.start();
      osc.stop(this.audioContext.currentTime + 0.001);
      
      this.audioUnlocked = true;
      sessionStorage.setItem(AUDIO_UNLOCKED_KEY, 'true');
      console.log('[AlertSound] audioUnlocked = true');
      
      this.onUnlockCallbacks.forEach(cb => cb());
      this.onUnlockCallbacks = [];
      
      return true;
    } catch (e) {
      console.error('[AlertSound] unlock failed:', e);
      return false;
    }
  }

  /**
   * Try to acquire cross-tab lock
   */
  _acquireLock() {
    try {
      const existing = localStorage.getItem(SOUND_LOCK_KEY);
      if (existing) {
        const data = JSON.parse(existing);
        if (Date.now() - data.timestamp < SOUND_LOCK_TIMEOUT && data.tabId !== this.tabId) {
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
   * Release lock
   */
  _releaseLock() {
    try {
      const existing = localStorage.getItem(SOUND_LOCK_KEY);
      if (existing) {
        const data = JSON.parse(existing);
        if (data.tabId === this.tabId) {
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
   * Create and play a NEW oscillator burst (NEVER reuse)
   */
  _createAndPlayBurst() {
    if (!this.audioContext || !this.audioUnlocked) {
      console.log('[AlertSound] Cannot play - not unlocked');
      return null;
    }

    try {
      // Resume if needed
      if (this.audioContext.state === 'suspended') {
        this.audioContext.resume();
      }

      console.log('[AlertSound] Creating new oscillator');
      
      // Create NEW oscillator (required by Web Audio API)
      const oscillator = this.audioContext.createOscillator();
      const gainNode = this.audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(this.audioContext.destination);

      // Alert pattern
      const now = this.audioContext.currentTime;
      oscillator.frequency.setValueAtTime(880, now);
      oscillator.frequency.setValueAtTime(660, now + 0.15);
      oscillator.frequency.setValueAtTime(880, now + 0.3);
      oscillator.frequency.setValueAtTime(660, now + 0.45);

      gainNode.gain.setValueAtTime(0.5, now);
      gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.6);

      oscillator.type = 'square';
      
      // Track this oscillator
      this.currentOscillators.push(oscillator);
      
      // Clean up when done
      oscillator.onended = () => {
        const idx = this.currentOscillators.indexOf(oscillator);
        if (idx > -1) {
          this.currentOscillators.splice(idx, 1);
        }
      };

      oscillator.start(now);
      oscillator.stop(now + 0.6);
      
      this._refreshLock();
      console.log('[AlertSound] Sound burst started');
      
      return oscillator;
    } catch (e) {
      console.error('[AlertSound] Error creating burst:', e);
      return null;
    }
  }

  /**
   * Stop all current sounds
   */
  _stopInternal() {
    console.log('[AlertSound] _stopInternal called');
    
    // Stop the loop
    if (this.soundLoopInterval) {
      clearInterval(this.soundLoopInterval);
      this.soundLoopInterval = null;
    }

    // Stop all active oscillators
    this.currentOscillators.forEach(osc => {
      try {
        osc.stop();
      } catch (e) {}
    });
    this.currentOscillators = [];

    this.isPlaying = false;
    console.log('[AlertSound] Sound stopped, isPlaying = false');
  }

  /**
   * Play alert sound - ALWAYS restarts if already playing
   * Returns: { success: boolean, blocked: boolean }
   */
  play() {
    console.log('[AlertSound] play() called, unlocked:', this.audioUnlocked, 'isPlaying:', this.isPlaying);
    
    // Check unlock
    if (!this.audioUnlocked || !this.audioContext) {
      console.log('[AlertSound] Blocked - needs unlock');
      return { success: false, blocked: true };
    }

    // Check tab lock
    if (!this._acquireLock()) {
      console.log('[AlertSound] Another tab is playing');
      return { success: false, blocked: false };
    }

    // IMPORTANT: If already playing, stop first then restart
    if (this.isPlaying) {
      console.log('[AlertSound] Stopping previous sound to restart');
      this._stopInternal();
    }

    console.log('[AlertSound] Starting panic sound loop');
    this.isPlaying = true;

    // Play first burst immediately
    const firstBurst = this._createAndPlayBurst();
    if (!firstBurst) {
      this.isPlaying = false;
      this._releaseLock();
      return { success: false, blocked: true };
    }

    // Loop every 2 seconds
    this.soundLoopInterval = setInterval(() => {
      if (this.isPlaying) {
        this._createAndPlayBurst();
      }
    }, 2000);

    console.log('[AlertSound] Sound loop started');
    return { success: true, blocked: false };
  }

  /**
   * Stop all sounds
   */
  stop() {
    console.log('[AlertSound] stop() called');
    this._stopInternal();
    this._releaseLock();
    
    // Broadcast to other tabs
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
   * Reset manager
   */
  reset() {
    this.stop();
  }

  /**
   * Check if playing
   */
  getIsPlaying() {
    return this.isPlaying;
  }
}

// Singleton
const AlertSoundManager = new AlertSoundManagerClass();

// Global access
if (typeof window !== 'undefined') {
  window.AlertSoundManager = AlertSoundManager;
  window.stopPanicSound = () => AlertSoundManager.stop();
}

export default AlertSoundManager;
