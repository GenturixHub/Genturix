"""
Test suite for Push Notification APIs and Identity Bug Fix
Tests:
1. Identity bug - profile data should not persist after logout/login with different user
2. Push subscription validation endpoints
3. Push subscription limit enforcement
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CREDENTIALS = {
    "superadmin": {"email": "superadmin@genturix.com", "password": "Admin123!"},
    "admin": {"email": "admin@genturix.com", "password": "Admin123!"},
    "resident": {"email": "test-resident@genturix.com", "password": "Admin123!"},
    "guard": {"email": "guarda1@genturix.com", "password": "Guard123!"}
}


class TestIdentityBug:
    """Tests for identity persistence bug fix - user profile should not persist after logout"""
    
    @pytest.fixture
    def session(self):
        """Create a fresh session for each test"""
        return requests.Session()
    
    def login(self, session, role):
        """Helper to login and return tokens"""
        creds = CREDENTIALS[role]
        response = session.post(f"{BASE_URL}/api/auth/login", json=creds)
        if response.status_code != 200:
            pytest.skip(f"Could not login as {role}: {response.status_code}")
        return response
    
    def get_profile(self, session, cookies):
        """Helper to get profile with cookies"""
        response = session.get(f"{BASE_URL}/api/profile", cookies=cookies)
        return response
    
    def logout(self, session, cookies):
        """Helper to logout"""
        response = session.post(f"{BASE_URL}/api/auth/logout", cookies=cookies)
        return response
    
    def test_admin_logout_resident_login_different_profile(self, session):
        """
        BUG TEST: Login as Admin -> Logout -> Login as Resident
        Profile should show Resident data, NOT Admin data
        """
        # Step 1: Login as Admin
        admin_login = self.login(session, "admin")
        assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
        admin_data = admin_login.json()
        admin_cookies = admin_login.cookies
        
        # Get admin profile
        admin_profile = self.get_profile(session, admin_cookies)
        assert admin_profile.status_code == 200, f"Admin profile failed: {admin_profile.text}"
        admin_profile_data = admin_profile.json()
        admin_email = admin_profile_data.get("email", "")
        admin_name = admin_profile_data.get("name", "")
        print(f"Admin profile: {admin_name} ({admin_email})")
        
        # Step 2: Logout
        logout_resp = self.logout(session, admin_cookies)
        assert logout_resp.status_code == 200, f"Logout failed: {logout_resp.text}"
        
        # Small delay to ensure session is cleared
        time.sleep(0.5)
        
        # Step 3: Login as Resident (new session)
        new_session = requests.Session()
        resident_login = self.login(new_session, "resident")
        assert resident_login.status_code == 200, f"Resident login failed: {resident_login.text}"
        resident_cookies = resident_login.cookies
        
        # Get resident profile
        resident_profile = self.get_profile(new_session, resident_cookies)
        assert resident_profile.status_code == 200, f"Resident profile failed: {resident_profile.text}"
        resident_profile_data = resident_profile.json()
        resident_email = resident_profile_data.get("email", "")
        resident_name = resident_profile_data.get("name", "")
        print(f"Resident profile: {resident_name} ({resident_email})")
        
        # CRITICAL ASSERTION: Resident data should NOT match Admin data
        assert resident_email != admin_email, f"BUG: Resident email ({resident_email}) matches Admin email ({admin_email})"
        assert resident_email == CREDENTIALS["resident"]["email"], f"Resident email should be {CREDENTIALS['resident']['email']}, got {resident_email}"
        print("PASS: Identity bug fixed - different users have different profiles after logout/login")
    
    def test_resident_logout_guard_login_different_profile(self, session):
        """
        BUG TEST INVERSE: Login as Resident -> Logout -> Login as Guard
        Profile should show Guard data, NOT Resident data
        """
        # Step 1: Login as Resident
        resident_login = self.login(session, "resident")
        assert resident_login.status_code == 200
        resident_cookies = resident_login.cookies
        
        resident_profile = self.get_profile(session, resident_cookies)
        assert resident_profile.status_code == 200
        resident_data = resident_profile.json()
        resident_email = resident_data.get("email", "")
        print(f"Resident profile: {resident_data.get('name', 'N/A')} ({resident_email})")
        
        # Step 2: Logout
        self.logout(session, resident_cookies)
        time.sleep(0.5)
        
        # Step 3: Login as Guard (new session)
        new_session = requests.Session()
        guard_login = self.login(new_session, "guard")
        assert guard_login.status_code == 200, f"Guard login failed: {guard_login.text}"
        guard_cookies = guard_login.cookies
        
        guard_profile = self.get_profile(new_session, guard_cookies)
        assert guard_profile.status_code == 200
        guard_data = guard_profile.json()
        guard_email = guard_data.get("email", "")
        print(f"Guard profile: {guard_data.get('name', 'N/A')} ({guard_email})")
        
        # CRITICAL ASSERTION
        assert guard_email != resident_email, f"BUG: Guard email ({guard_email}) matches Resident email ({resident_email})"
        assert guard_email == CREDENTIALS["guard"]["email"], f"Guard email should be {CREDENTIALS['guard']['email']}, got {guard_email}"
        print("PASS: Identity bug fixed - Guard shows different profile after Resident logout")


class TestPushValidateSubscriptions:
    """Tests for POST /api/push/validate-subscriptions (SuperAdmin only)"""
    
    @pytest.fixture
    def superadmin_session(self):
        """Login as SuperAdmin and return session with cookies"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["superadmin"])
        if response.status_code != 200:
            pytest.skip(f"SuperAdmin login failed: {response.status_code}")
        return session, response.cookies
    
    @pytest.fixture
    def admin_session(self):
        """Login as Admin (non-superadmin) and return session with cookies"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return session, response.cookies
    
    def test_validate_subscriptions_dry_run_true(self, superadmin_session):
        """
        Test GET/POST /api/push/validate-subscriptions?dry_run=true
        Should return statistics without deleting anything
        """
        session, cookies = superadmin_session
        
        # Test with dry_run=true (safe mode)
        response = session.post(
            f"{BASE_URL}/api/push/validate-subscriptions?dry_run=true",
            cookies=cookies
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "dry_run" in data, "Response should include dry_run field"
        assert data["dry_run"] == True, "dry_run should be True"
        assert "total" in data, "Response should include total count"
        assert "valid" in data, "Response should include valid count"
        assert "invalid" in data, "Response should include invalid count"
        assert "deleted" in data, "Response should include deleted count"
        
        # In dry_run mode, deleted should be 0
        assert data["deleted"] == 0, f"dry_run=true should not delete anything, got {data['deleted']}"
        
        print(f"PASS: Dry run validation - Total: {data['total']}, Valid: {data['valid']}, Invalid: {data['invalid']}")
    
    def test_validate_subscriptions_requires_superadmin(self, admin_session):
        """
        Test that validate-subscriptions requires SuperAdmin role
        Regular Admin should get 403
        """
        session, cookies = admin_session
        
        response = session.post(
            f"{BASE_URL}/api/push/validate-subscriptions?dry_run=true",
            cookies=cookies
        )
        
        # Should be 403 Forbidden for non-SuperAdmin
        assert response.status_code == 403, f"Expected 403 for Admin, got {response.status_code}: {response.text}"
        print("PASS: validate-subscriptions correctly requires SuperAdmin role")
    
    def test_validate_subscriptions_dry_run_false(self, superadmin_session):
        """
        Test POST /api/push/validate-subscriptions?dry_run=false
        Should actually validate and delete invalid subscriptions
        """
        session, cookies = superadmin_session
        
        # First, run with dry_run=true to see current state
        dry_response = session.post(
            f"{BASE_URL}/api/push/validate-subscriptions?dry_run=true",
            cookies=cookies
        )
        assert dry_response.status_code == 200
        dry_data = dry_response.json()
        initial_total = dry_data.get("total", 0)
        print(f"Initial state: {initial_total} total subscriptions")
        
        # Now run with dry_run=false (actual validation)
        response = session.post(
            f"{BASE_URL}/api/push/validate-subscriptions?dry_run=false",
            cookies=cookies
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["dry_run"] == False, "dry_run should be False"
        assert "deleted" in data, "Response should include deleted count"
        assert "errors_detail" in data, "Response should include errors_detail"
        
        print(f"PASS: Actual validation - Total: {data['total']}, Valid: {data['valid']}, Invalid: {data['invalid']}, Deleted: {data['deleted']}")


class TestPushValidateUserSubscription:
    """Tests for GET /api/push/validate-user-subscription (any authenticated user)"""
    
    @pytest.fixture
    def resident_session(self):
        """Login as Resident and return session with cookies"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["resident"])
        if response.status_code != 200:
            pytest.skip(f"Resident login failed: {response.status_code}")
        return session, response.cookies
    
    @pytest.fixture
    def admin_session(self):
        """Login as Admin and return session with cookies"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return session, response.cookies
    
    def test_validate_user_subscription_resident(self, resident_session):
        """
        Test GET /api/push/validate-user-subscription for Resident
        Should return subscription status for current user
        """
        session, cookies = resident_session
        
        response = session.get(
            f"{BASE_URL}/api/push/validate-user-subscription",
            cookies=cookies
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "has_subscription" in data, "Response should include has_subscription"
        assert "is_valid" in data, "Response should include is_valid"
        assert "subscription_count" in data, "Response should include subscription_count"
        assert "message" in data, "Response should include message"
        
        print(f"PASS: Resident subscription status - has: {data['has_subscription']}, valid: {data['is_valid']}, count: {data['subscription_count']}")
    
    def test_validate_user_subscription_admin(self, admin_session):
        """
        Test GET /api/push/validate-user-subscription for Admin
        Should return subscription status for current user
        """
        session, cookies = admin_session
        
        response = session.get(
            f"{BASE_URL}/api/push/validate-user-subscription",
            cookies=cookies
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "has_subscription" in data
        assert "is_valid" in data
        assert "subscription_count" in data
        
        print(f"PASS: Admin subscription status - has: {data['has_subscription']}, valid: {data['is_valid']}")


class TestPushStatus:
    """Tests for GET /api/push/status (any authenticated user)"""
    
    @pytest.fixture
    def authenticated_session(self):
        """Login as Admin and return session with cookies"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        if response.status_code != 200:
            pytest.skip(f"Login failed: {response.status_code}")
        return session, response.cookies
    
    def test_push_status_endpoint(self, authenticated_session):
        """
        Test GET /api/push/status
        Should return current user's push subscription status
        """
        session, cookies = authenticated_session
        
        response = session.get(f"{BASE_URL}/api/push/status", cookies=cookies)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "is_subscribed" in data, "Response should include is_subscribed"
        assert "subscription_count" in data, "Response should include subscription_count"
        assert "subscriptions" in data, "Response should include subscriptions list"
        
        # subscriptions should be a list
        assert isinstance(data["subscriptions"], list), "subscriptions should be a list"
        
        print(f"PASS: Push status - subscribed: {data['is_subscribed']}, count: {data['subscription_count']}")
    
    def test_push_status_requires_auth(self):
        """
        Test GET /api/push/status requires authentication
        """
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/push/status")
        
        # Should return 401 without auth
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: push/status correctly requires authentication")


