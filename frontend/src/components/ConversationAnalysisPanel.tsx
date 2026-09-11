import React, { useState } from 'react';
import {
  MessageSquare,
  Mic,
  Send,
  Sparkles,
  HelpCircle,
  ArrowRight,
  BookOpen,
  FileCheck
} from 'lucide-react';

export interface Message {
  id: string;
  sender: 'user' | 'baba';
  text: string;
  time: string;
  isClarification?: boolean;
  grounded?: boolean;
  citations?: Array<{ title: string; authority: string; section: string; snippet: string }>;
}

export interface ArchitectureStateInfo {
  step: 'understanding' | 'classification' | 'clarification' | 'retrieval' | 'validation' | 'complete';
  detectedEntities: string[];
  formulationCategory: string;
  legalRegime: string;
  confidenceScore: string;
  confidenceTier: string;
}

interface ConversationAnalysisPanelProps {
  messages: Message[];
  onSendQuery: (text: string) => void;
  isSpeaking?: boolean;
  isListening?: boolean;
  isProcessing?: boolean;
  activeClarification?: {
    question: string;
    chips: string[];
  } | null;
  onSelectClarificationChip?: (chip: string) => void;
  architectureState?: ArchitectureStateInfo;
}

export const ConversationAnalysisPanel: React.FC<ConversationAnalysisPanelProps> = ({
  messages,
  onSendQuery,
  isSpeaking = false,
  isListening = false,
  isProcessing = false,
  activeClarification,
  onSelectClarificationChip,
  architectureState = {
    step: 'complete',
    detectedEntities: ['Curcuma longa (Haridra)', 'Azadirachta indica (Nimba)'],
    formulationCategory: 'Section 3(p) Classical Base Formulation',
    legalRegime: 'India (IPA 1970 · Section 3(p) & Section 3(e))',
    confidenceScore: '94%',
    confidenceTier: 'High',
  },
}) => {
  const [inputVal, setInputVal] = useState('');

  const handleSend = (e?: React.FormEvent) => {
    e?.preventDefault();
    const text = inputVal.trim();
    if (!text) return;
    setInputVal('');
    onSendQuery(text);
  };

  return (
    <aside className="w-full lg:w-[330px] xl:w-[360px] 2xl:w-[380px] h-full bg-[#0E131F]/95 border-l border-white/10 flex flex-col justify-between p-3 overflow-hidden backdrop-blur-2xl shadow-2xl select-none">
      {/* Panel Header with System Architecture Subheading */}
      <div className="flex items-center justify-between pb-2 border-b border-white/10 shrink-0">
        <div className="flex items-center space-x-2">
          <div className="w-5 h-5 rounded-md bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <MessageSquare className="w-3 h-3" />
          </div>
          <div>
            <h2 className="font-sans font-semibold text-xs text-white tracking-wide">
              Conversation & Analysis
            </h2>
            <div className="text-[9px] text-[#E5A93C] leading-none mt-0.5 font-mono">
              6. End-to-End Architecture
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-1 text-[10px] text-slate-400 bg-white/5 px-2 py-0.5 rounded-full border border-white/5">
          <Sparkles className="w-2.5 h-2.5 text-[#E5A93C]" />
          <span>Ayush AI</span>
        </div>
      </div>

      {/* Main Scrollable Conversation Thread & Live Architecture Cards */}
      <div className="flex-1 overflow-y-auto py-2.5 space-y-2.5 pr-0.5">
        {/* Chat Thread */}
        {messages.map((msg) => (
          <div key={msg.id} className="space-y-1">
            {msg.sender === 'user' ? (
              <div className="flex flex-col items-end">
                <div className="flex items-center space-x-1 mb-0.5 text-[9px] text-slate-400">
                  <span>You</span>
                  <span>·</span>
                  <span>{msg.time}</span>
                </div>
                <div className="max-w-[90%] bg-gradient-to-r from-[#3B4FD8] to-[#6366F1] text-white rounded-xl rounded-tr-xs px-3 py-2 text-xs shadow-md leading-relaxed">
                  {msg.text}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-start">
                <div className="flex items-center space-x-1.5 mb-1">
                  <img
                    src="/assets/baba-portrait.jpg"
                    alt="Baba Ji"
                    className="w-4 h-4 rounded-full object-cover border border-[#E5A93C]"
                  />
                  <span className="text-[11px] font-semibold text-white">Baba Ji</span>
                  {msg.isClarification && (
                    <span className="bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[8.5px] px-1 rounded font-semibold uppercase">
                      Clarification
                    </span>
                  )}
                  {msg.grounded === false && (
                    <span className="bg-slate-500/20 text-slate-300 border border-slate-500/40 text-[8.5px] px-1 rounded font-semibold uppercase">
                      Insufficient evidence
                    </span>
                  )}
                  {isSpeaking && (
                    <div className="flex items-center space-x-0.5 text-indigo-400">
                      <span className="w-0.5 h-2 bg-indigo-400 rounded-full animate-wave-1" />
                      <span className="w-0.5 h-3 bg-indigo-400 rounded-full animate-wave-2" />
                      <span className="w-0.5 h-1.5 bg-indigo-400 rounded-full animate-wave-3" />
                    </div>
                  )}
                  <span className="text-[9px] text-slate-400 ml-auto">{msg.time}</span>
                </div>
                <div
                  className={`max-w-[95%] border rounded-xl rounded-tl-xs p-2.5 text-xs shadow-md leading-relaxed space-y-2 ${
                    msg.grounded === false
                      ? 'bg-slate-900/80 border-amber-500/30 text-slate-300'
                      : 'bg-[#182032] border-white/10 text-slate-200'
                  }`}
                >
                  <p>{msg.text}</p>

                  {/* Render inline retrieved citations if present on answer */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="pt-2 border-t border-white/10 space-y-1.5">
                      <div className="flex items-center space-x-1 text-[9.5px] text-[#E5A93C] font-semibold uppercase tracking-wider">
                        <BookOpen className="w-3 h-3" />
                        <span>Authoritative Citations & Prior Art</span>
                      </div>
                      {msg.citations.map((c, i) => (
                        <div key={i} className="bg-black/30 rounded-lg p-1.5 border border-white/5 text-[10px] space-y-0.5">
                          <div className="text-white font-medium flex items-center justify-between">
                            <span>{c.title}</span>
                            <span className="text-slate-400 font-normal text-[9px]">{c.authority}</span>
                          </div>
                          <div className="text-slate-400 italic text-[9.5px]">{c.snippet}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Dynamic Clarification Question Card: Appears when Baba Ji needs to clarify modification */}
        {activeClarification && (
          <div className="bg-[#191F33] border border-amber-500/40 rounded-xl p-3 shadow-lg space-y-2 animate-fade-in">
            <div className="flex items-center space-x-1.5 text-amber-400 text-[11px] font-semibold">
              <HelpCircle className="w-3.5 h-3.5" />
              <span>Clarification Required (Section 3(p))</span>
            </div>
            <p className="text-xs text-slate-200 leading-relaxed font-sans">
              {activeClarification.question}
            </p>
            <div className="space-y-1.5 pt-1">
              <span className="text-[9.5px] text-slate-400 uppercase tracking-wider font-semibold">
                Tap to answer or speak into mic:
              </span>
              <div className="flex flex-col space-y-1">
                {activeClarification.chips.map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSelectClarificationChip?.(chip)}
                    className="flex items-center justify-between text-left text-xs bg-white/5 hover:bg-indigo-600/30 border border-white/10 hover:border-indigo-400/40 px-2.5 py-1.5 rounded-lg text-slate-200 hover:text-white transition-all cursor-pointer group"
                  >
                    <span>{chip}</span>
                    <ArrowRight className="w-3 h-3 text-slate-400 group-hover:text-white group-hover:translate-x-0.5 transition-all" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Live Audio Status Card (STT Listening or TTS Speaking) */}
        <div className="bg-[#121826] border border-white/10 rounded-xl p-2.5 shadow-md space-y-1.5">
          <div className="flex items-center justify-between">
            <div
              className={`inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium transition-all ${
                isListening
                  ? 'bg-red-500/30 border border-red-400/50 text-red-200 animate-pulse'
                  : isSpeaking
                  ? 'bg-indigo-500/30 border border-indigo-400/50 text-indigo-200 animate-pulse'
                  : isProcessing
                  ? 'bg-amber-500/20 border border-amber-500/40 text-amber-300'
                  : 'bg-white/5 border border-white/10 text-slate-300'
              }`}
            >
              <Mic
                className={`w-2.5 h-2.5 ${
                  isListening ? 'text-red-400' : isSpeaking ? 'text-indigo-400' : 'text-slate-400'
                }`}
              />
              <span>
                {isListening
                  ? 'Listening to you speak...'
                  : isSpeaking
                  ? 'Baba Ji Speaking...'
                  : isProcessing
                  ? 'Searching knowledge base…'
                  : 'Voice Active (Push to Talk)'}
              </span>
            </div>

            {/* Visualizer Waveform */}
            <div className="flex items-center space-x-0.5">
              <span
                className={`w-0.5 rounded-full ${isListening ? 'bg-red-400' : 'bg-indigo-400'} ${
                  isListening || isSpeaking ? 'animate-wave-1 h-3.5' : 'h-1.5'
                }`}
              />
              <span
                className={`w-0.5 rounded-full ${isListening ? 'bg-red-400' : 'bg-purple-400'} ${
                  isListening || isSpeaking ? 'animate-wave-2 h-4.5' : 'h-2'
                }`}
              />
              <span
                className={`w-0.5 rounded-full ${isListening ? 'bg-red-400' : 'bg-indigo-400'} ${
                  isListening || isSpeaking ? 'animate-wave-3 h-5' : 'h-3'
                }`}
              />
              <span
                className={`w-0.5 rounded-full ${isListening ? 'bg-red-400' : 'bg-purple-400'} ${
                  isListening || isSpeaking ? 'animate-wave-4 h-3.5' : 'h-1.5'
                }`}
              />
              <span
                className={`w-0.5 rounded-full ${isListening ? 'bg-red-400' : 'bg-indigo-400'} ${
                  isListening || isSpeaking ? 'animate-wave-5 h-4' : 'h-2'
                }`}
              />
            </div>
          </div>

          <div className="flex items-center space-x-1.5 text-[10px] text-slate-400 pt-1 border-t border-white/5">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isListening
                  ? 'bg-red-400 animate-ping'
                  : isSpeaking
                  ? 'bg-emerald-400 animate-pulse'
                  : 'bg-emerald-500'
              }`}
            />
            <span>
              {isListening
                ? 'Speak clearly into your microphone'
                : isSpeaking
                ? 'Baba Ji voice streaming aloud'
                : 'Tap mic on stage to ask your question'}
            </span>
          </div>
        </div>

        {/* 6. End-to-End System Architecture Pipeline Tracker */}
        <div className="bg-[#121826] border border-white/10 rounded-xl p-2.5 shadow-md space-y-2">
          <div className="flex items-center justify-between text-[11px] font-semibold text-white">
            <div className="flex items-center space-x-1.5">
              <FileCheck className="w-3.5 h-3.5 text-[#E5A93C]" />
              <span>Architecture Pipeline Progress</span>
            </div>
            <span className="text-[9px] text-[#E5A93C] font-mono">Person 1-6 Stack</span>
          </div>

          {/* Pipeline Stage Indicators */}
          <div className="space-y-1.5 text-[10px]">
            <div className="flex items-center justify-between py-0.5 border-b border-white/5">
              <span className="text-slate-400">1. Query Understanding & Entities:</span>
              <span className="text-slate-200 font-medium truncate max-w-[170px]">
                {architectureState.detectedEntities.join(', ') || 'Extracted'}
              </span>
            </div>
            <div className="flex items-center justify-between py-0.5 border-b border-white/5">
              <span className="text-slate-400">2. Formulation Classification:</span>
              <span className="text-indigo-300 font-medium truncate max-w-[170px]">
                {architectureState.formulationCategory}
              </span>
            </div>
            <div className="flex items-center justify-between py-0.5 border-b border-white/5">
              <span className="text-slate-400">3. Legal Regime Applied:</span>
              <span className="text-amber-300 font-medium truncate max-w-[170px]">
                {architectureState.legalRegime}
              </span>
            </div>
            <div className="flex items-center justify-between py-0.5 border-b border-white/5">
              <span className="text-slate-400">4. Authoritative Retrieval:</span>
              <span className="text-emerald-400 font-medium">Charaka / Sushruta / API</span>
            </div>
            <div className="flex items-center justify-between py-0.5">
              <span className="text-slate-400">5. Evidence & Confidence:</span>
              <span className="flex items-center space-x-1">
                <span className="text-white font-bold">{architectureState.confidenceScore}</span>
                <span className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 text-[8px] px-1 rounded font-semibold uppercase">
                  {architectureState.confidenceTier}
                </span>
              </span>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-800 rounded-full h-1 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 ${
                isProcessing ? 'w-3/4 animate-pulse' : 'w-full'
              }`}
            />
          </div>
        </div>
      </div>

      {/* Bottom Text Prompt Input Field for Typing Option */}
      <div className="pt-2 border-t border-white/10 shrink-0">
        <form onSubmit={handleSend} className="relative flex items-center">
          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="Type your question or formulation..."
            className="w-full bg-[#121826] border border-white/10 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all pr-10 font-sans"
          />
          <button
            type="submit"
            className="absolute right-2 p-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-all shadow-xs cursor-pointer"
            title="Send Text"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </aside>
  );
};
