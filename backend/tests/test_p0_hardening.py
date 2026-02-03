"""
GENTURIX P0 Hardening Tests
Tests for critical fixes:
1. Admin Create User with badge_number for Guarda role
2. Shift creation error handling
3. Authorization creation
"""

import pytest
import requests
import os
import random

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rezbook-i18n.preview.emergentagent.com').rstrip('/')

class TestAdminUserCreation:
    """Test Admin Create User functionality with badge_number for Guarda role"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@genturix.com",
            "password": "Admin123!"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")
    
    def test_create_guarda_without_badge_fails(self, admin_token):
        """Creating Guarda without badge_number should fail"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": f"testguard_nobadge_{random.randint(1000,9999)}@test.com",
                "password": "TestPass123!",
                "full_name": "Test Guard No Badge",
                "role": "Guarda"
                # Missing badge_number
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "placa" in response.json().get("detail", "").lower() or "badge" in response.json().get("detail", "").lower()
        print(f"SUCCESS: Creating Guarda without badge_number returns 400: {response.json()}")
    
    def test_create_guarda_with_badge_succeeds(self, admin_token):
        """Creating Guarda with badge_number should succeed"""
        test_id = random.randint(10000, 99999)
        response = requests.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": f"testguard_api_{test_id}@test.com",
                "password": "TestPass123!",
                "full_name": f"Test Guard API {test_id}",
                "role": "Guarda",
                "badge_number": f"G-API-{test_id}"
            }
        )
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data or "user_id" in data
        print(f"SUCCESS: Created Guarda with badge_number: {data}")
    
    def test_create_residente_succeeds(self, admin_token):
        """Creating Residente should succeed"""
        test_id = random.randint(10000, 99999)
        response = requests.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": f"testresident_api_{test_id}@test.com",
                "password": "TestPass123!",
                "full_name": f"Test Resident API {test_id}",
                "role": "Residente",
                "apartment_number": f"A-{test_id}"
            }
        )
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        print(f"SUCCESS: Created Residente: {response.json()}")


class TestShiftCreation:
    """Test Shift creation error handling"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@genturix.com",
            "password": "Admin123!"
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    def test_shift_creation_invalid_guard_fails(self, admin_token):
        """Creating shift with invalid guard_id should fail"""
        response = requests.post(
            f"{BASE_URL}/api/hr/shifts",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "guard_id": "invalid-guard-id-12345",
                "start_time": "2026-02-01T08:00:00",
                "end_time": "2026-02-01T16:00:00",
                "location": "Entrada Principal"
            }
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"SUCCESS: Invalid guard_id returns 404: {response.json()}")
    
    def test_shift_creation_invalid_time_fails(self, admin_token):
        """Creating shift with end_time before start_time should fail"""
        # First get a valid guard
        guards_response = requests.get(
            f"{BASE_URL}/api/hr/guards",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if guards_response.status_code != 200 or not guards_response.json():
            pytest.skip("No guards available for testing")
        
        guard_id = guards_response.json()[0].get("id")
        
        response = requests.post(
            f"{BASE_URL}/api/hr/shifts",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "guard_id": guard_id,
                "start_time": "2026-02-01T16:00:00",
                "end_time": "2026-02-01T08:00:00",  # End before start
                "location": "Entrada Principal"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"SUCCESS: Invalid time range returns 400: {response.json()}")


class TestResidentAuthorization:
    """Test Resident Authorization creation"""
    
    @pytest.fixture
    def resident_token(self):
        """Get resident authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "residente@genturix.com",
            "password": "Resi123!"
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    def test_create_temporal_authorization(self, resident_token):
        """Creating temporal authorization should succeed"""
        response = requests.post(
            f"{BASE_URL}/api/authorizations",
            headers={"Authorization": f"Bearer {resident_token}"},
            json={
                "visitor_name": "Test Visitor API",
                "visitor_id": "12345678",
                "vehicle_plate": "TEST-123",
                "authorization_type": "temporary",  # API uses 'temporary' not 'temporal'
                "valid_from": "2026-01-31",
                "valid_until": "2026-02-01",
                "notes": "API test authorization"
            }
        )
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"SUCCESS: Created temporal authorization: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
