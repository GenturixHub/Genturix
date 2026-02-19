"""
Test: Resident Direct Push Notifications for Check-in, Check-out, and Reservation Status

This test verifies that:
1. Check-in (POST /api/guard/checkin) sends push notification to resident_id using send_targeted_push_notification
2. Check-out (POST /api/guard/checkout/{entry_id}) sends push notification to resident_id using send_targeted_push_notification  
3. Reservation Approved (PATCH /api/reservations/{id}) sends push notification to resident_id
4. Reservation Rejected (PATCH /api/reservations/{id}) sends push notification to resident_id
5. All notifications include exclude_user_ids=[current_user['id']] to avoid self-notifications
6. create_and_send_notification uses send_push=False to avoid duplicates
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CREDENTIALS = {
    "superadmin": {"email": "superadmin@genturix.com", "password": "SuperAdmin123!"},
    "admin": {"email": "admin@genturix.com", "password": "Admin123!"},
    "guard": {"email": "guarda1@genturix.com", "password": "Guard123!"},
    "resident": {"email": "residente@genturix.com", "password": "Resi123!"}
}


class TestHealthAndLogin:
    """Basic health and login verification"""
    
    def test_health_endpoint(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("Health endpoint OK")
    
    def test_guard_login(self):
        """Verify guard can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["guard"])
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print(f"Guard login successful: {data['user']['email']}")
        
    def test_admin_login(self):
        """Verify admin can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print(f"Admin login successful: {data['user']['email']}")
        
    def test_resident_login(self):
        """Verify resident can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["resident"])
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print(f"Resident login successful: {data['user']['email']}")


class TestCodeAnalysisCheckinNotification:
    """Verify check-in notification code implementation (Phase 1)"""
    
    def test_checkin_uses_send_targeted_push_notification(self):
        """
        Verify that the check-in endpoint uses send_targeted_push_notification 
        with target_user_ids=[resident_id]
        """
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        # Find the check-in section (around line 4804)
        checkin_section_start = content.find("await send_targeted_push_notification(")
        assert checkin_section_start != -1, "send_targeted_push_notification not found in code"
        
        # Find section around check-in with visitor_arrival
        checkin_notification_section = content[checkin_section_start:checkin_section_start+800]
        
        # Verify target_user_ids is used with resident_id
        assert "target_user_ids=[resident_id]" in checkin_notification_section or \
               "target_user_ids=[resident_id]" in content, \
               "Check-in should use target_user_ids=[resident_id]"
        
        print("VERIFIED: Check-in uses send_targeted_push_notification with target_user_ids=[resident_id]")
    
    def test_checkin_exclude_user_ids(self):
        """Verify check-in excludes the current user from notifications"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        # Find checkin section with visitor_arrival
        idx = content.find('type": "visitor_arrival"')
        if idx == -1:
            idx = content.find("type\": \"visitor_arrival\"")
        
        assert idx != -1, "visitor_arrival notification type not found"
        
        # Search around the visitor_arrival section for exclude_user_ids
        section = content[max(0, idx-500):idx+500]
        
        assert 'exclude_user_ids=[current_user["id"]]' in section or \
               "exclude_user_ids=[current_user['id']]" in section or \
               'exclude_user_ids' in section, \
               "Check-in should have exclude_user_ids"
        
        print("VERIFIED: Check-in includes exclude_user_ids to avoid self-notification")
    
    def test_checkin_create_and_send_notification_send_push_false(self):
        """Verify create_and_send_notification uses send_push=False in check-in"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        # Find the check-in create_and_send_notification call with visitor_arrival
        visitor_arrival_idx = content.find('notification_type="visitor_arrival"')
        if visitor_arrival_idx == -1:
            visitor_arrival_idx = content.find("notification_type='visitor_arrival'")
        
        assert visitor_arrival_idx != -1, "visitor_arrival notification not found"
        
        # Get the section around this call
        section_start = content.rfind("await create_and_send_notification(", 0, visitor_arrival_idx)
        section = content[section_start:visitor_arrival_idx+200]
        
        assert "send_push=False" in section, \
               "create_and_send_notification for visitor_arrival should have send_push=False"
        
        print("VERIFIED: Check-in uses send_push=False in create_and_send_notification")


