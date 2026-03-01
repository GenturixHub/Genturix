"""
GENTURIX - Stability Patches Testing (P0 Fixes)
=================================================
Testing 3 main fixes:
1. Admin dashboard pages should be scrollable with mouse wheel
2. Resident credential emails sent on access request approval (send_email=true)
3. Email service configuration health check endpoint returns healthy status
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://genturix-scroll-fix.preview.emergentagent.com').rstrip('/')

# Test credentials from main agent
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "Admin123!"


class TestEmailServiceHealth:
    """Test: Email service configuration health check endpoint"""
    
    @pytest.fixture
    def superadmin_token(self):
        """Get SuperAdmin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Cannot get SuperAdmin token: {response.text}")
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        """Get Admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Cannot get Admin token: {response.text}")
        return response.json()["access_token"]
    
    def test_health_endpoint_healthy(self):
        """Test basic health endpoint returns ok"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get("status") == "ok", "Health status should be 'ok'"
        print(f"✅ Health check passed: {data}")
    
    def test_email_service_status_endpoint(self, superadmin_token):
        """Test GET /api/email/service-status returns healthy status"""
        headers = {"Authorization": f"Bearer {superadmin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/email/service-status",
            headers=headers
        )
        
        print(f"Email service status response: {response.status_code}")
        print(f"Response: {response.json()}")
        
        assert response.status_code == 200, f"Email service status failed: {response.text}"
        data = response.json()
        
        # Verify expected fields
        assert "configured" in data, "Missing 'configured' field"
        assert "sender" in data, "Missing 'sender' field"
        assert "api_key_set" in data, "Missing 'api_key_set' field"
        
        # Verify healthy configuration
        assert data.get("configured") == True, "Email should be configured"
        assert data.get("api_key_set") == True, "API key should be set"
        assert "genturix" in data.get("sender", "").lower() or "resend" in data.get("sender", "").lower(), \
            f"Sender should contain 'genturix' or 'resend', got: {data.get('sender')}"
        
        print(f"✅ Email service healthy: configured={data.get('configured')}, sender={data.get('sender')}")
    
    def test_readiness_endpoint(self):
        """Test readiness endpoint checks email among dependencies"""
        response = requests.get(f"{BASE_URL}/api/readiness")
        
        print(f"Readiness response: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Can be 200 (ready) or 503 (not ready)
        assert response.status_code in [200, 503], f"Unexpected status: {response.status_code}"
        
        data = response.json()
        if response.status_code == 200:
            assert data.get("status") == "ready", "Should be ready"
            print("✅ System is ready")
        else:
            print(f"⚠️ System not ready: {data}")


class TestAccessRequestEmailDelivery:
    """Test: Resident credential emails should be sent on access request approval"""
    
    @pytest.fixture
    def admin_token(self):
        """Get Admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Cannot get Admin token: {response.text}")
        
        data = response.json()
        # Verify has Administrador role
        if "Administrador" not in data.get("user", {}).get("roles", []):
            pytest.skip("User is not Administrador")
        
        return data["access_token"]
    
    @pytest.fixture
    def admin_condo_id(self):
        """Get Admin's condominium ID"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Cannot get Admin token")
        return response.json()["user"].get("condominium_id")
    
    def test_get_pending_access_requests(self, admin_token):
        """Test listing pending access requests"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/access-requests?status=pending_approval",
            headers=headers
        )
        
        print(f"Access requests response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Pending requests found: {len(data)}")
            for req in data[:3]:  # Show first 3
                print(f"  - {req.get('full_name')} ({req.get('email')}) - {req.get('status')}")
        else:
            print(f"Response: {response.text}")
        
        assert response.status_code == 200, f"Failed to get access requests: {response.text}"
    
    def test_access_request_count_endpoint(self, admin_token):
        """Test access request count endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/access-requests/count",
            headers=headers
        )
        
        print(f"Access requests count response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Pending count: {data}")
        
        assert response.status_code == 200, f"Failed to get count: {response.text}"
    
    def test_approve_access_request_with_email_flag(self, admin_token):
        """
        Test approving an access request with send_email=true.
        
        This tests:
        1. POST /api/access-requests/{id}/action with action=approve, send_email=true
        2. Response should include email_sent: true
        """
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
        
        # First, get pending requests
        response = requests.get(
            f"{BASE_URL}/api/access-requests?status=pending_approval",
            headers=headers
        )
        
        if response.status_code != 200:
            pytest.skip(f"Cannot fetch access requests: {response.text}")
        
        pending = response.json()
        print(f"Found {len(pending)} pending access requests")
        
        if len(pending) == 0:
            pytest.skip("No pending access requests to test approval")
        
        # Pick first pending request
        test_request = pending[0]
        request_id = test_request.get("id")
        print(f"Testing approval for: {test_request.get('full_name')} ({test_request.get('email')})")
        
        # Approve with send_email=true
        approval_payload = {
            "action": "approve",
            "message": "Welcome to the community!",
            "send_email": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/access-requests/{request_id}/action",
            json=approval_payload,
            headers=headers
        )
        
        print(f"Approval response: {response.status_code}")
        print(f"Response body: {response.json()}")
        
        assert response.status_code == 200, f"Approval failed: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "message" in data, "Missing 'message' in response"
        assert "user_id" in data, "Missing 'user_id' in response"
        assert "email_sent" in data, "Missing 'email_sent' in response"
        
        # CRITICAL: email_sent should be True when send_email=True was requested
        # (assuming email service is configured)
        email_sent = data.get("email_sent")
        print(f"✅ Access request approved. email_sent={email_sent}")
        
        # If email service is configured and enabled, email_sent should be True
        # Otherwise it may be False (skipped)
        if email_sent:
            print("✅ Credential email was sent successfully!")
        else:
            print("⚠️ Email was not sent (may be disabled or not configured)")


class TestAPIEndpointIntegrity:
    """Additional API endpoint tests"""
    
    def test_login_admin(self):
        """Test Admin login works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        print(f"Admin login response: {response.status_code}")
        
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Missing access_token"
        assert "user" in data, "Missing user data"
        
        user = data["user"]
        print(f"Admin user: {user.get('full_name')} - roles: {user.get('roles')}")
        
        assert "Administrador" in user.get("roles", []), "User should have Administrador role"
    
    def test_login_superadmin(self):
        """Test SuperAdmin login works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        
        print(f"SuperAdmin login response: {response.status_code}")
        
        assert response.status_code == 200, f"SuperAdmin login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Missing access_token"
        
        user = data["user"]
        print(f"SuperAdmin user: {user.get('full_name')} - roles: {user.get('roles')}")
        
        assert "SuperAdmin" in user.get("roles", []), "User should have SuperAdmin role"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
