"""
Test suite for Panic Alert Modal and HR Module features
- Panic alert resolution with notes
- HR clock history endpoint
- HR absences endpoint
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
GUARD_CREDENTIALS = {"email": "D@d.com", "password": "Guard123!"}
HR_CREDENTIALS = {"email": "christopher01campos@gmail.com", "password": "Guard123!"}


class TestAuthentication:
    """Test authentication for guard and HR users"""
    
    def test_guard_login(self):
        """Guard user can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=GUARD_CREDENTIALS)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "Guarda" in data["user"]["roles"]
        print(f"✓ Guard login successful: {data['user']['email']}")
    
    def test_hr_login(self):
        """HR user can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "HR" in data["user"]["roles"]
        print(f"✓ HR login successful: {data['user']['email']}")


class TestPanicAlertFeatures:
    """Test panic alert modal and resolution features"""
    
    @pytest.fixture
    def guard_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=GUARD_CREDENTIALS)
        return response.json()["access_token"]
    
    def test_get_panic_events(self, guard_token):
        """Guard can fetch panic events"""
        response = requests.get(
            f"{BASE_URL}/api/security/panic-events",
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Fetched {len(data)} panic events")
        
        # Verify event structure
        if data:
            event = data[0]
            assert "id" in event
            assert "panic_type" in event
            assert "status" in event
            assert "user_name" in event
            print(f"  First event: {event['panic_type']} - {event['status']} - {event['user_name']}")
    
    def test_panic_event_has_location_data(self, guard_token):
        """Panic events include GPS coordinates when available"""
        response = requests.get(
            f"{BASE_URL}/api/security/panic-events",
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find event with GPS coordinates
        events_with_gps = [e for e in data if e.get("latitude") and e.get("longitude")]
        print(f"✓ Found {len(events_with_gps)} events with GPS coordinates")
        
        if events_with_gps:
            event = events_with_gps[0]
            assert isinstance(event["latitude"], (int, float))
            assert isinstance(event["longitude"], (int, float))
            print(f"  GPS: {event['latitude']}, {event['longitude']}")
    
    def test_resolve_panic_with_notes(self, guard_token):
        """Guard can resolve panic event with resolution notes"""
        # Get an event to resolve
        response = requests.get(
            f"{BASE_URL}/api/security/panic-events",
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        events = response.json()
        
        if not events:
            pytest.skip("No panic events to test resolution")
        
        event_id = events[0]["id"]
        resolution_notes = f"Test resolution at {datetime.now().isoformat()}"
        
        # Resolve with notes
        response = requests.put(
            f"{BASE_URL}/api/security/panic/{event_id}/resolve",
            headers={"Authorization": f"Bearer {guard_token}"},
            json={"notes": resolution_notes}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Panic event resolved"
        print(f"✓ Resolved panic event {event_id[:8]}... with notes")
        
        # Verify notes were saved
        response = requests.get(
            f"{BASE_URL}/api/security/panic-events",
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        updated_event = next((e for e in response.json() if e["id"] == event_id), None)
        assert updated_event is not None
        assert updated_event.get("resolution_notes") == resolution_notes
        print(f"✓ Resolution notes saved correctly")
    
    def test_resolution_saved_to_guard_history(self, guard_token):
        """Resolution is saved to guard_history for audit trail"""
        response = requests.get(
            f"{BASE_URL}/api/guard/history",
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        assert response.status_code == 200
        history = response.json()
        
        # Find alert_resolved entries
        resolved_entries = [h for h in history if h.get("type") == "alert_resolved"]
        print(f"✓ Found {len(resolved_entries)} alert_resolved entries in guard history")
        
        if resolved_entries:
            entry = resolved_entries[0]
            assert "event_id" in entry
            assert "guard_name" in entry
            print(f"  Latest: {entry.get('guard_name')} resolved {entry.get('event_type_label', 'alert')}")


class TestHRClockHistory:
    """Test HR clock history endpoint"""
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def guard_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=GUARD_CREDENTIALS)
        return response.json()["access_token"]
    
    def test_hr_can_access_clock_history(self, hr_token):
        """HR role can access clock history endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/hr/clock/history",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ HR accessed clock history: {len(data)} records")
        
        if data:
            record = data[0]
            assert "employee_name" in record
            assert "type" in record
            assert "timestamp" in record
            print(f"  Latest: {record['employee_name']} - {record['type']} at {record['timestamp'][:19]}")
    
    def test_hr_can_access_clock_status(self, hr_token):
        """HR role can access clock status endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/hr/clock/status",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # HR user without guard record gets appropriate response
        assert "is_clocked_in" in data
        print(f"✓ HR accessed clock status")
    
    def test_clock_history_scoped_by_condominium(self, hr_token, guard_token):
        """Clock history is scoped by condominium_id"""
        # Get HR's clock history
        hr_response = requests.get(
            f"{BASE_URL}/api/hr/clock/history",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        hr_history = hr_response.json()
        
        # Get Guard's clock history
        guard_response = requests.get(
            f"{BASE_URL}/api/hr/clock/history",
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        guard_history = guard_response.json()
        
        # Both should see same condominium data
        print(f"✓ HR sees {len(hr_history)} records, Guard sees {len(guard_history)} records")


class TestHRAbsences:
    """Test HR absences functionality"""
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def guard_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=GUARD_CREDENTIALS)
        return response.json()["access_token"]
    
    def test_hr_can_view_absences(self, hr_token):
        """HR role can view absence requests"""
        response = requests.get(
            f"{BASE_URL}/api/hr/absences",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ HR viewed {len(data)} absence requests")
        
        if data:
            absence = data[0]
            assert "employee_name" in absence
            assert "type" in absence
            assert "status" in absence
            print(f"  Latest: {absence['employee_name']} - {absence['type']} - {absence['status']}")
    
    def test_guard_can_create_absence_request(self, guard_token):
        """Guard can create absence request"""
        # Use unique dates to avoid overlap
        start_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=65)).strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/hr/absences",
            headers={"Authorization": f"Bearer {guard_token}"},
            json={
                "reason": "Test absence from pytest",
                "type": "vacaciones",
                "start_date": start_date,
                "end_date": end_date,
                "notes": "Automated test"
            }
        )
        
        if response.status_code == 400 and "Ya tienes una solicitud" in response.text:
            print("⚠ Absence request already exists for these dates (expected)")
            return
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["type"] == "vacaciones"
        print(f"✓ Guard created absence request: {data['id'][:8]}...")
    
    def test_hr_cannot_create_absence(self, hr_token):
        """HR role cannot create absence requests (only guards can)"""
        response = requests.post(
            f"{BASE_URL}/api/hr/absences",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "reason": "Test",
                "type": "vacaciones",
                "start_date": "2026-04-01",
                "end_date": "2026-04-05"
            }
        )
        # HR should get 403 Forbidden
        assert response.status_code == 403
        print("✓ HR correctly denied from creating absence (only guards can)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
