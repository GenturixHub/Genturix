"""
Pre-production Patch Set Tests
Testing 3 fixes:
1. Notifications for preregistered visitors (guard_notifications collection)
2. PDF history download (frontend - tested separately)  
3. Privacy section with Change Password accordion (frontend - tested separately)

This file tests Fix 1: Backend notification creation when authorization is created
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
RESIDENT_EMAIL = "test-resident@genturix.com"
RESIDENT_PASSWORD = "Admin123!"
GUARD_EMAIL = "test-guard@genturix.com"
GUARD_PASSWORD = "Guard123!"


class TestAuthorizationNotifications:
    """
    Fix 1: Test that creating visitor authorization generates guard notifications
    """
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        """Get resident auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Resident login failed: {response.status_code} - {response.text}")
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def guard_token(self):
        """Get guard auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": GUARD_EMAIL, "password": GUARD_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Guard login failed: {response.status_code} - {response.text}")
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def resident_info(self, resident_token):
        """Get resident profile info"""
        response = requests.get(
            f"{BASE_URL}/api/profile",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        if response.status_code != 200:
            pytest.skip(f"Failed to get resident profile: {response.status_code}")
        return response.json()
    
    @pytest.fixture(scope="class")
    def guard_info(self, guard_token):
        """Get guard profile info"""
        response = requests.get(
            f"{BASE_URL}/api/profile",
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        if response.status_code != 200:
            pytest.skip(f"Failed to get guard profile: {response.status_code}")
        return response.json()
    
    def test_resident_login_success(self, resident_token):
        """Test resident can login"""
        assert resident_token is not None
        assert len(resident_token) > 10
        print(f"✅ Resident login successful, token length: {len(resident_token)}")
    
    def test_guard_login_success(self, guard_token):
        """Test guard can login"""
        assert guard_token is not None
        assert len(guard_token) > 10
        print(f"✅ Guard login successful, token length: {len(guard_token)}")
    
    def test_create_authorization_creates_notification(self, resident_token, guard_token, resident_info, guard_info):
        """
        FIX 1 MAIN TEST: When resident creates visitor authorization,
        a notification should be created in guard_notifications collection
        """
        # Ensure both users are in the same condominium
        resident_condo = resident_info.get("condominium_id")
        guard_condo = guard_info.get("condominium_id")
        
        if not resident_condo:
            pytest.skip("Resident doesn't have a condominium assigned")
        
        if resident_condo != guard_condo:
            pytest.skip(f"Resident and guard are in different condominiums: {resident_condo} vs {guard_condo}")
        
        # Get guard notifications BEFORE creating authorization
        response_before = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        before_status = response_before.status_code
        notifications_before = []
        if before_status == 200:
            notifications_before = response_before.json()  # Returns list directly
        count_before = len(notifications_before)
        print(f"📋 Guard notifications before: {count_before}")
        
        # Create unique visitor name for tracking
        unique_name = f"TEST_Visitor_{int(time.time())}"
        
        # Create visitor authorization
        auth_payload = {
            "visitor_name": unique_name,
            "identification_number": "TEST123456",
            "vehicle_plate": "ABC123",
            "authorization_type": "temporary",
            "valid_from": "2026-01-20",
            "valid_to": "2026-01-25",
            "notes": "Test authorization for notification verification"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/authorizations",
            json=auth_payload,
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        
        # Check authorization was created
        assert create_response.status_code in [200, 201], f"Authorization creation failed: {create_response.status_code} - {create_response.text}"
        created_auth = create_response.json()
        auth_id = created_auth.get("id")
        assert auth_id is not None, "Authorization ID not returned"
        print(f"✅ Authorization created: {auth_id} for visitor: {unique_name}")
        
        # Wait a moment for async notification processing
        time.sleep(1)
        
        # Get guard notifications AFTER creating authorization
        response_after = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        
        assert response_after.status_code == 200, f"Failed to get guard notifications: {response_after.status_code}"
        notifications_after = response_after.json()  # Returns list directly
        count_after = len(notifications_after)
        print(f"📋 Guard notifications after: {count_after}")
        
        # Verify notification count increased
        assert count_after > count_before, f"Expected notification count to increase. Before: {count_before}, After: {count_after}"
        print(f"✅ Notification count increased from {count_before} to {count_after}")
        
        # Find the notification for our visitor
        notification_found = None
        for notif in notifications_after:
            if unique_name in str(notif.get("message", "")) or unique_name in str(notif.get("title", "")):
                notification_found = notif
                break
            # Also check in data field
            if notif.get("data", {}).get("visitor_name") == unique_name:
                notification_found = notif
                break
            # Check if authorization_id matches
            if notif.get("data", {}).get("authorization_id") == auth_id:
                notification_found = notif
                break
        
        assert notification_found is not None, f"Notification for visitor '{unique_name}' not found in guard notifications"
        print(f"✅ Notification found for visitor: {unique_name}")
        print(f"   Type: {notification_found.get('type')}")
        print(f"   Message: {notification_found.get('message')}")
        
        # Verify notification structure
        assert notification_found.get("type") == "visitor_preregistration", f"Expected type 'visitor_preregistration', got '{notification_found.get('type')}'"
        assert notification_found.get("read") == False, "Notification should be unread"
        
        # Cleanup: Delete the test authorization
        delete_response = requests.delete(
            f"{BASE_URL}/api/authorizations/{auth_id}",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        print(f"🧹 Cleanup: Authorization delete status: {delete_response.status_code}")
        
        print("✅ FIX 1 VERIFIED: Visitor authorization creates guard notification")


class TestHealthEndpoints:
    """Basic health check tests"""
    
    def test_health_check(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print(f"✅ Health check passed: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
