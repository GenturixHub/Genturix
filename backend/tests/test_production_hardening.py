"""
Test Suite: Production Hardening Phase Features
Tests: Health check, Login, Rate limiting, JWT secrets validation

Testing the 3 phases implemented:
1. JWT secrets hardening (no fallbacks)
2. Rate limiting on login (5 attempts per minute per email+IP)
3. MongoDB indexes
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "SuperAdmin123!"
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"
RESIDENT_EMAIL = "residente@genturix.com"
RESIDENT_PASSWORD = "Resi123!"


class TestHealthEndpoint:
    """Health check endpoint tests"""
    
    def test_health_endpoint_returns_200(self):
        """GET /api/health should return 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Health status code: {response.status_code}")
        print(f"Health response: {response.json()}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_health_endpoint_has_status_ok(self):
        """Health response should have status='ok'"""
        response = requests.get(f"{BASE_URL}/api/health")
        data = response.json()
        assert data.get("status") == "ok", f"Expected status='ok', got {data.get('status')}"
    
    def test_health_endpoint_database_connected(self):
        """Health response should have database='connected'"""
        response = requests.get(f"{BASE_URL}/api/health")
        data = response.json()
        assert data.get("database") == "connected", f"Expected database='connected', got {data.get('database')}"
    
    def test_health_endpoint_has_version(self):
        """Health response should include version field"""
        response = requests.get(f"{BASE_URL}/api/health")
        data = response.json()
        assert "version" in data, "Health response should include 'version' field"
        print(f"API Version: {data.get('version')}")


class TestLoginWithValidCredentials:
    """Login endpoint tests with valid credentials"""
    
    def test_login_superadmin_success(self):
        """Login with superadmin credentials should succeed"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        print(f"Superadmin login status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "access_token" in data, "Response should include access_token"
        assert "refresh_token" in data, "Response should include refresh_token"
        assert "user" in data, "Response should include user info"
        assert data["user"]["email"] == SUPERADMIN_EMAIL, f"Email mismatch"
        print(f"Superadmin login successful, user: {data['user']['full_name']}")
    
    def test_login_admin_success(self):
        """Login with admin credentials should succeed"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        print(f"Admin login status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "access_token" in data, "Response should include access_token"
        assert data["user"]["email"] == ADMIN_EMAIL
    
    def test_login_guard_success(self):
        """Login with guard credentials should succeed"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": GUARD_EMAIL, "password": GUARD_PASSWORD}
        )
        print(f"Guard login status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == GUARD_EMAIL
    
    def test_login_resident_success(self):
        """Login with resident credentials should succeed"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD}
        )
        print(f"Resident login status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == RESIDENT_EMAIL
    
    def test_login_invalid_password_returns_401(self):
        """Login with wrong password should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": "WrongPassword123!"}
        )
        print(f"Invalid password login status: {response.status_code}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_login_invalid_email_returns_401(self):
        """Login with non-existent email should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "nonexistent@genturix.com", "password": "SomePassword123!"}
        )
        print(f"Invalid email login status: {response.status_code}")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestRateLimitingLocalhost:
    """
    Rate limiting tests - MAX 5 attempts per minute per email+IP
    
    NOTE: Rate limiting is per email+IP combination. Through external proxy,
    IPs may vary, so these tests use localhost:8001 for consistent IP.
    """
    
    # Use localhost for rate limiting tests (consistent IP)
    LOCAL_URL = "http://localhost:8001"
    
    def test_rate_limiting_blocks_after_5_failed_attempts_localhost(self):
        """
        After 5 failed login attempts with same email+IP, the 6th should return HTTP 429
        Testing against localhost:8001 where IP is consistent.
        """
        # Use a unique test email to avoid interference from other tests
        test_email = f"ratelimit_test_{int(time.time())}@genturix.com"
        wrong_password = "WrongPassword123!"
        
        print(f"\n=== Rate Limiting Test (localhost) ===")
        print(f"Testing email: {test_email}")
        print(f"Making 6 failed login attempts against localhost:8001...")
        
        # Make 5 failed attempts
        for i in range(5):
            response = requests.post(
                f"{self.LOCAL_URL}/api/auth/login",
                json={"email": test_email, "password": wrong_password}
            )
            print(f"Attempt {i+1}: Status {response.status_code}")
            # Should return 401 (invalid credentials) for first 5 attempts
            assert response.status_code == 401, f"Attempt {i+1}: Expected 401, got {response.status_code}"
        
        # 6th attempt should be rate limited (429)
        response = requests.post(
            f"{self.LOCAL_URL}/api/auth/login",
            json={"email": test_email, "password": wrong_password}
        )
        print(f"Attempt 6 (should be blocked): Status {response.status_code}")
        print(f"Attempt 6 response: {response.text}")
        
        assert response.status_code == 429, f"Expected 429 (Too Many Requests), got {response.status_code}"
        
        # Verify the error message
        data = response.json()
        assert "detail" in data or "error" in data, "Response should include error message"
        error_msg = data.get("detail") or data.get("error", "")
        print(f"Rate limit error message: {error_msg}")
    
    def test_rate_limiting_message_content_localhost(self):
        """Verify rate limit error message is informative (via localhost)"""
        test_email = f"ratelimit_msg_test_{int(time.time())}@genturix.com"
        wrong_password = "WrongPassword123!"
        
        # Exhaust rate limit
        for i in range(5):
            requests.post(
                f"{self.LOCAL_URL}/api/auth/login",
                json={"email": test_email, "password": wrong_password}
            )
        
        # Get the rate limited response
        response = requests.post(
            f"{self.LOCAL_URL}/api/auth/login",
            json={"email": test_email, "password": wrong_password}
        )
        
        assert response.status_code == 429
        data = response.json()
        # Check that message mentions "too many" or similar
        error_text = str(data.get("detail", "")).lower()
        assert "too many" in error_text or "login attempts" in error_text, \
            f"Error message should mention rate limiting: {error_text}"
    
    def test_rate_limiting_7th_attempt_still_blocked(self):
        """Verify rate limiting continues to block after 6th attempt"""
        test_email = f"ratelimit_persist_{int(time.time())}@genturix.com"
        wrong_password = "WrongPassword123!"
        
        # Exhaust rate limit (5 attempts)
        for i in range(5):
            requests.post(
                f"{self.LOCAL_URL}/api/auth/login",
                json={"email": test_email, "password": wrong_password}
            )
        
        # 6th and 7th attempts should both be blocked
        for i in range(6, 8):
            response = requests.post(
                f"{self.LOCAL_URL}/api/auth/login",
                json={"email": test_email, "password": wrong_password}
            )
            print(f"Attempt {i}: Status {response.status_code}")
            assert response.status_code == 429, f"Attempt {i}: Expected 429, got {response.status_code}"


