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

# Test credentials from the problem statement
SUPERADMIN_CREDS = {"email": "superadmin@genturix.com", "password": "Admin123!"}


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
    
    def test_02_get_or_create_admin_user(self):
        """Get or create an Admin user for testing"""
        # First, get list of condominiums to find one with an Admin
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.superadmin_token}"}
        
        # Get all condominiums
        response = self.session.get(f"{BASE_URL}/api/condominiums", headers=headers)
        print(f"Get condominiums response: {response.status_code}")
        assert response.status_code == 200
        
        condos = response.json()
        print(f"Found {len(condos)} condominiums")
        
        # Find a production condominium with at least some users
        target_condo = None
        for condo in condos:
            env = condo.get("environment", "production")
            is_demo = condo.get("is_demo", False)
            if env != "demo" and not is_demo:
                target_condo = condo
                break
        
        if not target_condo:
            # Create a test production condominium
            print("Creating test production condominium...")
            create_response = self.session.post(
                f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
                headers=headers,
                json={
                    "step1": {
                        "condominium_name": "Test Condo Admin Upgrade",
                        "address": "Test Address 123",
                        "contact_email": "testadmin@testcondo.com",
                        "contact_phone": "+1234567890"
                    },
                    "step2": {
                        "modules": {"security": True, "hr": True, "reservations": False}
                    },
                    "step3": {
                        "admin_full_name": "Test Admin User",
                        "admin_email": "testadmin@testcondo.com",
                        "admin_phone": "+1234567890",
                        "generate_password": True
                    },
                    "step4": {
                        "billing_email": "billing@testcondo.com",
                        "initial_units": 20,
                        "billing_cycle": "monthly",
                        "billing_provider": "manual"
                    },
                    "step5": {
                        "send_credentials": False
                    }
                }
            )
            print(f"Create condo response: {create_response.status_code}")
            if create_response.status_code in [200, 201]:
                condo_data = create_response.json()
                TestSeatUpgradeRequestFeature.admin_condo_id = condo_data.get("condominium_id")
                admin_password = condo_data.get("admin_password")
                if admin_password:
                    # Login as admin
                    admin_login = self.session.post(
                        f"{BASE_URL}/api/auth/login",
                        json={"email": "testadmin@testcondo.com", "password": admin_password}
                    )
                    if admin_login.status_code == 200:
                        TestSeatUpgradeRequestFeature.admin_token = admin_login.json()["access_token"]
                        print("Created new condo and logged in as Admin")
                        return
        else:
            TestSeatUpgradeRequestFeature.admin_condo_id = target_condo["id"]
            print(f"Using existing condo: {target_condo['name']} (id: {target_condo['id'][:8]}...)")
        
        # Try to find existing admin users for this condo
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/users?condo_id={TestSeatUpgradeRequestFeature.admin_condo_id}&role=Administrador",
            headers=headers
        )
        
        if response.status_code == 200:
            users = response.json()
            print(f"Found {len(users)} Administrador users")
            
            if users:
                # We found an Admin, but we don't have their password
                # Let's try to create a new admin user with known credentials
                pass
        
        # Create a new admin user with known credentials
        print("Creating new Admin user with known credentials...")
        test_admin_email = f"testadmin_{int(time.time())}@testcondo.com"
        create_user_response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers=headers,
            json={
                "email": test_admin_email,
                "password": "Admin123!",
                "full_name": "Test Admin For Upgrade",
                "role": "Administrador",
                "condominium_id": TestSeatUpgradeRequestFeature.admin_condo_id
            }
        )
        print(f"Create admin user response: {create_user_response.status_code}")
        
        if create_user_response.status_code in [200, 201]:
            # Login as new admin
            admin_login = self.session.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": test_admin_email, "password": "Admin123!"}
            )
            if admin_login.status_code == 200:
                TestSeatUpgradeRequestFeature.admin_token = admin_login.json()["access_token"]
                print(f"Created and logged in as Admin: {test_admin_email}")
                return
            else:
                print(f"Admin login failed: {admin_login.text}")
        else:
            print(f"Create admin failed: {create_user_response.text}")
        
        # If we couldn't create an admin, skip tests that need it
        pytest.skip("Could not create Admin user for testing")
    
    # ==== BACKEND API TESTS ====
    
    def test_03_upgrade_seats_requires_superadmin(self):
        """POST /api/billing/upgrade-seats now requires SuperAdmin role (not just Administrador)"""
        if not TestSeatUpgradeRequestFeature.admin_token:
            pytest.skip("No admin token available")
        
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.admin_token}"}
        
        # Admin trying to directly upgrade seats should get 403
        response = self.session.post(
            f"{BASE_URL}/api/billing/upgrade-seats",
            headers=headers,
            json={"additional_seats": 5}
        )
        print(f"Admin upgrade-seats response: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        # Should be 403 Forbidden (role not allowed)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: Admin cannot call upgrade-seats directly (403)")
    
    def test_04_admin_can_request_seat_upgrade(self):
        """POST /api/billing/request-seat-upgrade creates pending request (for Admins)"""
        if not TestSeatUpgradeRequestFeature.admin_token:
            pytest.skip("No admin token available")
        
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.admin_token}"}
        
        # First, get current billing info to know how many seats we have
        billing_response = self.session.get(
            f"{BASE_URL}/api/billing/info",
            headers=headers
        )
        print(f"Billing info response: {billing_response.status_code}")
        
        if billing_response.status_code == 200:
            billing_info = billing_response.json()
            current_seats = billing_info.get("paid_seats", 10)
            print(f"Current seats: {current_seats}")
        else:
            current_seats = 10
        
        # Request more seats
        new_seats = current_seats + 15
        response = self.session.post(
            f"{BASE_URL}/api/billing/request-seat-upgrade",
            headers=headers,
            json={
                "requested_seats": new_seats,
                "reason": "Testing seat upgrade request feature"
            }
        )
        print(f"Request seat upgrade response: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        # Could be 200 (success) or 400 (already pending request)
        if response.status_code == 400:
            data = response.json()
            if "Ya existe una solicitud pendiente" in data.get("detail", ""):
                print("PASS: Request endpoint works (already has pending request)")
                return
        
        assert response.status_code == 200, f"Expected 200 or 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "request_id" in data
        assert data["status"] == "pending"
        TestSeatUpgradeRequestFeature.test_request_id = data["request_id"]
        print(f"PASS: Created seat upgrade request: {data['request_id'][:8]}...")
    
    def test_05_admin_can_get_pending_request(self):
        """GET /api/billing/my-pending-request returns Admin's pending request"""
        if not TestSeatUpgradeRequestFeature.admin_token:
            pytest.skip("No admin token available")
        
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.admin_token}"}
        
        response = self.session.get(
            f"{BASE_URL}/api/billing/my-pending-request",
            headers=headers
        )
        print(f"My pending request response: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        # Could be 200 (has pending) or 404 (no pending)
        if response.status_code == 404:
            data = response.json()
            if "No hay solicitud pendiente" in data.get("detail", ""):
                print("PASS: Endpoint works (no pending request found)")
                return
        
        assert response.status_code == 200, f"Expected 200 or 404, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data or "condominium_id" in data
        assert data.get("status") == "pending"
        print(f"PASS: Retrieved pending request for condo")
    
    def test_06_superadmin_can_list_upgrade_requests(self):
        """GET /api/billing/upgrade-requests (SuperAdmin only) lists all pending requests"""
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.superadmin_token}"}
        
        response = self.session.get(
            f"{BASE_URL}/api/billing/upgrade-requests",
            headers=headers
        )
        print(f"List upgrade requests response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total" in data
        assert "requests" in data
        print(f"PASS: SuperAdmin can list {data['total']} upgrade requests")
    
    def test_07_admin_cannot_list_upgrade_requests(self):
        """Admin cannot access GET /api/billing/upgrade-requests (SuperAdmin only)"""
        if not TestSeatUpgradeRequestFeature.admin_token:
            pytest.skip("No admin token available")
        
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.admin_token}"}
        
        response = self.session.get(
            f"{BASE_URL}/api/billing/upgrade-requests",
            headers=headers
        )
        print(f"Admin list upgrade requests response: {response.status_code}")
        
        # Should be 403 Forbidden
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: Admin cannot list all upgrade requests (403)")
    
    def test_08_superadmin_can_approve_request(self):
        """PATCH /api/billing/approve-seat-upgrade/{request_id} (SuperAdmin only) approves"""
        if not TestSeatUpgradeRequestFeature.test_request_id:
            # Try to get a pending request to approve
            headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.superadmin_token}"}
            response = self.session.get(
                f"{BASE_URL}/api/billing/upgrade-requests",
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("requests"):
                    for req in data["requests"]:
                        if req.get("status") == "pending":
                            TestSeatUpgradeRequestFeature.test_request_id = req["id"]
                            break
        
        if not TestSeatUpgradeRequestFeature.test_request_id:
            pytest.skip("No pending request available to approve")
        
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.superadmin_token}"}
        
        response = self.session.patch(
            f"{BASE_URL}/api/billing/approve-seat-upgrade/{TestSeatUpgradeRequestFeature.test_request_id}?approve=true",
            headers=headers
        )
        print(f"Approve request response: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        # Could be 200 (approved) or 400 (already processed)
        if response.status_code == 400:
            data = response.json()
            if "ya fue" in data.get("detail", "").lower():
                print("PASS: Approval endpoint works (request already processed)")
                return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "approved"
        print(f"PASS: SuperAdmin approved request")
    
    def test_09_admin_cannot_approve_requests(self):
        """Admin cannot access PATCH /api/billing/approve-seat-upgrade (SuperAdmin only)"""
        if not TestSeatUpgradeRequestFeature.admin_token:
            pytest.skip("No admin token available")
        
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.admin_token}"}
        
        # Use a fake request ID - we just want to verify the role check
        response = self.session.patch(
            f"{BASE_URL}/api/billing/approve-seat-upgrade/fake-request-id?approve=true",
            headers=headers
        )
        print(f"Admin approve request response: {response.status_code}")
        
        # Should be 403 Forbidden (before checking if request exists)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASS: Admin cannot approve upgrade requests (403)")
    
    def test_10_superadmin_can_directly_upgrade(self):
        """SuperAdmin CAN call POST /api/billing/upgrade-seats directly"""
        headers = {"Authorization": f"Bearer {TestSeatUpgradeRequestFeature.superadmin_token}"}
        
        # Get a production condo ID first
        condos_response = self.session.get(f"{BASE_URL}/api/condominiums", headers=headers)
        if condos_response.status_code != 200:
            pytest.skip("Could not get condominiums")
        
        condos = condos_response.json()
        production_condo = None
        for condo in condos:
            env = condo.get("environment", "production")
            is_demo = condo.get("is_demo", False)
            if env != "demo" and not is_demo:
                production_condo = condo
                break
        
        if not production_condo:
            pytest.skip("No production condominium available")
        
        # Try upgrade-seats as SuperAdmin
        response = self.session.post(
            f"{BASE_URL}/api/billing/upgrade-seats",
            headers=headers,
            json={
                "additional_seats": 1,
                "condominium_id": production_condo["id"]
            }
        )
        print(f"SuperAdmin upgrade-seats response: {response.status_code}")
        print(f"Response body: {response.text[:300] if response.text else 'empty'}")
        
        # SuperAdmin should be able to access this endpoint (200 or Stripe-related error like 500)
        # The key point is they don't get 403
        assert response.status_code != 403, f"SuperAdmin should have access, but got 403"
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
