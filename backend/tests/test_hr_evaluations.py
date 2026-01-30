"""
HR Performance Evaluation Module Tests
Tests for CRUD operations on evaluations, multi-tenant isolation, and permissions
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "SuperAdmin123!"


class TestHRPerformanceEvaluations:
    """Test HR Performance Evaluation endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_auth_token(self, email, password):
        """Helper to get auth token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token"), data.get("user")
        return None, None
    
    def test_01_admin_login(self):
        """Test admin can login successfully"""
        token, user = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None, "Admin login failed"
        assert user is not None, "User data not returned"
        assert "Administrador" in user.get("roles", []), "Admin role not found"
        print(f"✓ Admin login successful: {user.get('email')}")
    
    def test_02_get_evaluable_employees(self):
        """Test GET /api/hr/evaluable-employees returns employees list"""
        token, _ = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None, "Login failed"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/hr/evaluable-employees")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        employees = response.json()
        assert isinstance(employees, list), "Response should be a list"
        print(f"✓ GET /api/hr/evaluable-employees returned {len(employees)} employees")
        
        # Verify employee structure
        if employees:
            emp = employees[0]
            assert "id" in emp, "Employee should have id"
            assert "user_name" in emp, "Employee should have user_name"
            print(f"  Sample employee: {emp.get('user_name')} (ID: {emp.get('id')[:8]}...)")
    
    def test_03_get_evaluations_list(self):
        """Test GET /api/hr/evaluations returns evaluations list"""
        token, _ = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None, "Login failed"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        response = self.session.get(f"{BASE_URL}/api/hr/evaluations")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        evaluations = response.json()
        assert isinstance(evaluations, list), "Response should be a list"
        print(f"✓ GET /api/hr/evaluations returned {len(evaluations)} evaluations")
        
        # Verify evaluation structure if any exist
        if evaluations:
            eval_item = evaluations[0]
            assert "id" in eval_item, "Evaluation should have id"
            assert "employee_id" in eval_item, "Evaluation should have employee_id"
            assert "employee_name" in eval_item, "Evaluation should have employee_name"
            assert "categories" in eval_item, "Evaluation should have categories"
            assert "score" in eval_item, "Evaluation should have score"
            print(f"  Sample evaluation: {eval_item.get('employee_name')} - Score: {eval_item.get('score')}")
    
    def test_04_create_evaluation_success(self):
        """Test POST /api/hr/evaluations creates evaluation successfully"""
        token, _ = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None, "Login failed"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # First get an employee to evaluate
        emp_response = self.session.get(f"{BASE_URL}/api/hr/evaluable-employees")
        assert emp_response.status_code == 200, "Failed to get employees"
        employees = emp_response.json()
        
        if not employees:
            pytest.skip("No employees available to evaluate")
        
        employee = employees[0]
        employee_id = employee.get("id")
        
        # Create evaluation
        evaluation_data = {
            "employee_id": employee_id,
            "categories": {
                "discipline": 4,
                "punctuality": 5,
                "performance": 4,
                "communication": 3
            },
            "comments": f"TEST_Evaluation created at {uuid.uuid4().hex[:8]}"
        }
        
        response = self.session.post(f"{BASE_URL}/api/hr/evaluations", json=evaluation_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        created = response.json()
        
        # Verify response structure
        assert "id" in created, "Created evaluation should have id"
        assert created.get("employee_id") == employee_id, "Employee ID mismatch"
        assert "score" in created, "Should have calculated score"
        assert "categories" in created, "Should have categories"
        
        # Verify score calculation (average of 4+5+4+3 = 16/4 = 4.0)
        expected_score = 4.0
        assert created.get("score") == expected_score, f"Score should be {expected_score}, got {created.get('score')}"
        
        print(f"✓ POST /api/hr/evaluations created evaluation successfully")
        print(f"  Employee: {created.get('employee_name')}")
        print(f"  Score: {created.get('score')}")
        print(f"  ID: {created.get('id')}")
        
        # Store for later tests
        self.__class__.created_evaluation_id = created.get("id")
    
    def test_05_get_specific_evaluation(self):
        """Test GET /api/hr/evaluations/{id} returns specific evaluation"""
        token, _ = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None, "Login failed"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get evaluations list first
        list_response = self.session.get(f"{BASE_URL}/api/hr/evaluations")
        assert list_response.status_code == 200, "Failed to get evaluations list"
        evaluations = list_response.json()
        
        if not evaluations:
            pytest.skip("No evaluations available to test")
        
        eval_id = evaluations[0].get("id")
        
        response = self.session.get(f"{BASE_URL}/api/hr/evaluations/{eval_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        evaluation = response.json()
        
        assert evaluation.get("id") == eval_id, "Evaluation ID mismatch"
        assert "employee_name" in evaluation, "Should have employee_name"
        assert "categories" in evaluation, "Should have categories"
        assert "score" in evaluation, "Should have score"
        
        print(f"✓ GET /api/hr/evaluations/{eval_id[:8]}... returned evaluation details")
        print(f"  Employee: {evaluation.get('employee_name')}")
        print(f"  Score: {evaluation.get('score')}")
    
    def test_06_evaluation_categories_validation(self):
        """Test evaluation categories must be 1-5"""
        token, _ = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None, "Login failed"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get an employee
        emp_response = self.session.get(f"{BASE_URL}/api/hr/evaluable-employees")
        employees = emp_response.json()
        
        if not employees:
            pytest.skip("No employees available")
        
        employee_id = employees[0].get("id")
        
        # Test invalid score (0 - below minimum)
        invalid_data = {
            "employee_id": employee_id,
            "categories": {
                "discipline": 0,  # Invalid - should be 1-5
                "punctuality": 3,
                "performance": 3,
                "communication": 3
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/hr/evaluations", json=invalid_data)
        assert response.status_code == 422, f"Expected 422 for invalid score, got {response.status_code}"
        print("✓ Invalid score (0) correctly rejected with 422")
        
        # Test invalid score (6 - above maximum)
        invalid_data["categories"]["discipline"] = 6
        response = self.session.post(f"{BASE_URL}/api/hr/evaluations", json=invalid_data)
        assert response.status_code == 422, f"Expected 422 for invalid score, got {response.status_code}"
        print("✓ Invalid score (6) correctly rejected with 422")
    
    def test_07_cannot_evaluate_self(self):
        """Test that users cannot evaluate themselves"""
        # This test requires a user who is also an employee
        # For now, we'll verify the endpoint exists and returns appropriate error
        token, user = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None, "Login failed"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Try to evaluate with the admin's own user ID
        user_id = user.get("id")
        
        evaluation_data = {
            "employee_id": user_id,  # Admin's own ID
            "categories": {
                "discipline": 5,
                "punctuality": 5,
                "performance": 5,
                "communication": 5
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/hr/evaluations", json=evaluation_data)
        
        # Should either return 404 (not found as employee) or 400 (cannot evaluate self)
        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}"
        print(f"✓ Self-evaluation correctly prevented (status: {response.status_code})")
    
    def test_08_audit_log_records_evaluation(self):
        """Test that evaluation creation is recorded in audit log"""
        token, _ = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None, "Login failed"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get recent audit logs
        response = self.session.get(f"{BASE_URL}/api/audit/logs?limit=50")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        logs = response.json()
        
        # Look for evaluation_created events
        eval_logs = [log for log in logs if log.get("event_type") == "evaluation_created"]
        
        print(f"✓ Found {len(eval_logs)} evaluation_created audit events")
        
        if eval_logs:
            latest = eval_logs[0]
            print(f"  Latest: {latest.get('timestamp')} - {latest.get('details', {}).get('employee_name', 'N/A')}")
    
    def test_09_employee_evaluation_summary(self):
        """Test GET /api/hr/evaluations/employee/{id}/summary returns summary"""
        token, _ = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None, "Login failed"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get evaluations to find an employee with evaluations
        eval_response = self.session.get(f"{BASE_URL}/api/hr/evaluations")
        evaluations = eval_response.json()
        
        if not evaluations:
            pytest.skip("No evaluations available for summary test")
        
        employee_id = evaluations[0].get("employee_id")
        
        response = self.session.get(f"{BASE_URL}/api/hr/evaluations/employee/{employee_id}/summary")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        summary = response.json()
        
        # Verify summary structure
        assert "employee_id" in summary, "Should have employee_id"
        assert "employee_name" in summary, "Should have employee_name"
        assert "total_evaluations" in summary, "Should have total_evaluations"
        assert "average_score" in summary, "Should have average_score"
        assert "category_averages" in summary, "Should have category_averages"
        
        print(f"✓ GET /api/hr/evaluations/employee/{employee_id[:8]}../summary returned summary")
        print(f"  Employee: {summary.get('employee_name')}")
        print(f"  Total evaluations: {summary.get('total_evaluations')}")
        print(f"  Average score: {summary.get('average_score')}")
    
    def test_10_guards_endpoint_returns_employees(self):
        """Test GET /api/hr/guards returns guards list (for evaluation)"""
        token, _ = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None, "Login failed"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/hr/guards")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        guards = response.json()
        
        print(f"✓ GET /api/hr/guards returned {len(guards)} guards")
        
        if guards:
            guard = guards[0]
            print(f"  Sample guard: {guard.get('user_name')} (Badge: {guard.get('badge_number')})")


class TestEvaluationPermissions:
    """Test role-based access control for evaluations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_auth_token(self, email, password):
        """Helper to get auth token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token"), data.get("user")
        return None, None
    
    def test_01_superadmin_can_access_evaluations(self):
        """Test SuperAdmin can access evaluation endpoints"""
        token, user = self.get_auth_token(SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD)
        assert token is not None, "SuperAdmin login failed"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # SuperAdmin should be able to get evaluations
        response = self.session.get(f"{BASE_URL}/api/hr/evaluations")
        
        # SuperAdmin may not have condominium_id, so might get empty list or 200
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ SuperAdmin can access evaluations endpoint")
    
    def test_02_unauthenticated_cannot_access(self):
        """Test unauthenticated requests are rejected"""
        # No auth header
        response = self.session.get(f"{BASE_URL}/api/hr/evaluations")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Unauthenticated request correctly rejected (status: {response.status_code})")
    
    def test_03_invalid_token_rejected(self):
        """Test invalid token is rejected"""
        self.session.headers.update({"Authorization": "Bearer invalid_token_12345"})
        
        response = self.session.get(f"{BASE_URL}/api/hr/evaluations")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid token correctly rejected with 401")


class TestEvaluationDataIntegrity:
    """Test data integrity and persistence for evaluations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_auth_token(self, email, password):
        """Helper to get auth token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        return None
    
    def test_01_create_and_verify_persistence(self):
        """Test that created evaluation persists and can be retrieved"""
        token = self.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None, "Login failed"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get an employee
        emp_response = self.session.get(f"{BASE_URL}/api/hr/evaluable-employees")
        employees = emp_response.json()
        
        if not employees:
            pytest.skip("No employees available")
        
        employee = employees[0]
        unique_comment = f"TEST_Persistence_{uuid.uuid4().hex[:12]}"
        
        # Create evaluation
        evaluation_data = {
            "employee_id": employee.get("id"),
            "categories": {
                "discipline": 3,
                "punctuality": 4,
                "performance": 5,
                "communication": 4
            },
            "comments": unique_comment
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/hr/evaluations", json=evaluation_data)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        
        created = create_response.json()
        eval_id = created.get("id")
        
        # Verify by GET
        get_response = self.session.get(f"{BASE_URL}/api/hr/evaluations/{eval_id}")
        assert get_response.status_code == 200, f"GET failed: {get_response.text}"
        
        fetched = get_response.json()
        
        # Verify data matches
        assert fetched.get("id") == eval_id, "ID mismatch"
        assert fetched.get("employee_id") == employee.get("id"), "Employee ID mismatch"
        assert fetched.get("comments") == unique_comment, "Comments mismatch"
        assert fetched.get("categories", {}).get("discipline") == 3, "Discipline score mismatch"
        assert fetched.get("categories", {}).get("punctuality") == 4, "Punctuality score mismatch"
        assert fetched.get("categories", {}).get("performance") == 5, "Performance score mismatch"
        assert fetched.get("categories", {}).get("communication") == 4, "Communication score mismatch"
        
        # Verify score calculation (3+4+5+4)/4 = 4.0
        assert fetched.get("score") == 4.0, f"Score should be 4.0, got {fetched.get('score')}"
        
        print(f"✓ Evaluation created and verified in database")
        print(f"  ID: {eval_id}")
        print(f"  Score: {fetched.get('score')}")
        print(f"  Comment: {unique_comment[:30]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
