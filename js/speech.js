/* ============================================
   🎤 Speech Module — Recognition & Synthesis
   ============================================ */

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

class SpeechModule {
  constructor() {
    this.recognition = null;
    this.synthesis = window.speechSynthesis;
    this.isListening = false;
    this.isSpeaking = false;
    this.currentUtterance = null;

    // Callbacks
    this.onResult = null;
    this.onInterim = null;
    this.onEnd = null;
    this.onError = null;
    this.onSpeakEnd = null;

    // Supported languages
    this.languages = [
      { code: 'en-IN', name: 'English', native: 'English' },
      { code: 'hi-IN', name: 'Hindi', native: 'हिन्दी' },
      { code: 'te-IN', name: 'Telugu', native: 'తెలుగు' },
      { code: 'ta-IN', name: 'Tamil', native: 'தமிழ்' },
      { code: 'kn-IN', name: 'Kannada', native: 'ಕನ್ನಡ' },
      { code: 'ml-IN', name: 'Malayalam', native: 'മലയാളം' },
      { code: 'bn-IN', name: 'Bengali', native: 'বাংলা' },
      { code: 'mr-IN', name: 'Marathi', native: 'मराठी' },
      { code: 'gu-IN', name: 'Gujarati', native: 'ગુજરાતી' },
    ];

    this._initRecognition();
    this._preloadVoices();
  }

  /** Check if speech recognition is supported */
  isSupported() {
    return !!SpeechRecognition;
  }

  /** Initialize the recognition engine */
  _initRecognition() {
    if (!this.isSupported()) return;

    this.recognition = new SpeechRecognition();
    this.recognition.continuous = false;
    this.recognition.interimResults = true;
    this.recognition.maxAlternatives = 1;

    this.recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      if (interimTranscript && this.onInterim) {
        this.onInterim(interimTranscript);
      }

      if (finalTranscript && this.onResult) {
        this.onResult(finalTranscript);
      }
    };

    this.recognition.onend = () => {
      this.isListening = false;
      if (this.onEnd) this.onEnd();
    };

    this.recognition.onerror = (event) => {
      this.isListening = false;
      console.error('Speech recognition error:', event.error);
      if (this.onError) this.onError(event.error);
    };
  }

  /** Preload available TTS voices */
  _preloadVoices() {
    // Voices may load async
    if (this.synthesis) {
      this.synthesis.getVoices();
      this.synthesis.onvoiceschanged = () => {
        this.synthesis.getVoices();
      };
    }
  }

  /** Start listening in a given language */
  startListening(langCode = 'en-IN') {
    if (!this.isSupported()) {
      if (this.onError) this.onError('not-supported');
      return;
    }

    // Stop any speaking first
    this.stopSpeaking();

    this.recognition.lang = langCode;
    this.isListening = true;

    try {
      this.recognition.start();
    } catch (e) {
      // Already started — abort and restart
      this.recognition.abort();
      setTimeout(() => {
        try {
          this.recognition.start();
        } catch (e2) {
          console.error('Failed to start recognition:', e2);
          this.isListening = false;
          if (this.onError) this.onError('start-failed');
        }
      }, 200);
    }
  }

  /** Stop listening */
  stopListening() {
    if (this.recognition && this.isListening) {
      this.recognition.stop();
      this.isListening = false;
    }
  }

  /** Get the best matching voice for a language */
  _getVoice(langCode) {
    const voices = this.synthesis.getVoices();
    const langPrefix = langCode.split('-')[0];

    // Exact match first
    let voice = voices.find(v => v.lang === langCode);

    // Prefix match
    if (!voice) {
      voice = voices.find(v => v.lang.startsWith(langPrefix));
    }

    // Google voice preference (usually higher quality)
    const googleVoice = voices.find(
      v => (v.lang === langCode || v.lang.startsWith(langPrefix)) && v.name.includes('Google')
    );

    return googleVoice || voice || null;
  }

  /** Speak text in a given language */
  speakText(text, langCode = 'en-IN', rate = 1.0) {
    return new Promise((resolve, reject) => {
      if (!this.synthesis) {
        reject(new Error('Speech synthesis not supported'));
        return;
      }

      // Stop any current speech
      this.stopSpeaking();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = langCode;
      utterance.rate = rate;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      const voice = this._getVoice(langCode);
      if (voice) {
        utterance.voice = voice;
      } else if (!langCode.startsWith('en')) {
        // Voice not found for non-English language
        console.warn(`No voice found for language ${langCode}`);
        reject(new Error(`No voice installed for ${langCode}. Please install the language pack in your OS settings.`));
        return;
      }

      utterance.onstart = () => {
        this.isSpeaking = true;
      };

      utterance.onend = () => {
        this.isSpeaking = false;
        this.currentUtterance = null;
        if (this.onSpeakEnd) this.onSpeakEnd();
        resolve();
      };

      utterance.onerror = (event) => {
        this.isSpeaking = false;
        this.currentUtterance = null;
        if (event.error !== 'interrupted') {
          reject(new Error(event.error));
        } else {
          resolve();
        }
      };

      this.currentUtterance = utterance;

      // Chrome bug workaround: resume synthesis if paused
      this.synthesis.cancel();
      setTimeout(() => {
        this.synthesis.speak(utterance);
      }, 50);
    });
  }

  /** Stop speaking */
  stopSpeaking() {
    if (this.synthesis) {
      this.synthesis.cancel();
      this.isSpeaking = false;
      this.currentUtterance = null;
    }
  }

  /** Get list of available voices for a language */
  getAvailableVoices(langCode) {
    if (!this.synthesis) return [];
    const langPrefix = langCode.split('-')[0];
    return this.synthesis.getVoices().filter(
      v => v.lang === langCode || v.lang.startsWith(langPrefix)
    );
  }
}

export default SpeechModule;
