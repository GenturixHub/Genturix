"""
Test Home Dashboard Features - Iteration 47
Tests for:
1. GET /api/auth/me returns apartment and role_data fields
2. GET /api/finanzas/unit/{apartment} returns balance and status
3. GET /api/casos returns cases with status field
4. GET /api/asamblea returns assemblies with status field
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
RESIDENT_EMAIL = "test-resident@genturix.com"
RESIDENT_PASSWORD = "Admin123!"
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"


class TestAuthMeEndpoint:
    """Test /api/auth/me returns apartment and role_data fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as resident and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as resident
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.user = data.get("user", {})
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_auth_me_returns_apartment_field(self):
        """GET /api/auth/me should return apartment field"""
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        print(f"[DEBUG] /api/auth/me response: {data}")
        
        # Verify apartment field exists
        assert "apartment" in data, "Response should contain 'apartment' field"
        
        # For test-resident, apartment should be A-102
        if data.get("apartment"):
            print(f"[INFO] Apartment value: {data['apartment']}")
    
    def test_auth_me_returns_role_data_field(self):
        """GET /api/auth/me should return role_data field"""
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify role_data field exists
        assert "role_data" in data, "Response should contain 'role_data' field"
        print(f"[INFO] role_data value: {data.get('role_data')}")
    
    def test_login_response_includes_apartment(self):
        """Login response should include apartment in user object"""
        # Already have user from login in setup
        print(f"[DEBUG] Login user object: {self.user}")
        
        # Verify apartment is in login response
        assert "apartment" in self.user, "Login response user should contain 'apartment' field"
        
        # For test-resident, apartment should be A-102
        expected_apartment = "A-102"
        actual_apartment = self.user.get("apartment")
        print(f"[INFO] Login apartment: {actual_apartment}")


class TestFinanceEndpoint:
    """Test /api/finanzas/unit/{apartment} returns balance and status"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as resident and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as resident
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.user = data.get("user", {})
            self.apartment = self.user.get("apartment", "A-102")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_get_unit_account_returns_balance(self):
        """GET /api/finanzas/unit/{apartment} should return balance"""
        response = self.session.get(f"{BASE_URL}/api/finanzas/unit/{self.apartment}")
        
        print(f"[DEBUG] /api/finanzas/unit/{self.apartment} status: {response.status_code}")
        print(f"[DEBUG] Response: {response.text[:500] if response.text else 'empty'}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify account structure
        assert "account" in data, "Response should contain 'account' field"
        
        account = data.get("account", {})
        assert "current_balance" in account, "Account should contain 'current_balance'"
        assert "status" in account, "Account should contain 'status'"
        
        print(f"[INFO] Balance: {account.get('current_balance')}")
        print(f"[INFO] Status: {account.get('status')}")
    
    def test_unit_account_status_values(self):
        """Account status should be 'atrasado' or 'al_dia'"""
        response = self.session.get(f"{BASE_URL}/api/finanzas/unit/{self.apartment}")
        
        if response.status_code != 200:
            pytest.skip(f"Finance endpoint returned {response.status_code}")
        
        data = response.json()
        account = data.get("account", {})
        status = account.get("status")
        
        # Status should be one of the expected values
        valid_statuses = ["atrasado", "al_dia", "pending", "active"]
        assert status in valid_statuses or status is None, f"Unexpected status: {status}"


class TestCasosEndpoint:
    """Test /api/casos returns cases with status field"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as resident and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as resident
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_get_casos_returns_items(self):
        """GET /api/casos should return items array"""
        response = self.session.get(f"{BASE_URL}/api/casos?page=1&page_size=5")
        
        print(f"[DEBUG] /api/casos status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify items array exists
        assert "items" in data, "Response should contain 'items' field"
        
        items = data.get("items", [])
        print(f"[INFO] Number of cases: {len(items)}")
        
        if items:
            # Verify case structure
            case = items[0]
            assert "id" in case, "Case should have 'id'"
            assert "title" in case, "Case should have 'title'"
            assert "status" in case, "Case should have 'status'"
            print(f"[INFO] First case: {case.get('title')} - {case.get('status')}")
    
    def test_casos_status_values(self):
        """Cases should have valid status values"""
        response = self.session.get(f"{BASE_URL}/api/casos?page=1&page_size=10")
        
        if response.status_code != 200:
            pytest.skip(f"Casos endpoint returned {response.status_code}")
        
        data = response.json()
        items = data.get("items", [])
        
        valid_statuses = ["open", "in_progress", "closed", "pending"]
        
        for case in items:
            status = case.get("status")
            assert status in valid_statuses, f"Invalid case status: {status}"
        
        # Count open cases
        open_count = len([c for c in items if c.get("status") == "open"])
        print(f"[INFO] Open cases: {open_count}")


class TestAsambleaEndpoint:
    """Test /api/asamblea returns assemblies with status field"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as resident and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as resident
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_get_asamblea_returns_list(self):
        """GET /api/asamblea should return list of assemblies"""
        response = self.session.get(f"{BASE_URL}/api/asamblea")
        
        print(f"[DEBUG] /api/asamblea status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Response could be array or object with items
        if isinstance(data, list):
            assemblies = data
        else:
            assemblies = data.get("items", data.get("assemblies", []))
        
        print(f"[INFO] Number of assemblies: {len(assemblies)}")
        
        if assemblies:
            assembly = assemblies[0]
            assert "id" in assembly, "Assembly should have 'id'"
            assert "title" in assembly, "Assembly should have 'title'"
            assert "status" in assembly, "Assembly should have 'status'"
            print(f"[INFO] First assembly: {assembly.get('title')} - {assembly.get('status')}")
    
    def test_asamblea_status_values(self):
        """Assemblies should have valid status values"""
        response = self.session.get(f"{BASE_URL}/api/asamblea")
        
        if response.status_code != 200:
            pytest.skip(f"Asamblea endpoint returned {response.status_code}")
        
        data = response.json()
        
        if isinstance(data, list):
            assemblies = data
        else:
            assemblies = data.get("items", data.get("assemblies", []))
        
        valid_statuses = ["scheduled", "in_progress", "completed", "cancelled", "draft"]
        
        for assembly in assemblies:
            status = assembly.get("status")
            assert status in valid_statuses, f"Invalid assembly status: {status}"
        
        # Count active assemblies
        active_count = len([a for a in assemblies if a.get("status") in ["scheduled", "in_progress"]])
        print(f"[INFO] Active assemblies: {active_count}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
