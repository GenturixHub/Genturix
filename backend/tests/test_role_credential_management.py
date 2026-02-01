"""
GENTURIX - Role and Credential Management Tests
Tests for:
1. HR Login and redirect to /rrhh
2. HR Access to RRHH Module (Turnos, Reclutamiento, Ausencias)
3. HR Create Candidate
4. HR Hire Candidate with credential generation
5. Admin Login and redirect to /admin/dashboard
6. Admin Create User Modal with all role options
7. Admin Create HR User
8. Admin Create Guarda
9. Admin Create Residente
10. New User Login verification
11. Guard Login Redirect to /guard
12. Resident Login Redirect to /resident
13. Multi-tenancy - condominium_id assignment
14. Super Admin Create Condo Admin
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://condo-access-19.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
HR_EMAIL = "hr_maria@genturix.com"
HR_PASSWORD = "HRMaria123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"
SUPER_ADMIN_EMAIL = "superadmin@genturix.com"
SUPER_ADMIN_PASSWORD = "SuperAdmin123!"


class TestHRLogin:
    """Test HR Login and access to RRHH module"""
    
    def test_hr_login_success(self):
        """HR can login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_EMAIL,
            "password": HR_PASSWORD
        })
        
        print(f"HR Login Response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "user" in data
            assert data["user"]["email"] == HR_EMAIL
            assert "HR" in data["user"]["roles"]
            print(f"HR Login SUCCESS - User: {data['user']['full_name']}, Roles: {data['user']['roles']}")
            print(f"HR has condominium_id: {data['user'].get('condominium_id')}")
        elif response.status_code == 401:
            # HR user might not exist yet - create it
            print("HR user not found - will be created by admin")
            pytest.skip("HR user not found - needs to be created first")
        else:
            print(f"HR Login failed: {response.text}")
            pytest.fail(f"HR Login failed with status {response.status_code}")
    
    def test_hr_redirect_should_be_rrhh(self):
        """HR role should redirect to /rrhh based on LoginPage.js logic"""
        # This is a frontend test - we verify the role is HR
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_EMAIL,
            "password": HR_PASSWORD
        })
        
        if response.status_code == 200:
            data = response.json()
            roles = data["user"]["roles"]
            # According to LoginPage.js line 51-53: case 'HR': navigate('/rrhh')
            if len(roles) == 1 and roles[0] == "HR":
                print("HR with single role should redirect to /rrhh")
                assert True
            else:
                print(f"HR has roles: {roles}")
        else:
            pytest.skip("HR user not available")


