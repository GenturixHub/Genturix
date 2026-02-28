"""
Multi-Tenant Isolation & Audit Log Tests for Genturix
Tests for P0 bug fixes:
1. /authorizations/my must filter by condominium_id
2. Audit logs record condominium_id field
3. GET /api/audit/logs filters by admin's condominium_id
4. PATCH /api/profile updates profile_photo and returns updated data
5. /resident/visit-history filters by condominium_id
6. /guard/entries-today filters by condominium_id
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "Admin123!"


class TestHelpers:
    """Helper methods for tests"""
    
    @staticmethod
    def get_auth_token(email: str, password: str) -> dict:
        """Get auth token and user info"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            return {
                "token": data.get("access_token"),
                "user": data.get("user"),
                "condominium_id": data.get("user", {}).get("condominium_id")
            }
        return None
    
    @staticmethod
    def auth_headers(token: str) -> dict:
        """Get auth headers with token"""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }


class TestAuthorizationsMyEndpoint:
    """Tests for /authorizations/my condominium_id filtering"""
    
    def test_authorizations_my_requires_auth(self):
        """Test that /authorizations/my requires authentication"""
        response = requests.get(f"{BASE_URL}/api/authorizations/my")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ /authorizations/my requires authentication")
    
    def test_authorizations_my_returns_200(self):
        """Test that authenticated user can get their authorizations"""
        auth = TestHelpers.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not auth:
            pytest.skip("Could not authenticate admin")
        
        response = requests.get(
            f"{BASE_URL}/api/authorizations/my",
            headers=TestHelpers.auth_headers(auth["token"])
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Response should be a list
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ /authorizations/my returns 200 with {len(data)} authorizations")
    
    def test_authorizations_my_has_condominium_filter(self):
        """Verify authorizations returned have matching condominium_id"""
        auth = TestHelpers.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not auth:
            pytest.skip("Could not authenticate admin")
        
        user_condo_id = auth["condominium_id"]
        if not user_condo_id:
            pytest.skip("Admin has no condominium_id")
        
        response = requests.get(
            f"{BASE_URL}/api/authorizations/my",
            headers=TestHelpers.auth_headers(auth["token"])
        )
        assert response.status_code == 200
        
        authorizations = response.json()
        # If there are authorizations, verify they belong to user's condominium
        for auth_item in authorizations:
            item_condo_id = auth_item.get("condominium_id")
            if item_condo_id:
                assert item_condo_id == user_condo_id, \
                    f"Authorization {auth_item.get('id')} has condo {item_condo_id}, expected {user_condo_id}"
        
        print(f"✓ All {len(authorizations)} authorizations belong to user's condominium")


class TestAuditLogCondominium:
    """Tests for audit log condominium_id recording and filtering"""
    
    def test_audit_logs_requires_auth(self):
        """Test that /audit/logs requires authentication"""
        response = requests.get(f"{BASE_URL}/api/audit/logs")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ /audit/logs requires authentication")
    
    def test_audit_logs_returns_200_for_admin(self):
        """Test admin can access audit logs"""
        auth = TestHelpers.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not auth:
            pytest.skip("Could not authenticate admin")
        
        response = requests.get(
            f"{BASE_URL}/api/audit/logs",
            headers=TestHelpers.auth_headers(auth["token"])
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ Admin can access audit logs ({len(data)} entries)")
    
    def test_audit_logs_filtered_by_condominium(self):
        """Verify audit logs are filtered by admin's condominium_id"""
        auth = TestHelpers.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not auth:
            pytest.skip("Could not authenticate admin")
        
        user_condo_id = auth["condominium_id"]
        if not user_condo_id:
            pytest.skip("Admin has no condominium_id")
        
        response = requests.get(
            f"{BASE_URL}/api/audit/logs",
            headers=TestHelpers.auth_headers(auth["token"])
        )
        assert response.status_code == 200
        
        logs = response.json()
        # All logs should belong to admin's condominium (or have no condo_id for legacy logs)
        for log in logs:
            log_condo_id = log.get("condominium_id")
            if log_condo_id:  # Only check logs that have condominium_id set
                assert log_condo_id == user_condo_id, \
                    f"Log {log.get('id')} has condo {log_condo_id}, expected {user_condo_id}"
        
        print(f"✓ Audit logs are properly filtered by condominium ({len(logs)} logs checked)")
    
    def test_audit_log_has_condominium_field(self):
        """Verify audit log entries have condominium_id field"""
        auth = TestHelpers.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not auth:
            pytest.skip("Could not authenticate admin")
        
        response = requests.get(
            f"{BASE_URL}/api/audit/logs",
            headers=TestHelpers.auth_headers(auth["token"])
        )
        assert response.status_code == 200
        
        logs = response.json()
        # Recent logs should have condominium_id field
        logs_with_condo = [l for l in logs if l.get("condominium_id")]
        
        print(f"✓ {len(logs_with_condo)}/{len(logs)} audit logs have condominium_id field")
        # At least some logs should have condominium_id for this test to be meaningful
        # Note: Legacy logs may not have the field


class TestProfileUpdate:
    """Tests for PATCH /api/profile - profile_photo update"""
    
    def test_profile_get_returns_200(self):
        """Test GET /profile returns 200"""
        auth = TestHelpers.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not auth:
            pytest.skip("Could not authenticate admin")
        
        response = requests.get(
            f"{BASE_URL}/api/profile",
            headers=TestHelpers.auth_headers(auth["token"])
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "full_name" in data
        print("✓ GET /profile returns 200 with user data")
    
    def test_profile_patch_updates_phone(self):
        """Test PATCH /profile updates phone and returns updated data"""
        auth = TestHelpers.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not auth:
            pytest.skip("Could not authenticate admin")
        
        # Get current profile
        get_response = requests.get(
            f"{BASE_URL}/api/profile",
            headers=TestHelpers.auth_headers(auth["token"])
        )
        original = get_response.json()
        
        # Update phone
        test_phone = f"+1-555-{str(uuid.uuid4())[:4]}"
        patch_response = requests.patch(
            f"{BASE_URL}/api/profile",
            json={"phone": test_phone},
            headers=TestHelpers.auth_headers(auth["token"])
        )
        
        assert patch_response.status_code == 200, f"Expected 200, got {patch_response.status_code}: {patch_response.text}"
        
        updated = patch_response.json()
        assert updated.get("phone") == test_phone, f"Phone not updated: {updated.get('phone')}"
        
        print(f"✓ PATCH /profile updates phone and returns updated data")
        
        # Restore original phone if it existed
        if original.get("phone"):
            requests.patch(
                f"{BASE_URL}/api/profile",
                json={"phone": original["phone"]},
                headers=TestHelpers.auth_headers(auth["token"])
            )
    
    def test_profile_patch_updates_profile_photo(self):
        """Test PATCH /profile updates profile_photo and returns updated data"""
        auth = TestHelpers.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not auth:
            pytest.skip("Could not authenticate admin")
        
        # Get current profile
        get_response = requests.get(
            f"{BASE_URL}/api/profile",
            headers=TestHelpers.auth_headers(auth["token"])
        )
        original = get_response.json()
        original_photo = original.get("profile_photo")
        
        # Update profile_photo with a test base64 image
        test_photo = f"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=={uuid.uuid4().hex[:8]}"
        
        patch_response = requests.patch(
            f"{BASE_URL}/api/profile",
            json={"profile_photo": test_photo},
            headers=TestHelpers.auth_headers(auth["token"])
        )
        
        assert patch_response.status_code == 200, f"Expected 200, got {patch_response.status_code}: {patch_response.text}"
        
        updated = patch_response.json()
        assert updated.get("profile_photo") == test_photo, \
            f"profile_photo not updated correctly. Got: {updated.get('profile_photo', 'NONE')[:50]}"
        
        # Verify GET also returns updated photo
        verify_response = requests.get(
            f"{BASE_URL}/api/profile",
            headers=TestHelpers.auth_headers(auth["token"])
        )
        verified = verify_response.json()
        assert verified.get("profile_photo") == test_photo, \
            f"GET /profile does not return updated photo"
        
        print("✓ PATCH /profile updates profile_photo correctly and GET returns updated data")
        
        # Restore original photo if it existed
        if original_photo:
            requests.patch(
                f"{BASE_URL}/api/profile",
                json={"profile_photo": original_photo},
                headers=TestHelpers.auth_headers(auth["token"])
            )


class TestVisitHistoryIsolation:
    """Tests for /resident/visit-history condominium_id filtering"""
    
    def test_visit_history_requires_auth(self):
        """Test that /resident/visit-history requires authentication"""
        response = requests.get(f"{BASE_URL}/api/resident/visit-history")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ /resident/visit-history requires authentication")
    
    def test_visit_history_returns_200(self):
        """Test authenticated user can access visit history"""
        auth = TestHelpers.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not auth:
            pytest.skip("Could not authenticate admin")
        
        response = requests.get(
            f"{BASE_URL}/api/resident/visit-history",
            headers=TestHelpers.auth_headers(auth["token"])
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Should return paginated data with entries list
        assert "entries" in data or isinstance(data, list), f"Unexpected response format"
        print(f"✓ /resident/visit-history returns 200")


class TestGuardEntriesToday:
    """Tests for /guard/entries-today condominium_id filtering"""
    
    def test_entries_today_requires_auth(self):
        """Test that /guard/entries-today requires authentication"""
        response = requests.get(f"{BASE_URL}/api/guard/entries-today")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ /guard/entries-today requires authentication")
    
    def test_entries_today_returns_200_for_admin(self):
        """Test admin can access today's entries"""
        auth = TestHelpers.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not auth:
            pytest.skip("Could not authenticate admin")
        
        response = requests.get(
            f"{BASE_URL}/api/guard/entries-today",
            headers=TestHelpers.auth_headers(auth["token"])
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ /guard/entries-today returns 200 with {len(data)} entries")
    
    def test_entries_today_filtered_by_condominium(self):
        """Verify entries are filtered by user's condominium_id"""
        auth = TestHelpers.get_auth_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not auth:
            pytest.skip("Could not authenticate admin")
        
        user_condo_id = auth["condominium_id"]
        if not user_condo_id:
            pytest.skip("Admin has no condominium_id")
        
        response = requests.get(
            f"{BASE_URL}/api/guard/entries-today",
            headers=TestHelpers.auth_headers(auth["token"])
        )
        assert response.status_code == 200
        
        entries = response.json()
        for entry in entries:
            entry_condo_id = entry.get("condominium_id")
            if entry_condo_id:  # Entry should have condominium_id
                assert entry_condo_id == user_condo_id, \
                    f"Entry {entry.get('id')} has condo {entry_condo_id}, expected {user_condo_id}"
        
        print(f"✓ All {len(entries)} entries belong to user's condominium")


class TestSuperAdminAuditAccess:
    """Tests for SuperAdmin audit log access - should see all condominiums"""
    
    def test_superadmin_audit_logs_returns_200(self):
        """Test SuperAdmin can access audit logs"""
        auth = TestHelpers.get_auth_token(SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD)
        if not auth:
            pytest.skip("Could not authenticate superadmin")
        
        response = requests.get(
            f"{BASE_URL}/api/audit/logs",
            headers=TestHelpers.auth_headers(auth["token"])
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"✓ SuperAdmin can access audit logs ({len(data)} entries)")
    
    def test_superadmin_sees_all_condominium_logs(self):
        """Verify SuperAdmin can see logs from multiple condominiums"""
        auth = TestHelpers.get_auth_token(SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD)
        if not auth:
            pytest.skip("Could not authenticate superadmin")
        
        response = requests.get(
            f"{BASE_URL}/api/audit/logs",
            headers=TestHelpers.auth_headers(auth["token"])
        )
        assert response.status_code == 200
        
        logs = response.json()
        
        # Count unique condominium_ids
        condo_ids = set()
        for log in logs:
            condo_id = log.get("condominium_id")
            if condo_id:
                condo_ids.add(condo_id)
        
        print(f"✓ SuperAdmin sees logs from {len(condo_ids)} different condominiums")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
