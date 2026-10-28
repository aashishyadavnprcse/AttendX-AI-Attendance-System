import React, { useState, useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { MetricsGrid } from './MetricsGrid';
import { LiveFeedSection } from './LiveFeedSection';
import { AnalyticsCharts } from './AnalyticsCharts';
import { NavTab, ActivityLog, RealtimeAnalyticsResponse } from './types';
import attendxService from '../../api/attendxService';

const INITIAL_LOGS: ActivityLog[] = [
  {
    id: 'log-1',
    studentName: 'Sarah Chen',
    rollNumber: 'CS-2026-001',
    avatarUrl: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100',
    timestamp: '10:14:22 AM',
    status: 'PRESENT',
    confidenceScore: 0.9982,
    verificationMethod: 'Biometric Face + Liveness',
    note: 'Matched with 99.8% confidence. Geofence: 5.2m.',
  },
  {
    id: 'log-2',
    studentName: 'Unknown Impostor',
    rollNumber: 'UNREGISTERED',
    avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100',
    timestamp: '10:13:58 AM',
    status: 'SPOOF_DETECTED',
    confidenceScore: 0.3241,
    verificationMethod: 'Anti-Spoof Defense',
    note: 'Mobile screen replay intercepted. High-frequency FFT grid anomaly.',
  },
  {
    id: 'log-3',
    studentName: 'Alex Mercer',
    rollNumber: 'CS-2026-002',
    avatarUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100',
    timestamp: '10:11:45 AM',
    status: 'BUNK_FLAGGED',
    confidenceScore: 0.0,
    verificationMethod: 'CCTV Bunk Tracker',
    note: 'Vacated desk SEAT_A2 midway during lecture interval #2.',
  },
  {
    id: 'log-4',
    studentName: 'David Kim',
    rollNumber: 'CS-2026-003',
    avatarUrl: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100',
    timestamp: '10:09:12 AM',
    status: 'PRESENT',
    confidenceScore: 0.9854,
    verificationMethod: 'Biometric Face + Liveness',
    note: 'Matched with 98.5% confidence. Geofence: 7.1m.',
  },
  {
    id: 'log-5',
    studentName: 'Emily Watson',
    rollNumber: 'CS-2026-004',
    avatarUrl: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=100',
    timestamp: '10:07:30 AM',
    status: 'PRESENT',
    confidenceScore: 0.9789,
    verificationMethod: 'Biometric Face + Liveness',
    note: 'Matched with 97.9% confidence. Geofence: 3.4m.',
  },
];

export const AttendXDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [sessionActive, setSessionActive] = useState<boolean>(true);
  const [sessionId, setSessionId] = useState<number>(1);
  const [totalStudents, setTotalStudents] = useState<number>(1443);
  const [presentCount, setPresentCount] = useState<number>(1420);
  const [spoofCount, setSpoofCount] = useState<number>(3);
  const [attentionScore, setAttentionScore] = useState<number>(89.2);
  const [logs, setLogs] = useState<ActivityLog[]>(INITIAL_LOGS);
  const [selectedLog, setSelectedLog] = useState<ActivityLog | null>(null);

  // Fetch real-time backend telemetry on mount and every 10 seconds
  useEffect(() => {
    let isMounted = true;

    const fetchLiveTelemetry = async () => {
      try {
        const data: RealtimeAnalyticsResponse = await attendxService.getRealtimeAnalytics(sessionId);
        if (!isMounted) return;

        if (data.total_students > 0) {
          setTotalStudents(data.total_students);
          setPresentCount(data.present_count);
          setSpoofCount(data.spoof_count);
        }

        if (data.active_session_id) {
          setSessionId(data.active_session_id);
          setSessionActive(true);
        }

        if (data.recent_logs && data.recent_logs.length > 0) {
          const adapted = attendxService.adaptRecentLogsToActivityLogs(data.recent_logs);
          setLogs((prev) => {
            const existingIds = new Set(prev.map((l) => l.id));
            const newLogs = adapted.filter((l) => !existingIds.has(l.id));
            return [...newLogs, ...prev].slice(0, 25);
          });
        }
      } catch (err) {
        // Backend offline or token pending: fallback to mock stream seamlessly
      }
    };

    fetchLiveTelemetry();
    const pollInterval = setInterval(fetchLiveTelemetry, 10000);

    return () => {
      isMounted = false;
      clearInterval(pollInterval);
    };
  }, [sessionId]);

  const handleToggleSession = async () => {
    try {
      if (sessionActive) {
        await attendxService.stopSession(sessionId);
        setSessionActive(false);
      } else {
        const newSession = await attendxService.startSession({
          subject_name: 'Neural Networks & Computer Vision',
          geofence_radius_meters: 20.0,
          require_geofence: true,
        });
        setSessionId(newSession.id);
        setSessionActive(true);
      }
    } catch {
      // Local toggle fallback
      setSessionActive(!sessionActive);
    }
  };

  // Periodic simulation adding live attendance events to the ticker
  useEffect(() => {
    if (!sessionActive) return;

    const mockPool = [
      { name: 'Marcus Vance', roll: 'CS-2026-005', avatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100', status: 'PRESENT' as const, conf: 0.991 },
      { name: 'Priya Sharma', roll: 'CS-2026-006', avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100', status: 'PRESENT' as const, conf: 0.984 },
      { name: 'Fake Photo Impostor', roll: 'N/A', avatar: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=100', status: 'SPOOF_DETECTED' as const, conf: 0.281 },
    ];

    let poolIdx = 0;
    const interval = setInterval(() => {
      const candidate = mockPool[poolIdx % mockPool.length];
      poolIdx++;

      const newLog: ActivityLog = {
        id: `log-${Date.now()}`,
        studentName: candidate.name,
        rollNumber: candidate.roll,
        avatarUrl: candidate.avatar,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        status: candidate.status,
        confidenceScore: candidate.conf,
        verificationMethod: candidate.status === 'PRESENT' ? 'Biometric Face + Liveness' : 'Anti-Spoof Defense',
        note: candidate.status === 'PRESENT' ? `Verified with ${(candidate.conf * 100).toFixed(1)}% match` : 'Printed photo attack blocked',
      };

      setLogs((prev) => [newLog, ...prev.slice(0, 19)]);
    }, 7000);

    return () => clearInterval(interval);
  }, [sessionActive]);

  return (
    <div className="min-h-screen bg-background text-gray-100 flex">
      {/* 1. Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        spoofAlertCount={3}
      />

      {/* 2. Main Content Canvas */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          sessionActive={sessionActive}
          onToggleSession={handleToggleSession}
        />

        <main className="p-8 space-y-8 flex-1 overflow-y-auto">
          {/* Live Metrics Grid */}
          <MetricsGrid
            totalEnrolled={totalStudents}
            presentCount={presentCount}
            spoofCount={spoofCount}
            attentionScore={attentionScore}
          />

          {/* Live CCTV Video Feed & Real-time Ticker */}
          <LiveFeedSection
            logs={logs}
            onInspectLog={(log) => setSelectedLog(log)}
          />

          {/* Interactive Attendance & Attention Analytics Charts */}
          <AnalyticsCharts />
        </main>
      </div>

      {/* 3. Modal Inspector for Clicked Activity Log */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
          <div className="card-glass max-w-md w-full rounded-2xl p-6 space-y-4 border border-brand-cyan/40 shadow-glow-cyan">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <span className="text-xs font-mono font-bold text-brand-cyan">
                BIOMETRIC TELEMETRY INSPECTION
              </span>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-gray-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="flex items-center gap-4">
              <img
                src={selectedLog.avatarUrl}
                alt={selectedLog.studentName}
                className="h-14 w-14 rounded-2xl object-cover border border-white/20"
              />
              <div>
                <h3 className="text-base font-bold text-white">{selectedLog.studentName}</h3>
                <p className="text-xs font-mono text-gray-400">{selectedLog.rollNumber}</p>
                <div className="mt-1">
                  {selectedLog.status === 'PRESENT' && (
                    <span className="badge-present text-xs">Verified Present</span>
                  )}
                  {selectedLog.status === 'SPOOF_DETECTED' && (
                    <span className="badge-spoof text-xs">Anti-Spoof Alert</span>
                  )}
                  {selectedLog.status === 'BUNK_FLAGGED' && (
                    <span className="badge-warning text-xs">Bunk Flagged</span>
                  )}
                </div>
              </div>
            </div>

            <div className="bg-black/30 rounded-xl p-3 font-mono text-xs space-y-1.5 text-gray-300">
              <div className="flex justify-between">
                <span>Timestamp:</span>
                <span className="text-white">{selectedLog.timestamp}</span>
              </div>
              <div className="flex justify-between">
                <span>Confidence Score:</span>
                <span className="text-brand-cyan">{(selectedLog.confidenceScore * 100).toFixed(2)}%</span>
              </div>
              <div className="flex justify-between">
                <span>Verification Method:</span>
                <span>{selectedLog.verificationMethod}</span>
              </div>
              <div className="flex justify-between">
                <span>Diagnostic Note:</span>
                <span className="text-right text-gray-400 max-w-[200px]">{selectedLog.note}</span>
              </div>
            </div>

            <button
              onClick={() => setSelectedLog(null)}
              className="w-full py-2.5 rounded-xl font-semibold text-xs bg-brand-cyan text-gray-950 hover:bg-[#22D3EE] transition-all"
            >
              Close Telemetry
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AttendXDashboard;