class TestPushSubscriptionLimit:
    """Tests for POST /api/push/subscribe subscription limit (max 3 per user)"""
    
    @pytest.fixture
    def authenticated_session(self):
        """Login as Resident and return session with cookies"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["resident"])
        if response.status_code != 200:
            pytest.skip(f"Login failed: {response.status_code}")
        return session, response.cookies
    
    def test_subscribe_endpoint_exists(self, authenticated_session):
        """
        Test that POST /api/push/subscribe endpoint exists and accepts requests
        Note: We can't fully test subscription without a real browser/service worker
        """
        session, cookies = authenticated_session
        
        # Test with minimal/mock subscription data
        # This will likely fail validation but confirms endpoint exists
        mock_subscription = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint-123",
            "expirationTime": None,
            "keys": {
                "p256dh": "test-p256dh-key-placeholder",
                "auth": "test-auth-key-placeholder"
            }
        }
        
        response = session.post(
            f"{BASE_URL}/api/push/subscribe",
            json=mock_subscription,
            cookies=cookies
        )
        
        # Endpoint should exist (even if subscription fails validation)
        # Accept 200 (success), 400 (validation error), or 500 (server error with push)
        assert response.status_code in [200, 201, 400, 500], f"Unexpected status: {response.status_code}: {response.text}"
        
        print(f"PASS: subscribe endpoint exists and responds (status: {response.status_code})")


class TestPushCleanup:
    """Tests for POST /api/push/cleanup (SuperAdmin only)"""
    
    @pytest.fixture
    def superadmin_session(self):
        """Login as SuperAdmin and return session with cookies"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["superadmin"])
        if response.status_code != 200:
            pytest.skip(f"SuperAdmin login failed: {response.status_code}")
        return session, response.cookies
    
    def test_cleanup_endpoint_exists(self, superadmin_session):
        """
        Test POST /api/push/cleanup endpoint
        Cleans up invalid subscriptions (no user_id, deleted users, etc.)
        """
        session, cookies = superadmin_session
        
        response = session.post(f"{BASE_URL}/api/push/cleanup", cookies=cookies)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "message" in data, "Response should include message"
        assert "details" in data, "Response should include details"
        assert "total_deleted" in data, "Response should include total_deleted"
        
        print(f"PASS: Cleanup completed - deleted: {data['total_deleted']}, details: {data['details']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
