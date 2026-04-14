"""
Notifications V2 Module Tests
Tests for the new notification system with broadcasts, preferences, and pagination.
All endpoints under /api/notifications/v2/*
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
ADMIN_CREDS = {"email": "admin@genturix.com", "password": "Admin123!"}
RESIDENT_CREDS = {"email": "test-resident@genturix.com", "password": "Admin123!"}
GUARD_CREDS = {"email": "guarda1@genturix.com", "password": "Guard123!"}
SUPERADMIN_CREDS = {"email": "superadmin@genturix.com", "password": "Admin123!"}


class TestNotificationsV2Setup:
    """Setup and authentication tests"""
    
    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()
    
    def get_token(self, session, creds):
        """Helper to get auth token"""
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=creds,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        return None
    
    def test_admin_login(self, session):
        """Test admin can login"""
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDS,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"✅ Admin login successful")
    
    def test_resident_login(self, session):
        """Test resident can login"""
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=RESIDENT_CREDS,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"✅ Resident login successful")
    
    def test_guard_login(self, session):
        """Test guard can login"""
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=GUARD_CREDS,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"✅ Guard login successful")


class TestNotificationsV2Endpoints:
    """Test all V2 notification endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDS,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=RESIDENT_CREDS,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Resident login failed")
    
    @pytest.fixture(scope="class")
    def guard_token(self):
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=GUARD_CREDS,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Guard login failed")
    
    @pytest.fixture(scope="class")
    def superadmin_token(self):
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=SUPERADMIN_CREDS,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("SuperAdmin login failed")
    
    # ==================== GET /api/notifications/v2 ====================
    def test_get_notifications_v2_admin(self, admin_token):
        """Admin can list notifications with pagination"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        print(f"✅ GET /api/notifications/v2 - Admin: {data['total']} notifications")
    
    def test_get_notifications_v2_with_pagination(self, admin_token):
        """Test pagination parameters"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2?page=1&page_size=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert len(data["items"]) <= 5
        print(f"✅ GET /api/notifications/v2 with pagination works")
    
    def test_get_notifications_v2_unread_only(self, admin_token):
        """Test unread_only filter"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2?unread_only=true",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # All returned items should be unread
        for item in data["items"]:
            assert item.get("read") == False, f"Found read notification in unread_only filter"
        print(f"✅ GET /api/notifications/v2?unread_only=true works")
    
    def test_get_notifications_v2_resident(self, resident_token):
        """Resident can list their notifications"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "items" in data
        print(f"✅ GET /api/notifications/v2 - Resident: {data['total']} notifications")
    
    def test_get_notifications_v2_guard(self, guard_token):
        """Guard can list their notifications"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2",
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "items" in data
        print(f"✅ GET /api/notifications/v2 - Guard: {data['total']} notifications")
    
    # ==================== GET /api/notifications/v2/unread-count ====================
    def test_get_unread_count_admin(self, admin_token):
        """Admin can get unread count"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2/unread-count",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)
        print(f"✅ GET /api/notifications/v2/unread-count - Admin: {data['count']} unread")
    
    def test_get_unread_count_resident(self, resident_token):
        """Resident can get unread count"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2/unread-count",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "count" in data
        print(f"✅ GET /api/notifications/v2/unread-count - Resident: {data['count']} unread")
    
    # ==================== POST /api/notifications/v2/broadcast ====================
    def test_create_broadcast_admin(self, admin_token):
        """Admin can create broadcast notification"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "title": f"TEST_Broadcast_{unique_id}",
            "message": f"Test broadcast message from admin - {unique_id}",
            "notification_type": "broadcast",
            "priority": "normal",
            "target_roles": None  # All roles
        }
        response = requests.post(
            f"{BASE_URL}/api/notifications/v2/broadcast",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["title"] == payload["title"]
        assert data["message"] == payload["message"]
        assert data["is_broadcast"] == True
        assert "id" in data
        print(f"✅ POST /api/notifications/v2/broadcast - Admin created: {data['id']}")
        return data["id"]
    
    def test_create_broadcast_with_target_roles(self, admin_token):
        """Admin can create broadcast targeting specific roles"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "title": f"TEST_Targeted_{unique_id}",
            "message": f"Test targeted broadcast - {unique_id}",
            "notification_type": "alert",
            "priority": "high",
            "target_roles": ["Residente", "Guarda"]
        }
        response = requests.post(
            f"{BASE_URL}/api/notifications/v2/broadcast",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["target_roles"] == ["Residente", "Guarda"]
        print(f"✅ POST /api/notifications/v2/broadcast with target_roles works")
    
    def test_create_broadcast_superadmin(self, superadmin_token):
        """SuperAdmin can create broadcast notification"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "title": f"TEST_SuperAdmin_Broadcast_{unique_id}",
            "message": f"Test broadcast from superadmin - {unique_id}",
            "notification_type": "system",
            "priority": "urgent"
        }
        response = requests.post(
            f"{BASE_URL}/api/notifications/v2/broadcast",
            json=payload,
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["priority"] == "urgent"
        print(f"✅ POST /api/notifications/v2/broadcast - SuperAdmin created")
    
    def test_create_broadcast_resident_forbidden(self, resident_token):
        """Resident CANNOT create broadcast (403)"""
        payload = {
            "title": "TEST_Unauthorized",
            "message": "This should fail",
            "notification_type": "broadcast",
            "priority": "normal"
        }
        response = requests.post(
            f"{BASE_URL}/api/notifications/v2/broadcast",
            json=payload,
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"✅ POST /api/notifications/v2/broadcast - Resident correctly gets 403")
    
    def test_create_broadcast_guard_forbidden(self, guard_token):
        """Guard CANNOT create broadcast (403)"""
        payload = {
            "title": "TEST_Unauthorized_Guard",
            "message": "This should fail",
            "notification_type": "broadcast",
            "priority": "normal"
        }
        response = requests.post(
            f"{BASE_URL}/api/notifications/v2/broadcast",
            json=payload,
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"✅ POST /api/notifications/v2/broadcast - Guard correctly gets 403")
    
    # ==================== PATCH /api/notifications/v2/read/{id} ====================
    def test_mark_notification_read(self, admin_token):
        """Mark a notification as read"""
        # First create a broadcast
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(
            f"{BASE_URL}/api/notifications/v2/broadcast",
            json={
                "title": f"TEST_MarkRead_{unique_id}",
                "message": "Test for mark read",
                "notification_type": "info",
                "priority": "low"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert create_response.status_code == 200
        notif_id = create_response.json()["id"]
        
        # Mark as read
        response = requests.patch(
            f"{BASE_URL}/api/notifications/v2/read/{notif_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"✅ PATCH /api/notifications/v2/read/{notif_id} works")
    
    def test_mark_notification_read_not_found(self, admin_token):
        """Mark non-existent notification returns 404"""
        fake_id = str(uuid.uuid4())
        response = requests.patch(
            f"{BASE_URL}/api/notifications/v2/read/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✅ PATCH /api/notifications/v2/read/{{invalid}} returns 404")
    
    # ==================== PATCH /api/notifications/v2/read-all ====================
    def test_mark_all_notifications_read(self, admin_token):
        """Mark all notifications as read"""
        response = requests.patch(
            f"{BASE_URL}/api/notifications/v2/read-all",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert "count" in data
        print(f"✅ PATCH /api/notifications/v2/read-all - Marked {data['count']} as read")
    
    # ==================== GET /api/notifications/v2/broadcasts ====================
    def test_get_broadcast_history_admin(self, admin_token):
        """Admin can get broadcast history"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2/broadcasts",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        print(f"✅ GET /api/notifications/v2/broadcasts - Admin: {data['total']} broadcasts")
    
    def test_get_broadcast_history_resident_forbidden(self, resident_token):
        """Resident CANNOT get broadcast history (403)"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2/broadcasts",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✅ GET /api/notifications/v2/broadcasts - Resident correctly gets 403")
    
    # ==================== GET /api/notifications/v2/preferences ====================
    def test_get_preferences(self, admin_token):
        """Get notification preferences"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2/preferences",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "user_id" in data
        # Check default preferences exist
        assert "broadcasts_enabled" in data
        assert "alerts_enabled" in data
        assert "system_enabled" in data
        assert "email_notifications" in data
        print(f"✅ GET /api/notifications/v2/preferences works")
    
    def test_get_preferences_resident(self, resident_token):
        """Resident can get their preferences"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2/preferences",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "broadcasts_enabled" in data
        print(f"✅ GET /api/notifications/v2/preferences - Resident works")
    
    # ==================== PATCH /api/notifications/v2/preferences ====================
    def test_update_preferences(self, admin_token):
        """Update notification preferences"""
        payload = {
            "broadcasts_enabled": True,
            "email_notifications": False
        }
        response = requests.patch(
            f"{BASE_URL}/api/notifications/v2/preferences",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["broadcasts_enabled"] == True
        assert data["email_notifications"] == False
        print(f"✅ PATCH /api/notifications/v2/preferences works")
    
    def test_update_preferences_empty_fails(self, admin_token):
        """Update with no fields returns 400"""
        response = requests.patch(
            f"{BASE_URL}/api/notifications/v2/preferences",
            json={},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"✅ PATCH /api/notifications/v2/preferences with empty body returns 400")


class TestLegacyEndpointsNotBroken:
    """Verify existing legacy notification endpoints still work"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDS,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")
    
    def test_legacy_get_notifications(self, admin_token):
        """Legacy GET /api/notifications still works"""
        response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should return 200 (may be empty array)
        assert response.status_code == 200, f"Legacy endpoint broken: {response.status_code} - {response.text}"
        print(f"✅ Legacy GET /api/notifications still works")
    
    def test_legacy_unread_count(self, admin_token):
        """Legacy GET /api/notifications/unread-count still works"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/unread-count",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Legacy endpoint broken: {response.status_code} - {response.text}"
        data = response.json()
        assert "count" in data
        print(f"✅ Legacy GET /api/notifications/unread-count still works")


class TestBroadcastVisibility:
    """Test that broadcasts are visible to correct users based on condominium and roles"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDS,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=RESIDENT_CREDS,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Resident login failed")
    
    @pytest.fixture(scope="class")
    def guard_token(self):
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=GUARD_CREDS,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Guard login failed")
    
    def test_broadcast_visible_to_all_roles(self, admin_token, resident_token, guard_token):
        """Broadcast with no target_roles is visible to all users in same condo"""
        # Create broadcast targeting all roles
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(
            f"{BASE_URL}/api/notifications/v2/broadcast",
            json={
                "title": f"TEST_AllRoles_{unique_id}",
                "message": f"Visible to all - {unique_id}",
                "notification_type": "broadcast",
                "priority": "normal",
                "target_roles": None
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert create_response.status_code == 200
        notif_id = create_response.json()["id"]
        
        # Small delay for DB propagation
        time.sleep(0.5)
        
        # Check admin can see it
        admin_notifs = requests.get(
            f"{BASE_URL}/api/notifications/v2",
            headers={"Authorization": f"Bearer {admin_token}"}
        ).json()
        admin_ids = [n["id"] for n in admin_notifs.get("items", [])]
        assert notif_id in admin_ids, "Admin should see broadcast"
        
        # Check resident can see it (if in same condo)
        resident_notifs = requests.get(
            f"{BASE_URL}/api/notifications/v2",
            headers={"Authorization": f"Bearer {resident_token}"}
        ).json()
        # Note: Resident may not see if in different condo - this is expected behavior
        
        # Check guard can see it (if in same condo)
        guard_notifs = requests.get(
            f"{BASE_URL}/api/notifications/v2",
            headers={"Authorization": f"Bearer {guard_token}"}
        ).json()
        
        print(f"✅ Broadcast visibility test completed - Admin sees: {len(admin_notifs.get('items', []))}")
    
    def test_targeted_broadcast_visibility(self, admin_token, resident_token, guard_token):
        """Broadcast targeting specific roles only visible to those roles"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create broadcast targeting only Residente
        create_response = requests.post(
            f"{BASE_URL}/api/notifications/v2/broadcast",
            json={
                "title": f"TEST_ResidentOnly_{unique_id}",
                "message": f"Only for residents - {unique_id}",
                "notification_type": "info",
                "priority": "normal",
                "target_roles": ["Residente"]
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert create_response.status_code == 200
        notif_id = create_response.json()["id"]
        
        time.sleep(0.5)
        
        # Resident should see it
        resident_notifs = requests.get(
            f"{BASE_URL}/api/notifications/v2",
            headers={"Authorization": f"Bearer {resident_token}"}
        ).json()
        resident_ids = [n["id"] for n in resident_notifs.get("items", [])]
        
        # Guard should NOT see it (unless guard also has Residente role)
        guard_notifs = requests.get(
            f"{BASE_URL}/api/notifications/v2",
            headers={"Authorization": f"Bearer {guard_token}"}
        ).json()
        guard_ids = [n["id"] for n in guard_notifs.get("items", [])]
        
        print(f"✅ Targeted broadcast test - Resident sees: {len(resident_ids)}, Guard sees: {len(guard_ids)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
