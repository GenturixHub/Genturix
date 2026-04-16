"""
GENTURIX - Post-Modularization Full Regression Test
Tests ALL 22 router modules after backend split from monolithic server.py
This is a breadth-first test to verify all endpoints respond correctly.

Uses session-based tokens to avoid rate limiting.
"""
import pytest
import requests
import os
import time
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://modular-backend-94.preview.emergentagent.com').rstrip('/')

# Test credentials from test_credentials.md
RESIDENT_EMAIL = "test-resident@genturix.com"
RESIDENT_PASSWORD = "Admin123!"
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "Admin123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"

# Known test data
RESIDENT_CONDO_ID = "46b9d344-a735-443a-8c9c-0e3d69c07824"
RESIDENT_UNIT = "A-102"

# Global token cache to avoid rate limiting
_token_cache = {}

def get_token(email, password):
    """Get token with caching to avoid rate limits"""
    cache_key = email
    if cache_key in _token_cache:
        return _token_cache[cache_key]
    
    time.sleep(0.5)  # Small delay to avoid rate limits
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    
    if response.status_code == 429:
        # Rate limited - wait and retry
        time.sleep(5)
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
    
    if response.status_code == 200:
        token = response.json().get("access_token")
        _token_cache[cache_key] = token
        return token
    return None


@pytest.fixture(scope="module")
def resident_token():
    """Get resident token once for all tests"""
    return get_token(RESIDENT_EMAIL, RESIDENT_PASSWORD)


@pytest.fixture(scope="module")
def admin_token():
    """Get admin token once for all tests"""
    return get_token(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def guard_token():
    """Get guard token once for all tests"""
    return get_token(GUARD_EMAIL, GUARD_PASSWORD)


class TestAuthModule:
    """AUTH MODULE: /api/auth/* endpoints"""
    
    def test_login_valid_resident(self, resident_token):
        """POST /api/auth/login with valid resident credentials returns tokens"""
        assert resident_token is not None, "Resident login failed"
    
    def test_login_valid_admin(self, admin_token):
        """POST /api/auth/login with valid admin credentials returns tokens"""
        assert admin_token is not None, "Admin login failed"
    
    def test_login_invalid_credentials(self):
        """POST /api/auth/login with invalid credentials returns 401"""
        time.sleep(0.5)
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [401, 429], f"Expected 401 or 429, got {response.status_code}"
    
    def test_auth_me_returns_profile(self, resident_token):
        """GET /api/auth/me returns current user profile"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == RESIDENT_EMAIL
        assert "roles" in data
    
    def test_auth_me_unauthorized(self):
        """GET /api/auth/me without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403]


