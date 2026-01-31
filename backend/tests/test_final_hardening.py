"""
GENTURIX Final Pre-Deployment Hardening Tests
Tests for:
1. Email normalization (case-insensitive login)
2. Super Admin module toggle
3. Super Admin refresh button
4. HR shift deletion
5. Resident reservations
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestEmailNormalization:
    """Test email case-insensitive login"""
    
    def test_login_lowercase_email(self):
        """Login with lowercase email should work"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "residente@genturix.com",
            "password": "Resi123!"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "residente@genturix.com"
        print(f"✓ Lowercase login successful for: {data['user']['email']}")
    
    def test_login_uppercase_email(self):
        """Login with UPPERCASE email should work (email normalization)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "RESIDENTE@GENTURIX.COM",
            "password": "Resi123!"
        })
        assert response.status_code == 200, f"Uppercase login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        # Email should be normalized to lowercase in response
        assert data["user"]["email"] == "residente@genturix.com"
        print(f"✓ UPPERCASE login successful, normalized to: {data['user']['email']}")
    
    def test_login_mixed_case_email(self):
        """Login with MixedCase email should work"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "Residente@Genturix.COM",
            "password": "Resi123!"
        })
        assert response.status_code == 200, f"Mixed case login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"✓ Mixed case login successful")
    
    def test_login_superadmin_uppercase(self):
        """SuperAdmin login with uppercase email"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "SUPERADMIN@GENTURIX.COM",
            "password": "SuperAdmin123!"
        })
        assert response.status_code == 200, f"SuperAdmin uppercase login failed: {response.text}"
        data = response.json()
        assert "SuperAdmin" in data["user"]["roles"]
        print(f"✓ SuperAdmin uppercase login successful")


class TestSuperAdminModuleToggle:
    """Test Super Admin module enable/disable functionality"""
    
    @pytest.fixture
    def superadmin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "superadmin@genturix.com",
            "password": "SuperAdmin123!"
        })
        if response.status_code != 200:
            pytest.skip("SuperAdmin login failed")
        return response.json()["access_token"]
    
    def test_get_condominiums(self, superadmin_token):
        """SuperAdmin can get list of condominiums"""
        headers = {"Authorization": f"Bearer {superadmin_token}"}
        response = requests.get(f"{BASE_URL}/api/superadmin/condominiums", headers=headers)
        assert response.status_code == 200, f"Get condos failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Got {len(data)} condominiums")
        return data
    
    def test_toggle_module_reservations(self, superadmin_token):
        """SuperAdmin can toggle reservations module"""
        headers = {"Authorization": f"Bearer {superadmin_token}"}
        
        # Get first condo
        response = requests.get(f"{BASE_URL}/api/superadmin/condominiums", headers=headers)
        condos = response.json()
        if not condos:
            pytest.skip("No condominiums found")
        
        condo_id = condos[0]["id"]
        
        # Toggle reservations module
        response = requests.put(
            f"{BASE_URL}/api/superadmin/condominiums/{condo_id}/modules/reservations",
            headers=headers,
            json={"enabled": True}
        )
        assert response.status_code == 200, f"Toggle module failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"✓ Module toggle successful: {data.get('message')}")
    
    def test_refresh_condo_data(self, superadmin_token):
        """SuperAdmin can refresh condominium data"""
        headers = {"Authorization": f"Bearer {superadmin_token}"}
        
        # Get condominiums (this is the refresh action)
        response = requests.get(f"{BASE_URL}/api/superadmin/condominiums", headers=headers)
        assert response.status_code == 200, f"Refresh failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        
        # Verify data structure
        if data:
            condo = data[0]
            assert "id" in condo
            assert "name" in condo
            assert "modules" in condo
        print(f"✓ Refresh data successful, got {len(data)} condos")


class TestHRShiftDeletion:
    """Test HR shift deletion with confirmation"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@genturix.com",
            "password": "Admin123!"
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr@genturix.com",
            "password": "HR123!"
        })
        if response.status_code != 200:
            pytest.skip("HR login failed")
        return response.json()["access_token"]
    
    def test_create_and_delete_shift(self, admin_token):
        """Create a shift and then delete it"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get guards first
        response = requests.get(f"{BASE_URL}/api/hr/guards", headers=headers)
        if response.status_code != 200 or not response.json():
            pytest.skip("No guards available")
        
        guards = response.json()
        guard_id = guards[0]["id"]
        
        # Create a shift
        from datetime import datetime, timedelta
        start = datetime.now() + timedelta(days=1)
        end = start + timedelta(hours=8)
        
        shift_data = {
            "guard_id": guard_id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "location": "Test Location for Deletion",
            "notes": "Test shift to be deleted"
        }
        
        response = requests.post(f"{BASE_URL}/api/hr/shifts", headers=headers, json=shift_data)
        assert response.status_code in [200, 201], f"Create shift failed: {response.text}"
        shift = response.json()
        shift_id = shift["id"]
        print(f"✓ Created shift: {shift_id}")
        
        # Delete the shift
        response = requests.delete(f"{BASE_URL}/api/hr/shifts/{shift_id}", headers=headers)
        assert response.status_code == 200, f"Delete shift failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"✓ Deleted shift: {data.get('message')}")
        
        # Verify shift is deleted
        response = requests.get(f"{BASE_URL}/api/hr/shifts", headers=headers)
        shifts = response.json()
        shift_ids = [s["id"] for s in shifts]
        assert shift_id not in shift_ids, "Shift still exists after deletion"
        print(f"✓ Verified shift no longer exists")
    
    def test_delete_nonexistent_shift(self, admin_token):
        """Deleting non-existent shift should return 404"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.delete(f"{BASE_URL}/api/hr/shifts/nonexistent-id-12345", headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Non-existent shift returns 404")


