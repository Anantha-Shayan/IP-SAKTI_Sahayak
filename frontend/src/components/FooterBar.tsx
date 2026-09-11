import React from 'react';
import { ShieldCheck, BookOpen, FileText, Link2, TrendingUp } from 'lucide-react';

export const FooterBar: React.FC = () => {
  return (
    <footer className="h-9 bg-[#07090E]/95 border-t border-white/10 px-6 flex items-center justify-between text-[11px] text-slate-400 select-none shrink-0 z-20">
      {/* Trust & Methodology Tags */}
      <div className="flex items-center space-x-6 overflow-x-auto no-scrollbar">
        <div className="flex items-center space-x-1.5 hover:text-slate-200 transition-colors cursor-pointer">
          <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
          <span>Trusted Knowledge</span>
        </div>
        <div className="flex items-center space-x-1.5 hover:text-slate-200 transition-colors cursor-pointer">
          <BookOpen className="w-3.5 h-3.5 text-slate-400" />
          <span>Authoritative Sources</span>
        </div>
        <div className="flex items-center space-x-1.5 hover:text-slate-200 transition-colors cursor-pointer">
          <FileText className="w-3.5 h-3.5 text-slate-400" />
          <span>Evidence-based Answers</span>
        </div>
        <div className="flex items-center space-x-1.5 hover:text-slate-200 transition-colors cursor-pointer">
          <Link2 className="w-3.5 h-3.5 text-slate-400" />
          <span>Citations & References</span>
        </div>
        <div className="flex items-center space-x-1.5 hover:text-slate-200 transition-colors cursor-pointer">
          <TrendingUp className="w-3.5 h-3.5 text-slate-400" />
          <span>Confidence Score</span>
        </div>
      </div>

      {/* Motto / Slogan */}
      <div className="hidden md:block font-serif italic text-slate-400 tracking-wide text-xs">
        Preserving Ayurveda <span className="mx-1 text-slate-600">·</span> Protecting Innovation
      </div>
    </footer>
  );
};
