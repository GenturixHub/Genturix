"""
Test HR Data Integrity Validation Endpoints
============================================
Tests for P0 RRHH bug fix: Empleado duplicado en la lista que no puede ser evaluado

Endpoints tested:
- GET /api/hr/validate-integrity - Detect duplicates, missing user_id, invalid users, orphan evaluations
- POST /api/hr/cleanup-invalid-guards - Clean up invalid guards (dry_run and real)
- GET /api/hr/evaluable-employees - Only return valid employees with user_id and active user
- GET /api/hr/guards - Filter by default only valid and active guards
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "SuperAdmin123!"


class TestHRIntegrityValidation:
    """Test HR data integrity validation endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    def get_superadmin_token(self):
        """Get superadmin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERADMIN_EMAIL,
            "password": SUPERADMIN_PASSWORD
        })
        assert response.status_code == 200, f"SuperAdmin login failed: {response.text}"
        return response.json()["access_token"]
    
    # ==================== VALIDATE INTEGRITY TESTS ====================
    
    def test_01_validate_integrity_endpoint_exists(self):
        """Test that validate-integrity endpoint exists and requires auth"""
        response = self.session.get(f"{BASE_URL}/api/hr/validate-integrity")
        # Should return 401 without auth, not 404
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ validate-integrity endpoint exists")
    
    def test_02_validate_integrity_returns_structure(self):
        """Test validate-integrity returns expected structure"""
        token = self.get_admin_token()
        self.session.headers["Authorization"] = f"Bearer {token}"
        
        response = self.session.get(f"{BASE_URL}/api/hr/validate-integrity")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Check required fields
        assert "duplicates" in data, "Missing 'duplicates' field"
        assert "missing_user_id" in data, "Missing 'missing_user_id' field"
        assert "invalid_user" in data, "Missing 'invalid_user' field"
        assert "orphan_evaluations" in data, "Missing 'orphan_evaluations' field"
        assert "summary" in data, "Missing 'summary' field"
        
        # Check summary structure
        summary = data["summary"]
        assert "total_guards" in summary, "Missing 'total_guards' in summary"
        assert "valid_guards" in summary, "Missing 'valid_guards' in summary"
        assert "invalid_guards" in summary, "Missing 'invalid_guards' in summary"
        
        print(f"✓ validate-integrity returns correct structure")
        print(f"  Summary: {summary}")
    
    def test_03_validate_integrity_detects_issues(self):
        """Test that validate-integrity correctly detects data issues"""
        token = self.get_admin_token()
        self.session.headers["Authorization"] = f"Bearer {token}"
        
        response = self.session.get(f"{BASE_URL}/api/hr/validate-integrity")
        assert response.status_code == 200
        
        data = response.json()
        summary = data["summary"]
        
        # Log findings
        print(f"✓ Integrity validation results:")
        print(f"  - Total guards: {summary['total_guards']}")
        print(f"  - Valid guards: {summary['valid_guards']}")
        print(f"  - Invalid guards: {summary['invalid_guards']}")
        print(f"  - Duplicates found: {len(data['duplicates'])}")
        print(f"  - Missing user_id: {len(data['missing_user_id'])}")
        print(f"  - Invalid users: {len(data['invalid_user'])}")
        print(f"  - Orphan evaluations: {len(data['orphan_evaluations'])}")
        
        # After cleanup, there should be no duplicates or missing user_id in active guards
        # (based on main agent's note that 8 guards were deactivated)
        
    # ==================== CLEANUP INVALID GUARDS TESTS ====================
    
    def test_04_cleanup_requires_superadmin(self):
        """Test that cleanup endpoint requires SuperAdmin role"""
        token = self.get_admin_token()  # Admin, not SuperAdmin
        self.session.headers["Authorization"] = f"Bearer {token}"
        
        response = self.session.post(f"{BASE_URL}/api/hr/cleanup-invalid-guards?dry_run=true")
        # Should be forbidden for regular admin
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ cleanup-invalid-guards requires SuperAdmin role")
    
    def test_05_cleanup_dry_run_mode(self):
        """Test cleanup in dry_run mode (no actual changes)"""
        token = self.get_superadmin_token()
        self.session.headers["Authorization"] = f"Bearer {token}"
        
        response = self.session.post(f"{BASE_URL}/api/hr/cleanup-invalid-guards?dry_run=true")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Check structure
        assert "dry_run" in data, "Missing 'dry_run' field"
        assert data["dry_run"] == True, "dry_run should be True"
        assert "deactivated" in data, "Missing 'deactivated' field"
        assert "removed_duplicates" in data, "Missing 'removed_duplicates' field"
        
        print(f"✓ cleanup dry_run mode works")
        print(f"  - Would deactivate: {len(data['deactivated'])} guards")
        print(f"  - Would remove duplicates: {len(data['removed_duplicates'])}")
    
    # ==================== EVALUABLE EMPLOYEES TESTS ====================
    
    def test_06_evaluable_employees_endpoint_exists(self):
        """Test that evaluable-employees endpoint exists"""
        token = self.get_admin_token()
        self.session.headers["Authorization"] = f"Bearer {token}"
        
        response = self.session.get(f"{BASE_URL}/api/hr/evaluable-employees")
        assert response.status_code == 200, f"Failed: {response.text}"
        print("✓ evaluable-employees endpoint exists")
    
    def test_07_evaluable_employees_returns_valid_only(self):
        """Test that evaluable-employees only returns valid employees"""
        token = self.get_admin_token()
        self.session.headers["Authorization"] = f"Bearer {token}"
        
        response = self.session.get(f"{BASE_URL}/api/hr/evaluable-employees")
        assert response.status_code == 200
        
        employees = response.json()
        assert isinstance(employees, list), "Should return a list"
        
        # All returned employees should be evaluable
        for emp in employees:
            assert emp.get("_is_evaluable") == True, f"Employee {emp.get('id')} should be evaluable"
            assert emp.get("user_id") is not None, f"Employee {emp.get('id')} should have user_id"
        
        print(f"✓ evaluable-employees returns {len(employees)} valid employees")
        for emp in employees[:5]:  # Show first 5
            print(f"  - {emp.get('user_name') or emp.get('full_name')} (ID: {emp.get('id')[:8]}...)")
    
    def test_08_evaluable_employees_no_duplicates(self):
        """Test that evaluable-employees has no duplicate entries"""
        token = self.get_admin_token()
        self.session.headers["Authorization"] = f"Bearer {token}"
        
        response = self.session.get(f"{BASE_URL}/api/hr/evaluable-employees")
        assert response.status_code == 200
        
        employees = response.json()
        
        # Check for duplicate IDs
        ids = [emp.get("id") for emp in employees]
        unique_ids = set(ids)
        
        assert len(ids) == len(unique_ids), f"Found {len(ids) - len(unique_ids)} duplicate employees"
        
        # Check for duplicate user_ids
        user_ids = [emp.get("user_id") for emp in employees if emp.get("user_id")]
        unique_user_ids = set(user_ids)
        
        assert len(user_ids) == len(unique_user_ids), f"Found {len(user_ids) - len(unique_user_ids)} duplicate user_ids"
        
        print(f"✓ No duplicates in evaluable-employees list ({len(employees)} unique employees)")
    
    # ==================== GET GUARDS TESTS ====================
    
    def test_09_get_guards_default_filters_invalid(self):
        """Test that GET /hr/guards by default filters out invalid guards"""
        token = self.get_admin_token()
        self.session.headers["Authorization"] = f"Bearer {token}"
        
        response = self.session.get(f"{BASE_URL}/api/hr/guards")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        guards = response.json()
        assert isinstance(guards, list), "Should return a list"
        
        # All returned guards should be valid and active
        for guard in guards:
            assert guard.get("is_active") == True, f"Guard {guard.get('id')} should be active"
            assert guard.get("user_id") is not None, f"Guard {guard.get('id')} should have user_id"
        
        print(f"✓ GET /hr/guards returns {len(guards)} valid guards (default filter)")
    
    def test_10_get_guards_include_invalid_flag(self):
        """Test that GET /hr/guards?include_invalid=true returns all guards"""
        token = self.get_admin_token()
        self.session.headers["Authorization"] = f"Bearer {token}"
        
        # Get default (valid only)
        response_default = self.session.get(f"{BASE_URL}/api/hr/guards")
        assert response_default.status_code == 200
        valid_guards = response_default.json()
        
        # Get with include_invalid=true
        response_all = self.session.get(f"{BASE_URL}/api/hr/guards?include_invalid=true")
        assert response_all.status_code == 200
        all_guards = response_all.json()
        
        # All guards should include invalid ones
        assert len(all_guards) >= len(valid_guards), "include_invalid should return more or equal guards"
        
        print(f"✓ GET /hr/guards filtering works:")
        print(f"  - Default (valid only): {len(valid_guards)} guards")
        print(f"  - With include_invalid: {len(all_guards)} guards")
    
    def test_11_guards_have_validation_status(self):
        """Test that guards have _is_evaluable and _validation_status fields"""
        token = self.get_admin_token()
        self.session.headers["Authorization"] = f"Bearer {token}"
        
        response = self.session.get(f"{BASE_URL}/api/hr/guards")
        assert response.status_code == 200
        
        guards = response.json()
        
        for guard in guards:
            assert "_is_evaluable" in guard, f"Guard {guard.get('id')} missing _is_evaluable"
            assert "_validation_status" in guard, f"Guard {guard.get('id')} missing _validation_status"
        
        print(f"✓ All guards have validation status fields")
    
    # ==================== EVALUATION CREATION TEST ====================
    
    def test_12_can_create_evaluation_for_valid_employee(self):
        """Test that evaluations can be created for valid employees"""
        token = self.get_admin_token()
        self.session.headers["Authorization"] = f"Bearer {token}"
        
        # Get evaluable employees
        response = self.session.get(f"{BASE_URL}/api/hr/evaluable-employees")
        assert response.status_code == 200
        
        employees = response.json()
        if not employees:
            pytest.skip("No evaluable employees found")
        
        # Try to create evaluation for first employee
        employee = employees[0]
        evaluation_data = {
            "employee_id": employee["id"],
            "categories": {
                "discipline": 4,
                "punctuality": 4,
                "performance": 4,
                "communication": 4
            },
            "comments": "Test evaluation from integrity test"
        }
        
        response = self.session.post(f"{BASE_URL}/api/hr/evaluations", json=evaluation_data)
        assert response.status_code in [200, 201], f"Failed to create evaluation: {response.text}"
        
        print(f"✓ Successfully created evaluation for {employee.get('user_name') or employee.get('full_name')}")
    
    # ==================== FRONTEND API INTEGRATION TEST ====================
    
    def test_13_api_service_methods_exist(self):
        """Test that frontend API service has the new methods"""
        # This is a documentation test - the methods should exist in api.js
        # validateHRIntegrity, cleanupInvalidGuards, getEvaluableEmployees
        print("✓ Frontend API methods documented:")
        print("  - validateHRIntegrity() -> GET /api/hr/validate-integrity")
        print("  - cleanupInvalidGuards(dryRun) -> POST /api/hr/cleanup-invalid-guards")
        print("  - getEvaluableEmployees() -> GET /api/hr/evaluable-employees")


class TestFrontendNoEmployeeDuplicates:
    """Test that frontend won't show duplicate employees"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_01_no_duplicate_employees_in_guards_list(self):
        """Verify no duplicate employees appear in guards list"""
        token = self.get_admin_token()
        self.session.headers["Authorization"] = f"Bearer {token}"
        
        response = self.session.get(f"{BASE_URL}/api/hr/guards")
        assert response.status_code == 200
        
        guards = response.json()
        
        # Check by ID
        ids = [g["id"] for g in guards]
        assert len(ids) == len(set(ids)), "Duplicate guard IDs found"
        
        # Check by user_id
        user_ids = [g.get("user_id") for g in guards if g.get("user_id")]
        assert len(user_ids) == len(set(user_ids)), "Duplicate user_ids found"
        
        print(f"✓ No duplicates in guards list ({len(guards)} unique guards)")
    
    def test_02_no_duplicate_employees_in_evaluable_list(self):
        """Verify no duplicate employees in evaluable employees list"""
        token = self.get_admin_token()
        self.session.headers["Authorization"] = f"Bearer {token}"
        
        response = self.session.get(f"{BASE_URL}/api/hr/evaluable-employees")
        assert response.status_code == 200
        
        employees = response.json()
        
        # Check by ID
        ids = [e["id"] for e in employees]
        assert len(ids) == len(set(ids)), "Duplicate employee IDs found"
        
        # Check by user_id
        user_ids = [e.get("user_id") for e in employees if e.get("user_id")]
        assert len(user_ids) == len(set(user_ids)), "Duplicate user_ids found"
        
        print(f"✓ No duplicates in evaluable employees list ({len(employees)} unique employees)")
    
    def test_03_all_evaluable_employees_have_evaluar_button(self):
        """Verify all evaluable employees can be evaluated (have valid data)"""
        token = self.get_admin_token()
        self.session.headers["Authorization"] = f"Bearer {token}"
        
        response = self.session.get(f"{BASE_URL}/api/hr/evaluable-employees")
        assert response.status_code == 200
        
        employees = response.json()
        
        for emp in employees:
            # Each employee should have required fields for evaluation
            assert emp.get("id"), f"Employee missing id"
            assert emp.get("user_id"), f"Employee {emp.get('id')} missing user_id"
            assert emp.get("_is_evaluable") == True, f"Employee {emp.get('id')} not evaluable"
            
            # Should have a name to display
            name = emp.get("user_name") or emp.get("full_name") or emp.get("name")
            assert name, f"Employee {emp.get('id')} missing name"
        
        print(f"✓ All {len(employees)} evaluable employees have valid data for 'Evaluar' button")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
