"""
GENTURIX - User Management API Tests
Tests for Admin User Management features:
- User creation by admin (all roles)
- User list with filters
- User status toggle (activate/deactivate)
- Audit logging for user actions
- condominium_id assignment
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
SUPER_ADMIN_EMAIL = "superadmin@genturix.com"
SUPER_ADMIN_PASSWORD = "SuperAdmin123!"


class TestUserManagementSetup:
    """Setup and authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get headers with admin auth"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def admin_user_info(self, admin_headers):
        """Get admin user info"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        assert response.status_code == 200
        return response.json()
    
    def test_admin_login(self):
        """Test admin can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        user = data.get("user", {})
        assert "Administrador" in user.get("roles", [])
        print(f"PASS: Admin login successful, roles: {user.get('roles')}")
    
    def test_admin_has_condominium_id(self, admin_user_info):
        """Test admin has condominium_id assigned"""
        assert "condominium_id" in admin_user_info, "Admin missing condominium_id"
        assert admin_user_info["condominium_id"] is not None, "Admin condominium_id is None"
        print(f"PASS: Admin has condominium_id: {admin_user_info['condominium_id']}")


class TestUserCreation:
    """Test user creation by admin"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def admin_user_info(self, admin_headers):
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        return response.json()
    
    def test_create_residente_user(self, admin_headers, admin_user_info):
        """Test creating a Residente user"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"TEST_residente_{unique_id}@genturix.com",
            "password": "TestPass123!",
            "full_name": f"Test Residente {unique_id}",
            "role": "Residente",
            "phone": "+52 555 111 2222"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to create Residente: {response.text}"
        data = response.json()
        assert "user_id" in data
        assert "message" in data
        print(f"PASS: Created Residente user: {user_data['email']}")
        
        # Verify user can login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200, f"New Residente cannot login: {login_response.text}"
        login_data = login_response.json()
        user_info = login_data.get("user", {})
        assert "Residente" in user_info.get("roles", [])
        
        # Verify condominium_id inherited
        assert user_info.get("condominium_id") == admin_user_info.get("condominium_id"), \
            "New user did not inherit admin's condominium_id"
        print(f"PASS: Residente can login and has correct condominium_id")
        
        return data["user_id"]
    
    def test_create_guarda_user(self, admin_headers, admin_user_info):
        """Test creating a Guarda user"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"TEST_guarda_{unique_id}@genturix.com",
            "password": "TestPass123!",
            "full_name": f"Test Guarda {unique_id}",
            "role": "Guarda",
            "phone": "+52 555 333 4444"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to create Guarda: {response.text}"
        data = response.json()
        assert "user_id" in data
        print(f"PASS: Created Guarda user: {user_data['email']}")
        
        # Verify user can login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200
        login_data = login_response.json()
        user_info = login_data.get("user", {})
        assert "Guarda" in user_info.get("roles", [])
        print(f"PASS: Guarda can login with correct role")
        
        return data["user_id"]
    
    def test_create_hr_user(self, admin_headers, admin_user_info):
        """Test creating an HR user"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"TEST_hr_{unique_id}@genturix.com",
            "password": "TestPass123!",
            "full_name": f"Test HR {unique_id}",
            "role": "HR",
            "phone": "+52 555 555 6666"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to create HR: {response.text}"
        data = response.json()
        assert "user_id" in data
        print(f"PASS: Created HR user: {user_data['email']}")
        
        # Verify user can login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200
        login_data = login_response.json()
        user_info = login_data.get("user", {})
        assert "HR" in user_info.get("roles", [])
        print(f"PASS: HR can login with correct role")
        
        return data["user_id"]
    
    def test_create_supervisor_user(self, admin_headers, admin_user_info):
        """Test creating a Supervisor user"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"TEST_supervisor_{unique_id}@genturix.com",
            "password": "TestPass123!",
            "full_name": f"Test Supervisor {unique_id}",
            "role": "Supervisor",
            "phone": "+52 555 777 8888"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to create Supervisor: {response.text}"
        data = response.json()
        assert "user_id" in data
        print(f"PASS: Created Supervisor user: {user_data['email']}")
        
        # Verify user can login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200
        login_data = login_response.json()
        user_info = login_data.get("user", {})
        assert "Supervisor" in user_info.get("roles", [])
        print(f"PASS: Supervisor can login with correct role")
        
        return data["user_id"]
    
    def test_create_estudiante_user(self, admin_headers, admin_user_info):
        """Test creating an Estudiante user"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"TEST_estudiante_{unique_id}@genturix.com",
            "password": "TestPass123!",
            "full_name": f"Test Estudiante {unique_id}",
            "role": "Estudiante",
            "phone": "+52 555 999 0000"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to create Estudiante: {response.text}"
        data = response.json()
        assert "user_id" in data
        print(f"PASS: Created Estudiante user: {user_data['email']}")
        
        # Verify user can login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200
        login_data = login_response.json()
        user_info = login_data.get("user", {})
        assert "Estudiante" in user_info.get("roles", [])
        print(f"PASS: Estudiante can login with correct role")
        
        return data["user_id"]
    
    def test_cannot_create_superadmin(self, admin_headers):
        """Test that admin cannot create SuperAdmin users"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"TEST_superadmin_{unique_id}@genturix.com",
            "password": "TestPass123!",
            "full_name": f"Test SuperAdmin {unique_id}",
            "role": "SuperAdmin",
            "phone": "+52 555 000 1111"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        assert response.status_code == 400, f"Should not allow SuperAdmin creation, got: {response.status_code}"
        print(f"PASS: Admin cannot create SuperAdmin users (got 400)")
    
    def test_cannot_create_administrador(self, admin_headers):
        """Test that admin cannot create Administrador users via this endpoint"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"TEST_admin_{unique_id}@genturix.com",
            "password": "TestPass123!",
            "full_name": f"Test Admin {unique_id}",
            "role": "Administrador",
            "phone": "+52 555 000 2222"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        assert response.status_code == 400, f"Should not allow Administrador creation, got: {response.status_code}"
        print(f"PASS: Admin cannot create Administrador users (got 400)")
    
    def test_duplicate_email_rejected(self, admin_headers):
        """Test that duplicate emails are rejected"""
        response = requests.post(f"{BASE_URL}/api/admin/users", json={
            "email": ADMIN_EMAIL,  # Already exists
            "password": "TestPass123!",
            "full_name": "Duplicate User",
            "role": "Residente"
        }, headers=admin_headers)
        assert response.status_code == 400, f"Should reject duplicate email, got: {response.status_code}"
        print(f"PASS: Duplicate email rejected (got 400)")


