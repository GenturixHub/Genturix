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
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERADMIN_CREDENTIALS = {"email": "superadmin@genturix.com", "password": "Admin123!"}
ADMIN_CREDENTIALS = {"email": "test-resident@genturix.com", "password": "Admin123!"}


@pytest.fixture(scope="module")
def session():
    """Module-scoped session"""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def superadmin_token(session):
    """Module-scoped SuperAdmin token to avoid rate limiting"""
    # Wait a bit to ensure rate limit is clear
    time.sleep(1)
    response = session.post(
        f"{BASE_URL}/api/auth/login",
        json=SUPERADMIN_CREDENTIALS
    )
    if response.status_code != 200:
        pytest.skip(f"SuperAdmin login failed: {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def test_condo_id(session, superadmin_token):
    """Get a test condominium ID"""
    response = session.get(
        f"{BASE_URL}/api/super-admin/billing/overview?page_size=1",
        headers={"Authorization": f"Bearer {superadmin_token}"}
    )
    if response.status_code == 200:
        data = response.json()
        condos = data.get("condominiums", [])
        if condos:
            # Get first condo with 'condominium_id' or 'id' key
            condo = condos[0]
            return condo.get("condominium_id") or condo.get("id")
    return None


# ==================== SCHEDULER ENDPOINTS (from modules.billing.scheduler) ====================

class TestSchedulerEndpoints:
    """Test scheduler endpoints that now use get_scheduler_instance() from module"""
    
    def test_scheduler_status(self, session, superadmin_token):
        """GET /api/billing/scheduler/status - Uses get_scheduler_instance from module"""
        response = session.get(
            f"{BASE_URL}/api/billing/scheduler/status",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 200, f"Scheduler status failed: {response.text}"
        data = response.json()
        
        # Verify expected response structure
        assert "is_running" in data, "Missing is_running field"
        assert "next_run_scheduled" in data, "Missing next_run_scheduled field"
        assert "last_run" in data, "Missing last_run field"
        
        print(f"✓ Scheduler status: is_running={data['is_running']}, next_run={data['next_run_scheduled']}")
    
    def test_scheduler_run_now(self, session, superadmin_token):
        """POST /api/billing/scheduler/run-now - Triggers run_daily_billing_check from module"""
        response = session.post(
            f"{BASE_URL}/api/billing/scheduler/run-now",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 200, f"Run-now failed: {response.text}"
        data = response.json()
        
        # API wraps results in a structure
        assert "success" in data, "Missing success field"
        assert data["success"] == True, "Expected success=True"
        
        # Results contain the actual run data
        results = data.get("results", data)
        assert "total_evaluated" in results, "Missing total_evaluated in results"
        
        print(f"✓ Scheduler run-now: evaluated {results.get('total_evaluated', 0)} condos")
    
    def test_scheduler_history(self, session, superadmin_token):
        """GET /api/billing/scheduler/history - Returns scheduler run history"""
        response = session.get(
            f"{BASE_URL}/api/billing/scheduler/history",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 200, f"Scheduler history failed: {response.text}"
        data = response.json()
        
        # API returns {count, runs} structure
        assert "runs" in data, "Missing runs field"
        assert "count" in data, "Missing count field"
        assert isinstance(data["runs"], list), "Expected runs to be array"
        
        print(f"✓ Scheduler history: {data['count']} runs recorded")


# ==================== BILLING PREVIEW (uses billing models) ====================

class TestBillingPreview:
    """Test billing preview which uses models from modules.billing.models"""
    
    def test_billing_preview_monthly(self, session, superadmin_token):
        """POST /api/billing/preview - Monthly cycle preview"""
        response = session.post(
            f"{BASE_URL}/api/billing/preview",
            headers={"Authorization": f"Bearer {superadmin_token}"},
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
    
    def test_billing_preview_yearly(self, session, superadmin_token):
        """POST /api/billing/preview - Yearly cycle with discount"""
        response = session.post(
            f"{BASE_URL}/api/billing/preview",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={
                "initial_units": 50,
                "billing_cycle": "yearly"
            }
        )
        
        assert response.status_code == 200, f"Preview yearly failed: {response.text}"
        data = response.json()
        
        assert data["billing_cycle"] == "yearly"
        assert "yearly_discount_percent" in data, "Missing yearly_discount_percent"
        
        print(f"✓ Preview yearly: {data['seats']} seats, {data['yearly_discount_percent']}% discount = ${data['effective_amount']}")


# ==================== PAYMENT ENDPOINTS ====================

class TestPaymentEndpoints:
    """Test payment confirmation and history endpoints"""
    
    def test_confirm_payment_invalid_condo(self, session, superadmin_token):
        """POST /api/billing/confirm-payment/{id} - Returns 404 for non-existent condo"""
        response = session.post(
            f"{BASE_URL}/api/billing/confirm-payment/non-existent-id-12345",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={
                "amount_paid": 100.0,
                "payment_reference": "TEST-REF",
                "notes": "Test payment"
            }
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Confirm payment returns 404 for non-existent condo")
    
    def test_confirm_payment_validation(self, session, superadmin_token, test_condo_id):
        """POST /api/billing/confirm-payment - Validates amount > 0"""
        if not test_condo_id:
            pytest.skip("No test condominium found")
        
        # Try with zero amount
        response = session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{test_condo_id}",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={
                "amount_paid": 0,
                "payment_reference": "TEST-REF"
            }
        )
        
        assert response.status_code == 422, f"Expected 422 for invalid amount, got {response.status_code}"
        print("✓ Confirm payment validates amount > 0")
    
    def test_payment_history_list(self, session, superadmin_token):
        """GET /api/billing/payments - List all payments (SuperAdmin)"""
        response = session.get(
            f"{BASE_URL}/api/billing/payments",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 200, f"Payments list failed: {response.text}"
        data = response.json()
        
        # API returns structured response with condominiums and pending_count
        assert "condominiums" in data or isinstance(data, list), "Expected condominiums or array"
        print(f"✓ Payments list endpoint working")
    
    def test_payment_history_by_condo(self, session, superadmin_token, test_condo_id):
        """GET /api/billing/payments/{id} - Get payment history for specific condo"""
        if not test_condo_id:
            pytest.skip("No test condominium found")
        
        response = session.get(
            f"{BASE_URL}/api/billing/payments/{test_condo_id}",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 200, f"Payment history failed: {response.text}"
        data = response.json()
        
        # API returns {condominium_id, condominium_name, payments, current_status}
        assert "condominium_id" in data, "Missing condominium_id"
        assert "payments" in data, "Missing payments field"
        assert isinstance(data["payments"], list), "payments should be array"
        print(f"✓ Payment history for condo: {len(data['payments'])} payments")


# ==================== BILLING BALANCE ====================

class TestBillingBalance:
    """Test billing balance endpoint"""
    
    def test_billing_balance(self, session, superadmin_token, test_condo_id):
        """GET /api/billing/balance/{id} - Returns balance info"""
        if not test_condo_id:
            pytest.skip("No test condominium found")
        
        response = session.get(
            f"{BASE_URL}/api/billing/balance/{test_condo_id}",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 200, f"Balance failed: {response.text}"
        data = response.json()
        
        # Verify balance response structure
        assert "condominium_id" in data, "Missing condominium_id"
        assert "invoice_amount" in data, "Missing invoice_amount"
        assert "balance_due" in data, "Missing balance_due"
        assert "billing_status" in data, "Missing billing_status"
        
        print(f"✓ Balance: invoice=${data['invoice_amount']}, due=${data['balance_due']}, status={data['billing_status']}")
    
    def test_billing_balance_not_found(self, session, superadmin_token):
        """GET /api/billing/balance/{id} - Returns 404 for non-existent condo"""
        response = session.get(
            f"{BASE_URL}/api/billing/balance/non-existent-condo-id",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Balance returns 404 for non-existent condo")


# ==================== SEAT MANAGEMENT (uses SeatUsageResponse model) ====================

class TestSeatManagement:
    """Test seat management - uses SeatUsageResponse from modules.billing.models"""
    
    def test_seat_status(self, session, superadmin_token, test_condo_id):
        """GET /api/billing/seat-status/{id} - Uses SeatUsageResponse from module"""
        if not test_condo_id:
            pytest.skip("No test condominium found")
        
        response = session.get(
            f"{BASE_URL}/api/billing/seat-status/{test_condo_id}",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 200, f"Seat status failed: {response.text}"
        data = response.json()
        
        # Verify seat status response structure
        assert "paid_seats" in data, "Missing paid_seats"
        assert "current_users" in data or "active_users" in data, "Missing user count field"
        assert "remaining" in data or "remaining_seats" in data, "Missing remaining seats field"
        assert "billing_status" in data, "Missing billing_status"
        assert "can_create" in data or "can_create_users" in data, "Missing can_create field"
        
        user_count = data.get("current_users") or data.get("active_users", 0)
        remaining = data.get("remaining") or data.get("remaining_seats", 0)
        print(f"✓ Seat status: {user_count}/{data['paid_seats']} seats used, {remaining} remaining")
    
    def test_update_seats_validation(self, session, superadmin_token, test_condo_id):
        """PATCH /api/billing/seats/{id} - Update seat count validation"""
        if not test_condo_id:
            pytest.skip("No test condominium found")
        
        # Try with invalid seat count (0)
        response = session.patch(
            f"{BASE_URL}/api/billing/seats/{test_condo_id}",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={
                "new_seat_count": 0,
                "reason": "Test - should fail"
            }
        )
        
        # Should get 422 for invalid seat count
        assert response.status_code == 422, f"Expected 422 for invalid seats, got {response.status_code}"
        print("✓ Seat update validates seat count >= 1")


# ==================== SEAT UPGRADE WORKFLOW ====================

class TestSeatUpgradeWorkflow:
    """Test seat upgrade request workflow"""
    
    def test_upgrade_requests_list(self, session, superadmin_token):
        """GET /api/billing/upgrade-requests - List pending upgrade requests"""
        response = session.get(
            f"{BASE_URL}/api/billing/upgrade-requests",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 200, f"Upgrade requests failed: {response.text}"
        data = response.json()
        
        assert "total" in data, "Missing total field"
        assert "requests" in data, "Missing requests field"
        assert isinstance(data["requests"], list), "Expected array of requests"
        
        print(f"✓ Upgrade requests: {data['total']} pending")
    
    def test_request_seat_upgrade_requires_admin(self, session, superadmin_token):
        """POST /api/billing/request-seat-upgrade - Requires Admin role (SuperAdmin lacks condo context)"""
        response = session.post(
            f"{BASE_URL}/api/billing/request-seat-upgrade",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={
                "requested_seats": 20,
                "reason": "Test upgrade request"
            }
        )
        
        # SuperAdmin lacks condominium context, should get error
        assert response.status_code in [400, 403, 422], f"Expected 400/403/422, got {response.status_code}"
        print("✓ Request seat upgrade correctly requires Admin role with condo context")
    
    def test_approve_upgrade_invalid_id(self, session, superadmin_token):
        """PATCH /api/billing/approve-seat-upgrade/{id} - Returns 404 for invalid ID"""
        response = session.patch(
            f"{BASE_URL}/api/billing/approve-seat-upgrade/invalid-request-id",
            headers={"Authorization": f"Bearer {superadmin_token}"},
            json={"action": "approve"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Approve upgrade returns 404 for invalid request ID")


# ==================== SUPER-ADMIN BILLING OVERVIEW ====================

class TestBillingOverview:
    """Test super-admin billing overview endpoints"""
    
    def test_billing_overview(self, session, superadmin_token):
        """GET /api/super-admin/billing/overview - Returns paginated condos with billing info"""
        response = session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 200, f"Overview failed: {response.text}"
        data = response.json()
        
        assert "condominiums" in data, "Missing condominiums field"
        assert "pagination" in data, "Missing pagination field"
        assert "totals" in data, "Missing totals field"
        
        pagination = data["pagination"]
        # May be 'total' or 'total_count' depending on implementation
        assert "page" in pagination, "Missing pagination.page"
        assert "page_size" in pagination, "Missing pagination.page_size"
        
        print(f"✓ Billing overview: page {pagination['page']}, {len(data['condominiums'])} condos")
    
    def test_billing_overview_pagination(self, session, superadmin_token):
        """GET /api/super-admin/billing/overview - With pagination params"""
        response = session.get(
            f"{BASE_URL}/api/super-admin/billing/overview?page=1&page_size=5",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 200, f"Overview pagination failed: {response.text}"
        data = response.json()
        
        assert len(data["condominiums"]) <= 5, "Page size not respected"
        print(f"✓ Billing overview pagination: {len(data['condominiums'])} condos on page 1")
    
    def test_billing_overview_filter(self, session, superadmin_token):
        """GET /api/super-admin/billing/overview - With status filter"""
        response = session.get(
            f"{BASE_URL}/api/super-admin/billing/overview?billing_status=pending_payment",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 200, f"Overview filter failed: {response.text}"
        data = response.json()
        
        # All returned condos should have pending_payment status (or list could be empty)
        for condo in data.get("condominiums", []):
            assert condo.get("billing_status") == "pending_payment", f"Filter not applied: {condo.get('billing_status')}"
        
        print(f"✓ Billing overview filter: {len(data['condominiums'])} condos with pending_payment")


# ==================== GRACE PERIOD ====================

class TestGracePeriod:
    """Test grace period update endpoint"""
    
    def test_update_grace_period(self, session, superadmin_token, test_condo_id):
        """PUT /api/condominiums/{id}/grace-period - Update grace period"""
        if not test_condo_id:
            pytest.skip("No test condominium found")
        
        response = session.put(
            f"{BASE_URL}/api/condominiums/{test_condo_id}/grace-period?grace_days=7",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 200, f"Grace period update failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True, "Expected success=True"
        assert data.get("grace_period_days") == 7, f"Expected 7 days, got {data.get('grace_period_days')}"
        
        print(f"✓ Grace period updated to {data['grace_period_days']} days")
    
    def test_update_grace_period_validation(self, session, superadmin_token, test_condo_id):
        """PUT /api/condominiums/{id}/grace-period - Validates 0-30 range"""
        if not test_condo_id:
            pytest.skip("No test condominium found")
        
        # Try with invalid value (> 30)
        response = session.put(
            f"{BASE_URL}/api/condominiums/{test_condo_id}/grace-period?grace_days=50",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 422, f"Expected 422 for invalid grace_days, got {response.status_code}"
        print("✓ Grace period validates 0-30 range")


# ==================== ACCESS CONTROL ====================

class TestAccessControl:
    """Test authentication requirements for billing endpoints"""
    
    def test_scheduler_requires_auth(self, session):
        """Scheduler endpoints require authentication"""
        response = session.get(f"{BASE_URL}/api/billing/scheduler/status")
        # FastAPI returns 403 for missing auth, not 401 (due to HTTPBearer)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Scheduler status requires auth")
    
    def test_billing_overview_requires_auth(self, session):
        """Billing overview requires authentication"""
        response = session.get(f"{BASE_URL}/api/super-admin/billing/overview")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Billing overview requires auth")
    
    def test_payments_requires_auth(self, session):
        """Payments endpoint requires authentication"""
        response = session.get(f"{BASE_URL}/api/billing/payments")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Payments endpoint requires auth")


# ==================== MODULE IMPORTS VERIFICATION ====================

class TestBillingModuleImports:
    """Verify that billing module imports are working correctly"""
    
    def test_billing_info_endpoint(self, session, superadmin_token):
        """GET /api/billing/info - Uses BillingInfoResponse model"""
        response = session.get(
            f"{BASE_URL}/api/billing/info",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        # SuperAdmin has no condominium, so expect error message
        # But endpoint should respond (not 500)
        assert response.status_code in [200, 400, 403], f"Unexpected status: {response.status_code}"
        print("✓ Billing info endpoint responds correctly")
    
    def test_can_create_user_endpoint(self, session, superadmin_token):
        """GET /api/billing/can-create-user - Uses billing logic"""
        response = session.get(
            f"{BASE_URL}/api/billing/can-create-user",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        # SuperAdmin has no condominium context
        assert response.status_code in [200, 400, 403], f"Unexpected status: {response.status_code}"
        print("✓ Can-create-user endpoint responds correctly")
    
    def test_billing_events(self, session, superadmin_token, test_condo_id):
        """GET /api/billing/events/{id} - Returns billing event log"""
        if not test_condo_id:
            pytest.skip("No test condo")
        
        response = session.get(
            f"{BASE_URL}/api/billing/events/{test_condo_id}",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        
        assert response.status_code == 200, f"Events failed: {response.text}"
        data = response.json()
        
        # API may return {condominium_id, events, total} or list directly
        if isinstance(data, dict):
            assert "events" in data, "Missing events field"
            events = data["events"]
        else:
            events = data
        
        assert isinstance(events, list), "Expected events to be array"
        print(f"✓ Billing events: {len(events)} events for condo")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
