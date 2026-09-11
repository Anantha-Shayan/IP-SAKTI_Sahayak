import React, { useState, useEffect } from 'react';
import {
  Mic,
  MicOff,
  BookOpen,
  FileText,
  Scale,
  ShieldCheck,
  User,
  RotateCcw,
  Volume2,
  VolumeX,
  X,
  Loader2,
  Sparkles,
  ArrowRight
} from 'lucide-react';
import { useSTT } from '../voice/useSTT';
import { ttsService } from '../services/ttsService';
import type { BabaSpeechState } from '../baba/BabaModel';

interface BabaStageProps {
  onUserSubmit?: (userText: string) => void;
  onSpeakingChange?: (isSpeaking: boolean) => void;
  isSpeaking?: boolean;
  activeClarification?: {
    question: string;
    chips: string[];
  } | null;
  onAnswerClarification?: (chip: string) => void;
  currentSpokenText?: string;
  isProcessing?: boolean;
}

export const BabaStage: React.FC<BabaStageProps> = ({
  onUserSubmit,
  onSpeakingChange,
  activeClarification,
  onAnswerClarification,
  currentSpokenText,
  isProcessing = false,
}) => {
  const [spokenText, setSpokenText] = useState<string>(
    'Namaste! I am Baba Ji, your Ayurvedic IP Assistant. Tap the mic below, speak your formulation question, and I will guide you.'
  );
  const [isSpeakingLocal, setIsSpeakingLocal] = useState<boolean>(false);
  const [speechState, setSpeechState] = useState<BabaSpeechState>('IDLE');
  const [amplitude, setAmplitude] = useState<number>(0);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [activeModal, setActiveModal] = useState<string | null>(null);

  // Sync speaking state with parent
  const updateSpeakingState = (speaking: boolean) => {
    setIsSpeakingLocal(speaking);
    onSpeakingChange?.(speaking);
  };

  // Clean shutdown on unmount
  useEffect(() => {
    return () => {
      ttsService.stopSpeech();
    };
  }, []);

  // Update speech state when parent triggers processing
  useEffect(() => {
    if (isProcessing && speechState !== 'SPEAKING') {
      setSpeechState('PROCESSING');
    }
  }, [isProcessing, speechState]);

  // Primary Neural Speech Playback: Single Audio Session, Zero Jitter
  const speakText = (text: string) => {
    setSpokenText(text);

    if (isMuted) {
      return;
    }

    ttsService.playSpeech(text, {
      onStart: () => {
        setSpeechState('SPEAKING');
        updateSpeakingState(true);
      },
      onEnd: () => {
        setSpeechState('IDLE');
        setAmplitude(0);
        updateSpeakingState(false);
      },
      onAmplitude: (amp) => {
        setAmplitude(amp);
      },
      onError: (err) => {
        console.warn('[BabaStage] TTS playback notice:', err);
        setSpeechState('ERROR');
        setAmplitude(0);
        updateSpeakingState(false);
      },
    });
  };

  // Immediate Cancellation & Audio Stop
  const stopSpeaking = () => {
    ttsService.stopSpeech();
    setSpeechState('INTERRUPTED');
    setAmplitude(0);
    updateSpeakingState(false);
  };

  // React to parent changing spoken text
  useEffect(() => {
    if (currentSpokenText && currentSpokenText !== spokenText) {
      speakText(currentSpokenText);
    }
  }, [currentSpokenText]);

  // Real Speech-to-Text Recognition Hook
  const {
    isListening,
    interimTranscript,
    transcript,
    error: sttError,
    startListening,
    stopListening,
    resetTranscript,
  } = useSTT({
    onFinalResult: (finalText) => {
      if (finalText.trim()) {
        setSpeechState('PROCESSING');
        onUserSubmit?.(finalText.trim());
        resetTranscript();
      }
    },
  });

  // Handle Push-to-Talk Mic Button
  const handleMicButtonClick = () => {
    // 1. If Baba is currently speaking: interrupt immediately and start listening
    if (isSpeakingLocal || speechState === 'SPEAKING') {
      stopSpeaking();
    }

    if (isListening) {
      // 2. User tapped to finish speaking: finalize transcript
      stopListening();
      setSpeechState('PROCESSING');
      const currentSpoken = (interimTranscript || transcript).trim();
      if (currentSpoken) {
        onUserSubmit?.(currentSpoken);
        resetTranscript();
      } else {
        setSpeechState('IDLE');
      }
    } else {
      // 3. User tapped to speak: start listening
      setSpeechState('LISTENING');
      startListening();
    }
  };

  return (
    <div className="relative flex-1 flex flex-col h-full bg-[#0B0E14] overflow-hidden select-none">
      {/* Full-Bleed High-Res Ayurvedic Scholar Desk Scene (Luminous & Framed for Full Head Visibility) */}
      <div
        className="absolute inset-0 bg-cover [background-position:center_top] bg-no-repeat transition-all duration-700"
        style={{
          backgroundImage: "url('/assets/baba-desk-scene.jpg')",
          filter: 'brightness(1.12) contrast(1.03)',
        }}
      >
        {/* Soft ambient edge lighting without darkening the scholar or study */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent pointer-events-none" />
      </div>

      {/* Top Left Floating Information & Navigation Strip */}
      <div className="absolute top-4 left-4 z-10 flex flex-col space-y-2 pointer-events-auto">
        {/* Avatar Status Card */}
        <div className="bg-[#0B0E14]/80 backdrop-blur-xl border border-white/10 rounded-2xl p-2.5 flex items-center space-x-3 shadow-xl max-w-[220px]">
          <div className="w-8 h-8 rounded-xl bg-white/10 border border-white/15 flex items-center justify-center text-slate-200">
            <User className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-xs text-white">Baba Ji</span>
              <span className="flex items-center space-x-1 text-[10px] text-emerald-400 bg-emerald-500/20 px-1.5 py-0.2 rounded-full border border-emerald-500/30">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>Online</span>
              </span>
            </div>
            <p className="text-[10px] text-slate-400 leading-none mt-0.5">
              Neural Ayurvedic IP Scholar
            </p>
          </div>
        </div>

        {/* Vertical Navigation Action Pills */}
        <div className="bg-[#0B0E14]/80 backdrop-blur-xl border border-white/10 rounded-2xl p-1.5 flex flex-col space-y-1 shadow-xl w-[180px]">
          <button
            onClick={handleMicButtonClick}
            className={`flex items-center space-x-2.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all cursor-pointer ${
              isListening
                ? 'bg-red-600 text-white shadow-md animate-pulse'
                : isSpeakingLocal
                ? 'bg-indigo-600 text-white shadow-md'
                : 'text-slate-300 hover:text-white hover:bg-white/10'
            }`}
          >
            <Mic className="w-4 h-4 text-indigo-400" />
            <span>{isListening ? 'Listening...' : 'Neural Voice'}</span>
          </button>

          <button
            onClick={() => setActiveModal('knowledge')}
            className="flex items-center space-x-2.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-white/10 transition-all text-left cursor-pointer"
          >
            <BookOpen className="w-4 h-4 text-amber-400" />
            <span>Knowledge Base</span>
          </button>

          <button
            onClick={() => setActiveModal('evidence')}
            className="flex items-center space-x-2.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-white/10 transition-all text-left cursor-pointer"
          >
            <FileText className="w-4 h-4 text-blue-400" />
            <span>Evidence & Citations</span>
          </button>

          <button
            onClick={() => setActiveModal('classification')}
            className="flex items-center space-x-2.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-white/10 transition-all text-left cursor-pointer"
          >
            <Scale className="w-4 h-4 text-purple-400" />
            <span>Classification</span>
          </button>

          <button
            onClick={() => setActiveModal('safe')}
            className="flex items-center space-x-2.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-white/10 transition-all text-left cursor-pointer"
          >
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Safe Guidance</span>
          </button>
        </div>
      </div>

      {/* Floating Conversational Speech Bubble */}
      <div className="absolute top-12 right-4 lg:right-6 z-10 pointer-events-auto max-w-xs md:max-w-[320px]">
        <div className="relative bg-[#0F1420]/90 backdrop-blur-2xl border border-white/15 rounded-2xl p-3.5 shadow-2xl text-white transition-all hover:bg-[#0F1420]/95">
          {/* Accent Header */}
          <div className="flex items-center justify-between mb-1 pb-1 border-b border-white/10">
            <span className="text-[10px] uppercase font-bold text-[#E5A93C] tracking-wider flex items-center space-x-1">
              <Sparkles className="w-3 h-3 text-[#E5A93C]" />
              <span>
                {activeClarification ? 'Baba Ji Asks Clarification' : 'Baba Ji Spoken Guidance'}
              </span>
            </span>
            <div className="flex items-center space-x-1">
              <button
                onClick={() => speakText(spokenText)}
                className="p-1 rounded-md hover:text-white hover:bg-white/10 text-slate-400 transition-colors cursor-pointer"
                title="Replay Voice"
              >
                <RotateCcw className="w-3 h-3" />
              </button>
              <button
                onClick={() => {
                  const nextMuted = !isMuted;
                  setIsMuted(nextMuted);
                  if (nextMuted) {
                    stopSpeaking();
                  }
                }}
                className="p-1 rounded-md hover:text-white hover:bg-white/10 text-slate-400 transition-colors cursor-pointer"
                title={isMuted ? 'Unmute' : 'Mute'}
              >
                {isMuted ? <VolumeX className="w-3 h-3 text-red-400" /> : <Volume2 className="w-3 h-3 text-indigo-400" />}
              </button>
            </div>
          </div>

          <p className="font-serif italic text-xs md:text-sm text-slate-100 leading-relaxed drop-shadow-sm">
            "{spokenText}"
          </p>

          {/* Interactive Clarification Chips on Stage if Baba asked a clarifying question */}
          {activeClarification && (
            <div className="mt-2.5 pt-2 border-t border-white/10 space-y-1.5">
              <div className="text-[10px] text-amber-300 font-medium">Select or speak your answer:</div>
              <div className="flex flex-col space-y-1">
                {activeClarification.chips.map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => onAnswerClarification?.(chip)}
                    className="flex items-center justify-between text-left text-[10.5px] bg-white/5 hover:bg-indigo-600/40 border border-white/10 hover:border-indigo-400/50 px-2.5 py-1.5 rounded-lg text-slate-200 hover:text-white transition-all cursor-pointer group"
                  >
                    <span>{chip}</span>
                    <ArrowRight className="w-3 h-3 text-slate-400 group-hover:text-white group-hover:translate-x-0.5 transition-all" />
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="mt-2 pt-1.5 border-t border-white/10 flex items-center justify-between">
            {/* Real Audio Amplitude Visualizer (Dynamically driven by TTS speech amplitude) */}
            <div className="flex items-center space-x-1 text-indigo-400">
              <span
                className="w-1 rounded-full bg-indigo-400 transition-all duration-75"
                style={{ height: `${Math.max(3, amplitude * 18)}px` }}
              />
              <span
                className="w-1 rounded-full bg-purple-400 transition-all duration-75"
                style={{ height: `${Math.max(4, amplitude * 24)}px` }}
              />
              <span
                className="w-1 rounded-full bg-indigo-400 transition-all duration-75"
                style={{ height: `${Math.max(5, amplitude * 28)}px` }}
              />
              <span
                className="w-1 rounded-full bg-purple-400 transition-all duration-75"
                style={{ height: `${Math.max(4, amplitude * 22)}px` }}
              />
              <span
                className="w-1 rounded-full bg-indigo-400 transition-all duration-75"
                style={{ height: `${Math.max(3, amplitude * 16)}px` }}
              />
            </div>
            <span className="text-[10px] text-slate-400">Neural en-IN-Prabhat</span>
          </div>
        </div>
      </div>

      {/* Real-time Listening Transcription HUD Overlay */}
      {isListening && (
        <div className="absolute bottom-28 left-1/2 -translate-x-1/2 z-20 w-full max-w-md px-4 pointer-events-auto animate-fade-in">
          <div className="bg-[#0B0E14]/95 backdrop-blur-2xl border border-red-500/40 rounded-2xl p-3.5 shadow-2xl space-y-2 text-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping" />
                <span className="text-xs font-semibold text-red-400 tracking-wide uppercase">
                  Listening to your voice...
                </span>
              </div>
              <button
                onClick={handleMicButtonClick}
                className="text-[10.5px] bg-white/10 hover:bg-white/20 px-2 py-0.5 rounded-md text-slate-300 transition-colors cursor-pointer"
              >
                Tap to submit
              </button>
            </div>

            <div className="bg-black/40 rounded-xl p-2.5 min-h-[44px] border border-white/10">
              <p className="text-xs md:text-sm font-sans text-slate-100 italic">
                {interimTranscript || transcript || 'Speak your formulation inquiry now...'}
              </p>
            </div>

            <div className="flex items-center justify-between text-[10px] text-slate-400">
              <span>Speech-to-Text active</span>
              <span>Say what you modified or ask your question</span>
            </div>
          </div>
        </div>
      )}

      {/* Processing Loader HUD */}
      {isProcessing && !isListening && (
        <div className="absolute bottom-28 left-1/2 -translate-x-1/2 z-20 w-full max-w-sm px-4 pointer-events-auto animate-fade-in">
          <div className="bg-[#0B0E14]/95 backdrop-blur-2xl border border-indigo-500/40 rounded-2xl p-3 shadow-2xl flex items-center space-x-3 text-white">
            <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
            <div className="text-xs text-slate-200">
              Analyzing formulation & evaluating Section 3(p) prior art...
            </div>
          </div>
        </div>
      )}

      {/* Fallback One-Click Prompt Chips if mic error occurs */}
      {sttError && (
        <div className="absolute bottom-28 left-1/2 -translate-x-1/2 z-20 w-full max-w-md px-4 pointer-events-auto">
          <div className="bg-[#0B0E14]/95 backdrop-blur-2xl border border-amber-500/40 rounded-2xl p-3 shadow-2xl space-y-2 text-white">
            <div className="flex items-center justify-between text-xs text-amber-300 font-medium">
              <span>{sttError}</span>
              <button onClick={() => {}} className="text-slate-400 hover:text-white">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="text-[10px] text-slate-300">Click to ask by voice:</div>
            <div className="flex flex-wrap gap-1.5">
              {[
                'Can I patent a modified Ayurvedic formulation?',
                'I modified the formulation with a novel nano-carrier',
                'Synergistic herbal ratio exceeding additive efficacy',
              ].map((query, i) => (
                <button
                  key={i}
                  onClick={() => onUserSubmit?.(query)}
                  className="text-[10px] bg-white/10 hover:bg-indigo-600/40 border border-white/15 px-2 py-1 rounded-lg text-slate-200 hover:text-white transition-all cursor-pointer"
                >
                  {query}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Bottom Center Floating Voice Bar (REAL NEURAL VOICE & AMPLITUDE VISUALIZER) */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 pointer-events-auto flex flex-col items-center">
        <div className="bg-[#0B0E17]/85 backdrop-blur-2xl border border-white/15 rounded-full px-7 py-3 shadow-2xl flex items-center space-x-5">
          {/* Left Audio Wave Visualizer (Real amplitude-driven) */}
          <div className="flex items-center space-x-1 text-indigo-400">
            <span
              className="w-1 rounded-full bg-indigo-400 transition-all duration-75"
              style={{ height: `${Math.max(3, amplitude * 20)}px` }}
            />
            <span
              className="w-1 rounded-full bg-indigo-400 transition-all duration-75"
              style={{ height: `${Math.max(4, amplitude * 26)}px` }}
            />
            <span
              className="w-1 rounded-full bg-indigo-400 transition-all duration-75"
              style={{ height: `${Math.max(6, amplitude * 34)}px` }}
            />
            <span
              className="w-1 rounded-full bg-indigo-400 transition-all duration-75"
              style={{ height: `${Math.max(4, amplitude * 24)}px` }}
            />
            <span
              className="w-1 rounded-full bg-indigo-400 transition-all duration-75"
              style={{ height: `${Math.max(3, amplitude * 18)}px` }}
            />
          </div>

          {/* Central Glowing Mic Button: REAL STT PUSH-TO-TALK & INTERRUPT */}
          <div className="relative flex items-center justify-center">
            <div
              className={`absolute -inset-2 rounded-full transition-all ${
                isListening
                  ? 'bg-red-500/60 blur-md animate-ping'
                  : isSpeakingLocal
                  ? 'bg-gradient-to-r from-blue-500 to-purple-600 blur-md animate-pulse opacity-80'
                  : 'bg-gradient-to-r from-blue-500 to-purple-600 blur-md animate-pulse opacity-40'
              }`}
            />
            <button
              onClick={handleMicButtonClick}
              className={`relative w-13 h-13 rounded-full text-white flex items-center justify-center shadow-xl hover:scale-105 active:scale-95 transition-all cursor-pointer ${
                isListening
                  ? 'bg-gradient-to-tr from-red-600 via-rose-600 to-red-500 shadow-red-500/50'
                  : 'bg-gradient-to-tr from-[#3B82F6] via-[#6366F1] to-[#8B5CF6] shadow-indigo-500/40'
              }`}
              title={
                isListening
                  ? 'Listening to you... Tap to submit'
                  : isSpeakingLocal
                  ? 'Baba Ji is speaking. Tap to interrupt & speak'
                  : 'Tap to speak your formulation question'
              }
            >
              {isListening ? (
                <MicOff className="w-6 h-6 text-white animate-pulse" />
              ) : (
                <Mic className="w-6 h-6 text-white" />
              )}
            </button>
          </div>

          {/* Right Audio Wave Visualizer (Real amplitude-driven) */}
          <div className="flex items-center space-x-1 text-indigo-400">
            <span
              className="w-1 rounded-full bg-indigo-400 transition-all duration-75"
              style={{ height: `${Math.max(4, amplitude * 24)}px` }}
            />
            <span
              className="w-1 rounded-full bg-indigo-400 transition-all duration-75"
              style={{ height: `${Math.max(3, amplitude * 18)}px` }}
            />
            <span
              className="w-1 rounded-full bg-indigo-400 transition-all duration-75"
              style={{ height: `${Math.max(6, amplitude * 34)}px` }}
            />
            <span
              className="w-1 rounded-full bg-indigo-400 transition-all duration-75"
              style={{ height: `${Math.max(4, amplitude * 26)}px` }}
            />
            <span
              className="w-1 rounded-full bg-indigo-400 transition-all duration-75"
              style={{ height: `${Math.max(3, amplitude * 20)}px` }}
            />
          </div>

          {/* Control Utility Buttons */}
          <div className="flex items-center space-x-2 pl-3 border-l border-white/10 text-slate-300">
            <button
              onClick={() => {
                const nextMuted = !isMuted;
                setIsMuted(nextMuted);
                if (nextMuted) {
                  stopSpeaking();
                }
              }}
              className="p-2 rounded-full hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
              title={isMuted ? 'Unmute Audio' : 'Mute Audio'}
            >
              {isMuted ? <VolumeX className="w-4 h-4 text-red-400" /> : <Volume2 className="w-4 h-4 text-emerald-400" />}
            </button>
            <button
              onClick={() => speakText(spokenText)}
              className="p-2 rounded-full hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
              title="Replay Baba Ji Spoken Voice"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Subtext Under the Voice Bar */}
        <p className="text-[11px] text-slate-400 mt-2 tracking-wide font-sans drop-shadow-md">
          {isListening
            ? '🔴 Listening to you... Speak your formulation question'
            : isSpeakingLocal
            ? '🔊 Baba Ji speaking in mature neural scholar voice...'
            : '🎙️ Tap mic to speak your question to Baba Ji'}
        </p>
      </div>

      {/* Info Modals for Navigation Buttons */}
      {activeModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0E131F] border border-white/15 rounded-2xl max-w-lg w-full p-5 shadow-2xl space-y-3 text-white">
            <div className="flex items-center justify-between pb-2 border-b border-white/10">
              <h3 className="font-serif font-bold text-base text-[#E5A93C] capitalize">
                {activeModal.replace('-', ' ')} Overview
              </h3>
              <button
                onClick={() => setActiveModal(null)}
                className="p-1 text-slate-400 hover:text-white rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            {activeModal === 'knowledge' && (
              <p className="text-xs text-slate-300 leading-relaxed">
                Authoritative Traditional Knowledge sources indexed: Charaka Samhita, Sushruta Samhita, Ashtanga Hridaya, and Ayurvedic Pharmacopoeia of India (API Vol 1-5).
              </p>
            )}
            {activeModal === 'evidence' && (
              <p className="text-xs text-slate-300 leading-relaxed">
                Evidence chunk validation active. Prior art references are mechanically verified against Gazette notifications and classical Sanskrit shlokas.
              </p>
            )}
            {activeModal === 'classification' && (
              <p className="text-xs text-slate-300 leading-relaxed">
                Section 3(p) Analysis Engine: Classifies formulations into Traditional Knowledge per se, Synergistic combinations under Section 3(e), or Novel Delivery Modifications under Section 3(d).
              </p>
            )}
            {activeModal === 'safe' && (
              <p className="text-xs text-slate-300 leading-relaxed">
                Safe Statement Guarantee: Analysis is performed strictly against public Classical Ayurvedic Texts. Direct access to TKDL is not claimed.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
