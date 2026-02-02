"""
P0 Bug Fix Test: Prevent deletion of authorizations when visitor is inside

Tests the fix for:
- Resident could delete authorizations even when visitor was inside
- Guard would lose track of who's inside the condominium

Test scenarios:
1. DELETE /api/authorizations/{id} returns 403 if has_visitor_inside=true
2. GET /api/authorizations/my includes has_visitor_inside field
3. Resident can delete PENDING authorization (no visitor inside)
4. Resident CANNOT delete authorization when visitor is INSIDE
5. Guard can still see active visitors regardless of resident actions
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
RESIDENT_EMAIL = "residente@genturix.com"
RESIDENT_PASSWORD = "Resi123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"


class TestP0DeleteAuthorizationInsideFix:
    """Test P0 bug fix: Prevent deletion when visitor is inside"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.resident_token = None
        self.guard_token = None
        self.test_auth_id = None
        self.test_entry_id = None
    
    def login_as_resident(self):
        """Login as resident and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        data = response.json()
        self.resident_token = data["access_token"]
        return data
    
    def login_as_guard(self):
        """Login as guard and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        data = response.json()
        self.guard_token = data["access_token"]
        return data
    
    def test_01_resident_login(self):
        """Test resident can login"""
        data = self.login_as_resident()
        assert "access_token" in data
        assert data["user"]["email"] == RESIDENT_EMAIL
        print(f"✓ Resident login successful: {RESIDENT_EMAIL}")
    
    def test_02_guard_login(self):
        """Test guard can login"""
        data = self.login_as_guard()
        assert "access_token" in data
        assert data["user"]["email"] == GUARD_EMAIL
        print(f"✓ Guard login successful: {GUARD_EMAIL}")
    
    def test_03_get_my_authorizations_includes_has_visitor_inside(self):
        """Test GET /api/authorizations/my includes has_visitor_inside field"""
        self.login_as_resident()
        
        response = self.session.get(
            f"{BASE_URL}/api/authorizations/my",
            headers={"Authorization": f"Bearer {self.resident_token}"}
        )
        
        assert response.status_code == 200, f"Failed to get authorizations: {response.text}"
        authorizations = response.json()
        
        print(f"✓ Got {len(authorizations)} authorizations")
        
        # Check that has_visitor_inside field exists in all authorizations
        for auth in authorizations:
            assert "has_visitor_inside" in auth, f"Missing has_visitor_inside field in auth {auth.get('id')}"
            print(f"  - {auth.get('visitor_name')}: has_visitor_inside={auth.get('has_visitor_inside')}")
        
        print("✓ All authorizations have has_visitor_inside field")
    
    def test_04_find_authorization_with_visitor_inside(self):
        """Find an authorization that has a visitor currently inside"""
        self.login_as_resident()
        
        response = self.session.get(
            f"{BASE_URL}/api/authorizations/my",
            headers={"Authorization": f"Bearer {self.resident_token}"}
        )
        
        assert response.status_code == 200
        authorizations = response.json()
        
        # Find authorization with visitor inside
        auth_with_inside = None
        for auth in authorizations:
            if auth.get("has_visitor_inside") == True:
                auth_with_inside = auth
                break
        
        if auth_with_inside:
            print(f"✓ Found authorization with visitor inside: {auth_with_inside.get('visitor_name')} (ID: {auth_with_inside.get('id')})")
            return auth_with_inside
        else:
            print("⚠ No authorization with visitor inside found - will test with PENDING authorization")
            return None
    
    def test_05_cannot_delete_authorization_when_visitor_inside(self):
        """Test that resident CANNOT delete authorization when visitor is inside"""
        self.login_as_resident()
        
        # Get authorizations
        response = self.session.get(
            f"{BASE_URL}/api/authorizations/my",
            headers={"Authorization": f"Bearer {self.resident_token}"}
        )
        
        assert response.status_code == 200
        authorizations = response.json()
        
        # Find authorization with visitor inside
        auth_with_inside = None
        for auth in authorizations:
            if auth.get("has_visitor_inside") == True:
                auth_with_inside = auth
                break
        
        if not auth_with_inside:
            pytest.skip("No authorization with visitor inside found - cannot test deletion block")
        
        auth_id = auth_with_inside.get("id")
        visitor_name = auth_with_inside.get("visitor_name")
        
        print(f"Attempting to delete authorization for '{visitor_name}' (visitor is INSIDE)...")
        
        # Try to delete - should fail with 403
        delete_response = self.session.delete(
            f"{BASE_URL}/api/authorizations/{auth_id}",
            headers={"Authorization": f"Bearer {self.resident_token}"}
        )
        
        assert delete_response.status_code == 403, f"Expected 403 Forbidden, got {delete_response.status_code}: {delete_response.text}"
        
        error_data = delete_response.json()
        assert "detail" in error_data
        assert "dentro" in error_data["detail"].lower() or "inside" in error_data["detail"].lower(), \
            f"Error message should mention visitor is inside: {error_data['detail']}"
        
        print(f"✓ DELETE correctly blocked with 403: {error_data['detail']}")
    
    def test_06_can_delete_pending_authorization(self):
        """Test that resident CAN delete PENDING authorization (no visitor inside)"""
        self.login_as_resident()
        
        # First create a new temporary authorization
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        create_response = self.session.post(
            f"{BASE_URL}/api/authorizations",
            headers={"Authorization": f"Bearer {self.resident_token}"},
            json={
                "visitor_name": "TEST_DeleteTest_Visitor",
                "identification_number": "TEST-12345",
                "authorization_type": "temporary",
                "valid_from": tomorrow,
                "valid_to": tomorrow,
                "notes": "Test authorization for deletion test"
            }
        )
        
        assert create_response.status_code in [200, 201], f"Failed to create test authorization: {create_response.text}"
        created_auth = create_response.json()
        test_auth_id = created_auth.get("id")
        
        print(f"✓ Created test authorization: {test_auth_id}")
        
        # Verify it has has_visitor_inside=false
        get_response = self.session.get(
            f"{BASE_URL}/api/authorizations/my",
            headers={"Authorization": f"Bearer {self.resident_token}"}
        )
        
        authorizations = get_response.json()
        test_auth = next((a for a in authorizations if a.get("id") == test_auth_id), None)
        
        assert test_auth is not None, "Test authorization not found in list"
        assert test_auth.get("has_visitor_inside") == False, "New authorization should have has_visitor_inside=false"
        
        print(f"✓ Verified has_visitor_inside=false for new authorization")
        
        # Now delete it - should succeed
        delete_response = self.session.delete(
            f"{BASE_URL}/api/authorizations/{test_auth_id}",
            headers={"Authorization": f"Bearer {self.resident_token}"}
        )
        
        assert delete_response.status_code == 200, f"Expected 200 OK, got {delete_response.status_code}: {delete_response.text}"
        
        print(f"✓ Successfully deleted PENDING authorization")
    
    def test_07_guard_can_see_active_visitors(self):
        """Test that guard can see visitors currently inside"""
        self.login_as_guard()
        
        # Get active visitors (inside)
        response = self.session.get(
            f"{BASE_URL}/api/guard/visitors/active",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        assert response.status_code == 200, f"Failed to get active visitors: {response.text}"
        active_visitors = response.json()
        
        print(f"✓ Guard can see {len(active_visitors)} active visitors inside")
        
        for visitor in active_visitors:
            print(f"  - {visitor.get('visitor_name')} (status: {visitor.get('status')})")
        
        return active_visitors
    
    def test_08_guard_authorizations_endpoint(self):
        """Test guard can access authorizations list"""
        self.login_as_guard()
        
        response = self.session.get(
            f"{BASE_URL}/api/guard/authorizations",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        assert response.status_code == 200, f"Failed to get guard authorizations: {response.text}"
        authorizations = response.json()
        
        print(f"✓ Guard can see {len(authorizations)} authorizations")
        
        return authorizations


class TestFrontendIntegration:
    """Test frontend integration with has_visitor_inside field"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_authorizations_response_structure(self):
        """Verify the response structure for frontend consumption"""
        # Login as resident
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Get authorizations
        response = self.session.get(
            f"{BASE_URL}/api/authorizations/my",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        authorizations = response.json()
        
        if len(authorizations) == 0:
            pytest.skip("No authorizations to test structure")
        
        # Check required fields for frontend
        required_fields = [
            "id",
            "visitor_name",
            "authorization_type",
            "is_active",
            "has_visitor_inside",  # P0 FIX: This field is critical
            "is_currently_valid",
            "validity_status",
            "validity_message"
        ]
        
        for auth in authorizations:
            for field in required_fields:
                assert field in auth, f"Missing required field '{field}' in authorization {auth.get('id')}"
        
        print(f"✓ All {len(authorizations)} authorizations have required fields for frontend")
        
        # Count authorizations by has_visitor_inside status
        inside_count = sum(1 for a in authorizations if a.get("has_visitor_inside") == True)
        outside_count = sum(1 for a in authorizations if a.get("has_visitor_inside") == False)
        
        print(f"  - With visitor inside: {inside_count}")
        print(f"  - Without visitor inside: {outside_count}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
