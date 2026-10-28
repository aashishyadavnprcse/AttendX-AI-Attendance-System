/**
 * AttendX API Client Service (Next.js / React)
 * Connects frontend dashboard components to the FastAPI backend.
 * Provides unified authentication, error parsing, and telemetry synchronization.
 */

import {
  RealtimeAnalyticsResponse,
  AttendanceVerifyRequest,
  AttendanceVerifyResponse,
  AttendanceReportsFilter,
  AttendanceReportsResponse,
  StartSessionRequest,
  SessionResponse,
  LoginResponse,
  ActivityLog,
} from '../components/dashboard/types';

const API_BASE_URL =
  (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_API_URL) ||
  'http://127.0.0.1:8000/api';

class AttendXApiError extends Error {
  status: number;
  errorCode?: string;
  data?: any;

  constructor(message: string, status: number, errorCode?: string, data?: any) {
    super(message);
    this.name = 'AttendXApiError';
    this.status = status;
    this.errorCode = errorCode;
    this.data = data;
  }
}

class AttendXService {
  private token: string | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('attendx_token');
    }
  }

  /**
   * Set or clear JWT authentication Bearer token
   */
  public setAuthToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('attendx_token', token);
      } else {
        localStorage.removeItem('attendx_token');
      }
    }
  }

  public getAuthToken(): string | null {
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('attendx_token');
    }
    return this.token;
  }

  /**
   * Base HTTP request wrapper with Bearer token injection and error parsing
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    const token = this.getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      // Handle non-2xx responses
      if (!response.ok) {
        let errorData: any = {};
        try {
          errorData = await response.json();
        } catch {
          errorData = { detail: response.statusText };
        }

        const detail = errorData?.detail;
        const message =
          typeof detail === 'string'
            ? detail
            : detail?.message || errorData?.message || `Request failed with status ${response.status}`;
        const errorCode = typeof detail === 'object' ? detail?.error_code : undefined;

        throw new AttendXApiError(message, response.status, errorCode, errorData);
      }

      return (await response.json()) as T;
    } catch (err: any) {
      if (err instanceof AttendXApiError) {
        throw err;
      }
      throw new AttendXApiError(
        err.message || 'Unable to communicate with AttendX backend server.',
        0
      );
    }
  }

  // ============================================================================
  // 1. Authentication Endpoints
  // ============================================================================

  /**
   * Authenticate educator/admin and automatically store bearer token
   */
  public async login(email: string, password: string): Promise<LoginResponse> {
    const data = await this.request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setAuthToken(data.access_token);
    return data;
  }

  public logout() {
    this.setAuthToken(null);
  }

  // ============================================================================
  // 2. Real-Time Analytics Telemetry
  // ============================================================================

  /**
   * GET /api/analytics/realtime
   * Returns live presence counts, attendance rate, and the latest 10 verification events
   */
  public async getRealtimeAnalytics(
    sessionId?: number
  ): Promise<RealtimeAnalyticsResponse> {
    const query = sessionId ? `?session_id=${sessionId}` : '';
    return this.request<RealtimeAnalyticsResponse>(`/analytics/realtime${query}`, {
      method: 'GET',
    });
  }

  // ============================================================================
  // 3. Biometric Attendance Verification (Face Embedding + Liveness + Geofence)
  // ============================================================================

  /**
   * POST /api/attendance/verify
   * Submits facial embedding vector, anti-spoof liveness score, and device GPS telemetry.
   * Enforces 20m geofence perimeter before recording attendance.
   */
  public async verifyAttendance(
    payload: AttendanceVerifyRequest
  ): Promise<AttendanceVerifyResponse> {
    return this.request<AttendanceVerifyResponse>('/attendance/verify', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // ============================================================================
  // 4. Historical Attendance Reports & Filtered Audits
  // ============================================================================

  /**
   * GET /api/attendance/reports
   * Retrieves paginated attendance audit logs with status filters, date ranges, and summary counts
   */
  public async getAttendanceReports(
    filters: AttendanceReportsFilter = {}
  ): Promise<AttendanceReportsResponse> {
    const params = new URLSearchParams();

    if (filters.session_id) params.append('session_id', filters.session_id.toString());
    if (filters.status) params.append('status', filters.status);
    if (filters.start_date) params.append('start_date', filters.start_date);
    if (filters.end_date) params.append('end_date', filters.end_date);
    if (filters.student_id) params.append('student_id', filters.student_id.toString());
    if (filters.search) params.append('search', filters.search);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());

    const queryString = params.toString() ? `?${params.toString()}` : '';
    return this.request<AttendanceReportsResponse>(`/attendance/reports${queryString}`, {
      method: 'GET',
    });
  }

  // ============================================================================
  // 5. Lecture Session Orchestration
  // ============================================================================

  /**
   * POST /api/session/start
   * Initiates a live attendance session with classroom GPS coordinates and 20m perimeter
   */
  public async startSession(
    payload: StartSessionRequest
  ): Promise<SessionResponse> {
    return this.request<SessionResponse>('/session/start', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * POST /api/session/stop
   * Concludes an active class attendance window
   */
  public async stopSession(sessionId: number): Promise<SessionResponse> {
    return this.request<SessionResponse>('/session/stop', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    });
  }

  /**
   * GET /api/session/active
   * Lists currently active lecture sessions
   */
  public async getActiveSessions(): Promise<SessionResponse[]> {
    return this.request<SessionResponse[]>('/session/active', {
      method: 'GET',
    });
  }

  // ============================================================================
  // 6. UI Adapter Helper: Map API Telemetry to Dashboard Activity Logs
  // ============================================================================

  /**
   * Converts RealtimeAnalyticsResponse recent logs into the ActivityLog UI format
   */
  public adaptRecentLogsToActivityLogs(
    recentLogs: RealtimeAnalyticsResponse['recent_logs']
  ): ActivityLog[] {
    return recentLogs.map((log) => {
      const dateObj = new Date(log.timestamp);
      const timeStr = !isNaN(dateObj.getTime())
        ? dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        : log.timestamp;

      let uiStatus: ActivityLog['status'] = 'PRESENT';
      if (log.status === 'SPOOF_DETECTED') uiStatus = 'SPOOF_DETECTED';
      else if (log.status === 'ABSENT') uiStatus = 'BUNK_FLAGGED';

      return {
        id: `api-log-${log.id}`,
        studentName: log.student_name,
        rollNumber: log.roll_number || 'UNREGISTERED',
        avatarUrl: log.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100',
        timestamp: timeStr,
        status: uiStatus,
        confidenceScore: log.confidence_score,
        verificationMethod: log.verification_method,
        note:
          log.status === 'PRESENT'
            ? `Verified with ${(log.confidence_score * 100).toFixed(1)}% match`
            : log.status === 'SPOOF_DETECTED'
            ? 'Anti-spoofing alert: presentation attack blocked'
            : 'Unexcused absence flagged',
      };
    });
  }
}

export const attendxService = new AttendXService();
export default attendxService;
