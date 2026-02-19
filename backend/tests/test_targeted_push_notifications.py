"""
Test suite for Dynamic Targeting System for Push Notifications

Tests the new send_targeted_push_notification() function and verifies:
1. Function exists with correct signature
2. Health endpoint works
3. Login works with all credentials
4. Legacy helper functions still exist (send_push_to_user, send_push_to_guards, send_push_to_admins)
5. notify_guards_of_panic() is unchanged

Feature: Sistema dinámico de targeting para push notifications
"""
import pytest
import requests
import os
import sys
import inspect
import importlib.util

# Test against public URL
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    pytest.skip("REACT_APP_BACKEND_URL not set", allow_module_level=True)

# Test credentials
TEST_CREDENTIALS = {
    "superadmin": {"email": "superadmin@genturix.com", "password": "SuperAdmin123!"},
    "admin": {"email": "admin@genturix.com", "password": "Admin123!"},
    "guard": {"email": "guarda1@genturix.com", "password": "Guard123!"},
    "resident": {"email": "residente@genturix.com", "password": "Resi123!"}
}


class TestHealthEndpoint:
    """Verify backend is healthy before running other tests"""
    
    def test_health_endpoint_returns_200(self):
        """GET /api/health should return 200 with status ok"""
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200, f"Health check failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "ok", f"Unexpected status: {data}"
        assert data.get("database") == "connected", f"Database not connected: {data}"
        print(f"✓ Health endpoint: {data}")


