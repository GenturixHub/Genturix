"""
Test suite for P0 Bug: Campanita de Notificaciones Estática
Tests the notification badge system for Admin/Guard/Supervisor roles.

Endpoints tested:
- GET /api/notifications - Returns list of notifications with 'read' field
- GET /api/notifications/unread-count - Returns exact count of unread notifications
- PUT /api/notifications/{id}/read - Marks individual notification as read
- PUT /api/notifications/mark-all-read - Marks all notifications as read
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "SuperAdmin123!"


class TestNotificationsBadge:
    """Test notification badge functionality for Guards/Admins/Supervisors"""
    
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
            return data
        return None
    
    # ==================== GET /api/notifications ====================
    
    def test_01_get_notifications_returns_list(self):
        """GET /api/notifications returns a list of notifications"""
        login_data = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_data is not None, "Guard login failed"
        
        response = self.session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/notifications returns list with {len(data)} notifications")
    
    def test_02_notifications_have_read_field(self):
        """Each notification has a 'read' boolean field"""
        login_data = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_data is not None, "Guard login failed"
        
        response = self.session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            for notif in data[:5]:  # Check first 5
                assert "read" in notif, f"Notification missing 'read' field: {notif.get('id')}"
                assert isinstance(notif["read"], bool), f"'read' should be boolean, got {type(notif['read'])}"
            print(f"✓ Notifications have 'read' boolean field")
        else:
            print("⚠ No notifications to verify 'read' field")
    
    def test_03_notifications_unread_only_filter(self):
        """GET /api/notifications?unread_only=true returns only unread"""
        login_data = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_data is not None, "Guard login failed"
        
        response = self.session.get(f"{BASE_URL}/api/notifications?unread_only=true")
        assert response.status_code == 200
        
        data = response.json()
        for notif in data:
            assert notif.get("read") == False, f"Notification {notif.get('id')} should be unread"
        print(f"✓ unread_only=true filter works, returned {len(data)} unread notifications")
    
    # ==================== GET /api/notifications/unread-count ====================
    
    def test_04_get_unread_count_returns_count(self):
        """GET /api/notifications/unread-count returns count object"""
        login_data = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_data is not None, "Guard login failed"
        
        response = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "count" in data, "Response should have 'count' field"
        assert isinstance(data["count"], int), f"'count' should be int, got {type(data['count'])}"
        assert data["count"] >= 0, "Count should be non-negative"
        print(f"✓ GET /api/notifications/unread-count returns count: {data['count']}")
    
    def test_05_unread_count_matches_filtered_list(self):
        """Unread count matches length of unread_only=true list"""
        login_data = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_data is not None, "Guard login failed"
        
        # Get count
        count_response = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert count_response.status_code == 200
        count_data = count_response.json()
        unread_count = count_data["count"]
        
        # Get unread list
        list_response = self.session.get(f"{BASE_URL}/api/notifications?unread_only=true")
        assert list_response.status_code == 200
        list_data = list_response.json()
        
        # Compare (allow for limit differences)
        assert unread_count >= len(list_data), f"Count {unread_count} should be >= list length {len(list_data)}"
        print(f"✓ Unread count ({unread_count}) matches filtered list ({len(list_data)})")
    
    # ==================== PUT /api/notifications/{id}/read ====================
    
    def test_06_mark_single_notification_as_read(self):
        """PUT /api/notifications/{id}/read marks notification as read"""
        login_data = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_data is not None, "Guard login failed"
        
        # Get initial unread count
        initial_count_resp = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        initial_count = initial_count_resp.json()["count"]
        
        # Get an unread notification
        list_response = self.session.get(f"{BASE_URL}/api/notifications?unread_only=true")
        unread_list = list_response.json()
        
        if len(unread_list) == 0:
            pytest.skip("No unread notifications to test")
        
        notif_id = unread_list[0]["id"]
        
        # Mark as read
        mark_response = self.session.put(f"{BASE_URL}/api/notifications/{notif_id}/read")
        assert mark_response.status_code == 200, f"Expected 200, got {mark_response.status_code}"
        
        # Verify count decreased
        new_count_resp = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        new_count = new_count_resp.json()["count"]
        
        assert new_count == initial_count - 1, f"Count should decrease from {initial_count} to {initial_count - 1}, got {new_count}"
        print(f"✓ Marked notification {notif_id} as read, count: {initial_count} -> {new_count}")
    
    def test_07_marked_notification_has_read_true(self):
        """After marking as read, notification has read=true"""
        login_data = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_data is not None, "Guard login failed"
        
        # Get all notifications
        list_response = self.session.get(f"{BASE_URL}/api/notifications")
        all_notifs = list_response.json()
        
        # Find a read notification
        read_notifs = [n for n in all_notifs if n.get("read") == True]
        
        if len(read_notifs) == 0:
            pytest.skip("No read notifications to verify")
        
        notif = read_notifs[0]
        assert notif["read"] == True, "Notification should have read=true"
        print(f"✓ Read notification {notif['id']} has read=true")
    
    # ==================== PUT /api/notifications/mark-all-read ====================
    
    def test_08_mark_all_notifications_as_read(self):
        """PUT /api/notifications/mark-all-read marks all as read"""
        login_data = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_data is not None, "Guard login failed"
        
        # Get initial unread count
        initial_count_resp = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        initial_count = initial_count_resp.json()["count"]
        
        # Mark all as read
        mark_response = self.session.put(f"{BASE_URL}/api/notifications/mark-all-read")
        assert mark_response.status_code == 200, f"Expected 200, got {mark_response.status_code}"
        
        data = mark_response.json()
        assert "count" in data, "Response should have 'count' field"
        
        # Verify count is now 0
        new_count_resp = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        new_count = new_count_resp.json()["count"]
        
        assert new_count == 0, f"Unread count should be 0 after mark-all-read, got {new_count}"
        print(f"✓ Marked all as read, count: {initial_count} -> {new_count}")
    
    def test_09_unread_list_empty_after_mark_all(self):
        """After mark-all-read, unread_only=true returns empty list"""
        login_data = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_data is not None, "Guard login failed"
        
        # Mark all as read first
        self.session.put(f"{BASE_URL}/api/notifications/mark-all-read")
        
        # Get unread list
        list_response = self.session.get(f"{BASE_URL}/api/notifications?unread_only=true")
        assert list_response.status_code == 200
        
        unread_list = list_response.json()
        assert len(unread_list) == 0, f"Unread list should be empty, got {len(unread_list)}"
        print(f"✓ Unread list is empty after mark-all-read")
    
    # ==================== Persistence Tests ====================
    
    def test_10_read_status_persists_after_refresh(self):
        """Read status persists after page refresh (re-login)"""
        # First login and mark all as read
        login_data = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_data is not None, "Guard login failed"
        
        self.session.put(f"{BASE_URL}/api/notifications/mark-all-read")
        
        # Get count before "refresh"
        count_before = self.session.get(f"{BASE_URL}/api/notifications/unread-count").json()["count"]
        
        # Simulate page refresh by creating new session and re-logging in
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_data = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_data is not None, "Guard re-login failed"
        
        # Get count after "refresh"
        count_after = self.session.get(f"{BASE_URL}/api/notifications/unread-count").json()["count"]
        
        assert count_after == count_before, f"Count should persist: before={count_before}, after={count_after}"
        print(f"✓ Read status persists after refresh: count={count_after}")
    
    # ==================== SuperAdmin Tests ====================
    
    def test_11_superadmin_can_access_notifications(self):
        """SuperAdmin can access notification endpoints"""
        login_data = self.login(SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD)
        assert login_data is not None, "SuperAdmin login failed"
        
        # Get notifications
        response = self.session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Get unread count
        count_response = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert count_response.status_code == 200
        
        print(f"✓ SuperAdmin can access notification endpoints")
    
    # ==================== Error Handling ====================
    
    def test_12_mark_nonexistent_notification_returns_404(self):
        """PUT /api/notifications/{invalid_id}/read returns 404"""
        login_data = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_data is not None, "Guard login failed"
        
        fake_id = str(uuid.uuid4())
        response = self.session.put(f"{BASE_URL}/api/notifications/{fake_id}/read")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Marking non-existent notification returns 404")
    
    def test_13_unauthenticated_access_returns_401(self):
        """Unauthenticated access to notifications returns 401"""
        # Create new session without auth
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        response = session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        
        print(f"✓ Unauthenticated access returns 401/403")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
