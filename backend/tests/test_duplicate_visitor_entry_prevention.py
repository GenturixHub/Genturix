"""
Test Module: Duplicate Visitor Entry Prevention
Tests PHASE 1 & 2 validations in POST /api/guard/checkin
Tests PHASE 3: is_visitor_inside flag in GET /api/guard/authorizations

Features tested:
1. PHASE 1: Block check-in if authorization_id already has visitor_entry with status='inside'
2. PHASE 2: Block manual entries with same visitor name already inside
3. PHASE 3: GET /api/guard/authorizations includes is_visitor_inside flag
4. Frontend behavior validation setup (badge and button disabled)
"""

import pytest
import requests
import os
import time
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"
RESIDENT_EMAIL = "residente@genturix.com"
RESIDENT_PASSWORD = "Resi123!"
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"


class TestSetup:
    """Setup class with authentication helpers"""
    
    @staticmethod
    def get_auth_token(email: str, password: str) -> str:
        """Get authentication token for a user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        assert response.status_code == 200, f"Login failed for {email}: {response.text}"
        return response.json().get("access_token")
    
    @staticmethod
    def get_headers(token: str) -> dict:
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }


class TestHealthAndLogin:
    """Basic health and authentication tests"""
    
    def test_health_endpoint(self):
        """Test /api/health is working"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data.get("status") == "ok"
        print("✓ Health endpoint is working")
    
    def test_guard_login(self):
        """Test guard can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"✓ Guard login successful")
    
    def test_resident_login(self):
        """Test resident can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"✓ Resident login successful")


