import React, { useState } from 'react';
import { ActivityLog } from './types';

interface LiveFeedSectionProps {
  logs: ActivityLog[];
  onInspectLog?: (log: ActivityLog) => void;
}

export const LiveFeedSection: React.FC<LiveFeedSectionProps> = ({ logs, onInspectLog }) => {
  const [filter, setFilter] = useState<'ALL' | 'PRESENT' | 'SPOOF_DETECTED' | 'BUNK_FLAGGED'>('ALL');
  const [activeCam, setActiveCam] = useState<'cam1' | 'cam2' | 'cctv'>('cam1');

  const filteredLogs = logs.filter((log) => {
    if (filter === 'ALL') return true;
    return log.status === filter;
  });

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* ------------------------------------------------------------- */}
      {/* Left Column: Live AI Biometric Camera Feed (7 cols)            */}
      {/* ------------------------------------------------------------- */}
      <div className="lg:col-span-7 card-glass rounded-2xl p-5 flex flex-col justify-between">
        {/* Stream Header */}
        <div className="flex items-center justify-between pb-3 border-b border-white/5">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-brand-emerald animate-ping"></span>
            <span className="text-xs font-semibold text-white tracking-wide">
              {activeCam === 'cam1' ? 'AI Biometric Vision — Gate A' : activeCam === 'cam2' ? 'AI Vision — Gate B' : 'Wide Classroom CCTV'}
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-brand-cyan/15 text-brand-cyan border border-brand-cyan/30">
              60.2 FPS
            </span>
          </div>

          {/* Camera Selector Pills */}
          <div className="flex items-center gap-1.5 bg-black/40 p-1 rounded-xl border border-white/5 text-[11px] font-mono">
            <button
              onClick={() => setActiveCam('cam1')}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                activeCam === 'cam1' ? 'bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40' : 'text-gray-400 hover:text-white'
              }`}
            >
              CAM-01
            </button>
            <button
              onClick={() => setActiveCam('cam2')}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                activeCam === 'cam2' ? 'bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40' : 'text-gray-400 hover:text-white'
              }`}
            >
              CAM-02
            </button>
            <button
              onClick={() => setActiveCam('cctv')}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                activeCam === 'cctv' ? 'bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40' : 'text-gray-400 hover:text-white'
              }`}
            >
              CCTV-YOLO
            </button>
          </div>
        </div>

        {/* Video Simulation Canvas */}
        <div className="relative my-4 h-[340px] rounded-xl bg-[#060912] border border-white/10 overflow-hidden flex items-center justify-center">
          {/* Cyberpunk Grid Background */}
          <div className="absolute inset-0 opacity-15 bg-[radial-gradient(#06B6D4_1px,transparent_1px)] [background-size:16px_16px]"></div>

          {/* Laser Scan Line Animation */}
          <div className="absolute inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-brand-cyan to-transparent shadow-[0_0_15px_#06B6D4] animate-scan-line z-10"></div>

          {/* HUD Crosshair Center */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-20">
            <div className="w-48 h-48 border border-brand-cyan/40 rounded-full flex items-center justify-center">
              <div className="w-24 h-24 border border-dashed border-brand-cyan/60 rounded-full"></div>
            </div>
          </div>

          {/* 1. GREEN Bounding Box — Verified Present (Sarah Chen) */}
          <div className="absolute left-[12%] top-[18%] w-[38%] h-[68%] border-2 border-brand-emerald rounded-lg bg-brand-emerald/[0.04] backdrop-blur-[1px]">
            {/* Target HUD Brackets */}
            <div className="absolute -top-1 -left-1 w-3 h-3 border-t-2 border-l-2 border-brand-emerald"></div>
            <div className="absolute -top-1 -right-1 w-3 h-3 border-t-2 border-r-2 border-brand-emerald"></div>
            <div className="absolute -bottom-1 -left-1 w-3 h-3 border-b-2 border-l-2 border-brand-emerald"></div>
            <div className="absolute -bottom-1 -right-1 w-3 h-3 border-b-2 border-r-2 border-brand-emerald"></div>

            {/* Top Tag */}
            <div className="absolute -top-7 left-0 right-0 flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-brand-emerald text-black shadow-glow-emerald">
                VERIFIED PRESENT
              </span>
              <span className="text-[10px] font-mono text-emerald-400">99.8% Match</span>
            </div>

            {/* Bottom Tag */}
            <div className="absolute -bottom-8 left-0 px-2 py-1 bg-surface/90 border border-brand-emerald/30 rounded text-[10px] font-mono text-gray-200">
              Sarah Chen • CS-2026-001 (5.2m GPS)
            </div>
          </div>

          {/* 2. RED Bounding Box — Spoof Detected (Mobile Screen Replay) */}
          <div className="absolute right-[12%] top-[25%] w-[32%] h-[60%] border-2 border-brand-rose rounded-lg bg-brand-rose/[0.05] backdrop-blur-[1px]">
            {/* Target HUD Brackets */}
            <div className="absolute -top-1 -left-1 w-3 h-3 border-t-2 border-l-2 border-brand-rose"></div>
            <div className="absolute -top-1 -right-1 w-3 h-3 border-t-2 border-r-2 border-brand-rose"></div>
            <div className="absolute -bottom-1 -left-1 w-3 h-3 border-b-2 border-l-2 border-brand-rose"></div>
            <div className="absolute -bottom-1 -right-1 w-3 h-3 border-b-2 border-r-2 border-brand-rose"></div>

            {/* Top Tag */}
            <div className="absolute -top-7 left-0 right-0 flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-brand-rose text-white shadow-glow-rose animate-pulse">
                SPOOF ALERT
              </span>
              <span className="text-[10px] font-mono text-rose-400">32.4% Match</span>
            </div>

            {/* Bottom Tag */}
            <div className="absolute -bottom-8 left-0 px-2 py-1 bg-surface/90 border border-brand-rose/30 rounded text-[10px] font-mono text-rose-300">
              Screen Glare Attack Intercepted
            </div>
          </div>
        </div>

        {/* Live Stream Telemetry Footer */}
        <div className="flex items-center justify-between text-xs font-mono text-gray-400 pt-2 border-t border-white/5">
          <div className="flex items-center gap-4">
            <span>Latency: <span className="text-brand-cyan">14.2ms</span></span>
            <span>Bitrate: <span className="text-gray-300">4,280 kbps</span></span>
          </div>
          <span className="text-emerald-400 flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
            Anti-Spoof Defense Active
          </span>
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* Right Column: Real-Time Activity Log Ticker (5 cols)           */}
      {/* ------------------------------------------------------------- */}
      <div className="lg:col-span-5 card-glass rounded-2xl p-5 flex flex-col justify-between">
        <div>
          {/* Ticker Header & Filter Pills */}
          <div className="flex items-center justify-between pb-3 border-b border-white/5">
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Real-Time Verification Ticker
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/5 text-gray-300 border border-white/10">
                {logs.length} events
              </span>
            </div>
          </div>

          {/* Quick Status Filter Tabs */}
          <div className="flex items-center gap-1.5 mt-3 mb-2 text-[11px] font-mono">
            {(['ALL', 'PRESENT', 'SPOOF_DETECTED', 'BUNK_FLAGGED'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setFilter(tab)}
                className={`px-2.5 py-1 rounded-lg transition-all ${
                  filter === tab
                    ? 'bg-brand-cyan text-gray-950 font-bold shadow-glow-cyan-sm'
                    : 'bg-white/5 text-gray-400 hover:text-white'
                }`}
              >
                {tab === 'SPOOF_DETECTED' ? 'SPOOFS' : tab === 'BUNK_FLAGGED' ? 'BUNKS' : tab}
              </button>
            ))}
          </div>

          {/* Scrollable Feed Ticker */}
          <div className="space-y-2.5 mt-3 max-h-[300px] overflow-y-auto pr-1">
            {filteredLogs.map((log) => {
              const isPresent = log.status === 'PRESENT';
              const isSpoof = log.status === 'SPOOF_DETECTED';
              const isBunk = log.status === 'BUNK_FLAGGED';

              return (
                <div
                  key={log.id}
                  onClick={() => onInspectLog?.(log)}
                  className="p-3 rounded-xl bg-white/[0.02] border border-white/5 hover:border-brand-cyan/30 hover:bg-white/[0.04] transition-all cursor-pointer flex items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <img
                      src={log.avatarUrl}
                      alt={log.studentName}
                      className="h-8 w-8 rounded-lg object-cover border border-white/10 flex-shrink-0"
                    />
                    <div className="overflow-hidden">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-white truncate">
                          {log.studentName}
                        </span>
                        <span className="text-[10px] font-mono text-gray-400">
                          {log.rollNumber}
                        </span>
                      </div>
                      <p className="text-[10px] text-gray-400 truncate font-mono">
                        {log.note || log.verificationMethod}
                      </p>
                    </div>
                  </div>

                  {/* Badge & Timestamp */}
                  <div className="text-right flex-shrink-0">
                    {isPresent && (
                      <span className="badge-present text-[10px] py-0.5 px-2">
                        {(log.confidenceScore * 100).toFixed(0)}% Match
                      </span>
                    )}
                    {isSpoof && (
                      <span className="badge-spoof text-[10px] py-0.5 px-2 animate-pulse">
                        Spoof
                      </span>
                    )}
                    {isBunk && (
                      <span className="badge-warning text-[10px] py-0.5 px-2">
                        Bunked
                      </span>
                    )}
                    <div className="text-[10px] font-mono text-gray-400 mt-1">
                      {log.timestamp}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Ticker Action Footer */}
        <div className="pt-3 border-t border-white/5 flex items-center justify-between text-xs text-gray-400 font-mono">
          <span>Auto-syncing with Edge Vision</span>
          <button className="text-brand-cyan hover:underline text-[11px]">
            Export Session CSV →
          </button>
        </div>
      </div>
    </div>
  );
};
