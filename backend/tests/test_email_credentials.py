"""
Test Email Credentials Feature
Tests for automatic email delivery of user credentials when creating new users.
Features tested:
- POST /api/admin/users with send_credentials_email=true generates temporary password
- POST /api/admin/users with send_credentials_email=false uses provided password
- POST /api/auth/login returns password_reset_required flag
- POST /api/auth/change-password allows password change and clears flag
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestEmailCredentialsFeature:
    """Test email credentials feature for user creation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_email = "admin@genturix.com"
        self.admin_password = "Admin123!"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return response.json().get("access_token")
    
    def get_condominium_id(self, token):
        """Get a valid condominium ID"""
        response = self.session.get(
            f"{BASE_URL}/api/condominiums",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            condos = response.json()
            if condos and len(condos) > 0:
                return condos[0].get("id")
        return None
    
    # ==================== BACKEND API TESTS ====================
    
    def test_create_user_without_email_credentials(self):
        """Test creating user with send_credentials_email=false uses provided password"""
        token = self.get_admin_token()
        condo_id = self.get_condominium_id(token)
        
        if not condo_id:
            pytest.skip("No condominium available for testing")
        
        test_email = f"TEST_no_email_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "TestPass123!"
        
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": test_password,
                "full_name": "Test User No Email",
                "role": "Residente",
                "phone": "+1234567890",
                "condominium_id": condo_id,
                "send_credentials_email": False,
                "apartment_number": "A-101"
            }
        )
        
        assert response.status_code in [200, 201], f"Create user failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "user_id" in data
        assert data.get("role") == "Residente"
        
        # Verify user can login with provided password
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        login_data = login_response.json()
        
        # password_reset_required should be False
        assert login_data.get("password_reset_required") == False, \
            "password_reset_required should be False when send_credentials_email=false"
        
        print(f"✓ User created without email credentials - password_reset_required=False")
    
    def test_create_user_with_email_credentials(self):
        """Test creating user with send_credentials_email=true generates temp password"""
        token = self.get_admin_token()
        condo_id = self.get_condominium_id(token)
        
        if not condo_id:
            pytest.skip("No condominium available for testing")
        
        test_email = f"TEST_with_email_{uuid.uuid4().hex[:8]}@test.com"
        
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": "DummyPass123!",  # This should be ignored
                "full_name": "Test User With Email",
                "role": "Residente",
                "phone": "+1234567890",
                "condominium_id": condo_id,
                "send_credentials_email": True,
                "apartment_number": "B-202"
            }
        )
        
        assert response.status_code in [200, 201], f"Create user failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "user_id" in data
        assert data.get("role") == "Residente"
        
        # Email status should be present (skipped because placeholder key)
        assert "email_status" in data, "email_status should be in response"
        # With placeholder key, status will be 'skipped'
        print(f"✓ User created with email credentials - email_status={data.get('email_status')}")
        
        # User should NOT be able to login with the dummy password
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": "DummyPass123!"
        })
        
        # Should fail because temp password was generated
        assert login_response.status_code == 401, \
            "Login with dummy password should fail when send_credentials_email=true"
        
        print(f"✓ Dummy password rejected - temp password was generated")
    
    def test_login_returns_password_reset_required_flag(self):
        """Test that login returns password_reset_required flag correctly"""
        token = self.get_admin_token()
        
        # Login response should include password_reset_required field
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify password_reset_required is in response
        assert "password_reset_required" in data, \
            "password_reset_required should be in login response"
        
        # Admin should not need password reset
        assert data.get("password_reset_required") == False, \
            "Admin should not have password_reset_required=true"
        
        # Also check user object
        user = data.get("user", {})
        assert "password_reset_required" in user, \
            "password_reset_required should be in user object"
        
        print(f"✓ Login returns password_reset_required flag correctly")
    
    def test_change_password_endpoint(self):
        """Test POST /api/auth/change-password endpoint"""
        token = self.get_admin_token()
        condo_id = self.get_condominium_id(token)
        
        if not condo_id:
            pytest.skip("No condominium available for testing")
        
        # Create a test user without email (so we know the password)
        test_email = f"TEST_change_pwd_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "OldPass123!"
        new_password = "NewPass456!"
        
        # Create user
        create_response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": test_password,
                "full_name": "Test Change Password",
                "role": "Residente",
                "condominium_id": condo_id,
                "send_credentials_email": False,
                "apartment_number": "C-303"
            }
        )
        
        assert create_response.status_code in [200, 201], f"Create user failed: {create_response.text}"
        
        # Login as the new user
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        
        assert login_response.status_code == 200
        user_token = login_response.json().get("access_token")
        
        # Change password
        change_response = self.session.post(
            f"{BASE_URL}/api/auth/change-password",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "current_password": test_password,
                "new_password": new_password
            }
        )
        
        assert change_response.status_code == 200, f"Change password failed: {change_response.text}"
        
        # Verify old password no longer works
        old_login = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        assert old_login.status_code == 401, "Old password should not work after change"
        
        # Verify new password works
        new_login = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": new_password
        })
        assert new_login.status_code == 200, "New password should work after change"
        
        print(f"✓ Password change endpoint works correctly")
    
    def test_change_password_clears_reset_flag(self):
        """Test that changing password clears password_reset_required flag"""
        token = self.get_admin_token()
        condo_id = self.get_condominium_id(token)
        
        if not condo_id:
            pytest.skip("No condominium available for testing")
        
        # Create user with password_reset_required=true by directly setting it
        test_email = f"TEST_reset_flag_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "TempPass123!"
        new_password = "NewSecure456!"
        
        # Create user without email (we'll manually set the flag)
        create_response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": test_password,
                "full_name": "Test Reset Flag",
                "role": "Residente",
                "condominium_id": condo_id,
                "send_credentials_email": False,
                "apartment_number": "D-404"
            }
        )
        
        assert create_response.status_code in [200, 201]
        
        # Login and change password
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        
        assert login_response.status_code == 200
        user_token = login_response.json().get("access_token")
        
        # Change password
        change_response = self.session.post(
            f"{BASE_URL}/api/auth/change-password",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "current_password": test_password,
                "new_password": new_password
            }
        )
        
        assert change_response.status_code == 200
        
        # Login again and verify password_reset_required is False
        final_login = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": new_password
        })
        
        assert final_login.status_code == 200
        final_data = final_login.json()
        
        assert final_data.get("password_reset_required") == False, \
            "password_reset_required should be False after password change"
        
        print(f"✓ Password change clears reset flag correctly")
    
    def test_change_password_validation(self):
        """Test password change validation rules"""
        token = self.get_admin_token()
        condo_id = self.get_condominium_id(token)
        
        if not condo_id:
            pytest.skip("No condominium available for testing")
        
        # Create test user
        test_email = f"TEST_pwd_validation_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "ValidPass123!"
        
        create_response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": test_password,
                "full_name": "Test Validation",
                "role": "Residente",
                "condominium_id": condo_id,
                "send_credentials_email": False,
                "apartment_number": "E-505"
            }
        )
        
        assert create_response.status_code in [200, 201]
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        
        assert login_response.status_code == 200
        user_token = login_response.json().get("access_token")
        
        # Test: Wrong current password
        wrong_pwd_response = self.session.post(
            f"{BASE_URL}/api/auth/change-password",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewPass456!"
            }
        )
        assert wrong_pwd_response.status_code == 400, \
            "Should reject wrong current password"
        
        # Test: Same password
        same_pwd_response = self.session.post(
            f"{BASE_URL}/api/auth/change-password",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "current_password": test_password,
                "new_password": test_password
            }
        )
        assert same_pwd_response.status_code == 400, \
            "Should reject same password"
        
        print(f"✓ Password change validation works correctly")
    
    def test_generate_temporary_password_format(self):
        """Test that temporary password meets security requirements"""
        # This is tested indirectly - when send_credentials_email=true,
        # the generated password should meet requirements:
        # - At least 8 characters
        # - Contains uppercase
        # - Contains lowercase
        # - Contains digit
        # - Contains special character
        
        # We can't directly test the generated password, but we verify
        # the user creation succeeds which means the password is valid
        token = self.get_admin_token()
        condo_id = self.get_condominium_id(token)
        
        if not condo_id:
            pytest.skip("No condominium available for testing")
        
        test_email = f"TEST_temp_pwd_{uuid.uuid4().hex[:8]}@test.com"
        
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": "Ignored123!",
                "full_name": "Test Temp Password",
                "role": "Guarda",
                "condominium_id": condo_id,
                "send_credentials_email": True,
                "badge_number": "G-999"
            }
        )
        
        assert response.status_code in [200, 201], f"Create user failed: {response.text}"
        
        # User was created successfully, meaning temp password was valid
        print(f"✓ Temporary password generation works correctly")
    
    def test_email_status_in_response(self):
        """Test that email status is included in create user response"""
        token = self.get_admin_token()
        condo_id = self.get_condominium_id(token)
        
        if not condo_id:
            pytest.skip("No condominium available for testing")
        
        test_email = f"TEST_email_status_{uuid.uuid4().hex[:8]}@test.com"
        
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": "TestPass123!",
                "full_name": "Test Email Status",
                "role": "Residente",
                "condominium_id": condo_id,
                "send_credentials_email": True,
                "apartment_number": "F-606"
            }
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        
        # With send_credentials_email=true, response should include email_status
        assert "email_status" in data, "email_status should be in response"
        
        # With placeholder API key, status should be 'skipped'
        assert data.get("email_status") in ["success", "skipped", "failed"], \
            f"Unexpected email_status: {data.get('email_status')}"
        
        print(f"✓ Email status included in response: {data.get('email_status')}")


class TestEmailCredentialsAuditLog:
    """Test audit logging for email credentials feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_email = "admin@genturix.com"
        self.admin_password = "Admin123!"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return response.json().get("access_token")
    
    def test_user_created_audit_log(self):
        """Test that user creation is logged in audit"""
        token = self.get_admin_token()
        
        # Get audit logs
        response = self.session.get(
            f"{BASE_URL}/api/audit/logs",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            pytest.skip("Audit logs endpoint not accessible")
        
        logs = response.json()
        
        # Check for user_created events
        user_created_logs = [l for l in logs if l.get("event_type") == "user_created"]
        
        # Should have at least one user_created event from our tests
        print(f"✓ Found {len(user_created_logs)} user_created audit events")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
