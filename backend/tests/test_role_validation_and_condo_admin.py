"""
GENTURIX - Role Validation and Condo Admin Creation Tests
Tests for:
1. Super Admin Create Condo Admin - POST /api/super-admin/condominiums/{id}/admin
2. Admin Create Users with Role-Specific Validation
3. Role-specific field requirements (apartment_number for Residente, badge_number for Guarda)
4. role_data storage in user document
5. Guard record creation when creating Guarda user
6. Audit logging for user creation
7. New user immediate login capability
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
SUPER_ADMIN_EMAIL = "superadmin@genturix.com"
SUPER_ADMIN_PASSWORD = "SuperAdmin123!"
DEMO_CONDO_ID = "267195e5-c18f-4374-a3a6-8016cfe70d86"


class TestRoleValidationAndCondoAdmin:
    """Test role-specific validation and condo admin creation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        self.super_admin_token = None
        self.created_users = []  # Track for cleanup
    
    def get_admin_token(self):
        """Get admin authentication token"""
        if self.admin_token:
            return self.admin_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            self.admin_token = response.json().get("access_token")
            return self.admin_token
        pytest.skip(f"Admin login failed: {response.status_code}")
    
    def get_super_admin_token(self):
        """Get super admin authentication token"""
        if self.super_admin_token:
            return self.super_admin_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            self.super_admin_token = response.json().get("access_token")
            return self.super_admin_token
        pytest.skip(f"Super admin login failed: {response.status_code}")
    
    # ==================== RESIDENTE VALIDATION TESTS ====================
    
    def test_create_residente_requires_apartment_number(self):
        """Residente creation without apartment_number should fail"""
        token = self.get_admin_token()
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": f"TEST_residente_no_apt_{uuid.uuid4().hex[:8]}@test.com",
                "password": "TestPass123!",
                "full_name": "Test Residente Sin Apartamento",
                "role": "Residente",
                "phone": "+1234567890"
                # Missing apartment_number
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "apartamento" in data.get("detail", "").lower() or "apartment" in data.get("detail", "").lower()
        print(f"PASS: Residente without apartment_number correctly rejected: {data.get('detail')}")
    
    def test_create_residente_with_apartment_number_succeeds(self):
        """Residente creation with apartment_number should succeed"""
        token = self.get_admin_token()
        test_email = f"TEST_residente_valid_{uuid.uuid4().hex[:8]}@test.com"
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": "TestPass123!",
                "full_name": "Test Residente Con Apartamento",
                "role": "Residente",
                "phone": "+1234567890",
                "apartment_number": "A-101",
                "tower_block": "Torre A",
                "resident_type": "owner"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("role") == "Residente"
        assert "role_data" in data
        assert data["role_data"].get("apartment_number") == "A-101"
        self.created_users.append(test_email)
        print(f"PASS: Residente with apartment_number created successfully")
        print(f"  role_data: {data.get('role_data')}")
    
    # ==================== GUARDA VALIDATION TESTS ====================
    
    def test_create_guarda_requires_badge_number(self):
        """Guarda creation without badge_number should fail"""
        token = self.get_admin_token()
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": f"TEST_guarda_no_badge_{uuid.uuid4().hex[:8]}@test.com",
                "password": "TestPass123!",
                "full_name": "Test Guarda Sin Placa",
                "role": "Guarda",
                "phone": "+1234567890"
                # Missing badge_number
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "placa" in data.get("detail", "").lower() or "badge" in data.get("detail", "").lower()
        print(f"PASS: Guarda without badge_number correctly rejected: {data.get('detail')}")
    
    def test_create_guarda_with_badge_number_succeeds(self):
        """Guarda creation with badge_number should succeed and create guard record"""
        token = self.get_admin_token()
        test_email = f"TEST_guarda_valid_{uuid.uuid4().hex[:8]}@test.com"
        test_badge = f"G-TEST-{uuid.uuid4().hex[:4]}"
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": "TestPass123!",
                "full_name": "Test Guarda Con Placa",
                "role": "Guarda",
                "phone": "+1234567890",
                "badge_number": test_badge,
                "main_location": "Entrada Principal",
                "initial_shift": "morning"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("role") == "Guarda"
        assert "role_data" in data
        assert data["role_data"].get("badge_number") == test_badge
        assert "guard_id" in data["role_data"], "Guard record should be created"
        self.created_users.append(test_email)
        print(f"PASS: Guarda with badge_number created successfully")
        print(f"  role_data: {data.get('role_data')}")
        print(f"  guard_id: {data['role_data'].get('guard_id')}")
    
    # ==================== HR CREATION TESTS ====================
    
    def test_create_hr_optional_fields(self):
        """HR creation with optional department and permission_level"""
        token = self.get_admin_token()
        test_email = f"TEST_hr_valid_{uuid.uuid4().hex[:8]}@test.com"
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": "TestPass123!",
                "full_name": "Test HR User",
                "role": "HR",
                "phone": "+1234567890",
                "department": "Recursos Humanos",
                "permission_level": "HR_SUPERVISOR"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("role") == "HR"
        assert "role_data" in data
        assert data["role_data"].get("department") == "Recursos Humanos"
        assert data["role_data"].get("permission_level") == "HR_SUPERVISOR"
        self.created_users.append(test_email)
        print(f"PASS: HR user created with optional fields")
        print(f"  role_data: {data.get('role_data')}")
    
    def test_create_hr_without_optional_fields(self):
        """HR creation without optional fields should use defaults"""
        token = self.get_admin_token()
        test_email = f"TEST_hr_defaults_{uuid.uuid4().hex[:8]}@test.com"
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": "TestPass123!",
                "full_name": "Test HR Default",
                "role": "HR",
                "phone": "+1234567890"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("role") == "HR"
        assert "role_data" in data
        # Should have default values
        assert data["role_data"].get("department") == "Recursos Humanos"
        assert data["role_data"].get("permission_level") == "HR"
        self.created_users.append(test_email)
        print(f"PASS: HR user created with default values")
    
    # ==================== ESTUDIANTE CREATION TESTS ====================
    
    def test_create_estudiante_optional_fields(self):
        """Estudiante creation with optional subscription fields"""
        token = self.get_admin_token()
        test_email = f"TEST_estudiante_{uuid.uuid4().hex[:8]}@test.com"
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": "TestPass123!",
                "full_name": "Test Estudiante",
                "role": "Estudiante",
                "phone": "+1234567890",
                "subscription_plan": "pro",
                "subscription_status": "active"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("role") == "Estudiante"
        assert "role_data" in data
        assert data["role_data"].get("subscription_plan") == "pro"
        assert data["role_data"].get("subscription_status") == "active"
        self.created_users.append(test_email)
        print(f"PASS: Estudiante created with subscription fields")
        print(f"  role_data: {data.get('role_data')}")
    
    # ==================== SUPERVISOR CREATION TESTS ====================
    
    def test_create_supervisor_optional_fields(self):
        """Supervisor creation with optional supervised_area"""
        token = self.get_admin_token()
        test_email = f"TEST_supervisor_{uuid.uuid4().hex[:8]}@test.com"
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": "TestPass123!",
                "full_name": "Test Supervisor",
                "role": "Supervisor",
                "phone": "+1234567890",
                "supervised_area": "Seguridad Perimetral"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("role") == "Supervisor"
        assert "role_data" in data
        assert data["role_data"].get("supervised_area") == "Seguridad Perimetral"
        self.created_users.append(test_email)
        print(f"PASS: Supervisor created with supervised_area")
        print(f"  role_data: {data.get('role_data')}")
    
    # ==================== ADMIN CANNOT CREATE ADMIN/SUPERADMIN ====================
    
    def test_admin_cannot_create_admin(self):
        """Admin should not be able to create Administrador role"""
        token = self.get_admin_token()
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": f"TEST_admin_blocked_{uuid.uuid4().hex[:8]}@test.com",
                "password": "TestPass123!",
                "full_name": "Test Admin Blocked",
                "role": "Administrador",
                "phone": "+1234567890"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"PASS: Admin cannot create Administrador role")
    
    def test_admin_cannot_create_superadmin(self):
        """Admin should not be able to create SuperAdmin role"""
        token = self.get_admin_token()
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": f"TEST_superadmin_blocked_{uuid.uuid4().hex[:8]}@test.com",
                "password": "TestPass123!",
                "full_name": "Test SuperAdmin Blocked",
                "role": "SuperAdmin",
                "phone": "+1234567890"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"PASS: Admin cannot create SuperAdmin role")
    
    # ==================== SUPER ADMIN CREATE CONDO ADMIN ====================
    
    def test_super_admin_create_condo_admin(self):
        """Super Admin can create Condo Admin for a condominium"""
        token = self.get_super_admin_token()
        test_email = f"TEST_condo_admin_{uuid.uuid4().hex[:8]}@test.com"
        response = self.session.post(
            f"{BASE_URL}/api/super-admin/condominiums/{DEMO_CONDO_ID}/admin",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": "TestAdmin123!",
                "full_name": "Test Condo Admin",
                "phone": "+1234567890"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "user_id" in data
        assert data.get("condominium_id") == DEMO_CONDO_ID
        assert "credentials" in data
        self.created_users.append(test_email)
        print(f"PASS: Super Admin created Condo Admin successfully")
        print(f"  user_id: {data.get('user_id')}")
        print(f"  condominium_id: {data.get('condominium_id')}")
        return test_email, "TestAdmin123!"
    
    def test_super_admin_create_condo_admin_invalid_condo(self):
        """Super Admin cannot create admin for non-existent condominium"""
        token = self.get_super_admin_token()
        fake_condo_id = str(uuid.uuid4())
        response = self.session.post(
            f"{BASE_URL}/api/super-admin/condominiums/{fake_condo_id}/admin",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": f"TEST_invalid_condo_{uuid.uuid4().hex[:8]}@test.com",
                "password": "TestAdmin123!",
                "full_name": "Test Invalid Condo Admin",
                "phone": "+1234567890"
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"PASS: Super Admin cannot create admin for non-existent condo")
    
    # ==================== NEW USER IMMEDIATE LOGIN ====================
    
    def test_new_user_can_login_immediately(self):
        """Newly created user should be able to login immediately"""
        # First create a user
        token = self.get_admin_token()
        test_email = f"TEST_login_test_{uuid.uuid4().hex[:8]}@test.com"
        test_password = "TestLogin123!"
        
        create_response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": test_password,
                "full_name": "Test Login User",
                "role": "Residente",
                "phone": "+1234567890",
                "apartment_number": "B-202"
            }
        )
        assert create_response.status_code == 200, f"User creation failed: {create_response.text}"
        self.created_users.append(test_email)
        
        # Now try to login with the new user
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": test_email,
                "password": test_password
            }
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.status_code}"
        login_data = login_response.json()
        assert "access_token" in login_data
        print(f"PASS: New user can login immediately after creation")
        print(f"  email: {test_email}")
    
    # ==================== AUDIT LOGGING ====================
    
    def test_user_creation_logged_in_audit(self):
        """User creation should be logged in audit with role_data"""
        token = self.get_admin_token()
        test_email = f"TEST_audit_log_{uuid.uuid4().hex[:8]}@test.com"
        
        # Create user
        create_response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": "TestAudit123!",
                "full_name": "Test Audit User",
                "role": "Guarda",
                "phone": "+1234567890",
                "badge_number": f"G-AUDIT-{uuid.uuid4().hex[:4]}"
            }
        )
        assert create_response.status_code == 200
        self.created_users.append(test_email)
        
        # Check audit logs
        audit_response = self.session.get(
            f"{BASE_URL}/api/audit/logs",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert audit_response.status_code == 200
        audit_logs = audit_response.json()
        
        # Find the user_created event for our test user
        user_created_log = None
        for log in audit_logs:
            if log.get("event_type") == "user_created" and test_email in str(log.get("details", {})):
                user_created_log = log
                break
        
        assert user_created_log is not None, "User creation should be logged in audit"
        assert "role_data" in str(user_created_log.get("details", {})), "Audit should include role_data"
        print(f"PASS: User creation logged in audit with role_data")
        print(f"  event_type: {user_created_log.get('event_type')}")
    
    # ==================== ROLE_DATA STORED IN USER DOCUMENT ====================
    
    def test_role_data_stored_in_user_document(self):
        """role_data should be stored in user document"""
        token = self.get_admin_token()
        test_email = f"TEST_role_data_{uuid.uuid4().hex[:8]}@test.com"
        
        # Create user with role_data
        create_response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": "TestRoleData123!",
                "full_name": "Test Role Data User",
                "role": "Residente",
                "phone": "+1234567890",
                "apartment_number": "C-303",
                "tower_block": "Torre C",
                "resident_type": "tenant"
            }
        )
        assert create_response.status_code == 200
        create_data = create_response.json()
        self.created_users.append(test_email)
        
        # Verify role_data in response
        assert "role_data" in create_data
        assert create_data["role_data"].get("apartment_number") == "C-303"
        assert create_data["role_data"].get("tower_block") == "Torre C"
        assert create_data["role_data"].get("resident_type") == "tenant"
        
        # Login as the new user and check /me endpoint
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": test_email, "password": "TestRoleData123!"}
        )
        assert login_response.status_code == 200
        user_token = login_response.json().get("access_token")
        
        me_response = self.session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        
        # Check role_data is in user document
        assert "role_data" in me_data, "role_data should be in user document"
        assert me_data["role_data"].get("apartment_number") == "C-303"
        print(f"PASS: role_data stored and retrievable from user document")
        print(f"  role_data: {me_data.get('role_data')}")


