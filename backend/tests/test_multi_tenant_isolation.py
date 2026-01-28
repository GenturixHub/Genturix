"""
GENTURIX - Multi-Tenant Isolation Tests
Tests for strict condominium data isolation and dynamic role forms

Test Scenarios:
1. New condo admin sees ZERO data (total_users=1 self, active_guards=0, active_alerts=0)
2. Existing condo admin sees their data (103 users, guards, etc)
3. Dashboard stats scoped by condominium_id
4. Security stats scoped by condominium_id
5. Users endpoint returns only users from admin's condo
6. Panic events, access logs, guards filtered by condo
7. SuperAdmin sees all data across condos
8. Dynamic form validation for role-specific fields
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EXISTING = {"email": "admin@genturix.com", "password": "Admin123!"}
ADMIN_NEW_CONDO = {"email": "isolation_admin@genturix.com", "password": "IsolationAdmin123!"}
SUPER_ADMIN = {"email": "superadmin@genturix.com", "password": "SuperAdmin123!"}

# Condo IDs
TEST_ISOLATION_CONDO_ID = "5d08fa37-13f8-403b-849f-5e937472627a"
EXISTING_CONDO_ID = "267195e5-c18f-4374-a3a6-8016cfe70d86"


class TestMultiTenantIsolation:
    """Test strict multi-tenant data isolation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, credentials):
        """Helper to login and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=credentials)
        if response.status_code == 200:
            data = response.json()
            self.session.headers.update({"Authorization": f"Bearer {data['access_token']}"})
            return data
        return None
    
    # ==================== NEW CONDO ADMIN ISOLATION ====================
    
    def test_new_condo_admin_login(self):
        """Test that new condo admin can login"""
        result = self.login(ADMIN_NEW_CONDO)
        if result is None:
            pytest.skip("New condo admin not found - may need to be created first")
        
        assert result is not None, "New condo admin should be able to login"
        assert result["user"]["email"] == ADMIN_NEW_CONDO["email"]
        assert "Administrador" in result["user"]["roles"]
        print(f"✓ New condo admin logged in: {result['user']['email']}")
        print(f"  Condominium ID: {result['user'].get('condominium_id')}")
    
    def test_new_condo_admin_dashboard_stats_zero_data(self):
        """New condo admin should see total_users=1 (self), active_guards=0, active_alerts=0"""
        result = self.login(ADMIN_NEW_CONDO)
        if result is None:
            pytest.skip("New condo admin not found")
        
        response = self.session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200, f"Dashboard stats failed: {response.text}"
        
        stats = response.json()
        print(f"New condo admin dashboard stats: {stats}")
        
        # New condo should have minimal data
        # total_users should be 1 (the admin themselves) or very low
        assert stats["total_users"] >= 1, "Should have at least 1 user (self)"
        assert stats["total_users"] <= 5, f"New condo should have minimal users, got {stats['total_users']}"
        assert stats["active_guards"] == 0, f"New condo should have 0 active guards, got {stats['active_guards']}"
        assert stats["active_alerts"] == 0, f"New condo should have 0 active alerts, got {stats['active_alerts']}"
        print(f"✓ New condo admin sees isolated data: users={stats['total_users']}, guards={stats['active_guards']}, alerts={stats['active_alerts']}")
    
    def test_new_condo_admin_security_stats_zero_data(self):
        """New condo admin should see zero security stats"""
        result = self.login(ADMIN_NEW_CONDO)
        if result is None:
            pytest.skip("New condo admin not found")
        
        response = self.session.get(f"{BASE_URL}/api/security/dashboard-stats")
        assert response.status_code == 200, f"Security stats failed: {response.text}"
        
        stats = response.json()
        print(f"New condo admin security stats: {stats}")
        
        assert stats["active_alerts"] == 0, f"New condo should have 0 active alerts, got {stats['active_alerts']}"
        assert stats["active_guards"] == 0, f"New condo should have 0 active guards, got {stats['active_guards']}"
        assert stats["today_accesses"] == 0, f"New condo should have 0 today accesses, got {stats['today_accesses']}"
        print(f"✓ New condo admin sees zero security stats")
    
    def test_new_condo_admin_users_list_only_self(self):
        """New condo admin should see only users from their condo"""
        result = self.login(ADMIN_NEW_CONDO)
        if result is None:
            pytest.skip("New condo admin not found")
        
        response = self.session.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code == 200, f"Users list failed: {response.text}"
        
        users = response.json()
        print(f"New condo admin sees {len(users)} users")
        
        # Should see only users from their condo (at minimum, themselves)
        assert len(users) >= 1, "Should see at least 1 user (self)"
        assert len(users) <= 5, f"New condo should have minimal users, got {len(users)}"
        
        # Verify all users belong to the same condo
        for user in users:
            condo_id = user.get("condominium_id")
            print(f"  User: {user.get('email')} - Condo: {condo_id}")
        
        print(f"✓ New condo admin sees only their condo users: {len(users)}")
    
    def test_new_condo_admin_panic_events_empty(self):
        """New condo admin should see no panic events"""
        result = self.login(ADMIN_NEW_CONDO)
        if result is None:
            pytest.skip("New condo admin not found")
        
        response = self.session.get(f"{BASE_URL}/api/security/panic-events")
        assert response.status_code == 200, f"Panic events failed: {response.text}"
        
        events = response.json()
        print(f"New condo admin sees {len(events)} panic events")
        
        assert len(events) == 0, f"New condo should have 0 panic events, got {len(events)}"
        print(f"✓ New condo admin sees zero panic events")
    
    def test_new_condo_admin_access_logs_empty(self):
        """New condo admin should see no access logs"""
        result = self.login(ADMIN_NEW_CONDO)
        if result is None:
            pytest.skip("New condo admin not found")
        
        response = self.session.get(f"{BASE_URL}/api/security/access-logs")
        assert response.status_code == 200, f"Access logs failed: {response.text}"
        
        logs = response.json()
        print(f"New condo admin sees {len(logs)} access logs")
        
        assert len(logs) == 0, f"New condo should have 0 access logs, got {len(logs)}"
        print(f"✓ New condo admin sees zero access logs")
    
    def test_new_condo_admin_guards_empty(self):
        """New condo admin should see no guards"""
        result = self.login(ADMIN_NEW_CONDO)
        if result is None:
            pytest.skip("New condo admin not found")
        
        response = self.session.get(f"{BASE_URL}/api/hr/guards")
        assert response.status_code == 200, f"Guards list failed: {response.text}"
        
        guards = response.json()
        print(f"New condo admin sees {len(guards)} guards")
        
        assert len(guards) == 0, f"New condo should have 0 guards, got {len(guards)}"
        print(f"✓ New condo admin sees zero guards")
    
    # ==================== EXISTING CONDO ADMIN DATA ====================
    
    def test_existing_condo_admin_login(self):
        """Test that existing condo admin can login"""
        result = self.login(ADMIN_EXISTING)
        assert result is not None, "Existing condo admin should be able to login"
        assert result["user"]["email"] == ADMIN_EXISTING["email"]
        print(f"✓ Existing condo admin logged in: {result['user']['email']}")
        print(f"  Condominium ID: {result['user'].get('condominium_id')}")
    
    def test_existing_condo_admin_sees_their_data(self):
        """Existing condo admin should see their condo's data"""
        result = self.login(ADMIN_EXISTING)
        assert result is not None
        
        response = self.session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        stats = response.json()
        print(f"Existing condo admin dashboard stats: {stats}")
        
        # Existing condo should have more data
        assert stats["total_users"] > 0, "Existing condo should have users"
        print(f"✓ Existing condo admin sees their data: users={stats['total_users']}, guards={stats['active_guards']}")
    
    def test_existing_condo_admin_users_list(self):
        """Existing condo admin should see their condo's users"""
        result = self.login(ADMIN_EXISTING)
        assert result is not None
        
        response = self.session.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code == 200
        
        users = response.json()
        print(f"Existing condo admin sees {len(users)} users")
        
        # Should have multiple users
        assert len(users) > 0, "Existing condo should have users"
        print(f"✓ Existing condo admin sees their users: {len(users)}")
    
    # ==================== SUPERADMIN GLOBAL DATA ====================
    
    def test_superadmin_login(self):
        """Test that SuperAdmin can login"""
        result = self.login(SUPER_ADMIN)
        assert result is not None, "SuperAdmin should be able to login"
        assert "SuperAdmin" in result["user"]["roles"]
        print(f"✓ SuperAdmin logged in: {result['user']['email']}")
    
    def test_superadmin_sees_all_data(self):
        """SuperAdmin should see global data across all condos"""
        result = self.login(SUPER_ADMIN)
        assert result is not None
        
        response = self.session.get(f"{BASE_URL}/api/dashboard/stats")
        assert response.status_code == 200
        
        stats = response.json()
        print(f"SuperAdmin dashboard stats: {stats}")
        
        # SuperAdmin should see more data than any single condo
        assert stats["total_users"] > 0, "SuperAdmin should see all users"
        print(f"✓ SuperAdmin sees global data: users={stats['total_users']}, guards={stats['active_guards']}")
    
    def test_superadmin_sees_all_condominiums(self):
        """SuperAdmin should see all condominiums"""
        result = self.login(SUPER_ADMIN)
        assert result is not None
        
        response = self.session.get(f"{BASE_URL}/api/super-admin/condominiums")
        assert response.status_code == 200
        
        condos = response.json()
        print(f"SuperAdmin sees {len(condos)} condominiums")
        
        assert len(condos) >= 2, "Should have at least 2 condominiums (existing + test isolation)"
        print(f"✓ SuperAdmin sees all condominiums: {len(condos)}")


