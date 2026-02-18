/**
 * AlertSoundManager - Sistema Simple de Audio para Alertas
 * 
 * Singleton simple sin locks ni coordinación entre pestañas.
 * - play() reproduce audio en loop
 * - stop() detiene audio
 */

class AlertSoundManagerClass {
  constructor() {
    if (AlertSoundManagerClass.instance) {
      return AlertSoundManagerClass.instance;
    }
    
    this.audio = null;
    this.isPlaying = false;
    this._initAudio();
    
    AlertSoundManagerClass.instance = this;
  }

  _initAudio() {
    try {
      this.audio = new Audio('/sounds/panic-alert.mp3');
      this.audio.loop = true;
      this.audio.preload = 'auto';
      this.audio.volume = 0.8;
      this.audio.load();
    } catch (e) {
      this.audio = null;
    }
  }

  play() {
    if (!this.audio || this.isPlaying) return;
    
    try {
      this.audio.currentTime = 0;
      this.audio.play().then(() => {
        this.isPlaying = true;
      }).catch(() => {
        this.isPlaying = false;
      });
    } catch (e) {
      // Silent
    }
  }

  stop() {
    if (!this.audio) return;
    
    try {
      this.audio.pause();
      this.audio.currentTime = 0;
      this.isPlaying = false;
    } catch (e) {
      // Silent
    }
  }

  unlock() {
    if (!this.audio) return;
    try {
      this.audio.play().then(() => {
        this.audio.pause();
        this.audio.currentTime = 0;
      }).catch(() => {});
    } catch (e) {
      // Silent
    }
  }
}

const AlertSoundManager = new AlertSoundManagerClass();

if (typeof window !== 'undefined') {
  window.AlertSoundManager = AlertSoundManager;
}

export default AlertSoundManager;
