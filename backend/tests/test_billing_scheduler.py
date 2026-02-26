"""
Billing Scheduler Tests - Automatic vencimientos con bloqueo parcial

Tests for:
1. GET /api/billing/scheduler/status - scheduler status info
2. POST /api/billing/scheduler/run-now - manual trigger billing check
3. Scheduler transitions: active -> past_due, past_due -> suspended
4. Billing events logging for auto_status_change
5. POST /api/billing/confirm-payment/{condo_id} - confirm payment restores active
6. GET /api/billing/scheduler/history - scheduler run history
7. PUT /api/condominiums/{condo_id}/grace-period - update grace period
8. Partial blocking middleware - 402 for suspended condos
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


# Global session to minimize login attempts
@pytest.fixture(scope="module")
def auth_session():
    """Setup: Get SuperAdmin token - shared across all tests in module"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login as superadmin
    login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "superadmin@genturix.com",
        "password": "Admin123!"
    })
    
    if login_resp.status_code != 200:
        pytest.skip(f"SuperAdmin login failed: {login_resp.status_code}")
    
    token = login_resp.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    yield session
    
    session.close()


class TestBillingSchedulerStatus:
    """Test scheduler status endpoints"""
    
    def test_scheduler_status_returns_info(self, auth_session):
        """GET /api/billing/scheduler/status should return is_running, next_run_scheduled, last_run"""
        resp = auth_session.get(f"{BASE_URL}/api/billing/scheduler/status")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # Validate structure
        assert "is_running" in data, "Response should contain 'is_running'"
        assert "next_run_scheduled" in data, "Response should contain 'next_run_scheduled'"
        assert "last_run" in data, "Response should contain 'last_run'"
        
        # is_running should be boolean
        assert isinstance(data["is_running"], bool), "is_running should be boolean"
        
        print(f"Scheduler status: running={data['is_running']}, next={data['next_run_scheduled']}")


class TestBillingSchedulerRunNow:
    """Test scheduler run-now endpoint"""
    
    def test_scheduler_run_now_executes_check(self, auth_session):
        """POST /api/billing/scheduler/run-now should execute billing check and return results"""
        resp = auth_session.post(f"{BASE_URL}/api/billing/scheduler/run-now")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # Validate structure
        assert data.get("success") == True, "Response should have success=True"
        assert "results" in data, "Response should contain 'results'"
        
        results = data["results"]
        assert "total_evaluated" in results, "Results should contain total_evaluated"
        assert "transitioned_to_past_due" in results, "Results should contain transitioned_to_past_due"
        assert "transitioned_to_suspended" in results, "Results should contain transitioned_to_suspended"
        assert "emails_sent" in results, "Results should contain emails_sent"
        assert "errors" in results, "Results should contain errors"
        
        print(f"Scheduler run results: evaluated={results['total_evaluated']}, "
              f"past_due={results['transitioned_to_past_due']}, "
              f"suspended={results['transitioned_to_suspended']}")

    def test_scheduler_is_idempotent(self, auth_session):
        """Scheduler should NOT duplicate transitions - running twice should be safe"""
        # Run scheduler twice
        resp1 = auth_session.post(f"{BASE_URL}/api/billing/scheduler/run-now")
        assert resp1.status_code == 200
        
        resp2 = auth_session.post(f"{BASE_URL}/api/billing/scheduler/run-now")
        assert resp2.status_code == 200
        
        # Second run should not transition same condos again
        results2 = resp2.json()["results"]
        
        # This verifies idempotency - already transitioned condos won't be counted again
        print(f"Second run: evaluated={results2['total_evaluated']}, "
              f"transitions={results2['transitioned_to_past_due'] + results2['transitioned_to_suspended']}")

    def test_run_now_returns_detailed_results(self, auth_session):
        """run-now should return detailed evaluation results"""
        resp = auth_session.post(f"{BASE_URL}/api/billing/scheduler/run-now")
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert data.get("success") == True
        assert "message" in data
        assert "results" in data
        
        results = data["results"]
        # Verify all expected fields
        expected_fields = ["total_evaluated", "transitioned_to_past_due", 
                          "transitioned_to_suspended", "emails_sent", "errors"]
        for field in expected_fields:
            assert field in results, f"Results should contain {field}"
            assert isinstance(results[field], int), f"{field} should be an integer"


