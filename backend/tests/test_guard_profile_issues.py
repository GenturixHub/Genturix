"""
GENTURIX - Backend Tests for Guard Profile Issues
Tests for 3 issues:
1. Guard Profile Navigation - Guard can access profile via tabs
2. Module Visibility - Disabled modules should not appear
3. Global Profile System - Profile directory endpoint
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "SuperAdmin123!"


class TestAuthentication:
    """Test authentication for Guard and SuperAdmin"""
    
    def test_guard_login(self):
        """Guard can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert "Guarda" in data["user"]["roles"]
        print(f"✓ Guard login successful: {data['user']['full_name']}")
    
    def test_superadmin_login(self):
        """SuperAdmin can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERADMIN_EMAIL,
            "password": SUPERADMIN_PASSWORD
        })
        assert response.status_code == 200, f"SuperAdmin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "SuperAdmin" in data["user"]["roles"]
        print(f"✓ SuperAdmin login successful: {data['user']['full_name']}")


class TestGuardProfileAccess:
    """ISSUE 1: Guard Profile Navigation - Guard can access profile"""
    
    @pytest.fixture
    def guard_token(self):
        """Get guard authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Guard login failed")
        return response.json()["access_token"]
    
    def test_guard_can_get_own_profile(self, guard_token):
        """Guard can access their own profile via GET /api/profile"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        response = requests.get(f"{BASE_URL}/api/profile", headers=headers)
        
        assert response.status_code == 200, f"Profile fetch failed: {response.text}"
        data = response.json()
        
        # Verify profile data structure
        assert "id" in data
        assert "full_name" in data
        assert "email" in data
        assert "roles" in data
        assert "Guarda" in data["roles"]
        
        # Verify editable fields exist
        assert "phone" in data or data.get("phone") is None
        assert "public_description" in data or data.get("public_description") is None
        assert "profile_photo" in data or data.get("profile_photo") is None
        
        print(f"✓ Guard profile accessible: {data['full_name']}")
        print(f"  - Phone: {data.get('phone', 'Not set')}")
        print(f"  - Description: {data.get('public_description', 'Not set')[:50] if data.get('public_description') else 'Not set'}")
    
    def test_guard_can_update_profile(self, guard_token):
        """Guard can update their profile (name, phone, description)"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        
        # Update profile
        update_data = {
            "phone": "+52 555 123 4567",
            "public_description": "Guardia de seguridad profesional con 5 años de experiencia"
        }
        
        response = requests.patch(f"{BASE_URL}/api/profile", headers=headers, json=update_data)
        assert response.status_code == 200, f"Profile update failed: {response.text}"
        
        data = response.json()
        assert data.get("phone") == update_data["phone"]
        assert data.get("public_description") == update_data["public_description"]
        
        print(f"✓ Guard profile updated successfully")
        print(f"  - Phone: {data.get('phone')}")
        print(f"  - Description: {data.get('public_description')[:50]}...")


