/* ============================================
   🏦 RichPerson FD Advisor — Main App
   ============================================ */

import SpeechModule from './speech.js';
import GeminiAPI from './gemini.js';
import UI from './ui.js';

class App {
  constructor() {
    this.speech = new SpeechModule();
    this.gemini = new GeminiAPI();
    this.ui = new UI();

    // State
    this.currentLang = 'hi-IN'; // default: Hindi
    this.currentLangName = 'Hindi';
    this.state = 'idle'; // idle | recording | processing | speaking
    this.lastTranscript = '';
    this.lastResponse = '';

    this._init();
  }

  _init() {
    // Check browser support
    if (!this.speech.isSupported()) {
      this.ui.showToast(
        'Speech recognition is not supported in this browser. Please use Chrome or Edge.',
        'error',
        10000
      );
    }

    // Load saved language
    const savedLang = localStorage.getItem('blostem_lang');
    if (savedLang) {
      this.currentLang = savedLang;
      const langObj = this.speech.languages.find(l => l.code === savedLang);
      if (langObj) this.currentLangName = langObj.name;
    }
    this.ui.setActiveLanguage(this.currentLang);

    this._bindEvents();
    this._bindSpeechCallbacks();
  }

  _bindEvents() {
    // Mic button
    this.ui.micBtn.addEventListener('click', () => this._toggleRecording());

    // Language buttons
    this.ui.langButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const langCode = btn.dataset.lang;
        const langObj = this.speech.languages.find(l => l.code === langCode);
        if (langObj) {
          this.currentLang = langCode;
          this.currentLangName = langObj.name;
          this.ui.setActiveLanguage(langCode);
          localStorage.setItem('blostem_lang', langCode);
        }
      });
    });

    // Play button
    this.ui.playBtn.addEventListener('click', () => this._togglePlayback());

    // Keyboard shortcut: Space to toggle recording
    document.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && !this._isInputFocused()) {
        e.preventDefault();
        this._toggleRecording();
      }
    });
  }

  _isInputFocused() {
    const el = document.activeElement;
    return el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT');
  }

  _bindSpeechCallbacks() {
    // Interim results (real-time transcription)
    this.speech.onInterim = (text) => {
      this.ui.setTranscript(text, true);
    };

    // Final result
    this.speech.onResult = (text) => {
      this.lastTranscript = text;
      this.ui.setTranscript(text, false);
      // Auto-process the query
      this._processQuery(text);
    };

    // Recognition ended
    this.speech.onEnd = () => {
      if (this.state === 'recording') {
        this.state = 'idle';
        this.ui.setMicState('idle');
      }
    };

    // Recognition error
    this.speech.onError = (error) => {
      this.state = 'idle';
      this.ui.setMicState('idle');

      const messages = {
        'not-allowed': 'Microphone access denied. Please allow microphone access in your browser settings.',
        'no-speech': 'No speech detected. Please try again.',
        'not-supported': 'Speech recognition not supported. Please use Chrome or Edge.',
        'start-failed': 'Failed to start listening. Please try again.',
        'network': 'Network error. Please check your internet connection.',
        'aborted': '', // Silent — user cancelled
      };

      const msg = messages[error] ?? `Speech error: ${error}`;
      if (msg) this.ui.showToast(msg, 'error');
    };

    // TTS ended
    this.speech.onSpeakEnd = () => {
      this.state = 'idle';
      this.ui.setMicState('idle');
      this.ui.setPlayState(false);
    };
  }

  /* ---------- Recording ---------- */
  _toggleRecording() {
    if (this.state === 'recording') {
      this._stopRecording();
    } else if (this.state === 'idle') {
      this._startRecording();
    } else if (this.state === 'speaking') {
      this.speech.stopSpeaking();
      this.state = 'idle';
      this.ui.setMicState('idle');
      this.ui.setPlayState(false);
    }
    // If processing, ignore clicks
  }

  _startRecording() {
    this.state = 'recording';
    this.ui.setMicState('recording');
    this.ui.setTranscript('', false);
    this.ui.setResponse('');
    this.speech.startListening(this.currentLang);
  }

  _stopRecording() {
    this.speech.stopListening();
    this.state = 'idle';
    this.ui.setMicState('idle');
  }

  /* ---------- Process Query via LLM ---------- */
  async _processQuery(query) {
    if (!query.trim()) return;

    this.state = 'processing';
    this.ui.setMicState('processing');
    this.ui.setResponseLoading();

    try {
      const response = await this.gemini.getFDSuggestion(query, this.currentLangName);
      this.lastResponse = response;
      this.ui.setResponse(response);

      // Add to history
      this.ui.addToHistory(query, response, this.currentLangName);

      // Auto-play the response
      this._playResponse(response);
    } catch (error) {
      this.state = 'idle';
      this.ui.setMicState('idle');
      this.ui.setResponse('');
      this.ui.showToast(error.message, 'error', 6000);
      console.error('Gemini error:', error);
    }
  }

  /* ---------- Playback ---------- */
  _togglePlayback() {
    if (this.speech.isSpeaking) {
      this.speech.stopSpeaking();
      this.state = 'idle';
      this.ui.setMicState('idle');
      this.ui.setPlayState(false);
    } else if (this.lastResponse) {
      this._playResponse(this.lastResponse);
    }
  }

  async _playResponse(text) {
    this.state = 'speaking';
    this.ui.setMicState('speaking');
    this.ui.setPlayState(true);

    try {
      await this.speech.speakText(text, this.currentLang, 1.0);
    } catch (error) {
      console.error('TTS error:', error);
      // Don't show error for interruptions
    } finally {
      this.state = 'idle';
      this.ui.setMicState('idle');
      this.ui.setPlayState(false);
    }
  }
}

// Boot
document.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
});