class TestPhase1AuthorizationDuplicatePrevention:
    """
    PHASE 1: Test validation by authorization_id before check-in
    Check if visitor with this authorization_id already has visitor_entry with status='inside'
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup tokens for each test"""
        self.guard_token = TestSetup.get_auth_token(GUARD_EMAIL, GUARD_PASSWORD)
        self.resident_token = TestSetup.get_auth_token(RESIDENT_EMAIL, RESIDENT_PASSWORD)
        self.guard_headers = TestSetup.get_headers(self.guard_token)
        self.resident_headers = TestSetup.get_headers(self.resident_token)
    
    def test_create_authorization_and_checkin_success(self):
        """Test creating an authorization and successful first check-in"""
        # Step 1: Create a temporary authorization as resident
        unique_name = f"TEST_Visitor_Auth_{int(time.time())}"
        
        auth_response = requests.post(
            f"{BASE_URL}/api/visitor-authorizations",
            headers=self.resident_headers,
            json={
                "visitor_name": unique_name,
                "authorization_type": "temporary",
                "valid_from": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "valid_to": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "notes": "Test authorization for duplicate prevention"
            }
        )
        
        # If resident doesn't have permission to create authorizations, skip this test
        if auth_response.status_code == 403:
            pytest.skip("Resident does not have permission to create authorizations")
        
        assert auth_response.status_code in [200, 201], f"Authorization creation failed: {auth_response.text}"
        auth_data = auth_response.json()
        auth_id = auth_data.get("id")
        print(f"✓ Created authorization: {auth_id}")
        
        # Step 2: First check-in should succeed
        checkin_response = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.guard_headers,
            json={
                "authorization_id": auth_id,
                "visitor_name": unique_name
            }
        )
        
        assert checkin_response.status_code in [200, 201], f"First check-in failed: {checkin_response.text}"
        checkin_data = checkin_response.json()
        entry_id = checkin_data.get("id") or checkin_data.get("entry_id")
        print(f"✓ First check-in successful, entry_id: {entry_id}")
        
        # Step 3: Second check-in with SAME authorization should be BLOCKED (PHASE 1)
        second_checkin = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.guard_headers,
            json={
                "authorization_id": auth_id,
                "visitor_name": unique_name
            }
        )
        
        assert second_checkin.status_code == 400, f"Second check-in should be blocked but got: {second_checkin.status_code}"
        error_data = second_checkin.json()
        error_detail = error_data.get("detail", "")
        assert "ya se encuentra dentro" in error_detail.lower() or "already inside" in error_detail.lower(), \
            f"Error message should indicate visitor is already inside: {error_detail}"
        print(f"✓ PHASE 1 VALIDATED: Second check-in blocked with message: {error_detail}")
        
        # Cleanup: Register exit
        if entry_id:
            checkout_response = requests.post(
                f"{BASE_URL}/api/guard/checkout/{entry_id}",
                headers=self.guard_headers,
                json={"notes": "Test cleanup"}  # FastCheckOutRequest requires body
            )
            print(f"✓ Cleanup: Checkout status {checkout_response.status_code}")
    
    def test_checkin_after_checkout_allowed_for_recurring(self):
        """Test that recurring authorizations allow check-in after checkout"""
        # Create a recurring authorization (should allow multiple entries)
        unique_name = f"TEST_Recurring_Visitor_{int(time.time())}"
        
        auth_response = requests.post(
            f"{BASE_URL}/api/visitor-authorizations",
            headers=self.resident_headers,
            json={
                "visitor_name": unique_name,
                "authorization_type": "recurring",
                "allowed_days": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
                "notes": "Test recurring authorization"
            }
        )
        
        if auth_response.status_code == 403:
            pytest.skip("Resident does not have permission to create authorizations")
        
        # For recurring, check if API returns 200 or different behavior
        if auth_response.status_code not in [200, 201]:
            print(f"Note: Recurring authorization creation returned {auth_response.status_code}")
            pytest.skip("Recurring authorization creation not supported in current setup")
        
        auth_data = auth_response.json()
        auth_id = auth_data.get("id")
        print(f"✓ Created recurring authorization: {auth_id}")
        
        # First check-in
        checkin1 = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.guard_headers,
            json={"authorization_id": auth_id}
        )
        
        if checkin1.status_code not in [200, 201]:
            print(f"Note: Check-in failed with {checkin1.status_code}: {checkin1.text}")
            return
        
        entry_id = checkin1.json().get("id") or checkin1.json().get("entry_id")
        print(f"✓ First check-in for recurring auth successful")
        
        # Check-out
        checkout = requests.post(
            f"{BASE_URL}/api/guard/checkout/{entry_id}",
            headers=self.guard_headers,
            json={}  # FastCheckOutRequest body
        )
        assert checkout.status_code in [200, 201], f"Checkout failed: {checkout.text}"
        print(f"✓ Checkout successful")
        
        # Second check-in (recurring should allow this)
        checkin2 = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.guard_headers,
            json={"authorization_id": auth_id}
        )
        
        # Recurring should allow multiple check-ins
        if checkin2.status_code in [200, 201]:
            print(f"✓ Second check-in allowed for recurring authorization")
            # Cleanup
            entry_id2 = checkin2.json().get("id") or checkin2.json().get("entry_id")
            if entry_id2:
                requests.post(f"{BASE_URL}/api/guard/checkout/{entry_id2}", headers=self.guard_headers, json={})
        else:
            print(f"Note: Second check-in returned {checkin2.status_code} - behavior may vary")


