"""
GENTURIX - Super Admin Dashboard Backend Tests
Testing:
- Super Admin login with superadmin@genturix.com / SuperAdmin123!
- /api/super-admin/stats - Platform KPIs
- /api/condominiums - List condominiums for SuperAdmin
- /api/super-admin/users - List all users with filters
- Condominium status change (active/demo/suspended)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://security-hub-39.preview.emergentagent.com').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "superadmin@genturix.com"
SUPER_ADMIN_PASSWORD = "SuperAdmin123!"
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"


class TestSuperAdminLogin:
    """Test Super Admin authentication"""
    
    def test_super_admin_login_success(self):
        """Super Admin can login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data, "Missing access_token"
        assert "refresh_token" in data, "Missing refresh_token"
        assert "user" in data, "Missing user object"
        
        # Verify user has SuperAdmin role
        user = data["user"]
        assert "SuperAdmin" in user["roles"], f"Expected SuperAdmin role, got: {user['roles']}"
        assert user["email"] == SUPER_ADMIN_EMAIL
        assert user["is_active"] == True
        
        print(f"✓ Super Admin login successful: {user['full_name']}")
    
    def test_super_admin_login_wrong_password(self):
        """Super Admin login fails with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": "WrongPassword123!"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Wrong password correctly rejected")


class TestSuperAdminStats:
    """Test /api/super-admin/stats endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get Super Admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_get_platform_stats(self):
        """GET /api/super-admin/stats returns correct KPIs"""
        response = requests.get(
            f"{BASE_URL}/api/super-admin/stats",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Stats failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "condominiums" in data, "Missing condominiums stats"
        assert "users" in data, "Missing users stats"
        assert "alerts" in data, "Missing alerts stats"
        assert "revenue" in data, "Missing revenue stats"
        
        # Verify condominiums structure
        condos = data["condominiums"]
        assert "total" in condos
        assert "active" in condos
        assert "demo" in condos
        assert "suspended" in condos
        assert isinstance(condos["total"], int)
        
        # Verify users structure
        users = data["users"]
        assert "total" in users
        assert "active" in users
        assert isinstance(users["total"], int)
        
        # Verify alerts structure
        alerts = data["alerts"]
        assert "total" in alerts
        assert "active" in alerts
        
        # Verify revenue structure
        revenue = data["revenue"]
        assert "mrr_usd" in revenue
        assert "price_per_user" in revenue
        assert revenue["price_per_user"] == 1.0  # $1 per user
        
        print(f"✓ Platform stats: {condos['total']} condos, {users['total']} users, ${revenue['mrr_usd']} MRR")
    
    def test_stats_requires_auth(self):
        """Stats endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/super-admin/stats")
        # Accept both 401 (Unauthorized) and 403 (Forbidden) as valid auth rejection
        assert response.status_code in [401, 403], f"Expected 401 or 403, got {response.status_code}"
        print("✓ Stats endpoint correctly requires auth")
    
    def test_stats_requires_super_admin_role(self):
        """Stats endpoint requires SuperAdmin or Administrador role"""
        # Login as guard (should not have access)
        guard_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        assert guard_response.status_code == 200
        guard_token = guard_response.json()["access_token"]
        
        response = requests.get(
            f"{BASE_URL}/api/super-admin/stats",
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Stats endpoint correctly restricts access to SuperAdmin/Admin")


class TestCondominiumsList:
    """Test /api/condominiums endpoint for SuperAdmin"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get Super Admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_list_condominiums(self):
        """GET /api/condominiums returns list with all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/condominiums",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"List failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have at least one condominium"
        
        # Verify structure of first condominium
        condo = data[0]
        required_fields = ["id", "name", "status", "is_demo", "discount_percent", "plan", "price_per_user", "current_users", "max_users"]
        for field in required_fields:
            assert field in condo, f"Missing field: {field}"
        
        # Verify status is valid
        assert condo["status"] in ["active", "demo", "suspended"], f"Invalid status: {condo['status']}"
        
        print(f"✓ Listed {len(data)} condominiums with all required fields")
    
    def test_condominiums_have_modules(self):
        """Condominiums include modules configuration"""
        response = requests.get(
            f"{BASE_URL}/api/condominiums",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            condo = data[0]
            assert "modules" in condo, "Missing modules field"
            modules = condo["modules"]
            
            # Check for expected modules
            expected_modules = ["security", "hr", "school", "payments", "audit"]
            for mod in expected_modules:
                assert mod in modules, f"Missing module: {mod}"
                assert "enabled" in modules[mod], f"Module {mod} missing 'enabled' field"
        
        print("✓ Condominiums include modules configuration")


class TestSuperAdminUsers:
    """Test /api/super-admin/users endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get Super Admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_get_all_users(self):
        """GET /api/super-admin/users returns all users"""
        response = requests.get(
            f"{BASE_URL}/api/super-admin/users",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get users failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have at least one user"
        
        # Verify user structure
        user = data[0]
        required_fields = ["id", "email", "full_name", "roles", "is_active"]
        for field in required_fields:
            assert field in user, f"Missing field: {field}"
        
        # Verify no password hash is returned
        assert "hashed_password" not in user, "Password hash should not be returned"
        
        print(f"✓ Listed {len(data)} users")
    
    def test_filter_users_by_role(self):
        """GET /api/super-admin/users?role=Guarda filters by role"""
        response = requests.get(
            f"{BASE_URL}/api/super-admin/users?role=Guarda",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Filter failed: {response.text}"
        data = response.json()
        
        # All returned users should have Guarda role
        for user in data:
            assert "Guarda" in user["roles"], f"User {user['email']} doesn't have Guarda role"
        
        print(f"✓ Filtered {len(data)} users with Guarda role")
    
    def test_users_include_condominium_name(self):
        """Users include condominium_name field"""
        response = requests.get(
            f"{BASE_URL}/api/super-admin/users",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that condominium_name is enriched (may be null if not assigned)
        for user in data:
            # Field should exist even if null
            if user.get("condominium_id"):
                assert "condominium_name" in user, f"User {user['email']} missing condominium_name"
        
        print("✓ Users include condominium_name enrichment")


class TestCondominiumStatusChange:
    """Test condominium status change functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get Super Admin token and create test condominium"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # Create a test condominium for status change tests
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(
            f"{BASE_URL}/api/condominiums",
            headers=self.headers,
            json={
                "name": f"TEST_StatusChange_{unique_id}",
                "address": "Status Test Address",
                "contact_email": f"status_{unique_id}@test.com",
                "contact_phone": "+1234567890",
                "max_users": 50
            }
        )
        assert create_response.status_code == 200
        self.test_condo_id = create_response.json()["id"]
    
    def test_change_status_to_demo(self):
        """POST /api/super-admin/condominiums/{id}/make-demo changes status to demo"""
        response = requests.post(
            f"{BASE_URL}/api/super-admin/condominiums/{self.test_condo_id}/make-demo",
            headers=self.headers,
            params={"max_users": 10}
        )
        
        assert response.status_code == 200, f"Make demo failed: {response.text}"
        data = response.json()
        assert "message" in data
        
        # Verify status changed
        get_response = requests.get(
            f"{BASE_URL}/api/condominiums",
            headers=self.headers
        )
        condos = get_response.json()
        test_condo = next((c for c in condos if c["id"] == self.test_condo_id), None)
        
        assert test_condo is not None, "Test condominium not found"
        assert test_condo["status"] == "demo", f"Expected demo status, got: {test_condo['status']}"
        assert test_condo["is_demo"] == True, "is_demo should be True"
        
        print("✓ Condominium status changed to demo")
    
    def test_update_condominium_status_via_patch(self):
        """PATCH /api/condominiums/{id} can update status"""
        # First make it demo
        requests.post(
            f"{BASE_URL}/api/super-admin/condominiums/{self.test_condo_id}/make-demo",
            headers=self.headers
        )
        
        # Now update via PATCH to suspended
        response = requests.patch(
            f"{BASE_URL}/api/condominiums/{self.test_condo_id}",
            headers=self.headers,
            json={"is_active": False}
        )
        
        assert response.status_code == 200, f"Patch failed: {response.text}"
        print("✓ Condominium can be updated via PATCH")


class TestUserLockUnlock:
    """Test user lock/unlock functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get Super Admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_lock_user(self):
        """PUT /api/super-admin/users/{id}/lock locks a user"""
        # Get a non-SuperAdmin user to lock
        users_response = requests.get(
            f"{BASE_URL}/api/super-admin/users",
            headers=self.headers
        )
        users = users_response.json()
        
        # Find a user that is not SuperAdmin
        test_user = next((u for u in users if "SuperAdmin" not in u["roles"] and u["is_active"]), None)
        
        if test_user:
            response = requests.put(
                f"{BASE_URL}/api/super-admin/users/{test_user['id']}/lock",
                headers=self.headers
            )
            
            assert response.status_code == 200, f"Lock failed: {response.text}"
            
            # Unlock the user to restore state
            requests.put(
                f"{BASE_URL}/api/super-admin/users/{test_user['id']}/unlock",
                headers=self.headers
            )
            
            print(f"✓ User {test_user['email']} locked and unlocked successfully")
        else:
            pytest.skip("No non-SuperAdmin active user found to test")
    
    def test_unlock_user(self):
        """PUT /api/super-admin/users/{id}/unlock unlocks a user"""
        # Get users
        users_response = requests.get(
            f"{BASE_URL}/api/super-admin/users",
            headers=self.headers
        )
        users = users_response.json()
        
        # Find a user that is not SuperAdmin
        test_user = next((u for u in users if "SuperAdmin" not in u["roles"]), None)
        
        if test_user:
            # First lock
            requests.put(
                f"{BASE_URL}/api/super-admin/users/{test_user['id']}/lock",
                headers=self.headers
            )
            
            # Then unlock
            response = requests.put(
                f"{BASE_URL}/api/super-admin/users/{test_user['id']}/unlock",
                headers=self.headers
            )
            
            assert response.status_code == 200, f"Unlock failed: {response.text}"
            print(f"✓ User {test_user['email']} unlocked successfully")
        else:
            pytest.skip("No non-SuperAdmin user found to test")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
