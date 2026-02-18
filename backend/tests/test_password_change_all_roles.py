"""
GENTURIX - Password Change Feature Tests
Tests for POST /api/auth/change-password across all roles
Testing: Guard, Resident, Admin password change functionality
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials for each role
TEST_USERS = {
    "guard": {
        "email": "guarda1@genturix.com",
        "password": "Guard123!"
    },
    "resident": {
        "email": "residente@genturix.com",
        "password": "Resi123!"
    },
    "admin": {
        "email": "admin@genturix.com",
        "password": "Admin123!"
    }
}

class TestPasswordChangeEndpoint:
    """Tests for POST /api/auth/change-password endpoint"""
    
    @pytest.fixture
    def api_client(self):
        """Shared requests session"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session
    
    def login_user(self, api_client, email, password):
        """Helper to login and get token"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_change_password_endpoint_exists(self, api_client):
        """Test that change-password endpoint exists and requires auth"""
        response = api_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": "test",
            "new_password": "TestNew123!",
            "confirm_password": "TestNew123!"
        })
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401 or response.status_code == 403, \
            f"Endpoint should require auth, got {response.status_code}"
        print("PASS: Change password endpoint exists and requires authentication")
    
    def test_guard_can_login(self, api_client):
        """Test guard user can login with provided credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USERS["guard"]["email"],
            "password": TEST_USERS["guard"]["password"]
        })
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert data.get("user", {}).get("email") == TEST_USERS["guard"]["email"]
        print(f"PASS: Guard login successful - {data.get('user', {}).get('full_name')}")
    
    def test_resident_can_login(self, api_client):
        """Test resident user can login with provided credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USERS["resident"]["email"],
            "password": TEST_USERS["resident"]["password"]
        })
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert data.get("user", {}).get("email") == TEST_USERS["resident"]["email"]
        print(f"PASS: Resident login successful - {data.get('user', {}).get('full_name')}")
    
    def test_admin_can_login(self, api_client):
        """Test admin user can login with provided credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USERS["admin"]["email"],
            "password": TEST_USERS["admin"]["password"]
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert data.get("user", {}).get("email") == TEST_USERS["admin"]["email"]
        print(f"PASS: Admin login successful - {data.get('user', {}).get('full_name')}")
    
    def test_change_password_wrong_current_password(self, api_client):
        """Test change password fails with wrong current password"""
        # Login as guard
        token = self.login_user(api_client, TEST_USERS["guard"]["email"], TEST_USERS["guard"]["password"])
        assert token, "Failed to login as guard"
        
        # Try to change password with wrong current password
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        response = api_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": "WrongPassword123!",
            "new_password": "NewGuard123!",
            "confirm_password": "NewGuard123!"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "incorrecta" in data.get("detail", "").lower() or "incorrect" in data.get("detail", "").lower(), \
            f"Error message should mention incorrect password: {data}"
        print("PASS: Change password correctly rejects wrong current password")
    
    def test_change_password_mismatched_passwords(self, api_client):
        """Test change password fails when new and confirm passwords don't match"""
        # Login as guard
        token = self.login_user(api_client, TEST_USERS["guard"]["email"], TEST_USERS["guard"]["password"])
        assert token, "Failed to login as guard"
        
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        response = api_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": TEST_USERS["guard"]["password"],
            "new_password": "NewGuard123!",
            "confirm_password": "DifferentPassword123!"
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "coinciden" in data.get("detail", "").lower() or "match" in data.get("detail", "").lower(), \
            f"Error message should mention password mismatch: {data}"
        print("PASS: Change password correctly rejects mismatched passwords")
    
    def test_change_password_same_as_current(self, api_client):
        """Test change password fails when new password same as current"""
        # Login as resident
        token = self.login_user(api_client, TEST_USERS["resident"]["email"], TEST_USERS["resident"]["password"])
        assert token, "Failed to login as resident"
        
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        response = api_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": TEST_USERS["resident"]["password"],
            "new_password": TEST_USERS["resident"]["password"],  # Same as current
            "confirm_password": TEST_USERS["resident"]["password"]
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "diferente" in data.get("detail", "").lower() or "different" in data.get("detail", "").lower(), \
            f"Error message should mention password must be different: {data}"
        print("PASS: Change password correctly rejects same password as current")
    
    def test_change_password_too_short(self, api_client):
        """Test change password fails with password less than 8 characters"""
        # Login as admin
        token = self.login_user(api_client, TEST_USERS["admin"]["email"], TEST_USERS["admin"]["password"])
        assert token, "Failed to login as admin"
        
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        response = api_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": TEST_USERS["admin"]["password"],
            "new_password": "Short1!",  # 7 chars
            "confirm_password": "Short1!"
        })
        assert response.status_code == 422 or response.status_code == 400, \
            f"Expected 422 or 400 for short password, got {response.status_code}"
        print("PASS: Change password correctly validates minimum length")
    
    def test_change_password_missing_uppercase(self, api_client):
        """Test change password fails without uppercase letter"""
        # Login as guard
        token = self.login_user(api_client, TEST_USERS["guard"]["email"], TEST_USERS["guard"]["password"])
        assert token, "Failed to login as guard"
        
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        response = api_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": TEST_USERS["guard"]["password"],
            "new_password": "lowercase123!",  # No uppercase
            "confirm_password": "lowercase123!"
        })
        assert response.status_code == 422 or response.status_code == 400, \
            f"Expected 422 or 400 for missing uppercase, got {response.status_code}"
        print("PASS: Change password correctly validates uppercase requirement")
    
    def test_change_password_missing_number(self, api_client):
        """Test change password fails without number"""
        # Login as resident
        token = self.login_user(api_client, TEST_USERS["resident"]["email"], TEST_USERS["resident"]["password"])
        assert token, "Failed to login as resident"
        
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        response = api_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": TEST_USERS["resident"]["password"],
            "new_password": "NoNumberHere!",  # No number
            "confirm_password": "NoNumberHere!"
        })
        assert response.status_code == 422 or response.status_code == 400, \
            f"Expected 422 or 400 for missing number, got {response.status_code}"
        print("PASS: Change password correctly validates number requirement")
    
    def test_change_password_success_and_revert(self, api_client):
        """Test complete password change cycle: change then revert"""
        # Login as guard
        original_password = TEST_USERS["guard"]["password"]
        new_password = f"NewGuard{uuid.uuid4().hex[:4]}123!"
        
        token = self.login_user(api_client, TEST_USERS["guard"]["email"], original_password)
        assert token, "Failed to login as guard"
        
        # Change password
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        response = api_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": original_password,
            "new_password": new_password,
            "confirm_password": new_password
        })
        assert response.status_code == 200, f"Password change failed: {response.text}"
        data = response.json()
        assert "message" in data, "No success message in response"
        assert "exitosamente" in data.get("message", "").lower() or "success" in data.get("message", "").lower()
        assert data.get("sessions_invalidated") == True, "sessions_invalidated should be True"
        print(f"PASS: Password changed successfully - {data.get('message')}")
        
        # Try login with old password (should fail - sessions invalidated)
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USERS["guard"]["email"],
            "password": original_password
        })
        assert response.status_code == 401 or response.status_code == 400, \
            "Old password should not work after change"
        print("PASS: Old password correctly rejected after change")
        
        # Login with new password
        new_token = self.login_user(api_client, TEST_USERS["guard"]["email"], new_password)
        assert new_token, "Failed to login with new password"
        print("PASS: New password works for login")
        
        # Revert password back to original
        api_client.headers.update({"Authorization": f"Bearer {new_token}"})
        response = api_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": new_password,
            "new_password": original_password,
            "confirm_password": original_password
        })
        assert response.status_code == 200, f"Password revert failed: {response.text}"
        print("PASS: Password reverted to original successfully")
        
        # Verify original password works
        final_token = self.login_user(api_client, TEST_USERS["guard"]["email"], original_password)
        assert final_token, "Failed to login with original password after revert"
        print("PASS: Original password works after revert")