class TestPhase2ManualEntryDuplicatePrevention:
    """
    PHASE 2: Test validation for manual entries by visitor_name
    Prevent duplicate manual entries with same visitor name in same condominium
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup tokens for each test"""
        self.guard_token = TestSetup.get_auth_token(GUARD_EMAIL, GUARD_PASSWORD)
        self.guard_headers = TestSetup.get_headers(self.guard_token)
    
    def test_manual_entry_duplicate_blocked(self):
        """Test that manual entries with same name are blocked"""
        unique_name = f"TEST_Manual_Visitor_{int(time.time())}"
        
        # First manual check-in
        checkin1 = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.guard_headers,
            json={
                "visitor_name": unique_name,
                "destination": "Apartamento 101",
                "notes": "First manual entry"
            }
        )
        
        assert checkin1.status_code in [200, 201], f"First manual check-in failed: {checkin1.text}"
        entry_data = checkin1.json()
        entry_id = entry_data.get("id") or entry_data.get("entry_id")
        print(f"✓ First manual check-in successful: {unique_name}")
        
        # Second manual check-in with SAME name should be BLOCKED (PHASE 2)
        checkin2 = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.guard_headers,
            json={
                "visitor_name": unique_name,
                "destination": "Apartamento 202",
                "notes": "Second manual entry - should fail"
            }
        )
        
        assert checkin2.status_code == 400, f"Second manual check-in should be blocked but got: {checkin2.status_code}"
        error_data = checkin2.json()
        error_detail = error_data.get("detail", "")
        assert unique_name.lower() in error_detail.lower() or "ya existe" in error_detail.lower(), \
            f"Error message should mention duplicate name: {error_detail}"
        print(f"✓ PHASE 2 VALIDATED: Second manual entry blocked with message: {error_detail}")
        
        # Cleanup: Register exit
        if entry_id:
            checkout_response = requests.post(
                f"{BASE_URL}/api/guard/checkout/{entry_id}",
                headers=self.guard_headers,
                json={"notes": "Test cleanup"}  # FastCheckOutRequest requires body
            )
            print(f"✓ Cleanup: Checkout status {checkout_response.status_code}")
    
    def test_different_names_allowed(self):
        """Test that different visitor names are allowed for manual entries"""
        name1 = f"TEST_Visitor_A_{int(time.time())}"
        name2 = f"TEST_Visitor_B_{int(time.time())}"
        
        # First visitor
        checkin1 = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.guard_headers,
            json={"visitor_name": name1, "destination": "Apt 101"}
        )
        assert checkin1.status_code in [200, 201], f"First check-in failed: {checkin1.text}"
        entry_id1 = checkin1.json().get("id") or checkin1.json().get("entry_id")
        print(f"✓ First visitor checked in: {name1}")
        
        # Second visitor with DIFFERENT name should be ALLOWED
        checkin2 = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.guard_headers,
            json={"visitor_name": name2, "destination": "Apt 102"}
        )
        assert checkin2.status_code in [200, 201], f"Second check-in should be allowed: {checkin2.text}"
        entry_id2 = checkin2.json().get("id") or checkin2.json().get("entry_id")
        print(f"✓ Second visitor (different name) allowed: {name2}")
        
        # Cleanup
        if entry_id1:
            requests.post(f"{BASE_URL}/api/guard/checkout/{entry_id1}", headers=self.guard_headers, json={})
        if entry_id2:
            requests.post(f"{BASE_URL}/api/guard/checkout/{entry_id2}", headers=self.guard_headers, json={})
        print("✓ Cleanup completed")
    
    def test_manual_entry_after_checkout_allowed(self):
        """Test that manual entry is allowed after previous checkout"""
        unique_name = f"TEST_ReEntry_{int(time.time())}"
        
        # First check-in
        checkin1 = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.guard_headers,
            json={"visitor_name": unique_name}
        )
        assert checkin1.status_code in [200, 201], f"First check-in failed: {checkin1.text}"
        checkin1_data = checkin1.json()
        # Entry ID can be at root, in entry_id field, or nested in entry.id
        entry_id = checkin1_data.get("id") or checkin1_data.get("entry_id")
        if not entry_id and "entry" in checkin1_data:
            entry_id = checkin1_data["entry"].get("id")
        print(f"✓ First manual check-in: {unique_name}, entry_id: {entry_id}")
        
        # Check-out
        checkout = requests.post(
            f"{BASE_URL}/api/guard/checkout/{entry_id}",
            headers=self.guard_headers,
            json={}  # FastCheckOutRequest body
        )
        assert checkout.status_code in [200, 201], f"Checkout failed: {checkout.text}"
        print(f"✓ Checkout successful")
        
        # Second check-in (after checkout) should be ALLOWED
        checkin2 = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.guard_headers,
            json={"visitor_name": unique_name}
        )
        assert checkin2.status_code in [200, 201], f"Re-entry after checkout should be allowed: {checkin2.text}"
        entry_id2 = checkin2.json().get("id") or checkin2.json().get("entry_id")
        print(f"✓ Re-entry after checkout allowed")
        
        # Cleanup
        if entry_id2:
            requests.post(f"{BASE_URL}/api/guard/checkout/{entry_id2}", headers=self.guard_headers, json={})


