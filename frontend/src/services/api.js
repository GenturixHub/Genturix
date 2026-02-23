const API_URL = process.env.REACT_APP_BACKEND_URL;

// Use XMLHttpRequest to avoid any fetch interceptors that may be consuming the response body
const apiRequest = (url, options = {}) => {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const method = options.method || 'GET';
    
    xhr.open(method, url, true);
    xhr.timeout = 30000;
    
    // SECURITY: Include credentials (cookies) for cross-origin requests
    // This is needed for httpOnly cookie authentication
    if (options.credentials === 'include') {
      xhr.withCredentials = true;
    }
    
    // Set headers
    const headers = options.headers || {};
    Object.keys(headers).forEach(key => {
      xhr.setRequestHeader(key, headers[key]);
    });
    
    xhr.onload = function() {
      const responseText = xhr.responseText;
      const status = xhr.status;
      
      if (status >= 200 && status < 300) {
        // Success - create a response-like object
        resolve({
          ok: true,
          status: status,
          json: async () => JSON.parse(responseText || '{}'),
          text: async () => responseText
        });
      } else {
        // Error - parse the response body
        let errorData = { detail: `Error del servidor (${status})` };
        let errorMessage = errorData.detail;
        
        if (responseText) {
          try {
            errorData = JSON.parse(responseText);
            errorMessage = errorData.detail || errorData.message || errorMessage;
          } catch {
            errorMessage = responseText;
            errorData = { detail: responseText };
          }
        }
        
        const error = new Error(errorMessage);
        error.status = status;
        error.data = errorData;
        reject(error);
      }
    };
    
    xhr.onerror = function() {
      const error = new Error('Error de conexión. Por favor verifica tu red.');
      error.status = 0;
      error.data = { detail: error.message };
      reject(error);
    };
    
    xhr.ontimeout = function() {
      const error = new Error('La solicitud tardó demasiado. Intenta de nuevo.');
      error.status = 408;
      error.data = { detail: error.message };
      reject(error);
    };
    
    // Send body if provided
    if (options.body) {
      xhr.send(options.body);
    } else {
      xhr.send();
    }
  });
};

// Storage keys must match AuthContext for session persistence
// SECURITY: REFRESH_TOKEN removed - now managed via httpOnly cookie
const STORAGE_KEYS = {
  ACCESS_TOKEN: 'genturix_access_token',
};

class ApiService {
  async request(endpoint, options = {}) {
    const url = `${API_URL}/api${endpoint}`;
    const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }

    try {
      const response = await apiRequest(url, {
        ...options,
        headers,
      });
      
      // Successful response
      return response;
      
    } catch (error) {
      // Handle 401 - try to refresh token via httpOnly cookie
      if (error.status === 401) {
        try {
          const refreshResponse = await window.fetch(`${API_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',  // SECURITY: Send httpOnly cookie
            body: JSON.stringify({}),  // Empty body, token comes from cookie
          });

          if (refreshResponse.ok) {
            const data = await refreshResponse.json();
            localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, data.access_token);
            
            // Retry original request with new token
            headers['Authorization'] = `Bearer ${data.access_token}`;
            return await apiRequest(url, { ...options, headers });
          }
        } catch (e) {
          // Refresh failed, clear storage
          localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
          window.location.href = '/login';
          throw error;
        }
        // Refresh failed, clear storage
        localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
        window.location.href = '/login';
      }
      
      // Re-throw the error for other status codes
      throw error;
    }
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
  changePassword = (currentPassword, newPassword, confirmPassword) => 
    this.post('/auth/change-password', { 
      current_password: currentPassword, 
      new_password: newPassword,
      confirm_password: confirmPassword
    });

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

  // General Notifications (Admin/Guard/Supervisor)
  getNotifications = (unreadOnly = false) => this.get(`/notifications${unreadOnly ? '?unread_only=true' : ''}`);
  getUnreadNotificationCount = () => this.get('/notifications/unread-count');
  markNotificationAsRead = (notificationId) => this.put(`/notifications/${notificationId}/read`);
  markAllNotificationsAsRead = () => this.put('/notifications/mark-all-read');

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
  
  // HR Data Integrity
  validateHRIntegrity = () => this.get('/hr/validate-integrity');
  cleanupInvalidGuards = (dryRun = true) => this.post(`/hr/cleanup-invalid-guards?dry_run=${dryRun}`);
  
  // Admin - User Management
  createUserByAdmin = (data) => this.post('/admin/users', data);
  getUsersByAdmin = (role = '') => {
    return this.get(`/admin/users${role ? `?role=${role}` : ''}`);
  };
  resetUserPassword = (userId) => this.post(`/admin/users/${userId}/reset-password`, {});
  
  // Super Admin - Condo Admin Creation
  createCondoAdmin = (condoId, data) => this.post(`/super-admin/condominiums/${condoId}/admin`, data);

  // ==================== INVITATION & ACCESS REQUESTS ====================
  // Admin: Create invitation link
  createInvitation = (data) => this.post('/invitations', data);
  
  // Admin: Get all invitations
  getInvitations = () => this.get('/invitations');
  
  // Admin: Revoke invitation
  revokeInvitation = (invitationId) => this.delete(`/invitations/${invitationId}`);
  
  // Public: Get invitation info (no auth)
  getInvitationInfo = async (token) => {
    const response = await apiRequest(`${API_URL}/api/invitations/${token}/info`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    return response.json();
  };
  
  // Public: Submit access request (no auth)
  submitAccessRequest = async (token, data) => {
    const response = await apiRequest(`${API_URL}/api/invitations/${token}/request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  };
  
  // Public: Check request status (no auth)
  getAccessRequestStatus = async (token, email) => {
    const response = await apiRequest(`${API_URL}/api/invitations/${token}/request-status?email=${encodeURIComponent(email)}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    return response.json();
  };
  
  // Admin: Get access requests
  getAccessRequests = (status = 'all') => this.get(`/access-requests${status !== 'all' ? `?status=${status}` : ''}`);
  
  // Admin: Get pending count
  getAccessRequestsCount = () => this.get('/access-requests/count');
  
  // Admin: Approve or reject request
  processAccessRequest = (requestId, action, message = '', sendEmail = true) => {
    return this.post(`/access-requests/${requestId}/action`, {
      action,
      message,
      send_email: sendEmail
    });
  };

  // ==================== CONDOMINIUM SETTINGS ====================
  // Admin: Get condominium settings
  getCondominiumSettings = () => this.get('/admin/condominium-settings');
  
  // Admin: Update condominium settings
  updateCondominiumSettings = (settings) => this.put('/admin/condominium-settings', settings);
  
  // Public: Get settings for current user's condominium (read-only)
  getPublicCondominiumSettings = () => this.get('/condominium-settings/public');

  // ==================== SAAS BILLING ====================
  // Get billing info for current condominium
  getBillingInfo = () => this.get('/billing/info');
  
  // Check if can create a new user
  canCreateUser = () => this.get('/billing/can-create-user');
  
  // Upgrade seats - creates Stripe checkout session
  upgradeSeats = (additionalSeats, originUrl = window.location.origin) => {
    const params = new URLSearchParams({ origin_url: originUrl });
    return this.post(`/billing/upgrade-seats?${params.toString()}`, { additional_seats: additionalSeats });
  };
  
  // Get billing transaction history
  getBillingHistory = () => this.get('/billing/history');
  
  // SuperAdmin: Get all condominiums billing overview
  getAllCondominiumsBilling = () => this.get('/super-admin/billing/overview');
  
  // SuperAdmin: Update condominium billing settings
  updateCondominiumBilling = (condoId, data) => {
    const params = new URLSearchParams();
    if (data.paid_seats !== undefined) params.append('paid_seats', data.paid_seats);
    if (data.billing_status) params.append('billing_status', data.billing_status);
    if (data.stripe_customer_id) params.append('stripe_customer_id', data.stripe_customer_id);
    if (data.stripe_subscription_id) params.append('stripe_subscription_id', data.stripe_subscription_id);
    return this.patch(`/super-admin/condominiums/${condoId}/billing?${params.toString()}`);
  };

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
  
  // ==================== SEAT MANAGEMENT ====================
  getSeatUsage = () => this.get('/admin/seat-usage');
  validateSeatReduction = (newSeatLimit) => this.post('/admin/validate-seat-reduction', { new_seat_limit: newSeatLimit });
  updateUserStatusV2 = (userId, status, reason = null) => 
    this.patch(`/admin/users/${userId}/status-v2`, { status, reason });
  deleteUser = (userId) => this.delete(`/admin/users/${userId}`);
  canCreateUser = (role = 'Residente') => this.get(`/billing/can-create-user?role=${role}`);

  // ==================== PASSWORD RESET (Admin) ====================
  adminResetPassword = (userId) => this.post(`/admin/users/${userId}/reset-password`);
  verifyResetToken = (token) => this.get(`/auth/verify-reset-token?token=${encodeURIComponent(token)}`);
  completePasswordReset = (token, newPassword) => 
    this.post('/auth/reset-password-complete', { token, new_password: newPassword });

  // Condominiums (Multi-tenant)
  getCondominiums = () => this.get('/condominiums');
  getCondominium = (id) => this.get(`/condominiums/${id}`);
  // Production condominium (with billing)
  createCondominium = (data) => this.post('/condominiums', data);
  // Demo condominium (no billing, fixed seats)
  createDemoCondominium = (data) => this.post('/superadmin/condominiums/demo', data);
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
  resetAllData = () => this.post('/super-admin/reset-all-data');
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
  validateOnboardingField = (field, value) => this.post('/super-admin/onboarding/validate', { field, value });
  createCondominiumOnboarding = (wizardData) => this.post('/super-admin/onboarding/create-condominium', wizardData);
  
  // Super Admin - Demo with Test Data
  createDemoWithTestData = (data) => this.post('/superadmin/condominiums/demo-with-data', data);

  // Super Admin - Pricing Management (SaaS)
  getGlobalPricing = () => this.get('/super-admin/pricing/global');
  updateGlobalPricing = (defaultSeatPrice, currency = 'USD') => 
    this.put('/super-admin/pricing/global', { default_seat_price: defaultSeatPrice, currency });
  getPricingByCondominium = () => this.get('/super-admin/pricing/condominiums');
  setCondominiumPriceOverride = (condoId, seatPriceOverride) => {
    const params = new URLSearchParams();
    params.append('seat_price_override', seatPriceOverride);
    return this.patch(`/super-admin/condominiums/${condoId}/pricing?${params.toString()}`);
  };
  removeCondominiumPriceOverride = (condoId) => {
    const params = new URLSearchParams();
    params.append('seat_price_override', '0');  // 0 or negative removes override
    return this.patch(`/super-admin/condominiums/${condoId}/pricing?${params.toString()}`);
  };

  // Profile - Public View
  getPublicProfile = (userId) => this.get(`/profile/${userId}`);
  
  // Profile Directory - All users in same condominium
  getCondominiumDirectory = () => this.get('/profile/directory/condominium');

  // Language Settings
  updateLanguage = (language) => this.patch('/profile/language', { language });

  // ==================== RESERVATIONS ====================
  // Areas
  getReservationAreas = () => this.get('/reservations/areas');
  createReservationArea = (data) => this.post('/reservations/areas', data);
  updateReservationArea = (areaId, data) => this.patch(`/reservations/areas/${areaId}`, data);
  deleteReservationArea = (areaId) => this.delete(`/reservations/areas/${areaId}`);
  getAreaAvailability = (areaId, date) => this.get(`/reservations/availability/${areaId}?date=${date}`);
  // NEW: Smart availability with behavior-based slot calculation
  getSmartAvailability = (areaId, date) => this.get(`/reservations/smart-availability/${areaId}?date=${date}`);
  
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
  updateReservation = (reservationId, data) => this.patch(`/reservations/${reservationId}`, data);
  updateReservationStatus = (reservationId, data) => this.patch(`/reservations/${reservationId}`, data);
  cancelReservation = (reservationId, reason = null) => this.delete(`/reservations/${reservationId}`, reason ? { reason } : null);
  getReservationAvailability = (areaId, date) => this.get(`/reservations/availability/${areaId}?date=${date}`);

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
  getResidentUnreadNotificationCount = () => this.get('/resident/visitor-notifications/unread-count');
  markNotificationRead = (notificationId) => this.put(`/resident/visitor-notifications/${notificationId}/read`);
  markAllNotificationsRead = () => this.put('/resident/visitor-notifications/read-all');
  
  // Resident Visit History (Advanced Module)
  getResidentVisitHistory = (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.filter_period) queryParams.append('filter_period', params.filter_period);
    if (params.date_from) queryParams.append('date_from', params.date_from);
    if (params.date_to) queryParams.append('date_to', params.date_to);
    if (params.visitor_type) queryParams.append('visitor_type', params.visitor_type);
    if (params.status) queryParams.append('status', params.status);
    if (params.search) queryParams.append('search', params.search);
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.page_size) queryParams.append('page_size', params.page_size.toString());
    const queryString = queryParams.toString();
    return this.get(`/resident/visit-history${queryString ? `?${queryString}` : ''}`);
  };
  exportResidentVisitHistory = (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.filter_period) queryParams.append('filter_period', params.filter_period);
    if (params.date_from) queryParams.append('date_from', params.date_from);
    if (params.date_to) queryParams.append('date_to', params.date_to);
    if (params.visitor_type) queryParams.append('visitor_type', params.visitor_type);
    if (params.status) queryParams.append('status', params.status);
    const queryString = queryParams.toString();
    return this.get(`/resident/visit-history/export${queryString ? `?${queryString}` : ''}`);
  };
  
  // Guard endpoints
  getAuthorizationsForGuard = (search = '', includeUsed = false) => {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (includeUsed) params.append('include_used', 'true');
    const queryString = params.toString();
    return this.get(`/guard/authorizations${queryString ? `?${queryString}` : ''}`);
  };
  guardCheckIn = (data) => this.post('/guard/checkin', data);
  guardCheckOut = (entryId, notes = '') => this.post(`/guard/checkout/${entryId}`, { notes });
  getEntriesToday = () => this.get('/guard/entries-today');
  getVisitorsInside = () => this.get('/guard/visitors-inside');
  getVisitsSummary = () => this.get('/guard/visits-summary'); // For Visitas tab - READ-ONLY view
  cleanupAuthorizations = () => this.post('/guard/cleanup-authorizations', {}); // Fix legacy used authorizations
  diagnoseAuthorizations = () => this.get('/guard/diagnose-authorizations'); // Debug authorization state
  
  // Audit & History
  getAuthorizationHistory = (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return this.get(`/authorizations/history${queryString ? `?${queryString}` : ''}`);
  };
  getAuthorizationStats = () => this.get('/authorizations/stats');
  // ==================== CONFIG ====================
  getDevModeStatus = () => this.get('/config/dev-mode');  // DEPRECATED: Use getTenantEnvironment
  getTenantEnvironment = () => this.get('/config/tenant-environment');
  getEmailStatus = () => this.get('/config/email-status');
  setEmailStatus = (enabled) => this.post('/config/email-status', { email_enabled: enabled });
}

export const api = new ApiService();
export default api;