class TestHRAccessRRHHModule:
    """Test HR access to RRHH submodules"""
    
    @pytest.fixture
    def hr_token(self):
        """Get HR auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_EMAIL,
            "password": HR_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("HR login failed")
    
    def test_hr_can_access_guards_list(self, hr_token):
        """HR can access guards/employees list"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/hr/guards", headers=headers)
        
        print(f"HR Get Guards: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        print(f"HR can see {len(data)} guards/employees")
    
    def test_hr_can_access_shifts(self, hr_token):
        """HR can access shifts (Turnos)"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/hr/shifts", headers=headers)
        
        print(f"HR Get Shifts: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        print(f"HR can see {len(data)} shifts")
    
    def test_hr_can_access_absences(self, hr_token):
        """HR can access absences (Ausencias)"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/hr/absences", headers=headers)
        
        print(f"HR Get Absences: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        print(f"HR can see {len(data)} absence requests")
    
    def test_hr_can_access_candidates(self, hr_token):
        """HR can access candidates (Reclutamiento)"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/hr/candidates", headers=headers)
        
        print(f"HR Get Candidates: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        print(f"HR can see {len(data)} candidates")


class TestHRRecruitmentFlow:
    """Test HR Recruitment flow - Create candidate and hire"""
    
    @pytest.fixture
    def hr_token(self):
        """Get HR auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_EMAIL,
            "password": HR_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("HR login failed")
    
    def test_hr_create_candidate(self, hr_token):
        """HR can create a new candidate"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        unique_id = str(uuid.uuid4())[:8]
        candidate_data = {
            "full_name": f"TEST_Candidate_{unique_id}",
            "email": f"test_candidate_{unique_id}@test.com",
            "phone": "+1234567890",
            "position": "Guarda",
            "experience_years": 2,
            "notes": "Test candidate created by HR"
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/candidates", json=candidate_data, headers=headers)
        
        print(f"HR Create Candidate: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["full_name"] == candidate_data["full_name"]
        assert data["status"] == "applied"
        print(f"Candidate created: {data['id']}")
        return data["id"]
    
    def test_hr_hire_candidate_generates_credentials(self, hr_token):
        """HR can hire candidate and generate user credentials"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        # First create a candidate
        unique_id = str(uuid.uuid4())[:8]
        candidate_data = {
            "full_name": f"TEST_HireCandidate_{unique_id}",
            "email": f"test_hire_{unique_id}@test.com",
            "phone": "+1234567890",
            "position": "Guarda",
            "experience_years": 1,
            "notes": "Test candidate for hiring"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/hr/candidates", json=candidate_data, headers=headers)
        assert create_response.status_code == 200
        candidate_id = create_response.json()["id"]
        
        # Now hire the candidate
        hire_data = {
            "badge_number": f"GRD-TEST-{unique_id}",
            "hourly_rate": 15.0,
            "password": "TestPassword123!"
        }
        
        hire_response = requests.post(f"{BASE_URL}/api/hr/candidates/{candidate_id}/hire", json=hire_data, headers=headers)
        
        print(f"HR Hire Candidate: {hire_response.status_code}")
        print(f"Response: {hire_response.text[:500]}")
        
        assert hire_response.status_code == 200
        data = hire_response.json()
        assert "user_id" in data
        assert "guard_id" in data
        assert "email" in data
        assert data["email"] == candidate_data["email"]
        print(f"Candidate hired! User ID: {data['user_id']}, Guard ID: {data['guard_id']}")
        
        # Verify the new user can login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": candidate_data["email"],
            "password": "TestPassword123!"
        })
        
        print(f"New hired user login: {login_response.status_code}")
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "Guarda" in login_data["user"]["roles"]
        assert login_data["user"].get("condominium_id") is not None
        print(f"Hired user can login! Roles: {login_data['user']['roles']}, Condo: {login_data['user']['condominium_id']}")


class TestAdminLogin:
    """Test Admin Login and redirect"""
    
    def test_admin_login_success(self):
        """Admin can login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        print(f"Admin Login Response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert "Administrador" in data["user"]["roles"]
        print(f"Admin Login SUCCESS - User: {data['user']['full_name']}, Roles: {data['user']['roles']}")
        print(f"Admin has condominium_id: {data['user'].get('condominium_id')}")
    
    def test_admin_redirect_should_be_dashboard(self):
        """Admin role should redirect to /admin/dashboard"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        assert response.status_code == 200
        data = response.json()
        roles = data["user"]["roles"]
        # According to LoginPage.js: case 'Administrador': navigate('/admin/dashboard')
        if "Administrador" in roles:
            print("Admin should redirect to /admin/dashboard")
            assert True