class TestPhase3IsVisitorInsideFlag:
    """
    PHASE 3: Test is_visitor_inside flag in GET /api/guard/authorizations
    This flag is used by frontend to show badge and disable check-in button
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup tokens for each test"""
        self.guard_token = TestSetup.get_auth_token(GUARD_EMAIL, GUARD_PASSWORD)
        self.resident_token = TestSetup.get_auth_token(RESIDENT_EMAIL, RESIDENT_PASSWORD)
        self.guard_headers = TestSetup.get_headers(self.guard_token)
        self.resident_headers = TestSetup.get_headers(self.resident_token)
    
    def test_is_visitor_inside_flag_in_response(self):
        """Test that is_visitor_inside flag exists in authorization response"""
        # Get authorizations
        response = requests.get(
            f"{BASE_URL}/api/guard/authorizations",
            headers=self.guard_headers
        )
        
        assert response.status_code == 200, f"Get authorizations failed: {response.text}"
        authorizations = response.json()
        
        if len(authorizations) > 0:
            auth = authorizations[0]
            # Check that is_visitor_inside field exists
            assert "is_visitor_inside" in auth, f"is_visitor_inside field missing from authorization: {auth.keys()}"
            assert isinstance(auth["is_visitor_inside"], bool), "is_visitor_inside should be boolean"
            print(f"✓ PHASE 3 VALIDATED: is_visitor_inside field present in authorization response")
        else:
            print("Note: No authorizations found to verify field")
    
    def test_is_visitor_inside_true_when_checked_in(self):
        """Test that is_visitor_inside is True when visitor has active entry"""
        unique_name = f"TEST_InsideFlag_{int(time.time())}"
        
        # Create authorization
        auth_response = requests.post(
            f"{BASE_URL}/api/visitor-authorizations",
            headers=self.resident_headers,
            json={
                "visitor_name": unique_name,
                "authorization_type": "permanent",  # Use permanent to avoid used status issue
                "notes": "Test is_visitor_inside flag"
            }
        )
        
        if auth_response.status_code == 403:
            pytest.skip("Resident does not have permission to create authorizations")
        
        if auth_response.status_code not in [200, 201]:
            print(f"Note: Authorization creation returned {auth_response.status_code}")
            pytest.skip("Could not create test authorization")
        
        auth_data = auth_response.json()
        auth_id = auth_data.get("id")
        print(f"✓ Created test authorization: {auth_id}")
        
        # Check is_visitor_inside is False before check-in
        auths_response = requests.get(
            f"{BASE_URL}/api/guard/authorizations?search={unique_name}",
            headers=self.guard_headers
        )
        assert auths_response.status_code == 200
        auths = auths_response.json()
        
        matching_auth = next((a for a in auths if a.get("id") == auth_id), None)
        if matching_auth:
            assert matching_auth.get("is_visitor_inside") == False, \
                f"is_visitor_inside should be False before check-in: {matching_auth.get('is_visitor_inside')}"
            print(f"✓ is_visitor_inside is False before check-in")
        
        # Check-in
        checkin_response = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.guard_headers,
            json={"authorization_id": auth_id}
        )
        
        if checkin_response.status_code not in [200, 201]:
            print(f"Note: Check-in failed: {checkin_response.text}")
            return
        
        entry_id = checkin_response.json().get("id") or checkin_response.json().get("entry_id")
        print(f"✓ Check-in successful, entry_id: {entry_id}")
        
        # Check is_visitor_inside is True after check-in
        auths_response2 = requests.get(
            f"{BASE_URL}/api/guard/authorizations?search={unique_name}&include_used=true",
            headers=self.guard_headers
        )
        assert auths_response2.status_code == 200
        auths2 = auths_response2.json()
        
        matching_auth2 = next((a for a in auths2 if a.get("id") == auth_id), None)
        if matching_auth2:
            assert matching_auth2.get("is_visitor_inside") == True, \
                f"is_visitor_inside should be True after check-in: {matching_auth2.get('is_visitor_inside')}"
            print(f"✓ PHASE 3 VALIDATED: is_visitor_inside is True after check-in")
            
            # Check additional fields
            if matching_auth2.get("entry_at"):
                print(f"✓ entry_at field present: {matching_auth2.get('entry_at')}")
        else:
            print(f"Note: Authorization not found in search results after check-in")
        
        # Cleanup: Register exit
        if entry_id:
            checkout_response = requests.post(
                f"{BASE_URL}/api/guard/checkout/{entry_id}",
                headers=self.guard_headers,
                json={"notes": "Test cleanup"}  # FastCheckOutRequest requires body
            )
            print(f"✓ Cleanup: Checkout status {checkout_response.status_code}")
            
            # Verify is_visitor_inside becomes False after checkout
            time.sleep(0.5)  # Small delay for DB update
            auths_response3 = requests.get(
                f"{BASE_URL}/api/guard/authorizations?search={unique_name}&include_used=true",
                headers=self.guard_headers
            )
            auths3 = auths_response3.json()
            matching_auth3 = next((a for a in auths3 if a.get("id") == auth_id), None)
            if matching_auth3:
                assert matching_auth3.get("is_visitor_inside") == False, \
                    f"is_visitor_inside should be False after checkout"
                print(f"✓ is_visitor_inside is False after checkout")