class TestPasswordChangeAllRoles:
    """Test that all roles have access to password change"""
    
    @pytest.fixture
    def api_client(self):
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session
    
    def test_guard_has_access_to_change_password(self, api_client):
        """Guard role can access change-password endpoint"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USERS["guard"]["email"],
            "password": TEST_USERS["guard"]["password"]
        })
        assert response.status_code == 200, f"Guard login failed"
        token = response.json().get("access_token")
        
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        # Just check endpoint is accessible (with wrong current password to not change it)
        response = api_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": "WrongPwd123!",
            "new_password": "TestNew123!",
            "confirm_password": "TestNew123!"
        })
        # 400 = accessible (bad request due to wrong password), 403 = forbidden, 401 = needs auth
        assert response.status_code == 400, f"Guard should have access, got {response.status_code}"
        print("PASS: Guard role has access to change-password endpoint")
    
    def test_resident_has_access_to_change_password(self, api_client):
        """Resident role can access change-password endpoint"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USERS["resident"]["email"],
            "password": TEST_USERS["resident"]["password"]
        })
        assert response.status_code == 200, f"Resident login failed"
        token = response.json().get("access_token")
        
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        response = api_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": "WrongPwd123!",
            "new_password": "TestNew123!",
            "confirm_password": "TestNew123!"
        })
        assert response.status_code == 400, f"Resident should have access, got {response.status_code}"
        print("PASS: Resident role has access to change-password endpoint")
    
    def test_admin_has_access_to_change_password(self, api_client):
        """Admin role can access change-password endpoint"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USERS["admin"]["email"],
            "password": TEST_USERS["admin"]["password"]
        })
        assert response.status_code == 200, f"Admin login failed"
        token = response.json().get("access_token")
        
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        response = api_client.post(f"{BASE_URL}/api/auth/change-password", json={
            "current_password": "WrongPwd123!",
            "new_password": "TestNew123!",
            "confirm_password": "TestNew123!"
        })
        assert response.status_code == 400, f"Admin should have access, got {response.status_code}"
        print("PASS: Admin role has access to change-password endpoint")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
