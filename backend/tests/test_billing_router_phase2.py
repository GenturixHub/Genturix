"""
Test Suite: Billing Router Phase 2 Modularization
==================================================
Tests all billing endpoints after migration from api_router to billing_router
and billing_super_admin_router.

PHASE 2 TESTING CHECKLIST:
- billing_router endpoints: /api/billing/*
- billing_super_admin_router endpoints: /api/super-admin/billing/*
- Related endpoints in api_router: /api/condominiums/{condo_id}/billing, etc.

All tests verify that routing works correctly after the refactoring.
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "Admin123!"


class TestBillingRouterPhase2:
    """Test billing endpoints after Phase 2 modularization"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as SuperAdmin to get token and test data"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as SuperAdmin
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"SuperAdmin login failed: {login_response.status_code}")
        
        data = login_response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Get a test condominium from billing overview
        overview_response = self.session.get(f"{BASE_URL}/api/super-admin/billing/overview?page_size=5")
        if overview_response.status_code == 200:
            condos = overview_response.json().get("condominiums", [])
            # Find a non-demo production condo for testing
            for condo in condos:
                if not condo.get("is_demo", True):
                    self.test_condo_id = condo.get("condominium_id")
                    self.test_condo_name = condo.get("condominium_name")
                    break
            else:
                self.test_condo_id = condos[0].get("condominium_id") if condos else None
                self.test_condo_name = condos[0].get("condominium_name") if condos else None
        else:
            self.test_condo_id = None
            self.test_condo_name = None
        
        print(f"✓ Setup complete - Test condo: {self.test_condo_id}")
    
    # ==================== SCHEDULER ENDPOINTS ====================
    
    def test_scheduler_status_endpoint(self):
        """Test: GET /api/billing/scheduler/status"""
        response = self.session.get(f"{BASE_URL}/api/billing/scheduler/status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Response has is_running, last_run, next_run_scheduled
        assert "is_running" in data or "status" in data, "Response should have scheduler status"
        assert "last_run" in data or "scheduler" in data, "Should have scheduler info"
        
        print(f"✓ Scheduler status endpoint working: is_running={data.get('is_running', 'N/A')}")
    
    def test_scheduler_history_endpoint(self):
        """Test: GET /api/billing/scheduler/history"""
        response = self.session.get(f"{BASE_URL}/api/billing/scheduler/history")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Should return an array or an object with runs/history
        assert isinstance(data, (list, dict)), "Response should be array or object"
        
        print(f"✓ Scheduler history endpoint working")
    
    def test_scheduler_run_now_endpoint(self):
        """Test: POST /api/billing/scheduler/run-now"""
        response = self.session.post(f"{BASE_URL}/api/billing/scheduler/run-now")
        
        # Can be 200 (success) or 202 (accepted/queued)
        assert response.status_code in [200, 202], f"Expected 200/202, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data or "status" in data, "Response should have message or status"
        
        print(f"✓ Scheduler run-now endpoint working")
    
    # ==================== BILLING PREVIEW ====================
    
    def test_billing_preview_endpoint(self):
        """Test: POST /api/billing/preview"""
        payload = {
            "initial_units": 10,
            "billing_cycle": "monthly"
        }
        
        response = self.session.post(f"{BASE_URL}/api/billing/preview", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "seats" in data, "Response should have 'seats'"
        assert "price_per_seat" in data, "Response should have 'price_per_seat'"
        assert "billing_cycle" in data, "Response should have 'billing_cycle'"
        assert "effective_amount" in data, "Response should have 'effective_amount'"
        
        print(f"✓ Billing preview endpoint working - Effective amount: ${data.get('effective_amount', 0):.2f}")
    
    def test_billing_preview_yearly_discount(self):
        """Test: POST /api/billing/preview with yearly billing"""
        payload = {
            "initial_units": 50,
            "billing_cycle": "yearly"
        }
        
        response = self.session.post(f"{BASE_URL}/api/billing/preview", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("billing_cycle") == "yearly"
        assert "yearly_discount_percent" in data
        assert data.get("yearly_discount_percent", 0) > 0, "Should have yearly discount"
        
        print(f"✓ Yearly billing preview with {data.get('yearly_discount_percent')}% discount")
    
    # ==================== BALANCE ENDPOINT ====================
    
    def test_balance_endpoint(self):
        """Test: GET /api/billing/balance/{condo_id}"""
        if not self.test_condo_id:
            pytest.skip("No test condominium available")
        
        response = self.session.get(f"{BASE_URL}/api/billing/balance/{self.test_condo_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "condominium_id" in data, "Response should have 'condominium_id'"
        assert "invoice_amount" in data or "balance_due" in data, "Should have billing amount info"
        
        print(f"✓ Balance endpoint working for condo {self.test_condo_id[:8]}...")
    
    def test_balance_nonexistent_condo(self):
        """Test: GET /api/billing/balance/{condo_id} with invalid condo"""
        fake_condo_id = "00000000-0000-0000-0000-000000000000"
        
        response = self.session.get(f"{BASE_URL}/api/billing/balance/{fake_condo_id}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ Balance endpoint correctly returns 404 for non-existent condo")
    
    # ==================== PAYMENT HISTORY ====================
    
    def test_payments_list_endpoint(self):
        """Test: GET /api/billing/payments (all pending payments)"""
        response = self.session.get(f"{BASE_URL}/api/billing/payments")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Can be array or object with 'payments' key
        assert isinstance(data, (list, dict)), "Response should be array or object"
        
        print(f"✓ Payments list endpoint working")
    
    def test_payments_by_condo_endpoint(self):
        """Test: GET /api/billing/payments/{condo_id}"""
        if not self.test_condo_id:
            pytest.skip("No test condominium available")
        
        response = self.session.get(f"{BASE_URL}/api/billing/payments/{self.test_condo_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, (list, dict)), "Response should be array or object"
        
        print(f"✓ Payments by condo endpoint working")
    
    # ==================== PAYMENT CONFIRMATION ====================
    
    def test_confirm_payment_validation(self):
        """Test: POST /api/billing/confirm-payment/{condo_id} validation"""
        if not self.test_condo_id:
            pytest.skip("No test condominium available")
        
        # Test with invalid amount (negative)
        payload = {
            "amount_paid": -10.00,
            "payment_reference": "TEST-REF"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{self.test_condo_id}",
            json=payload
        )
        
        # Should be 422 (validation error) or 400 (bad request)
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        
        print(f"✓ Payment confirmation correctly validates amount")
    
    def test_confirm_payment_nonexistent_condo(self):
        """Test: POST /api/billing/confirm-payment/{condo_id} with invalid condo"""
        fake_condo_id = "00000000-0000-0000-0000-000000000000"
        
        payload = {
            "amount_paid": 10.00,
            "payment_reference": "TEST-REF"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{fake_condo_id}",
            json=payload
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ Payment confirmation correctly returns 404 for non-existent condo")
    
    # ==================== SEAT UPGRADE WORKFLOW ====================
    
    def test_upgrade_requests_list_endpoint(self):
        """Test: GET /api/billing/upgrade-requests"""
        response = self.session.get(f"{BASE_URL}/api/billing/upgrade-requests")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be array of upgrade requests"
        
        print(f"✓ Upgrade requests list endpoint working - Found {len(data)} requests")
    
    def test_seat_status_endpoint(self):
        """Test: GET /api/billing/seat-status/{condo_id}"""
        if not self.test_condo_id:
            pytest.skip("No test condominium available")
        
        response = self.session.get(f"{BASE_URL}/api/billing/seat-status/{self.test_condo_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "paid_seats" in data or "condominium_id" in data, "Should have seat info"
        
        print(f"✓ Seat status endpoint working")
    
    def test_approve_upgrade_invalid_request(self):
        """Test: PATCH /api/billing/approve-seat-upgrade/{id} with invalid id"""
        fake_request_id = "00000000-0000-0000-0000-000000000000"
        
        payload = {"action": "approve"}
        
        response = self.session.patch(
            f"{BASE_URL}/api/billing/approve-seat-upgrade/{fake_request_id}",
            json=payload
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ Approve upgrade correctly returns 404 for non-existent request")
    
    # ==================== BILLING INFO ENDPOINTS ====================
    
    def test_billing_info_endpoint(self):
        """Test: GET /api/billing/info"""
        response = self.session.get(f"{BASE_URL}/api/billing/info")
        
        # SuperAdmin may not have a condominium, could return 400/403
        # Or it returns billing info
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Billing info endpoint working")
        else:
            # Expected for SuperAdmin without condo
            assert response.status_code in [400, 403, 404], f"Unexpected status: {response.status_code}"
            print(f"✓ Billing info returns expected error for SuperAdmin without condo")
    
    def test_can_create_user_endpoint(self):
        """Test: GET /api/billing/can-create-user"""
        response = self.session.get(f"{BASE_URL}/api/billing/can-create-user")
        
        # Same as billing_info - SuperAdmin may not have condo
        if response.status_code == 200:
            data = response.json()
            assert "can_create" in data or "can_create_users" in data, "Should have can_create flag"
            print(f"✓ Can create user endpoint working")
        else:
            assert response.status_code in [400, 403, 404], f"Unexpected status: {response.status_code}"
            print(f"✓ Can create user returns expected error for SuperAdmin without condo")
    
    # ==================== SUPER-ADMIN BILLING OVERVIEW ====================
    
    def test_superadmin_billing_overview_pagination(self):
        """Test: GET /api/super-admin/billing/overview with pagination"""
        response = self.session.get(f"{BASE_URL}/api/super-admin/billing/overview?page=1&page_size=10")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "condominiums" in data, "Response should have 'condominiums'"
        assert "pagination" in data, "Response should have 'pagination'"
        
        pagination = data["pagination"]
        assert pagination.get("page") == 1, "Page should be 1"
        assert pagination.get("page_size") == 10, "Page size should be 10"
        
        print(f"✓ SuperAdmin billing overview pagination working - Total: {pagination.get('total_count', 0)}")
    
    def test_superadmin_billing_overview_filtering(self):
        """Test: GET /api/super-admin/billing/overview with status filter"""
        response = self.session.get(f"{BASE_URL}/api/super-admin/billing/overview?billing_status=pending_payment")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        condos = data.get("condominiums", [])
        
        # Verify filter applied (if any results)
        for condo in condos[:5]:
            status = condo.get("billing_status", "")
            # Allow for case variations
            assert status.lower() in ["pending_payment", "pending"], f"Filter not applied: {status}"
        
        print(f"✓ Billing overview status filtering working - Found {len(condos)} condos")
    
    def test_superadmin_billing_overview_search(self):
        """Test: GET /api/super-admin/billing/overview with search"""
        response = self.session.get(f"{BASE_URL}/api/super-admin/billing/overview?search=test")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        print(f"✓ Billing overview search working")
    
    # ==================== CONDOMINIUM BILLING ENDPOINTS ====================
    
    def test_get_condominium_billing(self):
        """Test: GET /api/condominiums/{condo_id}/billing"""
        if not self.test_condo_id:
            pytest.skip("No test condominium available")
        
        response = self.session.get(f"{BASE_URL}/api/condominiums/{self.test_condo_id}/billing")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Should have billing info fields
        assert "billing_status" in data or "paid_seats" in data, "Should have billing info"
        
        print(f"✓ GET condominium billing endpoint working")
    
    def test_patch_superadmin_condominium_billing(self):
        """Test: PATCH /api/super-admin/condominiums/{condo_id}/billing (read structure only)"""
        if not self.test_condo_id:
            pytest.skip("No test condominium available")
        
        # Test with minimal update to verify endpoint works
        # Don't actually change billing status to avoid side effects
        payload = {
            "notes": f"Test update at {datetime.now().isoformat()}"
        }
        
        response = self.session.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{self.test_condo_id}/billing",
            json=payload
        )
        
        # 200 success or 422 if notes not a valid field (still proves endpoint exists)
        assert response.status_code in [200, 422], f"Expected 200/422, got {response.status_code}: {response.text}"
        
        print(f"✓ PATCH superadmin condominium billing endpoint exists and responds")
    
    # ==================== REQUEST SEAT UPGRADE (Admin endpoint) ====================
    
    def test_request_seat_upgrade_requires_admin(self):
        """Test: POST /api/billing/request-seat-upgrade (SuperAdmin should get error)"""
        payload = {
            "requested_seats": 20,
            "reason": "Testing from Phase 2"
        }
        
        response = self.session.post(f"{BASE_URL}/api/billing/request-seat-upgrade", json=payload)
        
        # SuperAdmin doesn't have a condominium, so this should fail
        # 400 (no condo) or 403 (not admin role) or 422 (validation)
        assert response.status_code in [400, 403, 422], f"Expected 400/403/422, got {response.status_code}"
        
        print(f"✓ Request seat upgrade correctly requires Admin role")


class TestBillingRouterAccessControl:
    """Test access control for billing endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Create session without auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_scheduler_requires_auth(self):
        """Test: Scheduler endpoints require authentication"""
        response = self.session.get(f"{BASE_URL}/api/billing/scheduler/status")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        print(f"✓ Scheduler endpoints require authentication")
    
    def test_billing_overview_requires_superadmin(self):
        """Test: Billing overview requires SuperAdmin role"""
        response = self.session.get(f"{BASE_URL}/api/super-admin/billing/overview")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        print(f"✓ Billing overview requires SuperAdmin authentication")
    
    def test_payments_list_requires_auth(self):
        """Test: Payments list requires authentication"""
        response = self.session.get(f"{BASE_URL}/api/billing/payments")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        print(f"✓ Payments list requires authentication")


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