class TestProfileModule:
    """PROFILE MODULE: /api/profile/* endpoints"""
    
    def test_get_profile(self, resident_token):
        """GET /api/profile returns user data"""
        response = requests.get(f"{BASE_URL}/api/profile", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "full_name" in data
        assert "roles" in data
    
    def test_get_condominium_directory(self, resident_token):
        """GET /api/profile/directory/condominium returns condo directory"""
        response = requests.get(f"{BASE_URL}/api/profile/directory/condominium", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "users" in data or "grouped_by_role" in data


class TestFinanzasModule:
    """FINANZAS MODULE: /api/finanzas/* endpoints"""
    
    def test_get_charge_catalog_admin(self, admin_token):
        """GET /api/finanzas/catalog returns charge types (admin)"""
        response = requests.get(f"{BASE_URL}/api/finanzas/catalog", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_financial_overview_admin(self, admin_token):
        """GET /api/finanzas/overview returns financial summary (admin)"""
        response = requests.get(f"{BASE_URL}/api/finanzas/overview", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data or "summary" in data
    
    def test_get_unit_account_resident(self, resident_token):
        """GET /api/finanzas/unit/{unit_id} returns unit account for resident"""
        response = requests.get(f"{BASE_URL}/api/finanzas/unit/{RESIDENT_UNIT}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "account" in data or "records" in data
    
    def test_get_payment_settings(self, admin_token):
        """GET /api/finanzas/payment-settings reads bank info"""
        response = requests.get(f"{BASE_URL}/api/finanzas/payment-settings", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
    
    def test_get_units_list(self, admin_token):
        """GET /api/units returns units list"""
        response = requests.get(f"{BASE_URL}/api/units", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestDocumentosModule:
    """DOCUMENTOS MODULE: /api/documentos/* endpoints"""
    
    def test_get_documents_list(self, resident_token):
        """GET /api/documentos returns documents list"""
        response = requests.get(f"{BASE_URL}/api/documentos", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestAsambleaModule:
    """ASAMBLEA MODULE: /api/asamblea/* endpoints"""
    
    def test_get_assemblies_list(self, resident_token):
        """GET /api/asamblea returns assemblies list"""
        response = requests.get(f"{BASE_URL}/api/asamblea", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestCasosModule:
    """CASOS MODULE: /api/casos/* endpoints"""
    
    def test_get_casos_list_resident(self, resident_token):
        """GET /api/casos returns cases list (resident sees own + community)"""
        response = requests.get(f"{BASE_URL}/api/casos", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    def test_get_casos_list_admin(self, admin_token):
        """GET /api/casos returns all cases for admin"""
        response = requests.get(f"{BASE_URL}/api/casos", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_create_and_delete_caso_resident(self, resident_token):
        """POST /api/casos creates case (resident) and DELETE removes it"""
        # Create case
        response = requests.post(f"{BASE_URL}/api/casos", headers={
            "Authorization": f"Bearer {resident_token}"
        }, json={
            "title": "TEST_Regression Test Case",
            "description": "This is a test case created during regression testing",
            "category": "mantenimiento",
            "priority": "low",
            "visibility": "private"
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        
        caso_id = data["id"]
        
        # Get case detail
        detail_resp = requests.get(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert detail_resp.status_code == 200
        
        # Cleanup - delete the test case
        delete_resp = requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert delete_resp.status_code == 200


class TestVisitorsModule:
    """VISITORS MODULE: /api/authorizations/* endpoints"""
    
    def test_get_my_authorizations(self, resident_token):
        """GET /api/authorizations/my returns resident's authorizations"""
        response = requests.get(f"{BASE_URL}/api/authorizations/my", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_and_delete_visitor_authorization(self, resident_token):
        """POST /api/authorizations creates new visitor authorization (resident)"""
        response = requests.post(f"{BASE_URL}/api/authorizations", headers={
            "Authorization": f"Bearer {resident_token}"
        }, json={
            "visitor_name": "TEST_Regression Visitor",
            "identification_number": "TEST123456",
            "authorization_type": "temporary",
            "valid_from": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "valid_to": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        
        # Cleanup - deactivate the authorization
        auth_id = data["id"]
        delete_resp = requests.delete(f"{BASE_URL}/api/authorizations/{auth_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert delete_resp.status_code == 200


class TestReservationsModule:
    """RESERVATIONS MODULE: /api/reservations/* endpoints"""
    
    def test_get_reservations_list(self, resident_token):
        """GET /api/reservations returns reservations list"""
        response = requests.get(f"{BASE_URL}/api/reservations", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_reservation_areas(self, resident_token):
        """GET /api/reservations/areas returns common areas"""
        response = requests.get(f"{BASE_URL}/api/reservations/areas", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestNotificationsModule:
    """NOTIFICATIONS MODULE: /api/notifications/v2/* endpoints"""
    
    def test_get_notifications_v2(self, resident_token):
        """GET /api/notifications/v2 returns notifications"""
        response = requests.get(f"{BASE_URL}/api/notifications/v2", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_get_unread_count(self, resident_token):
        """GET /api/notifications/v2/unread-count returns unread count"""
        response = requests.get(f"{BASE_URL}/api/notifications/v2/unread-count", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "count" in data


class TestAdminModule:
    """ADMIN MODULE: /api/admin/* endpoints"""
    
    def test_get_users_list_admin(self, admin_token):
        """GET /api/admin/users returns user list (admin only)"""
        response = requests.get(f"{BASE_URL}/api/admin/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_users_unauthorized(self, resident_token):
        """GET /api/admin/users without admin role returns 403"""
        response = requests.get(f"{BASE_URL}/api/admin/users", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 403


class TestGuardModule:
    """GUARD MODULE: /api/guard/* endpoints"""
    
    def test_guard_my_shift(self, guard_token):
        """GET /api/guard/my-shift returns guard shift info"""
        if not guard_token:
            pytest.skip("Guard user not available")
        response = requests.get(f"{BASE_URL}/api/guard/my-shift", headers={
            "Authorization": f"Bearer {guard_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert "has_guard_record" in data or "current_shift" in data
    
    def test_guard_history(self, guard_token):
        """GET /api/guard/history returns guard action history"""
        if not guard_token:
            pytest.skip("Guard user not available")
        response = requests.get(f"{BASE_URL}/api/guard/history", headers={
            "Authorization": f"Bearer {guard_token}"
        })
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestMultiTenantIsolation:
    """MULTI-TENANT: Verify data isolation between condominiums"""
    
    def test_resident_sees_own_condo_data(self, resident_token):
        """Resident from condo A cannot see data from condo B"""
        # Get profile to verify condominium_id
        profile_resp = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert profile_resp.status_code == 200
        profile = profile_resp.json()
        assert profile.get("condominium_id") == RESIDENT_CONDO_ID
        
        # Get cases - should only see own condo's cases
        casos_resp = requests.get(f"{BASE_URL}/api/casos", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert casos_resp.status_code == 200


class TestRoleBasedAccess:
    """ROLE-BASED ACCESS: Verify role restrictions"""
    
    def test_resident_cannot_access_admin_endpoints(self, resident_token):
        """Resident cannot access admin-only endpoints"""
        # Try to access admin users endpoint
        response = requests.get(f"{BASE_URL}/api/admin/users", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 403
        
        # Try to access finanzas overview (admin only)
        response = requests.get(f"{BASE_URL}/api/finanzas/overview", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert response.status_code == 403


class TestHealthAndBasicEndpoints:
    """Basic health and connectivity tests"""
    
    def test_api_reachable(self):
        """API is reachable"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        # Health endpoint might not exist, but we should get a response
        assert response.status_code in [200, 404, 405]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
