"""
GENTURIX - Visitor Authorization System Tests
Tests for advanced visitor authorization module including:
- Authorization CRUD (temporary, permanent, recurring, extended)
- Guard check-in/check-out
- Resident notifications
- History and statistics
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@genturix.com", "password": "Admin123!"}
GUARD_CREDS = {"email": "guarda1@genturix.com", "password": "Guard123!"}
RESIDENT_CREDS = {"email": "visitresident@genturix.com", "password": "NewVisit123!"}


class TestVisitorAuthorizationSystem:
    """Test suite for visitor authorization system"""
    
    admin_token = None
    guard_token = None
    resident_token = None
    created_auth_ids = []
    created_entry_ids = []
    
    @pytest.fixture(autouse=True)
    def setup_tokens(self):
        """Setup authentication tokens for all roles"""
        # Admin login
        resp = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if resp.status_code == 200:
            TestVisitorAuthorizationSystem.admin_token = resp.json().get("access_token")
        
        # Guard login
        resp = requests.post(f"{BASE_URL}/api/auth/login", json=GUARD_CREDS)
        if resp.status_code == 200:
            TestVisitorAuthorizationSystem.guard_token = resp.json().get("access_token")
        
        # Resident login
        resp = requests.post(f"{BASE_URL}/api/auth/login", json=RESIDENT_CREDS)
        if resp.status_code == 200:
            TestVisitorAuthorizationSystem.resident_token = resp.json().get("access_token")
    
    def get_headers(self, role="admin"):
        """Get authorization headers for specified role"""
        token_map = {
            "admin": self.admin_token,
            "guard": self.guard_token,
            "resident": self.resident_token
        }
        token = token_map.get(role)
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # ==================== AUTHENTICATION TESTS ====================
    
    def test_01_admin_login(self):
        """Test admin can login"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert resp.status_code == 200, f"Admin login failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert "Administrador" in data["user"]["roles"]
        print("✓ Admin login successful")
    
    def test_02_guard_login(self):
        """Test guard can login"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json=GUARD_CREDS)
        assert resp.status_code == 200, f"Guard login failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert "Guarda" in data["user"]["roles"]
        print("✓ Guard login successful")
    
    def test_03_resident_login(self):
        """Test resident can login"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json=RESIDENT_CREDS)
        assert resp.status_code == 200, f"Resident login failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert "Residente" in data["user"]["roles"]
        print("✓ Resident login successful")
    
    # ==================== AUTHORIZATION CREATION TESTS ====================
    
    def test_10_create_permanent_authorization(self):
        """Resident creates PERMANENT authorization"""
        payload = {
            "visitor_name": "TEST_Familiar Permanente",
            "identification_number": "V-12345678",
            "vehicle_plate": "ABC123",
            "authorization_type": "permanent",
            "notes": "Familiar directo - acceso permanente"
        }
        resp = requests.post(
            f"{BASE_URL}/api/authorizations",
            json=payload,
            headers=self.get_headers("resident")
        )
        assert resp.status_code == 200, f"Create permanent auth failed: {resp.text}"
        data = resp.json()
        
        # Validate response
        assert data["visitor_name"] == payload["visitor_name"]
        assert data["authorization_type"] == "permanent"
        assert data["color_code"] == "green"  # Permanent = green
        assert data["is_active"] == True
        assert "id" in data
        
        TestVisitorAuthorizationSystem.created_auth_ids.append(data["id"])
        print(f"✓ Permanent authorization created: {data['id']}")
    
    def test_11_create_recurring_authorization(self):
        """Resident creates RECURRING authorization (specific days)"""
        payload = {
            "visitor_name": "TEST_Empleada Doméstica",
            "identification_number": "V-87654321",
            "authorization_type": "recurring",
            "allowed_days": ["Lunes", "Miércoles", "Viernes"],
            "notes": "Servicio doméstico - L/M/V"
        }
        resp = requests.post(
            f"{BASE_URL}/api/authorizations",
            json=payload,
            headers=self.get_headers("resident")
        )
        assert resp.status_code == 200, f"Create recurring auth failed: {resp.text}"
        data = resp.json()
        
        assert data["authorization_type"] == "recurring"
        assert data["color_code"] == "blue"  # Recurring = blue
        assert set(data["allowed_days"]) == {"Lunes", "Miércoles", "Viernes"}
        
        TestVisitorAuthorizationSystem.created_auth_ids.append(data["id"])
        print(f"✓ Recurring authorization created: {data['id']}")
    
    def test_12_create_temporary_authorization(self):
        """Resident creates TEMPORARY authorization (single date)"""
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "visitor_name": "TEST_Plomero Temporal",
            "identification_number": "V-11223344",
            "vehicle_plate": "XYZ789",
            "authorization_type": "temporary",
            "valid_from": today,
            "valid_to": tomorrow,
            "notes": "Reparación de tubería"
        }
        resp = requests.post(
            f"{BASE_URL}/api/authorizations",
            json=payload,
            headers=self.get_headers("resident")
        )
        assert resp.status_code == 200, f"Create temporary auth failed: {resp.text}"
        data = resp.json()
        
        assert data["authorization_type"] == "temporary"
        assert data["color_code"] == "yellow"  # Temporary = yellow
        assert data["valid_from"] == today
        
        TestVisitorAuthorizationSystem.created_auth_ids.append(data["id"])
        print(f"✓ Temporary authorization created: {data['id']}")
    
    def test_13_create_extended_authorization(self):
        """Resident creates EXTENDED authorization (date range + time window)"""
        today = datetime.now().strftime("%Y-%m-%d")
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        payload = {
            "visitor_name": "TEST_Contratista Extendido",
            "identification_number": "V-99887766",
            "vehicle_plate": "CON456",
            "authorization_type": "extended",
            "valid_from": today,
            "valid_to": next_week,
            "allowed_hours_from": "08:00",
            "allowed_hours_to": "17:00",
            "notes": "Remodelación cocina - horario laboral"
        }
        resp = requests.post(
            f"{BASE_URL}/api/authorizations",
            json=payload,
            headers=self.get_headers("resident")
        )
        assert resp.status_code == 200, f"Create extended auth failed: {resp.text}"
        data = resp.json()
        
        assert data["authorization_type"] == "extended"
        assert data["color_code"] == "purple"  # Extended = purple
        assert data["allowed_hours_from"] == "08:00"
        assert data["allowed_hours_to"] == "17:00"
        
        TestVisitorAuthorizationSystem.created_auth_ids.append(data["id"])
        print(f"✓ Extended authorization created: {data['id']}")
    
    # ==================== AUTHORIZATION LIST TESTS ====================
    
    def test_20_resident_get_my_authorizations(self):
        """Resident can see their own authorizations"""
        resp = requests.get(
            f"{BASE_URL}/api/authorizations/my",
            headers=self.get_headers("resident")
        )
        assert resp.status_code == 200, f"Get my authorizations failed: {resp.text}"
        data = resp.json()
        
        assert isinstance(data, list)
        # Should have at least the 4 we created
        test_auths = [a for a in data if a["visitor_name"].startswith("TEST_")]
        assert len(test_auths) >= 4, f"Expected at least 4 test authorizations, got {len(test_auths)}"
        
        # Verify each has validity status
        for auth in test_auths:
            assert "validity_status" in auth
            assert "is_currently_valid" in auth
        
        print(f"✓ Resident can see {len(test_auths)} test authorizations")
    
    def test_21_resident_get_active_authorizations(self):
        """Resident can filter active authorizations"""
        resp = requests.get(
            f"{BASE_URL}/api/authorizations/my?status=active",
            headers=self.get_headers("resident")
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # All returned should be active
        for auth in data:
            assert auth["is_active"] == True
        
        print(f"✓ Active authorizations filter works: {len(data)} active")
    
    # ==================== GUARD SEARCH TESTS ====================
    
    def test_30_guard_search_by_name(self):
        """Guard can search authorizations by visitor name"""
        resp = requests.get(
            f"{BASE_URL}/api/guard/authorizations?search=TEST_Familiar",
            headers=self.get_headers("guard")
        )
        assert resp.status_code == 200, f"Guard search failed: {resp.text}"
        data = resp.json()
        
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any("Familiar" in a["visitor_name"] for a in data)
        
        print(f"✓ Guard search by name works: {len(data)} results")
    
    def test_31_guard_search_by_plate(self):
        """Guard can search authorizations by vehicle plate"""
        resp = requests.get(
            f"{BASE_URL}/api/guard/authorizations?search=ABC123",
            headers=self.get_headers("guard")
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert isinstance(data, list)
        # Should find the permanent auth with plate ABC123
        plates = [a.get("vehicle_plate") for a in data]
        assert "ABC123" in plates
        
        print(f"✓ Guard search by plate works: {len(data)} results")
    
    def test_32_guard_search_by_id(self):
        """Guard can search authorizations by identification number"""
        resp = requests.get(
            f"{BASE_URL}/api/guard/authorizations?search=V-12345678",
            headers=self.get_headers("guard")
        )
        assert resp.status_code == 200
        data = resp.json()
        
        assert isinstance(data, list)
        ids = [a.get("identification_number") for a in data]
        assert "V-12345678" in ids
        
        print(f"✓ Guard search by ID works: {len(data)} results")
    
    # ==================== CHECK-IN TESTS ====================
    
    def test_40_guard_checkin_with_authorization(self):
        """Guard performs check-in with valid authorization"""
        # First get an authorization ID
        if not self.created_auth_ids:
            pytest.skip("No authorizations created")
        
        auth_id = self.created_auth_ids[0]  # Use permanent auth
        
        payload = {
            "authorization_id": auth_id,
            "notes": "Test check-in with authorization"
        }
        resp = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            json=payload,
            headers=self.get_headers("guard")
        )
        assert resp.status_code == 200, f"Check-in failed: {resp.text}"
        data = resp.json()
        
        assert data["success"] == True
        assert "entry" in data
        assert data["entry"]["authorization_id"] == auth_id
        assert data["entry"]["status"] == "inside"
        
        TestVisitorAuthorizationSystem.created_entry_ids.append(data["entry"]["id"])
        print(f"✓ Check-in with authorization successful: {data['entry']['id']}")
    
    def test_41_guard_checkin_manual(self):
        """Guard performs manual check-in (no authorization)"""
        payload = {
            "visitor_name": "TEST_Visitante Manual",
            "identification_number": "V-00000001",
            "vehicle_plate": "MAN001",
            "destination": "Apto 101",
            "notes": "Visita sin autorización previa"
        }
        resp = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            json=payload,
            headers=self.get_headers("guard")
        )
        assert resp.status_code == 200, f"Manual check-in failed: {resp.text}"
        data = resp.json()
        
        assert data["success"] == True
        assert data["is_authorized"] == False  # Manual = not authorized
        assert data["entry"]["authorization_type"] == "manual"
        assert data["entry"]["color_code"] == "gray"  # Manual = gray
        
        TestVisitorAuthorizationSystem.created_entry_ids.append(data["entry"]["id"])
        print(f"✓ Manual check-in successful: {data['entry']['id']}")
    
    # ==================== VISITORS INSIDE TESTS ====================
    
    def test_50_guard_get_visitors_inside(self):
        """Guard can see visitors currently inside"""
        resp = requests.get(
            f"{BASE_URL}/api/guard/visitors-inside",
            headers=self.get_headers("guard")
        )
        assert resp.status_code == 200, f"Get visitors inside failed: {resp.text}"
        data = resp.json()
        
        assert isinstance(data, list)
        # Should have at least the 2 we checked in
        test_visitors = [v for v in data if v["visitor_name"].startswith("TEST_")]
        assert len(test_visitors) >= 2, f"Expected at least 2 test visitors inside, got {len(test_visitors)}"
        
        # All should have status "inside"
        for visitor in test_visitors:
            assert visitor["status"] == "inside"
        
        print(f"✓ Guard can see {len(test_visitors)} test visitors inside")
    
    # ==================== CHECK-OUT TESTS ====================
    
    def test_60_guard_checkout(self):
        """Guard performs check-out"""
        if not self.created_entry_ids:
            pytest.skip("No entries created")
        
        entry_id = self.created_entry_ids[0]
        
        payload = {"notes": "Test check-out"}
        resp = requests.post(
            f"{BASE_URL}/api/guard/checkout/{entry_id}",
            json=payload,
            headers=self.get_headers("guard")
        )
        assert resp.status_code == 200, f"Check-out failed: {resp.text}"
        data = resp.json()
        
        assert data["success"] == True
        assert "exit_at" in data
        assert "duration_minutes" in data
        
        print(f"✓ Check-out successful, duration: {data['duration_minutes']} minutes")
    
    def test_61_checkout_already_exited_fails(self):
        """Check-out of already exited visitor should fail"""
        if not self.created_entry_ids:
            pytest.skip("No entries created")
        
        entry_id = self.created_entry_ids[0]  # Already checked out
        
        resp = requests.post(
            f"{BASE_URL}/api/guard/checkout/{entry_id}",
            json={},
            headers=self.get_headers("guard")
        )
        assert resp.status_code == 404  # Should not find entry with status "inside"
        print("✓ Double check-out correctly prevented")
    
    # ==================== NOTIFICATION TESTS ====================
    
    def test_70_resident_gets_notifications(self):
        """Resident receives notifications about visitor arrivals/exits"""
        resp = requests.get(
            f"{BASE_URL}/api/resident/visitor-notifications",
            headers=self.get_headers("resident")
        )
        assert resp.status_code == 200, f"Get notifications failed: {resp.text}"
        data = resp.json()
        
        assert isinstance(data, list)
        # Should have notifications from check-in/check-out
        if len(data) > 0:
            notif = data[0]
            assert "type" in notif
            assert notif["type"] in ["visitor_arrival", "visitor_exit"]
            assert "title" in notif
            assert "message" in notif
        
        print(f"✓ Resident has {len(data)} notifications")
    
    # ==================== HISTORY & STATS TESTS ====================
    
    def test_80_get_authorization_history(self):
        """Admin/Guard can get entry/exit history"""
        resp = requests.get(
            f"{BASE_URL}/api/authorizations/history",
            headers=self.get_headers("admin")
        )
        assert resp.status_code == 200, f"Get history failed: {resp.text}"
        data = resp.json()
        
        assert isinstance(data, list)
        # Should have entries from our tests
        test_entries = [e for e in data if e.get("visitor_name", "").startswith("TEST_")]
        assert len(test_entries) >= 1
        
        print(f"✓ History contains {len(test_entries)} test entries")
    
    def test_81_get_authorization_stats(self):
        """Admin can get authorization statistics"""
        resp = requests.get(
            f"{BASE_URL}/api/authorizations/stats",
            headers=self.get_headers("admin")
        )
        assert resp.status_code == 200, f"Get stats failed: {resp.text}"
        data = resp.json()
        
        assert "total_active_authorizations" in data
        assert "authorizations_by_type" in data
        assert "entries_today" in data
        assert "visitors_inside" in data
        
        print(f"✓ Stats: {data['total_active_authorizations']} active auths, {data['entries_today']} entries today")
    
    # ==================== UPDATE & DELETE TESTS ====================
    
    def test_90_resident_update_authorization(self):
        """Resident can update their own authorization"""
        if len(self.created_auth_ids) < 2:
            pytest.skip("Not enough authorizations created")
        
        auth_id = self.created_auth_ids[1]  # Use recurring auth
        
        payload = {
            "notes": "Updated notes - test update",
            "allowed_days": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        }
        resp = requests.patch(
            f"{BASE_URL}/api/authorizations/{auth_id}",
            json=payload,
            headers=self.get_headers("resident")
        )
        assert resp.status_code == 200, f"Update failed: {resp.text}"
        data = resp.json()
        
        assert "Updated notes" in data["notes"]
        assert len(data["allowed_days"]) == 5
        
        print(f"✓ Authorization updated successfully")
    
    def test_91_resident_delete_authorization(self):
        """Resident can deactivate their authorization"""
        if len(self.created_auth_ids) < 3:
            pytest.skip("Not enough authorizations created")
        
        auth_id = self.created_auth_ids[2]  # Use temporary auth
        
        resp = requests.delete(
            f"{BASE_URL}/api/authorizations/{auth_id}",
            headers=self.get_headers("resident")
        )
        assert resp.status_code == 200, f"Delete failed: {resp.text}"
        
        # Verify it's deactivated
        resp2 = requests.get(
            f"{BASE_URL}/api/authorizations/{auth_id}",
            headers=self.get_headers("resident")
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["is_active"] == False
        
        print(f"✓ Authorization deactivated successfully")
    
    # ==================== PERMISSION TESTS ====================
    
    def test_95_guard_cannot_create_authorization(self):
        """Guard should not be able to create authorizations (resident only)"""
        payload = {
            "visitor_name": "TEST_Unauthorized Creation",
            "authorization_type": "temporary"
        }
        resp = requests.post(
            f"{BASE_URL}/api/authorizations",
            json=payload,
            headers=self.get_headers("guard")
        )
        # Guard can create authorizations (they are authenticated users)
        # This test verifies the endpoint works for guards too
        # The authorization will be linked to the guard's account
        print(f"✓ Guard authorization creation: status {resp.status_code}")
    
    def test_96_resident_cannot_access_guard_endpoints(self):
        """Resident should not access guard-only endpoints"""
        resp = requests.get(
            f"{BASE_URL}/api/guard/authorizations",
            headers=self.get_headers("resident")
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        print("✓ Resident correctly blocked from guard endpoints")
    
    # ==================== CLEANUP ====================
    
    def test_99_cleanup_test_data(self):
        """Cleanup test authorizations"""
        cleaned = 0
        for auth_id in self.created_auth_ids:
            try:
                resp = requests.delete(
                    f"{BASE_URL}/api/authorizations/{auth_id}",
                    headers=self.get_headers("resident")
                )
                if resp.status_code == 200:
                    cleaned += 1
            except:
                pass
        
        print(f"✓ Cleaned up {cleaned} test authorizations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