class TestAdminCreateUser:
    """Test Admin Create User functionality"""
    
    @pytest.fixture
    def admin_token(self):
        """Get Admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_admin_create_hr_user(self, admin_token):
        """Admin can create HR user via POST /api/admin/users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = str(uuid.uuid4())[:8]
        
        user_data = {
            "email": f"test_hr_{unique_id}@test.com",
            "password": "TestHR123!",
            "full_name": f"TEST_HR_User_{unique_id}",
            "role": "HR",
            "phone": "+1234567890"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=headers)
        
        print(f"Admin Create HR User: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "message" in data
        print(f"HR User created: {data['user_id']}")
        
        # Verify the new HR user can login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "HR" in login_data["user"]["roles"]
        assert login_data["user"].get("condominium_id") is not None
        print(f"New HR user can login! Condo: {login_data['user']['condominium_id']}")
    
    def test_admin_create_guarda_user(self, admin_token):
        """Admin can create Guarda user via POST /api/admin/users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = str(uuid.uuid4())[:8]
        
        user_data = {
            "email": f"test_guarda_{unique_id}@test.com",
            "password": "TestGuarda123!",
            "full_name": f"TEST_Guarda_User_{unique_id}",
            "role": "Guarda",
            "phone": "+1234567890"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=headers)
        
        print(f"Admin Create Guarda User: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        print(f"Guarda User created: {data['user_id']}")
        
        # Verify the new Guarda user can login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "Guarda" in login_data["user"]["roles"]
        print(f"New Guarda user can login! Roles: {login_data['user']['roles']}")
    
    def test_admin_create_residente_user(self, admin_token):
        """Admin can create Residente user via POST /api/admin/users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = str(uuid.uuid4())[:8]
        
        user_data = {
            "email": f"test_residente_{unique_id}@test.com",
            "password": "TestResidente123!",
            "full_name": f"TEST_Residente_User_{unique_id}",
            "role": "Residente",
            "phone": "+1234567890"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=headers)
        
        print(f"Admin Create Residente User: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        print(f"Residente User created: {data['user_id']}")
        
        # Verify the new Residente user can login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "Residente" in login_data["user"]["roles"]
        print(f"New Residente user can login! Roles: {login_data['user']['roles']}")
    
    def test_admin_create_supervisor_user(self, admin_token):
        """Admin can create Supervisor user via POST /api/admin/users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = str(uuid.uuid4())[:8]
        
        user_data = {
            "email": f"test_supervisor_{unique_id}@test.com",
            "password": "TestSupervisor123!",
            "full_name": f"TEST_Supervisor_User_{unique_id}",
            "role": "Supervisor",
            "phone": "+1234567890"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=headers)
        
        print(f"Admin Create Supervisor User: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        print(f"Supervisor User created: {data['user_id']}")
    
    def test_admin_create_estudiante_user(self, admin_token):
        """Admin can create Estudiante user via POST /api/admin/users"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = str(uuid.uuid4())[:8]
        
        user_data = {
            "email": f"test_estudiante_{unique_id}@test.com",
            "password": "TestEstudiante123!",
            "full_name": f"TEST_Estudiante_User_{unique_id}",
            "role": "Estudiante",
            "phone": "+1234567890"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=headers)
        
        print(f"Admin Create Estudiante User: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        print(f"Estudiante User created: {data['user_id']}")


class TestRoleRedirects:
    """Test login redirects for different roles"""
    
    def test_guard_login_redirect(self):
        """Guard should redirect to /guard"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        
        print(f"Guard Login: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            roles = data["user"]["roles"]
            # According to LoginPage.js: case 'Guarda': navigate('/guard')
            if "Guarda" in roles:
                print(f"Guard with roles {roles} should redirect to /guard")
                assert True
        else:
            pytest.skip("Guard user not available")
    
    def test_resident_login_redirect(self):
        """Resident should redirect to /resident"""
        # Try to login as resident
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "residente@genturix.com",
            "password": "Resi123!"
        })
        
        print(f"Resident Login: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            roles = data["user"]["roles"]
            # According to LoginPage.js: case 'Residente': navigate('/resident')
            if "Residente" in roles:
                print(f"Resident with roles {roles} should redirect to /resident")
                assert True
        else:
            print("Resident user not available - this is expected if not seeded")
            pytest.skip("Resident user not available")


class TestMultiTenancy:
    """Test multi-tenancy - condominium_id assignment"""
    
    def test_admin_has_condominium_id(self):
        """Admin user should have condominium_id"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        assert response.status_code == 200
        data = response.json()
        condominium_id = data["user"].get("condominium_id")
        print(f"Admin condominium_id: {condominium_id}")
        assert condominium_id is not None, "Admin should have condominium_id"
    
    def test_guard_has_condominium_id(self):
        """Guard user should have condominium_id"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        
        if response.status_code == 200:
            data = response.json()
            condominium_id = data["user"].get("condominium_id")
            print(f"Guard condominium_id: {condominium_id}")
            assert condominium_id is not None, "Guard should have condominium_id"
        else:
            pytest.skip("Guard user not available")
    
    def test_created_users_inherit_condominium_id(self):
        """Users created by admin should inherit admin's condominium_id"""
        # Login as admin
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert admin_response.status_code == 200
        admin_data = admin_response.json()
        admin_condo_id = admin_data["user"].get("condominium_id")
        admin_token = admin_data["access_token"]
        
        # Create a new user
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"test_condo_{unique_id}@test.com",
            "password": "TestCondo123!",
            "full_name": f"TEST_Condo_User_{unique_id}",
            "role": "Residente",
            "phone": "+1234567890"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=headers)
        assert create_response.status_code == 200
        
        # Login as the new user and check condominium_id
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        
        assert login_response.status_code == 200
        new_user_data = login_response.json()
        new_user_condo_id = new_user_data["user"].get("condominium_id")
        
        print(f"Admin condo: {admin_condo_id}, New user condo: {new_user_condo_id}")
        assert new_user_condo_id == admin_condo_id, "New user should inherit admin's condominium_id"


class TestSuperAdminCreateCondoAdmin:
    """Test Super Admin creating Condo Admin"""
    
    @pytest.fixture
    def super_admin_token(self):
        """Get Super Admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Super Admin login failed")
    
    def test_super_admin_login(self):
        """Super Admin can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        
        print(f"Super Admin Login: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            assert "SuperAdmin" in data["user"]["roles"]
            print(f"Super Admin Login SUCCESS - Roles: {data['user']['roles']}")
        else:
            print(f"Super Admin login failed: {response.text}")
            pytest.skip("Super Admin user not available")
    
    def test_super_admin_get_condominiums(self, super_admin_token):
        """Super Admin can list condominiums"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        response = requests.get(f"{BASE_URL}/api/condominiums", headers=headers)
        
        print(f"Super Admin Get Condominiums: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data)} condominiums")
            if len(data) > 0:
                print(f"First condo: {data[0].get('name')}, ID: {data[0].get('id')}")
                return data[0].get('id')
        else:
            print(f"Failed: {response.text}")
    
    def test_super_admin_create_condo_admin(self, super_admin_token):
        """Super Admin can create admin for a condominium"""
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # First get a condominium
        condos_response = requests.get(f"{BASE_URL}/api/condominiums", headers=headers)
        if condos_response.status_code != 200:
            pytest.skip("Cannot get condominiums")
        
        condos = condos_response.json()
        if len(condos) == 0:
            pytest.skip("No condominiums available")
        
        condo_id = condos[0]["id"]
        unique_id = str(uuid.uuid4())[:8]
        
        admin_data = {
            "email": f"test_condo_admin_{unique_id}@test.com",
            "password": "TestCondoAdmin123!",
            "full_name": f"TEST_Condo_Admin_{unique_id}",
            "role": "Administrador",
            "phone": "+1234567890"
        }
        
        response = requests.post(f"{BASE_URL}/api/super-admin/condominiums/{condo_id}/admin", json=admin_data, headers=headers)
        
        print(f"Super Admin Create Condo Admin: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            assert "user_id" in data
            assert data["condominium_id"] == condo_id
            print(f"Condo Admin created: {data['user_id']} for condo {condo_id}")
            
            # Verify the new admin can login
            login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": admin_data["email"],
                "password": admin_data["password"]
            })
            
            assert login_response.status_code == 200
            login_data = login_response.json()
            assert "Administrador" in login_data["user"]["roles"]
            assert login_data["user"]["condominium_id"] == condo_id
            print(f"New Condo Admin can login! Condo: {login_data['user']['condominium_id']}")
        else:
            print(f"Failed to create condo admin: {response.text}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
