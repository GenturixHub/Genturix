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


@pytest.fixture(scope="module")
def superadmin_session():
    """Module-scoped fixture for SuperAdmin authentication"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login as SuperAdmin
    login_response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
    )
    
    if login_response.status_code != 200:
        pytest.skip(f"SuperAdmin login failed: {login_response.status_code}")
    
    data = login_response.json()
    token = data.get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    return session


@pytest.fixture(scope="module")
def test_condo_id(superadmin_session):
    """Module-scoped fixture to get a test condominium ID"""
    overview_response = superadmin_session.get(f"{BASE_URL}/api/super-admin/billing/overview?page_size=10")
    
    if overview_response.status_code != 200:
        pytest.skip("Could not fetch billing overview")
    
    condos = overview_response.json().get("condominiums", [])
    
    # Find a non-demo production condo for testing
    for condo in condos:
        if not condo.get("is_demo", True):
            return condo.get("condominium_id")
    
    # Fall back to first condo
    if condos:
        return condos[0].get("condominium_id")
    
    return None


class TestBillingSchedulerEndpoints:
    """Test billing scheduler endpoints - /api/billing/scheduler/*"""
    
    def test_scheduler_status(self, superadmin_session):
        """Test: GET /api/billing/scheduler/status"""
        response = superadmin_session.get(f"{BASE_URL}/api/billing/scheduler/status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "is_running" in data or "status" in data, "Response should have scheduler status"
        assert "last_run" in data, "Should have last_run info"
        
        print(f"✓ Scheduler status: is_running={data.get('is_running')}")
    
    def test_scheduler_history(self, superadmin_session):
        """Test: GET /api/billing/scheduler/history"""
        response = superadmin_session.get(f"{BASE_URL}/api/billing/scheduler/history")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, (list, dict)), "Response should be array or object"
        
        print(f"✓ Scheduler history endpoint working")
    
    def test_scheduler_run_now(self, superadmin_session):
        """Test: POST /api/billing/scheduler/run-now"""
        response = superadmin_session.post(f"{BASE_URL}/api/billing/scheduler/run-now")
        
        assert response.status_code in [200, 202], f"Expected 200/202, got {response.status_code}"
        
        data = response.json()
        assert "message" in data or "status" in data or "result" in data
        
        print(f"✓ Scheduler run-now endpoint working")


class TestBillingPreviewEndpoint:
    """Test billing preview - POST /api/billing/preview"""
    
    def test_billing_preview_monthly(self, superadmin_session):
        """Test: POST /api/billing/preview with monthly billing"""
        payload = {"initial_units": 10, "billing_cycle": "monthly"}
        
        response = superadmin_session.post(f"{BASE_URL}/api/billing/preview", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "seats" in data
        assert "price_per_seat" in data
        assert "effective_amount" in data
        assert data["billing_cycle"] == "monthly"
        
        print(f"✓ Monthly preview: ${data.get('effective_amount', 0):.2f}")
    
    def test_billing_preview_yearly(self, superadmin_session):
        """Test: POST /api/billing/preview with yearly billing"""
        payload = {"initial_units": 50, "billing_cycle": "yearly"}
        
        response = superadmin_session.post(f"{BASE_URL}/api/billing/preview", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["billing_cycle"] == "yearly"
        assert data.get("yearly_discount_percent", 0) > 0
        
        print(f"✓ Yearly preview with {data.get('yearly_discount_percent')}% discount")


class TestBillingBalanceEndpoint:
    """Test billing balance - GET /api/billing/balance/{condo_id}"""
    
    def test_balance_valid_condo(self, superadmin_session, test_condo_id):
        """Test: GET /api/billing/balance/{condo_id} with valid condo"""
        if not test_condo_id:
            pytest.skip("No test condominium available")
        
        response = superadmin_session.get(f"{BASE_URL}/api/billing/balance/{test_condo_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "condominium_id" in data
        
        print(f"✓ Balance endpoint working for condo {test_condo_id[:8]}...")
    
    def test_balance_nonexistent_condo(self, superadmin_session):
        """Test: GET /api/billing/balance/{condo_id} with invalid condo"""
        fake_condo_id = "00000000-0000-0000-0000-000000000000"
        
        response = superadmin_session.get(f"{BASE_URL}/api/billing/balance/{fake_condo_id}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ Balance returns 404 for non-existent condo")


class TestPaymentHistoryEndpoints:
    """Test payment history - GET /api/billing/payments/*"""
    
    def test_payments_list(self, superadmin_session):
        """Test: GET /api/billing/payments (all pending)"""
        response = superadmin_session.get(f"{BASE_URL}/api/billing/payments")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, (list, dict))
        
        print(f"✓ Payments list endpoint working")
    
    def test_payments_by_condo(self, superadmin_session, test_condo_id):
        """Test: GET /api/billing/payments/{condo_id}"""
        if not test_condo_id:
            pytest.skip("No test condominium available")
        
        response = superadmin_session.get(f"{BASE_URL}/api/billing/payments/{test_condo_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        print(f"✓ Payments by condo endpoint working")


class TestPaymentConfirmationEndpoint:
    """Test payment confirmation - POST /api/billing/confirm-payment/{condo_id}"""
    
    def test_confirm_payment_validation(self, superadmin_session, test_condo_id):
        """Test: Validation rejects negative amount"""
        if not test_condo_id:
            pytest.skip("No test condominium available")
        
        payload = {"amount_paid": -10.00, "payment_reference": "TEST-NEG"}
        
        response = superadmin_session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{test_condo_id}",
            json=payload
        )
        
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        
        print(f"✓ Payment confirmation validates amount")
    
    def test_confirm_payment_nonexistent_condo(self, superadmin_session):
        """Test: 404 for non-existent condo"""
        fake_condo_id = "00000000-0000-0000-0000-000000000000"
        
        payload = {"amount_paid": 10.00, "payment_reference": "TEST-FAKE"}
        
        response = superadmin_session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{fake_condo_id}",
            json=payload
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ Payment confirmation returns 404 for non-existent condo")


class TestSeatUpgradeWorkflow:
    """Test seat upgrade workflow endpoints"""
    
    def test_upgrade_requests_list(self, superadmin_session):
        """Test: GET /api/billing/upgrade-requests"""
        response = superadmin_session.get(f"{BASE_URL}/api/billing/upgrade-requests")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Can be {"total": n, "requests": []} or just array
        assert "requests" in data or "total" in data or isinstance(data, list)
        
        print(f"✓ Upgrade requests list endpoint working")
    
    def test_seat_status(self, superadmin_session, test_condo_id):
        """Test: GET /api/billing/seat-status/{condo_id}"""
        if not test_condo_id:
            pytest.skip("No test condominium available")
        
        response = superadmin_session.get(f"{BASE_URL}/api/billing/seat-status/{test_condo_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "paid_seats" in data or "condominium_id" in data
        
        print(f"✓ Seat status endpoint working")
    
    def test_approve_upgrade_nonexistent_request(self, superadmin_session):
        """Test: PATCH /api/billing/approve-seat-upgrade/{id} with invalid id"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        payload = {"action": "approve"}
        
        response = superadmin_session.patch(
            f"{BASE_URL}/api/billing/approve-seat-upgrade/{fake_id}",
            json=payload
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        
        print(f"✓ Approve upgrade returns 404 for non-existent request")


class TestBillingInfoEndpoints:
    """Test billing info endpoints (SuperAdmin context)"""
    
    def test_billing_info_superadmin(self, superadmin_session):
        """Test: GET /api/billing/info (SuperAdmin without condo)"""
        response = superadmin_session.get(f"{BASE_URL}/api/billing/info")
        
        # SuperAdmin doesn't have condo, so expect 400/403/404
        if response.status_code == 200:
            print(f"✓ Billing info endpoint returns data")
        else:
            assert response.status_code in [400, 403, 404]
            print(f"✓ Billing info returns expected error for SuperAdmin without condo")
    
    def test_can_create_user_superadmin(self, superadmin_session):
        """Test: GET /api/billing/can-create-user (SuperAdmin without condo)"""
        response = superadmin_session.get(f"{BASE_URL}/api/billing/can-create-user")
        
        if response.status_code == 200:
            data = response.json()
            assert "can_create" in data or "can_create_users" in data
            print(f"✓ Can create user endpoint returns data")
        else:
            assert response.status_code in [400, 403, 404]
            print(f"✓ Can create user returns expected error for SuperAdmin without condo")


class TestSuperAdminBillingOverview:
    """Test super-admin billing overview endpoints"""
    
    def test_billing_overview_basic(self, superadmin_session):
        """Test: GET /api/super-admin/billing/overview"""
        response = superadmin_session.get(f"{BASE_URL}/api/super-admin/billing/overview")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "condominiums" in data
        assert "pagination" in data
        
        print(f"✓ Billing overview basic pagination working")
    
    def test_billing_overview_pagination(self, superadmin_session):
        """Test: GET /api/super-admin/billing/overview with pagination params"""
        response = superadmin_session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={"page": 1, "page_size": 10}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        pagination = data.get("pagination", {})
        assert pagination.get("page") == 1
        assert pagination.get("page_size") == 10
        
        print(f"✓ Pagination params work - Total: {pagination.get('total_count', 0)}")
    
    def test_billing_overview_status_filter(self, superadmin_session):
        """Test: GET /api/super-admin/billing/overview with billing_status filter"""
        response = superadmin_session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={"billing_status": "pending_payment"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        print(f"✓ Status filter working")
    
    def test_billing_overview_search(self, superadmin_session):
        """Test: GET /api/super-admin/billing/overview with search"""
        response = superadmin_session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={"search": "test"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        print(f"✓ Search filter working")


class TestCondominiumBillingEndpoints:
    """Test condominium-level billing endpoints"""
    
    def test_get_condominium_billing(self, superadmin_session, test_condo_id):
        """Test: GET /api/condominiums/{condo_id}/billing"""
        if not test_condo_id:
            pytest.skip("No test condominium available")
        
        response = superadmin_session.get(f"{BASE_URL}/api/condominiums/{test_condo_id}/billing")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "billing_status" in data or "paid_seats" in data
        
        print(f"✓ GET condominium billing working")
    
    def test_patch_superadmin_condominium_billing_exists(self, superadmin_session, test_condo_id):
        """Test: PATCH /api/super-admin/condominiums/{condo_id}/billing endpoint exists"""
        if not test_condo_id:
            pytest.skip("No test condominium available")
        
        # Test with empty payload to verify endpoint exists
        response = superadmin_session.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{test_condo_id}/billing",
            json={}
        )
        
        # 200 (no changes) or 422 (validation error) both prove endpoint exists
        assert response.status_code in [200, 422], f"Expected 200/422, got {response.status_code}"
        
        print(f"✓ PATCH superadmin condominium billing endpoint exists")


class TestBillingRouterAccessControl:
    """Test access control for billing endpoints (no auth)"""
    
    def test_scheduler_requires_auth(self):
        """Test: Scheduler endpoints require authentication"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/billing/scheduler/status")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        print(f"✓ Scheduler requires authentication")
    
    def test_billing_overview_requires_superadmin(self):
        """Test: Billing overview requires SuperAdmin role"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/super-admin/billing/overview")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        print(f"✓ Billing overview requires SuperAdmin authentication")
    
    def test_payments_requires_auth(self):
        """Test: Payments endpoint requires authentication"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/billing/payments")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        print(f"✓ Payments requires authentication")


class TestRequestSeatUpgradeEndpoint:
    """Test request seat upgrade (Admin-only endpoint)"""
    
    def test_request_upgrade_requires_admin(self, superadmin_session):
        """Test: POST /api/billing/request-seat-upgrade requires Admin role"""
        payload = {"requested_seats": 20, "reason": "Testing Phase 2"}
        
        response = superadmin_session.post(
            f"{BASE_URL}/api/billing/request-seat-upgrade",
            json=payload
        )
        
        # SuperAdmin doesn't have a condo - should get 400/403/422
        assert response.status_code in [400, 403, 422], f"Expected 400/403/422, got {response.status_code}"
        
        print(f"✓ Request seat upgrade correctly requires Admin role/condo")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
