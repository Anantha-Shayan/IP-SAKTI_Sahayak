import React, { useState } from 'react';
import { BookOpen, FileText, CheckCircle2, Layers, History, Scale } from 'lucide-react';

export const EvidencePanelPlaceholder: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'evidence' | 'classification' | 'citations' | 'history'>('evidence');

  return (
    <aside className="w-full lg:w-[420px] xl:w-[480px] 2xl:w-[540px] h-full bg-[#FAF8F5] flex flex-col border-l border-[#E7E0D3] overflow-hidden select-none shadow-xs">
      {/* Panel Top Header Tabs */}
      <div className="bg-white border-b border-[#E7E0D3] p-2 flex items-center justify-between shrink-0 shadow-2xs">
        <div className="flex items-center space-x-1 w-full overflow-x-auto no-scrollbar">
          <button
            onClick={() => setActiveTab('evidence')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all shrink-0 ${
              activeTab === 'evidence'
                ? 'bg-[#D97706] text-white shadow-xs'
                : 'text-[#574F45] hover:text-[#1C1712] hover:bg-[#F4EFE6]'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Evidence</span>
          </button>

          <button
            onClick={() => setActiveTab('classification')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all shrink-0 ${
              activeTab === 'classification'
                ? 'bg-[#D97706] text-white shadow-xs'
                : 'text-[#574F45] hover:text-[#1C1712] hover:bg-[#F4EFE6]'
            }`}
          >
            <Scale className="w-3.5 h-3.5" />
            <span>Classification</span>
          </button>

          <button
            onClick={() => setActiveTab('citations')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all shrink-0 ${
              activeTab === 'citations'
                ? 'bg-[#D97706] text-white shadow-xs'
                : 'text-[#574F45] hover:text-[#1C1712] hover:bg-[#F4EFE6]'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Citations</span>
          </button>

          <button
            onClick={() => setActiveTab('history')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all shrink-0 ${
              activeTab === 'history'
                ? 'bg-[#D97706] text-white shadow-xs'
                : 'text-[#574F45] hover:text-[#1C1712] hover:bg-[#F4EFE6]'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            <span>History</span>
          </button>
        </div>
      </div>

      {/* Main Panel Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Classification Summary Card */}
        <div className="bg-white text-[#1C1712] rounded-xl p-4 shadow-xs border border-[#E7E0D3]">
          <div className="flex items-center justify-between pb-2 border-b border-stone-200">
            <span className="text-[11px] font-sans font-bold uppercase tracking-wider text-[#1E1B4B]">
              Legal Classification & Section 3(p) Analysis
            </span>
            {/* Confidence Badge (Shape + Color + Text) */}
            <div className="flex items-center space-x-1.5 bg-[#486E3C] text-white text-[11px] px-2.5 py-0.5 rounded-full font-semibold shadow-2xs">
              <span className="text-xs leading-none">●</span>
              <span>High confidence</span>
            </div>
          </div>

          <div className="mt-3 space-y-2">
            <h4 className="font-serif font-bold text-base text-[#1E1B4B]">
              Section 3(p) Traditional Knowledge Bar
            </h4>
            <p className="font-sans text-xs text-[#574F45] leading-relaxed max-w-[75ch]">
              Formulation contains direct traditional knowledge components (Haridra & Nimba). Under Section 3(p) of the Indian Patent Act 1970, an invention which in effect is traditional knowledge is not patentable unless synergistic novelty is demonstrated.
            </p>
          </div>
        </div>

        {/* Evidence Documents Section */}
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h3 className="font-serif font-semibold text-sm text-[#1E1B4B] flex items-center space-x-1.5">
              <Layers className="w-4 h-4 text-[#D97706]" />
              <span>Validated Evidence Chunks (2)</span>
            </h3>
            <span className="text-[11px] text-[#786F63]">Source verified</span>
          </div>

          {/* Evidence Card 1 */}
          <div className="bg-white border border-[#E7E0D3] rounded-xl p-4 space-y-2.5 hover:border-[#D97706]/60 transition-colors shadow-2xs">
            <div className="flex items-center justify-between text-xs">
              <span className="font-serif font-semibold text-[#1E1B4B] truncate max-w-[240px]">
                Ayurvedic Pharmacopoeia of India (API Vol 1)
              </span>
              <span className="text-[10px] font-mono bg-emerald-50 text-emerald-800 px-2 py-0.5 rounded-md border border-emerald-200">
                Verified
              </span>
            </div>

            <p className="font-sans text-xs text-[#1C1712]/85 leading-relaxed max-w-[75ch]">
              "Haridra (Curcuma longa L.) rhizome formulation parameters, therapeutic applications in Vrana Ropa (wound healing), and classical dosage guidelines."
            </p>

            <div className="pt-2 border-t border-[#E7E0D3] flex items-center justify-between text-[11px] text-[#786F63]">
              <span>Authority: Govt of India Ayush Dept</span>
              <span className="font-mono font-semibold text-[#D97706]">Section 4.12</span>
            </div>
          </div>

          {/* Evidence Card 2 */}
          <div className="bg-white border border-[#E7E0D3] rounded-xl p-4 space-y-2.5 hover:border-[#D97706]/60 transition-colors shadow-2xs">
            <div className="flex items-center justify-between text-xs">
              <span className="font-serif font-semibold text-[#1E1B4B] truncate max-w-[240px]">
                Charaka Samhita — Sutrasthana Ch. 27
              </span>
              <span className="text-[10px] font-mono bg-emerald-50 text-emerald-800 px-2 py-0.5 rounded-md border border-emerald-200">
                Verified
              </span>
            </div>

            <p className="font-sans text-xs text-[#1C1712]/85 leading-relaxed max-w-[75ch]">
              "Classical references describing topical application of Nimba (Azadirachta indica) leaf extract combined with Haridra for dermatological soothing."
            </p>

            <div className="pt-2 border-t border-[#E7E0D3] flex items-center justify-between text-[11px] text-[#786F63]">
              <span>Classical Text Citation</span>
              <span className="font-mono font-semibold text-[#D97706]">Verse 84-88</span>
            </div>
          </div>
        </div>

        {/* Non-TKDL Safe Statement Box */}
        <div className="bg-white border border-[#E7E0D3] rounded-xl p-3 flex items-start space-x-3 text-xs text-[#574F45] shadow-2xs">
          <CheckCircle2 className="w-4 h-4 text-[#486E3C] shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-[#1E1B4B]">Safe Statement Guarantee</span>
            <p className="text-[11px] text-[#574F45] leading-relaxed">
              "Public Classical Ayurvedic Text Evidence analysis performed. TKDL direct access is not claimed or required for initial patent novelty evaluation."
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
};