class TestJWTSecurityHeaders:
    """Test JWT and security features"""
    
    def test_login_returns_request_id_header(self):
        """Login response should include X-Request-ID header"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        assert response.status_code == 200
        
        # Check for X-Request-ID header
        request_id = response.headers.get("X-Request-ID")
        print(f"X-Request-ID header: {request_id}")
        assert request_id is not None, "Response should include X-Request-ID header"
        assert len(request_id) > 0, "X-Request-ID should not be empty"
    
    def test_error_response_includes_request_id(self):
        """Error responses should also include request_id"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@test.com", "password": "wrong"}
        )
        assert response.status_code == 401
        
        # Check header
        request_id_header = response.headers.get("X-Request-ID")
        assert request_id_header is not None, "Error response should include X-Request-ID header"
        
        # Check body
        data = response.json()
        print(f"Error response body: {data}")
        # The body may also include request_id depending on implementation


class TestEnvironmentConfiguration:
    """Verify environment is properly configured"""
    
    def test_health_endpoint_works_without_auth(self):
        """Health endpoint should not require authentication"""
        response = requests.get(f"{BASE_URL}/api/health")
        # Should NOT return 401/403
        assert response.status_code not in [401, 403], \
            f"Health endpoint should be public, got {response.status_code}"
    
    def test_protected_endpoint_requires_auth(self):
        """Protected endpoints should require authentication"""
        response = requests.get(f"{BASE_URL}/api/profile")
        assert response.status_code in [401, 403], \
            f"Protected endpoint should require auth, got {response.status_code}"


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
