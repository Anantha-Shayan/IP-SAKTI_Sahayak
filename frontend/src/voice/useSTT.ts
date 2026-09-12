import { useState, useEffect, useRef, useCallback } from 'react';

// TypeScript definitions for Web Speech Recognition API
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognitionInstance extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error: string; message?: string }) => void) | null;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
}

interface WindowWithSpeech extends Window {
  SpeechRecognition?: { new (): SpeechRecognitionInstance };
  webkitSpeechRecognition?: { new (): SpeechRecognitionInstance };
}

export interface UseSTTOptions {
  onFinalResult?: (transcript: string) => void;
  lang?: string;
}

export const useSTT = (options: UseSTTOptions = {}) => {
  const { onFinalResult, lang = 'en-IN' } = options;
  const [isListening, setIsListening] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<string>('');
  const [interimTranscript, setInterimTranscript] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState<boolean>(true);
  const [googleReachable, setGoogleReachable] = useState<boolean | null>(null);
  const [usingLocalSTT, setUsingLocalSTT] = useState(false);

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const onFinalResultRef = useRef(onFinalResult);
  onFinalResultRef.current = onFinalResult;

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const attemptLocalFallbackRef = useRef<(() => void) | null>(null);

  const startLocalRecording = useCallback(async () => {
    try {
      setError(null);
      setTranscript('');
      setInterimTranscript('🎤 Recording locally (offline mode)...');
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];
      
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      
      recorder.onstop = async () => {
        // Clean up stream
        stream.getTracks().forEach(t => t.stop());
        mediaStreamRef.current = null;
        
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        if (audioBlob.size < 1000) {
          setError('No speech was detected. Please try speaking again.');
          setInterimTranscript('');
          setIsListening(false);
          return;
        }
        
        setInterimTranscript('Processing speech locally...');
        
        try {
          const formData = new FormData();
          formData.append('audio', audioBlob, 'recording.webm');
          formData.append('lang', lang);
          
          const response = await fetch('/api/stt', {
            method: 'POST',
            body: formData,
          });
          
          if (!response.ok) {
            throw new Error(`Local STT server responded with ${response.status}`);
          }
          
          const result = await response.json();
          const text = (result.transcript || '').trim();
          
          if (text) {
            setTranscript(text);
            setInterimTranscript('');
            onFinalResultRef.current?.(text);
          } else {
            setError('No speech was detected. Please try speaking again.');
            setInterimTranscript('');
          }
        } catch (fetchErr) {
          console.warn('[STT] Local fallback fetch error:', fetchErr);
          setError(
            'Voice input is currently unavailable (both online and local). ' +
            'Please type your question instead.'
          );
          setInterimTranscript('');
        }
        
        setIsListening(false);
      };
      
      recorder.start();
      setIsListening(true);
      setUsingLocalSTT(true);
    } catch (micErr) {
      console.warn('[STT] Local recording failed:', micErr);
      setError(
        'Voice input is currently unavailable. ' +
        'Please type your question instead.'
      );
      setIsListening(false);
    }
  }, [lang]);

  const stopLocalRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setUsingLocalSTT(false);
  }, []);

  // Wire up the fallback trigger
  useEffect(() => {
    attemptLocalFallbackRef.current = () => {
      // Auto-start local recording when browser STT fails with 'network'
      startLocalRecording();
    };
  }, [startLocalRecording]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    // Check if we're on a secure context (required for Web Speech API)
    if (!window.isSecureContext) {
      console.warn('[STT] Not a secure context:', window.location.origin,
        '— Web Speech API requires https:// or http://localhost');
    }

    // Lightweight reachability probe for Google's speech servers
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    fetch('https://www.google.com/generate_204', {
      method: 'HEAD',
      mode: 'no-cors',
      signal: controller.signal,
    })
      .then(() => {
        clearTimeout(timeoutId);
        setGoogleReachable(true);
      })
      .catch(() => {
        clearTimeout(timeoutId);
        setGoogleReachable(false);
        console.warn('[STT] Google speech servers appear unreachable — local fallback will be used');
      });

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const win = window as WindowWithSpeech;
    const SpeechRecognitionClass = win.SpeechRecognition || win.webkitSpeechRecognition;

    if (!SpeechRecognitionClass) {
      setIsSupported(false);
      return;
    }

    try {
      const recognition = new SpeechRecognitionClass();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = lang;

      recognition.onstart = () => {
        setIsListening(true);
        setError(null);
        setInterimTranscript('');
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        let currentInterim = '';
        let currentFinal = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) {
            currentFinal += result[0].transcript;
          } else {
            currentInterim += result[0].transcript;
          }
        }

        if (currentInterim) {
          setInterimTranscript(currentInterim);
        }

        if (currentFinal) {
          const trimmed = currentFinal.trim();
          setTranscript(trimmed);
          setInterimTranscript('');
          onFinalResultRef.current?.(trimmed);
        }
      };

      recognition.onerror = (event) => {
        console.warn('SpeechRecognition error:', event.error, '| navigator.onLine:', navigator.onLine);
        if (event.error === 'no-speech') {
          setError('No speech was detected. Please try speaking again.');
        } else if (event.error === 'not-allowed') {
          setError('Microphone permission denied. Please allow mic access in your browser settings.');
        } else if (event.error === 'network') {
          console.warn(
            '[STT] Network error — origin:', window.location.origin,
            '| onLine:', navigator.onLine,
            '| Likely cause: browser cannot reach Google speech servers (firewall, no internet, or non-https origin)'
          );
          setError(
            'Voice input needs an internet connection to Google\'s speech service — ' +
            'this network/browser can\'t reach it right now. ' +
            'Falling back to local speech recognition...'
          );
          // Attempt local STT fallback
          attemptLocalFallbackRef.current?.();
        } else {
          setError(`Speech recognition error: ${event.error}. Please use text input or try again.`);
        }
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    } catch (e) {
      console.warn('SpeechRecognition initialization error:', e);
      setIsSupported(false);
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }
    };
  }, [lang]);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(t => t.stop());
      }
    };
  }, []);

  const startListening = useCallback(() => {
    setError(null);
    setTranscript('');
    setInterimTranscript('');
    
    // If browser speech recognition isn't available or Google is unreachable,
    // go directly to local recording fallback
    if (!recognitionRef.current || googleReachable === false) {
      startLocalRecording();
      return;
    }
    
    try {
      recognitionRef.current.start();
    } catch (err: unknown) {
      console.warn('Recognition start exception, attempting reset:', err);
      try {
        recognitionRef.current.abort();
        setTimeout(() => {
          recognitionRef.current?.start();
        }, 100);
      } catch {
        // ignore
      }
    }
  }, [googleReachable, startLocalRecording]);

  const stopListening = useCallback(() => {
    if (usingLocalSTT) {
      stopLocalRecording();
      return;
    }
    if (recognitionRef.current && isListening) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
    }
    setIsListening(false);
  }, [isListening, usingLocalSTT, stopLocalRecording]);

  const resetTranscript = useCallback(() => {
    setTranscript('');
    setInterimTranscript('');
    setError(null);
  }, []);

  return {
    isListening,
    transcript,
    interimTranscript,
    error,
    isSupported,
    startListening,
    stopListening,
    resetTranscript,
    usingLocalSTT,
    googleReachable,
  };
};
