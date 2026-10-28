import React from 'react';
import { AttendanceTrendData, AttentionBreakdownData } from './types';

interface AnalyticsChartsProps {
  trendData?: AttendanceTrendData[];
  attentionData?: AttentionBreakdownData[];
}

const DEFAULT_TREND_DATA: AttendanceTrendData[] = [
  { day: 'Mon', present: 1420, absent: 23, spoof: 4 },
  { day: 'Tue', present: 1398, absent: 45, spoof: 2 },
  { day: 'Wed', present: 1435, absent: 8, spoof: 1 },
  { day: 'Thu', present: 1410, absent: 33, spoof: 5 },
  { day: 'Fri', present: 1420, absent: 23, spoof: 3 },
];

const DEFAULT_ATTENTION_DATA: AttentionBreakdownData[] = [
  { name: 'Board Focus', value: 72, color: '#06B6D4' },      // Neon Cyan
  { name: 'Active Notes', value: 18, color: '#10B981' },     // Emerald
  { name: 'Smartphone', value: 7, color: '#F43F5E' },       // Rose
  { name: 'Turned Sideways', value: 3, color: '#F59E0B' },   // Amber
];

export const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({
  trendData = DEFAULT_TREND_DATA,
  attentionData = DEFAULT_ATTENTION_DATA,
}) => {
  const maxPresent = Math.max(...trendData.map((d) => d.present + d.absent));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* ------------------------------------------------------------- */}
      {/* 1. Weekly Attendance Trends (8 cols)                          */}
      {/* ------------------------------------------------------------- */}
      <div className="lg:col-span-8 card-glass rounded-2xl p-6 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">
                Weekly Attendance & Spoof Telemetry
              </h3>
              <p className="text-xs text-gray-400 font-mono mt-0.5">
                5-Day Verified Attendance vs. Presentation Attacks Intercepted
              </p>
            </div>
            {/* Chart Legend */}
            <div className="flex items-center gap-4 text-xs font-mono">
              <span className="flex items-center gap-1.5 text-gray-300">
                <span className="h-2 w-2 rounded-full bg-brand-emerald"></span> Present
              </span>
              <span className="flex items-center gap-1.5 text-gray-400">
                <span className="h-2 w-2 rounded-full bg-gray-500"></span> Absent
              </span>
              <span className="flex items-center gap-1.5 text-brand-rose">
                <span className="h-2 w-2 rounded-full bg-brand-rose"></span> Spoof
              </span>
            </div>
          </div>

          {/* SVG / CSS Bar Chart Visualization */}
          <div className="h-56 w-full flex items-end justify-between gap-4 pt-6 pb-2 px-2">
            {trendData.map((item, idx) => {
              const presentHeight = (item.present / maxPresent) * 100;
              const absentHeight = (item.absent / maxPresent) * 100;

              return (
                <div key={idx} className="flex-1 flex flex-col items-center gap-2 group h-full justify-end">
                  {/* Tooltip on Hover */}
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity text-[10px] font-mono bg-surface border border-white/10 p-1.5 rounded shadow-xl text-center pointer-events-none mb-1">
                    <div className="text-brand-emerald font-bold">{item.present} Present</div>
                    <div className="text-gray-400">{item.absent} Absent</div>
                    <div className="text-brand-rose font-semibold">{item.spoof} Spoofs</div>
                  </div>

                  {/* Stacked Vertical Bar */}
                  <div className="w-full max-w-[48px] bg-white/[0.04] rounded-xl overflow-hidden flex flex-col justify-end p-1 h-44">
                    {/* Spoof indicator dot */}
                    {item.spoof > 0 && (
                      <div className="w-full h-1.5 bg-brand-rose rounded-full mb-1 shadow-glow-rose"></div>
                    )}
                    {/* Absent Bar */}
                    <div
                      className="w-full bg-gray-600/40 rounded-t-lg transition-all duration-500"
                      style={{ height: `${Math.max(4, absentHeight)}%` }}
                    ></div>
                    {/* Present Bar with Emerald Glow */}
                    <div
                      className="w-full bg-gradient-to-t from-emerald-600 to-brand-emerald rounded-lg transition-all duration-500 shadow-glow-emerald"
                      style={{ height: `${Math.max(12, presentHeight)}%` }}
                    ></div>
                  </div>

                  {/* Day Label */}
                  <span className="text-xs font-mono font-medium text-gray-400 group-hover:text-brand-cyan transition-colors">
                    {item.day}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Chart Summary Footer */}
        <div className="pt-4 border-t border-white/5 flex items-center justify-between text-xs text-gray-400 font-mono">
          <span>Weekly Avg: <strong className="text-white">98.2%</strong> Attendance</span>
          <span className="text-brand-cyan">Peak Day: Wednesday (1,435)</span>
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 2. Class Attention Breakdown Donut (4 cols)                   */}
      {/* ------------------------------------------------------------- */}
      <div className="lg:col-span-4 card-glass rounded-2xl p-6 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-white tracking-tight">
              Class Attention Breakdown
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-brand-cyan/15 text-brand-cyan border border-brand-cyan/30">
              MediaPipe
            </span>
          </div>

          {/* Donut Visualization */}
          <div className="relative h-44 flex items-center justify-center">
            {/* SVG Donut */}
            <svg className="w-36 h-36 transform -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="40" stroke="#1F2937" strokeWidth="12" fill="none" />
              {/* Board Focus: 72% */}
              <circle
                cx="50"
                cy="50"
                r="40"
                stroke="#06B6D4"
                strokeWidth="12"
                strokeDasharray="180.9 251.3"
                strokeDashoffset="0"
                fill="none"
                strokeLinecap="round"
                className="transition-all duration-700"
              />
              {/* Notes: 18% */}
              <circle
                cx="50"
                cy="50"
                r="40"
                stroke="#10B981"
                strokeWidth="12"
                strokeDasharray="45.2 251.3"
                strokeDashoffset="-180.9"
                fill="none"
                strokeLinecap="round"
                className="transition-all duration-700"
              />
              {/* Phone Distraction: 7% */}
              <circle
                cx="50"
                cy="50"
                r="40"
                stroke="#F43F5E"
                strokeWidth="12"
                strokeDasharray="17.5 251.3"
                strokeDashoffset="-226.1"
                fill="none"
                strokeLinecap="round"
                className="transition-all duration-700"
              />
            </svg>

            {/* Inner Center Metric */}
            <div className="absolute text-center">
              <span className="text-2xl font-black text-white tracking-tight">89.2%</span>
              <p className="text-[10px] font-mono text-gray-400">Class Focus</p>
            </div>
          </div>

          {/* Breakdown Legend Items */}
          <div className="space-y-2 mt-4">
            {attentionData.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between text-xs font-mono">
                <span className="flex items-center gap-2 text-gray-300">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }}></span>
                  {item.name}
                </span>
                <span className="font-semibold text-white">{item.value}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Attention Suggestion Footer */}
        <p className="text-[11px] text-gray-400 border-t border-white/5 pt-3 mt-3">
          💡 <strong className="text-gray-300">AI Insight:</strong> Engagement peaked during visual slide demo. 7% phone distraction flagged in row 4.
        </p>
      </div>
    </div>
  );
};
