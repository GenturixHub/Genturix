"""
Test Condominium Settings Module
Tests for GET/PUT /api/admin/condominium-settings and GET /api/condominium-settings/public
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"
RESIDENT_EMAIL = "residente@genturix.com"
RESIDENT_PASSWORD = "Resi123!"


class TestCondominiumSettingsBackend:
    """Test condominium settings API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, email, password):
        """Helper to login and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            return token
        return None
    
    # ==================== ADMIN GET SETTINGS ====================
    def test_admin_get_settings_returns_200(self):
        """Admin can GET condominium settings"""
        token = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None, "Admin login failed"
        
        response = self.session.get(f"{BASE_URL}/api/admin/condominium-settings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify structure
        assert "condominium_id" in data, "Missing condominium_id"
        assert "condominium_name" in data, "Missing condominium_name"
        assert "general" in data, "Missing general settings"
        assert "reservations" in data, "Missing reservations settings"
        assert "visits" in data, "Missing visits settings"
        assert "notifications" in data, "Missing notifications settings"
        print(f"✓ Admin GET settings returned: {data['condominium_name']}")
    
    def test_admin_get_settings_has_default_values(self):
        """Settings have correct default values"""
        token = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None
        
        response = self.session.get(f"{BASE_URL}/api/admin/condominium-settings")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check general defaults
        general = data.get("general", {})
        assert "timezone" in general, "Missing timezone"
        assert "working_hours" in general, "Missing working_hours"
        
        # Check reservations defaults
        reservations = data.get("reservations", {})
        assert "enabled" in reservations, "Missing enabled"
        assert "max_active_per_user" in reservations, "Missing max_active_per_user"
        assert "allow_same_day" in reservations, "Missing allow_same_day"
        assert "approval_required_by_default" in reservations, "Missing approval_required_by_default"
        
        # Check visits defaults
        visits = data.get("visits", {})
        assert "allow_resident_preregistration" in visits, "Missing allow_resident_preregistration"
        assert "allow_recurrent_visits" in visits, "Missing allow_recurrent_visits"
        assert "allow_permanent_visits" in visits, "Missing allow_permanent_visits"
        
        # Check notifications defaults
        notifications = data.get("notifications", {})
        assert "panic_sound_enabled" in notifications, "Missing panic_sound_enabled"
        assert "push_enabled" in notifications, "Missing push_enabled"
        assert "email_notifications_enabled" in notifications, "Missing email_notifications_enabled"
        
        print("✓ All default settings fields present")
    
    # ==================== ADMIN UPDATE SETTINGS ====================
    def test_admin_update_general_settings(self):
        """Admin can update general settings"""
        token = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None
        
        # Update timezone
        update_data = {
            "general": {
                "timezone": "America/Cancun",
                "working_hours": {"start": "07:00", "end": "21:00"}
            }
        }
        
        response = self.session.put(f"{BASE_URL}/api/admin/condominium-settings", json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["general"]["timezone"] == "America/Cancun", "Timezone not updated"
        assert data["general"]["working_hours"]["start"] == "07:00", "Working hours start not updated"
        assert data["general"]["working_hours"]["end"] == "21:00", "Working hours end not updated"
        
        print("✓ General settings updated successfully")
        
        # Revert to default
        revert_data = {
            "general": {
                "timezone": "America/Mexico_City",
                "working_hours": {"start": "06:00", "end": "22:00"}
            }
        }
        self.session.put(f"{BASE_URL}/api/admin/condominium-settings", json=revert_data)
    
    def test_admin_update_reservations_settings(self):
        """Admin can update reservations settings"""
        token = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None
        
        # Get current settings first
        get_response = self.session.get(f"{BASE_URL}/api/admin/condominium-settings")
        original = get_response.json()
        
        # Update reservations
        update_data = {
            "reservations": {
                "enabled": False,
                "max_active_per_user": 5,
                "allow_same_day": False,
                "approval_required_by_default": True,
                "min_hours_advance": 2,
                "max_days_advance": 60
            }
        }
        
        response = self.session.put(f"{BASE_URL}/api/admin/condominium-settings", json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["reservations"]["enabled"] == False, "enabled not updated"
        assert data["reservations"]["max_active_per_user"] == 5, "max_active_per_user not updated"
        assert data["reservations"]["allow_same_day"] == False, "allow_same_day not updated"
        assert data["reservations"]["approval_required_by_default"] == True, "approval_required_by_default not updated"
        
        print("✓ Reservations settings updated successfully")
        
        # Revert to original
        revert_data = {"reservations": original.get("reservations", {})}
        self.session.put(f"{BASE_URL}/api/admin/condominium-settings", json=revert_data)
    
    def test_admin_update_visits_settings(self):
        """Admin can update visits settings"""
        token = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None
        
        # Get current settings first
        get_response = self.session.get(f"{BASE_URL}/api/admin/condominium-settings")
        original = get_response.json()
        
        # Update visits
        update_data = {
            "visits": {
                "allow_resident_preregistration": False,
                "allow_recurrent_visits": False,
                "allow_permanent_visits": True,
                "require_id_photo": True,
                "max_preregistrations_per_day": 20
            }
        }
        
        response = self.session.put(f"{BASE_URL}/api/admin/condominium-settings", json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["visits"]["allow_resident_preregistration"] == False
        assert data["visits"]["allow_recurrent_visits"] == False
        assert data["visits"]["allow_permanent_visits"] == True
        assert data["visits"]["require_id_photo"] == True
        assert data["visits"]["max_preregistrations_per_day"] == 20
        
        print("✓ Visits settings updated successfully")
        
        # Revert to original
        revert_data = {"visits": original.get("visits", {})}
        self.session.put(f"{BASE_URL}/api/admin/condominium-settings", json=revert_data)
    
    def test_admin_update_notifications_settings(self):
        """Admin can update notifications settings"""
        token = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None
        
        # Get current settings first
        get_response = self.session.get(f"{BASE_URL}/api/admin/condominium-settings")
        original = get_response.json()
        
        # Update notifications
        update_data = {
            "notifications": {
                "panic_sound_enabled": False,
                "push_enabled": False,
                "email_notifications_enabled": False
            }
        }
        
        response = self.session.put(f"{BASE_URL}/api/admin/condominium-settings", json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["notifications"]["panic_sound_enabled"] == False
        assert data["notifications"]["push_enabled"] == False
        assert data["notifications"]["email_notifications_enabled"] == False
        
        print("✓ Notifications settings updated successfully")
        
        # Revert to original
        revert_data = {"notifications": original.get("notifications", {})}
        self.session.put(f"{BASE_URL}/api/admin/condominium-settings", json=revert_data)
    
    def test_admin_update_persists_to_database(self):
        """Settings update persists and can be retrieved"""
        token = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert token is not None
        
        # Get original
        get_response = self.session.get(f"{BASE_URL}/api/admin/condominium-settings")
        original = get_response.json()
        
        # Update with unique value
        update_data = {
            "reservations": {
                "max_active_per_user": 7,
                "enabled": True,
                "allow_same_day": True,
                "approval_required_by_default": False,
                "min_hours_advance": 1,
                "max_days_advance": 30
            }
        }
        
        put_response = self.session.put(f"{BASE_URL}/api/admin/condominium-settings", json=update_data)
        assert put_response.status_code == 200
        
        # GET again to verify persistence
        verify_response = self.session.get(f"{BASE_URL}/api/admin/condominium-settings")
        assert verify_response.status_code == 200
        
        verify_data = verify_response.json()
        assert verify_data["reservations"]["max_active_per_user"] == 7, "Update did not persist"
        
        print("✓ Settings update persisted to database")
        
        # Revert
        revert_data = {"reservations": original.get("reservations", {})}
        self.session.put(f"{BASE_URL}/api/admin/condominium-settings", json=revert_data)
    
    # ==================== PUBLIC SETTINGS ENDPOINT ====================
    def test_guard_can_read_public_settings(self):
        """Guard can read public settings (read-only)"""
        token = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert token is not None, "Guard login failed"
        
        response = self.session.get(f"{BASE_URL}/api/condominium-settings/public")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "condominium_id" in data or "general" in data, "Missing expected fields"
        print("✓ Guard can read public settings")
    
    def test_resident_can_read_public_settings(self):
        """Resident can read public settings (read-only)"""
        token = self.login(RESIDENT_EMAIL, RESIDENT_PASSWORD)
        assert token is not None, "Resident login failed"
        
        response = self.session.get(f"{BASE_URL}/api/condominium-settings/public")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "general" in data or "condominium_id" in data, "Missing expected fields"
        print("✓ Resident can read public settings")
    
    # ==================== ACCESS CONTROL ====================
    def test_guard_cannot_update_settings(self):
        """Guard cannot update settings (admin only)"""
        token = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert token is not None
        
        update_data = {
            "general": {
                "timezone": "America/Bogota",
                "working_hours": {"start": "08:00", "end": "20:00"}
            }
        }
        
        response = self.session.put(f"{BASE_URL}/api/admin/condominium-settings", json=update_data)
        # Should be 403 Forbidden or 401 Unauthorized
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Guard correctly denied from updating settings")
    
    def test_resident_cannot_update_settings(self):
        """Resident cannot update settings (admin only)"""
        token = self.login(RESIDENT_EMAIL, RESIDENT_PASSWORD)
        assert token is not None
        
        update_data = {
            "general": {
                "timezone": "America/Lima",
                "working_hours": {"start": "09:00", "end": "19:00"}
            }
        }
        
        response = self.session.put(f"{BASE_URL}/api/admin/condominium-settings", json=update_data)
        # Should be 403 Forbidden or 401 Unauthorized
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Resident correctly denied from updating settings")
    
    def test_guard_cannot_access_admin_get_settings(self):
        """Guard cannot access admin GET endpoint"""
        token = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert token is not None
        
        response = self.session.get(f"{BASE_URL}/api/admin/condominium-settings")
        # Should be 403 Forbidden or 401 Unauthorized
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Guard correctly denied from admin GET settings")
    
    def test_resident_cannot_access_admin_get_settings(self):
        """Resident cannot access admin GET endpoint"""
        token = self.login(RESIDENT_EMAIL, RESIDENT_PASSWORD)
        assert token is not None
        
        response = self.session.get(f"{BASE_URL}/api/admin/condominium-settings")
        # Should be 403 Forbidden or 401 Unauthorized
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Resident correctly denied from admin GET settings")
    
    def test_unauthenticated_cannot_access_settings(self):
        """Unauthenticated user cannot access any settings endpoint"""
        # Clear any existing auth
        self.session.headers.pop("Authorization", None)
        
        # Try admin endpoint
        response = self.session.get(f"{BASE_URL}/api/admin/condominium-settings")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        # Try public endpoint
        response = self.session.get(f"{BASE_URL}/api/condominium-settings/public")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        print("✓ Unauthenticated user correctly denied access")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
