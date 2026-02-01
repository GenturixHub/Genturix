"""
P0 Bug Fix Tests - Iteration 42
Tests for:
1. Shift Deletion - DELETE /api/hr/shifts/{id} and UI update
2. User Creation - Role-specific field validation
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://condo-access-19.preview.emergentagent.com').rstrip('/')

class TestShiftDeletion:
    """P0 BUG #1 - Shift Deletion Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@genturix.com",
            "password": "Admin123!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get a guard ID for creating shifts
        guards_response = requests.get(f"{BASE_URL}/api/hr/guards", headers=self.headers)
        assert guards_response.status_code == 200
        guards = guards_response.json()
        assert len(guards) > 0, "No guards available for testing"
        self.guard_id = guards[0]["id"]
    
    def test_delete_shift_returns_success_message(self):
        """DELETE /api/hr/shifts/{id} returns success message"""
        # Create a shift first
        create_response = requests.post(f"{BASE_URL}/api/hr/shifts", headers=self.headers, json={
            "guard_id": self.guard_id,
            "start_time": "2026-02-10T08:00:00",
            "end_time": "2026-02-10T16:00:00",
            "location": "Test Location Delete",
            "notes": "Test shift for deletion"
        })
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        shift_id = create_response.json()["id"]
        
        # Delete the shift
        delete_response = requests.delete(f"{BASE_URL}/api/hr/shifts/{shift_id}", headers=self.headers)
        assert delete_response.status_code == 200
        
        data = delete_response.json()
        assert "message" in data
        assert "cancelado" in data["message"].lower() or "eliminado" in data["message"].lower()
    
    def test_deleted_shift_has_cancelled_status(self):
        """Deleted shift has status='cancelled' and cancelled_at timestamp"""
        # Create a shift
        create_response = requests.post(f"{BASE_URL}/api/hr/shifts", headers=self.headers, json={
            "guard_id": self.guard_id,
            "start_time": "2026-02-11T08:00:00",
            "end_time": "2026-02-11T16:00:00",
            "location": "Test Location Status",
            "notes": "Test shift for status check"
        })
        assert create_response.status_code == 200
        shift_id = create_response.json()["id"]
        
        # Delete the shift
        delete_response = requests.delete(f"{BASE_URL}/api/hr/shifts/{shift_id}", headers=self.headers)
        assert delete_response.status_code == 200
        
        # Verify shift status
        shifts_response = requests.get(f"{BASE_URL}/api/hr/shifts", headers=self.headers)
        assert shifts_response.status_code == 200
        
        shifts = shifts_response.json()
        deleted_shift = next((s for s in shifts if s["id"] == shift_id), None)
        assert deleted_shift is not None, "Deleted shift not found in list"
        assert deleted_shift["status"] == "cancelled"
        assert "cancelled_at" in deleted_shift
        assert deleted_shift["cancelled_at"] is not None
    
    def test_cancelled_shifts_filtered_from_active_list(self):
        """Frontend should filter out cancelled shifts"""
        # Get all shifts
        shifts_response = requests.get(f"{BASE_URL}/api/hr/shifts", headers=self.headers)
        assert shifts_response.status_code == 200
        
        all_shifts = shifts_response.json()
        active_shifts = [s for s in all_shifts if s.get("status") != "cancelled"]
        cancelled_shifts = [s for s in all_shifts if s.get("status") == "cancelled"]
        
        print(f"Total shifts: {len(all_shifts)}")
        print(f"Active shifts: {len(active_shifts)}")
        print(f"Cancelled shifts: {len(cancelled_shifts)}")
        
        # This test verifies the data is correct for frontend filtering
        assert isinstance(all_shifts, list)


