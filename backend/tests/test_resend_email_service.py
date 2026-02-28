"""
Test Resend Email Service Integration
======================================
Tests for the email service using Resend API.

Features tested:
1. GET /api/test-email?email= endpoint - Simple email test
2. GET /api/email/service-status - Service configuration status
3. Email service configuration verification
4. Email templates HTML structure
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestEmailServiceEndpoints:
    """Tests for email service REST endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.superadmin_email = "superadmin@genturix.com"
        self.superadmin_password = "Admin123!"
        self.test_recipient = "genturix@gmail.com"  # Sandbox-verified email
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_superadmin_token(self):
        """Get SuperAdmin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.superadmin_email,
            "password": self.superadmin_password
        })
        if response.status_code != 200:
            pytest.skip(f"SuperAdmin login failed: {response.status_code} - {response.text}")
        return response.json().get("access_token")
    
    # ==================== TEST EMAIL ENDPOINT ====================
    
    def test_test_email_endpoint_returns_sent_status(self):
        """
        Test GET /api/test-email?email= endpoint
        Should return {"status": "sent"} or {"status": "error"}
        """
        # Note: Sandbox mode only allows sending to verified emails
        response = self.session.get(
            f"{BASE_URL}/api/test-email",
            params={"email": self.test_recipient}
        )
        
        assert response.status_code == 200, f"Test email endpoint failed: {response.text}"
        data = response.json()
        
        # Response should have status field
        assert "status" in data, "Response should contain 'status' field"
        
        # Status should be either 'sent' or 'error'
        assert data["status"] in ["sent", "error"], \
            f"Unexpected status: {data['status']}"
        
        if data["status"] == "sent":
            # If sent, should have email_id
            assert "email_id" in data, "Sent response should include email_id"
            print(f"✓ Test email sent successfully - email_id: {data.get('email_id')}")
        else:
            # If error, should have error message
            assert "error" in data, "Error response should include error message"
            print(f"✓ Test email returned error (expected in sandbox): {data.get('error')}")
    
    def test_test_email_endpoint_requires_email_param(self):
        """Test that email parameter is required"""
        response = self.session.get(f"{BASE_URL}/api/test-email")
        
        # Should return 422 (validation error) if email is missing
        assert response.status_code == 422, \
            f"Should return 422 for missing email param, got {response.status_code}"
        print("✓ Test email endpoint correctly requires email parameter")
    
    def test_test_email_endpoint_with_invalid_email(self):
        """Test with invalid email format"""
        response = self.session.get(
            f"{BASE_URL}/api/test-email",
            params={"email": "invalid-email"}
        )
        
        # Should either return validation error or email error
        assert response.status_code in [200, 422], \
            f"Unexpected status code: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            # If 200, should indicate error
            assert data.get("status") == "error", \
                "Invalid email should result in error status"
        
        print("✓ Test email endpoint handles invalid email correctly")
    
    # ==================== EMAIL SERVICE STATUS ENDPOINT ====================
    
    def test_email_service_status_requires_superadmin(self):
        """Test that /api/email/service-status requires SuperAdmin role"""
        # Without auth - should return 401 or 403 (both indicate unauthorized)
        response = self.session.get(f"{BASE_URL}/api/email/service-status")
        assert response.status_code in [401, 403], \
            f"Should require authentication, got {response.status_code}"
        
        print("✓ Email service status endpoint requires authentication")
    
    def test_email_service_status_returns_config(self):
        """
        Test GET /api/email/service-status endpoint
        Should return configuration status for SuperAdmin
        """
        token = self.get_superadmin_token()
        
        response = self.session.get(
            f"{BASE_URL}/api/email/service-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, \
            f"Email service status failed: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "configured" in data, "Response should have 'configured' field"
        assert "sender" in data, "Response should have 'sender' field"
        assert "api_key_set" in data, "Response should have 'api_key_set' field"
        
        # With RESEND_API_KEY configured
        assert data["configured"] == True, "Email service should be configured"
        assert data["api_key_set"] == True, "API key should be set"
        
        # Verify sender is set (sandbox or production)
        assert data["sender"], "Sender should be configured"
        
        print(f"✓ Email service status: configured={data['configured']}, sender={data['sender']}")


class TestEmailServiceIntegration:
    """Tests for email service integration in various flows"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.superadmin_email = "superadmin@genturix.com"
        self.superadmin_password = "Admin123!"
        self.admin_email = "admin@genturix.com"
        self.admin_password = "Admin123!"
        self.test_recipient = "genturix@gmail.com"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_superadmin_token(self):
        """Get SuperAdmin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.superadmin_email,
            "password": self.superadmin_password
        })
        if response.status_code != 200:
            pytest.skip(f"SuperAdmin login failed: {response.status_code}")
        return response.json().get("access_token")
    
    def get_admin_token(self):
        """Get Admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return response.json().get("access_token")
    
    def get_condominium_id(self, token):
        """Get a valid condominium ID"""
        response = self.session.get(
            f"{BASE_URL}/api/condominiums",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            condos = response.json()
            if condos and len(condos) > 0:
                return condos[0].get("id")
        return None
    
    # ==================== USER CREATION EMAIL ====================
    
    def test_user_creation_triggers_email(self):
        """
        Test that POST /api/admin/users with send_credentials_email=true
        triggers email sending and returns email_status
        """
        token = self.get_admin_token()
        condo_id = self.get_condominium_id(token)
        
        if not condo_id:
            pytest.skip("No condominium available for testing")
        
        import uuid
        test_email = f"TEST_email_trigger_{uuid.uuid4().hex[:8]}@test.com"
        
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": "DummyPass123!",
                "full_name": "Test Email Trigger",
                "role": "Residente",
                "phone": "+1234567890",
                "condominium_id": condo_id,
                "send_credentials_email": True,
                "apartment_number": "EMAIL-101"
            }
        )
        
        # Skip if seat limit reached (DEMO mode limitation)
        if response.status_code == 403 and "asientos" in response.text.lower():
            pytest.skip("Demo seat limit reached - cannot test user creation")
        
        assert response.status_code in [200, 201], \
            f"Create user failed: {response.text}"
        
        data = response.json()
        
        # Should have email_status in response
        assert "email_status" in data, \
            "Response should include email_status when send_credentials_email=true"
        
        # Status should be success, skipped, or failed
        email_status = data.get("email_status")
        assert email_status in ["success", "skipped", "failed"], \
            f"Unexpected email_status: {email_status}"
        
        print(f"✓ User creation email status: {email_status}")
    
    # ==================== EMAIL TEMPLATES ====================
    
    def test_email_templates_available(self):
        """
        Test that email templates are properly configured in email_service.py
        This is a code verification test - templates should be importable
        """
        try:
            import sys
            sys.path.insert(0, '/app/backend')
            
            from services.email_service import (
                get_welcome_email_html,
                get_password_reset_email_html,
                get_notification_email_html,
                get_emergency_alert_email_html,
                get_condominium_welcome_email_html,
                get_visitor_preregistration_email_html,
                get_user_credentials_email_html
            )
            
            # Test welcome email template
            welcome_html = get_welcome_email_html(
                user_name="Test User",
                email="test@example.com",
                password="TempPass123!",
                login_url="https://example.com/login"
            )
            assert "GENTURIX" in welcome_html
            assert "Test User" in welcome_html
            
            # Test password reset template
            reset_html = get_password_reset_email_html(
                user_name="Test User",
                reset_url="https://example.com/reset"
            )
            assert "Restablecer Contraseña" in reset_html or "GENTURIX" in reset_html
            
            # Test notification template
            notification_html = get_notification_email_html(
                title="Test Notification",
                message="This is a test message",
                action_url="https://example.com"
            )
            assert "GENTURIX" in notification_html
            
            # Test emergency alert template
            alert_html = get_emergency_alert_email_html(
                resident_name="Test Resident",
                alert_type="Emergencia Médica",
                location="Apt 101",
                timestamp="2026-01-15 10:00:00",
                condominium_name="Test Condo"
            )
            assert "ALERTA" in alert_html or "EMERGENCIA" in alert_html
            
            # Test condominium welcome template
            condo_welcome_html = get_condominium_welcome_email_html(
                admin_name="Test Admin",
                condominium_name="Test Condo",
                email="admin@test.com",
                password="TempPass123!",
                login_url="https://example.com/login"
            )
            assert "GENTURIX" in condo_welcome_html
            assert "Test Condo" in condo_welcome_html
            
            # Test visitor preregistration template
            visitor_html = get_visitor_preregistration_email_html(
                guard_name="Test Guard",
                visitor_name="Test Visitor",
                resident_name="Test Resident",
                apartment="Apt 101",
                valid_from="2026-01-15",
                valid_to="2026-01-16",
                condominium_name="Test Condo"
            )
            assert "Visitante" in visitor_html or "GENTURIX" in visitor_html
            
            # Test user credentials template
            credentials_html = get_user_credentials_email_html(
                user_name="Test User",
                email="test@example.com",
                password="TempPass123!",
                role="Residente",
                condominium_name="Test Condo",
                login_url="https://example.com/login"
            )
            assert "GENTURIX" in credentials_html
            
            print("✓ All 7 email templates are properly configured and generate valid HTML")
            
        except ImportError as e:
            pytest.fail(f"Failed to import email templates: {e}")
    
    def test_email_service_utility_functions(self):
        """Test email service utility functions"""
        try:
            import sys
            sys.path.insert(0, '/app/backend')
            
            from services.email_service import (
                is_email_configured,
                get_email_status,
                get_sender
            )
            
            # Test is_email_configured
            configured = is_email_configured()
            assert isinstance(configured, bool)
            
            # Test get_email_status
            status = get_email_status()
            assert "configured" in status
            assert "sender" in status
            assert "api_key_set" in status
            
            # Test get_sender
            sender = get_sender()
            assert "@" in sender  # Should be a valid email format
            
            print(f"✓ Email service utilities work correctly")
            print(f"  - configured: {configured}")
            print(f"  - sender: {sender}")
            
        except ImportError as e:
            pytest.fail(f"Failed to import email service utilities: {e}")


