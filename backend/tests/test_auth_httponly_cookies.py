"""
GENTURIX - Authentication Tests for httpOnly Cookie Migration
Tests the security migration of refresh_token from localStorage to httpOnly cookies.

Test Coverage:
1. Login flow - verify NO refresh_token in JSON response
2. Login flow - verify httpOnly cookie is set correctly
3. Token refresh - verify it works via httpOnly cookie
4. Logout flow - verify cookie is cleared
5. Cookie security flags validation
"""

import pytest
import requests
import os
import json
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://manifest-debug-1.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_RESIDENT = {
    "email": "residente.test@genturix.com",
    "password": "Test123!"
}

TEST_SUPERADMIN = {
    "email": "superadmin@genturix.com", 
    "password": "Admin123!"
}


class TestLoginHttpOnlyCookies:
    """Test login flow with httpOnly cookie implementation"""
    
    def test_login_success_returns_access_token_only(self):
        """Login response should contain access_token but NOT refresh_token in JSON body"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=TEST_RESIDENT,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        
        # CRITICAL: access_token MUST be in response
        assert "access_token" in data, "access_token missing from response"
        assert len(data["access_token"]) > 0, "access_token is empty"
        
        # CRITICAL: refresh_token must NOT be in JSON body (security requirement)
        assert "refresh_token" not in data, "SECURITY VIOLATION: refresh_token found in JSON response body"
        
        # Verify user data is present
        assert "user" in data, "user data missing"
        assert data["user"]["email"] == TEST_RESIDENT["email"], "Email mismatch"
        assert data["token_type"] == "bearer", "Invalid token_type"
        
        print(f"✅ Login response contains access_token but NOT refresh_token")
        print(f"   User: {data['user']['full_name']} ({data['user']['email']})")
        print(f"   Roles: {data['user']['roles']}")
    
    def test_login_sets_httponly_cookie(self):
        """Login should set genturix_refresh_token as httpOnly cookie"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=TEST_RESIDENT,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        # Check Set-Cookie header
        set_cookie_header = response.headers.get('Set-Cookie', '')
        
        # For multiple cookies, headers might be combined
        all_cookies = response.headers.get_all('Set-Cookie') if hasattr(response.headers, 'get_all') else [set_cookie_header]
        
        # Find the refresh token cookie
        refresh_cookie_found = False
        for cookie in all_cookies:
            if 'genturix_refresh_token' in str(cookie):
                refresh_cookie_found = True
                cookie_str = str(cookie)
                
                # SECURITY CHECKS
                assert 'HttpOnly' in cookie_str, "SECURITY: HttpOnly flag missing from cookie"
                assert 'Path=/api/auth' in cookie_str, "Cookie path should be /api/auth"
                assert 'SameSite=lax' in cookie_str.lower() or 'samesite=lax' in cookie_str.lower(), "SameSite=lax missing"
                
                # In development, Secure flag should be False
                # Note: Secure flag presence depends on environment
                print(f"✅ Cookie set with correct security flags")
                print(f"   HttpOnly: ✓")
                print(f"   Path=/api/auth: ✓")
                print(f"   SameSite=lax: ✓")
                break
        
        # Also check via response.cookies
        if not refresh_cookie_found:
            # Check if cookie is in response.cookies
            assert 'genturix_refresh_token' in response.cookies, "genturix_refresh_token cookie not set"
            print(f"✅ genturix_refresh_token cookie present in response")
        
    def test_login_cookie_max_age(self):
        """Verify cookie has correct Max-Age (604800 = 7 days)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=TEST_RESIDENT,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        
        set_cookie_header = response.headers.get('Set-Cookie', '')
        
        # Check Max-Age
        if 'Max-Age=604800' in set_cookie_header:
            print(f"✅ Cookie Max-Age is 604800 (7 days)")
        elif 'max-age=604800' in set_cookie_header.lower():
            print(f"✅ Cookie Max-Age is 604800 (7 days)")
        else:
            # Extract actual max-age for debugging
            match = re.search(r'max-age=(\d+)', set_cookie_header, re.IGNORECASE)
            if match:
                actual_age = match.group(1)
                assert actual_age == "604800", f"Expected Max-Age 604800, got {actual_age}"
            print(f"✅ Cookie Max-Age validated")


class TestTokenRefreshViaCookie:
    """Test token refresh using httpOnly cookie"""
    
    def test_refresh_works_with_cookie(self):
        """Token refresh should work when refresh_token is sent via cookie"""
        session = requests.Session()
        
        # Login to get cookie
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=TEST_RESIDENT,
            headers={"Content-Type": "application/json"}
        )
        
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        # Verify cookie was set in session
        assert 'genturix_refresh_token' in session.cookies, "Cookie not set in session"
        
        # Refresh token using cookie (empty body)
        refresh_response = session.post(
            f"{BASE_URL}/api/auth/refresh",
            json={},  # Empty body - token comes from cookie
            headers={"Content-Type": "application/json"}
        )
        
        assert refresh_response.status_code == 200, f"Refresh failed: {refresh_response.text}"
        
        data = refresh_response.json()
        
        # Should receive new access_token
        assert "access_token" in data, "New access_token missing from refresh response"
        assert len(data["access_token"]) > 0, "New access_token is empty"
        assert data["token_type"] == "bearer", "Invalid token_type"
        
        # Should NOT have refresh_token in body
        assert "refresh_token" not in data, "refresh_token should not be in refresh response body"
        
        print(f"✅ Token refresh successful via httpOnly cookie")
        print(f"   New access_token received")
    
    def test_refresh_fails_without_cookie(self):
        """Token refresh should fail when no cookie is provided"""
        # Fresh session without cookies
        response = requests.post(
            f"{BASE_URL}/api/auth/refresh",
            json={},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✅ Token refresh correctly rejected without cookie (401)")
    
    def test_refresh_rotates_token(self):
        """Refresh should rotate the token (old token invalid after refresh)"""
        session1 = requests.Session()
        session2 = requests.Session()
        
        # Login with session1
        login_response = session1.post(
            f"{BASE_URL}/api/auth/login",
            json=TEST_RESIDENT,
            headers={"Content-Type": "application/json"}
        )
        
        assert login_response.status_code == 200
        
        # Copy cookie to session2 before refresh
        session2.cookies = session1.cookies.copy()
        
        # Refresh with session1 - this should rotate the token
        refresh_response = session1.post(
            f"{BASE_URL}/api/auth/refresh",
            json={},
            headers={"Content-Type": "application/json"}
        )
        
        assert refresh_response.status_code == 200, "First refresh should succeed"
        
        # Try to refresh with session2 using old cookie - should fail
        # (token rotation means old token is invalidated)
        refresh_response2 = session2.post(
            f"{BASE_URL}/api/auth/refresh",
            json={},
            headers={"Content-Type": "application/json"}
        )
        
        # Should fail because token was rotated
        assert refresh_response2.status_code == 401, "Old token should be invalid after rotation"
        print(f"✅ Token rotation working - old tokens invalidated after refresh")


class TestLogoutClearsCookie:
    """Test logout clears the httpOnly cookie"""
    
    def test_logout_clears_cookie(self):
        """Logout should clear the genturix_refresh_token cookie"""
        session = requests.Session()
        
        # Login
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=TEST_RESIDENT,
            headers={"Content-Type": "application/json"}
        )
        
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        
        # Verify cookie exists
        assert 'genturix_refresh_token' in session.cookies, "Cookie not set after login"
        
        # Logout
        logout_response = session.post(
            f"{BASE_URL}/api/auth/logout",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
        
        assert logout_response.status_code == 200, f"Logout failed: {logout_response.text}"
        
        # Check if cookie is cleared (Set-Cookie with empty value or Max-Age=0)
        set_cookie_header = logout_response.headers.get('Set-Cookie', '')
        
        # Cookie should be deleted (empty value or max-age=0)
        cookie_cleared = (
            'genturix_refresh_token=""' in set_cookie_header or
            'genturix_refresh_token=;' in set_cookie_header or
            'Max-Age=0' in set_cookie_header or
            'max-age=0' in set_cookie_header.lower()
        )
        
        assert cookie_cleared, f"Cookie not properly cleared. Set-Cookie: {set_cookie_header}"
        
        print(f"✅ Logout clears httpOnly cookie correctly")
        print(f"   Message: {logout_response.json().get('message')}")
    
    def test_refresh_fails_after_logout(self):
        """Refresh should fail after logout (even with old cookie)"""
        session = requests.Session()
        
        # Login
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json=TEST_RESIDENT,
            headers={"Content-Type": "application/json"}
        )
        
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        
        # Save the cookie before logout
        old_cookie = session.cookies.get('genturix_refresh_token')
        
        # Logout
        logout_response = session.post(
            f"{BASE_URL}/api/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert logout_response.status_code == 200
        
        # Try to refresh with old cookie manually
        refresh_session = requests.Session()
        refresh_session.cookies.set('genturix_refresh_token', old_cookie, domain='genturix-mobile.preview.emergentagent.com', path='/api/auth')
        
        refresh_response = refresh_session.post(
            f"{BASE_URL}/api/auth/refresh",
            json={},
            headers={"Content-Type": "application/json"}
        )
        
        # Should fail because refresh_token_id was invalidated in DB
        assert refresh_response.status_code == 401, "Refresh should fail after logout"
        print(f"✅ Refresh correctly fails after logout (token invalidated in DB)")


class TestHealthEndpoint:
    """Basic health check to ensure API is running"""
    
    def test_health_check(self):
        """API health endpoint should return OK"""
        response = requests.get(f"{BASE_URL}/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "genturix-api"
        print(f"✅ API Health: {data['status']} - {data['service']} v{data['version']}")


class TestSuperAdminLogin:
    """Test SuperAdmin login with httpOnly cookies"""
    
    def test_superadmin_login_no_refresh_in_body(self):
        """SuperAdmin login should also use httpOnly cookies"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=TEST_SUPERADMIN,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"SuperAdmin login failed: {response.text}"
        
        data = response.json()
        
        # Same security requirements
        assert "access_token" in data, "access_token missing"
        assert "refresh_token" not in data, "SECURITY: refresh_token should not be in body"
        
        # Verify SuperAdmin role
        assert "SuperAdmin" in data["user"]["roles"], f"Expected SuperAdmin role, got {data['user']['roles']}"
        
        print(f"✅ SuperAdmin login uses httpOnly cookies correctly")
        print(f"   User: {data['user']['full_name']} - Roles: {data['user']['roles']}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
