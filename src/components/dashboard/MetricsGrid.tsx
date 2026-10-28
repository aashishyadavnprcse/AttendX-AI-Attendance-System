import React from 'react';

interface MetricsGridProps {
  totalEnrolled?: number;
  presentCount?: number;
  spoofCount?: number;
  attentionScore?: number;
}

export const MetricsGrid: React.FC<MetricsGridProps> = ({
  totalEnrolled = 1443,
  presentCount = 1420,
  spoofCount = 3,
  attentionScore = 89.2,
}) => {
  const attendanceRate = totalEnrolled > 0 ? ((presentCount / totalEnrolled) * 100).toFixed(1) : '0.0';

  const metrics = [
    {
      title: 'Total Enrolled',
      value: totalEnrolled.toLocaleString(),
      change: '+14 this term',
      isPositive: true,
      subtitle: 'Registered Biometric Profiles',
      colorClass: 'text-brand-cyan',
      borderClass: 'hover:border-brand-cyan/40',
      glowShadow: 'hover:shadow-[0_0_25px_-5px_rgba(6,182,212,0.3)]',
      icon: (
        <svg className="w-5 h-5 text-brand-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      ),
    },
    {
      title: 'Present Today',
      value: presentCount.toLocaleString(),
      change: `${attendanceRate}% verified`,
      isPositive: true,
      subtitle: '23 unexcused absences',
      colorClass: 'text-brand-emerald',
      borderClass: 'hover:border-brand-emerald/40',
      glowShadow: 'hover:shadow-[0_0_25px_-5px_rgba(16,185,129,0.3)]',
      icon: (
        <svg className="w-5 h-5 text-brand-emerald" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    {
      title: 'Active Spoof Attempts',
      value: spoofCount.toString(),
      change: '100% blocked',
      isPositive: false,
      subtitle: 'Replay & photo attacks prevented',
      colorClass: 'text-brand-rose',
      borderClass: 'hover:border-brand-rose/40',
      glowShadow: 'hover:shadow-[0_0_25px_-5px_rgba(244,63,94,0.3)]',
      icon: (
        <svg className="w-5 h-5 text-brand-rose" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
    },
    {
      title: 'Class Attention %',
      value: `${attentionScore}%`,
      change: '+3.4% vs last week',
      isPositive: true,
      subtitle: 'Pose Pitch & Whiteboard Focus',
      colorClass: 'text-[#F59E0B]',
      borderClass: 'hover:border-amber-400/40',
      glowShadow: 'hover:shadow-[0_0_25px_-5px_rgba(245,158,11,0.3)]',
      icon: (
        <svg className="w-5 h-5 text-[#F59E0B]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
        </svg>
      ),
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      {metrics.map((card, idx) => (
        <div
          key={idx}
          className={`card-glass rounded-2xl p-5 transition-all duration-300 ${card.borderClass} ${card.glowShadow} flex flex-col justify-between`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-medium text-gray-400 uppercase tracking-wider">
              {card.title}
            </span>
            <div className="p-2 rounded-xl bg-white/[0.04] border border-white/5">
              {card.icon}
            </div>
          </div>

          <div className="my-3">
            <div className={`text-3xl font-extrabold tracking-tight ${card.colorClass}`}>
              {card.value}
            </div>
            <div className="flex items-center gap-1.5 mt-1 text-xs">
              <span
                className={`font-semibold font-mono ${
                  card.isPositive ? 'text-brand-emerald' : 'text-brand-rose'
                }`}
              >
                {card.change}
              </span>
            </div>
          </div>

          <p className="text-[11px] text-gray-400 font-mono border-t border-white/5 pt-2.5">
            {card.subtitle}
          </p>
        </div>
      ))}
    </div>
  );
};
