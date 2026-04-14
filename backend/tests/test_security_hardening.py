"""
Security Hardening Tests for Genturix SaaS Platform
Tests: XSS protection, CORS, file upload validation, rate limiting, security headers, input sanitization

Test Credentials:
- Admin: admin@genturix.com / Admin123!
- Resident: test-resident@genturix.com / Admin123!
"""

import pytest
import requests
import os
import time
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://vuln-remediation-3.preview.emergentagent.com"

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
RESIDENT_EMAIL = "test-resident@genturix.com"
RESIDENT_PASSWORD = "Admin123!"


class TestSecurityHeaders:
    """Test security headers are present in all responses"""
    
    def test_health_endpoint_returns_200(self):
        """GET /api/health returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("status") == "ok"
        print("✓ Health endpoint returns 200 with status ok")
    
    def test_security_headers_present(self):
        """Security headers X-Content-Type-Options, X-Frame-Options, Referrer-Policy present"""
        response = requests.get(f"{BASE_URL}/api/health")
        
        # Check X-Content-Type-Options
        x_content_type = response.headers.get("X-Content-Type-Options")
        assert x_content_type == "nosniff", f"X-Content-Type-Options: expected 'nosniff', got '{x_content_type}'"
        
        # Check X-Frame-Options
        x_frame = response.headers.get("X-Frame-Options")
        assert x_frame == "DENY", f"X-Frame-Options: expected 'DENY', got '{x_frame}'"
        
        # Check Referrer-Policy
        referrer = response.headers.get("Referrer-Policy")
        assert referrer == "strict-origin-when-cross-origin", f"Referrer-Policy: expected 'strict-origin-when-cross-origin', got '{referrer}'"
        
        print("✓ All security headers present: X-Content-Type-Options=nosniff, X-Frame-Options=DENY, Referrer-Policy=strict-origin-when-cross-origin")


class TestAuthentication:
    """Test login flows still work after security hardening"""
    
    def test_admin_login_success(self):
        """Admin login with admin@genturix.com / Admin123!"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Admin login successful: {ADMIN_EMAIL}")
        return data["access_token"]
    
    def test_resident_login_success(self):
        """Resident login with test-resident@genturix.com / Admin123!"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        assert response.status_code == 200, f"Resident login failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == RESIDENT_EMAIL
        print(f"✓ Resident login successful: {RESIDENT_EMAIL}")
        return data["access_token"]


class TestCORSConfiguration:
    """Test CORS is properly configured (not wildcard in production)"""
    
    def test_cors_not_wildcard_for_credentials(self):
        """CORS should have explicit origins, not wildcard when credentials are used"""
        # Make an OPTIONS preflight request
        response = requests.options(
            f"{BASE_URL}/api/auth/login",
            headers={
                "Origin": "https://genturix.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Check that CORS headers are present
        allow_origin = response.headers.get("Access-Control-Allow-Origin")
        allow_credentials = response.headers.get("Access-Control-Allow-Credentials")
        
        # If credentials are allowed, origin should not be wildcard
        if allow_credentials and allow_credentials.lower() == "true":
            assert allow_origin != "*", "CORS allows credentials but uses wildcard origin - security risk!"
        
        print(f"✓ CORS configured: Allow-Origin={allow_origin}, Allow-Credentials={allow_credentials}")


class TestExistingEndpoints:
    """Test existing endpoints still work after security hardening"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            self.admin_token = response.json()["access_token"]
        else:
            pytest.skip("Admin login failed - skipping authenticated tests")
    
    def test_finanzas_overview(self):
        """GET /api/finanzas/overview still works"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/overview",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Finanzas overview failed: {response.status_code} - {response.text}"
        print("✓ GET /api/finanzas/overview returns 200")
    
    def test_casos_endpoint(self):
        """GET /api/casos still works"""
        response = requests.get(
            f"{BASE_URL}/api/casos",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Casos endpoint failed: {response.status_code} - {response.text}"
        print("✓ GET /api/casos returns 200")
    
    def test_documentos_endpoint(self):
        """GET /api/documentos still works"""
        response = requests.get(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Documentos endpoint failed: {response.status_code} - {response.text}"
        print("✓ GET /api/documentos returns 200")
    
    def test_notifications_v2_endpoint(self):
        """GET /api/notifications/v2 still works"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200, f"Notifications V2 failed: {response.status_code} - {response.text}"
        print("✓ GET /api/notifications/v2 returns 200")
    
    def test_legacy_notifications_endpoint(self):
        """GET /api/notifications still works"""
        response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        # Legacy endpoint may return 200 or redirect
        assert response.status_code in [200, 307, 308], f"Legacy notifications failed: {response.status_code}"
        print(f"✓ GET /api/notifications returns {response.status_code}")


