// SINGLETON AUDIO PLAYBACK & NEURAL TTS SERVICE
// Enforces: ONE TTS REQUEST → ONE AUDIO OBJECT → ONE PLAYBACK SESSION
// Provides real-time Web Audio Analyser for amplitude-driven lip-sync & speech states

interface PlaySpeechOptions {
  onStart?: () => void;
  onEnd?: () => void;
  onAmplitude?: (amplitude: number) => void;
  onError?: (err: unknown) => void;
}

// Pre-synthesized neural audio assets for zero-latency instant response
const STATIC_NEURAL_CLIPS: Record<string, string> = {
  test: '/assets/baba-test.mp3',
  greeting: '/assets/baba-greeting.mp3',
  clarification: '/assets/baba-clarification.mp3',
  nano: '/assets/baba-answer-nano.mp3',
  synergism: '/assets/baba-answer-synergism.mp3',
  extract: '/assets/baba-answer-extract.mp3',
};

class TTSService {
  private currentAudio: HTMLAudioElement | null = null;
  private currentAbortController: AbortController | null = null;
  private currentObjectUrl: string | null = null;
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private sourceNode: MediaElementAudioSourceNode | null = null;
  private animFrameId: number | null = null;
  private isSpeaking = false;
  private generation = 0;

  public getSpeakingState(): boolean {
    return this.isSpeaking;
  }

