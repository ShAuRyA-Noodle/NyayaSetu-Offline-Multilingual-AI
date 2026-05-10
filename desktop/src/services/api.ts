import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import toast from 'react-hot-toast';

// Environment guard: warn (do not crash) if production lacks VITE_API_URL
if (!import.meta.env.VITE_API_URL && import.meta.env.PROD === true) {
  // eslint-disable-next-line no-console
  console.error(
    '[NyayaSetu] VITE_API_URL is not defined in a production build. ' +
      'Falling back to http://localhost:8001 — this will NOT work for end users. ' +
      'Set VITE_API_URL in your Vercel environment variables.'
  );
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: inject auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: surface user-friendly toasts and redirect on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const isNetworkError = !error.response;

    if (status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      // BrowserRouter-safe redirect (replaces previous hash-based redirect)
      if (window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    } else if (status === 403) {
      toast.error('Permission denied');
    } else if (status === 422) {
      const detail = error.response?.data?.detail;
      const msg =
        Array.isArray(detail) && detail.length > 0
          ? detail.map((d: any) => d.msg || d).join(', ')
          : typeof detail === 'string'
          ? detail
          : 'Validation error';
      toast.error(msg);
    } else if (typeof status === 'number' && status >= 500) {
      toast.error('Server error. Please try again in a moment.');
    } else if (isNetworkError) {
      toast.error('Network error. Check your connection.');
    }

    return Promise.reject(error);
  }
);

// ============================================================================
// API SERVICE
// ============================================================================

