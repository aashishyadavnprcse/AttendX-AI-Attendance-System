export type NavTab = 'dashboard' | 'live-feed' | 'analytics' | 'reports' | 'settings';

export type AttendanceStatus = 'PRESENT' | 'ABSENT' | 'SPOOF_DETECTED';

export interface MetricCardData {
  title: string;
  value: string;
  change: string;
  isPositive: boolean;
  accentColor: 'cyan' | 'emerald' | 'rose' | 'amber';
  subtitle: string;
}

export interface ActivityLog {
  id: string;
  studentName: string;
  rollNumber: string;
  avatarUrl: string;
  timestamp: string;
  status: 'PRESENT' | 'SPOOF_DETECTED' | 'BUNK_FLAGGED' | 'ANALYZING';
  confidenceScore: number;
  verificationMethod: string;
  note?: string;
}

export interface AttendanceTrendData {
  day: string;
  present: number;
  absent: number;
  spoof: number;
}

export interface AttentionBreakdownData {
  name: string;
  value: number;
  color: string;
}

// ==============================================================================
// AttendX Backend DTO & API Interfaces (FastAPI Synchronization)
// ==============================================================================

export interface RealtimeAnalyticsRecentLog {
  id: number;
  student_name: string;
  roll_number: string | null;
  avatar_url: string | null;
  subject_name: string;
  timestamp: string;
  status: AttendanceStatus;
  confidence_score: number;
  verification_method: string;
}

export interface RealtimeAnalyticsResponse {
  active_session_id: number | null;
  active_subject: string | null;
  total_students: number;
  present_count: number;
  absent_count: number;
  spoof_count: number;
  attendance_rate: number;
  spoof_rejection_rate: number;
  last_updated: string;
  recent_logs: RealtimeAnalyticsRecentLog[];
}

export interface AttendanceVerifyRequest {
  session_id: number;
  student_id?: number;
  roll_number?: string;
  embedding_vector: number[];
  latitude?: number;
  longitude?: number;
  accuracy_meters?: number;
  wifi_bssid?: string;
  is_live: boolean;
  liveness_score?: number;
  verification_method?: string;
}

export interface AttendanceVerifyResponse {
  log_id: number;
  student_id: number;
  student_name: string;
  session_id: number;
  status: AttendanceStatus;
  confidence_score: number;
  liveness_verified: boolean;
  distance_meters: number | null;
  geofence_verified: boolean;
  timestamp: string;
  message: string;
}

export interface AttendanceReportsFilter {
  session_id?: number;
  status?: AttendanceStatus;
  start_date?: string;
  end_date?: string;
  student_id?: number;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface AttendanceReportItem {
  id: number;
  student_id: number;
  student_name: string;
  roll_number: string | null;
  avatar_url: string | null;
  session_id: number;
  subject_name: string;
  timestamp: string;
  status: AttendanceStatus;
  confidence_score: number;
  verification_method: string;
  distance_meters: number | null;
  liveness_score: number | null;
  notes: string | null;
}

export interface AttendanceReportsSummary {
  total_records: number;
  present_count: number;
  absent_count: number;
  spoof_count: number;
  attendance_rate: number;
}

export interface AttendanceReportsResponse {
  total_records: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary: AttendanceReportsSummary;
  records: AttendanceReportItem[];
}

export interface SessionResponse {
  id: number;
  teacher_id: number;
  subject_name: string;
  classroom_latitude: number;
  classroom_longitude: number;
  geofence_radius_meters: number;
  require_geofence: boolean;
  start_time: string;
  end_time: string | null;
  is_active: boolean;
  created_at: string;
}

export interface StartSessionRequest {
  subject_name: string;
  classroom_latitude?: number;
  classroom_longitude?: number;
  geofence_radius_meters?: number;
  require_geofence?: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  name: string;
  email: string;
  role: string;
}

