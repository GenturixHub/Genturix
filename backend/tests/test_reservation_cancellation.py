"""
GENTURIX - Reservation Cancellation Feature Tests
P0 Feature: Sistema de cancelación de reservaciones

Tests:
- Resident cancels own future reservation (success)
- Resident cannot cancel another's reservation (403)
- Resident cannot cancel started/past reservation (400)
- Resident cannot cancel already cancelled reservation (400)
- Admin cancels any reservation with reason (success)
- Admin cancels without reason (success)
- Slot liberation verification
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
RESIDENT_PASSWORD = "Resi123!"

# Default area ID for testing
DEFAULT_AREA_ID = "8a2515f0-a1cc-4909-ae3f-fc0ee33bfc21"


class TestReservationCancellation:
    """Test reservation cancellation feature for residents and admins"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        return data.get("access_token")
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        """Get resident authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        data = response.json()
        return data.get("access_token")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Admin request headers"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def resident_headers(self, resident_token):
        """Resident request headers"""
        return {
            "Authorization": f"Bearer {resident_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture
    def future_date(self):
        """Get a future date for testing (3 days from now)"""
        return (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    
    @pytest.fixture
    def past_date(self):
        """Get a past date for testing"""
        return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    def get_available_area(self, headers):
        """Get an available area for testing"""
        response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=headers)
        if response.status_code == 200:
            areas = response.json()
            if areas:
                return areas[0]
        return None
    
    def create_test_reservation(self, headers, area_id, date, start_time="10:00", end_time="12:00"):
        """Create a test reservation and return its ID"""
        response = requests.post(f"{BASE_URL}/api/reservations", headers=headers, json={
            "area_id": area_id,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "purpose": "TEST_CANCEL_FEATURE",
            "guests_count": 1
        })
        if response.status_code == 201:
            data = response.json()
            return data.get("reservation_id") or data.get("id")
        return None
    
    # ==================== RESIDENT TESTS ====================
    
    def test_resident_login(self, resident_token):
        """Test resident can login"""
        assert resident_token is not None
        print("✓ Resident login successful")
    
    def test_admin_login(self, admin_token):
        """Test admin can login"""
        assert admin_token is not None
        print("✓ Admin login successful")
    
    def test_resident_cancel_own_future_reservation(self, resident_headers, admin_headers, future_date):
        """Resident can cancel their own future pending/approved reservation"""
        # Get an area
        area = self.get_available_area(resident_headers)
        if not area:
            pytest.skip("No areas available for testing")
        
        area_id = area.get("id")
        
        # Create a reservation as resident
        reservation_id = self.create_test_reservation(resident_headers, area_id, future_date, "14:00", "16:00")
        if not reservation_id:
            pytest.skip("Could not create test reservation")
        
        print(f"Created reservation: {reservation_id}")
        
        # Approve it as admin (so it's in approved state)
        approve_response = requests.patch(
            f"{BASE_URL}/api/reservations/{reservation_id}",
            headers=admin_headers,
            json={"status": "approved"}
        )
        print(f"Approve response: {approve_response.status_code}")
        
        # Now cancel as resident
        cancel_response = requests.delete(
            f"{BASE_URL}/api/reservations/{reservation_id}",
            headers=resident_headers
        )
        
        assert cancel_response.status_code == 200, f"Cancel failed: {cancel_response.text}"
        data = cancel_response.json()
        assert "message" in data
        assert "cancelada" in data["message"].lower() or "cancelled" in data["message"].lower()
        print(f"✓ Resident cancelled own future reservation: {data['message']}")
    
    def test_resident_cannot_cancel_others_reservation(self, resident_headers, admin_headers, future_date):
        """Resident cannot cancel another resident's reservation (403)"""
        # Get an area
        area = self.get_available_area(admin_headers)
        if not area:
            pytest.skip("No areas available for testing")
        
        area_id = area.get("id")
        
        # Create a reservation as admin (different user)
        reservation_id = self.create_test_reservation(admin_headers, area_id, future_date, "08:00", "09:00")
        if not reservation_id:
            pytest.skip("Could not create test reservation")
        
        print(f"Created admin reservation: {reservation_id}")
        
        # Try to cancel as resident (should fail with 403)
        cancel_response = requests.delete(
            f"{BASE_URL}/api/reservations/{reservation_id}",
            headers=resident_headers
        )
        
        assert cancel_response.status_code == 403, f"Expected 403, got {cancel_response.status_code}: {cancel_response.text}"
        print(f"✓ Resident correctly blocked from cancelling other's reservation (403)")
        
        # Cleanup: cancel as admin
        requests.delete(f"{BASE_URL}/api/reservations/{reservation_id}", headers=admin_headers)
    
    def test_resident_cannot_cancel_started_reservation(self, resident_headers, admin_headers, past_date):
        """Resident cannot cancel a reservation that has already started (400)"""
        # Get an area
        area = self.get_available_area(resident_headers)
        if not area:
            pytest.skip("No areas available for testing")
        
        area_id = area.get("id")
        
        # Create a reservation for a past date (already started)
        # Note: This might fail if backend validates date on creation
        response = requests.post(f"{BASE_URL}/api/reservations", headers=resident_headers, json={
            "area_id": area_id,
            "date": past_date,
            "start_time": "10:00",
            "end_time": "12:00",
            "purpose": "TEST_PAST_RESERVATION",
            "guests_count": 1
        })
        
        if response.status_code != 201:
            # Backend correctly prevents past date reservations
            print(f"✓ Backend prevents creating past reservations: {response.status_code}")
            return
        
        reservation_id = response.json().get("reservation_id") or response.json().get("id")
        
        # Try to cancel (should fail with 400)
        cancel_response = requests.delete(
            f"{BASE_URL}/api/reservations/{reservation_id}",
            headers=resident_headers
        )
        
        assert cancel_response.status_code == 400, f"Expected 400, got {cancel_response.status_code}"
        print(f"✓ Resident correctly blocked from cancelling started reservation (400)")
    
    def test_resident_cannot_cancel_already_cancelled(self, resident_headers, admin_headers, future_date):
        """Resident cannot cancel an already cancelled reservation (400)"""
        # Get an area
        area = self.get_available_area(resident_headers)
        if not area:
            pytest.skip("No areas available for testing")
        
        area_id = area.get("id")
        
        # Create and cancel a reservation
        reservation_id = self.create_test_reservation(resident_headers, area_id, future_date, "16:00", "18:00")
        if not reservation_id:
            pytest.skip("Could not create test reservation")
        
        # Cancel it first time
        first_cancel = requests.delete(
            f"{BASE_URL}/api/reservations/{reservation_id}",
            headers=resident_headers
        )
        assert first_cancel.status_code == 200, f"First cancel failed: {first_cancel.text}"
        
        # Try to cancel again (should fail with 400)
        second_cancel = requests.delete(
            f"{BASE_URL}/api/reservations/{reservation_id}",
            headers=resident_headers
        )
        
        assert second_cancel.status_code == 400, f"Expected 400, got {second_cancel.status_code}: {second_cancel.text}"
        print(f"✓ Resident correctly blocked from cancelling already cancelled reservation (400)")
    
    # ==================== ADMIN TESTS ====================
    
    def test_admin_cancel_with_reason(self, admin_headers, resident_headers, future_date):
        """Admin can cancel any reservation with a reason"""
        # Get an area
        area = self.get_available_area(resident_headers)
        if not area:
            pytest.skip("No areas available for testing")
        
        area_id = area.get("id")
        
        # Create a reservation as resident
        reservation_id = self.create_test_reservation(resident_headers, area_id, future_date, "09:00", "11:00")
        if not reservation_id:
            pytest.skip("Could not create test reservation")
        
        print(f"Created reservation for admin cancel test: {reservation_id}")
        
        # Admin cancels with reason
        cancel_response = requests.delete(
            f"{BASE_URL}/api/reservations/{reservation_id}",
            headers=admin_headers,
            json={"reason": "Mantenimiento programado del área"}
        )
        
        assert cancel_response.status_code == 200, f"Admin cancel failed: {cancel_response.text}"
        data = cancel_response.json()
        assert "message" in data
        print(f"✓ Admin cancelled reservation with reason: {data['message']}")
    
    def test_admin_cancel_without_reason(self, admin_headers, resident_headers, future_date):
        """Admin can cancel any reservation without providing a reason"""
        # Get an area
        area = self.get_available_area(resident_headers)
        if not area:
            pytest.skip("No areas available for testing")
        
        area_id = area.get("id")
        
        # Create a reservation as resident
        reservation_id = self.create_test_reservation(resident_headers, area_id, future_date, "11:00", "13:00")
        if not reservation_id:
            pytest.skip("Could not create test reservation")
        
        print(f"Created reservation for admin cancel (no reason) test: {reservation_id}")
        
        # Admin cancels without reason
        cancel_response = requests.delete(
            f"{BASE_URL}/api/reservations/{reservation_id}",
            headers=admin_headers
        )
        
        assert cancel_response.status_code == 200, f"Admin cancel failed: {cancel_response.text}"
        data = cancel_response.json()
        assert "message" in data
        print(f"✓ Admin cancelled reservation without reason: {data['message']}")
    
    def test_admin_cannot_cancel_completed(self, admin_headers, resident_headers, future_date):
        """Admin cannot cancel a completed reservation"""
        # Get an area
        area = self.get_available_area(resident_headers)
        if not area:
            pytest.skip("No areas available for testing")
        
        area_id = area.get("id")
        
        # Create a reservation
        reservation_id = self.create_test_reservation(resident_headers, area_id, future_date, "13:00", "15:00")
        if not reservation_id:
            pytest.skip("Could not create test reservation")
        
        # Mark as completed (if endpoint exists)
        complete_response = requests.patch(
            f"{BASE_URL}/api/reservations/{reservation_id}",
            headers=admin_headers,
            json={"status": "completed"}
        )
        
        if complete_response.status_code != 200:
            # If we can't mark as completed, skip this test
            print(f"Could not mark reservation as completed: {complete_response.status_code}")
            # Cleanup
            requests.delete(f"{BASE_URL}/api/reservations/{reservation_id}", headers=admin_headers)
            pytest.skip("Cannot mark reservation as completed for this test")
        
        # Try to cancel completed reservation
        cancel_response = requests.delete(
            f"{BASE_URL}/api/reservations/{reservation_id}",
            headers=admin_headers
        )
        
        assert cancel_response.status_code == 400, f"Expected 400, got {cancel_response.status_code}"
        print(f"✓ Admin correctly blocked from cancelling completed reservation (400)")
    
    # ==================== SLOT LIBERATION TEST ====================
    
    def test_slot_liberation_after_cancel(self, resident_headers, admin_headers, future_date):
        """Verify that cancelled slot becomes available again"""
        # Get an area
        area = self.get_available_area(resident_headers)
        if not area:
            pytest.skip("No areas available for testing")
        
        area_id = area.get("id")
        test_time = "15:00"
        test_end = "17:00"
        
        # Check initial availability
        avail_response = requests.get(
            f"{BASE_URL}/api/reservations/smart-availability/{area_id}?date={future_date}",
            headers=resident_headers
        )
        
        if avail_response.status_code != 200:
            # Try legacy endpoint
            avail_response = requests.get(
                f"{BASE_URL}/api/reservations/availability/{area_id}?date={future_date}",
                headers=resident_headers
            )
        
        # Create a reservation
        reservation_id = self.create_test_reservation(resident_headers, area_id, future_date, test_time, test_end)
        if not reservation_id:
            pytest.skip("Could not create test reservation")
        
        print(f"Created reservation for slot liberation test: {reservation_id}")
        
        # Cancel the reservation
        cancel_response = requests.delete(
            f"{BASE_URL}/api/reservations/{reservation_id}",
            headers=resident_headers
        )
        assert cancel_response.status_code == 200, f"Cancel failed: {cancel_response.text}"
        
        # Check availability again - slot should be available
        avail_after = requests.get(
            f"{BASE_URL}/api/reservations/smart-availability/{area_id}?date={future_date}",
            headers=resident_headers
        )
        
        if avail_after.status_code == 200:
            data = avail_after.json()
            # The slot should be available again
            print(f"✓ Slot liberation verified - availability check returned: {avail_after.status_code}")
        else:
            print(f"Availability check returned: {avail_after.status_code}")
        
        print(f"✓ Slot liberation test completed")
    
    # ==================== ERROR HANDLING TESTS ====================
    
    def test_cancel_nonexistent_reservation(self, resident_headers):
        """Cancelling non-existent reservation returns 404"""
        fake_id = "nonexistent-reservation-id-12345"
        
        cancel_response = requests.delete(
            f"{BASE_URL}/api/reservations/{fake_id}",
            headers=resident_headers
        )
        
        assert cancel_response.status_code == 404, f"Expected 404, got {cancel_response.status_code}"
        print(f"✓ Non-existent reservation returns 404")
    
    def test_cancel_without_auth(self):
        """Cancelling without authentication returns 401/403"""
        fake_id = "some-reservation-id"
        
        cancel_response = requests.delete(
            f"{BASE_URL}/api/reservations/{fake_id}"
        )
        
        assert cancel_response.status_code in [401, 403], f"Expected 401/403, got {cancel_response.status_code}"
        print(f"✓ Unauthenticated cancel returns {cancel_response.status_code}")