  // Lazy init and unlock AudioContext on user gesture
  public unlockAudio(): void {
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        if (!this.audioContext || this.audioContext.state === 'closed') {
          this.audioContext = new AudioCtx();
        }
        if (this.audioContext.state === 'suspended') {
          this.audioContext.resume().catch(() => { /* ignore */ });
        }
      }
    } catch (err) {
      console.warn('[TTS Service] Failed to unlock audio context', err);
    }
  }

  // Abort and cleanly stop any existing playback
  public stopSpeech(): void {
    if (this.currentAbortController) {
      this.currentAbortController.abort();
      this.currentAbortController = null;
    }

    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }

    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio.onplay = null;
      this.currentAudio.onended = null;
      this.currentAudio.onerror = null;
      this.currentAudio = null;
    }

    if (this.sourceNode) {
      try { this.sourceNode.disconnect(); } catch { /* ignore */ }
      this.sourceNode = null;
    }
    if (this.analyser) {
      try { this.analyser.disconnect(); } catch { /* ignore */ }
      this.analyser = null;
    }

    if (this.currentObjectUrl) {
      URL.revokeObjectURL(this.currentObjectUrl);
      this.currentObjectUrl = null;
    }

    // Stop browser fallback if running
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }

    this.isSpeaking = false;
  }

  // Identify matching pre-generated static audio clip to avoid unnecessary network delay
  private findMatchingClip(text: string): string | null {
    const norm = text.toLowerCase();
    if (norm.includes('namaste') && norm.includes('ayurvedic ip assistant')) {
      return STATIC_NEURAL_CLIPS.greeting;
    }
    if (norm.includes('tell me about your ayurvedic formulation') && norm.includes('traditional knowledge')) {
      return STATIC_NEURAL_CLIPS.test;
    }
    if (
      norm.includes('what exact modification have you made') ||
      (norm.includes('section 3(p)') && norm.includes('synergistic ratio') && norm.includes('carrier'))
    ) {
      return STATIC_NEURAL_CLIPS.clarification;
    }
    if (norm.includes('novel drug delivery') || norm.includes('nano-carrier') || norm.includes('lipid micro-encapsulation')) {
      return STATIC_NEURAL_CLIPS.nano;
    }
    if (norm.includes('mere aggregation') || (norm.includes('section 3(e)') && norm.includes('synergistic efficacy'))) {
      return STATIC_NEURAL_CLIPS.synergism;
    }
    if (norm.includes('bioactive fraction') || norm.includes('extraction method') || norm.includes('phytochemical')) {
      return STATIC_NEURAL_CLIPS.extract;
    }
    return null;
  }

  // Play neural TTS with full lifecycle tracking and amplitude analyser
  public async playSpeech(text: string, options: PlaySpeechOptions = {}): Promise<void> {
    const { onStart, onEnd, onAmplitude, onError } = options;

    // 1. Immediately cancel any running or pending speech
    this.stopSpeech();
    const myGen = ++this.generation;

    const trimmed = text.trim();
    if (!trimmed) return;

    this.currentAbortController = new AbortController();
    const signal = this.currentAbortController.signal;

    try {
      let audioSrc = this.findMatchingClip(trimmed);

      // If not in static clips, request from neural /api/tts endpoint
      if (!audioSrc) {
        const response = await fetch('/api/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: trimmed,
            rate: '-10%',
            pitch: '-8Hz', // Deep scholarly Indian male tone
          }),
          signal,
        });

        if (!response.ok) {
          throw new Error(`TTS server responded with status: ${response.status}`);
        }

        if (myGen !== this.generation) return;

        const blob = await response.blob();
        if (myGen !== this.generation) return;
        if (signal.aborted) return;

        this.currentObjectUrl = URL.createObjectURL(blob);
        audioSrc = this.currentObjectUrl;
      }

      if (signal.aborted) return;

      // 2. Instantiate single Audio object
      const audio = new Audio(audioSrc);
      this.currentAudio = audio;
      audio.preload = 'auto';

      // 3. Configure Web Audio API Analyser for amplitude-driven Lip Sync
      try {
        if (this.audioContext) {
          if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
            if (myGen !== this.generation) return;
          }

          if (this.audioContext.state === 'running') {
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 64;
            this.analyser.smoothingTimeConstant = 0.5;

            // Connect audio element through analyser to speaker destination
            this.sourceNode = this.audioContext.createMediaElementSource(audio);
            this.sourceNode.connect(this.analyser);
            this.analyser.connect(this.audioContext.destination);
          }
        }
      } catch (audioCtxErr) {
        console.warn('[TTS Analyser] AudioContext hook notice (fallback to direct playback):', audioCtxErr);
      }

      // Amplitude measurement loop (updates lip sync jaw movement)
      const dataArray = new Uint8Array(this.analyser?.frequencyBinCount || 32);
      const trackAmplitude = () => {
        if (!this.isSpeaking || !this.currentAudio) {
          onAmplitude?.(0);
          return;
        }

        if (this.analyser) {
          this.analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const avg = sum / dataArray.length;
          // Normalized amplitude between 0.0 and 1.0
          const normalized = Math.min(1.0, Math.max(0.0, avg / 128.0));
          onAmplitude?.(normalized);
        } else {
          // Subtle synthetic fluctuation if analyser unavailable
          onAmplitude?.(0.4 + Math.sin(Date.now() / 100) * 0.2);
        }

        this.animFrameId = requestAnimationFrame(trackAmplitude);
      };

      // 4. Audio Playback Event Listeners
      audio.onplay = () => {
        this.isSpeaking = true;
        onStart?.();
        this.animFrameId = requestAnimationFrame(trackAmplitude);
      };

      audio.onended = () => {
        this.isSpeaking = false;
        if (this.animFrameId !== null) {
          cancelAnimationFrame(this.animFrameId);
          this.animFrameId = null;
        }
        onAmplitude?.(0);
        onEnd?.();
      };

      audio.onerror = (e) => {
        console.warn('[TTS Service] Audio playback error, engaging fallback:', e);
        this.isSpeaking = false;
        if (this.animFrameId !== null) {
          cancelAnimationFrame(this.animFrameId);
          this.animFrameId = null;
        }
        onAmplitude?.(0);
        this.fallbackSpeechSynthesis(trimmed, options);
      };

      if (myGen !== this.generation) return;
      await audio.play();
    } catch (err: unknown) {
      if ((err as Error)?.name === 'AbortError') {
        return; // Normal cancellation on user interaction
      }
      console.warn('[TTS Service] Neural TTS error, falling back to browser speech synthesis:', err);
      onError?.(err);
      this.fallbackSpeechSynthesis(trimmed, options);
    }
  }

  // Emergency fallback using browser Web Speech API (only used if server fails)
  private fallbackSpeechSynthesis(text: string, options: PlaySpeechOptions): void {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      options.onEnd?.();
      return;
    }

    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.88;
      utterance.pitch = 0.85;

      const voices = window.speechSynthesis.getVoices();
      const preferred =
        voices.find((v) => v.lang === 'en-IN') ||
        voices.find((v) => v.lang.startsWith('en')) ||
        voices[0];

      if (preferred) utterance.voice = preferred;

      utterance.onstart = () => {
        this.isSpeaking = true;
        options.onStart?.();
      };
      utterance.onend = () => {
        this.isSpeaking = false;
        options.onAmplitude?.(0);
        options.onEnd?.();
      };
      utterance.onerror = () => {
        this.isSpeaking = false;
        options.onAmplitude?.(0);
        options.onEnd?.();
      };

      window.speechSynthesis.speak(utterance);
    } catch {
      options.onEnd?.();
    }
  }
}

export const ttsService = new TTSService();