export const apiService = {
  // ---- Raw axios client (for blob fetches with auth, etc.) ----
  client: api,

  // ---- Health ----
  checkHealth: async () => (await api.get('/health')).data,

  // ---- Auth ----
  login: async (username: string, password: string) =>
    (await api.post('/api/v1/auth/login', { username, password })).data,

  register: async (data: {
    username: string; email: string; password: string;
    phone?: string; role?: string; location?: string; preferred_language?: string;
    officer_code?: string; designation?: string;
    captcha_token?: string;
  }) => (await api.post('/api/v1/auth/register', data)).data,

  logout: async () => (await api.post('/api/v1/auth/logout')).data,
  logoutAll: async () => (await api.post('/api/v1/auth/logout-all')).data,
  checkAuth: async () => (await api.get('/api/v1/auth/check')).data,
  getMe: async () => (await api.get('/api/v1/auth/me')).data,
  refreshToken: async () => (await api.post('/api/v1/auth/refresh')).data,

  changePassword: async (currentPassword: string, newPassword: string) =>
    (await api.put('/api/v1/auth/change-password', { current_password: currentPassword, new_password: newPassword })).data,

  forgotPassword: async (email: string) =>
    (await api.post('/api/v1/auth/forgot-password', { email })).data,

  resetPassword: async (token: string, newPassword: string) =>
    (await api.post('/api/v1/auth/reset-password', { token, new_password: newPassword })).data,

  listSessions: async () => (await api.get('/api/v1/auth/sessions')).data,
  revokeSession: async (sessionId: number) => (await api.delete(`/api/v1/auth/sessions/${sessionId}`)).data,

  // ---- Schemes ----
  listSchemes: async () => (await api.get('/api/v1/schemes/list')).data,

  listSchemesDetailed: async () => (await api.get('/api/v1/schemes/list?detailed=true')).data,

  summarizeScheme: async (schemeName: string, language: string = 'en') =>
    (await api.post('/api/v1/summarize', { scheme_name: schemeName, language })).data,

  getSchemeDetail: async (schemeId: string) =>
    (await api.get(`/api/v1/schemes/${schemeId}`)).data,

  getMySchemes: async () => (await api.get('/api/v1/schemes/my-schemes')).data,

  getSchemeHistory: async (schemeId: string) =>
    (await api.get(`/api/v1/schemes/${schemeId}/history`)).data,

  getSchemeVersions: async (schemeId: string) =>
    (await api.get(`/api/v1/schemes/${schemeId}/versions`)).data,

  getSchemeChunks: async (schemeId: string) =>
    (await api.get(`/api/v1/schemes/${schemeId}/chunks`)).data,

  getSchemeDocument: async (schemeName: string) =>
    (await api.get(`/api/v1/schemes/by-name/${encodeURIComponent(schemeName)}/document`)).data,

  getSchemeDocumentFormatted: async (schemeName: string) =>
    (await api.get(`/api/v1/schemes/by-name/${encodeURIComponent(schemeName)}/document`, { params: { formatted: true }, timeout: 120000 })).data,

  updateSchemeMetadata: async (schemeId: string, data: Record<string, any>) =>
    (await api.put(`/api/v1/schemes/${schemeId}/metadata`, data)).data,

  deleteScheme: async (schemeId: string) =>
    (await api.delete(`/api/v1/schemes/${schemeId}`)).data,

  uploadScheme: async (file: File, schemeName?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (schemeName) formData.append('scheme_name', schemeName);
    return (await api.post('/api/v1/admin/schemes/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })).data;
  },

  assignSchemeOfficer: async (schemeId: string, officerId: number) =>
    (await api.post(`/api/v1/admin/schemes/${schemeId}/assign`, null, { params: { officer_id: officerId } })).data,

  unassignSchemeOfficer: async (schemeId: string, officerId: number) =>
    (await api.delete(`/api/v1/admin/schemes/${schemeId}/unassign/${officerId}`)).data,

  schemeAnalytics: async () => (await api.get('/api/v1/admin/schemes/analytics')).data,

  // ---- RAG Q&A ----
  askQuestion: async (question: string, language: string = 'en') =>
    (await api.post('/api/v1/ask', { question, language, top_k: 5 })).data,

  // ---- Grievances ----
  routeGrievance: async (grievanceText: string, language: string = 'en') =>
    (await api.post('/api/v1/grievances/route', { grievance_text: grievanceText, language })).data,

  submitGrievance: async (data: {
    description: string; title?: string; citizen_name?: string;
    citizen_phone?: string; citizen_email?: string; citizen_location?: string;
    category?: string; language?: string;
  }) => (await api.post('/api/v1/grievances/submit', data)).data,

  // Multipart variant supporting up to N attachments. Backend route may need
  // to accept files via UploadFile[] — see grievance_routes TODO.
  submitGrievanceWithFiles: async (
    data: {
      description: string; title?: string; citizen_name?: string;
      citizen_phone?: string; citizen_email?: string; citizen_location?: string;
      category?: string; language?: string;
    },
    files: File[],
  ) => {
    const fd = new FormData();
    Object.entries(data).forEach(([k, v]) => {
      if (v !== undefined && v !== null) fd.append(k, String(v));
    });
    files.forEach((f) => fd.append('attachments', f, f.name));
    return (await api.post('/api/v1/grievances/submit', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })).data;
  },

  getMyGrievances: async () => (await api.get('/api/v1/grievances/my')).data,

  getAssignedGrievances: async () => (await api.get('/api/v1/grievances/assigned')).data,

  getGrievanceDetail: async (grievanceId: string) =>
    (await api.get(`/api/v1/grievances/${grievanceId}`)).data,

  getGrievanceTimeline: async (grievanceId: string) =>
    (await api.get(`/api/v1/grievances/${grievanceId}/timeline`)).data,

  getDepartmentGrievances: async (department: string, status: string = 'pending', limit: number = 50) =>
    (await api.get(`/api/v1/grievances/department/${department}`, { params: { status, limit } })).data,

  getDepartmentDashboard: async (department: string) =>
    (await api.get(`/api/v1/grievances/department/${department}/dashboard`)).data,

  acceptGrievance: async (grievanceId: string, officerName: string, notes?: string) =>
    (await api.post(`/api/v1/grievances/${grievanceId}/accept`, { officer_name: officerName, notes })).data,

  rejectGrievance: async (grievanceId: string, officerName: string, reason: string) =>
    (await api.post(`/api/v1/grievances/${grievanceId}/reject`, { officer_name: officerName, reason })).data,

  resolveGrievance: async (grievanceId: string, officerName: string, resolutionNotes: string) =>
    (await api.post(`/api/v1/grievances/${grievanceId}/resolve`, { officer_name: officerName, resolution_notes: resolutionNotes })).data,

  updateGrievanceStatus: async (grievanceId: string, newStatus: string, officerName: string, notes?: string) =>
    (await api.post(`/api/v1/grievances/${grievanceId}/update-status`, { new_status: newStatus, officer_name: officerName, notes })).data,

  addGrievanceComment: async (grievanceId: string, commentText: string, commentType: string = 'note', isPublic: boolean = true) =>
    (await api.post(`/api/v1/grievances/${grievanceId}/comment`, null, { params: { comment_text: commentText, comment_type: commentType, is_public: isPublic } })).data,

  getGrievanceComments: async (grievanceId: string) =>
    (await api.get(`/api/v1/grievances/${grievanceId}/comments`)).data,

  rateGrievance: async (grievanceId: string, rating: number, feedback?: string) =>
    (await api.post(`/api/v1/grievances/${grievanceId}/rate`, null, { params: { rating, feedback_text: feedback } })).data,

  pauseSla: async (grievanceId: string, reason: string) =>
    (await api.post(`/api/v1/grievances/${grievanceId}/pause-sla`, null, { params: { reason } })).data,

  resumeSla: async (grievanceId: string) =>
    (await api.post(`/api/v1/grievances/${grievanceId}/resume-sla`)).data,

  trackGrievance: async (grievanceId: string) =>
    (await api.get(`/api/v1/grievances/${grievanceId}/track`)).data,

  getDepartmentInbox: async () => (await api.get('/api/v1/grievances/department-inbox')).data,

  getAllGrievances: async (status?: string, department?: string, limit: number = 100) =>
    (await api.get('/api/v1/grievances/all', { params: { status, department, limit } })).data,

  getGrievanceStats: async () => (await api.get('/api/v1/grievances/stats')).data,

  getGrievanceAnalytics: async () => (await api.get('/api/v1/grievances/analytics')).data,

  slaDashboard: async () => (await api.get('/api/v1/grievances/sla/dashboard')).data,

  slaBreaches: async () => (await api.get('/api/v1/grievances/sla/breaches')).data,

  // ---- Notifications ----
  getNotifications: async () => (await api.get('/api/v1/grievances/notifications')).data,
  markNotificationRead: async (id: number) => (await api.post(`/api/v1/grievances/notifications/${id}/read`)).data,
  markAllNotificationsRead: async () => (await api.post('/api/v1/grievances/notifications/read-all')).data,
  getNotificationCount: async () => (await api.get('/api/v1/grievances/notifications/count')).data,

  // ---- Notices ----
  generateNotice: async (request: { scheme_name: string; notice_type: string; language: string; effective_date?: string }) =>
    (await api.post('/api/v1/notices/generate', request)).data,

  draftNotice: async (request: { scheme_name: string; notice_type: string; language: string; effective_date?: string }) =>
    (await api.post('/api/v1/draft-notice', request)).data,

  saveNoticeDraft: async (data: {
    scheme_name: string; notice_type: string; subject: string;
    body: string; formatted_notice?: string; language?: string; effective_date?: string;
  }) => (await api.post('/api/v1/notices/draft', data)).data,

  listNotices: async (status?: string) =>
    (await api.get('/api/v1/notices', { params: status ? { status } : {} })).data,

  getNotice: async (noticeId: string) => (await api.get(`/api/v1/notices/${noticeId}`)).data,

  updateNotice: async (noticeId: string, data: Record<string, any>) =>
    (await api.put(`/api/v1/notices/${noticeId}`, data)).data,

  deleteNotice: async (noticeId: string) => (await api.delete(`/api/v1/notices/${noticeId}`)).data,

  submitNoticeForReview: async (noticeId: string) =>
    (await api.post(`/api/v1/notices/${noticeId}/submit-review`)).data,

  reviewNotice: async (noticeId: string, approved: boolean, notes?: string) =>
    (await api.post(`/api/v1/notices/${noticeId}/review`, null, { params: { approved, review_notes: notes } })).data,

  publishNotice: async (noticeId: string) =>
    (await api.post(`/api/v1/notices/${noticeId}/publish`)).data,

  withdrawNotice: async (noticeId: string, reason: string) =>
    (await api.post(`/api/v1/notices/${noticeId}/withdraw`, null, { params: { reason } })).data,

  getPublicNotices: async (limit: number = 20, offset: number = 0) =>
    (await api.get('/api/v1/notices/public', { params: { limit, offset } })).data,

  getPublicNoticeDetail: async (noticeId: string) =>
    (await api.get(`/api/v1/notices/public/${noticeId}`)).data,

  // ---- Admin ----
  listUsers: async (role?: string) =>
    (await api.get('/api/v1/admin/users', { params: role ? { role } : {} })).data,

  getUser: async (userId: number) => (await api.get(`/api/v1/admin/users/${userId}`)).data,

  updateUser: async (userId: number, data: Record<string, any>) =>
    (await api.put(`/api/v1/admin/users/${userId}`, null, { params: data })).data,

  disableUser: async (userId: number) =>
    (await api.post(`/api/v1/admin/users/${userId}/disable`)).data,

  unlockUser: async (userId: number) =>
    (await api.post(`/api/v1/admin/users/${userId}/unlock`)).data,

  getAuditLogs: async (limit: number = 50, offset: number = 0) =>
    (await api.get('/api/v1/admin/audit-logs', { params: { limit, offset } })).data,

  adminAnalyticsOverview: async () => (await api.get('/api/v1/admin/analytics/overview')).data,

  adminAnalyticsTrends: async (days: number = 30) =>
    (await api.get('/api/v1/admin/analytics/trends', { params: { days } })).data,

  officerPerformance: async () => (await api.get('/api/v1/admin/analytics/officer-performance')).data,

  systemHealth: async () => (await api.get('/api/v1/admin/system/health')).data,

  generateOfficerCode: async (department: string, designation?: string) =>
    (await api.post('/api/v1/admin/officer-codes/generate', null, { params: { department, designation } })).data,

  listOfficerCodes: async () => (await api.get('/api/v1/admin/officer-codes')).data,

  validateOfficerCode: async (code: string) =>
    (await api.get('/api/v1/admin/officer-codes/validate', { params: { code } })).data,

  clearCache: async () => (await api.post('/api/v1/admin/clear-cache')).data,

  // ---- Statistics ----
  getStats: async () => (await api.get('/stats')).data,

  // ---- SLA Config ----
  getSlaConfig: async () => (await api.get('/api/v1/grievances/admin/sla/config')).data,
  updateSlaConfig: async (department: string, config: Record<string, number>) =>
    (await api.post('/api/v1/grievances/admin/sla/config', null, { params: { department, ...config } })).data,

  // ---- NyayaVaani ----
  nyayavaaniStatus: async () => (await api.get('/api/v1/nyayavaani/status')).data,

  getNyayaVaaniSchemes: async () => (await api.get('/api/v1/nyayavaani/schemes')).data,

  transcribeAudio: async (formData: FormData) =>
    (await api.post('/api/v1/nyayavaani/transcribe', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    })).data,

  synthesizeSpeech: async (data: { text: string; language: string; voice_gender?: string }) =>
    (await api.post('/api/v1/nyayavaani/synthesize', data)).data,

  classifyIntent: async (data: { text: string; language?: string }) =>
    (await api.post('/api/v1/nyayavaani/classify-intent', data)).data,

  voiceGrievance: async (data: {
    transcription: string; language: string;
    citizen_name?: string; citizen_phone?: string; citizen_location?: string;
  }) => (await api.post('/api/v1/nyayavaani/voice-grievance', data)).data,

  getNoticeAudio: (noticeId: string, language: string = 'hi') =>
    `${API_BASE_URL}/api/v1/nyayavaani/notice/${noticeId}/audio?language=${language}`,

  getSchemeAudio: (schemeId: string, language: string = 'hi') =>
    `${API_BASE_URL}/api/v1/nyayavaani/scheme/${schemeId}/audio?language=${language}`,

  nyayavaaniLanguages: async () => (await api.get('/api/v1/nyayavaani/languages')).data,
};

export default apiService;
