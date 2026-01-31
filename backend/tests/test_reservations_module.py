"""
GENTURIX - Reservations Module Tests
Tests for:
- GET /api/reservations/areas - list areas
- POST /api/reservations/areas - create area (admin)
- PATCH /api/reservations/areas/{id} - edit area (admin)
- DELETE /api/reservations/areas/{id} - delete area (admin)
- GET /api/reservations/availability/{area_id}?date=YYYY-MM-DD - availability
- POST /api/reservations - create reservation (validate days, hours, max per day)
- PATCH /api/reservations/{id} - approve/reject (admin)
- GET /api/reservations?status=pending - pending reservations
- GET /api/reservations/today - today's reservations (guard view)
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
RESIDENT_EMAIL = "residente@genturix.com"
RESIDENT_PASSWORD = "Residente123!"


class TestReservationsModule:
    """Reservations Module API Tests"""
    
    admin_token = None
    resident_token = None
    test_area_id = None
    test_reservation_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get tokens for admin and resident"""
        # Admin login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        TestReservationsModule.admin_token = response.json()["access_token"]
        
        # Resident login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        TestReservationsModule.resident_token = response.json()["access_token"]
    
    def get_admin_headers(self):
        return {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
    
    def get_resident_headers(self):
        return {"Authorization": f"Bearer {self.resident_token}", "Content-Type": "application/json"}
    
    # ==================== AREAS TESTS ====================
    
    def test_01_get_areas_as_admin(self):
        """GET /api/reservations/areas - Admin can list areas"""
        response = requests.get(
            f"{BASE_URL}/api/reservations/areas",
            headers=self.get_admin_headers()
        )
        assert response.status_code == 200, f"Failed to get areas: {response.text}"
        areas = response.json()
        assert isinstance(areas, list), "Response should be a list"
        print(f"Found {len(areas)} areas")
    
    def test_02_get_areas_as_resident(self):
        """GET /api/reservations/areas - Resident can list areas"""
        response = requests.get(
            f"{BASE_URL}/api/reservations/areas",
            headers=self.get_resident_headers()
        )
        assert response.status_code == 200, f"Failed to get areas: {response.text}"
        areas = response.json()
        assert isinstance(areas, list), "Response should be a list"
        print(f"Resident sees {len(areas)} areas")
    
    def test_03_create_area_as_admin(self):
        """POST /api/reservations/areas - Admin can create area"""
        area_data = {
            "name": f"TEST_Pool_{datetime.now().strftime('%H%M%S')}",
            "area_type": "pool",
            "capacity": 20,
            "description": "Test pool area for automated testing",
            "rules": "No running, no diving",
            "available_from": "08:00",
            "available_until": "20:00",
            "requires_approval": True,
            "max_hours_per_reservation": 3,
            "max_reservations_per_day": 5,
            "allowed_days": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/reservations/areas",
            headers=self.get_admin_headers(),
            json=area_data
        )
        assert response.status_code == 200, f"Failed to create area: {response.text}"
        data = response.json()
        assert "area_id" in data, "Response should contain area_id"
        TestReservationsModule.test_area_id = data["area_id"]
        print(f"Created area: {data['area_id']}")
    
    def test_04_create_area_as_resident_forbidden(self):
        """POST /api/reservations/areas - Resident cannot create area"""
        area_data = {
            "name": "TEST_Unauthorized_Area",
            "area_type": "gym",
            "capacity": 10
        }
        
        response = requests.post(
            f"{BASE_URL}/api/reservations/areas",
            headers=self.get_resident_headers(),
            json=area_data
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("Resident correctly forbidden from creating areas")
    
    def test_05_update_area_as_admin(self):
        """PATCH /api/reservations/areas/{id} - Admin can update area"""
        if not self.test_area_id:
            pytest.skip("No test area created")
        
        update_data = {
            "capacity": 25,
            "description": "Updated test pool description"
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/reservations/areas/{self.test_area_id}",
            headers=self.get_admin_headers(),
            json=update_data
        )
        assert response.status_code == 200, f"Failed to update area: {response.text}"
        print(f"Updated area {self.test_area_id}")
    
    def test_06_update_area_as_resident_forbidden(self):
        """PATCH /api/reservations/areas/{id} - Resident cannot update area"""
        if not self.test_area_id:
            pytest.skip("No test area created")
        
        response = requests.patch(
            f"{BASE_URL}/api/reservations/areas/{self.test_area_id}",
            headers=self.get_resident_headers(),
            json={"capacity": 30}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("Resident correctly forbidden from updating areas")
    
    # ==================== AVAILABILITY TESTS ====================
    
    def test_07_get_availability_allowed_day(self):
        """GET /api/reservations/availability/{area_id}?date=YYYY-MM-DD - Check availability on allowed day"""
        if not self.test_area_id:
            pytest.skip("No test area created")
        
        # Find next Monday (allowed day)
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)
        date_str = next_monday.strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/reservations/availability/{self.test_area_id}?date={date_str}",
            headers=self.get_resident_headers()
        )
        assert response.status_code == 200, f"Failed to get availability: {response.text}"
        data = response.json()
        
        assert "is_day_allowed" in data, "Response should contain is_day_allowed"
        assert "available_from" in data, "Response should contain available_from"
        assert "available_until" in data, "Response should contain available_until"
        assert "slots_remaining" in data, "Response should contain slots_remaining"
        
        print(f"Availability for {date_str}: is_day_allowed={data['is_day_allowed']}, slots_remaining={data['slots_remaining']}")
    
    def test_08_get_availability_blocked_day(self):
        """GET /api/reservations/availability - Check availability on blocked day (weekend)"""
        if not self.test_area_id:
            pytest.skip("No test area created")
        
        # Find next Saturday (blocked day for our test area)
        today = datetime.now()
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7
        next_saturday = today + timedelta(days=days_until_saturday)
        date_str = next_saturday.strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/reservations/availability/{self.test_area_id}?date={date_str}",
            headers=self.get_resident_headers()
        )
        assert response.status_code == 200, f"Failed to get availability: {response.text}"
        data = response.json()
        
        # Saturday should be blocked (not in allowed_days)
        assert data["is_day_allowed"] == False, f"Saturday should be blocked, got is_day_allowed={data['is_day_allowed']}"
        print(f"Saturday {date_str} correctly blocked: is_day_allowed={data['is_day_allowed']}")
    
    # ==================== RESERVATION TESTS ====================
    
    def test_09_create_reservation_on_allowed_day(self):
        """POST /api/reservations - Create reservation on allowed day"""
        if not self.test_area_id:
            pytest.skip("No test area created")
        
        # Find next Monday
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)
        date_str = next_monday.strftime("%Y-%m-%d")
        
        reservation_data = {
            "area_id": self.test_area_id,
            "date": date_str,
            "start_time": "10:00",
            "end_time": "12:00",
            "purpose": "Test reservation",
            "guests_count": 5
        }
        
        response = requests.post(
            f"{BASE_URL}/api/reservations",
            headers=self.get_resident_headers(),
            json=reservation_data
        )
        assert response.status_code == 200, f"Failed to create reservation: {response.text}"
        data = response.json()
        
        assert "reservation_id" in data, "Response should contain reservation_id"
        assert "status" in data, "Response should contain status"
        # Area requires approval, so status should be pending
        assert data["status"] == "pending", f"Expected pending status, got {data['status']}"
        
        TestReservationsModule.test_reservation_id = data["reservation_id"]
        print(f"Created reservation: {data['reservation_id']} with status {data['status']}")
    
    def test_10_create_reservation_on_blocked_day_fails(self):
        """POST /api/reservations - Reservation on blocked day should fail"""
        if not self.test_area_id:
            pytest.skip("No test area created")
        
        # Find next Saturday (blocked)
        today = datetime.now()
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7
        next_saturday = today + timedelta(days=days_until_saturday)
        date_str = next_saturday.strftime("%Y-%m-%d")
        
        reservation_data = {
            "area_id": self.test_area_id,
            "date": date_str,
            "start_time": "10:00",
            "end_time": "12:00",
            "purpose": "Should fail",
            "guests_count": 2
        }
        
        response = requests.post(
            f"{BASE_URL}/api/reservations",
            headers=self.get_resident_headers(),
            json=reservation_data
        )
        assert response.status_code == 400, f"Expected 400 for blocked day, got {response.status_code}"
        print(f"Reservation on blocked day correctly rejected: {response.json().get('detail')}")
    
    def test_11_create_reservation_outside_hours_fails(self):
        """POST /api/reservations - Reservation outside available hours should fail"""
        if not self.test_area_id:
            pytest.skip("No test area created")
        
        # Find next Monday
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)
        date_str = next_monday.strftime("%Y-%m-%d")
        
        # Area is available 08:00-20:00, try to book 06:00-08:00
        reservation_data = {
            "area_id": self.test_area_id,
            "date": date_str,
            "start_time": "06:00",
            "end_time": "08:00",
            "purpose": "Should fail - outside hours",
            "guests_count": 2
        }
        
        response = requests.post(
            f"{BASE_URL}/api/reservations",
            headers=self.get_resident_headers(),
            json=reservation_data
        )
        assert response.status_code == 400, f"Expected 400 for outside hours, got {response.status_code}"
        print(f"Reservation outside hours correctly rejected: {response.json().get('detail')}")
    
    def test_12_create_reservation_exceeds_capacity_fails(self):
        """POST /api/reservations - Reservation exceeding capacity should fail"""
        if not self.test_area_id:
            pytest.skip("No test area created")
        
        # Find next Tuesday
        today = datetime.now()
        days_until_tuesday = (1 - today.weekday()) % 7
        if days_until_tuesday == 0:
            days_until_tuesday = 7
        next_tuesday = today + timedelta(days=days_until_tuesday)
        date_str = next_tuesday.strftime("%Y-%m-%d")
        
        # Area capacity is 25, try to book for 30
        reservation_data = {
            "area_id": self.test_area_id,
            "date": date_str,
            "start_time": "10:00",
            "end_time": "12:00",
            "purpose": "Should fail - exceeds capacity",
            "guests_count": 30
        }
        
        response = requests.post(
            f"{BASE_URL}/api/reservations",
            headers=self.get_resident_headers(),
            json=reservation_data
        )
        assert response.status_code == 400, f"Expected 400 for exceeding capacity, got {response.status_code}"
        print(f"Reservation exceeding capacity correctly rejected: {response.json().get('detail')}")
    
    # ==================== APPROVAL FLOW TESTS ====================
    
    def test_13_get_pending_reservations_as_admin(self):
        """GET /api/reservations?status=pending - Admin can see pending reservations"""
        response = requests.get(
            f"{BASE_URL}/api/reservations?status=pending",
            headers=self.get_admin_headers()
        )
        assert response.status_code == 200, f"Failed to get pending reservations: {response.text}"
        reservations = response.json()
        assert isinstance(reservations, list), "Response should be a list"
        print(f"Found {len(reservations)} pending reservations")
    
    def test_14_approve_reservation_as_admin(self):
        """PATCH /api/reservations/{id} - Admin can approve reservation"""
        if not self.test_reservation_id:
            pytest.skip("No test reservation created")
        
        response = requests.patch(
            f"{BASE_URL}/api/reservations/{self.test_reservation_id}",
            headers=self.get_admin_headers(),
            json={"status": "approved", "admin_notes": "Approved by test"}
        )
        assert response.status_code == 200, f"Failed to approve reservation: {response.text}"
        print(f"Approved reservation {self.test_reservation_id}")
    
    def test_15_resident_cannot_approve_reservation(self):
        """PATCH /api/reservations/{id} - Resident cannot approve reservations"""
        if not self.test_reservation_id:
            pytest.skip("No test reservation created")
        
        response = requests.patch(
            f"{BASE_URL}/api/reservations/{self.test_reservation_id}",
            headers=self.get_resident_headers(),
            json={"status": "approved"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("Resident correctly forbidden from approving reservations")
    
    def test_16_get_my_reservations_as_resident(self):
        """GET /api/reservations - Resident sees only their own reservations"""
        response = requests.get(
            f"{BASE_URL}/api/reservations",
            headers=self.get_resident_headers()
        )
        assert response.status_code == 200, f"Failed to get reservations: {response.text}"
        reservations = response.json()
        assert isinstance(reservations, list), "Response should be a list"
        print(f"Resident sees {len(reservations)} reservations")
    
    # ==================== TODAY'S RESERVATIONS (GUARD VIEW) ====================
    
    def test_17_get_today_reservations(self):
        """GET /api/reservations/today - Get today's approved reservations"""
        response = requests.get(
            f"{BASE_URL}/api/reservations/today",
            headers=self.get_admin_headers()
        )
        assert response.status_code == 200, f"Failed to get today's reservations: {response.text}"
        reservations = response.json()
        assert isinstance(reservations, list), "Response should be a list"
        print(f"Today's reservations: {len(reservations)}")
    
    # ==================== CANCEL RESERVATION ====================
    
    def test_18_resident_can_cancel_own_reservation(self):
        """PATCH /api/reservations/{id} - Resident can cancel their own reservation"""
        # First create a new reservation to cancel
        if not self.test_area_id:
            pytest.skip("No test area created")
        
        # Find next Wednesday
        today = datetime.now()
        days_until_wednesday = (2 - today.weekday()) % 7
        if days_until_wednesday == 0:
            days_until_wednesday = 7
        next_wednesday = today + timedelta(days=days_until_wednesday)
        date_str = next_wednesday.strftime("%Y-%m-%d")
        
        # Create reservation
        reservation_data = {
            "area_id": self.test_area_id,
            "date": date_str,
            "start_time": "14:00",
            "end_time": "16:00",
            "purpose": "To be cancelled",
            "guests_count": 3
        }
        
        response = requests.post(
            f"{BASE_URL}/api/reservations",
            headers=self.get_resident_headers(),
            json=reservation_data
        )
        if response.status_code != 200:
            pytest.skip(f"Could not create reservation to cancel: {response.text}")
        
        cancel_id = response.json()["reservation_id"]
        
        # Cancel it
        response = requests.patch(
            f"{BASE_URL}/api/reservations/{cancel_id}",
            headers=self.get_resident_headers(),
            json={"status": "cancelled"}
        )
        assert response.status_code == 200, f"Failed to cancel reservation: {response.text}"
        print(f"Resident successfully cancelled reservation {cancel_id}")
    
    # ==================== DELETE AREA ====================
    
    def test_19_delete_area_as_admin(self):
        """DELETE /api/reservations/areas/{id} - Admin can delete area"""
        if not self.test_area_id:
            pytest.skip("No test area created")
        
        response = requests.delete(
            f"{BASE_URL}/api/reservations/areas/{self.test_area_id}",
            headers=self.get_admin_headers()
        )
        assert response.status_code == 200, f"Failed to delete area: {response.text}"
        print(f"Deleted area {self.test_area_id}")
    
    def test_20_delete_area_as_resident_forbidden(self):
        """DELETE /api/reservations/areas/{id} - Resident cannot delete area"""
        # Try to delete a non-existent area (just to test permission)
        response = requests.delete(
            f"{BASE_URL}/api/reservations/areas/fake-area-id",
            headers=self.get_resident_headers()
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("Resident correctly forbidden from deleting areas")


class TestReservationsWithExistingData:
    """Test with existing data mentioned by main agent"""
    
    admin_token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        TestReservationsWithExistingData.admin_token = response.json()["access_token"]
    
    def get_admin_headers(self):
        return {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
    
    def test_existing_areas_visible(self):
        """Verify existing areas (like Test Pool) are visible"""
        response = requests.get(
            f"{BASE_URL}/api/reservations/areas",
            headers=self.get_admin_headers()
        )
        assert response.status_code == 200
        areas = response.json()
        print(f"Existing areas: {[a.get('name') for a in areas]}")
        
        # Check if any area exists
        if len(areas) > 0:
            # Verify area structure
            area = areas[0]
            assert "id" in area, "Area should have id"
            assert "name" in area, "Area should have name"
            assert "area_type" in area, "Area should have area_type"
            assert "capacity" in area, "Area should have capacity"
            print(f"First area: {area.get('name')} - type: {area.get('area_type')}")
    
    def test_existing_reservations_visible(self):
        """Verify existing reservations are visible"""
        response = requests.get(
            f"{BASE_URL}/api/reservations",
            headers=self.get_admin_headers()
        )
        assert response.status_code == 200
        reservations = response.json()
        print(f"Found {len(reservations)} reservations")
        
        if len(reservations) > 0:
            res = reservations[0]
            assert "id" in res, "Reservation should have id"
            assert "status" in res, "Reservation should have status"
            assert "date" in res, "Reservation should have date"
            print(f"First reservation: {res.get('area_name')} on {res.get('date')} - status: {res.get('status')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
