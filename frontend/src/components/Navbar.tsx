import React from 'react';
import { Globe, ChevronDown, BookOpen, Settings, User } from 'lucide-react';

interface NavbarProps {
  currentJurisdiction?: string;
  systemState?: string;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentJurisdiction = 'India (IPA 1970 & Section 3(p))',
}) => {
  return (
    <header className="h-14 bg-[#0B0E14] border-b border-white/10 px-5 flex items-center justify-between z-20 shrink-0 select-none backdrop-blur-md">
      {/* Brand & Team Info */}
      <div className="flex items-center space-x-3">
        {/* Golden Ayush Lotus Emblem */}
        <div className="w-8 h-8 flex items-center justify-center text-[#E5A93C] drop-shadow-[0_0_8px_rgba(229,169,60,0.5)]">
          <svg viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7">
            <path d="M12 2C11.5 5 9 8 5 9C9 10 11.5 13 12 16C12.5 13 15 10 19 9C15 8 12.5 5 12 2Z" />
            <path d="M12 16C10 18 8 20 5 21C9 21.5 11 20 12 18C13 20 15 21.5 19 21C16 20 14 18 12 16Z" opacity="0.8" />
            <path d="M12 6C11 8.5 8 11 3 11C7.5 12 10 15 11 18C11.5 15.5 13 13.5 15 12C13 10.5 12.5 8 12 6Z" opacity="0.6" />
          </svg>
        </div>
        <div>
          <h1 className="font-serif text-base tracking-tight leading-none text-white flex items-center space-x-1.5">
            <span className="font-bold tracking-wide">IP-SAKTI</span>
            <span className="font-serif italic font-normal text-[#E5A93C]">Sahayak</span>
          </h1>
          <p className="text-[11px] text-slate-400 font-sans tracking-tight mt-0.5">
            Ayurvedic IP & Regulatory Intelligence
          </p>
        </div>
      </div>

      {/* Jurisdiction & System Status */}
      <div className="flex items-center space-x-3">
        {/* Jurisdiction Selector Pill */}
        <div className="flex items-center space-x-2 bg-white/5 hover:bg-white/10 border border-white/10 px-3.5 py-1.5 rounded-full text-xs text-slate-200 cursor-pointer transition-colors shadow-xs">
          <Globe className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">Jurisdiction:</span>
          <span className="font-medium text-white">{currentJurisdiction}</span>
          <ChevronDown className="w-3 h-3 text-slate-400 ml-0.5" />
        </div>

        {/* System State Pill */}
        <div className="flex items-center space-x-2 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-full text-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-emerald-400 text-[11px] font-medium tracking-wide">
            System Online
          </span>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-1 ml-2 text-slate-400">
          <button
            className="p-1.5 rounded-lg hover:text-white hover:bg-white/10 transition-colors"
            title="Library & Knowledge Base"
          >
            <BookOpen className="w-4 h-4" />
          </button>
          <button
            className="p-1.5 rounded-lg hover:text-white hover:bg-white/10 transition-colors"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
          <button
            className="p-1.5 rounded-lg hover:text-white hover:bg-white/10 transition-colors"
            title="User Profile"
          >
            <User className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