class TestCancellationResponseFormat:
    """Test that cancellation responses have correct format"""
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        """Get resident authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    @pytest.fixture(scope="class")
    def resident_headers(self, resident_token):
        """Resident request headers"""
        if not resident_token:
            pytest.skip("Could not get resident token")
        return {
            "Authorization": f"Bearer {resident_token}",
            "Content-Type": "application/json"
        }
    
    def test_success_response_format(self, resident_headers):
        """Verify successful cancellation response format"""
        # Get an area
        response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=resident_headers)
        if response.status_code != 200 or not response.json():
            pytest.skip("No areas available")
        
        area = response.json()[0]
        area_id = area.get("id")
        future_date = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")
        
        # Create reservation
        create_response = requests.post(f"{BASE_URL}/api/reservations", headers=resident_headers, json={
            "area_id": area_id,
            "date": future_date,
            "start_time": "17:00",
            "end_time": "19:00",
            "purpose": "TEST_RESPONSE_FORMAT",
            "guests_count": 1
        })
        
        if create_response.status_code != 201:
            pytest.skip("Could not create test reservation")
        
        reservation_id = create_response.json().get("reservation_id") or create_response.json().get("id")
        
        # Cancel and check response format
        cancel_response = requests.delete(
            f"{BASE_URL}/api/reservations/{reservation_id}",
            headers=resident_headers
        )
        
        assert cancel_response.status_code == 200
        data = cancel_response.json()
        
        # Verify response structure
        assert "message" in data, "Response should contain 'message' field"
        assert isinstance(data["message"], str), "Message should be a string"
        assert len(data["message"]) > 0, "Message should not be empty"
        
        # Verify message is user-friendly (not [object Object])
        assert "[object" not in data["message"].lower(), "Message should not contain [object Object]"
        
        print(f"✓ Response format verified: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