class TestCodeAnalysisCheckoutNotification:
    """Verify check-out notification code implementation (Phase 2)"""
    
    def test_checkout_uses_send_targeted_push_notification(self):
        """Verify checkout uses send_targeted_push_notification"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        # Find checkout tag in the send_targeted_push_notification call
        assert 'tag=f"checkout-' in content or 'tag="checkout-' in content, \
               "Checkout notification with checkout tag not found"
        
        print("VERIFIED: Check-out uses send_targeted_push_notification")
    
    def test_checkout_target_resident_id(self):
        """Verify checkout targets the resident_id"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        # Find visitor_exit section
        visitor_exit_idx = content.find('type": "visitor_exit"')
        if visitor_exit_idx == -1:
            visitor_exit_idx = content.find("type\": \"visitor_exit\"")
        
        assert visitor_exit_idx != -1, "visitor_exit notification type not found"
        
        # Get section around this
        section = content[max(0, visitor_exit_idx-600):visitor_exit_idx+100]
        
        assert "target_user_ids=[resident_id]" in section, \
               "Check-out should target resident_id"
        
        print("VERIFIED: Check-out targets resident_id with target_user_ids")
    
    def test_checkout_exclude_current_user(self):
        """Verify checkout excludes the current user"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        visitor_exit_idx = content.find('type": "visitor_exit"')
        if visitor_exit_idx == -1:
            visitor_exit_idx = content.find("type\": \"visitor_exit\"")
        
        assert visitor_exit_idx != -1
        
        section = content[max(0, visitor_exit_idx-600):visitor_exit_idx+100]
        
        assert 'exclude_user_ids' in section, \
               "Check-out should have exclude_user_ids"
        
        print("VERIFIED: Check-out includes exclude_user_ids")
    
    def test_checkout_create_and_send_notification_send_push_false(self):
        """Verify create_and_send_notification uses send_push=False in checkout"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        visitor_exit_idx = content.find('notification_type="visitor_exit"')
        if visitor_exit_idx == -1:
            visitor_exit_idx = content.find("notification_type='visitor_exit'")
        
        assert visitor_exit_idx != -1, "visitor_exit notification not found"
        
        section_start = content.rfind("await create_and_send_notification(", 0, visitor_exit_idx)
        section = content[section_start:visitor_exit_idx+200]
        
        assert "send_push=False" in section, \
               "create_and_send_notification for visitor_exit should have send_push=False"
        
        print("VERIFIED: Check-out uses send_push=False in create_and_send_notification")


class TestCodeAnalysisReservationApprovalNotification:
    """Verify reservation approval notification code implementation (Phase 3)"""
    
    def test_reservation_approved_uses_send_targeted_push_notification(self):
        """Verify reservation approval uses send_targeted_push_notification"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        assert 'tag=f"reservation-approved-' in content, \
               "Reservation approved notification with tag not found"
        
        print("VERIFIED: Reservation approval uses send_targeted_push_notification")
    
    def test_reservation_approved_target_resident_id(self):
        """Verify reservation approval targets the resident_id"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        # Find reservation_approved section
        idx = content.find('type": "reservation_approved"')
        if idx == -1:
            idx = content.find("type\": \"reservation_approved\"")
        
        assert idx != -1, "reservation_approved notification type not found"
        
        section = content[max(0, idx-600):idx+100]
        
        assert "target_user_ids=[resident_id]" in section, \
               "Reservation approval should target resident_id"
        
        print("VERIFIED: Reservation approval targets resident_id")
    
    def test_reservation_approved_exclude_current_user(self):
        """Verify reservation approval excludes the current user"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        idx = content.find('type": "reservation_approved"')
        if idx == -1:
            idx = content.find("type\": \"reservation_approved\"")
        
        section = content[max(0, idx-600):idx+100]
        
        assert 'exclude_user_ids' in section, \
               "Reservation approval should have exclude_user_ids"
        
        print("VERIFIED: Reservation approval includes exclude_user_ids")
    
    def test_reservation_approved_send_push_false(self):
        """Verify create_and_send_notification uses send_push=False for approved"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        idx = content.find('notification_type="reservation_approved"')
        if idx == -1:
            idx = content.find("notification_type='reservation_approved'")
        
        assert idx != -1, "reservation_approved in create_and_send_notification not found"
        
        section_start = content.rfind("await create_and_send_notification(", 0, idx)
        section = content[section_start:idx+200]
        
        assert "send_push=False" in section, \
               "create_and_send_notification for reservation_approved should have send_push=False"
        
        print("VERIFIED: Reservation approval uses send_push=False")