class TestDynamicFormUI:
    """Test dynamic form fields based on role selection"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_available_roles_list(self):
        """Verify available roles for admin user creation"""
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        
        # The available roles should be: Residente, Guarda, HR, Supervisor, Estudiante
        # Admin and SuperAdmin should NOT be available
        valid_roles = ["Residente", "Guarda", "HR", "Supervisor", "Estudiante"]
        invalid_roles = ["Administrador", "SuperAdmin"]
        
        token = response.json().get("access_token")
        
        # Test each valid role
        for role in valid_roles:
            test_data = {
                "email": f"TEST_role_check_{role}_{uuid.uuid4().hex[:8]}@test.com",
                "password": "TestPass123!",
                "full_name": f"Test {role}",
                "role": role,
                "phone": "+1234567890"
            }
            
            # Add required fields for specific roles
            if role == "Residente":
                test_data["apartment_number"] = "TEST-APT"
            elif role == "Guarda":
                test_data["badge_number"] = f"TEST-{uuid.uuid4().hex[:4]}"
            
            check_response = self.session.post(
                f"{BASE_URL}/api/admin/users",
                headers={"Authorization": f"Bearer {token}"},
                json=test_data
            )
            # Should succeed (200) or fail for other reasons, but not 400 for invalid role
            assert check_response.status_code == 200, f"Role {role} should be valid: {check_response.text}"
            print(f"PASS: Role {role} is valid and can be created")
        
        # Test invalid roles
        for role in invalid_roles:
            check_response = self.session.post(
                f"{BASE_URL}/api/admin/users",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "email": f"TEST_invalid_role_{uuid.uuid4().hex[:8]}@test.com",
                    "password": "TestPass123!",
                    "full_name": f"Test Invalid {role}",
                    "role": role,
                    "phone": "+1234567890"
                }
            )
            assert check_response.status_code == 400, f"Role {role} should be invalid"
            print(f"PASS: Role {role} is correctly blocked")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
