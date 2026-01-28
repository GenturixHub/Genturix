"""
GENTURIX HR Module Tests - Iteration 8
Tests for Shifts, Clock In/Out, and Absences CRUD operations
"""
import pytest
import requests
import os
from datetime import datetime, timedelta
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@genturix.com", "password": "Admin123!"}
GUARD_CREDS = {"email": "guarda1@genturix.com", "password": "Guard123!"}


class TestAuth:
    """Authentication tests"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert "Administrador" in data["user"]["roles"]
        print(f"✓ Admin login successful: {data['user']['email']}")
    
    def test_guard_login(self):
        """Test guard login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=GUARD_CREDS)
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert "Guarda" in data["user"]["roles"]
        print(f"✓ Guard login successful: {data['user']['email']}")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def guard_token():
    """Get guard auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=GUARD_CREDS)
    if response.status_code != 200:
        pytest.skip(f"Guard login failed: {response.text}")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Admin request headers"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def guard_headers(guard_token):
    """Guard request headers"""
    return {"Authorization": f"Bearer {guard_token}", "Content-Type": "application/json"}


# ==================== GUARDS TESTS ====================
class TestGuards:
    """HR Guards CRUD tests"""
    
    def test_get_guards_list(self, admin_headers):
        """GET /api/hr/guards - List all guards"""
        response = requests.get(f"{BASE_URL}/api/hr/guards", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get guards: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/hr/guards - Found {len(data)} guards")
        return data
    
    def test_get_guard_by_id(self, admin_headers):
        """GET /api/hr/guards/{id} - Get single guard"""
        # First get list
        guards = requests.get(f"{BASE_URL}/api/hr/guards", headers=admin_headers).json()
        if not guards:
            pytest.skip("No guards found to test")
        
        guard_id = guards[0]["id"]
        response = requests.get(f"{BASE_URL}/api/hr/guards/{guard_id}", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get guard: {response.text}"
        data = response.json()
        assert data["id"] == guard_id
        print(f"✓ GET /api/hr/guards/{guard_id} - Guard: {data.get('user_name')}")
    
    def test_get_guard_not_found(self, admin_headers):
        """GET /api/hr/guards/{id} - 404 for non-existent guard"""
        response = requests.get(f"{BASE_URL}/api/hr/guards/nonexistent-id", headers=admin_headers)
        assert response.status_code == 404
        print("✓ GET /api/hr/guards/nonexistent - Returns 404")


# ==================== SHIFTS TESTS ====================
class TestShifts:
    """HR Shifts CRUD tests"""
    
    @pytest.fixture(scope="class")
    def test_guard_id(self, admin_headers):
        """Get a guard ID for testing"""
        guards = requests.get(f"{BASE_URL}/api/hr/guards", headers=admin_headers).json()
        if not guards:
            pytest.skip("No guards found for shift testing")
        return guards[0]["id"]
    
    def test_create_shift_success(self, admin_headers, test_guard_id):
        """POST /api/hr/shifts - Create shift with valid data"""
        # Create shift far in the future to avoid conflicts with existing shifts
        # Use a random offset to ensure uniqueness
        import random
        future_day = datetime.now() + timedelta(days=100 + random.randint(1, 100))
        start_time = future_day.replace(hour=8, minute=0, second=0, microsecond=0).isoformat()
        end_time = future_day.replace(hour=16, minute=0, second=0, microsecond=0).isoformat()
        
        shift_data = {
            "guard_id": test_guard_id,
            "start_time": start_time,
            "end_time": end_time,
            "location": "TEST_Entrada Principal",
            "notes": "Test shift created by pytest"
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/shifts", json=shift_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to create shift: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["guard_id"] == test_guard_id
        assert data["status"] == "scheduled"
        assert data["location"] == "TEST_Entrada Principal"
        print(f"✓ POST /api/hr/shifts - Created shift: {data['id']}")
    
    def test_create_shift_invalid_guard(self, admin_headers):
        """POST /api/hr/shifts - 404 for non-existent guard"""
        tomorrow = datetime.now() + timedelta(days=2)
        shift_data = {
            "guard_id": "nonexistent-guard-id",
            "start_time": tomorrow.replace(hour=8).isoformat(),
            "end_time": tomorrow.replace(hour=16).isoformat(),
            "location": "Test Location"
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/shifts", json=shift_data, headers=admin_headers)
        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"].lower()
        print("✓ POST /api/hr/shifts - Returns 404 for invalid guard")
    
    def test_create_shift_invalid_times(self, admin_headers, test_guard_id):
        """POST /api/hr/shifts - 400 for end_time before start_time"""
        tomorrow = datetime.now() + timedelta(days=3)
        shift_data = {
            "guard_id": test_guard_id,
            "start_time": tomorrow.replace(hour=16).isoformat(),  # Later
            "end_time": tomorrow.replace(hour=8).isoformat(),     # Earlier
            "location": "Test Location"
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/shifts", json=shift_data, headers=admin_headers)
        assert response.status_code == 400
        assert "inicio" in response.json()["detail"].lower() or "anterior" in response.json()["detail"].lower()
        print("✓ POST /api/hr/shifts - Returns 400 for invalid times")
    
    def test_get_shifts_list(self, admin_headers):
        """GET /api/hr/shifts - List all shifts"""
        response = requests.get(f"{BASE_URL}/api/hr/shifts", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get shifts: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/hr/shifts - Found {len(data)} shifts")
    
    def test_get_shifts_with_status_filter(self, admin_headers):
        """GET /api/hr/shifts?status=scheduled - Filter by status"""
        response = requests.get(f"{BASE_URL}/api/hr/shifts?status=scheduled", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        for shift in data:
            assert shift["status"] == "scheduled"
        print(f"✓ GET /api/hr/shifts?status=scheduled - Found {len(data)} scheduled shifts")
    
    def test_get_shifts_with_guard_filter(self, admin_headers, test_guard_id):
        """GET /api/hr/shifts?guard_id=X - Filter by guard"""
        response = requests.get(f"{BASE_URL}/api/hr/shifts?guard_id={test_guard_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        for shift in data:
            assert shift["guard_id"] == test_guard_id
        print(f"✓ GET /api/hr/shifts?guard_id={test_guard_id[:8]}... - Found {len(data)} shifts")
    
    def test_update_shift(self, admin_headers, test_guard_id):
        """PUT /api/hr/shifts/{id} - Update shift"""
        # First create a shift far in the future
        import random
        day_after = datetime.now() + timedelta(days=200 + random.randint(1, 50))
        shift_data = {
            "guard_id": test_guard_id,
            "start_time": day_after.replace(hour=9).isoformat(),
            "end_time": day_after.replace(hour=17).isoformat(),
            "location": "TEST_Original Location"
        }
        create_resp = requests.post(f"{BASE_URL}/api/hr/shifts", json=shift_data, headers=admin_headers)
        assert create_resp.status_code == 200, f"Failed to create shift for update test: {create_resp.text}"
        shift_id = create_resp.json()["id"]
        
        # Update the shift
        update_data = {
            "location": "TEST_Updated Location",
            "notes": "Updated by pytest"
        }
        response = requests.put(f"{BASE_URL}/api/hr/shifts/{shift_id}", json=update_data, headers=admin_headers)
        assert response.status_code == 200, f"Failed to update shift: {response.text}"
        data = response.json()
        assert data["location"] == "TEST_Updated Location"
        assert data["notes"] == "Updated by pytest"
        print(f"✓ PUT /api/hr/shifts/{shift_id[:8]}... - Updated successfully")
    
    def test_update_shift_invalid_status(self, admin_headers, test_guard_id):
        """PUT /api/hr/shifts/{id} - 400 for invalid status"""
        # Create a shift first far in the future
        import random
        day_after = datetime.now() + timedelta(days=250 + random.randint(1, 50))
        shift_data = {
            "guard_id": test_guard_id,
            "start_time": day_after.replace(hour=10).isoformat(),
            "end_time": day_after.replace(hour=18).isoformat(),
            "location": "TEST_Status Test"
        }
        create_resp = requests.post(f"{BASE_URL}/api/hr/shifts", json=shift_data, headers=admin_headers)
        assert create_resp.status_code == 200, f"Failed to create shift: {create_resp.text}"
        shift_id = create_resp.json()["id"]
        
        # Try invalid status
        update_data = {"status": "invalid_status"}
        response = requests.put(f"{BASE_URL}/api/hr/shifts/{shift_id}", json=update_data, headers=admin_headers)
        assert response.status_code == 400
        print("✓ PUT /api/hr/shifts - Returns 400 for invalid status")
    
    def test_delete_shift(self, admin_headers, test_guard_id):
        """DELETE /api/hr/shifts/{id} - Soft delete (cancel) shift"""
        # Create a shift first far in the future
        import random
        day_after = datetime.now() + timedelta(days=300 + random.randint(1, 50))
        shift_data = {
            "guard_id": test_guard_id,
            "start_time": day_after.replace(hour=7).isoformat(),
            "end_time": day_after.replace(hour=15).isoformat(),
            "location": "TEST_To Be Deleted"
        }
        create_resp = requests.post(f"{BASE_URL}/api/hr/shifts", json=shift_data, headers=admin_headers)
        assert create_resp.status_code == 200, f"Failed to create shift: {create_resp.text}"
        shift_id = create_resp.json()["id"]
        
        # Delete the shift
        response = requests.delete(f"{BASE_URL}/api/hr/shifts/{shift_id}", headers=admin_headers)
        assert response.status_code == 200, f"Failed to delete shift: {response.text}"
        
        # Verify it's cancelled (soft delete)
        get_resp = requests.get(f"{BASE_URL}/api/hr/shifts/{shift_id}", headers=admin_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "cancelled"
        print(f"✓ DELETE /api/hr/shifts/{shift_id[:8]}... - Soft deleted (cancelled)")
    
    def test_delete_shift_not_found(self, admin_headers):
        """DELETE /api/hr/shifts/{id} - 404 for non-existent shift"""
        response = requests.delete(f"{BASE_URL}/api/hr/shifts/nonexistent-id", headers=admin_headers)
        assert response.status_code == 404
        print("✓ DELETE /api/hr/shifts/nonexistent - Returns 404")


# ==================== CLOCK IN/OUT TESTS ====================
class TestClockInOut:
    """HR Clock In/Out tests"""
    
    def test_get_clock_status(self, guard_headers):
        """GET /api/hr/clock/status - Get current clock status"""
        response = requests.get(f"{BASE_URL}/api/hr/clock/status", headers=guard_headers)
        assert response.status_code == 200, f"Failed to get clock status: {response.text}"
        data = response.json()
        assert "is_clocked_in" in data
        print(f"✓ GET /api/hr/clock/status - Clocked in: {data.get('is_clocked_in')}")
        return data
    
    def test_clock_in_success(self, guard_headers):
        """POST /api/hr/clock - Clock IN"""
        # First check status
        status_resp = requests.get(f"{BASE_URL}/api/hr/clock/status", headers=guard_headers)
        status = status_resp.json()
        
        if status.get("is_clocked_in"):
            # Clock out first
            requests.post(f"{BASE_URL}/api/hr/clock", json={"type": "OUT"}, headers=guard_headers)
        
        # Now clock in
        response = requests.post(f"{BASE_URL}/api/hr/clock", json={"type": "IN"}, headers=guard_headers)
        assert response.status_code == 200, f"Failed to clock in: {response.text}"
        data = response.json()
        assert data["type"] == "IN"
        assert "message" in data
        assert "entrada" in data["message"].lower()
        print(f"✓ POST /api/hr/clock (IN) - {data['message']}")
    
    def test_clock_in_double_prevention(self, guard_headers):
        """POST /api/hr/clock - Prevent double clock-in"""
        # Ensure clocked in
        status_resp = requests.get(f"{BASE_URL}/api/hr/clock/status", headers=guard_headers)
        if not status_resp.json().get("is_clocked_in"):
            requests.post(f"{BASE_URL}/api/hr/clock", json={"type": "IN"}, headers=guard_headers)
        
        # Try to clock in again
        response = requests.post(f"{BASE_URL}/api/hr/clock", json={"type": "IN"}, headers=guard_headers)
        assert response.status_code == 400
        assert "entrada" in response.json()["detail"].lower() or "salida" in response.json()["detail"].lower()
        print("✓ POST /api/hr/clock (IN) - Prevents double clock-in")
    
    def test_clock_out_success(self, guard_headers):
        """POST /api/hr/clock - Clock OUT"""
        # Ensure clocked in first
        status_resp = requests.get(f"{BASE_URL}/api/hr/clock/status", headers=guard_headers)
        if not status_resp.json().get("is_clocked_in"):
            requests.post(f"{BASE_URL}/api/hr/clock", json={"type": "IN"}, headers=guard_headers)
        
        # Now clock out
        response = requests.post(f"{BASE_URL}/api/hr/clock", json={"type": "OUT"}, headers=guard_headers)
        assert response.status_code == 200, f"Failed to clock out: {response.text}"
        data = response.json()
        assert data["type"] == "OUT"
        assert "message" in data
        assert "salida" in data["message"].lower()
        print(f"✓ POST /api/hr/clock (OUT) - {data['message']}")
    
    def test_clock_out_without_clock_in(self, guard_headers):
        """POST /api/hr/clock - Prevent clock-out without clock-in"""
        # Ensure not clocked in
        status_resp = requests.get(f"{BASE_URL}/api/hr/clock/status", headers=guard_headers)
        if status_resp.json().get("is_clocked_in"):
            requests.post(f"{BASE_URL}/api/hr/clock", json={"type": "OUT"}, headers=guard_headers)
        
        # Try to clock out again
        response = requests.post(f"{BASE_URL}/api/hr/clock", json={"type": "OUT"}, headers=guard_headers)
        assert response.status_code == 400
        assert "entrada" in response.json()["detail"].lower()
        print("✓ POST /api/hr/clock (OUT) - Requires prior clock-in")
    
    def test_clock_invalid_type(self, guard_headers):
        """POST /api/hr/clock - 400 for invalid type"""
        response = requests.post(f"{BASE_URL}/api/hr/clock", json={"type": "INVALID"}, headers=guard_headers)
        assert response.status_code == 400
        print("✓ POST /api/hr/clock - Returns 400 for invalid type")
    
    def test_get_clock_history(self, admin_headers):
        """GET /api/hr/clock/history - Get clock history"""
        response = requests.get(f"{BASE_URL}/api/hr/clock/history", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get clock history: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/hr/clock/history - Found {len(data)} records")
    
    def test_guard_sees_own_history(self, guard_headers):
        """GET /api/hr/clock/history - Guard sees only own history"""
        response = requests.get(f"{BASE_URL}/api/hr/clock/history", headers=guard_headers)
        assert response.status_code == 200
        data = response.json()
        # All records should be for the same employee
        if data:
            employee_ids = set(log["employee_id"] for log in data)
            assert len(employee_ids) <= 1, "Guard should only see own history"
        print(f"✓ GET /api/hr/clock/history (guard) - Sees only own records")


# ==================== ABSENCES TESTS ====================
class TestAbsences:
    """HR Absences CRUD tests"""
    
    def test_create_absence_success(self, guard_headers):
        """POST /api/hr/absences - Create absence request"""
        # Use future dates with random offset to avoid conflicts
        import random
        offset = random.randint(100, 200)
        start_date = (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=offset + 2)).strftime("%Y-%m-%d")
        
        absence_data = {
            "reason": "TEST_Vacaciones familiares",
            "type": "vacaciones",
            "start_date": start_date,
            "end_date": end_date,
            "notes": "Test absence created by pytest"
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/absences", json=absence_data, headers=guard_headers)
        assert response.status_code == 200, f"Failed to create absence: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
        assert data["type"] == "vacaciones"
        print(f"✓ POST /api/hr/absences - Created: {data['id']}")
    
    def test_create_absence_invalid_dates(self, guard_headers):
        """POST /api/hr/absences - 400 for end_date before start_date"""
        absence_data = {
            "reason": "Test",
            "type": "personal",
            "start_date": "2026-03-15",
            "end_date": "2026-03-10"  # Before start
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/absences", json=absence_data, headers=guard_headers)
        assert response.status_code == 400
        assert "fecha" in response.json()["detail"].lower()
        print("✓ POST /api/hr/absences - Returns 400 for invalid dates")
    
    def test_create_absence_invalid_type(self, guard_headers):
        """POST /api/hr/absences - 400 for invalid type"""
        absence_data = {
            "reason": "Test",
            "type": "invalid_type",
            "start_date": "2026-04-01",
            "end_date": "2026-04-02"
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/absences", json=absence_data, headers=guard_headers)
        assert response.status_code == 400
        assert "tipo" in response.json()["detail"].lower() or "inválido" in response.json()["detail"].lower()
        print("✓ POST /api/hr/absences - Returns 400 for invalid type")
    
    def test_get_absences_list(self, admin_headers):
        """GET /api/hr/absences - List all absences"""
        response = requests.get(f"{BASE_URL}/api/hr/absences", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get absences: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/hr/absences - Found {len(data)} absences")
    
    def test_get_absences_with_status_filter(self, admin_headers):
        """GET /api/hr/absences?status=pending - Filter by status"""
        response = requests.get(f"{BASE_URL}/api/hr/absences?status=pending", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        for absence in data:
            assert absence["status"] == "pending"
        print(f"✓ GET /api/hr/absences?status=pending - Found {len(data)} pending")
    
    def test_approve_absence(self, admin_headers, guard_headers):
        """PUT /api/hr/absences/{id}/approve - Admin approves absence"""
        # Create a new absence to approve with random offset
        import random
        offset = random.randint(200, 300)
        start_date = (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=offset + 1)).strftime("%Y-%m-%d")
        
        absence_data = {
            "reason": "TEST_To be approved",
            "type": "permiso_medico",
            "start_date": start_date,
            "end_date": end_date
        }
        create_resp = requests.post(f"{BASE_URL}/api/hr/absences", json=absence_data, headers=guard_headers)
        assert create_resp.status_code == 200, f"Failed to create absence: {create_resp.text}"
        absence_id = create_resp.json()["id"]
        
        # Approve it
        response = requests.put(f"{BASE_URL}/api/hr/absences/{absence_id}/approve", headers=admin_headers)
        assert response.status_code == 200, f"Failed to approve: {response.text}"
        data = response.json()
        assert data["status"] == "approved"
        assert "approved_by" in data
        print(f"✓ PUT /api/hr/absences/{absence_id[:8]}../approve - Approved")
    
    def test_reject_absence(self, admin_headers, guard_headers):
        """PUT /api/hr/absences/{id}/reject - Admin rejects absence"""
        # Create a new absence to reject with random offset
        import random
        offset = random.randint(300, 400)
        start_date = (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=offset + 1)).strftime("%Y-%m-%d")
        
        absence_data = {
            "reason": "TEST_To be rejected",
            "type": "personal",
            "start_date": start_date,
            "end_date": end_date
        }
        create_resp = requests.post(f"{BASE_URL}/api/hr/absences", json=absence_data, headers=guard_headers)
        assert create_resp.status_code == 200, f"Failed to create absence: {create_resp.text}"
        absence_id = create_resp.json()["id"]
        
        # Reject it
        response = requests.put(f"{BASE_URL}/api/hr/absences/{absence_id}/reject", headers=admin_headers)
        assert response.status_code == 200, f"Failed to reject: {response.text}"
        data = response.json()
        assert data["status"] == "rejected"
        assert "rejected_by" in data
        print(f"✓ PUT /api/hr/absences/{absence_id[:8]}../reject - Rejected")
    
    def test_approve_already_processed(self, admin_headers, guard_headers):
        """PUT /api/hr/absences/{id}/approve - 400 for already processed"""
        # Create and approve an absence with random offset
        import random
        offset = random.randint(400, 500)
        start_date = (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=offset + 1)).strftime("%Y-%m-%d")
        
        absence_data = {
            "reason": "TEST_Already processed",
            "type": "otro",
            "start_date": start_date,
            "end_date": end_date
        }
        create_resp = requests.post(f"{BASE_URL}/api/hr/absences", json=absence_data, headers=guard_headers)
        assert create_resp.status_code == 200, f"Failed to create absence: {create_resp.text}"
        absence_id = create_resp.json()["id"]
        
        # Approve first
        requests.put(f"{BASE_URL}/api/hr/absences/{absence_id}/approve", headers=admin_headers)
        
        # Try to approve again
        response = requests.put(f"{BASE_URL}/api/hr/absences/{absence_id}/approve", headers=admin_headers)
        assert response.status_code == 400
        print("✓ PUT /api/hr/absences/approve - Returns 400 for already processed")
    
    def test_get_absence_by_id(self, admin_headers):
        """GET /api/hr/absences/{id} - Get single absence"""
        # Get list first
        absences = requests.get(f"{BASE_URL}/api/hr/absences", headers=admin_headers).json()
        if not absences:
            pytest.skip("No absences found")
        
        absence_id = absences[0]["id"]
        response = requests.get(f"{BASE_URL}/api/hr/absences/{absence_id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == absence_id
        print(f"✓ GET /api/hr/absences/{absence_id[:8]}... - Found")
    
    def test_get_absence_not_found(self, admin_headers):
        """GET /api/hr/absences/{id} - 404 for non-existent"""
        response = requests.get(f"{BASE_URL}/api/hr/absences/nonexistent-id", headers=admin_headers)
        assert response.status_code == 404
        print("✓ GET /api/hr/absences/nonexistent - Returns 404")


# ==================== PAYROLL TESTS ====================
class TestPayroll:
    """HR Payroll tests"""
    
    def test_get_payroll(self, admin_headers):
        """GET /api/hr/payroll - Get payroll data"""
        response = requests.get(f"{BASE_URL}/api/hr/payroll", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get payroll: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "guard_name" in data[0]
            assert "hourly_rate" in data[0]
            assert "total_hours" in data[0]
            assert "total_pay" in data[0]
        print(f"✓ GET /api/hr/payroll - Found {len(data)} records")


# ==================== ROLE-BASED ACCESS TESTS ====================
class TestRoleBasedAccess:
    """Test role-based access control"""
    
    def test_guard_cannot_delete_shift(self, guard_headers, admin_headers):
        """Guards cannot delete shifts (admin only)"""
        # Get a shift
        shifts = requests.get(f"{BASE_URL}/api/hr/shifts", headers=admin_headers).json()
        if not shifts:
            pytest.skip("No shifts to test")
        
        shift_id = shifts[0]["id"]
        response = requests.delete(f"{BASE_URL}/api/hr/shifts/{shift_id}", headers=guard_headers)
        assert response.status_code == 403
        print("✓ DELETE /api/hr/shifts - Guard gets 403 (admin only)")
    
    def test_guard_cannot_approve_absence(self, guard_headers, admin_headers):
        """Guards cannot approve absences"""
        absences = requests.get(f"{BASE_URL}/api/hr/absences?status=pending", headers=admin_headers).json()
        if not absences:
            pytest.skip("No pending absences")
        
        absence_id = absences[0]["id"]
        response = requests.put(f"{BASE_URL}/api/hr/absences/{absence_id}/approve", headers=guard_headers)
        assert response.status_code == 403
        print("✓ PUT /api/hr/absences/approve - Guard gets 403")
    
    def test_guard_cannot_access_payroll(self, guard_headers):
        """Guards cannot access payroll"""
        response = requests.get(f"{BASE_URL}/api/hr/payroll", headers=guard_headers)
        assert response.status_code == 403
        print("✓ GET /api/hr/payroll - Guard gets 403 (admin only)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