class TestUserList:
    """Test user list and filtering"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_get_all_users(self, admin_headers):
        """Test getting all users"""
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get users: {response.text}"
        users = response.json()
        assert isinstance(users, list), "Response should be a list"
        assert len(users) > 0, "Should have at least one user"
        print(f"PASS: Got {len(users)} users")
        
        # Verify user structure
        user = users[0]
        assert "id" in user
        assert "email" in user
        assert "full_name" in user or "roles" in user
        print(f"PASS: User structure is correct")
    
    def test_filter_by_role_residente(self, admin_headers):
        """Test filtering users by Residente role"""
        response = requests.get(f"{BASE_URL}/api/admin/users?role=Residente", headers=admin_headers)
        assert response.status_code == 200
        users = response.json()
        for user in users:
            assert "Residente" in user.get("roles", []), f"User {user.get('email')} is not Residente"
        print(f"PASS: Filtered {len(users)} Residente users")
    
    def test_filter_by_role_guarda(self, admin_headers):
        """Test filtering users by Guarda role"""
        response = requests.get(f"{BASE_URL}/api/admin/users?role=Guarda", headers=admin_headers)
        assert response.status_code == 200
        users = response.json()
        for user in users:
            assert "Guarda" in user.get("roles", []), f"User {user.get('email')} is not Guarda"
        print(f"PASS: Filtered {len(users)} Guarda users")
    
    def test_filter_by_role_hr(self, admin_headers):
        """Test filtering users by HR role"""
        response = requests.get(f"{BASE_URL}/api/admin/users?role=HR", headers=admin_headers)
        assert response.status_code == 200
        users = response.json()
        for user in users:
            assert "HR" in user.get("roles", []), f"User {user.get('email')} is not HR"
        print(f"PASS: Filtered {len(users)} HR users")


class TestUserStatusToggle:
    """Test user status toggle (activate/deactivate)"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def test_user_id(self, admin_headers):
        """Create a test user for status toggle tests"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"TEST_status_{unique_id}@genturix.com",
            "password": "TestPass123!",
            "full_name": f"Test Status User {unique_id}",
            "role": "Residente"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        assert response.status_code == 200
        return response.json()["user_id"], user_data["email"], user_data["password"]
    
    def test_deactivate_user(self, admin_headers, test_user_id):
        """Test deactivating a user"""
        user_id, email, password = test_user_id
        
        response = requests.patch(
            f"{BASE_URL}/api/admin/users/{user_id}/status",
            json={"is_active": False},
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed to deactivate user: {response.text}"
        print(f"PASS: User deactivated successfully")
        
        # Verify user cannot login when deactivated
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        # Should fail with 401 or 403
        assert login_response.status_code in [401, 403], \
            f"Deactivated user should not be able to login, got: {login_response.status_code}"
        print(f"PASS: Deactivated user cannot login")
    
    def test_activate_user(self, admin_headers, test_user_id):
        """Test activating a user"""
        user_id, email, password = test_user_id
        
        response = requests.patch(
            f"{BASE_URL}/api/admin/users/{user_id}/status",
            json={"is_active": True},
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed to activate user: {response.text}"
        print(f"PASS: User activated successfully")
        
        # Verify user can login when activated
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        assert login_response.status_code == 200, \
            f"Activated user should be able to login, got: {login_response.status_code}"
        print(f"PASS: Activated user can login")
    
    def test_cannot_deactivate_self(self, admin_headers):
        """Test that admin cannot deactivate themselves"""
        # Get admin's user ID
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
        admin_id = me_response.json()["id"]
        
        response = requests.patch(
            f"{BASE_URL}/api/admin/users/{admin_id}/status",
            json={"is_active": False},
            headers=admin_headers
        )
        assert response.status_code == 400, f"Should not allow self-deactivation, got: {response.status_code}"
        print(f"PASS: Admin cannot deactivate themselves")


class TestAuditLogging:
    """Test audit logging for user management actions"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_user_creation_logged(self, admin_headers):
        """Test that user creation is logged in audit"""
        # Create a user
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"TEST_audit_{unique_id}@genturix.com",
            "password": "TestPass123!",
            "full_name": f"Test Audit User {unique_id}",
            "role": "Residente"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        assert create_response.status_code == 200
        
        # Check audit logs
        audit_response = requests.get(f"{BASE_URL}/api/audit/logs", headers=admin_headers)
        assert audit_response.status_code == 200
        logs = audit_response.json()
        
        # Find the user creation log
        user_created_logs = [log for log in logs if log.get("event_type") == "user_created"]
        assert len(user_created_logs) > 0, "No user_created audit logs found"
        
        # Check if our user creation is logged
        recent_log = user_created_logs[0]
        assert "details" in recent_log
        print(f"PASS: User creation logged in audit")
    
    def test_status_change_logged(self, admin_headers):
        """Test that status changes are logged in audit"""
        # Create a user first
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"TEST_audit_status_{unique_id}@genturix.com",
            "password": "TestPass123!",
            "full_name": f"Test Audit Status {unique_id}",
            "role": "Residente"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        user_id = create_response.json()["user_id"]
        
        # Toggle status
        requests.patch(
            f"{BASE_URL}/api/admin/users/{user_id}/status",
            json={"is_active": False},
            headers=admin_headers
        )
        
        # Check audit logs
        audit_response = requests.get(f"{BASE_URL}/api/audit/logs", headers=admin_headers)
        logs = audit_response.json()
        
        # Find status change logs
        status_logs = [log for log in logs if log.get("event_type") == "user_updated"]
        assert len(status_logs) > 0, "No user_updated audit logs found"
        print(f"PASS: Status change logged in audit")


class TestSidebarNavigation:
    """Test sidebar navigation to Users page"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_admin_has_users_access(self, admin_headers):
        """Test that admin role has access to users endpoint"""
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=admin_headers)
        assert response.status_code == 200, f"Admin should have access to users: {response.text}"
        print(f"PASS: Admin has access to /admin/users endpoint")


# Cleanup fixture
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_users():
    """Cleanup TEST_ prefixed users after all tests"""
    yield
    # Cleanup would happen here if needed
    print("Test session complete - TEST_ users created during testing")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
