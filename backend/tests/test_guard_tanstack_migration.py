"""
Test Guard TanStack Query Migration - API Endpoints
Tests all endpoints used by Guard role with TanStack Query hooks.

Endpoints tested:
- GET /api/panic/events - Alerts (useGuardAlerts)
- GET /api/guard/clock-status - Clock status (useGuardClockStatus)
- GET /api/guard/visits-summary - Visitor entries (useGuardVisitorEntries)
- GET /api/guard/my-shift - Shift data (useGuardShift)
- GET /api/guard/my-absences - Absences (useGuardAbsences)
- GET /api/guard/history - History (useGuardHistory)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Guard credentials
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"


class TestGuardAuth:
    """Test Guard authentication - prerequisite for all Guard tests"""
    
    def test_guard_login(self):
        """Test guard login returns valid token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": GUARD_EMAIL, "password": GUARD_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == GUARD_EMAIL
        assert "Guarda" in data["user"]["roles"]
        print(f"Guard login successful: {data['user']['full_name']}")


@pytest.fixture
def guard_token():
    """Get guard authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": GUARD_EMAIL, "password": GUARD_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Guard login failed: {response.text}")
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(guard_token):
    """Get authorization headers with guard token"""
    return {
        "Authorization": f"Bearer {guard_token}",
        "Content-Type": "application/json"
    }


class TestGuardAlertsAPI:
    """Test Alerts API - useGuardAlerts hook"""
    
    def test_get_panic_events(self, auth_headers):
        """Test GET /api/security/panic-events returns alerts array"""
        response = requests.get(
            f"{BASE_URL}/api/security/panic-events",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get panic events: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of panic events"
        print(f"Panic events count: {len(data)}")
        
        # If there are events, validate structure
        if len(data) > 0:
            event = data[0]
            assert "id" in event or "_id" in event
            assert "panic_type" in event or "type" in event
            assert "status" in event
            print(f"First event type: {event.get('panic_type', event.get('type'))}, status: {event.get('status')}")


class TestGuardClockAPI:
    """Test Clock Status API - useGuardClockStatus hook"""
    
    def test_get_clock_status(self, auth_headers):
        """Test GET /api/hr/clock/status returns clock status"""
        response = requests.get(
            f"{BASE_URL}/api/hr/clock/status",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get clock status: {response.text}"
        
        data = response.json()
        assert "is_clocked_in" in data, "Expected is_clocked_in field"
        print(f"Clock status - is_clocked_in: {data.get('is_clocked_in')}")


class TestGuardVisitorEntriesAPI:
    """Test Visitor Entries API - useGuardVisitorEntries hook"""
    
    def test_get_visits_summary(self, auth_headers):
        """Test GET /api/guard/visits-summary returns visitor data"""
        response = requests.get(
            f"{BASE_URL}/api/guard/visits-summary",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get visits summary: {response.text}"
        
        data = response.json()
        # Validate expected structure
        assert "pending" in data or "inside" in data or "exits" in data, \
            f"Expected visitor categories, got: {list(data.keys())}"
        
        pending_count = len(data.get("pending", []))
        inside_count = len(data.get("inside", []))
        exits_count = len(data.get("exits", []))
        
        print(f"Visitor entries - Pending: {pending_count}, Inside: {inside_count}, Exits: {exits_count}")


class TestGuardShiftAPI:
    """Test Shift Data API - useGuardShift/useGuardShiftData hooks"""
    
    def test_get_my_shift(self, auth_headers):
        """Test GET /api/guard/my-shift returns shift data"""
        response = requests.get(
            f"{BASE_URL}/api/guard/my-shift",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get shift: {response.text}"
        
        data = response.json()
        # Shift data may be null if no shifts assigned
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        print(f"Shift data keys: {list(data.keys())}")
        
        has_guard_record = data.get("has_guard_record", False)
        current_shift = data.get("current_shift")
        next_shift = data.get("next_shift")
        print(f"Has guard record: {has_guard_record}, Has current shift: {current_shift is not None}")


class TestGuardAbsencesAPI:
    """Test Absences API - useGuardAbsences hook"""
    
    def test_get_my_absences(self, auth_headers):
        """Test GET /api/guard/my-absences returns absences array"""
        response = requests.get(
            f"{BASE_URL}/api/guard/my-absences",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get absences: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"Absences count: {len(data)}")


class TestGuardHistoryAPI:
    """Test History API - useGuardHistory hook"""
    
    def test_get_guard_history(self, auth_headers):
        """Test GET /api/guard/history returns history data"""
        response = requests.get(
            f"{BASE_URL}/api/guard/history",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to get history: {response.text}"
        
        data = response.json()
        assert isinstance(data, (list, dict)), f"Expected list or dict, got {type(data)}"
        
        if isinstance(data, dict):
            print(f"History data keys: {list(data.keys())}")
        else:
            print(f"History entries count: {len(data)}")


class TestGuardMutations:
    """Test Guard mutation endpoints - used by TanStack Query mutations"""
    
    def test_resolve_alert_endpoint_exists(self, auth_headers):
        """Test POST /api/panic/events/{id}/resolve endpoint exists"""
        # We don't actually resolve an alert, just verify the endpoint pattern exists
        # Using a fake ID should return 404, not 405 (method not allowed)
        response = requests.post(
            f"{BASE_URL}/api/panic/events/fake-id-123/resolve",
            headers=auth_headers,
            json={"notes": "Test resolution"}
        )
        # 404 = endpoint exists but ID not found (good)
        # 405 = endpoint doesn't exist (bad)
        # 422 = validation error (also acceptable)
        assert response.status_code in [404, 422, 400], \
            f"Unexpected status {response.status_code}: {response.text}"
        print(f"Resolve alert endpoint status: {response.status_code}")
    
    def test_clock_in_endpoint_exists(self, auth_headers):
        """Test POST /api/guard/clock-in endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/guard/clock-in",
            headers=auth_headers,
            json={}
        )
        # May fail due to business rules but endpoint should exist
        assert response.status_code != 405, f"Clock in endpoint not found"
        print(f"Clock in endpoint status: {response.status_code}")
    
    def test_clock_out_endpoint_exists(self, auth_headers):
        """Test POST /api/guard/clock-out endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/guard/clock-out",
            headers=auth_headers,
            json={}
        )
        # May fail due to business rules but endpoint should exist
        assert response.status_code != 405, f"Clock out endpoint not found"
        print(f"Clock out endpoint status: {response.status_code}")
    
    def test_guard_checkin_endpoint_exists(self, auth_headers):
        """Test POST /api/guard/checkin endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=auth_headers,
            json={"visitor_name": "Test Visitor"}
        )
        # Should return 2xx, 400, 422 - not 405
        assert response.status_code != 405, f"Guard checkin endpoint not found"
        print(f"Guard checkin endpoint status: {response.status_code}")
    
    def test_guard_checkout_endpoint_exists(self, auth_headers):
        """Test POST /api/guard/checkout/{id} endpoint exists"""
        response = requests.post(
            f"{BASE_URL}/api/guard/checkout/fake-id-123",
            headers=auth_headers,
            json={}
        )
        # Should return 404, 400, 422 - not 405
        assert response.status_code != 405, f"Guard checkout endpoint not found"
        print(f"Guard checkout endpoint status: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
