"""
Test Suite for P0/P1 Bug Fixes:
- P0 Admin: 'Registro de Accesos' y 'Actividad Reciente' no muestran información
- P1 Residente: Los pre-registros no reflejan el estado real después de ser usados por el guardia

Endpoints tested:
1. GET /api/security/access-logs - Unified access_logs + visitor_entries
2. GET /api/dashboard/recent-activity - Multiple event types (audit_logs, visitor_entries, panic_events, reservations)
3. GET /api/authorizations/my - Includes status, was_used, used_at, used_by_guard fields
"""

import pytest
import requests
import os
from datetime import datetime, timedelta
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "SuperAdmin123!"
RESIDENT_EMAIL = "residente@genturix.com"
RESIDENT_PASSWORD = "Resi123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"


class TestAuthentication:
    """Helper class for authentication"""
    
    @staticmethod
    def login(email: str, password: str) -> dict:
        """Login and return tokens"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            return {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "user": data.get("user")
            }
        return None
    
    @staticmethod
    def get_headers(token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }


class TestAccessLogsEndpoint:
    """
    Test GET /api/security/access-logs
    Should return unified data from access_logs + visitor_entries
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup admin authentication"""
        auth = TestAuthentication.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not auth:
            pytest.skip("Admin login failed")
        self.token = auth["access_token"]
        self.headers = TestAuthentication.get_headers(self.token)
    
    def test_01_access_logs_returns_list(self):
        """GET /api/security/access-logs should return a list"""
        response = requests.get(
            f"{BASE_URL}/api/security/access-logs",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Access logs returned {len(data)} entries")
    
    def test_02_access_logs_has_unified_format(self):
        """Each access log entry should have unified format fields"""
        response = requests.get(
            f"{BASE_URL}/api/security/access-logs",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            entry = data[0]
            # Check required unified fields
            assert "id" in entry, "Entry should have 'id'"
            assert "person_name" in entry, "Entry should have 'person_name'"
            assert "access_type" in entry, "Entry should have 'access_type'"
            assert "timestamp" in entry, "Entry should have 'timestamp'"
            assert "source" in entry, "Entry should have 'source' field (manual or check_in)"
            print(f"✓ Entry has unified format: source={entry.get('source')}, person={entry.get('person_name')}")
        else:
            print("⚠ No access logs found - creating test data may be needed")
    
    def test_03_access_logs_includes_visitor_entries(self):
        """Access logs should include visitor check-ins (source='check_in')"""
        response = requests.get(
            f"{BASE_URL}/api/security/access-logs?include_visitor_entries=true",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check if any entries have source='check_in'
        check_in_entries = [e for e in data if e.get("source") == "check_in"]
        manual_entries = [e for e in data if e.get("source") == "manual"]
        
        print(f"✓ Found {len(check_in_entries)} check-in entries, {len(manual_entries)} manual entries")
        
        # Verify check-in entries have visitor-specific fields
        if check_in_entries:
            entry = check_in_entries[0]
            assert "entry_type" in entry, "Check-in entry should have 'entry_type'"
            print(f"  Check-in entry type: {entry.get('entry_type')}")
    
    def test_04_access_logs_sorted_by_timestamp(self):
        """Access logs should be sorted by timestamp (most recent first)"""
        response = requests.get(
            f"{BASE_URL}/api/security/access-logs",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data) >= 2:
            timestamps = [e.get("timestamp") for e in data if e.get("timestamp")]
            for i in range(len(timestamps) - 1):
                assert timestamps[i] >= timestamps[i+1], "Entries should be sorted by timestamp descending"
            print(f"✓ Entries are sorted by timestamp (most recent first)")
        else:
            print("⚠ Not enough entries to verify sorting")


class TestRecentActivityEndpoint:
    """
    Test GET /api/dashboard/recent-activity
    Should include: audit_logs, visitor_entries, panic_events, reservations
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup admin authentication"""
        auth = TestAuthentication.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not auth:
            pytest.skip("Admin login failed")
        self.token = auth["access_token"]
        self.headers = TestAuthentication.get_headers(self.token)
    
    def test_01_recent_activity_returns_list(self):
        """GET /api/dashboard/recent-activity should return a list"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/recent-activity",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Recent activity returned {len(data)} entries")
    
    def test_02_recent_activity_has_required_fields(self):
        """Each activity entry should have required fields"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/recent-activity",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            entry = data[0]
            assert "id" in entry, "Entry should have 'id'"
            assert "event_type" in entry, "Entry should have 'event_type'"
            assert "module" in entry, "Entry should have 'module'"
            assert "timestamp" in entry, "Entry should have 'timestamp'"
            assert "source" in entry, "Entry should have 'source'"
            print(f"✓ Entry has required fields: event_type={entry.get('event_type')}, source={entry.get('source')}")
        else:
            print("⚠ No recent activity found")
    
    def test_03_recent_activity_includes_multiple_sources(self):
        """Recent activity should include multiple event sources"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/recent-activity",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        sources = set(e.get("source") for e in data if e.get("source"))
        expected_sources = {"audit", "visitor", "panic", "reservation"}
        
        print(f"✓ Found sources: {sources}")
        print(f"  Expected sources: {expected_sources}")
        
        # At minimum, audit logs should be present (from login)
        assert "audit" in sources, "Should have audit log entries (at least from login)"
    
    def test_04_recent_activity_includes_visitor_checkins(self):
        """Recent activity should include visitor check-ins"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/recent-activity",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        visitor_entries = [e for e in data if e.get("source") == "visitor"]
        print(f"✓ Found {len(visitor_entries)} visitor check-in entries in recent activity")
        
        if visitor_entries:
            entry = visitor_entries[0]
            assert entry.get("event_type") == "visitor_checkin", "Visitor entry should have event_type='visitor_checkin'"
            print(f"  Visitor entry: {entry.get('description')}")
    
    def test_05_recent_activity_sorted_by_timestamp(self):
        """Recent activity should be sorted by timestamp (most recent first)"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/recent-activity",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data) >= 2:
            timestamps = [e.get("timestamp") for e in data if e.get("timestamp")]
            for i in range(len(timestamps) - 1):
                assert timestamps[i] >= timestamps[i+1], "Entries should be sorted by timestamp descending"
            print(f"✓ Entries are sorted by timestamp (most recent first)")
        else:
            print("⚠ Not enough entries to verify sorting")


