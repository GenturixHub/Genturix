"""
PHASE 3 - BILLING MODULE FULL DECOUPLING TEST
==============================================
Tests that billing functions have been correctly decoupled from server.py
and are now imported from modules.billing.* without logic changes.

Key changes verified:
- 7 functions removed from server.py (now imported from modules.billing.service/scheduler)
- 2 models (SeatUsageResponse, SeatReductionValidation) from modules.billing.models
- Scheduler instance managed by get_scheduler_instance()
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERADMIN_CREDENTIALS = {"email": "superadmin@genturix.com", "password": "Admin123!"}
ADMIN_CREDENTIALS = {"email": "test-resident@genturix.com", "password": "Admin123!"}


class TestPhase3BillingDecoupling:
    """Test billing module decoupling - REGRESSION tests, behavior should be IDENTICAL"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session and tokens"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_superadmin_token(self):
        """Get SuperAdmin auth token"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=SUPERADMIN_CREDENTIALS
        )
        assert response.status_code == 200, f"SuperAdmin login failed: {response.text}"
        return response.json()["access_token"]
    
    def get_admin_token(self):
        """Get Admin/Resident auth token"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDENTIALS
        )
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        return response.json()["access_token"]
    
    def get_test_condo_id(self, token):
        """Get a test condominium ID for testing"""
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview?page_size=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("condominiums") and len(data["condominiums"]) > 0:
                return data["condominiums"][0]["id"]
        return None
    
    # ==================== SCHEDULER ENDPOINTS (from modules.billing.scheduler) ====================
    
    def test_scheduler_status(self):
        """GET /api/billing/scheduler/status - Uses get_scheduler_instance from module"""
        token = self.get_superadmin_token()
        response = self.session.get(
            f"{BASE_URL}/api/billing/scheduler/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Scheduler status failed: {response.text}"
        data = response.json()
        
        # Verify expected response structure
        assert "is_running" in data, "Missing is_running field"
        assert "next_run_scheduled" in data, "Missing next_run_scheduled field"
        assert "last_run" in data, "Missing last_run field"
        
        print(f"✓ Scheduler status: is_running={data['is_running']}, next_run={data['next_run_scheduled']}")
    
    def test_scheduler_run_now(self):
        """POST /api/billing/scheduler/run-now - Triggers run_daily_billing_check from module"""
        token = self.get_superadmin_token()
        response = self.session.post(
            f"{BASE_URL}/api/billing/scheduler/run-now",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Run-now failed: {response.text}"
        data = response.json()
        
        # Verify run results structure (from run_daily_billing_check)
        assert "run_date" in data, "Missing run_date field"
        assert "total_evaluated" in data, "Missing total_evaluated field"
        
        print(f"✓ Scheduler run-now: evaluated {data.get('total_evaluated', 0)} condos")
    
    def test_scheduler_history(self):
        """GET /api/billing/scheduler/history - Returns scheduler run history"""
        token = self.get_superadmin_token()
        response = self.session.get(
            f"{BASE_URL}/api/billing/scheduler/history",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Scheduler history failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Expected array of run history"
        print(f"✓ Scheduler history: {len(data)} runs recorded")
    
    # ==================== BILLING PREVIEW (uses billing models) ====================
    
    def test_billing_preview_monthly(self):
        """POST /api/billing/preview - Monthly cycle preview"""
        token = self.get_superadmin_token()
        response = self.session.post(
            f"{BASE_URL}/api/billing/preview",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "initial_units": 25,
                "billing_cycle": "monthly"
            }
        )
        
        assert response.status_code == 200, f"Preview monthly failed: {response.text}"
        data = response.json()
        
        # Verify BillingPreviewResponse model structure
        assert "seats" in data, "Missing seats field"
        assert "price_per_seat" in data, "Missing price_per_seat field"
        assert "billing_cycle" in data, "Missing billing_cycle field"
        assert "monthly_amount" in data, "Missing monthly_amount field"
        assert "yearly_amount" in data, "Missing yearly_amount field"
        assert "effective_amount" in data, "Missing effective_amount field"
        assert data["seats"] == 25, f"Expected 25 seats, got {data['seats']}"
        assert data["billing_cycle"] == "monthly", f"Expected monthly cycle, got {data['billing_cycle']}"
        
        print(f"✓ Preview monthly: {data['seats']} seats @ ${data['price_per_seat']}/seat = ${data['effective_amount']}")
    
    def test_billing_preview_yearly(self):
        """POST /api/billing/preview - Yearly cycle with discount"""
        token = self.get_superadmin_token()
        response = self.session.post(
            f"{BASE_URL}/api/billing/preview",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "initial_units": 50,
                "billing_cycle": "yearly"
            }
        )
        
        assert response.status_code == 200, f"Preview yearly failed: {response.text}"
        data = response.json()
        
        assert data["billing_cycle"] == "yearly"
        assert "yearly_discount_percent" in data, "Missing yearly_discount_percent"
        assert data["yearly_discount_percent"] > 0, "Expected yearly discount > 0"
        
        print(f"✓ Preview yearly: {data['seats']} seats, {data['yearly_discount_percent']}% discount = ${data['effective_amount']}")
    
    # ==================== PAYMENT CONFIRMATION (supports partial payments) ====================
    
    def test_confirm_payment_invalid_condo(self):
        """POST /api/billing/confirm-payment/{id} - Returns 404 for non-existent condo"""
        token = self.get_superadmin_token()
        response = self.session.post(
            f"{BASE_URL}/api/billing/confirm-payment/non-existent-id-12345",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount_paid": 100.0,
                "payment_reference": "TEST-REF",
                "notes": "Test payment"
            }
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Confirm payment returns 404 for non-existent condo")
    
    def test_confirm_payment_validation(self):
        """POST /api/billing/confirm-payment - Validates amount > 0"""
        token = self.get_superadmin_token()
        condo_id = self.get_test_condo_id(token)
        
        if not condo_id:
            pytest.skip("No test condominium found")
        
        # Try with zero/negative amount
        response = self.session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{condo_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount_paid": 0,
                "payment_reference": "TEST-REF"
            }
        )
        
        assert response.status_code == 422, f"Expected 422 for invalid amount, got {response.status_code}"
        print("✓ Confirm payment validates amount > 0")
    
    # ==================== BILLING BALANCE ====================
    
    def test_billing_balance(self):
        """GET /api/billing/balance/{id} - Returns balance info"""
        token = self.get_superadmin_token()
        condo_id = self.get_test_condo_id(token)
        
        if not condo_id:
            pytest.skip("No test condominium found")
        
        response = self.session.get(
            f"{BASE_URL}/api/billing/balance/{condo_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Balance failed: {response.text}"
        data = response.json()
        
        # Verify balance response structure
        assert "condominium_id" in data, "Missing condominium_id"
        assert "invoice_amount" in data, "Missing invoice_amount"
        assert "balance_due" in data, "Missing balance_due"
        assert "billing_status" in data, "Missing billing_status"
        
        print(f"✓ Balance: invoice=${data['invoice_amount']}, due=${data['balance_due']}, status={data['billing_status']}")
    
    def test_billing_balance_not_found(self):
        """GET /api/billing/balance/{id} - Returns 404 for non-existent condo"""
        token = self.get_superadmin_token()
        response = self.session.get(
            f"{BASE_URL}/api/billing/balance/non-existent-condo-id",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Balance returns 404 for non-existent condo")
    
    # ==================== PAYMENT HISTORY ====================
    
    def test_payment_history_list(self):
        """GET /api/billing/payments - List all payments (SuperAdmin)"""
        token = self.get_superadmin_token()
        response = self.session.get(
            f"{BASE_URL}/api/billing/payments",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Payments list failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Expected array of payments"
        print(f"✓ Payments list: {len(data)} payments found")
    
    def test_payment_history_by_condo(self):
        """GET /api/billing/payments/{id} - Get payment history for specific condo"""
        token = self.get_superadmin_token()
        condo_id = self.get_test_condo_id(token)
        
        if not condo_id:
            pytest.skip("No test condominium found")
        
        response = self.session.get(
            f"{BASE_URL}/api/billing/payments/{condo_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Payment history failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Expected array of payment history"
        print(f"✓ Payment history for condo: {len(data)} payments")
    
    # ==================== SEAT MANAGEMENT (uses SeatUsageResponse, SeatReductionValidation models) ====================
    
    def test_seat_status(self):
        """GET /api/billing/seat-status/{id} - Uses SeatUsageResponse from module"""
        token = self.get_superadmin_token()
        condo_id = self.get_test_condo_id(token)
        
        if not condo_id:
            pytest.skip("No test condominium found")
        
        response = self.session.get(
            f"{BASE_URL}/api/billing/seat-status/{condo_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Seat status failed: {response.text}"
        data = response.json()
        
        # Verify SeatUsageResponse model structure
        assert "condominium_id" in data, "Missing condominium_id"
        assert "paid_seats" in data, "Missing paid_seats"
        assert "active_users" in data, "Missing active_users"
        assert "remaining_seats" in data, "Missing remaining_seats"
        assert "usage_percent" in data, "Missing usage_percent"
        assert "can_create_users" in data, "Missing can_create_users"
        assert "billing_status" in data, "Missing billing_status"
        
        print(f"✓ Seat status: {data['active_users']}/{data['paid_seats']} seats used ({data['usage_percent']}%)")
    
    def test_update_seats(self):
        """PATCH /api/billing/seats/{id} - Update seat count"""
        token = self.get_superadmin_token()
        condo_id = self.get_test_condo_id(token)
        
        if not condo_id:
            pytest.skip("No test condominium found")
        
        # First get current seats
        status_response = self.session.get(
            f"{BASE_URL}/api/billing/seat-status/{condo_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if status_response.status_code != 200:
            pytest.skip("Could not get seat status")
        
        current_seats = status_response.json().get("paid_seats", 10)
        
        # Try increasing by 1 (should succeed)
        response = self.session.patch(
            f"{BASE_URL}/api/billing/seats/{condo_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "new_seat_count": current_seats + 1,
                "reason": "Phase 3 test - increasing seats"
            }
        )
        
        # May succeed or fail depending on billing status, but should not 500
        assert response.status_code in [200, 400, 402], f"Unexpected status: {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "paid_seats" in data or "new_seat_count" in data, "Missing seat info in response"
            print(f"✓ Seats updated: {current_seats} -> {current_seats + 1}")
        else:
            print(f"✓ Seats update correctly rejected: {response.json().get('detail', 'validation error')}")
    
    # ==================== SEAT UPGRADE WORKFLOW ====================
    
    def test_upgrade_requests_list(self):
        """GET /api/billing/upgrade-requests - List pending upgrade requests"""
        token = self.get_superadmin_token()
        response = self.session.get(
            f"{BASE_URL}/api/billing/upgrade-requests",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Upgrade requests failed: {response.text}"
        data = response.json()
        
        assert "total" in data, "Missing total field"
        assert "requests" in data, "Missing requests field"
        assert isinstance(data["requests"], list), "Expected array of requests"
        
        print(f"✓ Upgrade requests: {data['total']} pending")
    
    def test_request_seat_upgrade_requires_admin(self):
        """POST /api/billing/request-seat-upgrade - Requires Admin role"""
        token = self.get_superadmin_token()
        
        # SuperAdmin should get 403 (requires Admin/condominium context)
        response = self.session.post(
            f"{BASE_URL}/api/billing/request-seat-upgrade",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "requested_seats": 20,
                "reason": "Test upgrade request"
            }
        )
        
        # SuperAdmin lacks condominium context, should get error
        assert response.status_code in [400, 403, 422], f"Expected 400/403/422, got {response.status_code}"
        print("✓ Request seat upgrade correctly requires Admin role with condo context")
    
    def test_approve_upgrade_invalid_id(self):
        """PATCH /api/billing/approve-seat-upgrade/{id} - Returns 404 for invalid ID"""
        token = self.get_superadmin_token()
        response = self.session.patch(
            f"{BASE_URL}/api/billing/approve-seat-upgrade/invalid-request-id",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "approve"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Approve upgrade returns 404 for invalid request ID")
    
    # ==================== SUPER-ADMIN BILLING OVERVIEW ====================
    
    def test_billing_overview(self):
        """GET /api/super-admin/billing/overview - Returns paginated condos with billing info"""
        token = self.get_superadmin_token()
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Overview failed: {response.text}"
        data = response.json()
        
        assert "condominiums" in data, "Missing condominiums field"
        assert "pagination" in data, "Missing pagination field"
        assert "totals" in data, "Missing totals field"
        
        pagination = data["pagination"]
        assert "total" in pagination, "Missing pagination.total"
        assert "page" in pagination, "Missing pagination.page"
        
        print(f"✓ Billing overview: {pagination['total']} condos, page {pagination['page']}")
    
    def test_billing_overview_pagination(self):
        """GET /api/super-admin/billing/overview - With pagination params"""
        token = self.get_superadmin_token()
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview?page=1&page_size=5",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Overview pagination failed: {response.text}"
        data = response.json()
        
        assert len(data["condominiums"]) <= 5, "Page size not respected"
        print(f"✓ Billing overview pagination: {len(data['condominiums'])} condos on page 1")
    
    def test_billing_overview_filter(self):
        """GET /api/super-admin/billing/overview - With status filter"""
        token = self.get_superadmin_token()
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview?billing_status=pending_payment",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Overview filter failed: {response.text}"
        data = response.json()
        
        # All returned condos should have pending_payment status (or list could be empty)
        for condo in data.get("condominiums", []):
            assert condo.get("billing_status") == "pending_payment", f"Filter not applied: {condo.get('billing_status')}"
        
        print(f"✓ Billing overview filter: {len(data['condominiums'])} condos with pending_payment")
    
    # ==================== GRACE PERIOD ====================
    
    def test_update_grace_period(self):
        """PUT /api/condominiums/{id}/grace-period - Update grace period"""
        token = self.get_superadmin_token()
        condo_id = self.get_test_condo_id(token)
        
        if not condo_id:
            pytest.skip("No test condominium found")
        
        response = self.session.put(
            f"{BASE_URL}/api/condominiums/{condo_id}/grace-period?grace_days=7",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Grace period update failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Expected success=True"
        assert data.get("grace_period_days") == 7, f"Expected 7 days, got {data.get('grace_period_days')}"
        
        print(f"✓ Grace period updated to {data['grace_period_days']} days")
    
    def test_update_grace_period_validation(self):
        """PUT /api/condominiums/{id}/grace-period - Validates 0-30 range"""
        token = self.get_superadmin_token()
        condo_id = self.get_test_condo_id(token)
        
        if not condo_id:
            pytest.skip("No test condominium found")
        
        # Try with invalid value (> 30)
        response = self.session.put(
            f"{BASE_URL}/api/condominiums/{condo_id}/grace-period?grace_days=50",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422, f"Expected 422 for invalid grace_days, got {response.status_code}"
        print("✓ Grace period validates 0-30 range")
    
    # ==================== ACCESS CONTROL ====================
    
    def test_scheduler_requires_auth(self):
        """Scheduler endpoints require authentication"""
        response = self.session.get(f"{BASE_URL}/api/billing/scheduler/status")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Scheduler status requires auth")
    
    def test_billing_overview_requires_superadmin(self):
        """Billing overview requires SuperAdmin role"""
        response = self.session.get(f"{BASE_URL}/api/super-admin/billing/overview")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Billing overview requires SuperAdmin auth")
    
    def test_payments_requires_auth(self):
        """Payments endpoint requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/billing/payments")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Payments endpoint requires auth")


class TestBillingModuleImports:
    """Verify that billing module imports are working correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_superadmin_token(self):
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=SUPERADMIN_CREDENTIALS
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_billing_info_endpoint(self):
        """GET /api/billing/info - Uses BillingInfoResponse model"""
        token = self.get_superadmin_token()
        response = self.session.get(
            f"{BASE_URL}/api/billing/info",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # SuperAdmin has no condominium, so expect error message
        # But endpoint should respond (not 500)
        assert response.status_code in [200, 400, 403], f"Unexpected status: {response.status_code}"
        print("✓ Billing info endpoint responds correctly")
    
    def test_can_create_user_endpoint(self):
        """GET /api/billing/can-create-user - Uses billing logic"""
        token = self.get_superadmin_token()
        response = self.session.get(
            f"{BASE_URL}/api/billing/can-create-user",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # SuperAdmin has no condominium context
        assert response.status_code in [200, 400, 403], f"Unexpected status: {response.status_code}"
        print("✓ Can-create-user endpoint responds correctly")
    
    def test_billing_events(self):
        """GET /api/billing/events/{id} - Returns billing event log"""
        token = self.get_superadmin_token()
        
        # Get a condo ID
        overview_response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview?page_size=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if overview_response.status_code != 200:
            pytest.skip("Could not get test condo")
        
        condos = overview_response.json().get("condominiums", [])
        if not condos:
            pytest.skip("No condos available")
        
        condo_id = condos[0]["id"]
        
        response = self.session.get(
            f"{BASE_URL}/api/billing/events/{condo_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Events failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Expected array of events"
        print(f"✓ Billing events: {len(data)} events for condo")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