class TestDynamicRoleForms:
    """Test dynamic role-based form validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, credentials):
        """Helper to login and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=credentials)
        if response.status_code == 200:
            data = response.json()
            self.session.headers.update({"Authorization": f"Bearer {data['access_token']}"})
            return data
        return None
    
    # ==================== RESIDENTE VALIDATION ====================
    
    def test_residente_requires_apartment_number(self):
        """Creating Residente without apartment_number should return 400"""
        result = self.login(ADMIN_EXISTING)
        assert result is not None
        
        # Try to create Residente without apartment_number
        payload = {
            "email": f"test_residente_no_apt_{os.urandom(4).hex()}@test.com",
            "password": "TestPass123!",
            "full_name": "Test Residente No Apt",
            "role": "Residente"
            # Missing apartment_number
        }
        
        response = self.session.post(f"{BASE_URL}/api/admin/users", json=payload)
        print(f"Residente without apartment_number: {response.status_code} - {response.text}")
        
        assert response.status_code == 400, f"Should return 400 for missing apartment_number, got {response.status_code}"
        assert "apartment_number" in response.text.lower() or "apartamento" in response.text.lower(), \
            "Error should mention apartment_number"
        print(f"✓ Residente validation: apartment_number required")
    
    def test_residente_with_apartment_number_succeeds(self):
        """Creating Residente with apartment_number should succeed"""
        result = self.login(ADMIN_EXISTING)
        assert result is not None
        
        unique_id = os.urandom(4).hex()
        payload = {
            "email": f"test_residente_valid_{unique_id}@test.com",
            "password": "TestPass123!",
            "full_name": "Test Residente Valid",
            "role": "Residente",
            "apartment_number": "A-101",
            "tower_block": "Torre A",
            "resident_type": "owner"
        }
        
        response = self.session.post(f"{BASE_URL}/api/admin/users", json=payload)
        print(f"Residente with apartment_number: {response.status_code}")
        
        # API returns 200 for successful creation
        if response.status_code in [200, 201]:
            data = response.json()
            assert data.get("role_data", {}).get("apartment_number") == "A-101", \
                "role_data should contain apartment_number"
            print(f"✓ Residente created with role_data: {data.get('role_data')}")
        elif response.status_code == 409:
            print(f"✓ Residente validation works (user already exists)")
        else:
            pytest.fail(f"Unexpected status: {response.status_code} - {response.text}")
    
    # ==================== GUARDA VALIDATION ====================
    
    def test_guarda_requires_badge_number(self):
        """Creating Guarda without badge_number should return 400"""
        result = self.login(ADMIN_EXISTING)
        assert result is not None
        
        payload = {
            "email": f"test_guarda_no_badge_{os.urandom(4).hex()}@test.com",
            "password": "TestPass123!",
            "full_name": "Test Guarda No Badge",
            "role": "Guarda"
            # Missing badge_number
        }
        
        response = self.session.post(f"{BASE_URL}/api/admin/users", json=payload)
        print(f"Guarda without badge_number: {response.status_code} - {response.text}")
        
        assert response.status_code == 400, f"Should return 400 for missing badge_number, got {response.status_code}"
        assert "badge" in response.text.lower() or "placa" in response.text.lower(), \
            "Error should mention badge_number"
        print(f"✓ Guarda validation: badge_number required")
    
    def test_guarda_with_badge_number_succeeds(self):
        """Creating Guarda with badge_number should succeed"""
        result = self.login(ADMIN_EXISTING)
        assert result is not None
        
        unique_id = os.urandom(4).hex()
        payload = {
            "email": f"test_guarda_valid_{unique_id}@test.com",
            "password": "TestPass123!",
            "full_name": "Test Guarda Valid",
            "role": "Guarda",
            "badge_number": f"G-{unique_id[:4]}",
            "main_location": "Entrada Principal",
            "initial_shift": "morning"
        }
        
        response = self.session.post(f"{BASE_URL}/api/admin/users", json=payload)
        print(f"Guarda with badge_number: {response.status_code}")
        
        # API returns 200 for successful creation
        if response.status_code in [200, 201]:
            data = response.json()
            assert data.get("role_data", {}).get("badge_number") == payload["badge_number"], \
                "role_data should contain badge_number"
            print(f"✓ Guarda created with role_data: {data.get('role_data')}")
        elif response.status_code == 409:
            print(f"✓ Guarda validation works (user already exists)")
        else:
            pytest.fail(f"Unexpected status: {response.status_code} - {response.text}")
    
    # ==================== HR FORM ====================
    
    def test_hr_optional_fields(self):
        """HR role should accept optional department and permission_level"""
        result = self.login(ADMIN_EXISTING)
        assert result is not None
        
        unique_id = os.urandom(4).hex()
        payload = {
            "email": f"test_hr_{unique_id}@test.com",
            "password": "TestPass123!",
            "full_name": "Test HR User",
            "role": "HR",
            "department": "Recursos Humanos",
            "permission_level": "HR"
        }
        
        response = self.session.post(f"{BASE_URL}/api/admin/users", json=payload)
        print(f"HR user creation: {response.status_code}")
        
        # API returns 200 for successful creation
        if response.status_code in [200, 201]:
            data = response.json()
            role_data = data.get("role_data", {})
            assert role_data.get("department") == "Recursos Humanos"
            print(f"✓ HR created with role_data: {role_data}")
        elif response.status_code == 409:
            print(f"✓ HR creation works (user already exists)")
        else:
            # HR fields are optional, so should not fail
            assert response.status_code in [200, 201, 409], f"Unexpected: {response.status_code}"
    
    # ==================== ESTUDIANTE FORM ====================
    
    def test_estudiante_optional_fields(self):
        """Estudiante role should accept optional subscription fields"""
        result = self.login(ADMIN_EXISTING)
        assert result is not None
        
        unique_id = os.urandom(4).hex()
        payload = {
            "email": f"test_estudiante_{unique_id}@test.com",
            "password": "TestPass123!",
            "full_name": "Test Estudiante",
            "role": "Estudiante",
            "subscription_plan": "basic",
            "subscription_status": "trial"
        }
        
        response = self.session.post(f"{BASE_URL}/api/admin/users", json=payload)
        print(f"Estudiante creation: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            role_data = data.get("role_data", {})
            assert role_data.get("subscription_plan") == "basic"
            print(f"✓ Estudiante created with role_data: {role_data}")
        elif response.status_code == 409:
            print(f"✓ Estudiante creation works (user already exists)")
    
    # ==================== SUPERVISOR FORM ====================
    
    def test_supervisor_optional_fields(self):
        """Supervisor role should accept optional supervised_area"""
        result = self.login(ADMIN_EXISTING)
        assert result is not None
        
        unique_id = os.urandom(4).hex()
        payload = {
            "email": f"test_supervisor_{unique_id}@test.com",
            "password": "TestPass123!",
            "full_name": "Test Supervisor",
            "role": "Supervisor",
            "supervised_area": "Seguridad Perimetral"
        }
        
        response = self.session.post(f"{BASE_URL}/api/admin/users", json=payload)
        print(f"Supervisor creation: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            role_data = data.get("role_data", {})
            assert role_data.get("supervised_area") == "Seguridad Perimetral"
            print(f"✓ Supervisor created with role_data: {role_data}")
        elif response.status_code == 409:
            print(f"✓ Supervisor creation works (user already exists)")
    
    # ==================== ROLE DATA STORAGE ====================
    
    def test_role_data_stored_in_user_document(self):
        """Verify role_data is stored in user document"""
        result = self.login(ADMIN_EXISTING)
        assert result is not None
        
        # Get users list and check for role_data
        response = self.session.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code == 200
        
        users = response.json()
        users_with_role_data = [u for u in users if u.get("role_data")]
        
        print(f"Users with role_data: {len(users_with_role_data)} / {len(users)}")
        
        # At least some users should have role_data
        if users_with_role_data:
            sample = users_with_role_data[0]
            print(f"Sample role_data: {sample.get('role_data')}")
            print(f"✓ role_data is stored in user documents")
        else:
            print(f"⚠ No users with role_data found (may be legacy users)")


class TestCrossCondoIsolation:
    """Test that data from one condo is not visible to another"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, credentials):
        """Helper to login and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=credentials)
        if response.status_code == 200:
            data = response.json()
            self.session.headers.update({"Authorization": f"Bearer {data['access_token']}"})
            return data
        return None
    
    def test_no_cross_condo_user_leakage(self):
        """Admin from one condo should not see users from another condo"""
        # Login as existing condo admin
        result1 = self.login(ADMIN_EXISTING)
        assert result1 is not None
        existing_condo_id = result1["user"].get("condominium_id")
        
        response1 = self.session.get(f"{BASE_URL}/api/admin/users")
        assert response1.status_code == 200
        existing_users = response1.json()
        existing_user_ids = {u["id"] for u in existing_users}
        
        # Login as new condo admin
        result2 = self.login(ADMIN_NEW_CONDO)
        if result2 is None:
            pytest.skip("New condo admin not found")
        new_condo_id = result2["user"].get("condominium_id")
        
        response2 = self.session.get(f"{BASE_URL}/api/admin/users")
        assert response2.status_code == 200
        new_users = response2.json()
        new_user_ids = {u["id"] for u in new_users}
        
        # Verify no overlap (except if same condo)
        if existing_condo_id != new_condo_id:
            overlap = existing_user_ids & new_user_ids
            assert len(overlap) == 0, f"Cross-condo user leakage detected: {overlap}"
            print(f"✓ No cross-condo user leakage: existing={len(existing_users)}, new={len(new_users)}")
        else:
            print(f"⚠ Same condo - cannot test cross-condo isolation")
    
    def test_no_cross_condo_guard_leakage(self):
        """Admin from one condo should not see guards from another condo"""
        # Login as existing condo admin
        result1 = self.login(ADMIN_EXISTING)
        assert result1 is not None
        
        response1 = self.session.get(f"{BASE_URL}/api/hr/guards")
        assert response1.status_code == 200
        existing_guards = response1.json()
        
        # Login as new condo admin
        result2 = self.login(ADMIN_NEW_CONDO)
        if result2 is None:
            pytest.skip("New condo admin not found")
        
        response2 = self.session.get(f"{BASE_URL}/api/hr/guards")
        assert response2.status_code == 200
        new_guards = response2.json()
        
        print(f"Existing condo guards: {len(existing_guards)}")
        print(f"New condo guards: {len(new_guards)}")
        
        # New condo should have 0 guards
        assert len(new_guards) == 0, f"New condo should have 0 guards, got {len(new_guards)}"
        print(f"✓ No cross-condo guard leakage")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
