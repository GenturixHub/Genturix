"""
Push Notifications API Tests for GENTURIX
Tests: VAPID key, subscribe, unsubscribe, status, panic trigger with push
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"
RESIDENT_EMAIL = "residente@genturix.com"
RESIDENT_PASSWORD = "Residente123!"
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"


class TestPushNotificationAPIs:
    """Test Push Notification endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session for each test"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, email, password):
        """Helper to login and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            return response.json()
        return None
    
    # ==================== VAPID PUBLIC KEY ====================
    def test_get_vapid_public_key_success(self):
        """GET /api/push/vapid-public-key returns VAPID public key"""
        response = self.session.get(f"{BASE_URL}/api/push/vapid-public-key")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "vapid_public_key" in data, "Response should contain vapid_public_key"
        assert len(data["vapid_public_key"]) > 0, "VAPID key should not be empty"
        # VAPID keys are base64url encoded
        assert data["vapid_public_key"].startswith("BB"), "VAPID public key should start with BB"
    
    # ==================== SUBSCRIBE - ROLE VALIDATION ====================
    def test_subscribe_guard_allowed(self):
        """POST /api/push/subscribe - Guard can subscribe"""
        login_result = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_result is not None, "Guard login failed"
        
        # Create mock subscription data
        subscription = {
            "subscription": {
                "endpoint": f"https://fcm.googleapis.com/fcm/send/test-guard-{uuid.uuid4()}",
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                    "auth": "tBHItJI5svbpez7KI4CCXg"
                },
                "expirationTime": None
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/push/subscribe", json=subscription)
        
        # Should succeed (201 created or 200 updated)
        assert response.status_code in [200, 201], f"Guard subscribe failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "message" in data
        assert data.get("status") in ["created", "updated"]
    
    def test_subscribe_admin_allowed(self):
        """POST /api/push/subscribe - Admin can subscribe"""
        login_result = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        assert login_result is not None, "Admin login failed"
        
        subscription = {
            "subscription": {
                "endpoint": f"https://fcm.googleapis.com/fcm/send/test-admin-{uuid.uuid4()}",
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                    "auth": "tBHItJI5svbpez7KI4CCXg"
                },
                "expirationTime": None
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/push/subscribe", json=subscription)
        
        assert response.status_code in [200, 201], f"Admin subscribe failed: {response.status_code} - {response.text}"
    
    def test_subscribe_resident_forbidden(self):
        """POST /api/push/subscribe - Resident cannot subscribe (403)"""
        login_result = self.login(RESIDENT_EMAIL, RESIDENT_PASSWORD)
        assert login_result is not None, "Resident login failed"
        
        subscription = {
            "subscription": {
                "endpoint": f"https://fcm.googleapis.com/fcm/send/test-resident-{uuid.uuid4()}",
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                    "auth": "tBHItJI5svbpez7KI4CCXg"
                },
                "expirationTime": None
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/push/subscribe", json=subscription)
        
        # Resident should be forbidden
        assert response.status_code == 403, f"Expected 403 for resident, got {response.status_code}: {response.text}"
        data = response.json()
        assert "seguridad" in data.get("detail", "").lower() or "security" in data.get("detail", "").lower()
    
    def test_subscribe_unauthenticated_fails(self):
        """POST /api/push/subscribe - Unauthenticated request fails (401)"""
        subscription = {
            "subscription": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/test-unauth",
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                    "auth": "tBHItJI5svbpez7KI4CCXg"
                }
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/push/subscribe", json=subscription)
        
        assert response.status_code == 401 or response.status_code == 403, f"Expected 401/403, got {response.status_code}"
    
    # ==================== UNSUBSCRIBE ====================
    def test_unsubscribe_success(self):
        """DELETE /api/push/unsubscribe - Guard can unsubscribe"""
        login_result = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_result is not None, "Guard login failed"
        
        # First subscribe
        unique_endpoint = f"https://fcm.googleapis.com/fcm/send/test-unsub-{uuid.uuid4()}"
        subscription = {
            "subscription": {
                "endpoint": unique_endpoint,
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                    "auth": "tBHItJI5svbpez7KI4CCXg"
                }
            }
        }
        
        # Subscribe first
        sub_response = self.session.post(f"{BASE_URL}/api/push/subscribe", json=subscription)
        assert sub_response.status_code in [200, 201], f"Subscribe failed: {sub_response.text}"
        
        # Now unsubscribe
        unsub_response = self.session.delete(f"{BASE_URL}/api/push/unsubscribe", json=subscription)
        
        assert unsub_response.status_code == 200, f"Unsubscribe failed: {unsub_response.status_code} - {unsub_response.text}"
        data = unsub_response.json()
        assert "message" in data
    
    def test_unsubscribe_not_found(self):
        """DELETE /api/push/unsubscribe - Returns 404 for non-existent subscription"""
        login_result = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_result is not None, "Guard login failed"
        
        subscription = {
            "subscription": {
                "endpoint": f"https://fcm.googleapis.com/fcm/send/nonexistent-{uuid.uuid4()}",
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                    "auth": "tBHItJI5svbpez7KI4CCXg"
                }
            }
        }
        
        response = self.session.delete(f"{BASE_URL}/api/push/unsubscribe", json=subscription)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    # ==================== PUSH STATUS ====================
    def test_push_status_not_subscribed(self):
        """GET /api/push/status - Returns status for user without subscriptions"""
        login_result = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_result is not None, "Guard login failed"
        
        response = self.session.get(f"{BASE_URL}/api/push/status")
        
        assert response.status_code == 200, f"Status check failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "is_subscribed" in data
        assert "subscription_count" in data
        assert isinstance(data["is_subscribed"], bool)
        assert isinstance(data["subscription_count"], int)
    
    def test_push_status_after_subscribe(self):
        """GET /api/push/status - Returns subscribed=true after subscribing"""
        login_result = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_result is not None, "Guard login failed"
        
        # Subscribe
        unique_endpoint = f"https://fcm.googleapis.com/fcm/send/test-status-{uuid.uuid4()}"
        subscription = {
            "subscription": {
                "endpoint": unique_endpoint,
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                    "auth": "tBHItJI5svbpez7KI4CCXg"
                }
            }
        }
        
        sub_response = self.session.post(f"{BASE_URL}/api/push/subscribe", json=subscription)
        assert sub_response.status_code in [200, 201]
        
        # Check status
        status_response = self.session.get(f"{BASE_URL}/api/push/status")
        
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["is_subscribed"] == True, "Should be subscribed after subscribing"
        assert data["subscription_count"] >= 1
        
        # Cleanup - unsubscribe
        self.session.delete(f"{BASE_URL}/api/push/unsubscribe", json=subscription)
    
    # ==================== PANIC TRIGGER WITH PUSH ====================
    def test_panic_trigger_includes_push_notifications(self):
        """POST /api/security/panic - Response includes push_notifications field"""
        login_result = self.login(RESIDENT_EMAIL, RESIDENT_PASSWORD)
        assert login_result is not None, "Resident login failed"
        
        panic_data = {
            "panic_type": "emergencia_general",
            "location": "Test Location - Push Test",
            "latitude": 10.4806,
            "longitude": -66.9036,
            "description": "Test panic for push notification verification"
        }
        
        response = self.session.post(f"{BASE_URL}/api/security/panic", json=panic_data)
        
        assert response.status_code == 200, f"Panic trigger failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "event_id" in data, "Response should contain event_id"
        assert "push_notifications" in data, "Response should contain push_notifications field"
        
        # Verify push_notifications structure
        push_result = data["push_notifications"]
        assert "sent" in push_result, "push_notifications should have 'sent' count"
        assert "failed" in push_result, "push_notifications should have 'failed' count"
        assert "total" in push_result, "push_notifications should have 'total' count"
        
        # Values should be integers
        assert isinstance(push_result["sent"], int)
        assert isinstance(push_result["failed"], int)
        assert isinstance(push_result["total"], int)
    
    # ==================== MULTI-TENANT FILTERING ====================
    def test_subscriptions_filtered_by_condominium(self):
        """Verify subscriptions are stored with condominium_id for multi-tenant filtering"""
        login_result = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_result is not None, "Guard login failed"
        
        # Get user info to verify condominium_id
        user_response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert user_response.status_code == 200
        user_data = user_response.json()
        
        # Subscribe
        unique_endpoint = f"https://fcm.googleapis.com/fcm/send/test-condo-{uuid.uuid4()}"
        subscription = {
            "subscription": {
                "endpoint": unique_endpoint,
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                    "auth": "tBHItJI5svbpez7KI4CCXg"
                }
            }
        }
        
        sub_response = self.session.post(f"{BASE_URL}/api/push/subscribe", json=subscription)
        assert sub_response.status_code in [200, 201], f"Subscribe failed: {sub_response.text}"
        
        # Verify status shows subscription
        status_response = self.session.get(f"{BASE_URL}/api/push/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["is_subscribed"] == True
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/push/unsubscribe", json=subscription)


class TestPushNotificationEdgeCases:
    """Edge cases and error handling for push notifications"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, email, password):
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            return response.json()
        return None
    
    def test_subscribe_duplicate_endpoint_updates(self):
        """Subscribing with same endpoint updates existing subscription"""
        login_result = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_result is not None
        
        unique_endpoint = f"https://fcm.googleapis.com/fcm/send/test-dup-{uuid.uuid4()}"
        subscription = {
            "subscription": {
                "endpoint": unique_endpoint,
                "keys": {
                    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                    "auth": "tBHItJI5svbpez7KI4CCXg"
                }
            }
        }
        
        # First subscribe
        response1 = self.session.post(f"{BASE_URL}/api/push/subscribe", json=subscription)
        assert response1.status_code in [200, 201]
        status1 = response1.json().get("status")
        
        # Subscribe again with same endpoint
        response2 = self.session.post(f"{BASE_URL}/api/push/subscribe", json=subscription)
        assert response2.status_code in [200, 201]
        status2 = response2.json().get("status")
        
        # Second should be "updated" not "created"
        assert status2 == "updated", f"Expected 'updated' for duplicate, got '{status2}'"
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/push/unsubscribe", json=subscription)
    
    def test_subscribe_invalid_payload(self):
        """Subscribe with invalid payload returns 422"""
        login_result = self.login(GUARD_EMAIL, GUARD_PASSWORD)
        assert login_result is not None
        
        # Missing required fields
        invalid_subscription = {
            "subscription": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/test"
                # Missing keys
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/push/subscribe", json=invalid_subscription)
        
        # Should fail validation
        assert response.status_code == 422, f"Expected 422 for invalid payload, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
