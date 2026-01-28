const API_URL = process.env.REACT_APP_BACKEND_URL;

class ApiService {
  async request(endpoint, options = {}) {
    const url = `${API_URL}/api${endpoint}`;
    const accessToken = sessionStorage.getItem('accessToken');

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      // Try to refresh token
      const refreshToken = sessionStorage.getItem('refreshToken');
      if (refreshToken) {
        try {
          const refreshResponse = await fetch(`${API_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });

          if (refreshResponse.ok) {
            const data = await refreshResponse.json();
            sessionStorage.setItem('accessToken', data.access_token);
            sessionStorage.setItem('refreshToken', data.refresh_token);
            
            // Retry original request
            headers['Authorization'] = `Bearer ${data.access_token}`;
            const retryResponse = await fetch(url, { ...options, headers });
            if (!retryResponse.ok) {
              throw new Error(`API error: ${retryResponse.status}`);
            }
            return retryResponse;
          }
        } catch (e) {
          // Refresh failed, clear session
          sessionStorage.clear();
          window.location.href = '/login';
        }
      }
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response;
  }

  async get(endpoint) {
    const response = await this.request(endpoint, { method: 'GET' });
    return response.json();
  }

  async post(endpoint, data) {
    const response = await this.request(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
    return response.json();
  }

  async put(endpoint, data) {
    const response = await this.request(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
    return response.json();
  }

  async delete(endpoint) {
    await this.request(endpoint, { method: 'DELETE' });
  }

  // Auth endpoints
  seedDemoData = () => this.post('/seed-demo-data');

  // Dashboard
  getDashboardStats = () => this.get('/dashboard/stats');
  getRecentActivity = () => this.get('/dashboard/recent-activity');

  // Security
  triggerPanic = (data) => this.post('/security/panic', data);
  getPanicEvents = () => this.get('/security/panic-events');
  resolvePanic = (eventId) => this.put(`/security/panic/${eventId}/resolve`);
  createAccessLog = (data) => this.post('/security/access-log', data);
  getAccessLogs = () => this.get('/security/access-logs');
  getGuardLogbook = () => this.get('/security/logbook');
  getActiveGuards = () => this.get('/security/active-guards');
  getSecurityStats = () => this.get('/security/dashboard-stats');

  // Resident notifications
  getResidentNotifications = () => this.get('/resident/notifications');

  // HR
  createGuard = (data) => this.post('/hr/guards', data);
  getGuards = () => this.get('/hr/guards');
  getGuard = (id) => this.get(`/hr/guards/${id}`);
  createShift = (data) => this.post('/hr/shifts', data);
  getShifts = () => this.get('/hr/shifts');
  getPayroll = () => this.get('/hr/payroll');

  // School
  createCourse = (data) => this.post('/school/courses', data);
  getCourses = () => this.get('/school/courses');
  getCourse = (id) => this.get(`/school/courses/${id}`);
  enrollCourse = (data) => this.post('/school/enroll', data);
  getEnrollments = () => this.get('/school/enrollments');
  getCertificates = () => this.get('/school/certificates');
  getStudentProgress = (studentId) => this.get(`/school/student-progress/${studentId}`);

  // Payments - GENTURIX Model: $1 per user per month
  getPricing = () => this.get('/payments/pricing');
  calculatePrice = (userCount) => this.post('/payments/calculate', { user_count: userCount });
  createCheckout = (data) => {
    const params = new URLSearchParams({
      user_count: data.user_count || 1,
      origin_url: data.origin_url || window.location.origin
    });
    return this.post(`/payments/checkout?${params.toString()}`);
  };
  getPaymentStatus = (sessionId) => this.get(`/payments/status/${sessionId}`);
  getPaymentHistory = () => this.get('/payments/history');

  // Audit
  getAuditLogs = (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return this.get(`/audit/logs${query ? `?${query}` : ''}`);
  };
  getAuditStats = () => this.get('/audit/stats');

  // Users
  getUsers = () => this.get('/users');
  updateUserRoles = (userId, roles) => this.put(`/users/${userId}/roles`, roles);
  updateUserStatus = (userId, isActive) => this.put(`/users/${userId}/status`, isActive);
}

export const api = new ApiService();
export default api;