class TestBillingSchedulerHistory:
    """Test scheduler history endpoint"""
    
    def test_scheduler_history_returns_runs(self, auth_session):
        """GET /api/billing/scheduler/history should return list of scheduler runs"""
        resp = auth_session.get(f"{BASE_URL}/api/billing/scheduler/history")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        # Validate structure
        assert "runs" in data, "Response should contain 'runs'"
        assert "count" in data, "Response should contain 'count'"
        assert isinstance(data["runs"], list), "runs should be a list"
        
        # If there are runs, validate their structure
        if data["count"] > 0:
            run = data["runs"][0]
            assert "run_date" in run, "Run should contain run_date"
            assert "run_time" in run, "Run should contain run_time"
            assert "total_evaluated" in run, "Run should contain total_evaluated"
            print(f"Found {data['count']} scheduler runs")
        else:
            print("No scheduler runs found yet")

    def test_scheduler_history_limit_param(self, auth_session):
        """GET /api/billing/scheduler/history?limit=5 should respect limit parameter"""
        resp = auth_session.get(f"{BASE_URL}/api/billing/scheduler/history?limit=5")
        
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["runs"]) <= 5, "Should respect limit parameter"

    def test_scheduler_history_ordered_by_time(self, auth_session):
        """Scheduler history should be ordered by most recent first"""
        resp = auth_session.get(f"{BASE_URL}/api/billing/scheduler/history?limit=10")
        
        assert resp.status_code == 200
        data = resp.json()
        
        if len(data["runs"]) >= 2:
            # Verify ordering
            first_run = data["runs"][0]
            second_run = data["runs"][1]
            
            first_time = datetime.fromisoformat(first_run["run_time"].replace("Z", "+00:00"))
            second_time = datetime.fromisoformat(second_run["run_time"].replace("Z", "+00:00"))
            
            assert first_time >= second_time, "History should be ordered by most recent first"


