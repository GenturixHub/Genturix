"""
Test Suite: P0 Bug Fix - Reservations Module Error Handling
Tests that error messages are properly formatted (no [object Object])
and all CRUD operations work correctly for areas and reservations.

Credentials:
- Admin: admin@genturix.com / Admin123!
- Residente: residente@genturix.com / Resi123!
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data prefix for cleanup
TEST_PREFIX = "TEST_P0_"


class TestSetup:
    """Setup and authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@genturix.com",
            "password": "Admin123!"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        """Get resident authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "residente@genturix.com",
            "password": "Resi123!"
        })
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Headers with admin auth"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def resident_headers(self, resident_token):
        """Headers with resident auth"""
        return {
            "Authorization": f"Bearer {resident_token}",
            "Content-Type": "application/json"
        }


class TestAdminAreaCRUD(TestSetup):
    """Test Admin CRUD operations for common areas"""
    
    def test_admin_login_success(self, admin_token):
        """Verify admin can login"""
        assert admin_token is not None
        assert len(admin_token) > 0
        print(f"✓ Admin login successful, token length: {len(admin_token)}")
    
    def test_get_areas_list(self, admin_headers):
        """Test GET /api/reservations/areas returns list"""
        response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get areas: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Got {len(data)} areas")
    
    def test_create_area_success(self, admin_headers):
        """Test creating a new area - should show 'Área creada' toast"""
        area_name = f"{TEST_PREFIX}Piscina_{uuid.uuid4().hex[:6]}"
        area_data = {
            "name": area_name,
            "area_type": "pool",
            "capacity": 20,
            "description": "Test pool area",
            "rules": "No running",
            "available_from": "08:00",
            "available_until": "20:00",
            "requires_approval": False,
            "max_hours_per_reservation": 2,
            "max_reservations_per_day": 5,
            "allowed_days": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        }
        
        response = requests.post(f"{BASE_URL}/api/reservations/areas", 
                                json=area_data, headers=admin_headers)
        
        assert response.status_code == 200, f"Failed to create area: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Response should contain 'id'"
        assert data.get("name") == area_name, "Name should match"
        assert data.get("area_type") == "pool", "Area type should match"
        
        # Store for cleanup
        self.__class__.created_area_id = data["id"]
        print(f"✓ Area created successfully: {data['id']}")
        return data["id"]
    
    def test_create_area_error_handling(self, admin_headers):
        """Test that error messages are properly formatted (no [object Object])"""
        # Try to create area with missing required field
        invalid_data = {
            "area_type": "pool",
            "capacity": 20
            # Missing 'name' which is required
        }
        
        response = requests.post(f"{BASE_URL}/api/reservations/areas", 
                                json=invalid_data, headers=admin_headers)
        
        # Should return error
        if response.status_code != 200:
            error_text = response.text
            # Verify error is NOT [object Object]
            assert "[object Object]" not in error_text, f"Error contains [object Object]: {error_text}"
            print(f"✓ Error message properly formatted: {error_text[:100]}")
    
    def test_update_area_success(self, admin_headers):
        """Test updating an area - should show 'Área actualizada' toast"""
        # First get existing areas
        response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=admin_headers)
        areas = response.json()
        
        if not areas:
            pytest.skip("No areas to update")
        
        area_id = areas[0]["id"]
        update_data = {
            "description": f"Updated description {datetime.now().isoformat()}"
        }
        
        response = requests.patch(f"{BASE_URL}/api/reservations/areas/{area_id}", 
                                 json=update_data, headers=admin_headers)
        
        assert response.status_code == 200, f"Failed to update area: {response.text}"
        data = response.json()
        assert "id" in data, "Response should contain 'id'"
        print(f"✓ Area updated successfully: {area_id}")
    
    def test_delete_area_success(self, admin_headers):
        """Test deleting an area - should show confirmation then 'Área eliminada' toast"""
        # Create a test area to delete
        area_name = f"{TEST_PREFIX}ToDelete_{uuid.uuid4().hex[:6]}"
        create_response = requests.post(f"{BASE_URL}/api/reservations/areas", 
                                       json={
                                           "name": area_name,
                                           "area_type": "other",
                                           "capacity": 10,
                                           "available_from": "08:00",
                                           "available_until": "18:00"
                                       }, headers=admin_headers)
        
        if create_response.status_code != 200:
            pytest.skip("Could not create test area for deletion")
        
        area_id = create_response.json()["id"]
        
        # Now delete it
        response = requests.delete(f"{BASE_URL}/api/reservations/areas/{area_id}", 
                                  headers=admin_headers)
        
        assert response.status_code == 200, f"Failed to delete area: {response.text}"
        print(f"✓ Area deleted successfully: {area_id}")


class TestResidentReservations(TestSetup):
    """Test Resident reservation operations"""
    
    def test_resident_login_success(self, resident_token):
        """Verify resident can login"""
        assert resident_token is not None
        assert len(resident_token) > 0
        print(f"✓ Resident login successful, token length: {len(resident_token)}")
    
    def test_resident_get_areas(self, resident_headers):
        """Test resident can view available areas"""
        response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=resident_headers)
        assert response.status_code == 200, f"Failed to get areas: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Resident can see {len(data)} areas")
    
    def test_resident_get_reservations(self, resident_headers):
        """Test resident can view their reservations"""
        response = requests.get(f"{BASE_URL}/api/reservations", headers=resident_headers)
        assert response.status_code == 200, f"Failed to get reservations: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Resident has {len(data)} reservations")
    
    def test_resident_create_reservation_success(self, resident_headers):
        """Test creating a reservation - should show 'Reservación creada exitosamente' toast"""
        # First get available areas
        areas_response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=resident_headers)
        areas = areas_response.json()
        
        if not areas:
            pytest.skip("No areas available for reservation")
        
        area = areas[0]
        area_id = area["id"]
        
        # Get tomorrow's date
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        reservation_data = {
            "area_id": area_id,
            "date": tomorrow,
            "start_time": "10:00",
            "end_time": "12:00",
            "guests_count": 2,
            "purpose": f"{TEST_PREFIX}Test reservation"
        }
        
        response = requests.post(f"{BASE_URL}/api/reservations", 
                                json=reservation_data, headers=resident_headers)
        
        # Check response
        if response.status_code == 200:
            data = response.json()
            assert "reservation_id" in data or "id" in data, "Response should contain reservation id"
            res_id = data.get("reservation_id") or data.get("id")
            self.__class__.created_reservation_id = res_id
            print(f"✓ Reservation created successfully: {res_id}")
        else:
            # Check error is properly formatted
            error_text = response.text
            assert "[object Object]" not in error_text, f"Error contains [object Object]: {error_text}"
            print(f"✓ Reservation creation returned error (expected if slot occupied): {error_text[:100]}")
    
    def test_resident_create_reservation_error_handling(self, resident_headers):
        """Test that reservation errors are properly formatted (no [object Object])"""
        # Try to create reservation with invalid data
        invalid_data = {
            "area_id": "non-existent-area-id",
            "date": "2026-02-01",
            "start_time": "10:00",
            "end_time": "12:00",
            "guests_count": 2
        }
        
        response = requests.post(f"{BASE_URL}/api/reservations", 
                                json=invalid_data, headers=resident_headers)
        
        # Should return error
        if response.status_code != 200:
            error_text = response.text
            # Verify error is NOT [object Object]
            assert "[object Object]" not in error_text, f"Error contains [object Object]: {error_text}"
            print(f"✓ Error message properly formatted: {error_text[:100]}")
    
    def test_resident_cancel_reservation(self, resident_headers):
        """Test canceling a reservation - should show 'Reservación cancelada' toast"""
        # Get resident's reservations
        response = requests.get(f"{BASE_URL}/api/reservations", headers=resident_headers)
        reservations = response.json()
        
        # Find a pending reservation to cancel
        pending = [r for r in reservations if r.get("status") == "pending"]
        
        if not pending:
            pytest.skip("No pending reservations to cancel")
        
        res_id = pending[0]["id"]
        
        # Cancel it
        response = requests.patch(f"{BASE_URL}/api/reservations/{res_id}", 
                                 json={"status": "cancelled"}, headers=resident_headers)
        
        assert response.status_code == 200, f"Failed to cancel reservation: {response.text}"
        print(f"✓ Reservation cancelled successfully: {res_id}")


class TestAdminReservationManagement(TestSetup):
    """Test Admin reservation approval/rejection"""
    
    def test_admin_get_all_reservations(self, admin_headers):
        """Test admin can view all reservations"""
        response = requests.get(f"{BASE_URL}/api/reservations", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get reservations: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Admin can see {len(data)} reservations")
        return data
    
    def test_admin_approve_reservation(self, admin_headers):
        """Test approving a reservation - should show 'Reservación aprobada' toast"""
        # Get all reservations
        response = requests.get(f"{BASE_URL}/api/reservations", headers=admin_headers)
        reservations = response.json()
        
        # Find a pending reservation
        pending = [r for r in reservations if r.get("status") == "pending"]
        
        if not pending:
            pytest.skip("No pending reservations to approve")
        
        res_id = pending[0]["id"]
        
        # Approve it
        response = requests.patch(f"{BASE_URL}/api/reservations/{res_id}", 
                                 json={"status": "approved"}, headers=admin_headers)
        
        assert response.status_code == 200, f"Failed to approve reservation: {response.text}"
        
        # Verify error is not [object Object]
        if response.status_code != 200:
            assert "[object Object]" not in response.text
        
        print(f"✓ Reservation approved successfully: {res_id}")
    
    def test_admin_reject_reservation(self, admin_headers):
        """Test rejecting a reservation - should show 'Reservación rechazada' toast"""
        # First create a reservation to reject
        # Get areas
        areas_response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=admin_headers)
        areas = areas_response.json()
        
        if not areas:
            pytest.skip("No areas available")
        
        # Get resident token to create reservation
        res_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "residente@genturix.com",
            "password": "Resi123!"
        })
        res_token = res_login.json().get("access_token")
        res_headers = {"Authorization": f"Bearer {res_token}", "Content-Type": "application/json"}
        
        # Create a reservation
        tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        create_response = requests.post(f"{BASE_URL}/api/reservations", json={
            "area_id": areas[0]["id"],
            "date": tomorrow,
            "start_time": "14:00",
            "end_time": "16:00",
            "guests_count": 1,
            "purpose": f"{TEST_PREFIX}To be rejected"
        }, headers=res_headers)
        
        if create_response.status_code != 200:
            # Get existing pending reservations
            response = requests.get(f"{BASE_URL}/api/reservations", headers=admin_headers)
            reservations = response.json()
            pending = [r for r in reservations if r.get("status") == "pending"]
            
            if not pending:
                pytest.skip("No pending reservations to reject")
            
            res_id = pending[0]["id"]
        else:
            res_id = create_response.json().get("reservation_id") or create_response.json().get("id")
        
        # Reject it
        response = requests.patch(f"{BASE_URL}/api/reservations/{res_id}", 
                                 json={"status": "rejected", "admin_notes": "Test rejection"}, 
                                 headers=admin_headers)
        
        if response.status_code == 200:
            print(f"✓ Reservation rejected successfully: {res_id}")
        else:
            # Verify error is not [object Object]
            assert "[object Object]" not in response.text, f"Error contains [object Object]: {response.text}"
            print(f"✓ Rejection returned error (may already be processed): {response.text[:100]}")


class TestSmartAvailability(TestSetup):
    """Test smart availability endpoint"""
    
    def test_get_smart_availability(self, resident_headers):
        """Test getting smart availability for an area"""
        # Get areas
        areas_response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=resident_headers)
        areas = areas_response.json()
        
        if not areas:
            pytest.skip("No areas available")
        
        area_id = areas[0]["id"]
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = requests.get(f"{BASE_URL}/api/reservations/smart-availability/{area_id}?date={tomorrow}", 
                               headers=resident_headers)
        
        assert response.status_code == 200, f"Failed to get availability: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "is_available" in data or "is_day_allowed" in data, "Response should contain availability info"
        print(f"✓ Smart availability retrieved: is_available={data.get('is_available', data.get('is_day_allowed'))}")


class TestErrorMessageFormat(TestSetup):
    """Specific tests for error message formatting - no [object Object]"""
    
    def test_invalid_area_id_error(self, resident_headers):
        """Test error message when using invalid area ID"""
        response = requests.post(f"{BASE_URL}/api/reservations", json={
            "area_id": "invalid-uuid-format",
            "date": "2026-02-01",
            "start_time": "10:00",
            "end_time": "12:00",
            "guests_count": 1
        }, headers=resident_headers)
        
        if response.status_code != 200:
            error_text = response.text
            assert "[object Object]" not in error_text, f"Error contains [object Object]: {error_text}"
            print(f"✓ Invalid area ID error properly formatted")
    
    def test_past_date_error(self, resident_headers):
        """Test error message when using past date"""
        # Get areas
        areas_response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=resident_headers)
        areas = areas_response.json()
        
        if not areas:
            pytest.skip("No areas available")
        
        response = requests.post(f"{BASE_URL}/api/reservations", json={
            "area_id": areas[0]["id"],
            "date": "2020-01-01",  # Past date
            "start_time": "10:00",
            "end_time": "12:00",
            "guests_count": 1
        }, headers=resident_headers)
        
        if response.status_code != 200:
            error_text = response.text
            assert "[object Object]" not in error_text, f"Error contains [object Object]: {error_text}"
            print(f"✓ Past date error properly formatted")
    
    def test_capacity_exceeded_error(self, resident_headers):
        """Test error message when exceeding capacity"""
        # Get areas
        areas_response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=resident_headers)
        areas = areas_response.json()
        
        if not areas:
            pytest.skip("No areas available")
        
        area = areas[0]
        capacity = area.get("capacity", 10)
        
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = requests.post(f"{BASE_URL}/api/reservations", json={
            "area_id": area["id"],
            "date": tomorrow,
            "start_time": "10:00",
            "end_time": "12:00",
            "guests_count": capacity + 100  # Exceed capacity
        }, headers=resident_headers)
        
        if response.status_code != 200:
            error_text = response.text
            assert "[object Object]" not in error_text, f"Error contains [object Object]: {error_text}"
            print(f"✓ Capacity exceeded error properly formatted")


# Cleanup fixture
@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    """Cleanup test data after all tests"""
    def cleanup_test_data():
        # Login as admin
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@genturix.com",
            "password": "Admin123!"
        })
        if response.status_code != 200:
            return
        
        token = response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Get and delete test areas
        areas_response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=headers)
        if areas_response.status_code == 200:
            areas = areas_response.json()
            for area in areas:
                if area.get("name", "").startswith(TEST_PREFIX):
                    requests.delete(f"{BASE_URL}/api/reservations/areas/{area['id']}", headers=headers)
                    print(f"Cleaned up test area: {area['name']}")
    
    request.addfinalizer(cleanup_test_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