class TestLoginWithCredentials:
    """Verify all provided credentials work"""
    
    def test_superadmin_login(self):
        """SuperAdmin login should work"""
        creds = TEST_CREDENTIALS["superadmin"]
        response = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=10)
        assert response.status_code == 200, f"SuperAdmin login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert data["user"]["email"] == creds["email"]
        assert "SuperAdmin" in data["user"]["roles"]
        print(f"✓ SuperAdmin login successful")
    
    def test_admin_login(self):
        """Admin login should work"""
        creds = TEST_CREDENTIALS["admin"]
        response = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=10)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == creds["email"]
        print(f"✓ Admin login successful")
    
    def test_guard_login(self):
        """Guard login should work"""
        creds = TEST_CREDENTIALS["guard"]
        response = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=10)
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == creds["email"]
        print(f"✓ Guard login successful")
    
    def test_resident_login(self):
        """Resident login should work"""
        creds = TEST_CREDENTIALS["resident"]
        response = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=10)
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == creds["email"]
        print(f"✓ Resident login successful")
    
    def test_invalid_credentials_rejected(self):
        """Invalid credentials should return 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        }, timeout=10)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Invalid credentials correctly rejected")


class TestSendTargetedPushNotificationExists:
    """
    Verify send_targeted_push_notification() function exists and has correct signature
    This is a code inspection test - verifies the function structure
    """
    
    def test_function_exists_in_server_py(self):
        """Verify send_targeted_push_notification function exists in server.py"""
        # Read server.py directly
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check function definition exists
        assert "async def send_targeted_push_notification(" in content, \
            "send_targeted_push_notification function not found in server.py"
        print("✓ send_targeted_push_notification function exists")
    
    def test_function_has_correct_parameters(self):
        """Verify send_targeted_push_notification has the expected parameters"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Find the function definition and its parameters
        import re
        
        # Look for the function signature (may span multiple lines)
        pattern = r"async def send_targeted_push_notification\((.*?)\) -> dict:"
        match = re.search(pattern, content, re.DOTALL)
        
        assert match, "Could not find send_targeted_push_notification signature"
        
        params_str = match.group(1)
        
        # Check required parameters
        expected_params = [
            "condominium_id",
            "title",
            "body",
            "target_roles",
            "target_user_ids",
            "exclude_user_ids",
            "data",
            "tag",
            "require_interaction"
        ]
        
        for param in expected_params:
            assert param in params_str, f"Parameter '{param}' not found in function signature"
        
        print(f"✓ All expected parameters found: {expected_params}")
    
    def test_function_returns_dict_with_expected_keys(self):
        """Verify the function returns correct result structure"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check result dictionary initialization
        expected_keys = ['"sent"', '"failed"', '"total"', '"skipped"', '"target_type"', '"reason"']
        
        # Find the result dict initialization
        assert 'result = {' in content and '"sent": 0' in content, \
            "Result dictionary not properly initialized"
        
        for key in expected_keys:
            assert key in content, f"Expected key {key} not found in result dict"
        
        print(f"✓ Function returns dict with expected keys")


class TestLegacyPushFunctionsExist:
    """
    Verify legacy helper functions still exist for backward compatibility
    - send_push_to_user
    - send_push_to_guards
    - send_push_to_admins
    """
    
    def test_send_push_to_user_exists(self):
        """send_push_to_user should still exist"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        assert "async def send_push_to_user(" in content, \
            "send_push_to_user function not found - backward compatibility broken"
        print("✓ send_push_to_user function exists (backward compatible)")
    
    def test_send_push_to_guards_exists(self):
        """send_push_to_guards should still exist"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        assert "async def send_push_to_guards(" in content, \
            "send_push_to_guards function not found - backward compatibility broken"
        print("✓ send_push_to_guards function exists (backward compatible)")
    
    def test_send_push_to_admins_exists(self):
        """send_push_to_admins should still exist"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        assert "async def send_push_to_admins(" in content, \
            "send_push_to_admins function not found - backward compatibility broken"
        print("✓ send_push_to_admins function exists (backward compatible)")


class TestNotifyGuardsOfPanicUnchanged:
    """
    Verify notify_guards_of_panic() function was NOT modified
    This is critical - the panic notification system must remain unchanged
    """
    
    def test_notify_guards_of_panic_exists(self):
        """notify_guards_of_panic should still exist"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        assert "async def notify_guards_of_panic(" in content, \
            "notify_guards_of_panic function not found"
        print("✓ notify_guards_of_panic function exists")
    
    def test_notify_guards_of_panic_signature_unchanged(self):
        """notify_guards_of_panic should have the same signature"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Expected signature: condominium_id: str, panic_data: dict, sender_id: str = None
        expected_pattern = "async def notify_guards_of_panic(condominium_id: str, panic_data: dict, sender_id: str = None)"
        
        assert expected_pattern in content, \
            f"notify_guards_of_panic signature has changed! Expected: {expected_pattern}"
        print("✓ notify_guards_of_panic signature unchanged")
    
    def test_notify_guards_of_panic_not_using_targeted_function(self):
        """notify_guards_of_panic should NOT call send_targeted_push_notification"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        import re
        
        # Find the notify_guards_of_panic function body
        # Look for function start
        func_start = content.find("async def notify_guards_of_panic(")
        assert func_start > 0, "notify_guards_of_panic not found"
        
        # Find the next function definition (end of notify_guards_of_panic)
        next_func = content.find("async def send_push_to_user(", func_start)
        
        if next_func > func_start:
            func_body = content[func_start:next_func]
        else:
            # If not found, get next 3000 chars
            func_body = content[func_start:func_start + 3000]
        
        # Verify it does NOT call send_targeted_push_notification
        assert "send_targeted_push_notification" not in func_body, \
            "notify_guards_of_panic was modified to use send_targeted_push_notification - this is NOT allowed"
        
        # Verify it still uses send_push_notification directly
        assert "send_push_notification" in func_body, \
            "notify_guards_of_panic should still call send_push_notification directly"
        
        print("✓ notify_guards_of_panic implementation unchanged (does not use targeted function)")


class TestTargetedPushUsedInPreRegistration:
    """
    Verify send_targeted_push_notification is used for pre-registration notifications
    (Line ~3893 in server.py)
    """
    
    def test_preregistration_uses_targeted_push(self):
        """Pre-registration endpoint should use send_targeted_push_notification"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check that preregistration uses targeted push for guards
        assert 'await send_targeted_push_notification(' in content, \
            "send_targeted_push_notification is never called"
        
        # Check it targets guards for preregistration
        assert 'target_roles=["Guarda"]' in content, \
            "send_targeted_push_notification not targeting Guarda role"
        
        # Check it's for visitor preregistration
        assert '"type": "visitor_preregistration"' in content, \
            "visitor_preregistration notification type not found"
        
        print("✓ Pre-registration uses send_targeted_push_notification with target_roles=['Guarda']")


class TestTargetedPushUsedInReservations:
    """
    Verify send_targeted_push_notification is used for pending reservations
    (Line ~8298 in server.py)
    """
    
    def test_reservations_uses_targeted_push(self):
        """Pending reservations should notify Administrador and Supervisor"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check it targets admins/supervisors for reservations
        assert 'target_roles=["Administrador", "Supervisor"]' in content, \
            "Reservations not targeting Administrador/Supervisor roles"
        
        # Check it's for reservation pending
        assert '"type": "reservation_pending"' in content, \
            "reservation_pending notification type not found"
        
        print("✓ Reservations uses send_targeted_push_notification with target_roles=['Administrador', 'Supervisor']")


class TestTargetedPushValidations:
    """
    Verify the function has proper validations
    """
    
    def test_vapid_key_validation(self):
        """Function should check for VAPID keys"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Look for VAPID validation in the function
        assert 'VAPID_PUBLIC_KEY' in content and 'VAPID_PRIVATE_KEY' in content, \
            "VAPID key validation not found"
        
        # Check for the assignment format used in code
        assert 'result["reason"] = "VAPID keys not configured"' in content, \
            "VAPID validation reason message not found"
        
        print("✓ VAPID key validation present")
    
    def test_condominium_validation(self):
        """Function should validate condominium exists"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for the assignment format used in code
        assert 'result["reason"] = "No condominium_id provided"' in content or \
               'result["reason"] = "Condominium not found"' in content, \
            "Condominium validation not found"
        
        print("✓ Condominium validation present")
    
    def test_targeting_requirement_validation(self):
        """Function should require either target_roles or target_user_ids"""
        server_path = "/app/backend/server.py"
        
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Check for the assignment format used in code
        assert 'result["reason"] = "No targeting specified (target_roles or target_user_ids required)"' in content, \
            "Targeting requirement validation not found"
        
        print("✓ Targeting requirement validation present")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