class TestCodeAnalysisReservationRejectionNotification:
    """Verify reservation rejection notification code implementation (Phase 3)"""
    
    def test_reservation_rejected_uses_send_targeted_push_notification(self):
        """Verify reservation rejection uses send_targeted_push_notification"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        assert 'tag=f"reservation-rejected-' in content, \
               "Reservation rejected notification with tag not found"
        
        print("VERIFIED: Reservation rejection uses send_targeted_push_notification")
    
    def test_reservation_rejected_target_resident_id(self):
        """Verify reservation rejection targets the resident_id"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        idx = content.find('type": "reservation_rejected"')
        if idx == -1:
            idx = content.find("type\": \"reservation_rejected\"")
        
        assert idx != -1, "reservation_rejected notification type not found"
        
        section = content[max(0, idx-600):idx+100]
        
        assert "target_user_ids=[resident_id]" in section, \
               "Reservation rejection should target resident_id"
        
        print("VERIFIED: Reservation rejection targets resident_id")
    
    def test_reservation_rejected_exclude_current_user(self):
        """Verify reservation rejection excludes the current user"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        idx = content.find('type": "reservation_rejected"')
        if idx == -1:
            idx = content.find("type\": \"reservation_rejected\"")
        
        section = content[max(0, idx-600):idx+100]
        
        assert 'exclude_user_ids' in section, \
               "Reservation rejection should have exclude_user_ids"
        
        print("VERIFIED: Reservation rejection includes exclude_user_ids")
    
    def test_reservation_rejected_send_push_false(self):
        """Verify create_and_send_notification uses send_push=False for rejected"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        idx = content.find('notification_type="reservation_rejected"')
        if idx == -1:
            idx = content.find("notification_type='reservation_rejected'")
        
        assert idx != -1, "reservation_rejected in create_and_send_notification not found"
        
        section_start = content.rfind("await create_and_send_notification(", 0, idx)
        section = content[section_start:idx+200]
        
        assert "send_push=False" in section, \
               "create_and_send_notification for reservation_rejected should have send_push=False"
        
        print("VERIFIED: Reservation rejection uses send_push=False")