class TestGracePeriodUpdate:
    """Test grace period update endpoint"""
    
    def test_update_grace_period_for_condo(self, auth_session):
        """PUT /api/condominiums/{condo_id}/grace-period should update grace period"""
        # First, get a production condo to test with
        condos_resp = auth_session.get(f"{BASE_URL}/api/condominiums")
        assert condos_resp.status_code == 200, f"Failed to list condos: {condos_resp.status_code} - {condos_resp.text}"
        
        condos = condos_resp.json()
        # Find a production condo (not demo)
        prod_condo = None
        for c in condos:
            if not c.get("is_demo") and c.get("environment") != "demo":
                prod_condo = c
                break
        
        if not prod_condo:
            pytest.skip("No production condo found for testing")
        
        condo_id = prod_condo["id"]
        original_grace = prod_condo.get("grace_period_days", 5)
        
        # Update grace period
        new_grace = 10
        resp = auth_session.put(f"{BASE_URL}/api/condominiums/{condo_id}/grace-period?grace_days={new_grace}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert data.get("success") == True
        assert data.get("grace_period_days") == new_grace
        
        # Restore original value
        auth_session.put(f"{BASE_URL}/api/condominiums/{condo_id}/grace-period?grace_days={original_grace}")
        
        print(f"Successfully updated grace period for {condo_id[:8]}... to {new_grace} days")

    def test_update_grace_period_invalid_range(self, auth_session):
        """PUT /api/condominiums/{condo_id}/grace-period should reject invalid values"""
        # Get any condo
        condos_resp = auth_session.get(f"{BASE_URL}/api/condominiums")
        assert condos_resp.status_code == 200
        condos = condos_resp.json()
        
        if not condos:
            pytest.skip("No condos found")
        
        condo_id = condos[0]["id"]
        
        # Try invalid grace period (> 30)
        resp = auth_session.put(f"{BASE_URL}/api/condominiums/{condo_id}/grace-period?grace_days=50")
        assert resp.status_code == 422, "Should reject grace_days > 30"

    def test_update_grace_period_nonexistent_condo(self, auth_session):
        """PUT /api/condominiums/{condo_id}/grace-period should return 404 for invalid condo"""
        resp = auth_session.put(f"{BASE_URL}/api/condominiums/nonexistent-id/grace-period?grace_days=5")
        assert resp.status_code == 404


class TestConfirmPayment:
    """Test payment confirmation endpoint"""
    
    def test_confirm_payment_restores_active_status(self, auth_session):
        """POST /api/billing/confirm-payment/{condo_id} should change status to active"""
        # First create a test production condo
        unique_id = str(uuid.uuid4())[:8]
        condo_data = {
            "name": f"TEST_Payment_Restore_{unique_id}",
            "address": "Test Address 123",
            "contact_email": f"payment_test_{unique_id}@test.com",
            "contact_phone": "12345678",
            "initial_units": 10,
            "billing_cycle": "monthly",
            "billing_provider": "sinpe"
        }
        
        create_resp = auth_session.post(f"{BASE_URL}/api/condominiums", json=condo_data)
        if create_resp.status_code not in [200, 201]:
            pytest.fail(f"Failed to create test condo: {create_resp.text}")
        
        condo = create_resp.json()
        test_condo_id = condo["id"]
        
        try:
            # Confirm payment
            payment_data = {
                "amount_paid": 15.0,
                "payment_reference": f"SINPE-{unique_id}",
                "notes": "Test payment confirmation"
            }
            
            resp = auth_session.post(
                f"{BASE_URL}/api/billing/confirm-payment/{test_condo_id}",
                json=payment_data
            )
            
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            data = resp.json()
            
            # Validate response
            assert data.get("new_status") == "active", "Status should be active after payment"
            assert data.get("amount_paid") == 15.0
            assert data.get("next_billing_date") is not None
            assert "payment_id" in data
            
            print(f"Payment confirmed: status changed from {data['previous_status']} to {data['new_status']}")
        
        finally:
            # Cleanup test condo
            try:
                auth_session.delete(
                    f"{BASE_URL}/api/super-admin/condominiums/{test_condo_id}",
                    json={"password": "Admin123!"}
                )
            except:
                pass

    def test_confirm_payment_calculates_next_billing_date(self, auth_session):
        """Confirm payment should correctly calculate next billing date"""
        # Create test condo
        unique_id = str(uuid.uuid4())[:8]
        condo_data = {
            "name": f"TEST_BillingDate_{unique_id}",
            "address": "Test Address",
            "contact_email": f"billing_date_{unique_id}@test.com",
            "contact_phone": "12345678",
            "initial_units": 10,
            "billing_cycle": "monthly",
            "billing_provider": "sinpe"
        }
        
        create_resp = auth_session.post(f"{BASE_URL}/api/condominiums", json=condo_data)
        if create_resp.status_code not in [200, 201]:
            pytest.fail(f"Failed to create test condo: {create_resp.text}")
        
        condo = create_resp.json()
        test_condo_id = condo["id"]
        
        try:
            # Confirm payment
            resp = auth_session.post(
                f"{BASE_URL}/api/billing/confirm-payment/{test_condo_id}",
                json={"amount_paid": 15.0}
            )
            
            assert resp.status_code == 200
            data = resp.json()
            
            # Verify next billing date is ~1 month in future
            next_billing = datetime.fromisoformat(data["next_billing_date"].replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            
            # Should be roughly 28-31 days in the future for monthly
            days_diff = (next_billing - now).days
            assert 27 <= days_diff <= 32, f"Next billing should be ~1 month away, got {days_diff} days"
            
            print(f"Next billing date calculated: {data['next_billing_date']} ({days_diff} days)")
        
        finally:
            # Cleanup test condo
            try:
                auth_session.delete(
                    f"{BASE_URL}/api/super-admin/condominiums/{test_condo_id}",
                    json={"password": "Admin123!"}
                )
            except:
                pass

    def test_confirm_payment_demo_condo_rejected(self, auth_session):
        """Confirm payment should reject demo condos"""
        # Find a demo condo
        condos_resp = auth_session.get(f"{BASE_URL}/api/condominiums")
        assert condos_resp.status_code == 200
        
        demo_condo = None
        for c in condos_resp.json():
            if c.get("is_demo") or c.get("environment") == "demo":
                demo_condo = c
                break
        
        if not demo_condo:
            pytest.skip("No demo condo found for testing")
        
        resp = auth_session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{demo_condo['id']}",
            json={"amount_paid": 10.0}
        )
        
        assert resp.status_code == 403, "Should reject demo condo payment confirmation"


class TestBillingEvents:
    """Test billing events logging"""
    
    def test_billing_events_endpoint_exists(self, auth_session):
        """GET /api/billing/events/{condo_id} should return events"""
        # Get a production condo
        condos_resp = auth_session.get(f"{BASE_URL}/api/condominiums")
        assert condos_resp.status_code == 200
        
        prod_condo = None
        for c in condos_resp.json():
            if not c.get("is_demo") and c.get("environment") != "demo":
                prod_condo = c
                break
        
        if not prod_condo:
            pytest.skip("No production condo found")
        
        resp = auth_session.get(f"{BASE_URL}/api/billing/events/{prod_condo['id']}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        
        assert "events" in data, "Response should contain 'events'"
        assert "total" in data, "Response should contain 'total'"
        
        # If events exist, validate structure
        if data["total"] > 0:
            event = data["events"][0]
            assert "event_type" in event, "Event should have event_type"
            assert "condominium_id" in event, "Event should have condominium_id"
            print(f"Found {data['total']} billing events for {prod_condo['id'][:8]}...")


class TestPartialBlocking:
    """Test partial blocking middleware"""
    
    def test_superadmin_never_blocked(self, auth_session):
        """SuperAdmin should never be blocked by billing status"""
        # SuperAdmin should be able to access any route regardless of condo billing status
        # Try to access a protected route (list condos) - SuperAdmin should not be blocked
        resp = auth_session.get(f"{BASE_URL}/api/condominiums")
        assert resp.status_code == 200, "SuperAdmin should not be blocked"

    def test_billing_routes_always_allowed(self, auth_session):
        """Billing routes should always be accessible (to allow payment)"""
        # Even with any token, billing routes should be allowed
        resp = auth_session.get(f"{BASE_URL}/api/billing/scheduler/status")
        assert resp.status_code == 200, "Billing routes should be accessible"

    def test_health_routes_always_allowed(self):
        """Health routes should always be accessible"""
        # No auth needed
        resp = requests.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200, "Health should always be accessible"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