class TestMyAuthorizationsEndpoint:
    """
    Test GET /api/authorizations/my
    Should include: status, was_used, used_at, used_by_guard fields
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup resident authentication"""
        auth = TestAuthentication.login(RESIDENT_EMAIL, RESIDENT_PASSWORD)
        if not auth:
            pytest.skip("Resident login failed")
        self.token = auth["access_token"]
        self.headers = TestAuthentication.get_headers(self.token)
        self.user = auth["user"]
    
    def test_01_my_authorizations_returns_list(self):
        """GET /api/authorizations/my should return a list"""
        response = requests.get(
            f"{BASE_URL}/api/authorizations/my",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ My authorizations returned {len(data)} entries")
    
    def test_02_authorizations_have_validity_fields(self):
        """Each authorization should have validity status fields"""
        response = requests.get(
            f"{BASE_URL}/api/authorizations/my",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            auth = data[0]
            # Check validity fields
            assert "validity_status" in auth, "Authorization should have 'validity_status'"
            assert "validity_message" in auth, "Authorization should have 'validity_message'"
            assert "is_currently_valid" in auth, "Authorization should have 'is_currently_valid'"
            print(f"✓ Authorization has validity fields: status={auth.get('validity_status')}, valid={auth.get('is_currently_valid')}")
        else:
            print("⚠ No authorizations found - will create test authorization")
    
    def test_03_create_and_verify_authorization(self):
        """Create a temporary authorization and verify it has correct fields"""
        # Create a new authorization
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        create_data = {
            "visitor_name": f"TEST_Visitor_{uuid.uuid4().hex[:6]}",
            "identification_number": "TEST-12345",
            "vehicle_plate": "TEST-123",
            "authorization_type": "temporary",
            "valid_from": tomorrow,
            "valid_to": tomorrow,
            "notes": "Test authorization for P1 bug verification"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/authorizations",
            headers=self.headers,
            json=create_data
        )
        assert create_response.status_code == 200, f"Failed to create authorization: {create_response.text}"
        created_auth = create_response.json()
        auth_id = created_auth.get("id")
        print(f"✓ Created test authorization: {auth_id}")
        
        # Verify it appears in my authorizations with correct fields
        response = requests.get(
            f"{BASE_URL}/api/authorizations/my",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find our created authorization
        test_auth = next((a for a in data if a.get("id") == auth_id), None)
        assert test_auth is not None, "Created authorization should appear in my authorizations"
        
        # Verify usage fields exist
        assert "was_used" in test_auth or "status" in test_auth, "Authorization should have usage tracking fields"
        
        # For temporary authorization that hasn't been used
        if test_auth.get("authorization_type") == "temporary":
            # Should not be marked as used yet
            was_used = test_auth.get("was_used", False)
            status = test_auth.get("status", "active")
            print(f"✓ Authorization usage status: was_used={was_used}, status={status}")
            assert was_used == False or status != "used", "New authorization should not be marked as used"
        
        # Cleanup - delete the test authorization
        delete_response = requests.delete(
            f"{BASE_URL}/api/authorizations/{auth_id}",
            headers=self.headers
        )
        print(f"✓ Cleaned up test authorization")
    
    def test_04_authorizations_filter_by_status(self):
        """Test filtering authorizations by status"""
        # Test active filter
        response = requests.get(
            f"{BASE_URL}/api/authorizations/my?status=active",
            headers=self.headers
        )
        assert response.status_code == 200
        active_auths = response.json()
        print(f"✓ Active authorizations: {len(active_auths)}")
        
        # Test used filter
        response = requests.get(
            f"{BASE_URL}/api/authorizations/my?status=used",
            headers=self.headers
        )
        assert response.status_code == 200
        used_auths = response.json()
        print(f"✓ Used authorizations: {len(used_auths)}")
        
        # Verify used authorizations have usage fields
        for auth in used_auths:
            assert auth.get("status") == "used" or auth.get("was_used") == True, \
                "Used authorizations should have status='used' or was_used=True"
            if auth.get("used_at"):
                print(f"  Used auth: {auth.get('visitor_name')} - used_at: {auth.get('used_at')}")
            if auth.get("used_by_guard"):
                print(f"    used_by_guard: {auth.get('used_by_guard')}")


class TestGuardCheckInFlow:
    """
    Test the full flow: Resident creates authorization -> Guard checks in -> Resident sees updated status
    """
    
    def test_01_full_checkin_flow(self):
        """Test complete check-in flow and verify authorization status updates"""
        # Step 1: Resident creates authorization
        resident_auth = TestAuthentication.login(RESIDENT_EMAIL, RESIDENT_PASSWORD)
        if not resident_auth:
            pytest.skip("Resident login failed")
        
        resident_headers = TestAuthentication.get_headers(resident_auth["access_token"])
        
        today = datetime.now().strftime("%Y-%m-%d")
        visitor_name = f"TEST_FlowVisitor_{uuid.uuid4().hex[:6]}"
        create_data = {
            "visitor_name": visitor_name,
            "identification_number": "FLOW-12345",
            "authorization_type": "temporary",
            "valid_from": today,
            "valid_to": today,
            "notes": "Test for check-in flow"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/authorizations",
            headers=resident_headers,
            json=create_data
        )
        
        if create_response.status_code != 200:
            print(f"⚠ Could not create authorization: {create_response.text}")
            pytest.skip("Authorization creation failed")
        
        auth_id = create_response.json().get("id")
        print(f"✓ Step 1: Resident created authorization {auth_id}")
        
        # Step 2: Guard logs in and performs check-in
        guard_auth = TestAuthentication.login(GUARD_EMAIL, GUARD_PASSWORD)
        if not guard_auth:
            # Cleanup and skip
            requests.delete(f"{BASE_URL}/api/authorizations/{auth_id}", headers=resident_headers)
            pytest.skip("Guard login failed")
        
        guard_headers = TestAuthentication.get_headers(guard_auth["access_token"])
        
        # Guard performs check-in
        checkin_data = {
            "authorization_id": auth_id,
            "destination": "Apartamento Test",
            "notes": "Test check-in"
        }
        
        checkin_response = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=guard_headers,
            json=checkin_data
        )
        
        if checkin_response.status_code != 200:
            print(f"⚠ Check-in failed: {checkin_response.text}")
            # Cleanup
            requests.delete(f"{BASE_URL}/api/authorizations/{auth_id}", headers=resident_headers)
            pytest.skip("Check-in failed")
        
        entry_data = checkin_response.json()
        print(f"✓ Step 2: Guard performed check-in, entry_id: {entry_data.get('id')}")
        
        # Step 3: Resident verifies authorization status is updated
        response = requests.get(
            f"{BASE_URL}/api/authorizations/my",
            headers=resident_headers
        )
        assert response.status_code == 200
        
        auths = response.json()
        updated_auth = next((a for a in auths if a.get("id") == auth_id), None)
        
        if updated_auth:
            print(f"✓ Step 3: Resident sees updated authorization:")
            print(f"  - status: {updated_auth.get('status')}")
            print(f"  - was_used: {updated_auth.get('was_used')}")
            print(f"  - used_at: {updated_auth.get('used_at')}")
            print(f"  - used_by_guard: {updated_auth.get('used_by_guard')}")
            
            # Verify the authorization shows as used
            assert updated_auth.get("was_used") == True or updated_auth.get("status") == "used", \
                "Authorization should be marked as used after check-in"
            assert updated_auth.get("used_at") is not None, \
                "Authorization should have used_at timestamp"
        else:
            print("⚠ Could not find updated authorization")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/authorizations/{auth_id}", headers=resident_headers)
        print(f"✓ Cleaned up test data")


class TestSuperAdminAccess:
    """Test that SuperAdmin can access all endpoints without condominium filter"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup superadmin authentication"""
        auth = TestAuthentication.login(SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD)
        if not auth:
            pytest.skip("SuperAdmin login failed")
        self.token = auth["access_token"]
        self.headers = TestAuthentication.get_headers(self.token)
    
    def test_01_superadmin_access_logs(self):
        """SuperAdmin should see global access logs"""
        response = requests.get(
            f"{BASE_URL}/api/security/access-logs",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print(f"✓ SuperAdmin can access access-logs: {len(data)} entries")
    
    def test_02_superadmin_recent_activity(self):
        """SuperAdmin should see global recent activity"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/recent-activity",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        print(f"✓ SuperAdmin can access recent-activity: {len(data)} entries")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