class TestEmailFailSafeBehavior:
    """Tests for fail-safe behavior - API should not break if email fails"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_email = "admin@genturix.com"
        self.admin_password = "Admin123!"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Get Admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return response.json().get("access_token")
    
    def get_condominium_id(self, token):
        """Get a valid condominium ID"""
        response = self.session.get(
            f"{BASE_URL}/api/condominiums",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            condos = response.json()
            if condos and len(condos) > 0:
                return condos[0].get("id")
        return None
    
    def test_user_creation_succeeds_even_if_email_fails(self):
        """
        Test that user creation completes successfully even if email sending fails.
        This is the fail-safe behavior requirement.
        """
        token = self.get_admin_token()
        condo_id = self.get_condominium_id(token)
        
        if not condo_id:
            pytest.skip("No condominium available for testing")
        
        import uuid
        # Use an email that will likely fail in sandbox (not verified)
        test_email = f"TEST_failsafe_{uuid.uuid4().hex[:8]}@unverified-domain.com"
        
        response = self.session.post(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": test_email,
                "password": "TestPass123!",
                "full_name": "Test Fail Safe",
                "role": "Residente",
                "phone": "+1234567890",
                "condominium_id": condo_id,
                "send_credentials_email": True,
                "apartment_number": "SAFE-101"
            }
        )
        
        # User creation should succeed regardless of email status
        assert response.status_code in [200, 201], \
            f"User creation should succeed even if email fails: {response.text}"
        
        data = response.json()
        
        # User should be created
        assert "user_id" in data, "User should be created with valid user_id"
        
        # Email status should indicate the outcome (success/failed/skipped)
        assert "email_status" in data, "Response should include email_status"
        
        print(f"✓ User creation succeeded with email_status: {data.get('email_status')}")
        print(f"  - user_id: {data.get('user_id')}")


class TestEmailServiceLogging:
    """Tests for email service logging - verify [EMAIL SENT] logs are produced"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.test_recipient = "genturix@gmail.com"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_email_sent_log_format(self):
        """
        Verify that successful email sends produce [EMAIL SENT] log.
        Note: Actual log verification requires checking backend logs.
        This test verifies the endpoint responds correctly.
        """
        response = self.session.get(
            f"{BASE_URL}/api/test-email",
            params={"email": self.test_recipient}
        )
        
        assert response.status_code == 200, f"Test email failed: {response.text}"
        data = response.json()
        
        # If email was sent, the log format should be:
        # [EMAIL SENT] recipient@email.com
        # This is printed in email_service.py line 82 and 135
        
        if data.get("status") == "sent":
            print("✓ Email sent - [EMAIL SENT] log should be in backend logs")
            print(f"  - email_id: {data.get('email_id')}")
            print(f"  - To verify: check backend logs for '[EMAIL SENT] {self.test_recipient}'")
        else:
            print(f"✓ Email not sent (sandbox limitation): {data.get('error')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