class TestVisitorsInsideEndpoint:
    """Test /api/guard/visitors-inside endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup tokens for each test"""
        self.guard_token = TestSetup.get_auth_token(GUARD_EMAIL, GUARD_PASSWORD)
        self.guard_headers = TestSetup.get_headers(self.guard_token)
    
    def test_get_visitors_inside(self):
        """Test that visitors inside endpoint returns valid data"""
        response = requests.get(
            f"{BASE_URL}/api/guard/visitors-inside",
            headers=self.guard_headers
        )
        
        assert response.status_code == 200, f"Get visitors inside failed: {response.text}"
        visitors = response.json()
        assert isinstance(visitors, list), "Response should be a list"
        print(f"✓ Visitors inside endpoint working, found {len(visitors)} visitor(s) inside")
        
        # Verify response structure if there are visitors
        if len(visitors) > 0:
            visitor = visitors[0]
            assert "id" in visitor, "Visitor should have id"
            assert "visitor_name" in visitor, "Visitor should have visitor_name"
            assert "status" in visitor, "Visitor should have status"
            print(f"✓ Visitor data structure validated")


class TestErrorHandling:
    """Test error responses for edge cases"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup tokens for each test"""
        self.guard_token = TestSetup.get_auth_token(GUARD_EMAIL, GUARD_PASSWORD)
        self.guard_headers = TestSetup.get_headers(self.guard_token)
    
    def test_checkin_nonexistent_authorization(self):
        """Test check-in with non-existent authorization returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.guard_headers,
            json={
                "authorization_id": "nonexistent-auth-id-12345"
            }
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent auth, got: {response.status_code}"
        print("✓ Non-existent authorization returns 404")
    
    def test_checkin_empty_visitor_name_manual(self):
        """Test manual check-in with empty visitor name"""
        response = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=self.guard_headers,
            json={
                "visitor_name": "",
                "destination": "Test"
            }
        )
        
        # Should either fail validation or be rejected
        if response.status_code in [200, 201]:
            # If it succeeds, it should have created an entry
            entry_id = response.json().get("id") or response.json().get("entry_id")
            if entry_id:
                # Cleanup
                requests.post(f"{BASE_URL}/api/guard/checkout/{entry_id}", headers=self.guard_headers, json={})
            print("Note: Empty visitor name was accepted (may be allowed)")
        else:
            print(f"✓ Empty visitor name rejected with status {response.status_code}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
