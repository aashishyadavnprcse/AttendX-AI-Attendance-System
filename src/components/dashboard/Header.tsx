import React from 'react';

interface HeaderProps {
  sessionActive: boolean;
  onToggleSession: () => void;
}

export const Header: React.FC<HeaderProps> = ({ sessionActive, onToggleSession }) => {
  return (
    <header className="h-20 border-b border-white/5 bg-background/60 backdrop-blur-xl px-8 flex items-center justify-between sticky top-0 z-30">
      {/* Session Title & Breadcrumb */}
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold text-white tracking-tight">
            Neural Networks & Computer Vision
          </h1>
          {sessionActive ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-brand-emerald/10 text-brand-emerald border border-brand-emerald/30 shadow-[0_0_12px_rgba(16,185,129,0.3)]">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-emerald animate-ping"></span>
              LIVE SESSION ACTIVE
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-gray-500/10 text-gray-400 border border-gray-500/20">
              SESSION CONCLUDED
            </span>
          )}
        </div>
        <p className="text-xs text-gray-400 mt-0.5 font-mono">
          Lab Block C • Room 402 • Geofence Anchor: <span className="text-brand-cyan">37.7749° N, 122.4194° W</span> (20m)
        </p>
      </div>

      {/* Action Controls */}
      <div className="flex items-center gap-4">
        {/* Global Search Bar */}
        <div className="relative hidden md:block">
          <input
            type="text"
            placeholder="Search student or roll #..."
            className="w-64 bg-surface/80 border border-white/10 rounded-xl px-3.5 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-brand-cyan/60 focus:ring-1 focus:ring-brand-cyan/40 transition-all font-mono"
          />
          <kbd className="absolute right-2.5 top-2 px-1.5 py-0.5 text-[10px] font-mono text-gray-400 bg-white/5 border border-white/10 rounded">
            ⌘K
          </kbd>
        </div>

        {/* Toggle Live Session */}
        <button
          onClick={onToggleSession}
          className={`px-4 py-2 rounded-xl text-xs font-semibold tracking-wide transition-all duration-300 flex items-center gap-2 ${
            sessionActive
              ? 'bg-brand-rose/20 text-brand-rose border border-brand-rose/40 hover:bg-brand-rose/30 shadow-glow-rose'
              : 'bg-brand-cyan text-gray-950 font-bold shadow-glow-cyan hover:bg-[#22D3EE]'
          }`}
        >
          {sessionActive ? (
            <>
              <span className="h-2 w-2 rounded-full bg-brand-rose animate-pulse"></span>
              Conclude Attendance
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Resume Session
            </>
          )}
        </button>
      </div>
    </header>
  );
};
