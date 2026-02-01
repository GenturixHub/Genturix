"""
Test Suite: P0 BUG FIX - Pre-registros duplicados en Guard Check-In

Bug Description:
- El preregistro permanecía visible después del check-in permitiendo múltiples ingresos con la misma autorización.

Fix Implemented:
1. Autorizaciones tienen campo 'status' (pending/used)
2. GET /guard/authorizations filtra status='pending' por defecto
3. POST /guard/checkin retorna 409 si auth ya usada, marca status='used' para temporales
4. Nuevo endpoint GET /guard/entries-today para sección 'Ingresados Hoy'
5. Frontend remueve auth de lista en handleCheckInSubmit y maneja error 409

Test Cases:
- Crear autorización temporal como Residente
- Guardia ve la autorización en PRE-REGISTROS PENDIENTES
- Primer check-in con la autorización debe retornar HTTP 200
- Segundo check-in con MISMA autorización debe retornar HTTP 409
- Mensaje de error 409 debe decir 'Esta autorización ya fue utilizada'
- Después del check-in, la autorización NO debe aparecer en /guard/authorizations
- La sección 'INGRESADOS HOY' debe mostrar la entrada
- Autorizaciones PERMANENTES pueden usarse múltiples veces
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
RESIDENT_EMAIL = "residente@genturix.com"
RESIDENT_PASSWORD = "Resi123!"
GUARD_EMAIL = "guardia_test@genturix.com"
GUARD_PASSWORD = "Guard123!!"


class TestDuplicatePreregistroFix:
    """Test suite for P0 bug fix: duplicate pre-registrations in guard check-in"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.resident_token = None
        self.guard_token = None
        self.test_auth_id = None
        self.test_permanent_auth_id = None
    
    def login_as_resident(self):
        """Login as resident user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        if response.status_code == 200:
            self.resident_token = response.json().get("access_token")
            return True
        print(f"Resident login failed: {response.status_code} - {response.text}")
        return False
    
    def login_as_guard(self):
        """Login as guard user"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        if response.status_code == 200:
            self.guard_token = response.json().get("access_token")
            return True
        print(f"Guard login failed: {response.status_code} - {response.text}")
        return False
    
    def test_01_resident_login(self):
        """Test resident can login"""
        assert self.login_as_resident(), "Resident login should succeed"
        assert self.resident_token is not None, "Should receive access token"
        print(f"✓ Resident logged in successfully")
    
    def test_02_guard_login(self):
        """Test guard can login"""
        assert self.login_as_guard(), "Guard login should succeed"
        assert self.guard_token is not None, "Should receive access token"
        print(f"✓ Guard logged in successfully")
    
    def test_03_resident_creates_temporary_authorization(self):
        """Resident creates a TEMPORARY authorization for a visitor"""
        assert self.login_as_resident(), "Must login as resident first"
        
        # Create temporary authorization for today
        today = datetime.now().strftime("%Y-%m-%d")
        auth_data = {
            "visitor_name": f"TEST_Visitante_Temporal_{datetime.now().strftime('%H%M%S')}",
            "identification_number": "TEST-12345678",
            "vehicle_plate": "TEST-ABC123",
            "authorization_type": "temporary",
            "valid_from": today,
            "valid_to": today,
            "notes": "Test authorization for duplicate check-in bug fix"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/authorizations",
            json=auth_data,
            headers={"Authorization": f"Bearer {self.resident_token}"}
        )
        
        assert response.status_code == 201, f"Should create authorization: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain authorization ID"
        assert data.get("authorization_type") == "temporary", "Should be temporary type"
        assert data.get("status") == "pending", "Initial status should be 'pending'"
        
        self.test_auth_id = data["id"]
        print(f"✓ Created temporary authorization: {self.test_auth_id}")
        print(f"  - Visitor: {data.get('visitor_name')}")
        print(f"  - Status: {data.get('status')}")
        
        return self.test_auth_id
    
    def test_04_guard_sees_authorization_in_pending_list(self):
        """Guard should see the authorization in pending pre-registrations"""
        assert self.login_as_guard(), "Must login as guard first"
        
        # First create the authorization
        auth_id = self.test_03_resident_creates_temporary_authorization()
        
        # Now login as guard and check
        assert self.login_as_guard(), "Must login as guard"
        
        response = self.session.get(
            f"{BASE_URL}/api/guard/authorizations",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        assert response.status_code == 200, f"Should get authorizations: {response.status_code}"
        
        authorizations = response.json()
        assert isinstance(authorizations, list), "Should return a list"
        
        # Find our test authorization
        found = False
        for auth in authorizations:
            if auth.get("id") == auth_id:
                found = True
                assert auth.get("status") in ["pending", None], f"Status should be pending, got: {auth.get('status')}"
                print(f"✓ Authorization found in pending list")
                print(f"  - ID: {auth.get('id')}")
                print(f"  - Status: {auth.get('status')}")
                break
        
        assert found, f"Authorization {auth_id} should be visible in guard's pending list"
        return auth_id
    
    def test_05_first_checkin_returns_200(self):
        """First check-in with authorization should return HTTP 200"""
        # Create authorization and verify it's visible
        auth_id = self.test_04_guard_sees_authorization_in_pending_list()
        
        # Login as guard
        assert self.login_as_guard(), "Must login as guard"
        
        # Perform first check-in
        checkin_data = {
            "authorization_id": auth_id,
            "notes": "First check-in test"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/guard/checkin",
            json=checkin_data,
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        assert response.status_code == 200, f"First check-in should return 200: {response.status_code} - {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Should indicate success"
        assert data.get("is_authorized") == True, "Should be authorized"
        assert data.get("authorization_marked_used") == True, "Temporary auth should be marked as used"
        
        print(f"✓ First check-in successful (HTTP 200)")
        print(f"  - Entry ID: {data.get('entry', {}).get('id')}")
        print(f"  - Authorization marked used: {data.get('authorization_marked_used')}")
        
        return auth_id
    
    def test_06_second_checkin_returns_409(self):
        """Second check-in with SAME authorization should return HTTP 409"""
        # First check-in
        auth_id = self.test_05_first_checkin_returns_200()
        
        # Login as guard again
        assert self.login_as_guard(), "Must login as guard"
        
        # Attempt second check-in with same authorization
        checkin_data = {
            "authorization_id": auth_id,
            "notes": "Second check-in attempt - should fail"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/guard/checkin",
            json=checkin_data,
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        assert response.status_code == 409, f"Second check-in should return 409 Conflict: {response.status_code} - {response.text}"
        
        data = response.json()
        error_message = data.get("detail", "")
        assert "ya fue utilizada" in error_message.lower() or "already used" in error_message.lower(), \
            f"Error message should indicate authorization was already used: {error_message}"
        
        print(f"✓ Second check-in correctly blocked (HTTP 409)")
        print(f"  - Error message: {error_message}")
    
    def test_07_authorization_not_in_pending_list_after_checkin(self):
        """After check-in, authorization should NOT appear in /guard/authorizations"""
        # Create and check-in
        auth_id = self.test_05_first_checkin_returns_200()
        
        # Login as guard
        assert self.login_as_guard(), "Must login as guard"
        
        # Get authorizations (default: only pending)
        response = self.session.get(
            f"{BASE_URL}/api/guard/authorizations",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        assert response.status_code == 200, f"Should get authorizations: {response.status_code}"
        
        authorizations = response.json()
        
        # Check that our used authorization is NOT in the list
        found = False
        for auth in authorizations:
            if auth.get("id") == auth_id:
                found = True
                break
        
        assert not found, f"Used authorization {auth_id} should NOT appear in pending list"
        print(f"✓ Used authorization correctly removed from pending list")
    
    def test_08_entries_today_shows_checkin(self):
        """GET /guard/entries-today should show the entry"""
        # Create and check-in
        auth_id = self.test_05_first_checkin_returns_200()
        
        # Login as guard
        assert self.login_as_guard(), "Must login as guard"
        
        # Get today's entries
        response = self.session.get(
            f"{BASE_URL}/api/guard/entries-today",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        assert response.status_code == 200, f"Should get entries today: {response.status_code}"
        
        entries = response.json()
        assert isinstance(entries, list), "Should return a list"
        
        # Find our entry
        found = False
        for entry in entries:
            if entry.get("authorization_id") == auth_id:
                found = True
                assert entry.get("entry_at") is not None, "Should have entry timestamp"
                print(f"✓ Entry found in 'Entries Today' list")
                print(f"  - Entry ID: {entry.get('id')}")
                print(f"  - Visitor: {entry.get('visitor_name')}")
                print(f"  - Entry at: {entry.get('entry_at')}")
                break
        
        assert found, "Entry should appear in today's entries list"
    
    def test_09_permanent_authorization_can_be_used_multiple_times(self):
        """PERMANENT authorizations should allow multiple check-ins"""
        # Login as resident and create permanent authorization
        assert self.login_as_resident(), "Must login as resident"
        
        auth_data = {
            "visitor_name": f"TEST_Visitante_Permanente_{datetime.now().strftime('%H%M%S')}",
            "identification_number": "PERM-87654321",
            "vehicle_plate": "PERM-XYZ789",
            "authorization_type": "permanent",
            "notes": "Permanent authorization for multiple check-in test"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/authorizations",
            json=auth_data,
            headers={"Authorization": f"Bearer {self.resident_token}"}
        )
        
        assert response.status_code == 201, f"Should create permanent authorization: {response.status_code}"
        
        perm_auth_id = response.json().get("id")
        print(f"✓ Created permanent authorization: {perm_auth_id}")
        
        # Login as guard
        assert self.login_as_guard(), "Must login as guard"
        
        # First check-in
        response1 = self.session.post(
            f"{BASE_URL}/api/guard/checkin",
            json={"authorization_id": perm_auth_id, "notes": "First permanent check-in"},
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        assert response1.status_code == 200, f"First permanent check-in should succeed: {response1.status_code}"
        print(f"✓ First permanent check-in successful")
        
        # Second check-in (should also succeed for permanent)
        response2 = self.session.post(
            f"{BASE_URL}/api/guard/checkin",
            json={"authorization_id": perm_auth_id, "notes": "Second permanent check-in"},
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        assert response2.status_code == 200, f"Second permanent check-in should also succeed: {response2.status_code}"
        print(f"✓ Second permanent check-in successful (permanent auths allow multiple uses)")
        
        # Third check-in (should also succeed)
        response3 = self.session.post(
            f"{BASE_URL}/api/guard/checkin",
            json={"authorization_id": perm_auth_id, "notes": "Third permanent check-in"},
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        assert response3.status_code == 200, f"Third permanent check-in should succeed: {response3.status_code}"
        print(f"✓ Third permanent check-in successful")
        print(f"✓ PERMANENT authorizations correctly allow multiple check-ins")
    
    def test_10_include_used_parameter_shows_used_authorizations(self):
        """GET /guard/authorizations?include_used=true should show used authorizations"""
        # Create and use a temporary authorization
        auth_id = self.test_05_first_checkin_returns_200()
        
        # Login as guard
        assert self.login_as_guard(), "Must login as guard"
        
        # Get authorizations WITH include_used=true
        response = self.session.get(
            f"{BASE_URL}/api/guard/authorizations?include_used=true",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        assert response.status_code == 200, f"Should get authorizations: {response.status_code}"
        
        authorizations = response.json()
        
        # Find our used authorization
        found = False
        for auth in authorizations:
            if auth.get("id") == auth_id:
                found = True
                assert auth.get("status") == "used", f"Status should be 'used', got: {auth.get('status')}"
                print(f"✓ Used authorization found when include_used=true")
                print(f"  - Status: {auth.get('status')}")
                break
        
        assert found, "Used authorization should appear when include_used=true"


class TestEndpointAvailability:
    """Quick tests to verify all required endpoints are available"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_guard_token(self):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_guard_authorizations_endpoint_exists(self):
        """GET /guard/authorizations endpoint should exist"""
        token = self.get_guard_token()
        assert token, "Guard login should succeed"
        
        response = self.session.get(
            f"{BASE_URL}/api/guard/authorizations",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [200, 401, 403], f"Endpoint should exist: {response.status_code}"
        print(f"✓ GET /guard/authorizations endpoint exists (status: {response.status_code})")
    
    def test_guard_checkin_endpoint_exists(self):
        """POST /guard/checkin endpoint should exist"""
        token = self.get_guard_token()
        assert token, "Guard login should succeed"
        
        # Send minimal data to test endpoint exists
        response = self.session.post(
            f"{BASE_URL}/api/guard/checkin",
            json={"visitor_name": "Test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404, f"Endpoint should exist: {response.status_code}"
        print(f"✓ POST /guard/checkin endpoint exists (status: {response.status_code})")
    
    def test_guard_entries_today_endpoint_exists(self):
        """GET /guard/entries-today endpoint should exist"""
        token = self.get_guard_token()
        assert token, "Guard login should succeed"
        
        response = self.session.get(
            f"{BASE_URL}/api/guard/entries-today",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [200, 401, 403], f"Endpoint should exist: {response.status_code}"
        print(f"✓ GET /guard/entries-today endpoint exists (status: {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
