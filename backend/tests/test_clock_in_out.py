"""
Test Clock In/Out Functionality for GENTURIX Guard System
Tests: Clock in with valid shift, clock in without shift, double clock in,
       clock out without clock in, clock out completes shift, multi-tenant isolation
"""
import pytest
import requests
import os
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
GUARD_MAIN_CONDO = {"email": "guarda1@genturix.com", "password": "Guard123!"}
ADMIN_MAIN_CONDO = {"email": "admin@genturix.com", "password": "Admin123!"}
GUARD_ID_MAIN = "da613be1-40de-44e4-9c6e-394b06441e5b"
CONDOMINIUM_MAIN = "9156da0f-2836-4162-b921-d307be8608a0"
CONDOMINIUM_ISOLATION = "4af52281-bab1-420c-be06-f5055f2cace3"


class TestClockInOut:
    """Test Clock In/Out functionality for guards"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get tokens and reset clock state"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as guard
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=GUARD_MAIN_CONDO)
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        self.guard_token = response.json()["access_token"]
        self.guard_user = response.json()["user"]
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_MAIN_CONDO)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        self.admin_token = response.json()["access_token"]
        
        # Reset clock state - clock out if clocked in
        self._reset_clock_state()
        
        yield
        
        # Cleanup - clock out if still clocked in
        self._reset_clock_state()
    
    def _reset_clock_state(self):
        """Reset clock state by clocking out if currently clocked in"""
        status = self.session.get(
            f"{BASE_URL}/api/hr/clock/status",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        ).json()
        
        if status.get("is_clocked_in"):
            self.session.post(
                f"{BASE_URL}/api/hr/clock",
                headers={"Authorization": f"Bearer {self.guard_token}"},
                json={"type": "OUT"}
            )
    
    def _create_shift_for_guard(self, guard_id, start_offset_minutes=0, duration_hours=6):
        """Create a shift for the guard starting at specified offset from now"""
        now = datetime.now(timezone.utc)
        start_time = (now + timedelta(minutes=start_offset_minutes)).isoformat()
        end_time = (now + timedelta(minutes=start_offset_minutes, hours=duration_hours)).isoformat()
        
        response = self.session.post(
            f"{BASE_URL}/api/hr/shifts",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json={
                "guard_id": guard_id,
                "start_time": start_time,
                "end_time": end_time,
                "location": "Test Location"
            }
        )
        return response
    
    def _delete_shift(self, shift_id):
        """Delete/cancel a shift"""
        self.session.delete(
            f"{BASE_URL}/api/hr/shifts/{shift_id}",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
    
    # ==================== TEST 1: Clock In with Valid Shift ====================
    def test_clock_in_with_valid_shift_returns_shift_id(self):
        """
        Test: Clock in with valid shift must succeed and return shift_id
        Expected: 200 OK, response contains shift_id
        """
        # First create a shift for the guard (starting now)
        shift_response = self._create_shift_for_guard(GUARD_ID_MAIN, start_offset_minutes=-5)
        
        if shift_response.status_code != 201:
            # Shift might already exist, check my-shift
            my_shift = self.session.get(
                f"{BASE_URL}/api/guard/my-shift",
                headers={"Authorization": f"Bearer {self.guard_token}"}
            ).json()
            
            if not my_shift.get("current_shift") and not my_shift.get("can_clock_in"):
                pytest.skip("No valid shift available for testing")
        
        # Clock IN
        response = self.session.post(
            f"{BASE_URL}/api/hr/clock",
            headers={"Authorization": f"Bearer {self.guard_token}"},
            json={"type": "IN"}
        )
        
        print(f"Clock IN response: {response.status_code} - {response.text}")
        
        assert response.status_code == 200, f"Clock IN failed: {response.text}"
        data = response.json()
        
        # Verify response contains shift_id
        assert "shift_id" in data, "Response should contain shift_id"
        assert data["shift_id"] is not None, "shift_id should not be None"
        assert data["type"] == "IN", "Type should be IN"
        assert "message" in data, "Response should contain message"
        
        print(f"✓ Clock IN successful with shift_id: {data['shift_id']}")
    
    # ==================== TEST 2: Clock In Without Shift ====================
    def test_clock_in_without_shift_fails_400(self):
        """
        Test: Clock in without an assigned shift must fail with 400
        Expected: 400 Bad Request
        """
        # First, we need a guard without a shift
        # For this test, we'll try to clock in when there's no current shift
        # Check current shift status
        my_shift = self.session.get(
            f"{BASE_URL}/api/guard/my-shift",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        ).json()
        
        # If guard has a current shift, we can't test this scenario directly
        # We'll verify the logic by checking the can_clock_in flag
        if my_shift.get("current_shift") or my_shift.get("can_clock_in"):
            # Guard has a valid shift, skip this test
            pytest.skip("Guard has an active shift - cannot test no-shift scenario")
        
        # Try to clock in without shift
        response = self.session.post(
            f"{BASE_URL}/api/hr/clock",
            headers={"Authorization": f"Bearer {self.guard_token}"},
            json={"type": "IN"}
        )
        
        print(f"Clock IN without shift response: {response.status_code} - {response.text}")
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Response should contain error detail"
        
        print(f"✓ Clock IN without shift correctly rejected: {data['detail']}")
    
    # ==================== TEST 3: Double Clock In ====================
    def test_double_clock_in_fails_400(self):
        """
        Test: Double clock in (already clocked in) must fail with 400
        Expected: 400 Bad Request with appropriate message
        """
        # First clock in
        response1 = self.session.post(
            f"{BASE_URL}/api/hr/clock",
            headers={"Authorization": f"Bearer {self.guard_token}"},
            json={"type": "IN"}
        )
        
        if response1.status_code != 200:
            pytest.skip(f"Initial clock in failed: {response1.text}")
        
        print(f"First clock IN: {response1.status_code}")
        
        # Try to clock in again (should fail)
        response2 = self.session.post(
            f"{BASE_URL}/api/hr/clock",
            headers={"Authorization": f"Bearer {self.guard_token}"},
            json={"type": "IN"}
        )
        
        print(f"Double clock IN response: {response2.status_code} - {response2.text}")
        
        assert response2.status_code == 400, f"Expected 400 for double clock in, got {response2.status_code}"
        data = response2.json()
        assert "detail" in data, "Response should contain error detail"
        assert "entrada" in data["detail"].lower() or "salida" in data["detail"].lower(), \
            "Error message should mention entry/exit"
        
        print(f"✓ Double clock IN correctly rejected: {data['detail']}")
    
    # ==================== TEST 4: Clock Out Without Clock In ====================
    def test_clock_out_without_clock_in_fails_400(self):
        """
        Test: Clock out without having clocked in must fail with 400
        Expected: 400 Bad Request
        """
        # Ensure we're not clocked in
        self._reset_clock_state()
        
        # Verify not clocked in
        status = self.session.get(
            f"{BASE_URL}/api/hr/clock/status",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        ).json()
        
        # If there are no logs today, or last action was OUT, we can test
        if status.get("is_clocked_in"):
            pytest.skip("Guard is still clocked in after reset")
        
        # Try to clock out without being clocked in
        response = self.session.post(
            f"{BASE_URL}/api/hr/clock",
            headers={"Authorization": f"Bearer {self.guard_token}"},
            json={"type": "OUT"}
        )
        
        print(f"Clock OUT without IN response: {response.status_code} - {response.text}")
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Response should contain error detail"
        
        print(f"✓ Clock OUT without IN correctly rejected: {data['detail']}")
    
    # ==================== TEST 5: Clock Out Completes Shift ====================
    def test_clock_out_completes_shift_correctly(self):
        """
        Test: Clock out should complete the shift (status=completed)
        Expected: Shift status changes to 'completed'
        """
        # First clock in
        clock_in_response = self.session.post(
            f"{BASE_URL}/api/hr/clock",
            headers={"Authorization": f"Bearer {self.guard_token}"},
            json={"type": "IN"}
        )
        
        if clock_in_response.status_code != 200:
            pytest.skip(f"Clock in failed: {clock_in_response.text}")
        
        shift_id = clock_in_response.json().get("shift_id")
        print(f"Clocked IN with shift_id: {shift_id}")
        
        # Now clock out
        clock_out_response = self.session.post(
            f"{BASE_URL}/api/hr/clock",
            headers={"Authorization": f"Bearer {self.guard_token}"},
            json={"type": "OUT"}
        )
        
        print(f"Clock OUT response: {clock_out_response.status_code} - {clock_out_response.text}")
        
        assert clock_out_response.status_code == 200, f"Clock OUT failed: {clock_out_response.text}"
        data = clock_out_response.json()
        
        # Verify hours_worked is calculated
        assert "hours_worked" in data, "Response should contain hours_worked"
        assert data["hours_worked"] is not None, "hours_worked should be calculated"
        
        # Verify shift is completed by checking my-shift
        my_shift = self.session.get(
            f"{BASE_URL}/api/guard/my-shift",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        ).json()
        
        # The current_shift should now be None or the shift should be completed
        if shift_id:
            # Get shift details from admin
            shifts_response = self.session.get(
                f"{BASE_URL}/api/hr/shifts",
                headers={"Authorization": f"Bearer {self.admin_token}"}
            )
            
            if shifts_response.status_code == 200:
                shifts = shifts_response.json()
                completed_shift = next((s for s in shifts if s["id"] == shift_id), None)
                if completed_shift:
                    assert completed_shift["status"] == "completed", \
                        f"Shift status should be 'completed', got '{completed_shift['status']}'"
                    print(f"✓ Shift {shift_id} status is 'completed'")
        
        print(f"✓ Clock OUT completed successfully, hours_worked: {data['hours_worked']}")


class TestMultiTenantIsolation:
    """Test multi-tenant isolation for guard clock functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get tokens"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as guard from main condo
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=GUARD_MAIN_CONDO)
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        self.guard_token = response.json()["access_token"]
        self.guard_user = response.json()["user"]
        
        yield
    
    def test_guard_sees_only_own_condominium_data(self):
        """
        Test: Guard should only see data from their own condominium
        Expected: History and shifts are filtered by condominium_id
        """
        # Get guard history
        history_response = self.session.get(
            f"{BASE_URL}/api/guard/history",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        assert history_response.status_code == 200, f"History request failed: {history_response.text}"
        history = history_response.json()
        
        # Verify all history entries belong to guard's condominium
        guard_condo_id = self.guard_user.get("condominium_id")
        
        for entry in history:
            if entry.get("condominium_id"):
                assert entry["condominium_id"] == guard_condo_id, \
                    f"History entry from wrong condo: {entry['condominium_id']} != {guard_condo_id}"
        
        print(f"✓ Guard history correctly filtered by condominium ({len(history)} entries)")
    
    def test_guard_my_shift_scoped_by_condominium(self):
        """
        Test: My-shift endpoint should only return shifts from guard's condominium
        Expected: current_shift and next_shift belong to guard's condominium
        """
        response = self.session.get(
            f"{BASE_URL}/api/guard/my-shift",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        assert response.status_code == 200, f"My-shift request failed: {response.text}"
        data = response.json()
        
        guard_condo_id = self.guard_user.get("condominium_id")
        
        # Check current_shift
        if data.get("current_shift"):
            assert data["current_shift"].get("condominium_id") == guard_condo_id, \
                "Current shift should belong to guard's condominium"
            print(f"✓ Current shift belongs to correct condominium")
        
        # Check next_shift
        if data.get("next_shift"):
            assert data["next_shift"].get("condominium_id") == guard_condo_id, \
                "Next shift should belong to guard's condominium"
            print(f"✓ Next shift belongs to correct condominium")
        
        print(f"✓ My-shift correctly scoped by condominium")


class TestClockStatusEndpoint:
    """Test clock status endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get tokens"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as guard
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=GUARD_MAIN_CONDO)
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        self.guard_token = response.json()["access_token"]
        
        yield
    
    def test_clock_status_returns_correct_state(self):
        """
        Test: Clock status endpoint returns correct is_clocked_in state
        """
        response = self.session.get(
            f"{BASE_URL}/api/hr/clock/status",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        assert response.status_code == 200, f"Clock status failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "is_clocked_in" in data, "Response should contain is_clocked_in"
        assert "employee_id" in data, "Response should contain employee_id"
        assert "employee_name" in data, "Response should contain employee_name"
        
        print(f"✓ Clock status: is_clocked_in={data['is_clocked_in']}, employee={data['employee_name']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
