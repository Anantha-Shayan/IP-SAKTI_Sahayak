import React from 'react';
import { Mic, Send, Sparkles, Volume2, ShieldAlert, BookOpen } from 'lucide-react';

interface StagePlaceholderProps {
  currentState?: string;
  transcript?: string;
  onMicClick?: () => void;
}

export const StagePlaceholder: React.FC<StagePlaceholderProps> = ({
  currentState = 'IDLE',
  transcript = '',
  onMicClick,
}) => {
  return (
    <div className="relative flex-1 flex flex-col h-full bg-gradient-to-b from-[#1C1712] via-[#25201A] to-[#181410] border-r border-[#C98A2B]/15 overflow-hidden select-none">
      {/* Subtle Ambient Glow Effect */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-[#C98A2B]/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header Overlay inside 3D Stage */}
      <div className="absolute top-4 left-4 right-4 flex items-center justify-between z-10 pointer-events-none">
        <div className="bg-[#181410]/80 backdrop-blur-md border border-[#C98A2B]/30 px-3 py-1.5 rounded-lg text-xs flex items-center space-x-2 text-[#EDE6D6] pointer-events-auto shadow-lg">
          <Sparkles className="w-3.5 h-3.5 text-[#C98A2B] animate-pulse" />
          <span className="font-serif italic text-[#C98A2B]">Ayurvedic Legal Scholar Avatar</span>
          <span className="text-[#EDE6D6]/40">|</span>
          <span className="text-[11px] font-sans text-[#EDE6D6]/80 uppercase tracking-wide">
            {currentState}
          </span>
        </div>

        <div className="bg-[#181410]/80 backdrop-blur-md border border-[#5B7B4F]/40 px-3 py-1.5 rounded-lg text-xs flex items-center space-x-2 text-[#5B7B4F] pointer-events-auto">
          <span className="w-2 h-2 rounded-full bg-[#5B7B4F] animate-ping" />
          <span className="font-medium text-[11px]">WebGL Stage Ready</span>
        </div>
      </div>

      {/* Central 3D Canvas Container / Static Baba Avatar Placeholder */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 relative">
        <div className="relative group flex flex-col items-center">
          {/* Outer halo */}
          <div className="w-56 h-56 md:w-72 md:h-72 rounded-full bg-gradient-to-t from-[#C98A2B]/20 to-transparent p-1 flex items-center justify-center border border-[#C98A2B]/30 shadow-2xl relative">
            {/* Baba Character Mock Silhouette Card */}
            <div className="w-full h-full rounded-full bg-[#25201A] border border-[#C98A2B]/20 flex flex-col items-center justify-center p-6 text-center relative overflow-hidden">
              <div className="w-24 h-24 rounded-full bg-[#C98A2B]/10 border border-[#C98A2B]/40 flex items-center justify-center mb-3 text-[#C98A2B] shadow-inner">
                <BookOpen className="w-12 h-12" />
              </div>
              <h3 className="font-serif font-semibold text-lg text-[#EDE6D6]">
                Baba — Ayush Legal Scholar
              </h3>
              <p className="text-xs text-[#EDE6D6]/60 mt-1 max-w-[200px]">
                3D Interactive Avatar Stage
              </p>
              <div className="mt-3 inline-flex items-center space-x-1 text-[10px] text-[#C98A2B] bg-[#C98A2B]/10 px-2 py-0.5 rounded border border-[#C98A2B]/20">
                <Volume2 className="w-3 h-3" />
                <span>Lip-Sync Ready</span>
              </div>
            </div>
          </div>

          {/* Spoken Captions Box overlay below Baba */}
          <div className="mt-6 max-w-lg w-full bg-[#181410]/90 backdrop-blur-md border border-[#C98A2B]/30 rounded-xl p-4 text-center shadow-xl">
            <p className="text-xs font-semibold text-[#C98A2B] uppercase tracking-wider mb-1">
              Spoken Captions
            </p>
            <p className="font-serif italic text-sm text-[#EDE6D6] leading-relaxed">
              "Greetings. Present your Ayurvedic formulation or patent claim to assess novelty, traditional knowledge prior art, and Section 3(p) compliance."
            </p>
          </div>
        </div>
      </div>

      {/* Safe Statement Notice */}
      <div className="px-6 py-2 bg-[#181410]/60 border-t border-[#C98A2B]/10 flex items-center justify-between text-[11px] text-[#EDE6D6]/60">
        <div className="flex items-center space-x-1.5">
          <ShieldAlert className="w-3.5 h-3.5 text-[#C98A2B]" />
          <span>Non-TKDL Direct Access Safe Statement Active</span>
        </div>
        <span className="hidden sm:inline italic text-[#EDE6D6]/40">
          Section 3(p) Indian Patent Act 1970 Compliance
        </span>
      </div>

      {/* Bottom Voice & Text Input Controls Bar */}
      <div className="p-4 bg-[#181410] border-t border-[#C98A2B]/20 flex items-center space-x-3 z-10">
        {/* Voice Push-to-Talk Mic Button */}
        <button
          onClick={onMicClick}
          className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#C98A2B] to-[#A8701F] text-[#1C1712] flex items-center justify-center shadow-lg hover:brightness-110 active:scale-95 transition-all shrink-0 font-semibold"
          title="Push to Talk / Voice Search"
        >
          <Mic className="w-5 h-5" />
        </button>

        {/* Text Prompt Input Field */}
        <div className="flex-1 relative">
          <input
            type="text"
            placeholder="Describe your Ayurvedic formulation or patent query (e.g., Turmeric and Neem formulation for wound healing)..."
            defaultValue={transcript}
            className="w-full bg-[#25201A] border border-[#C98A2B]/30 rounded-xl px-4 py-3 text-xs md:text-sm text-[#EDE6D6] placeholder-[#EDE6D6]/40 focus:outline-none focus:border-[#C98A2B] focus:ring-1 focus:ring-[#C98A2B] transition-all font-sans"
          />
          <button
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-[#C98A2B]/20 text-[#C98A2B] hover:bg-[#C98A2B] hover:text-[#1C1712] transition-all"
            title="Submit Query"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