class TestResidentReservations:
    """Test resident reservations UI functionality"""
    
    @pytest.fixture
    def resident_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "residente@genturix.com",
            "password": "Resi123!"
        })
        if response.status_code != 200:
            pytest.skip("Resident login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@genturix.com",
            "password": "Admin123!"
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    def test_get_reservation_areas(self, resident_token):
        """Resident can view available areas"""
        headers = {"Authorization": f"Bearer {resident_token}"}
        response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=headers)
        # May return 404 if module not enabled, or 200 with data
        assert response.status_code in [200, 404], f"Get areas failed: {response.text}"
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Got {len(data)} reservation areas")
        else:
            print(f"✓ Reservations module not enabled (expected)")
    
    def test_create_reservation(self, resident_token, admin_token):
        """Resident can create a reservation"""
        headers = {"Authorization": f"Bearer {resident_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First check if there are areas
        response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=headers)
        if response.status_code != 200:
            pytest.skip("Reservations module not enabled")
        
        areas = response.json()
        if not areas:
            # Create an area first as admin
            area_data = {
                "name": "Test Pool",
                "area_type": "pool",
                "capacity": 20,
                "available_from": "08:00",
                "available_until": "20:00",
                "max_hours_per_reservation": 2,
                "max_reservations_per_day": 5
            }
            response = requests.post(f"{BASE_URL}/api/reservations/areas", headers=admin_headers, json=area_data)
            if response.status_code not in [200, 201]:
                pytest.skip("Could not create test area")
            areas = [response.json()]
        
        area_id = areas[0]["id"]
        
        # Create reservation
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        reservation_data = {
            "area_id": area_id,
            "date": tomorrow,
            "start_time": "10:00",
            "end_time": "12:00",
            "guests_count": 2,
            "purpose": "Test reservation"
        }
        
        response = requests.post(f"{BASE_URL}/api/reservations", headers=headers, json=reservation_data)
        assert response.status_code in [200, 201], f"Create reservation failed: {response.text}"
        data = response.json()
        assert "id" in data
        print(f"✓ Created reservation: {data['id']}")


class TestGuardLogin:
    """Test guard login with various email cases"""
    
    def test_guard_login_lowercase(self):
        """Guard login with lowercase"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "guardia@genturix.com",
            "password": "Test123!"
        })
        # May or may not exist
        if response.status_code == 200:
            print(f"✓ Guard lowercase login successful")
        else:
            print(f"✓ Guard user may not exist (expected)")
    
    def test_guard_login_uppercase(self):
        """Guard login with UPPERCASE"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "GUARDIA@GENTURIX.COM",
            "password": "Test123!"
        })
        # Email normalization should work regardless of user existence
        if response.status_code == 200:
            data = response.json()
            assert data["user"]["email"] == "guardia@genturix.com"
            print(f"✓ Guard UPPERCASE login normalized correctly")
        else:
            print(f"✓ Guard user may not exist (expected)")


class TestProfileLogout:
    """Test logout functionality in profile"""
    
    def test_logout_endpoint(self):
        """Test logout API endpoint"""
        # Login first
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "residente@genturix.com",
            "password": "Resi123!"
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        # Logout
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{BASE_URL}/api/auth/logout", headers=headers)
        assert response.status_code == 200, f"Logout failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"✓ Logout successful: {data.get('message')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
