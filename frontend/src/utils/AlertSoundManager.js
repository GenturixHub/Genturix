/**
 * AlertSoundManager v4 - Simplified
 * 
 * Simple audio playback for panic alerts.
 * NO locks, NO cross-tab communication, NO complex state.
 * 
 * Usage:
 *   AlertSoundManager.play()  - Play alert sound
 *   AlertSoundManager.stop()  - Stop alert sound
 */

class AlertSoundManagerClass {
  constructor() {
    this.audio = null;
    this.isPlaying = false;
  }

  /**
   * Play alert sound - simple Audio element approach
   */
  play() {
    console.log('[AlertSound] play()');
    
    // Stop any existing sound first
    this.stop();
    
    try {
      // Use simple HTML5 Audio (most reliable)
      this.audio = new Audio('/alert.mp3');
      this.audio.loop = true;
      this.audio.volume = 0.8;
      
      const playPromise = this.audio.play();
      
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            this.isPlaying = true;
            console.log('[AlertSound] Playing');
          })
          .catch((error) => {
            console.warn('[AlertSound] Autoplay blocked:', error.message);
            this.isPlaying = false;
            // Return blocked status for UI to show unlock prompt
            return { success: false, blocked: true };
          });
      }
      
      return { success: true, blocked: false };
    } catch (e) {
      console.error('[AlertSound] Error:', e);
      return { success: false, blocked: true };
    }
  }

  /**
   * Stop alert sound
   */
  stop() {
    console.log('[AlertSound] stop()');
    
    if (this.audio) {
      try {
        this.audio.pause();
        this.audio.currentTime = 0;
        this.audio = null;
      } catch (e) {
        console.warn('[AlertSound] Stop error:', e);
      }
    }
    
    this.isPlaying = false;
  }

  /**
   * Check if currently playing
   */
  getIsPlaying() {
    return this.isPlaying;
  }

  /**
   * Check if audio is available (always true with HTML5 Audio)
   */
  isUnlocked() {
    return true;
  }

  /**
   * Unlock audio - play silent sound to enable autoplay
   * Call this from a user gesture (click, tap)
   */
  async unlock() {
    console.log('[AlertSound] unlock()');
    try {
      const audio = new Audio('/alert.mp3');
      audio.volume = 0;
      await audio.play();
      audio.pause();
      console.log('[AlertSound] Unlocked');
      return true;
    } catch (e) {
      console.warn('[AlertSound] Unlock failed:', e);
      return false;
    }
  }
}

// Singleton
const AlertSoundManager = new AlertSoundManagerClass();

// Global access for debugging
if (typeof window !== 'undefined') {
  window.AlertSoundManager = AlertSoundManager;
  window.stopPanicSound = () => AlertSoundManager.stop();
}

export default AlertSoundManager;
