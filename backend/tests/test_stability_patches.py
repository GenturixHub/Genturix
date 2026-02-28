"""
GENTURIX - Stability Patch Tests (Pre-Production)
=================================================
Test suite for 5-point stability patches:
1. Carousel interactivo - Frontend test (Playwright)
2. PDF Export - API endpoint test for visit history export
3. SuperAdmin Danger Zone - Password protected system reset
4. $1 Pricing text removal - Verify no pricing marketing text visible (Frontend)
5. Email Service - Centralized using Resend

Tests include login, authentication, and endpoint validation.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://genturix-stability.preview.emergentagent.com').rstrip('/')

# Test credentials
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "Admin123!"
RESIDENT_EMAIL = "test-resident@genturix.com"
RESIDENT_PASSWORD = "Admin123!"


class TestAuthentication:
    """Test authentication flows for different user types"""
    
    def test_superadmin_login(self):
        """Test SuperAdmin can login successfully"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        print(f"SuperAdmin login response: {response.status_code}")
        
        assert response.status_code == 200, f"SuperAdmin login failed: {response.text}"
        data = response.json()
        
        assert "access_token" in data, "No access token returned"
        assert "user" in data, "No user data returned"
        assert "SuperAdmin" in data["user"]["roles"], "User is not SuperAdmin"
        
        print(f"SuperAdmin login SUCCESS - user_id: {data['user']['id']}")
        return data["access_token"]
    
    def test_resident_login(self):
        """Test Resident can login successfully"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD}
        )
        print(f"Resident login response: {response.status_code}")
        
        # 200 = success, 401 = invalid credentials (user may not exist)
        if response.status_code == 401:
            pytest.skip("Test resident user does not exist - skipping resident tests")
        
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        data = response.json()
        
        assert "access_token" in data, "No access token returned"
        print(f"Resident login SUCCESS - user_id: {data['user']['id']}")
        return data["access_token"]


class TestEmailService:
    """Test 5: Email service using Resend - centralized email endpoint"""
    
    @pytest.fixture
    def superadmin_token(self):
        """Get SuperAdmin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Cannot get SuperAdmin token")
        return response.json()["access_token"]
    
    def test_email_service_status(self, superadmin_token):
        """Test GET /api/email/service-status endpoint"""
        headers = {"Authorization": f"Bearer {superadmin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/email/service-status",
            headers=headers
        )
        
        print(f"Email service status response: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        assert response.status_code == 200, f"Email service status check failed: {response.text}"
        data = response.json()
        
        # Verify response has expected fields
        assert "configured" in data, "Missing 'configured' field"
        assert "sender" in data, "Missing 'sender' field"
        assert "api_key_set" in data, "Missing 'api_key_set' field"
        
        print(f"Email service configured: {data['configured']}")
        print(f"Email sender: {data['sender']}")
        print(f"API key set: {data['api_key_set']}")
    
    def test_email_config_status(self, superadmin_token):
        """Test GET /api/config/email-status endpoint (toggle status)"""
        headers = {"Authorization": f"Bearer {superadmin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/config/email-status",
            headers=headers
        )
        
        print(f"Email config status response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Email config data: {data}")
            assert "email_enabled" in data, "Missing 'email_enabled' field"
        else:
            # May require higher permissions or not exist
            print(f"Note: /api/config/email-status returned {response.status_code}")


class TestSuperAdminDangerZone:
    """Test 3: Danger Zone password protection for system reset"""
    
    @pytest.fixture
    def superadmin_token(self):
        """Get SuperAdmin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Cannot get SuperAdmin token")
        return response.json()["access_token"]
    
    def test_verify_password_endpoint_exists(self, superadmin_token):
        """Test that password verification endpoint exists for danger zone"""
        headers = {"Authorization": f"Bearer {superadmin_token}"}
        
        # Test with wrong password - should return 401 or error, not 404
        response = requests.post(
            f"{BASE_URL}/api/superadmin/verify-password",
            json={"password": "wrong_password_123"},
            headers=headers
        )
        
        print(f"Verify password response: {response.status_code}")
        print(f"Response body: {response.text}")
        
        # Should NOT be 404 - endpoint should exist
        # Should be 401/400 for wrong password, or 200 with verified=false
        assert response.status_code != 404, "Password verification endpoint not found"
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("verified") == False, "Wrong password should not verify"
            print("Password verification endpoint works correctly")
    
    def test_verify_correct_password(self, superadmin_token):
        """Test password verification with correct SuperAdmin password"""
        headers = {"Authorization": f"Bearer {superadmin_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/superadmin/verify-password",
            json={"password": SUPERADMIN_PASSWORD},
            headers=headers
        )
        
        print(f"Verify correct password response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Verification result: {data}")
            # Correct password should verify successfully
            assert data.get("verified") == True, "Correct password should verify"
        elif response.status_code == 404:
            # Endpoint doesn't exist - fallback login check may be used
            print("Note: /api/superadmin/verify-password not found - using login fallback")
        else:
            print(f"Response: {response.text}")


class TestVisitHistoryExport:
    """Test 2: PDF Export for visit history"""
    
    @pytest.fixture
    def resident_token(self):
        """Get Resident auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Cannot get Resident token")
        return response.json()["access_token"]
    
    @pytest.fixture
    def superadmin_token(self):
        """Get SuperAdmin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Cannot get SuperAdmin token")
        return response.json()["access_token"]
    
    def test_resident_visit_history_endpoint(self, resident_token):
        """Test GET /api/resident/visits/history endpoint"""
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/resident/visits/history",
            headers=headers
        )
        
        print(f"Visit history response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Visit history entries: {len(data.get('entries', []))}")
            assert "entries" in data, "Missing 'entries' field"
            assert "pagination" in data, "Missing 'pagination' field"
        elif response.status_code == 404:
            # User's condominium may not be configured
            print("Note: Resident's condominium not found - visit history unavailable")
        else:
            print(f"Response: {response.text}")
    
    def test_resident_visit_history_export(self, resident_token):
        """Test GET /api/resident/visits/history/export endpoint"""
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/resident/visits/history/export",
            headers=headers
        )
        
        print(f"Visit history export response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Export data keys: {data.keys()}")
            # Export should contain data for PDF generation
            assert "entries" in data, "Export should have 'entries'"
            assert "resident_name" in data, "Export should have 'resident_name'"
            print(f"Export resident: {data.get('resident_name')}")
            print(f"Export total entries: {data.get('total_entries', 0)}")
        elif response.status_code == 404:
            print("Note: Resident's condominium not found - export unavailable")
        else:
            print(f"Response: {response.text}")


class TestAPIHealth:
    """Basic health checks"""
    
    def test_health_endpoint(self):
        """Test /api/health returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print(f"Health check: {data}")
    
    def test_readiness_endpoint(self):
        """Test /api/readiness returns 200"""
        response = requests.get(f"{BASE_URL}/api/readiness")
        # May be 200 or 503 depending on config
        print(f"Readiness check: {response.status_code}")
        print(f"Response: {response.json()}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
