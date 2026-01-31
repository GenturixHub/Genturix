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
      // Parse error only once and create a structured error
      let errorData = { detail: 'Request failed' };
      try {
        errorData = await response.json();
        console.log('API Error Response:', errorData);
      } catch (e) {
        console.log('Failed to parse error JSON:', e);
        // If JSON parsing fails, use default error
      }
      
      // Create error with status code for proper handling
      const errorMessage = errorData.detail || errorData.message || `API error: ${response.status}`;
      const error = new Error(errorMessage);
      error.status = response.status;
      error.data = errorData;
      throw error;
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

  async delete(endpoint, data = null) {
    const response = await this.request(endpoint, { 
      method: 'DELETE',
      body: data ? JSON.stringify(data) : undefined,
    });
    // If the response has content, return json, otherwise return empty
    const text = await response.text();
    return text ? JSON.parse(text) : {};
  }

  async patch(endpoint, data) {
    const response = await this.request(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
    return response.json();
  }

  // Auth endpoints
  seedDemoData = () => this.post('/seed-demo-data');

  // Dashboard
  getDashboardStats = () => this.get('/dashboard/stats');
  getRecentActivity = () => this.get('/dashboard/recent-activity');

  // Security
  triggerPanic = (data) => this.post('/security/panic', data);
  getPanicEvents = () => this.get('/security/panic-events');
  resolvePanic = (eventId, notes = '') => this.put(`/security/panic/${eventId}/resolve`, { notes });
  createAccessLog = (data) => this.post('/security/access-log', data);
  getAccessLogs = () => this.get('/security/access-logs');
  getGuardLogbook = () => this.get('/security/logbook');
  getActiveGuards = () => this.get('/security/active-guards');
  getSecurityStats = () => this.get('/security/dashboard-stats');
  
  // Guard Module (for Guard UI)
  getGuardHistory = (historyType = '') => this.get(`/guard/history${historyType ? `?history_type=${historyType}` : ''}`);
  getGuardMyShift = () => this.get('/guard/my-shift');
  getGuardMyAbsences = () => this.get('/guard/my-absences');

  // Resident notifications
  getResidentNotifications = () => this.get('/resident/notifications');
  
  // Resident Alert History
  getResidentAlerts = () => this.get('/resident/my-alerts');

  // Visitor Pre-Registration (Resident creates, Guard executes)
  preRegisterVisitor = (data) => this.post('/visitors/pre-register', data);
  getMyVisitors = () => this.get('/visitors/my-visitors');
  cancelVisitor = (visitorId) => this.delete(`/visitors/${visitorId}`);
  getPendingVisitors = (search = '') => this.get(`/visitors/pending${search ? `?search=${encodeURIComponent(search)}` : ''}`);
  registerVisitorEntry = (visitorId, notes = '') => this.post(`/visitors/${visitorId}/entry`, { visitor_id: visitorId, notes });
  registerVisitorExit = (visitorId, notes = '') => this.post(`/visitors/${visitorId}/exit`, { visitor_id: visitorId, notes });
  getAllVisitors = (status = '') => this.get(`/visitors/all${status ? `?status=${status}` : ''}`);

  // HR - Guards
  createGuard = (data) => this.post('/hr/guards', data);
  getGuards = () => this.get('/hr/guards');
  getGuard = (id) => this.get(`/hr/guards/${id}`);
  updateGuard = (id, data) => this.put(`/hr/guards/${id}`, data);
  
  // HR - Shifts
  createShift = (data) => this.post('/hr/shifts', data);
  getShifts = (status = '', guardId = '') => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (guardId) params.append('guard_id', guardId);
    const query = params.toString();
    return this.get(`/hr/shifts${query ? `?${query}` : ''}`);
  };
  getShift = (id) => this.get(`/hr/shifts/${id}`);
  updateShift = (id, data) => this.put(`/hr/shifts/${id}`, data);
  deleteShift = (id) => this.delete(`/hr/shifts/${id}`);
  
  // HR - Clock In/Out
  clockInOut = (type) => this.post('/hr/clock', { type });
  getClockStatus = () => this.get('/hr/clock/status');
  getClockHistory = (employeeId = '', startDate = '', endDate = '') => {
    const params = new URLSearchParams();
    if (employeeId) params.append('employee_id', employeeId);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    const query = params.toString();
    return this.get(`/hr/clock/history${query ? `?${query}` : ''}`);
  };
  
  // HR - Absences
  createAbsence = (data) => this.post('/hr/absences', data);
  getAbsences = (status = '', employeeId = '') => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (employeeId) params.append('employee_id', employeeId);
    const query = params.toString();
    return this.get(`/hr/absences${query ? `?${query}` : ''}`);
  };
  getAbsence = (id) => this.get(`/hr/absences/${id}`);
  approveAbsence = (id, notes = '') => this.put(`/hr/absences/${id}/approve${notes ? `?admin_notes=${encodeURIComponent(notes)}` : ''}`);
  rejectAbsence = (id, notes = '') => this.put(`/hr/absences/${id}/reject${notes ? `?admin_notes=${encodeURIComponent(notes)}` : ''}`);
  
  // HR - Payroll
  getPayroll = () => this.get('/hr/payroll');

  // HR - Recruitment
  createCandidate = (data) => this.post('/hr/candidates', data);
  getCandidates = (status = '', position = '') => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (position) params.append('position', position);
    const query = params.toString();
    return this.get(`/hr/candidates${query ? `?${query}` : ''}`);
  };
  getCandidate = (id) => this.get(`/hr/candidates/${id}`);
  updateCandidate = (id, data) => this.put(`/hr/candidates/${id}`, data);
  hireCandidate = (id, data) => this.post(`/hr/candidates/${id}/hire`, data);
  rejectCandidate = (id, reason = '') => this.put(`/hr/candidates/${id}/reject${reason ? `?reason=${encodeURIComponent(reason)}` : ''}`);
  
  // HR - Employee Management
  createEmployee = (data) => this.post('/hr/employees', data);
  deactivateEmployee = (guardId) => this.put(`/hr/employees/${guardId}/deactivate`);
  activateEmployee = (guardId) => this.put(`/hr/employees/${guardId}/activate`);
  
  // HR - Performance Evaluations
  createEvaluation = (data) => this.post('/hr/evaluations', data);
  getEvaluations = (employeeId = '') => {
    return this.get(`/hr/evaluations${employeeId ? `?employee_id=${employeeId}` : ''}`);
  };
  getEvaluation = (id) => this.get(`/hr/evaluations/${id}`);
  getEmployeeEvaluationSummary = (employeeId) => this.get(`/hr/evaluations/employee/${employeeId}/summary`);
  getEvaluableEmployees = () => this.get('/hr/evaluable-employees');
  
  // Admin - User Management
  createUserByAdmin = (data) => this.post('/admin/users', data);
  getUsersByAdmin = (role = '') => {
    return this.get(`/admin/users${role ? `?role=${role}` : ''}`);
  };
  
  // Super Admin - Condo Admin Creation
  createCondoAdmin = (condoId, data) => this.post(`/super-admin/condominiums/${condoId}/admin`, data);

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

  // Condominiums (Multi-tenant)
  getCondominiums = () => this.get('/condominiums');
  getCondominium = (id) => this.get(`/condominiums/${id}`);
  createCondominium = (data) => this.post('/condominiums', data);
  updateCondominium = (id, data) => this.patch(`/condominiums/${id}`, data);
  deleteCondominium = (id) => this.delete(`/condominiums/${id}`);
  getCondominiumUsers = (id) => this.get(`/condominiums/${id}/users`);
  getCondominiumBilling = (id) => this.get(`/condominiums/${id}/billing`);
  updateCondoModule = (condoId, moduleName, enabled) => 
    this.patch(`/condominiums/${condoId}/modules/${moduleName}?enabled=${enabled}`);

  // Super Admin
  getPlatformStats = () => this.get('/super-admin/stats');
  getAllUsersGlobal = (condoId = '', role = '') => {
    const params = new URLSearchParams();
    if (condoId) params.append('condo_id', condoId);
    if (role) params.append('role', role);
    return this.get(`/super-admin/users${params.toString() ? '?' + params.toString() : ''}`);
  };
  lockUser = (userId) => this.put(`/super-admin/users/${userId}/lock`);
  unlockUser = (userId) => this.put(`/super-admin/users/${userId}/unlock`);
  makeCondoDemo = (condoId, maxUsers = 10) => 
    this.post(`/super-admin/condominiums/${condoId}/make-demo?max_users=${maxUsers}`);
  resetDemoData = (condoId) => this.post(`/super-admin/condominiums/${condoId}/reset-demo`);
  updateCondoPricing = (condoId, discountPercent, plan) => {
    const params = new URLSearchParams();
    params.append('discount_percent', discountPercent);
    params.append('plan', plan);
    return this.patch(`/super-admin/condominiums/${condoId}/pricing?${params.toString()}`);
  };
  updateCondoStatus = (condoId, status) => 
    this.patch(`/super-admin/condominiums/${condoId}/status?status=${status}`);
  getSuperAdminAudit = (module = 'super_admin', limit = 100) => 
    this.get(`/super-admin/audit?module=${module}&limit=${limit}`);
  
  // Super Admin - Permanent Deletion (requires password)
  permanentlyDeleteCondominium = (condoId, password) =>
    this.delete(`/super-admin/condominiums/${condoId}`, { password });

  // Super Admin - Onboarding Wizard
  getOnboardingTimezones = () => this.get('/super-admin/onboarding/timezones');
  createCondominiumOnboarding = (wizardData) => this.post('/super-admin/onboarding/create-condominium', wizardData);

  // Profile - Public View
  getPublicProfile = (userId) => this.get(`/profile/${userId}`);
  
  // Profile Directory - All users in same condominium
  getCondominiumDirectory = () => this.get('/profile/directory/condominium');

  // ==================== RESERVATIONS ====================
  // Areas
  getReservationAreas = () => this.get('/reservations/areas');
  createReservationArea = (data) => this.post('/reservations/areas', data);
  updateReservationArea = (areaId, data) => this.patch(`/reservations/areas/${areaId}`, data);
  deleteReservationArea = (areaId) => this.delete(`/reservations/areas/${areaId}`);
  getAreaAvailability = (areaId, date) => this.get(`/reservations/availability/${areaId}?date=${date}`);
  
  // Legacy aliases for backward compatibility
  getAreas = () => this.get('/reservations/areas');
  createArea = (data) => this.post('/reservations/areas', data);
  updateArea = (areaId, data) => this.patch(`/reservations/areas/${areaId}`, data);
  deleteArea = (areaId) => this.delete(`/reservations/areas/${areaId}`);
  
  // Reservations
  getReservations = (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return this.get(`/reservations${queryString ? `?${queryString}` : ''}`);
  };
  getTodayReservations = () => this.get('/reservations/today');
  createReservation = (data) => this.post('/reservations', data);
  updateReservationStatus = (reservationId, data) => this.patch(`/reservations/${reservationId}`, data);

  // ==================== PUSH NOTIFICATIONS ====================
  getVapidPublicKey = () => this.get('/push/vapid-public-key');
  subscribeToPush = (subscription) => this.post('/push/subscribe', { subscription });
  unsubscribeFromPush = (subscription) => this.delete('/push/unsubscribe', { subscription });
  getPushStatus = () => this.get('/push/status');

  // ==================== ADVANCED VISITOR AUTHORIZATIONS ====================
  // Resident endpoints
  createAuthorization = (data) => this.post('/authorizations', data);
  getMyAuthorizations = (status = '') => this.get(`/authorizations/my${status ? `?status=${status}` : ''}`);
  getAuthorization = (authId) => this.get(`/authorizations/${authId}`);
  updateAuthorization = (authId, data) => this.patch(`/authorizations/${authId}`, data);
  deleteAuthorization = (authId) => this.delete(`/authorizations/${authId}`);
  
  // Resident notifications
  getVisitorNotifications = (unreadOnly = false) => this.get(`/resident/visitor-notifications${unreadOnly ? '?unread_only=true' : ''}`);
  markNotificationRead = (notificationId) => this.put(`/resident/visitor-notifications/${notificationId}/read`);
  markAllNotificationsRead = () => this.put('/resident/visitor-notifications/read-all');
  
  // Guard endpoints
  getAuthorizationsForGuard = (search = '') => this.get(`/guard/authorizations${search ? `?search=${encodeURIComponent(search)}` : ''}`);
  guardCheckIn = (data) => this.post('/guard/checkin', data);
  guardCheckOut = (entryId, notes = '') => this.post(`/guard/checkout/${entryId}`, { notes });
  getVisitorsInside = () => this.get('/guard/visitors-inside');
  
  // Audit & History
  getAuthorizationHistory = (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return this.get(`/authorizations/history${queryString ? `?${queryString}` : ''}`);
  };
  getAuthorizationStats = () => this.get('/authorizations/stats');
  // ==================== CONFIG ====================
  getDevModeStatus = () => this.get('/config/dev-mode');
  getEmailStatus = () => this.get('/config/email-status');
  setEmailStatus = (enabled) => this.post('/config/email-status', { email_enabled: enabled });
}

export const api = new ApiService();
export default api;