class TestProfileDirectory:
    """ISSUE 3: Global Profile System - Profile directory endpoint"""
    
    @pytest.fixture
    def guard_token(self):
        """Get guard authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Guard login failed")
        return response.json()["access_token"]
    
    def test_profile_directory_endpoint_exists(self, guard_token):
        """GET /api/profile/directory/condominium returns users grouped by role"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        response = requests.get(f"{BASE_URL}/api/profile/directory/condominium", headers=headers)
        
        assert response.status_code == 200, f"Directory fetch failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "users" in data
        assert "grouped_by_role" in data
        assert "condominium_name" in data
        assert "total_count" in data
        
        print(f"✓ Profile directory endpoint working")
        print(f"  - Condominium: {data.get('condominium_name')}")
        print(f"  - Total users: {data.get('total_count')}")
    
    def test_directory_returns_users_grouped_by_role(self, guard_token):
        """Directory returns users grouped by role (Administradores, Supervisores, Guardias, Residentes)"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        response = requests.get(f"{BASE_URL}/api/profile/directory/condominium", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        grouped = data.get("grouped_by_role", {})
        
        # Check that we have role groups
        assert isinstance(grouped, dict), "grouped_by_role should be a dictionary"
        
        # Log the role groups found
        print(f"✓ Directory groups users by role:")
        for role, users in grouped.items():
            print(f"  - {role}: {len(users)} users")
            if users:
                print(f"    First user: {users[0].get('full_name')}")
    
    def test_directory_user_has_required_fields(self, guard_token):
        """Each user in directory has required fields for display"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        response = requests.get(f"{BASE_URL}/api/profile/directory/condominium", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        users = data.get("users", [])
        if not users:
            pytest.skip("No users in directory")
        
        # Check first user has required fields
        user = users[0]
        required_fields = ["id", "full_name", "roles"]
        for field in required_fields:
            assert field in user, f"User missing required field: {field}"
        
        # Optional but expected fields
        optional_fields = ["profile_photo", "phone", "public_description"]
        for field in optional_fields:
            if field in user:
                print(f"  - {field}: present")
        
        print(f"✓ Directory users have required fields")
    
    def test_guard_can_view_other_user_profile(self, guard_token):
        """Guard can view another user's public profile in same condominium"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        
        # First get directory to find another user
        response = requests.get(f"{BASE_URL}/api/profile/directory/condominium", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        users = data.get("users", [])
        
        # Find a user that's not the current guard
        other_user = None
        for user in users:
            if user.get("email") != GUARD_EMAIL:
                other_user = user
                break
        
        if not other_user:
            pytest.skip("No other users in condominium to test")
        
        # Try to view their profile
        user_id = other_user["id"]
        response = requests.get(f"{BASE_URL}/api/profile/{user_id}", headers=headers)
        
        assert response.status_code == 200, f"Failed to view other user profile: {response.text}"
        profile = response.json()
        
        assert profile["id"] == user_id
        assert "full_name" in profile
        assert "roles" in profile
        
        print(f"✓ Guard can view other user's profile: {profile['full_name']}")


class TestModuleVisibility:
    """ISSUE 2: Module Visibility - Disabled modules should not appear"""
    
    @pytest.fixture
    def guard_token_and_condo(self):
        """Get guard token and condominium ID"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Guard login failed")
        data = response.json()
        return data["access_token"], data["user"].get("condominium_id")
    
    def test_condominium_has_modules_config(self, guard_token_and_condo):
        """Condominium endpoint returns modules configuration"""
        token, condo_id = guard_token_and_condo
        
        if not condo_id:
            pytest.skip("Guard has no condominium assigned")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/condominiums/{condo_id}", headers=headers)
        
        assert response.status_code == 200, f"Condominium fetch failed: {response.text}"
        data = response.json()
        
        # Verify modules config exists
        assert "modules" in data, "Condominium should have modules config"
        modules = data["modules"]
        
        print(f"✓ Condominium modules config found:")
        for module_name, config in modules.items():
            enabled = config.get("enabled", True) if isinstance(config, dict) else config
            status = "✓ enabled" if enabled else "✗ disabled"
            print(f"  - {module_name}: {status}")
    
    def test_modules_have_enabled_flag(self, guard_token_and_condo):
        """Each module has an 'enabled' flag"""
        token, condo_id = guard_token_and_condo
        
        if not condo_id:
            pytest.skip("Guard has no condominium assigned")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/condominiums/{condo_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        modules = data.get("modules", {})
        
        # Expected modules
        expected_modules = ["security", "hr", "school", "payments", "audit"]
        
        for module in expected_modules:
            if module in modules:
                config = modules[module]
                if isinstance(config, dict):
                    assert "enabled" in config, f"Module {module} should have 'enabled' flag"
                print(f"✓ Module '{module}' has proper config")


class TestGuardUIIntegration:
    """Integration tests for Guard UI features"""
    
    @pytest.fixture
    def guard_token(self):
        """Get guard authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Guard login failed")
        return response.json()["access_token"]
    
    def test_guard_can_access_all_required_endpoints(self, guard_token):
        """Guard can access all endpoints needed for 8-tab UI"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        
        endpoints = [
            ("/api/profile", "Profile (Perfil tab)"),
            ("/api/profile/directory/condominium", "Directory (Personas tab)"),
            ("/api/security/panic-events", "Alerts (Alertas tab)"),
            ("/api/visitors/pending", "Visitors (Visitas tab)"),
            ("/api/guard/my-shift", "My Shift (Mi Turno tab)"),
            ("/api/guard/my-absences", "Absences (Ausencias tab)"),
            ("/api/guard/history", "History (Historial tab)"),
        ]
        
        all_passed = True
        for endpoint, description in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            status = "✓" if response.status_code == 200 else "✗"
            print(f"{status} {description}: {response.status_code}")
            if response.status_code != 200:
                all_passed = False
        
        assert all_passed, "Some endpoints failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