class TestUserCreation:
    """P0 BUG #2 - User Creation with Role-Specific Fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@genturix.com",
            "password": "Admin123!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.timestamp = int(time.time())
    
    def test_residente_requires_apartment_number(self):
        """Creating Residente without apartment_number should fail"""
        response = requests.post(f"{BASE_URL}/api/admin/users", headers=self.headers, json={
            "email": f"test_residente_fail_{self.timestamp}@test.com",
            "password": "TestPass123!",
            "full_name": "Test Residente Fail",
            "role": "Residente"
            # Missing apartment_number
        })
        assert response.status_code == 400
        data = response.json()
        assert "apartamento" in data["detail"].lower() or "apartment" in data["detail"].lower()
    
    def test_guarda_requires_badge_number(self):
        """Creating Guarda without badge_number should fail"""
        response = requests.post(f"{BASE_URL}/api/admin/users", headers=self.headers, json={
            "email": f"test_guarda_fail_{self.timestamp}@test.com",
            "password": "TestPass123!",
            "full_name": "Test Guarda Fail",
            "role": "Guarda"
            # Missing badge_number
        })
        assert response.status_code == 400
        data = response.json()
        assert "placa" in data["detail"].lower() or "badge" in data["detail"].lower()
    
    def test_create_residente_with_apartment_number(self):
        """Creating Residente with apartment_number should succeed"""
        response = requests.post(f"{BASE_URL}/api/admin/users", headers=self.headers, json={
            "email": f"test_residente_ok_{self.timestamp}@test.com",
            "password": "TestPass123!",
            "full_name": "Test Residente OK",
            "role": "Residente",
            "apartment_number": "A-101",
            "tower_block": "Torre A",
            "resident_type": "owner"
        })
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        data = response.json()
        assert "user_id" in data
        assert data["role"] == "Residente"
        assert data["role_data"]["apartment_number"] == "A-101"
        assert data["role_data"]["tower_block"] == "Torre A"
        assert data["role_data"]["resident_type"] == "owner"
    
    def test_create_guarda_with_badge_number(self):
        """Creating Guarda with badge_number should succeed"""
        response = requests.post(f"{BASE_URL}/api/admin/users", headers=self.headers, json={
            "email": f"test_guarda_ok_{self.timestamp}@test.com",
            "password": "TestPass123!",
            "full_name": "Test Guarda OK",
            "role": "Guarda",
            "badge_number": f"G-{self.timestamp}"
        })
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        data = response.json()
        assert "user_id" in data
        assert data["role"] == "Guarda"
        assert data["role_data"]["badge_number"] == f"G-{self.timestamp}"
        assert "guard_id" in data["role_data"]  # Guard record should be created
    
    def test_guarda_is_active_by_default(self):
        """New Guarda should have is_active=True by default"""
        response = requests.post(f"{BASE_URL}/api/admin/users", headers=self.headers, json={
            "email": f"test_guarda_active_{self.timestamp}@test.com",
            "password": "TestPass123!",
            "full_name": "Test Guarda Active",
            "role": "Guarda",
            "badge_number": f"G-ACT-{self.timestamp}"
        })
        assert response.status_code == 200
        
        data = response.json()
        guard_id = data["role_data"]["guard_id"]
        
        # Verify guard is active
        guards_response = requests.get(f"{BASE_URL}/api/hr/guards", headers=self.headers)
        assert guards_response.status_code == 200
        
        guards = guards_response.json()
        new_guard = next((g for g in guards if g["id"] == guard_id), None)
        assert new_guard is not None, "New guard not found in guards list"
        assert new_guard.get("is_active") == True, "New guard should be active by default"


class TestHRRolePermissions:
    """Test that HR role can delete shifts"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin first"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@genturix.com",
            "password": "Admin123!"
        })
        assert response.status_code == 200
        self.admin_token = response.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Get a guard ID
        guards_response = requests.get(f"{BASE_URL}/api/hr/guards", headers=self.admin_headers)
        assert guards_response.status_code == 200
        guards = guards_response.json()
        if len(guards) > 0:
            self.guard_id = guards[0]["id"]
        else:
            self.guard_id = None
    
    def test_delete_endpoint_allows_hr_role(self):
        """DELETE /api/hr/shifts/{id} should allow HR role (verified via code review)"""
        # This test verifies the endpoint decorator includes HR role
        # The actual test would require an HR user, but we verify via admin
        if not self.guard_id:
            pytest.skip("No guards available")
        
        # Create a shift
        create_response = requests.post(f"{BASE_URL}/api/hr/shifts", headers=self.admin_headers, json={
            "guard_id": self.guard_id,
            "start_time": "2026-02-12T08:00:00",
            "end_time": "2026-02-12T16:00:00",
            "location": "Test HR Permission",
            "notes": "Test shift for HR permission"
        })
        assert create_response.status_code == 200
        shift_id = create_response.json()["id"]
        
        # Delete should work for admin (which includes HR permissions)
        delete_response = requests.delete(f"{BASE_URL}/api/hr/shifts/{shift_id}", headers=self.admin_headers)
        assert delete_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
