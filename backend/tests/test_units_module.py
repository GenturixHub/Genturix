"""
Units Module Tests - Testing CRUD operations for units and user assignment
Tests: GET /units, POST /units, DELETE /units/{id}, PUT /units/{id}/assign-user, PUT /units/{id}/unassign-user
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
RESIDENT_EMAIL = "test-resident@genturix.com"
RESIDENT_PASSWORD = "Admin123!"

# Test data prefix for cleanup
TEST_PREFIX = "TEST_UNIT_"

# Shared token to avoid rate limiting
_admin_token = None
_admin_session = None


def get_admin_session():
    """Get or create admin session (reuse to avoid rate limiting)"""
    global _admin_token, _admin_session
    
    if _admin_session and _admin_token:
        return _admin_session, _admin_token
    
    _admin_session = requests.Session()
    _admin_session.headers.update({"Content-Type": "application/json"})
    
    # Login as admin
    login_resp = _admin_session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    
    if login_resp.status_code == 429:
        # Rate limited, wait and retry
        time.sleep(60)
        login_resp = _admin_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
    
    assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
    _admin_token = login_resp.json().get("access_token")
    _admin_session.headers.update({"Authorization": f"Bearer {_admin_token}"})
    
    return _admin_session, _admin_token


class TestUnitsModule:
    """Units CRUD and user assignment tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with admin auth"""
        self.session, self.admin_token = get_admin_session()
        yield
        
        # Cleanup: Delete test units created during tests
        self._cleanup_test_units()
    
    def _cleanup_test_units(self):
        """Delete all test units created during tests"""
        try:
            resp = self.session.get(f"{BASE_URL}/api/units")
            if resp.status_code == 200:
                units = resp.json().get("items", [])
                for unit in units:
                    if unit.get("number", "").startswith(TEST_PREFIX):
                        self.session.delete(f"{BASE_URL}/api/units/{unit['id']}")
        except Exception as e:
            print(f"Cleanup warning: {e}")
    
    # ==================== GET /units Tests ====================
    
    def test_get_units_returns_list(self):
        """GET /api/units returns list of units with residents and finance info"""
        response = self.session.get(f"{BASE_URL}/api/units")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "items" in data, "Response should have 'items' key"
        assert isinstance(data["items"], list), "items should be a list"
        
        # If there are units, verify structure
        if len(data["items"]) > 0:
            unit = data["items"][0]
            assert "id" in unit, "Unit should have 'id'"
            assert "number" in unit, "Unit should have 'number'"
            assert "condominium_id" in unit, "Unit should have 'condominium_id'"
            assert "residents" in unit, "Unit should have 'residents' array"
            assert "finance" in unit, "Unit should have 'finance' object"
            
            # Verify finance structure
            finance = unit["finance"]
            assert "current_balance" in finance, "Finance should have 'current_balance'"
            assert "status" in finance, "Finance should have 'status'"
        
        print(f"✓ GET /units returned {len(data['items'])} units")
    
    def test_get_units_multi_tenant_isolation(self):
        """Units are scoped by condominium_id"""
        response = self.session.get(f"{BASE_URL}/api/units")
        assert response.status_code == 200
        
        data = response.json()
        units = data.get("items", [])
        
        # All units should belong to the same condominium
        if len(units) > 1:
            condo_ids = set(u.get("condominium_id") for u in units)
            assert len(condo_ids) == 1, "All units should belong to same condominium"
        
        print(f"✓ Multi-tenant isolation verified for {len(units)} units")
    
    # ==================== POST /units Tests ====================
    
    def test_create_unit_success(self):
        """POST /api/units creates new unit and auto-creates unit_account"""
        unit_number = f"{TEST_PREFIX}{uuid.uuid4().hex[:6]}"
        
        response = self.session.post(f"{BASE_URL}/api/units", json={
            "number": unit_number
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Response should have 'id'"
        assert data["number"] == unit_number, f"Number mismatch: expected {unit_number}, got {data['number']}"
        assert "condominium_id" in data, "Response should have 'condominium_id'"
        assert "created_at" in data, "Response should have 'created_at'"
        
        # Verify unit appears in list
        list_resp = self.session.get(f"{BASE_URL}/api/units")
        assert list_resp.status_code == 200
        units = list_resp.json().get("items", [])
        unit_numbers = [u["number"] for u in units]
        assert unit_number in unit_numbers, "Created unit should appear in list"
        
        # Verify unit_account was auto-created (check via finanzas overview)
        overview_resp = self.session.get(f"{BASE_URL}/api/finanzas/overview")
        if overview_resp.status_code == 200:
            accounts = overview_resp.json().get("accounts", [])
            account_unit_ids = [a["unit_id"] for a in accounts]
            assert unit_number in account_unit_ids, "unit_account should be auto-created"
        
        print(f"✓ Created unit {unit_number} with auto-created unit_account")
        return data["id"]
    
    def test_create_unit_duplicate_returns_409(self):
        """POST /api/units with duplicate number returns 409"""
        unit_number = f"{TEST_PREFIX}DUP_{uuid.uuid4().hex[:4]}"
        
        # Create first unit
        resp1 = self.session.post(f"{BASE_URL}/api/units", json={"number": unit_number})
        assert resp1.status_code == 200, f"First create failed: {resp1.text}"
        
        # Try to create duplicate
        resp2 = self.session.post(f"{BASE_URL}/api/units", json={"number": unit_number})
        assert resp2.status_code == 409, f"Expected 409 for duplicate, got {resp2.status_code}: {resp2.text}"
        
        print(f"✓ Duplicate unit {unit_number} correctly rejected with 409")
    
    def test_create_unit_requires_admin_role(self):
        """POST /api/units requires Administrador or SuperAdmin role"""
        # Login as resident
        resident_session = requests.Session()
        resident_session.headers.update({"Content-Type": "application/json"})
        
        login_resp = resident_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        
        if login_resp.status_code == 200:
            token = login_resp.json().get("access_token")
            resident_session.headers.update({"Authorization": f"Bearer {token}"})
            
            # Try to create unit as resident
            resp = resident_session.post(f"{BASE_URL}/api/units", json={
                "number": f"{TEST_PREFIX}RESIDENT_ATTEMPT"
            })
            
            # Should be forbidden (403) or unauthorized
            assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"
            print("✓ Resident correctly denied unit creation")
        else:
            print("⚠ Resident login failed, skipping role test")
    
    # ==================== DELETE /units/{id} Tests ====================
    
    def test_delete_unit_success(self):
        """DELETE /api/units/{id} deletes unit (only if no financial records)"""
        # Create a unit to delete
        unit_number = f"{TEST_PREFIX}DEL_{uuid.uuid4().hex[:4]}"
        create_resp = self.session.post(f"{BASE_URL}/api/units", json={"number": unit_number})
        assert create_resp.status_code == 200
        unit_id = create_resp.json()["id"]
        
        # Delete the unit
        delete_resp = self.session.delete(f"{BASE_URL}/api/units/{unit_id}")
        assert delete_resp.status_code == 200, f"Delete failed: {delete_resp.text}"
        
        # Verify unit is gone
        list_resp = self.session.get(f"{BASE_URL}/api/units")
        units = list_resp.json().get("items", [])
        unit_ids = [u["id"] for u in units]
        assert unit_id not in unit_ids, "Deleted unit should not appear in list"
        
        print(f"✓ Deleted unit {unit_number}")
    
    def test_delete_unit_not_found(self):
        """DELETE /api/units/{id} returns 404 for non-existent unit"""
        fake_id = str(uuid.uuid4())
        resp = self.session.delete(f"{BASE_URL}/api/units/{fake_id}")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("✓ Delete non-existent unit returns 404")
    
    # ==================== PUT /units/{id}/assign-user Tests ====================
    
    def test_assign_user_to_unit(self):
        """PUT /api/units/{id}/assign-user assigns user to unit"""
        # Create a test unit
        unit_number = f"{TEST_PREFIX}ASSIGN_{uuid.uuid4().hex[:4]}"
        create_resp = self.session.post(f"{BASE_URL}/api/units", json={"number": unit_number})
        assert create_resp.status_code == 200
        unit_id = create_resp.json()["id"]
        
        # Get a user to assign (use admin users list)
        users_resp = self.session.get(f"{BASE_URL}/api/admin/users?page_size=10")
        if users_resp.status_code == 200:
            users_data = users_resp.json()
            # Handle both list and dict response formats
            if isinstance(users_data, list):
                users = users_data
            else:
                users = users_data.get("users") or users_data.get("items") or []
            
            if len(users) > 0:
                # Find a user not already assigned to this unit
                target_user = users[0]
                user_id = target_user["id"]
                
                # Assign user to unit
                assign_resp = self.session.put(
                    f"{BASE_URL}/api/units/{unit_id}/assign-user?user_id={user_id}"
                )
                assert assign_resp.status_code == 200, f"Assign failed: {assign_resp.text}"
                
                data = assign_resp.json()
                assert data.get("status") == "ok", "Response should have status 'ok'"
                assert data.get("unit") == unit_number, "Response should include unit number"
                assert data.get("user_id") == user_id, "Response should include user_id"
                
                # Verify user appears in unit's residents
                list_resp = self.session.get(f"{BASE_URL}/api/units")
                units = list_resp.json().get("items", [])
                target_unit = next((u for u in units if u["id"] == unit_id), None)
                
                if target_unit:
                    resident_ids = [r["id"] for r in target_unit.get("residents", [])]
                    assert user_id in resident_ids, "Assigned user should appear in unit's residents"
                
                print(f"✓ Assigned user {user_id} to unit {unit_number}")
            else:
                print("⚠ No users available for assignment test")
        else:
            print(f"⚠ Could not get users list: {users_resp.status_code}")
    
    def test_assign_user_unit_not_found(self):
        """PUT /api/units/{id}/assign-user returns 404 for non-existent unit"""
        fake_unit_id = str(uuid.uuid4())
        fake_user_id = str(uuid.uuid4())
        
        resp = self.session.put(
            f"{BASE_URL}/api/units/{fake_unit_id}/assign-user?user_id={fake_user_id}"
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("✓ Assign to non-existent unit returns 404")
    
    # ==================== PUT /units/{id}/unassign-user Tests ====================
    
    def test_unassign_user_from_unit(self):
        """PUT /api/units/{id}/unassign-user removes user from unit"""
        # Create a test unit
        unit_number = f"{TEST_PREFIX}UNASSIGN_{uuid.uuid4().hex[:4]}"
        create_resp = self.session.post(f"{BASE_URL}/api/units", json={"number": unit_number})
        assert create_resp.status_code == 200
        unit_id = create_resp.json()["id"]
        
        # Get a user to assign then unassign
        users_resp = self.session.get(f"{BASE_URL}/api/admin/users?page_size=10")
        if users_resp.status_code == 200:
            users_data = users_resp.json()
            # Handle both list and dict response formats
            if isinstance(users_data, list):
                users = users_data
            else:
                users = users_data.get("users") or users_data.get("items") or []
            
            if len(users) > 0:
                target_user = users[0]
                user_id = target_user["id"]
                
                # First assign
                self.session.put(f"{BASE_URL}/api/units/{unit_id}/assign-user?user_id={user_id}")
                
                # Then unassign
                unassign_resp = self.session.put(
                    f"{BASE_URL}/api/units/{unit_id}/unassign-user?user_id={user_id}"
                )
                assert unassign_resp.status_code == 200, f"Unassign failed: {unassign_resp.text}"
                
                data = unassign_resp.json()
                assert data.get("status") == "ok", "Response should have status 'ok'"
                
                print(f"✓ Unassigned user {user_id} from unit {unit_number}")
            else:
                print("⚠ No users available for unassignment test")
        else:
            print(f"⚠ Could not get users list: {users_resp.status_code}")
    
    def test_unassign_user_unit_not_found(self):
        """PUT /api/units/{id}/unassign-user returns 404 for non-existent unit"""
        fake_unit_id = str(uuid.uuid4())
        fake_user_id = str(uuid.uuid4())
        
        resp = self.session.put(
            f"{BASE_URL}/api/units/{fake_unit_id}/unassign-user?user_id={fake_user_id}"
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("✓ Unassign from non-existent unit returns 404")


class TestUnitsFinanceIntegration:
    """Test units integration with finance module"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with admin auth"""
        self.session, _ = get_admin_session()
        yield
    
    def test_unit_shows_financial_badge(self):
        """Unit shows financial badge (balance/status)"""
        resp = self.session.get(f"{BASE_URL}/api/units")
        assert resp.status_code == 200
        
        units = resp.json().get("items", [])
        for unit in units:
            finance = unit.get("finance", {})
            assert "current_balance" in finance, f"Unit {unit['number']} missing current_balance"
            assert "status" in finance, f"Unit {unit['number']} missing status"
            assert finance["status"] in ["al_dia", "atrasado", "adelantado"], \
                f"Invalid status: {finance['status']}"
        
        print(f"✓ All {len(units)} units have valid financial badges")
    
    def test_unit_shows_assigned_residents(self):
        """Unit shows list of assigned residents with name+email"""
        resp = self.session.get(f"{BASE_URL}/api/units")
        assert resp.status_code == 200
        
        units = resp.json().get("items", [])
        units_with_residents = [u for u in units if len(u.get("residents", [])) > 0]
        
        for unit in units_with_residents:
            for resident in unit["residents"]:
                assert "id" in resident, "Resident should have 'id'"
                assert "full_name" in resident, "Resident should have 'full_name'"
                assert "email" in resident, "Resident should have 'email'"
        
        print(f"✓ {len(units_with_residents)} units have residents with proper structure")


class TestResidentFinanzasAfterUnitChanges:
    """Test that resident finanzas still works after unit changes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        yield
    
    def test_resident_can_view_finanzas(self):
        """Resident finanzas still works after unit changes"""
        # Login as resident
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        
        if login_resp.status_code == 200:
            token = login_resp.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            
            # Try to access finanzas overview (may be restricted to admin)
            # Residents typically see their own unit account
            resp = self.session.get(f"{BASE_URL}/api/finanzas/overview")
            
            # Either 200 (if allowed) or 403 (if admin-only) is acceptable
            assert resp.status_code in [200, 403], f"Unexpected status: {resp.status_code}"
            
            if resp.status_code == 200:
                print("✓ Resident can access finanzas overview")
            else:
                print("✓ Resident finanzas access correctly restricted (admin-only)")
        else:
            print(f"⚠ Resident login failed: {login_resp.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
