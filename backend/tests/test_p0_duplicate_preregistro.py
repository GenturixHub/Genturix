"""
P0 Bug Fix Test: Pre-registraciones de visitantes re-usadas infinitamente

This test verifies the fix for the critical bug where:
- Temporary/Extended visitor authorizations could be used multiple times
- After check-in, the authorization should disappear from pending list
- Second check-in attempt should return 409 Conflict

Test scenarios:
1. TEMPORARY authorization: single use, then blocked
2. EXTENDED authorization: single use, then blocked  
3. PERMANENT authorization: can be used multiple times (expected behavior)
4. Diagnose endpoint identifies problematic authorizations
5. Cleanup endpoint fixes legacy data
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"
RESIDENT_EMAIL = "residente@genturix.com"
RESIDENT_PASSWORD = "Resi123!"


class TestP0DuplicatePreregistro:
    """Test suite for P0 bug: duplicate pre-registration check-ins"""
    
    guard_token = None
    resident_token = None
    test_auth_id = None
    test_permanent_auth_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup tokens before each test class"""
        if not TestP0DuplicatePreregistro.guard_token:
            # Login as guard
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": GUARD_EMAIL,
                "password": GUARD_PASSWORD
            })
            if response.status_code == 200:
                TestP0DuplicatePreregistro.guard_token = response.json().get("access_token")
                print(f"✓ Guard login successful")
            else:
                pytest.skip(f"Guard login failed: {response.status_code} - {response.text}")
        
        if not TestP0DuplicatePreregistro.resident_token:
            # Login as resident
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": RESIDENT_EMAIL,
                "password": RESIDENT_PASSWORD
            })
            if response.status_code == 200:
                TestP0DuplicatePreregistro.resident_token = response.json().get("access_token")
                print(f"✓ Resident login successful")
            else:
                pytest.skip(f"Resident login failed: {response.status_code} - {response.text}")
    
    def get_guard_headers(self):
        return {"Authorization": f"Bearer {TestP0DuplicatePreregistro.guard_token}"}
    
    def get_resident_headers(self):
        return {"Authorization": f"Bearer {TestP0DuplicatePreregistro.resident_token}"}
    
    # ==================== TEST 1: Create TEMPORARY authorization ====================
    def test_01_resident_creates_temporary_authorization(self):
        """Resident creates a TEMPORARY authorization - should have status='pending'"""
        today = datetime.now().strftime("%Y-%m-%d")
        unique_name = f"TEST_Temporal_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/authorizations",
            headers=self.get_resident_headers(),
            json={
                "visitor_name": unique_name,
                "identification_number": "12345678",
                "authorization_type": "temporary",
                "valid_from": today,
                "valid_to": today,
                "notes": "Test P0 bug fix - temporary auth"
            }
        )
        
        # API returns 200 for creation (not 201)
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Store for later tests
        TestP0DuplicatePreregistro.test_auth_id = data.get("id")
        assert TestP0DuplicatePreregistro.test_auth_id, "Authorization ID should be returned"
        
        # Verify status is pending
        assert data.get("status") == "pending", f"Expected status='pending', got '{data.get('status')}'"
        assert data.get("authorization_type") == "temporary"
        print(f"✓ Created TEMPORARY auth: {unique_name} (id: {data.get('id')[:12]}...)")
    
    # ==================== TEST 2: Guard sees authorization in pending list ====================
    def test_02_guard_sees_authorization_in_pending_list(self):
        """Guard should see the new authorization in /guard/authorizations"""
        assert TestP0DuplicatePreregistro.test_auth_id, "test_auth_id not set - run test_01 first"
        
        response = requests.get(
            f"{BASE_URL}/api/guard/authorizations",
            headers=self.get_guard_headers()
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        authorizations = response.json()
        
        # Find our test authorization
        found = any(a.get("id") == TestP0DuplicatePreregistro.test_auth_id for a in authorizations)
        assert found, f"Authorization {TestP0DuplicatePreregistro.test_auth_id[:12]}... not found in pending list"
        print(f"✓ Authorization visible in pending list ({len(authorizations)} total)")
    
    # ==================== TEST 3: First check-in succeeds ====================
    def test_03_first_checkin_returns_200(self):
        """First check-in with TEMPORARY authorization should succeed"""
        assert TestP0DuplicatePreregistro.test_auth_id, "test_auth_id not set - run test_01 first"
        
        response = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.get_guard_headers(),
            json={
                "authorization_id": TestP0DuplicatePreregistro.test_auth_id,
                "notes": "First check-in - should succeed"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("is_authorized") == True, f"Expected is_authorized=True, got {data}"
        print(f"✓ First check-in succeeded - entry_id: {data.get('entry', {}).get('id', 'N/A')[:12]}...")
    
    # ==================== TEST 4: Second check-in returns 409 ====================
    def test_04_second_checkin_returns_409(self):
        """Second check-in with SAME TEMPORARY authorization should return 409 Conflict"""
        assert TestP0DuplicatePreregistro.test_auth_id, "test_auth_id not set - run test_01 first"
        
        response = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.get_guard_headers(),
            json={
                "authorization_id": TestP0DuplicatePreregistro.test_auth_id,
                "notes": "Second check-in - should be blocked"
            }
        )
        
        assert response.status_code == 409, f"Expected 409 Conflict, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify error message mentions authorization already used
        detail = data.get("detail", "")
        assert "ya" in detail.lower() or "utilizada" in detail.lower() or "already" in detail.lower(), \
            f"Error message should mention 'already used': {detail}"
        print(f"✓ Second check-in blocked with 409: {detail}")
    
    # ==================== TEST 5: Authorization NOT in pending list after check-in ====================
    def test_05_authorization_not_in_pending_list_after_checkin(self):
        """After check-in, TEMPORARY authorization should NOT appear in pending list"""
        assert TestP0DuplicatePreregistro.test_auth_id, "test_auth_id not set - run test_01 first"
        
        response = requests.get(
            f"{BASE_URL}/api/guard/authorizations",
            headers=self.get_guard_headers()
        )
        
        assert response.status_code == 200
        authorizations = response.json()
        
        # Should NOT find our test authorization
        found = any(a.get("id") == TestP0DuplicatePreregistro.test_auth_id for a in authorizations)
        assert not found, f"Authorization should NOT be in pending list after check-in"
        print(f"✓ Authorization correctly removed from pending list")
    
    # ==================== TEST 6: Entry appears in entries-today ====================
    def test_06_entry_appears_in_entries_today(self):
        """The check-in should appear in /guard/entries-today"""
        assert TestP0DuplicatePreregistro.test_auth_id, "test_auth_id not set - run test_01 first"
        
        response = requests.get(
            f"{BASE_URL}/api/guard/entries-today",
            headers=self.get_guard_headers()
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        entries = response.json()
        
        # Find entry with our authorization_id
        found = any(e.get("authorization_id") == TestP0DuplicatePreregistro.test_auth_id for e in entries)
        assert found, "Entry should appear in entries-today"
        print(f"✓ Entry found in entries-today ({len(entries)} total entries)")
    
    # ==================== TEST 7: PERMANENT authorization can be used multiple times ====================
    def test_07_permanent_authorization_multiple_checkins(self):
        """PERMANENT authorizations should allow multiple check-ins (expected behavior)"""
        # Create a PERMANENT authorization
        unique_name = f"TEST_Permanente_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/authorizations",
            headers=self.get_resident_headers(),
            json={
                "visitor_name": unique_name,
                "identification_number": "87654321",
                "authorization_type": "permanent",
                "notes": "Test P0 - permanent auth should allow multiple uses"
            }
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"
        TestP0DuplicatePreregistro.test_permanent_auth_id = response.json().get("id")
        assert TestP0DuplicatePreregistro.test_permanent_auth_id, "Permanent auth ID should be returned"
        print(f"✓ Created PERMANENT auth: {unique_name}")
        
        # First check-in
        response1 = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.get_guard_headers(),
            json={
                "authorization_id": TestP0DuplicatePreregistro.test_permanent_auth_id,
                "notes": "First check-in for permanent"
            }
        )
        assert response1.status_code == 200, f"First check-in failed: {response1.status_code}"
        print(f"✓ First check-in for PERMANENT succeeded")
        
        # Second check-in - should also succeed for PERMANENT
        response2 = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.get_guard_headers(),
            json={
                "authorization_id": TestP0DuplicatePreregistro.test_permanent_auth_id,
                "notes": "Second check-in for permanent"
            }
        )
        assert response2.status_code == 200, f"Second check-in should succeed for PERMANENT: {response2.status_code}"
        print(f"✓ Second check-in for PERMANENT succeeded (expected behavior)")
    
    # ==================== TEST 8: Diagnose endpoint works ====================
    def test_08_diagnose_authorizations_endpoint(self):
        """Diagnose endpoint should identify problematic authorizations"""
        response = requests.get(
            f"{BASE_URL}/api/guard/diagnose-authorizations",
            headers=self.get_guard_headers()
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert "total_pending" in data, "Response should include total_pending"
        assert "authorizations" in data, "Response should include authorizations list"
        print(f"✓ Diagnose endpoint works - {data.get('total_pending')} pending authorizations")
    
    # ==================== TEST 9: Cleanup endpoint works ====================
    def test_09_cleanup_authorizations_endpoint(self):
        """Cleanup endpoint should fix legacy data"""
        response = requests.post(
            f"{BASE_URL}/api/guard/cleanup-authorizations",
            headers=self.get_guard_headers()
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data.get("success") == True, "Cleanup should return success=True"
        assert "fixed_count" in data, "Response should include fixed_count"
        assert "total_pending_checked" in data, "Response should include total_pending_checked"
        print(f"✓ Cleanup endpoint works - fixed {data.get('fixed_count')} authorizations")
    
    # ==================== TEST 10: include_used parameter shows used authorizations ====================
    def test_10_include_used_parameter(self):
        """include_used=true should show used authorizations"""
        assert TestP0DuplicatePreregistro.test_auth_id, "test_auth_id not set - run test_01 first"
        
        response = requests.get(
            f"{BASE_URL}/api/guard/authorizations?include_used=true",
            headers=self.get_guard_headers()
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        authorizations = response.json()
        
        # Should find our used test authorization
        found = any(a.get("id") == TestP0DuplicatePreregistro.test_auth_id for a in authorizations)
        assert found, f"Used authorization should appear when include_used=true (looking for {TestP0DuplicatePreregistro.test_auth_id[:12]}...)"
        print(f"✓ include_used=true shows used authorizations ({len(authorizations)} total)")


class TestExtendedAuthorization:
    """Test EXTENDED authorization type (date range + time windows)"""
    
    guard_token = None
    resident_token = None
    test_extended_auth_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup tokens"""
        if not TestExtendedAuthorization.guard_token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": GUARD_EMAIL,
                "password": GUARD_PASSWORD
            })
            if response.status_code == 200:
                TestExtendedAuthorization.guard_token = response.json().get("access_token")
        
        if not TestExtendedAuthorization.resident_token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": RESIDENT_EMAIL,
                "password": RESIDENT_PASSWORD
            })
            if response.status_code == 200:
                TestExtendedAuthorization.resident_token = response.json().get("access_token")
    
    def get_guard_headers(self):
        return {"Authorization": f"Bearer {TestExtendedAuthorization.guard_token}"}
    
    def get_resident_headers(self):
        return {"Authorization": f"Bearer {TestExtendedAuthorization.resident_token}"}
    
    def test_01_create_extended_authorization(self):
        """Create EXTENDED authorization with date range"""
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        unique_name = f"TEST_Extendido_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/authorizations",
            headers=self.get_resident_headers(),
            json={
                "visitor_name": unique_name,
                "identification_number": "11223344",
                "authorization_type": "extended",
                "valid_from": today.strftime("%Y-%m-%d"),
                "valid_to": tomorrow.strftime("%Y-%m-%d"),
                "allowed_hours_from": "08:00",
                "allowed_hours_to": "18:00",
                "notes": "Test P0 - extended auth"
            }
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        TestExtendedAuthorization.test_extended_auth_id = data.get("id")
        assert TestExtendedAuthorization.test_extended_auth_id, "Extended auth ID should be returned"
        
        assert data.get("authorization_type") == "extended"
        assert data.get("status") == "pending"
        print(f"✓ Created EXTENDED auth: {unique_name}")
    
    def test_02_first_checkin_extended_succeeds(self):
        """First check-in with EXTENDED authorization should succeed"""
        assert TestExtendedAuthorization.test_extended_auth_id, "test_extended_auth_id not set - run test_01 first"
        
        response = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.get_guard_headers(),
            json={
                "authorization_id": TestExtendedAuthorization.test_extended_auth_id,
                "notes": "First check-in for extended"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ First check-in for EXTENDED succeeded")
    
    def test_03_second_checkin_extended_blocked(self):
        """Second check-in with EXTENDED authorization should be blocked (409)"""
        assert TestExtendedAuthorization.test_extended_auth_id, "test_extended_auth_id not set - run test_01 first"
        
        response = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.get_guard_headers(),
            json={
                "authorization_id": TestExtendedAuthorization.test_extended_auth_id,
                "notes": "Second check-in for extended - should fail"
            }
        )
        
        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"
        print(f"✓ Second check-in for EXTENDED blocked with 409")


class TestRecurringAuthorization:
    """Test RECURRING authorization type (specific days of week)"""
    
    guard_token = None
    resident_token = None
    test_recurring_auth_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup tokens"""
        if not TestRecurringAuthorization.guard_token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": GUARD_EMAIL,
                "password": GUARD_PASSWORD
            })
            if response.status_code == 200:
                TestRecurringAuthorization.guard_token = response.json().get("access_token")
        
        if not TestRecurringAuthorization.resident_token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": RESIDENT_EMAIL,
                "password": RESIDENT_PASSWORD
            })
            if response.status_code == 200:
                TestRecurringAuthorization.resident_token = response.json().get("access_token")
    
    def get_guard_headers(self):
        return {"Authorization": f"Bearer {TestRecurringAuthorization.guard_token}"}
    
    def get_resident_headers(self):
        return {"Authorization": f"Bearer {TestRecurringAuthorization.resident_token}"}
    
    def test_01_create_recurring_authorization(self):
        """Create RECURRING authorization for specific days"""
        unique_name = f"TEST_Recurrente_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/authorizations",
            headers=self.get_resident_headers(),
            json={
                "visitor_name": unique_name,
                "identification_number": "55667788",
                "authorization_type": "recurring",
                "allowed_days": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
                "allowed_hours_from": "06:00",
                "allowed_hours_to": "22:00",
                "notes": "Test P0 - recurring auth"
            }
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        TestRecurringAuthorization.test_recurring_auth_id = data.get("id")
        assert TestRecurringAuthorization.test_recurring_auth_id, "Recurring auth ID should be returned"
        
        assert data.get("authorization_type") == "recurring"
        print(f"✓ Created RECURRING auth: {unique_name}")
    
    def test_02_recurring_allows_multiple_checkins(self):
        """RECURRING authorization should allow multiple check-ins (like permanent)"""
        assert TestRecurringAuthorization.test_recurring_auth_id, "test_recurring_auth_id not set - run test_01 first"
        
        # First check-in
        response1 = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.get_guard_headers(),
            json={
                "authorization_id": TestRecurringAuthorization.test_recurring_auth_id,
                "notes": "First check-in for recurring"
            }
        )
        assert response1.status_code == 200, f"First check-in failed: {response1.status_code}"
        print(f"✓ First check-in for RECURRING succeeded")
        
        # Second check-in - should also succeed for RECURRING
        response2 = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.get_guard_headers(),
            json={
                "authorization_id": TestRecurringAuthorization.test_recurring_auth_id,
                "notes": "Second check-in for recurring"
            }
        )
        assert response2.status_code == 200, f"Second check-in should succeed for RECURRING: {response2.status_code}"
        print(f"✓ Second check-in for RECURRING succeeded (expected behavior)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