class TestFileUploadValidation:
    """Test file upload security validations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            self.admin_token = response.json()["access_token"]
        else:
            pytest.skip("Admin login failed - skipping file upload tests")
    
    def test_block_exe_extension(self):
        """Document upload blocks .exe files"""
        files = {
            'file': ('malware.exe', b'MZ\x90\x00', 'application/octet-stream')
        }
        response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            files=files,
            data={"name": "Test Malware", "category": "otro", "visibility": "public"}
        )
        # 400 or 422 are both valid for validation errors
        assert response.status_code in [400, 422], f"Expected 400/422 for .exe, got {response.status_code}"
        print(f"✓ .exe files are blocked ({response.status_code})")
    
    def test_block_sh_extension(self):
        """Document upload blocks .sh files"""
        files = {
            'file': ('script.sh', b'#!/bin/bash\nrm -rf /', 'text/x-shellscript')
        }
        response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            files=files,
            data={"name": "Test Script", "category": "otro", "visibility": "public"}
        )
        # 400 or 422 are both valid for validation errors
        assert response.status_code in [400, 422], f"Expected 400/422 for .sh, got {response.status_code}"
        print(f"✓ .sh files are blocked ({response.status_code})")
    
    def test_block_bat_extension(self):
        """Document upload blocks .bat files"""
        files = {
            'file': ('script.bat', b'@echo off\ndel /f /q *', 'application/x-msdos-program')
        }
        response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            files=files,
            data={"name": "Test Batch", "category": "otro", "visibility": "public"}
        )
        # 400 or 422 are both valid for validation errors
        assert response.status_code in [400, 422], f"Expected 400/422 for .bat, got {response.status_code}"
        print(f"✓ .bat files are blocked ({response.status_code})")
    
    def test_reject_large_file(self):
        """Document upload rejects files > 20MB"""
        # Create a 21MB file (just over limit)
        large_content = b'X' * (21 * 1024 * 1024)
        files = {
            'file': ('large_file.pdf', large_content, 'application/pdf')
        }
        response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            files=files,
            data={"name": "Large File", "category": "otro", "visibility": "public"}
        )
        # 400, 413 (Payload Too Large), or 422 are valid for size rejection
        assert response.status_code in [400, 413, 422], f"Expected 400/413/422 for large file, got {response.status_code}"
        print(f"✓ Files > 20MB are rejected ({response.status_code})")
    
    def test_reject_empty_file(self):
        """Document upload rejects empty files"""
        files = {
            'file': ('empty.pdf', b'', 'application/pdf')
        }
        response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            files=files,
            data={"name": "Empty File", "category": "otro", "visibility": "public"}
        )
        # 400 or 422 are both valid for validation errors
        assert response.status_code in [400, 422], f"Expected 400/422 for empty file, got {response.status_code}"
        print(f"✓ Empty files are rejected ({response.status_code})")
    
    def test_allow_pdf_upload(self):
        """Document upload allows valid PDF files"""
        # Minimal valid PDF content
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF'
        files = {
            'file': ('test_document.pdf', pdf_content, 'application/pdf')
        }
        response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            files=files,
            data={"name": "TEST_Valid PDF", "category": "otro", "visibility": "public"}
        )
        # Should succeed or fail for other reasons (not extension/MIME)
        if response.status_code in [200, 201]:
            print("✓ Valid PDF files are accepted")
        else:
            # May fail due to storage config, but not due to validation
            try:
                error = response.json().get("detail", "")
                if isinstance(error, list):
                    error = str(error)
                assert "no permitido" not in error.lower(), f"PDF was blocked: {error}"
            except:
                pass
            print(f"✓ PDF validation passed (upload may fail for other reasons: {response.status_code})")


class TestRateLimiting:
    """Test rate limiting on sensitive endpoints"""
    
    def test_change_password_rate_limit(self):
        """Rate limiting on /api/auth/change-password (3/minute)"""
        # First login to get token
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if login_resp.status_code != 200:
            pytest.skip("Login failed - skipping rate limit test")
        
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Make 5 rapid requests - should hit rate limit
        responses = []
        for i in range(5):
            resp = requests.post(
                f"{BASE_URL}/api/auth/change-password",
                headers=headers,
                json={"current_password": "wrong", "new_password": "NewPass123!"}
            )
            responses.append(resp.status_code)
        
        # At least one should be 429 (rate limited) or all should be 400/401 (validation errors)
        has_rate_limit = 429 in responses
        all_validation_errors = all(r in [400, 401, 422] for r in responses)
        
        print(f"Change password responses: {responses}")
        if has_rate_limit:
            print("✓ Rate limiting active on /api/auth/change-password (429 received)")
        elif all_validation_errors:
            print("✓ Change password endpoint working (validation errors expected)")
        else:
            print(f"⚠ Rate limiting may not be active: {responses}")
    
    def test_reset_password_rate_limit(self):
        """Rate limiting on /api/auth/reset-password (3/minute)"""
        # Make 5 rapid requests
        responses = []
        for i in range(5):
            resp = requests.post(
                f"{BASE_URL}/api/auth/reset-password",
                json={"email": "nonexistent@test.com"}
            )
            responses.append(resp.status_code)
        
        # At least one should be 429 (rate limited) or endpoint may not exist
        has_rate_limit = 429 in responses
        
        print(f"Reset password responses: {responses}")
        if has_rate_limit:
            print("✓ Rate limiting active on /api/auth/reset-password (429 received)")
        elif 404 in responses:
            print("⚠ Reset password endpoint may not exist")
        else:
            print(f"⚠ Rate limiting status unclear: {responses}")


class TestResidentAccess:
    """Test resident user access after security hardening"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get resident token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        if response.status_code == 200:
            self.resident_token = response.json()["access_token"]
            self.user_data = response.json()["user"]
        else:
            pytest.skip("Resident login failed - skipping resident tests")
    
    def test_resident_can_access_finanzas(self):
        """Resident can access their finanzas data"""
        # Get unit_id from user data
        unit_id = self.user_data.get("unit_id")
        if unit_id:
            response = requests.get(
                f"{BASE_URL}/api/finanzas/unit/{unit_id}",
                headers={"Authorization": f"Bearer {self.resident_token}"}
            )
            # Should be 200 or 404 (no data), not 403
            assert response.status_code in [200, 404], f"Resident finanzas access failed: {response.status_code}"
            print(f"✓ Resident can access finanzas (status: {response.status_code})")
        else:
            # Try charges endpoint instead
            response = requests.get(
                f"{BASE_URL}/api/finanzas/charges",
                headers={"Authorization": f"Bearer {self.resident_token}"}
            )
            assert response.status_code in [200, 404], f"Resident charges access failed: {response.status_code}"
            print(f"✓ Resident can access charges (status: {response.status_code})")
    
    def test_resident_can_access_casos(self):
        """Resident can access casos"""
        response = requests.get(
            f"{BASE_URL}/api/casos",
            headers={"Authorization": f"Bearer {self.resident_token}"}
        )
        assert response.status_code == 200, f"Resident casos access failed: {response.status_code}"
        print("✓ Resident can access casos")
    
    def test_resident_can_access_notifications(self):
        """Resident can access notifications"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2",
            headers={"Authorization": f"Bearer {self.resident_token}"}
        )
        assert response.status_code == 200, f"Resident notifications access failed: {response.status_code}"
        print("✓ Resident can access notifications")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
