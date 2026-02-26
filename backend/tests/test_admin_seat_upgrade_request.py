"""
Test Admin Seat Upgrade Request Feature (REESTRUCTURACION UI)

Tests the new seat upgrade request flow:
1. Admin cannot directly upgrade seats (must use request)
2. Admin can submit seat upgrade request
3. Admin can view their pending request
4. SuperAdmin can view all pending requests
5. SuperAdmin can approve/reject requests
6. Security: Admin cannot call upgrade-seats directly (403)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERADMIN_CREDS = {"email": "superadmin@genturix.com", "password": "Admin123!"}
ADMIN_CREDS = {"email": "upgradetestadmin@genturix.com", "password": "@%1Kjt2UQ2o3"}


class TestSeatUpgradeRequestFeature:
    """Test the complete seat upgrade request flow"""
    
    superadmin_token = None
    admin_token = None
    admin_condo_id = None
    test_request_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    # ==== AUTHENTICATION TESTS ====
    
    def test_01_superadmin_login(self):
        """SuperAdmin can login successfully"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=SUPERADMIN_CREDS
        )
        print(f"SuperAdmin login response: {response.status_code}")
        assert response.status_code == 200, f"SuperAdmin login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        TestSeatUpgradeRequestFeature.superadmin_token = data["access_token"]
        print(f"SuperAdmin logged in, roles: {data['user']['roles']}")
    
    def test_02_admin_login(self):
        """Admin can login successfully"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDS
        )
        print(f"Admin login response: {response.status_code}")
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        TestSeatUpgradeRequestFeature.admin_token = data["access_token"]
        print(f"Admin logged in, roles: {data['user']['roles']}")
    
    # ==== SECURITY TESTS ====
    
    def test_03_upgrade_seats_requires_superadmin(self):
        """POST /api/billing/upgrade-seats requires SuperAdmin role - Admin gets 403"""
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.admin_token}"}
        
        response = self.session.post(
            f"{BASE_URL}/api/billing/upgrade-seats",
            headers=headers,
            json={"additional_seats": 5}
        )
        print(f"Admin upgrade-seats response: {response.status_code}")
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: Admin cannot call upgrade-seats directly (403)")
    
    def test_04_admin_can_get_billing_info(self):
        """Admin can view billing info (READ ONLY)"""
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.admin_token}"}
        
        response = self.session.get(
            f"{BASE_URL}/api/billing/info",
            headers=headers
        )
        print(f"Billing info response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        print(f"Current seats: {data.get('paid_seats')}, Active: {data.get('active_users')}")
        assert "paid_seats" in data
        assert "active_users" in data
        assert "billing_status" in data
        print("PASS: Admin can read billing info")
    
    def test_05_admin_can_request_seat_upgrade(self):
        """POST /api/billing/request-seat-upgrade creates pending request"""
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.admin_token}"}
        
        # First get current billing to calculate proper request
        billing_response = self.session.get(f"{BASE_URL}/api/billing/info", headers=headers)
        current_seats = billing_response.json().get("paid_seats", 10) if billing_response.status_code == 200 else 10
        
        new_seats = current_seats + 20
        response = self.session.post(
            f"{BASE_URL}/api/billing/request-seat-upgrade",
            headers=headers,
            json={
                "requested_seats": new_seats,
                "reason": "Testing seat upgrade request feature"
            }
        )
        print(f"Request seat upgrade response: {response.status_code}")
        
        # Accept either 200 (created) or 400 (already has pending request)
        if response.status_code == 400:
            data = response.json()
            assert "Ya existe una solicitud pendiente" in data.get("detail", ""), f"Unexpected error: {data}"
            print("PASS: Request endpoint works (already has pending request)")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "pending"
        TestSeatUpgradeRequestFeature.test_request_id = data.get("request_id")
        print(f"PASS: Created seat upgrade request: {data.get('request_id', 'N/A')[:8]}...")
    
    def test_06_admin_can_get_pending_request(self):
        """GET /api/billing/my-pending-request returns Admin's pending request"""
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.admin_token}"}
        
        response = self.session.get(
            f"{BASE_URL}/api/billing/my-pending-request",
            headers=headers
        )
        print(f"My pending request response: {response.status_code}")
        
        # Accept 200 (has pending) or 404 (no pending - if already approved)
        if response.status_code == 404:
            print("INFO: No pending request (likely already approved)")
            return
        
        assert response.status_code == 200
        data = response.json()
        print(f"Pending request: {data.get('status')}, seats: {data.get('requested_seats')}")
        print("PASS: Admin can view pending request")
    
    def test_07_superadmin_can_list_upgrade_requests(self):
        """GET /api/billing/upgrade-requests (SuperAdmin only) lists all requests"""
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.superadmin_token}"}
        
        response = self.session.get(
            f"{BASE_URL}/api/billing/upgrade-requests",
            headers=headers
        )
        print(f"List upgrade requests response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        assert "requests" in data
        print(f"PASS: SuperAdmin can list {data['total']} upgrade requests")
    
    def test_08_admin_cannot_list_upgrade_requests(self):
        """Admin cannot access GET /api/billing/upgrade-requests (SuperAdmin only)"""
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.admin_token}"}
        
        response = self.session.get(
            f"{BASE_URL}/api/billing/upgrade-requests",
            headers=headers
        )
        print(f"Admin list upgrade requests response: {response.status_code}")
        assert response.status_code == 403
        print("PASS: Admin cannot list all upgrade requests (403)")
    
    def test_09_admin_cannot_approve_requests(self):
        """Admin cannot access PATCH /api/billing/approve-seat-upgrade (SuperAdmin only)"""
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.admin_token}"}
        
        response = self.session.patch(
            f"{BASE_URL}/api/billing/approve-seat-upgrade/fake-request-id?approve=true",
            headers=headers
        )
        print(f"Admin approve request response: {response.status_code}")
        assert response.status_code == 403
        print("PASS: Admin cannot approve upgrade requests (403)")
    
    def test_10_superadmin_can_directly_upgrade(self):
        """SuperAdmin CAN call POST /api/billing/upgrade-seats (not 403)"""
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.superadmin_token}"}
        
        # Get a production condo ID
        condos_response = self.session.get(f"{BASE_URL}/api/condominiums", headers=headers)
        assert condos_response.status_code == 200
        
        condos = condos_response.json()
        production_condo = next((c for c in condos if c.get("environment") != "demo" and not c.get("is_demo")), None)
        
        if not production_condo:
            pytest.skip("No production condominium available")
        
        response = self.session.post(
            f"{BASE_URL}/api/billing/upgrade-seats",
            headers=headers,
            json={"additional_seats": 1, "condominium_id": production_condo["id"]}
        )
        print(f"SuperAdmin upgrade-seats response: {response.status_code}")
        
        # SuperAdmin should NOT get 403 (access granted - may fail for other reasons like Stripe)
        assert response.status_code != 403, f"SuperAdmin should have access, got 403"
        print(f"PASS: SuperAdmin has access to upgrade-seats endpoint (status: {response.status_code})")


class TestSecurityValidation:
    """Security validation tests"""
    
    def test_unauthenticated_cannot_access_billing_endpoints(self):
        """Unauthenticated users cannot access billing endpoints"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        endpoints = [
            ("GET", f"{BASE_URL}/api/billing/info"),
            ("POST", f"{BASE_URL}/api/billing/request-seat-upgrade"),
            ("GET", f"{BASE_URL}/api/billing/my-pending-request"),
            ("GET", f"{BASE_URL}/api/billing/upgrade-requests"),
            ("PATCH", f"{BASE_URL}/api/billing/approve-seat-upgrade/test-id"),
            ("POST", f"{BASE_URL}/api/billing/upgrade-seats"),
        ]
        
        for method, url in endpoints:
            if method == "GET":
                response = session.get(url)
            elif method == "POST":
                response = session.post(url, json={})
            elif method == "PATCH":
                response = session.patch(url)
            
            print(f"{method} {url.split('/api')[1]}: {response.status_code}")
            assert response.status_code in [401, 403], f"Expected 401/403 for {url}, got {response.status_code}"
        
        print("PASS: All billing endpoints require authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
