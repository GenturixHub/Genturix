"""
Test Guard Manual Check-In Flow (P0 Bug Verification)
Tests the 'Entrada Manual (Sin Autorización)' button flow in Check-In tab
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"


class TestGuardManualCheckIn:
    """Test Guard Manual Check-In Flow - P0 Bug Verification"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.guard_token = None
        self.created_entry_id = None
    
    def test_01_guard_login(self):
        """Test guard can login successfully"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        
        print(f"Guard login response: {response.status_code}")
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert "user" in data, "No user in response"
        
        self.guard_token = data["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.guard_token}"})
        
        # Verify guard role
        user = data["user"]
        print(f"Guard user: {user.get('full_name')}, roles: {user.get('roles')}")
        assert "Guarda" in user.get("roles", []), "User is not a guard"
        
        return self.guard_token
    
    def test_02_manual_checkin_creates_real_record(self):
        """Test that manual check-in creates a real record in visitor_entries"""
        # First login
        token = self.test_01_guard_login()
        
        # Create unique visitor name for this test
        test_visitor_name = f"TEST_Manual_Visitor_{int(time.time())}"
        
        # Perform manual check-in (no authorization_id)
        checkin_payload = {
            "authorization_id": None,
            "visitor_name": test_visitor_name,
            "identification_number": "TEST-12345",
            "vehicle_plate": "TEST-001",
            "destination": "Casa Test",
            "notes": "Test manual entry"
        }
        
        print(f"Sending manual check-in request: {checkin_payload}")
        
        response = self.session.post(f"{BASE_URL}/api/guard/checkin", json=checkin_payload)
        
        print(f"Check-in response status: {response.status_code}")
        print(f"Check-in response body: {response.text[:500]}")
        
        assert response.status_code == 200, f"Manual check-in failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Check-in success flag is not True"
        assert "entry" in data, "No entry in response"
        
        entry = data["entry"]
        self.created_entry_id = entry.get("id")
        
        # Verify entry data
        assert entry.get("visitor_name") == test_visitor_name, "Visitor name mismatch"
        assert entry.get("status") == "inside", "Entry status should be 'inside'"
        assert entry.get("is_authorized") == False, "Manual entry should not be authorized"
        assert entry.get("authorization_type") == "manual", "Authorization type should be 'manual'"
        
        print(f"✓ Manual check-in created entry with ID: {self.created_entry_id}")
        
        return self.created_entry_id
    
    def test_03_verify_entry_in_visitors_inside(self):
        """Verify the entry appears in visitors-inside list"""
        # First create an entry
        entry_id = self.test_02_manual_checkin_creates_real_record()
        
        # Get visitors inside
        response = self.session.get(f"{BASE_URL}/api/guard/visitors-inside")
        
        print(f"Visitors inside response: {response.status_code}")
        assert response.status_code == 200, f"Failed to get visitors inside: {response.text}"
        
        visitors = response.json()
        print(f"Found {len(visitors)} visitors inside")
        
        # Find our entry
        found_entry = None
        for v in visitors:
            if v.get("id") == entry_id:
                found_entry = v
                break
        
        assert found_entry is not None, f"Entry {entry_id} not found in visitors-inside list"
        assert found_entry.get("status") == "inside", "Entry status should be 'inside'"
        
        print(f"✓ Entry found in visitors-inside list")
        
        return entry_id
    
    def test_04_verify_entry_in_history(self):
        """Verify the entry appears in guard history"""
        # First create an entry
        entry_id = self.test_02_manual_checkin_creates_real_record()
        
        # Get guard history
        response = self.session.get(f"{BASE_URL}/api/guard/history")
        
        print(f"Guard history response: {response.status_code}")
        assert response.status_code == 200, f"Failed to get guard history: {response.text}"
        
        history = response.json()
        print(f"Found {len(history)} history entries")
        
        # Find our entry (history entries have id like "{entry_id}_in")
        found_entry = None
        for h in history:
            if h.get("id") == f"{entry_id}_in" or h.get("id") == entry_id:
                found_entry = h
                break
        
        assert found_entry is not None, f"Entry {entry_id} not found in history"
        
        print(f"✓ Entry found in guard history")
        
        return entry_id
    
    def test_05_checkout_visitor(self):
        """Test checking out a visitor"""
        # First create an entry
        entry_id = self.test_02_manual_checkin_creates_real_record()
        
        # Checkout the visitor
        checkout_payload = {
            "notes": "Test checkout"
        }
        
        response = self.session.post(f"{BASE_URL}/api/guard/checkout/{entry_id}", json=checkout_payload)
        
        print(f"Checkout response: {response.status_code}")
        print(f"Checkout response body: {response.text[:500]}")
        
        assert response.status_code == 200, f"Checkout failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Checkout success flag is not True"
        
        # Verify entry is no longer in visitors-inside
        response = self.session.get(f"{BASE_URL}/api/guard/visitors-inside")
        assert response.status_code == 200
        
        visitors = response.json()
        found = any(v.get("id") == entry_id for v in visitors)
        assert not found, "Entry should not be in visitors-inside after checkout"
        
        print(f"✓ Visitor checked out successfully")
    
    def test_06_entries_today_shows_entry(self):
        """Verify entry appears in entries-today"""
        # First create an entry
        entry_id = self.test_02_manual_checkin_creates_real_record()
        
        # Get entries today
        response = self.session.get(f"{BASE_URL}/api/guard/entries-today")
        
        print(f"Entries today response: {response.status_code}")
        assert response.status_code == 200, f"Failed to get entries today: {response.text}"
        
        entries = response.json()
        print(f"Found {len(entries)} entries today")
        
        # Find our entry
        found_entry = None
        for e in entries:
            if e.get("id") == entry_id:
                found_entry = e
                break
        
        assert found_entry is not None, f"Entry {entry_id} not found in entries-today"
        
        print(f"✓ Entry found in entries-today")


class TestGuardCheckInWithToast:
    """Test that the correct toast message appears"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_manual_checkin_response_message(self):
        """Verify the response message for manual check-in"""
        # Login as guard
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        assert response.status_code == 200
        
        token = response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Manual check-in
        checkin_payload = {
            "authorization_id": None,
            "visitor_name": f"TEST_Toast_Visitor_{int(time.time())}",
            "identification_number": None,
            "vehicle_plate": None,
            "destination": None,
            "notes": None
        }
        
        response = self.session.post(f"{BASE_URL}/api/guard/checkin", json=checkin_payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # For manual entry (no authorization), is_authorized should be False
        assert data.get("is_authorized") == False, "Manual entry should not be authorized"
        
        # The message should indicate it's without valid authorization
        message = data.get("message", "")
        print(f"Response message: {message}")
        
        # Frontend shows '⚠️ Entrada manual registrada' for is_authorized=False
        # Backend returns 'Entrada registrada (sin autorización válida)'
        assert "sin autorización" in message.lower() or "entrada registrada" in message.lower(), \
            f"Unexpected message: {message}"
        
        print(f"✓ Correct response message for manual entry")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
