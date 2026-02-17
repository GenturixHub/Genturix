"""
Test P0 Bug Fixes:
1. Panic alert sending from resident - should work and send alert
2. Module access control - HR endpoints return 403 when HR module disabled
3. Module access control - Security endpoints return 403 when security disabled
4. Panic endpoint should work even when security module is disabled (critical emergency)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
RESIDENT_EMAIL = "residente@genturix.com"
RESIDENT_PASSWORD = "Resi123!"
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"


def get_token(email, password):
    """Get auth token for user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    return None


def get_user_condominium_id(token):
    """Get condominium ID from user profile"""
    response = requests.get(
        f"{BASE_URL}/api/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        return response.json().get("condominium_id")
    return None


def toggle_module(admin_token, condo_id, module_name, enabled):
    """Toggle module for condominium"""
    response = requests.patch(
        f"{BASE_URL}/api/condominiums/{condo_id}/modules/{module_name}?enabled={str(enabled).lower()}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    return response


class TestPanicAlertSending:
    """Test panic alert functionality - P0 Bug Fix #1"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get tokens and ensure security module is enabled"""
        self.resident_token = get_token(RESIDENT_EMAIL, RESIDENT_PASSWORD)
        self.admin_token = get_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        assert self.resident_token, "Failed to get resident token"
        assert self.admin_token, "Failed to get admin token"
        
        # Get condominium ID
        self.condo_id = get_user_condominium_id(self.resident_token)
        assert self.condo_id, "Failed to get condominium ID"
        
        # Ensure security module is enabled for setup
        toggle_module(self.admin_token, self.condo_id, "security", True)
        yield
        # Re-enable security module after tests
        toggle_module(self.admin_token, self.condo_id, "security", True)
    
    def test_resident_can_trigger_panic_alert(self):
        """Test that resident can successfully send panic alert"""
        response = requests.post(
            f"{BASE_URL}/api/security/panic",
            headers={"Authorization": f"Bearer {self.resident_token}"},
            json={
                "panic_type": "emergencia_general",
                "location": "Apartamento 101, Torre A",
                "description": "Test panic alert"
            }
        )
        
        print(f"Panic response status: {response.status_code}")
        print(f"Panic response body: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "event_id" in data or "id" in data, "Response should contain event ID"
        assert "message" in data or "status" in data, "Response should contain status/message"
    
    def test_panic_works_without_gps(self):
        """Test panic alert works without GPS coordinates"""
        response = requests.post(
            f"{BASE_URL}/api/security/panic",
            headers={"Authorization": f"Bearer {self.resident_token}"},
            json={
                "panic_type": "emergencia_medica",
                "location": "Lobby Principal"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_panic_works_with_gps(self):
        """Test panic alert works with GPS coordinates"""
        response = requests.post(
            f"{BASE_URL}/api/security/panic",
            headers={"Authorization": f"Bearer {self.resident_token}"},
            json={
                "panic_type": "actividad_sospechosa",
                "location": "Estacionamiento",
                "latitude": 19.4326,
                "longitude": -99.1332,
                "description": "Persona sospechosa en estacionamiento"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


class TestPanicBypassesSecurityModule:
    """Test that panic endpoint works even when security module is disabled - P0 Requirement"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get tokens"""
        self.resident_token = get_token(RESIDENT_EMAIL, RESIDENT_PASSWORD)
        self.admin_token = get_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        assert self.resident_token, "Failed to get resident token"
        assert self.admin_token, "Failed to get admin token"
        
        self.condo_id = get_user_condominium_id(self.resident_token)
        assert self.condo_id, "Failed to get condominium ID"
        yield
        # Re-enable security module after tests
        toggle_module(self.admin_token, self.condo_id, "security", True)
    
    def test_panic_works_when_security_module_disabled(self):
        """Panic is CRITICAL - must work even when security module is disabled"""
        # Disable security module
        toggle_response = toggle_module(self.admin_token, self.condo_id, "security", False)
        print(f"Toggle security OFF response: {toggle_response.status_code}")
        
        # Panic should still work
        response = requests.post(
            f"{BASE_URL}/api/security/panic",
            headers={"Authorization": f"Bearer {self.resident_token}"},
            json={
                "panic_type": "emergencia_general",
                "location": "Área común",
                "description": "CRITICAL TEST - Panic must work even when module disabled"
            }
        )
        
        print(f"Panic response status: {response.status_code}")
        print(f"Panic response body: {response.text}")
        
        # Panic should succeed regardless of module status
        assert response.status_code == 200, f"CRITICAL: Panic MUST work even when security module is disabled. Got {response.status_code}: {response.text}"


class TestHRModuleAccessControl:
    """Test HR module access control - P0 Bug Fix #2"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get tokens"""
        self.admin_token = get_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert self.admin_token, "Failed to get admin token"
        
        self.condo_id = get_user_condominium_id(self.admin_token)
        assert self.condo_id, "Failed to get condominium ID"
        yield
        # Re-enable HR module after tests
        toggle_module(self.admin_token, self.condo_id, "hr", True)
    
    def test_hr_guards_returns_403_when_hr_disabled(self):
        """GET /api/hr/guards should return 403 when HR module is disabled"""
        # Disable HR module
        toggle_response = toggle_module(self.admin_token, self.condo_id, "hr", False)
        print(f"Toggle HR OFF response: {toggle_response.status_code}")
        
        # Try to access HR guards endpoint
        response = requests.get(
            f"{BASE_URL}/api/hr/guards",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        print(f"HR guards response status: {response.status_code}")
        print(f"HR guards response body: {response.text}")
        
        assert response.status_code == 403, f"Expected 403 when HR module disabled, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "hr" in data.get("detail", "").lower() or "módulo" in data.get("detail", "").lower(), \
            "Error message should mention HR module"
    
    def test_hr_guards_works_when_hr_enabled(self):
        """GET /api/hr/guards should work when HR module is enabled"""
        # Enable HR module
        toggle_module(self.admin_token, self.condo_id, "hr", True)
        
        # Access HR guards endpoint
        response = requests.get(
            f"{BASE_URL}/api/hr/guards",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        print(f"HR guards (enabled) response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200 when HR module enabled, got {response.status_code}: {response.text}"
    
    def test_hr_shifts_returns_403_when_hr_disabled(self):
        """GET /api/hr/shifts should return 403 when HR module is disabled"""
        # Disable HR module
        toggle_module(self.admin_token, self.condo_id, "hr", False)
        
        response = requests.get(
            f"{BASE_URL}/api/hr/shifts",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        
        print(f"HR shifts response status: {response.status_code}")
        
        assert response.status_code == 403, f"Expected 403 when HR module disabled, got {response.status_code}: {response.text}"


class TestSecurityModuleAccessControl:
    """Test Security module access control - P0 Bug Fix #3"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get tokens"""
        self.guard_token = get_token(GUARD_EMAIL, GUARD_PASSWORD)
        self.admin_token = get_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        
        assert self.guard_token, "Failed to get guard token"
        assert self.admin_token, "Failed to get admin token"
        
        self.condo_id = get_user_condominium_id(self.guard_token)
        assert self.condo_id, "Failed to get condominium ID"
        yield
        # Re-enable security module after tests
        toggle_module(self.admin_token, self.condo_id, "security", True)
    
    def test_security_access_logs_returns_403_when_disabled(self):
        """GET /api/security/access-logs should return 403 when security module disabled"""
        # Disable security module
        toggle_module(self.admin_token, self.condo_id, "security", False)
        
        response = requests.get(
            f"{BASE_URL}/api/security/access-logs",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        print(f"Security access-logs response status: {response.status_code}")
        print(f"Security access-logs response body: {response.text}")
        
        assert response.status_code == 403, f"Expected 403 when security module disabled, got {response.status_code}: {response.text}"
    
    def test_security_access_logs_works_when_enabled(self):
        """GET /api/security/access-logs should work when security module enabled"""
        # Enable security module
        toggle_module(self.admin_token, self.condo_id, "security", True)
        
        response = requests.get(
            f"{BASE_URL}/api/security/access-logs",
            headers={"Authorization": f"Bearer {self.guard_token}"}
        )
        
        print(f"Security access-logs (enabled) response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200 when security module enabled, got {response.status_code}: {response.text}"


class TestTokenStorageIntegration:
    """Test that frontend API uses correct token storage (localStorage with correct keys)"""
    
    def test_login_returns_valid_tokens(self):
        """Login should return access_token and refresh_token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD}
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Response should contain access_token"
        assert "refresh_token" in data, "Response should contain refresh_token"
        assert len(data["access_token"]) > 0, "access_token should not be empty"
        assert len(data["refresh_token"]) > 0, "refresh_token should not be empty"
    
    def test_token_works_for_authenticated_requests(self):
        """Token from login should work for authenticated requests"""
        # Login
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD}
        )
        token = login_response.json().get("access_token")
        
        # Use token for authenticated request
        profile_response = requests.get(
            f"{BASE_URL}/api/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert profile_response.status_code == 200, f"Token should work for auth requests: {profile_response.text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