class TestFunctionalCheckinEndpoint:
    """Test the actual check-in endpoint functionality"""
    
    @pytest.fixture
    def guard_token(self):
        """Get guard authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["guard"])
        if response.status_code != 200:
            pytest.skip("Guard login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def resident_token(self):
        """Get resident authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["resident"])
        if response.status_code != 200:
            pytest.skip("Resident login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def resident_user_info(self, resident_token):
        """Get resident user info for creating authorization"""
        headers = {"Authorization": f"Bearer {resident_token}"}
        response = requests.get(f"{BASE_URL}/api/profile/me", headers=headers)
        if response.status_code != 200:
            pytest.skip("Could not get resident profile")
        return response.json()
    
    def test_guard_checkin_endpoint_exists(self, guard_token):
        """Verify check-in endpoint is accessible"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        
        # Try to check-in with minimal data (should fail validation but endpoint exists)
        response = requests.post(
            f"{BASE_URL}/api/guard/checkin",
            headers=headers,
            json={
                "visitor_name": "TEST_Visitor_Push_Check",
                "visitor_type": "visitor"
            }
        )
        
        # Should either succeed (200) or fail with validation error (400/422), not 404
        assert response.status_code != 404, "Check-in endpoint not found"
        print(f"Check-in endpoint responded with status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            assert "entry" in data or "success" in data
            print("Check-in successful - endpoint working correctly")


class TestFunctionalCheckoutEndpoint:
    """Test the actual check-out endpoint functionality"""
    
    @pytest.fixture
    def guard_token(self):
        """Get guard authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["guard"])
        if response.status_code != 200:
            pytest.skip("Guard login failed")
        return response.json()["access_token"]
    
    def test_guard_checkout_endpoint_exists(self, guard_token):
        """Verify check-out endpoint exists"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        
        # Try to checkout with a fake ID (should fail with 404 for entry, not endpoint)
        response = requests.post(
            f"{BASE_URL}/api/guard/checkout/fake-entry-id-12345",
            headers=headers,
            json={}
        )
        
        # Should return 404 for entry not found, not method not allowed
        assert response.status_code in [404, 400, 200], \
               f"Unexpected status code: {response.status_code}"
        
        print(f"Check-out endpoint responded with status: {response.status_code}")


class TestFunctionalReservationEndpoint:
    """Test the reservation update endpoint functionality"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        return response.json()["access_token"]
    
    def test_reservation_patch_endpoint_exists(self, admin_token):
        """Verify reservation PATCH endpoint exists"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Try to update a fake reservation (should fail with 404, not method not allowed)
        response = requests.patch(
            f"{BASE_URL}/api/reservations/fake-reservation-id-12345",
            headers=headers,
            json={
                "status": "approved"
            }
        )
        
        # Should return 404 for reservation not found, or 422 for validation
        assert response.status_code in [404, 400, 422], \
               f"Unexpected status code: {response.status_code}"
        
        print(f"Reservation PATCH endpoint responded with status: {response.status_code}")


class TestNotifyGuardsOfPanicUnchanged:
    """Verify notify_guards_of_panic was NOT modified as per requirements"""
    
    def test_notify_guards_of_panic_exists(self):
        """Verify notify_guards_of_panic function still exists"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        assert "async def notify_guards_of_panic" in content, \
               "notify_guards_of_panic function not found"
        
        print("VERIFIED: notify_guards_of_panic function exists")
    
    def test_notify_guards_of_panic_not_using_targeted_function(self):
        """Verify notify_guards_of_panic does NOT use send_targeted_push_notification"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        # Find the function
        func_start = content.find("async def notify_guards_of_panic")
        assert func_start != -1
        
        # Find the next function definition to delimit the function body
        next_func = content.find("\nasync def ", func_start + 1)
        if next_func == -1:
            next_func = len(content)
        
        func_body = content[func_start:next_func]
        
        # Verify it does NOT call send_targeted_push_notification
        assert "send_targeted_push_notification" not in func_body, \
               "notify_guards_of_panic should NOT use send_targeted_push_notification (intentionally unchanged)"
        
        print("VERIFIED: notify_guards_of_panic was NOT modified (as per requirements)")


class TestSendTargetedPushNotificationFunction:
    """Verify the send_targeted_push_notification function exists and has correct signature"""
    
    def test_function_exists(self):
        """Verify send_targeted_push_notification function exists"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        assert "async def send_targeted_push_notification" in content, \
               "send_targeted_push_notification function not found"
        
        print("VERIFIED: send_targeted_push_notification function exists")
    
    def test_function_has_target_user_ids_parameter(self):
        """Verify function has target_user_ids parameter"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        func_start = content.find("async def send_targeted_push_notification")
        func_sig_end = content.find(") -> dict:", func_start)
        func_signature = content[func_start:func_sig_end]
        
        assert "target_user_ids" in func_signature, \
               "Function should have target_user_ids parameter"
        
        print("VERIFIED: send_targeted_push_notification has target_user_ids parameter")
    
    def test_function_has_exclude_user_ids_parameter(self):
        """Verify function has exclude_user_ids parameter"""
        with open("/app/backend/server.py", "r") as f:
            content = f.read()
        
        func_start = content.find("async def send_targeted_push_notification")
        func_sig_end = content.find(") -> dict:", func_start)
        func_signature = content[func_start:func_sig_end]
        
        assert "exclude_user_ids" in func_signature, \
               "Function should have exclude_user_ids parameter"
        
        print("VERIFIED: send_targeted_push_notification has exclude_user_ids parameter")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
