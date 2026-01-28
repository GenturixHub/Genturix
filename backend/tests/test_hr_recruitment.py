"""
GENTURIX HR Recruitment & User Management Tests - Iteration 9
Tests for:
- HR role in RoleEnum
- Candidate CRUD (create, list, update status, hire, reject)
- Employee management (create directly, deactivate, activate)
- Admin user creation
- Super Admin condo admin creation
- Full hire flow: create candidate -> hire -> new user can login
"""
import pytest
import requests
import os
from datetime import datetime
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_CREDS = {"email": "superadmin@genturix.com", "password": "SuperAdmin123!"}
ADMIN_CREDS = {"email": "admin@genturix.com", "password": "Admin123!"}
GUARD_CREDS = {"email": "guarda1@genturix.com", "password": "Guard123!"}


class TestAuth:
    """Authentication tests for all roles"""
    
    def test_super_admin_login(self):
        """Test super admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPER_ADMIN_CREDS)
        assert response.status_code == 200, f"Super Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "SuperAdmin" in data["user"]["roles"]
        print(f"✓ Super Admin login successful: {data['user']['email']}")
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "Administrador" in data["user"]["roles"]
        print(f"✓ Admin login successful: {data['user']['email']}")


@pytest.fixture(scope="module")
def super_admin_token():
    """Get super admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=SUPER_ADMIN_CREDS)
    if response.status_code != 200:
        pytest.skip(f"Super Admin login failed: {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def super_admin_headers(super_admin_token):
    """Super Admin request headers"""
    return {"Authorization": f"Bearer {super_admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Admin request headers"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# ==================== HR CANDIDATES TESTS ====================
class TestHRCandidates:
    """HR Recruitment Candidates CRUD tests"""
    
    def test_create_candidate_success(self, admin_headers):
        """POST /api/hr/candidates - Create recruitment candidate"""
        unique_id = str(uuid.uuid4())[:8]
        candidate_data = {
            "full_name": f"TEST_Candidate_{unique_id}",
            "email": f"test_candidate_{unique_id}@test.com",
            "phone": "+52 555 123 4567",
            "position": "Guarda",
            "experience_years": 3,
            "notes": "Test candidate created by pytest"
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/candidates", json=candidate_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to create candidate: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["full_name"] == candidate_data["full_name"]
        assert data["email"] == candidate_data["email"]
        assert data["status"] == "applied"
        assert data["position"] == "Guarda"
        print(f"✓ POST /api/hr/candidates - Created: {data['id'][:8]}...")
        return data
    
    def test_create_candidate_supervisor_position(self, admin_headers):
        """POST /api/hr/candidates - Create candidate for Supervisor position"""
        unique_id = str(uuid.uuid4())[:8]
        candidate_data = {
            "full_name": f"TEST_Supervisor_{unique_id}",
            "email": f"test_supervisor_{unique_id}@test.com",
            "phone": "+52 555 987 6543",
            "position": "Supervisor",
            "experience_years": 5,
            "notes": "Supervisor candidate"
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/candidates", json=candidate_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to create supervisor candidate: {response.text}"
        data = response.json()
        assert data["position"] == "Supervisor"
        print(f"✓ POST /api/hr/candidates - Created Supervisor candidate: {data['id'][:8]}...")
    
    def test_get_candidates_list(self, admin_headers):
        """GET /api/hr/candidates - List all candidates"""
        response = requests.get(f"{BASE_URL}/api/hr/candidates", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get candidates: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/hr/candidates - Found {len(data)} candidates")
        return data
    
    def test_get_candidates_filter_by_status(self, admin_headers):
        """GET /api/hr/candidates?status=applied - Filter by status"""
        response = requests.get(f"{BASE_URL}/api/hr/candidates?status=applied", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        for candidate in data:
            assert candidate["status"] == "applied"
        print(f"✓ GET /api/hr/candidates?status=applied - Found {len(data)} applied candidates")
    
    def test_get_candidates_filter_by_position(self, admin_headers):
        """GET /api/hr/candidates?position=Guarda - Filter by position"""
        response = requests.get(f"{BASE_URL}/api/hr/candidates?position=Guarda", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        for candidate in data:
            assert candidate["position"] == "Guarda"
        print(f"✓ GET /api/hr/candidates?position=Guarda - Found {len(data)} guard candidates")
    
    def test_get_candidate_by_id(self, admin_headers):
        """GET /api/hr/candidates/{id} - Get single candidate"""
        # First create a candidate
        unique_id = str(uuid.uuid4())[:8]
        candidate_data = {
            "full_name": f"TEST_GetById_{unique_id}",
            "email": f"test_getbyid_{unique_id}@test.com",
            "phone": "+52 555 111 2222",
            "position": "Guarda",
            "experience_years": 1
        }
        create_resp = requests.post(f"{BASE_URL}/api/hr/candidates", json=candidate_data, headers=admin_headers)
        candidate_id = create_resp.json()["id"]
        
        # Get by ID
        response = requests.get(f"{BASE_URL}/api/hr/candidates/{candidate_id}", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get candidate: {response.text}"
        data = response.json()
        assert data["id"] == candidate_id
        print(f"✓ GET /api/hr/candidates/{candidate_id[:8]}... - Found")
    
    def test_get_candidate_not_found(self, admin_headers):
        """GET /api/hr/candidates/{id} - 404 for non-existent"""
        response = requests.get(f"{BASE_URL}/api/hr/candidates/nonexistent-id", headers=admin_headers)
        assert response.status_code == 404
        print("✓ GET /api/hr/candidates/nonexistent - Returns 404")
    
    def test_update_candidate_status_to_interview(self, admin_headers):
        """PUT /api/hr/candidates/{id} - Update status to interview"""
        # Create candidate
        unique_id = str(uuid.uuid4())[:8]
        candidate_data = {
            "full_name": f"TEST_Interview_{unique_id}",
            "email": f"test_interview_{unique_id}@test.com",
            "phone": "+52 555 333 4444",
            "position": "Guarda",
            "experience_years": 2
        }
        create_resp = requests.post(f"{BASE_URL}/api/hr/candidates", json=candidate_data, headers=admin_headers)
        candidate_id = create_resp.json()["id"]
        
        # Update to interview
        update_data = {"status": "interview"}
        response = requests.put(f"{BASE_URL}/api/hr/candidates/{candidate_id}", json=update_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to update candidate: {response.text}"
        data = response.json()
        assert data["status"] == "interview"
        print(f"✓ PUT /api/hr/candidates/{candidate_id[:8]}... - Status updated to interview")
    
    def test_update_candidate_invalid_status(self, admin_headers):
        """PUT /api/hr/candidates/{id} - 400 for invalid status"""
        # Create candidate
        unique_id = str(uuid.uuid4())[:8]
        candidate_data = {
            "full_name": f"TEST_InvalidStatus_{unique_id}",
            "email": f"test_invalidstatus_{unique_id}@test.com",
            "phone": "+52 555 555 6666",
            "position": "Guarda",
            "experience_years": 1
        }
        create_resp = requests.post(f"{BASE_URL}/api/hr/candidates", json=candidate_data, headers=admin_headers)
        candidate_id = create_resp.json()["id"]
        
        # Try invalid status
        update_data = {"status": "invalid_status"}
        response = requests.put(f"{BASE_URL}/api/hr/candidates/{candidate_id}", json=update_data, headers=admin_headers)
        assert response.status_code == 400
        print("✓ PUT /api/hr/candidates - Returns 400 for invalid status")


# ==================== HIRE CANDIDATE FLOW TESTS ====================
class TestHireCandidateFlow:
    """Full hire flow: create candidate -> hire -> new user can login"""
    
    def test_hire_candidate_full_flow(self, admin_headers):
        """POST /api/hr/candidates/{id}/hire - Full hire flow"""
        # 1. Create candidate
        unique_id = str(uuid.uuid4())[:8]
        candidate_email = f"test_hire_{unique_id}@test.com"
        candidate_data = {
            "full_name": f"TEST_HireFlow_{unique_id}",
            "email": candidate_email,
            "phone": "+52 555 777 8888",
            "position": "Guarda",
            "experience_years": 2,
            "notes": "Candidate for hire flow test"
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/hr/candidates", json=candidate_data, headers=admin_headers)
        assert create_resp.status_code == 200, f"Failed to create candidate: {create_resp.text}"
        candidate_id = create_resp.json()["id"]
        print(f"  Step 1: Created candidate {candidate_id[:8]}...")
        
        # 2. Hire the candidate
        hire_password = "TestHire123!"
        hire_data = {
            "badge_number": f"GRD-TEST-{unique_id}",
            "hourly_rate": 15.0,
            "password": hire_password
        }
        
        hire_resp = requests.post(f"{BASE_URL}/api/hr/candidates/{candidate_id}/hire", json=hire_data, headers=admin_headers)
        assert hire_resp.status_code == 200, f"Failed to hire candidate: {hire_resp.text}"
        hire_result = hire_resp.json()
        assert "user_id" in hire_result
        assert "guard_id" in hire_result
        assert hire_result["email"] == candidate_email
        print(f"  Step 2: Hired candidate - user_id: {hire_result['user_id'][:8]}...")
        
        # 3. Verify candidate status is now 'hired'
        get_resp = requests.get(f"{BASE_URL}/api/hr/candidates/{candidate_id}", headers=admin_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "hired"
        print(f"  Step 3: Verified candidate status is 'hired'")
        
        # 4. Verify new user can login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": candidate_email,
            "password": hire_password
        })
        assert login_resp.status_code == 200, f"New user login failed: {login_resp.text}"
        login_data = login_resp.json()
        assert "access_token" in login_data
        assert "Guarda" in login_data["user"]["roles"]
        print(f"  Step 4: New user can login successfully!")
        
        print(f"✓ FULL HIRE FLOW COMPLETE: Candidate -> Hire -> Login works!")
        return hire_result
    
    def test_hire_candidate_already_hired(self, admin_headers):
        """POST /api/hr/candidates/{id}/hire - 400 for already hired"""
        # Create and hire a candidate
        unique_id = str(uuid.uuid4())[:8]
        candidate_data = {
            "full_name": f"TEST_AlreadyHired_{unique_id}",
            "email": f"test_alreadyhired_{unique_id}@test.com",
            "phone": "+52 555 999 0000",
            "position": "Guarda",
            "experience_years": 1
        }
        create_resp = requests.post(f"{BASE_URL}/api/hr/candidates", json=candidate_data, headers=admin_headers)
        candidate_id = create_resp.json()["id"]
        
        # Hire first time
        hire_data = {"badge_number": f"GRD-AH-{unique_id}", "hourly_rate": 12.0, "password": "TestPass123!"}
        requests.post(f"{BASE_URL}/api/hr/candidates/{candidate_id}/hire", json=hire_data, headers=admin_headers)
        
        # Try to hire again
        hire_data2 = {"badge_number": f"GRD-AH2-{unique_id}", "hourly_rate": 12.0, "password": "TestPass123!"}
        response = requests.post(f"{BASE_URL}/api/hr/candidates/{candidate_id}/hire", json=hire_data2, headers=admin_headers)
        assert response.status_code == 400
        assert "contratado" in response.json()["detail"].lower()
        print("✓ POST /api/hr/candidates/hire - Returns 400 for already hired")
    
    def test_hire_candidate_duplicate_badge(self, admin_headers):
        """POST /api/hr/candidates/{id}/hire - 400 for duplicate badge number"""
        # Create first candidate and hire
        unique_id1 = str(uuid.uuid4())[:8]
        badge_number = f"GRD-DUP-{unique_id1}"
        
        candidate1 = {
            "full_name": f"TEST_DupBadge1_{unique_id1}",
            "email": f"test_dupbadge1_{unique_id1}@test.com",
            "phone": "+52 555 111 1111",
            "position": "Guarda",
            "experience_years": 1
        }
        create1 = requests.post(f"{BASE_URL}/api/hr/candidates", json=candidate1, headers=admin_headers)
        candidate1_id = create1.json()["id"]
        
        hire1 = {"badge_number": badge_number, "hourly_rate": 12.0, "password": "TestPass123!"}
        requests.post(f"{BASE_URL}/api/hr/candidates/{candidate1_id}/hire", json=hire1, headers=admin_headers)
        
        # Create second candidate and try to hire with same badge
        unique_id2 = str(uuid.uuid4())[:8]
        candidate2 = {
            "full_name": f"TEST_DupBadge2_{unique_id2}",
            "email": f"test_dupbadge2_{unique_id2}@test.com",
            "phone": "+52 555 222 2222",
            "position": "Guarda",
            "experience_years": 1
        }
        create2 = requests.post(f"{BASE_URL}/api/hr/candidates", json=candidate2, headers=admin_headers)
        candidate2_id = create2.json()["id"]
        
        hire2 = {"badge_number": badge_number, "hourly_rate": 12.0, "password": "TestPass123!"}
        response = requests.post(f"{BASE_URL}/api/hr/candidates/{candidate2_id}/hire", json=hire2, headers=admin_headers)
        assert response.status_code == 400
        assert "identificación" in response.json()["detail"].lower() or "uso" in response.json()["detail"].lower()
        print("✓ POST /api/hr/candidates/hire - Returns 400 for duplicate badge number")


# ==================== REJECT CANDIDATE TESTS ====================
class TestRejectCandidate:
    """Reject candidate tests"""
    
    def test_reject_candidate_success(self, admin_headers):
        """PUT /api/hr/candidates/{id}/reject - Reject candidate"""
        # Create candidate
        unique_id = str(uuid.uuid4())[:8]
        candidate_data = {
            "full_name": f"TEST_Reject_{unique_id}",
            "email": f"test_reject_{unique_id}@test.com",
            "phone": "+52 555 333 3333",
            "position": "Guarda",
            "experience_years": 0
        }
        create_resp = requests.post(f"{BASE_URL}/api/hr/candidates", json=candidate_data, headers=admin_headers)
        candidate_id = create_resp.json()["id"]
        
        # Reject
        response = requests.put(f"{BASE_URL}/api/hr/candidates/{candidate_id}/reject", headers=admin_headers)
        assert response.status_code == 200, f"Failed to reject: {response.text}"
        assert "rechazado" in response.json()["message"].lower()
        
        # Verify status
        get_resp = requests.get(f"{BASE_URL}/api/hr/candidates/{candidate_id}", headers=admin_headers)
        assert get_resp.json()["status"] == "rejected"
        print(f"✓ PUT /api/hr/candidates/{candidate_id[:8]}../reject - Rejected")
    
    def test_reject_already_hired(self, admin_headers):
        """PUT /api/hr/candidates/{id}/reject - 400 for already hired"""
        # Create and hire
        unique_id = str(uuid.uuid4())[:8]
        candidate_data = {
            "full_name": f"TEST_RejectHired_{unique_id}",
            "email": f"test_rejecthired_{unique_id}@test.com",
            "phone": "+52 555 444 4444",
            "position": "Guarda",
            "experience_years": 1
        }
        create_resp = requests.post(f"{BASE_URL}/api/hr/candidates", json=candidate_data, headers=admin_headers)
        candidate_id = create_resp.json()["id"]
        
        hire_data = {"badge_number": f"GRD-RH-{unique_id}", "hourly_rate": 12.0, "password": "TestPass123!"}
        requests.post(f"{BASE_URL}/api/hr/candidates/{candidate_id}/hire", json=hire_data, headers=admin_headers)
        
        # Try to reject
        response = requests.put(f"{BASE_URL}/api/hr/candidates/{candidate_id}/reject", headers=admin_headers)
        assert response.status_code == 400
        print("✓ PUT /api/hr/candidates/reject - Returns 400 for already hired")


# ==================== EMPLOYEE MANAGEMENT TESTS ====================
class TestEmployeeManagement:
    """HR Employee management tests (create directly, deactivate, activate)"""
    
    def test_create_employee_directly(self, admin_headers):
        """POST /api/hr/employees - Create employee without recruitment"""
        unique_id = str(uuid.uuid4())[:8]
        employee_data = {
            "email": f"test_direct_emp_{unique_id}@test.com",
            "password": "DirectEmp123!",
            "full_name": f"TEST_DirectEmployee_{unique_id}",
            "badge_number": f"GRD-DIR-{unique_id}",
            "phone": "+52 555 555 5555",
            "emergency_contact": "+52 555 666 6666",
            "hourly_rate": 14.0
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/employees", json=employee_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to create employee: {response.text}"
        data = response.json()
        assert "user_id" in data
        assert "guard_id" in data
        print(f"✓ POST /api/hr/employees - Created directly: {data['guard_id'][:8]}...")
        return data
    
    def test_create_employee_duplicate_email(self, admin_headers):
        """POST /api/hr/employees - 400 for duplicate email"""
        unique_id = str(uuid.uuid4())[:8]
        email = f"test_dup_emp_{unique_id}@test.com"
        
        # Create first
        employee1 = {
            "email": email,
            "password": "DupEmp123!",
            "full_name": f"TEST_DupEmp1_{unique_id}",
            "badge_number": f"GRD-DE1-{unique_id}",
            "phone": "+52 555 777 7777",
            "emergency_contact": "+52 555 888 8888",
            "hourly_rate": 12.0
        }
        requests.post(f"{BASE_URL}/api/hr/employees", json=employee1, headers=admin_headers)
        
        # Try duplicate
        employee2 = {
            "email": email,
            "password": "DupEmp123!",
            "full_name": f"TEST_DupEmp2_{unique_id}",
            "badge_number": f"GRD-DE2-{unique_id}",
            "phone": "+52 555 999 9999",
            "emergency_contact": "+52 555 000 0000",
            "hourly_rate": 12.0
        }
        response = requests.post(f"{BASE_URL}/api/hr/employees", json=employee2, headers=admin_headers)
        assert response.status_code == 400
        print("✓ POST /api/hr/employees - Returns 400 for duplicate email")
    
    def test_deactivate_employee(self, admin_headers):
        """PUT /api/hr/employees/{id}/deactivate - Deactivate employee"""
        # Create employee first
        unique_id = str(uuid.uuid4())[:8]
        employee_data = {
            "email": f"test_deact_{unique_id}@test.com",
            "password": "Deact123!",
            "full_name": f"TEST_Deactivate_{unique_id}",
            "badge_number": f"GRD-DEACT-{unique_id}",
            "phone": "+52 555 111 2222",
            "emergency_contact": "+52 555 333 4444",
            "hourly_rate": 12.0
        }
        create_resp = requests.post(f"{BASE_URL}/api/hr/employees", json=employee_data, headers=admin_headers)
        guard_id = create_resp.json()["guard_id"]
        
        # Deactivate
        response = requests.put(f"{BASE_URL}/api/hr/employees/{guard_id}/deactivate", headers=admin_headers)
        assert response.status_code == 200, f"Failed to deactivate: {response.text}"
        assert "desactivado" in response.json()["message"].lower()
        
        # Verify guard is inactive
        guard_resp = requests.get(f"{BASE_URL}/api/hr/guards/{guard_id}", headers=admin_headers)
        assert guard_resp.json()["is_active"] == False
        print(f"✓ PUT /api/hr/employees/{guard_id[:8]}../deactivate - Deactivated")
    
    def test_activate_employee(self, admin_headers):
        """PUT /api/hr/employees/{id}/activate - Reactivate employee"""
        # Create and deactivate first
        unique_id = str(uuid.uuid4())[:8]
        employee_data = {
            "email": f"test_react_{unique_id}@test.com",
            "password": "React123!",
            "full_name": f"TEST_Reactivate_{unique_id}",
            "badge_number": f"GRD-REACT-{unique_id}",
            "phone": "+52 555 555 6666",
            "emergency_contact": "+52 555 777 8888",
            "hourly_rate": 12.0
        }
        create_resp = requests.post(f"{BASE_URL}/api/hr/employees", json=employee_data, headers=admin_headers)
        guard_id = create_resp.json()["guard_id"]
        
        # Deactivate
        requests.put(f"{BASE_URL}/api/hr/employees/{guard_id}/deactivate", headers=admin_headers)
        
        # Reactivate
        response = requests.put(f"{BASE_URL}/api/hr/employees/{guard_id}/activate", headers=admin_headers)
        assert response.status_code == 200, f"Failed to activate: {response.text}"
        assert "reactivado" in response.json()["message"].lower()
        
        # Verify guard is active
        guard_resp = requests.get(f"{BASE_URL}/api/hr/guards/{guard_id}", headers=admin_headers)
        assert guard_resp.json()["is_active"] == True
        print(f"✓ PUT /api/hr/employees/{guard_id[:8]}../activate - Reactivated")


# ==================== ADMIN USER CREATION TESTS ====================
class TestAdminUserCreation:
    """Admin creates users in their condo"""
    
    def test_admin_create_resident(self, admin_headers):
        """POST /api/admin/users - Admin creates Resident user"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"test_resident_{unique_id}@test.com",
            "password": "Resident123!",
            "full_name": f"TEST_Resident_{unique_id}",
            "role": "Residente",
            "phone": "+52 555 111 1111"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to create resident: {response.text}"
        data = response.json()
        assert "user_id" in data
        print(f"✓ POST /api/admin/users - Created Resident: {data['user_id'][:8]}...")
    
    def test_admin_create_hr_user(self, admin_headers):
        """POST /api/admin/users - Admin creates HR user"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"test_hr_{unique_id}@test.com",
            "password": "HRUser123!",
            "full_name": f"TEST_HR_{unique_id}",
            "role": "HR",
            "phone": "+52 555 222 2222"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to create HR user: {response.text}"
        data = response.json()
        assert "user_id" in data
        print(f"✓ POST /api/admin/users - Created HR user: {data['user_id'][:8]}...")
    
    def test_admin_create_guard_user(self, admin_headers):
        """POST /api/admin/users - Admin creates Guard user"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"test_guard_user_{unique_id}@test.com",
            "password": "GuardUser123!",
            "full_name": f"TEST_Guard_{unique_id}",
            "role": "Guarda",
            "phone": "+52 555 333 3333"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to create guard user: {response.text}"
        data = response.json()
        assert "user_id" in data
        print(f"✓ POST /api/admin/users - Created Guard user: {data['user_id'][:8]}...")
    
    def test_admin_create_invalid_role(self, admin_headers):
        """POST /api/admin/users - 400 for invalid role"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"test_invalid_role_{unique_id}@test.com",
            "password": "Invalid123!",
            "full_name": f"TEST_InvalidRole_{unique_id}",
            "role": "InvalidRole"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        assert response.status_code == 400
        print("✓ POST /api/admin/users - Returns 400 for invalid role")
    
    def test_admin_get_users(self, admin_headers):
        """GET /api/admin/users - Admin lists users in their condo"""
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get users: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/admin/users - Found {len(data)} users")
    
    def test_admin_get_users_filter_by_role(self, admin_headers):
        """GET /api/admin/users?role=Guarda - Filter by role"""
        response = requests.get(f"{BASE_URL}/api/admin/users?role=Guarda", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        for user in data:
            assert "Guarda" in user.get("roles", [])
        print(f"✓ GET /api/admin/users?role=Guarda - Found {len(data)} guards")


# ==================== SUPER ADMIN CONDO ADMIN CREATION TESTS ====================
class TestSuperAdminCondoAdmin:
    """Super Admin creates Condo Admin"""
    
    def test_super_admin_create_condo_admin(self, super_admin_headers):
        """POST /api/super-admin/condominiums/{id}/admin - Create Condo Admin"""
        # First get a condominium
        condos_resp = requests.get(f"{BASE_URL}/api/condominiums", headers=super_admin_headers)
        if condos_resp.status_code != 200 or not condos_resp.json():
            pytest.skip("No condominiums found")
        
        condo_id = condos_resp.json()[0]["id"]
        
        unique_id = str(uuid.uuid4())[:8]
        admin_data = {
            "email": f"test_condo_admin_{unique_id}@test.com",
            "password": "CondoAdmin123!",
            "full_name": f"TEST_CondoAdmin_{unique_id}",
            "role": "Administrador",
            "phone": "+52 555 444 4444"
        }
        
        response = requests.post(f"{BASE_URL}/api/super-admin/condominiums/{condo_id}/admin", json=admin_data, headers=super_admin_headers)
        assert response.status_code == 200, f"Failed to create condo admin: {response.text}"
        data = response.json()
        assert "user_id" in data
        assert data["condominium_id"] == condo_id
        print(f"✓ POST /api/super-admin/condominiums/{condo_id[:8]}../admin - Created Condo Admin")
        
        # Verify new admin can login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": admin_data["email"],
            "password": admin_data["password"]
        })
        assert login_resp.status_code == 200, f"New condo admin login failed: {login_resp.text}"
        assert "Administrador" in login_resp.json()["user"]["roles"]
        print(f"✓ New Condo Admin can login successfully!")
    
    def test_super_admin_create_condo_admin_invalid_condo(self, super_admin_headers):
        """POST /api/super-admin/condominiums/{id}/admin - 404 for invalid condo"""
        unique_id = str(uuid.uuid4())[:8]
        admin_data = {
            "email": f"test_invalid_condo_{unique_id}@test.com",
            "password": "Invalid123!",
            "full_name": f"TEST_InvalidCondo_{unique_id}",
            "role": "Administrador"
        }
        
        response = requests.post(f"{BASE_URL}/api/super-admin/condominiums/nonexistent-condo/admin", json=admin_data, headers=super_admin_headers)
        assert response.status_code == 404
        print("✓ POST /api/super-admin/condominiums/invalid/admin - Returns 404")


# ==================== HR ROLE VERIFICATION ====================
class TestHRRole:
    """Verify HR role exists and works"""
    
    def test_hr_role_in_enum(self, admin_headers):
        """Verify HR role exists by creating HR user"""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"test_hr_role_{unique_id}@test.com",
            "password": "HRRole123!",
            "full_name": f"TEST_HRRole_{unique_id}",
            "role": "HR"
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        assert response.status_code == 200, f"HR role not accepted: {response.text}"
        
        # Verify HR user can login
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        assert login_resp.status_code == 200
        assert "HR" in login_resp.json()["user"]["roles"]
        print("✓ HR role exists in RoleEnum and works correctly")
    
    def test_hr_user_can_access_candidates(self, admin_headers):
        """Verify HR user can access candidate endpoints"""
        # Create HR user
        unique_id = str(uuid.uuid4())[:8]
        hr_email = f"test_hr_access_{unique_id}@test.com"
        hr_password = "HRAccess123!"
        
        user_data = {
            "email": hr_email,
            "password": hr_password,
            "full_name": f"TEST_HRAccess_{unique_id}",
            "role": "HR"
        }
        requests.post(f"{BASE_URL}/api/admin/users", json=user_data, headers=admin_headers)
        
        # Login as HR
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": hr_email,
            "password": hr_password
        })
        hr_token = login_resp.json()["access_token"]
        hr_headers = {"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"}
        
        # Access candidates
        response = requests.get(f"{BASE_URL}/api/hr/candidates", headers=hr_headers)
        assert response.status_code == 200, f"HR cannot access candidates: {response.text}"
        print("✓ HR user can access /api/hr/candidates")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
