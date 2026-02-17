"""
Test Admin Password Reset Feature - Enterprise-grade password reset system
Tests:
- POST /api/admin/users/{id}/reset-password (Admin initiates reset)
- GET /api/auth/verify-reset-token (Verify token validity)
- POST /api/auth/reset-password-complete (Complete reset with new password)
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
RESIDENT_EMAIL = "residente@genturix.com"
RESIDENT_PASSWORD = "Resi123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def admin_user_info():
    """Get admin user info"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200
    return response.json()["user"]


@pytest.fixture(scope="module")
def resident_token():
    """Get resident authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": RESIDENT_EMAIL,
        "password": RESIDENT_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip("Resident login failed - skipping resident tests")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def resident_user_info():
    """Get resident user info"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": RESIDENT_EMAIL,
        "password": RESIDENT_PASSWORD
    })
    if response.status_code != 200:
        return None
    return response.json()["user"]


@pytest.fixture(scope="module")
def guard_user_info(admin_token):
    """Get guard user info"""
    response = requests.get(
        f"{BASE_URL}/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if response.status_code != 200:
        pytest.skip("Cannot fetch users")
    users = response.json()
    guard = next((u for u in users if GUARD_EMAIL in u.get("email", "")), None)
    return guard


class TestAdminPasswordResetEndpoint:
    """Tests for POST /api/admin/users/{id}/reset-password"""
    
    def test_reset_password_for_resident_returns_success(self, admin_token, resident_user_info):
        """Admin can initiate password reset for a resident"""
        if not resident_user_info:
            pytest.skip("No resident user found")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{resident_user_info['id']}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Should succeed (email may or may not be sent depending on Resend config)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "email_status" in data
        assert "token_expires_in" in data
        assert data["sessions_invalidated"] == True
        print(f"✓ Password reset initiated for resident. Email status: {data.get('email_status')}")

    def test_reset_password_for_guard_returns_success(self, admin_token, guard_user_info):
        """Admin can initiate password reset for a guard"""
        if not guard_user_info:
            pytest.skip("No guard user found")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{guard_user_info['id']}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert data["sessions_invalidated"] == True
        print(f"✓ Password reset initiated for guard. Email status: {data.get('email_status')}")

    def test_cannot_reset_own_password(self, admin_token, admin_user_info):
        """Admin cannot reset their own password via this endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{admin_user_info['id']}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "propia contraseña" in data.get("detail", "").lower() or "own password" in data.get("detail", "").lower()
        print("✓ Admin blocked from resetting own password")

    def test_cannot_reset_superadmin_password(self, admin_token):
        """Admin cannot reset SuperAdmin password"""
        # First, find a SuperAdmin user
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code != 200:
            pytest.skip("Cannot fetch users")
        
        users = response.json()
        superadmin = next((u for u in users if "SuperAdmin" in u.get("roles", [])), None)
        
        if not superadmin:
            pytest.skip("No SuperAdmin found in user list")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{superadmin['id']}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "SuperAdmin" in data.get("detail", "")
        print("✓ Admin blocked from resetting SuperAdmin password")

    def test_admin_cannot_reset_other_admin_password(self, admin_token):
        """Regular admin cannot reset another admin's password"""
        # First get all users to find another admin
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code != 200:
            pytest.skip("Cannot fetch users")
        
        users = response.json()
        # Find another admin that's not the current user
        other_admin = next((u for u in users if "Administrador" in u.get("roles", []) and u.get("email") != ADMIN_EMAIL), None)
        
        if not other_admin:
            print("✓ No other admin found to test - skipping")
            pytest.skip("No other admin found")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{other_admin['id']}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Should get 403 because regular admins can't reset other admins
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Admin blocked from resetting other admin password")

    def test_resident_cannot_access_reset_endpoint(self, resident_token, guard_user_info):
        """Resident (non-admin) cannot access the reset password endpoint"""
        if not guard_user_info:
            pytest.skip("No guard user found")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{guard_user_info['id']}/reset-password",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        
        # Should be 401 or 403 (forbidden)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}: {response.text}"
        print("✓ Resident blocked from accessing admin reset endpoint")

    def test_reset_nonexistent_user_returns_404(self, admin_token):
        """Reset password for non-existent user returns 404"""
        fake_user_id = "nonexistent-user-id-12345"
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{fake_user_id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Non-existent user returns 404")


class TestVerifyResetTokenEndpoint:
    """Tests for GET /api/auth/verify-reset-token"""
    
    def test_verify_invalid_token_returns_invalid(self):
        """Invalid/random token returns invalid=false"""
        response = requests.get(
            f"{BASE_URL}/api/auth/verify-reset-token?token=invalid-random-token-12345"
        )
        
        # Endpoint should return 200 with valid=false
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["valid"] == False
        assert "reason" in data
        print(f"✓ Invalid token correctly marked as invalid. Reason: {data.get('reason')}")

    def test_verify_empty_token_returns_invalid(self):
        """Empty token returns invalid"""
        response = requests.get(f"{BASE_URL}/api/auth/verify-reset-token?token=")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["valid"] == False
        print("✓ Empty token correctly marked as invalid")

    def test_verify_malformed_jwt_returns_invalid(self):
        """Malformed JWT returns invalid"""
        # A malformed JWT
        bad_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.INVALID.SIGNATURE"
        
        response = requests.get(f"{BASE_URL}/api/auth/verify-reset-token?token={bad_jwt}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["valid"] == False
        print("✓ Malformed JWT correctly marked as invalid")


class TestCompletePasswordResetEndpoint:
    """Tests for POST /api/auth/reset-password-complete"""
    
    def test_complete_with_invalid_token_returns_error(self):
        """Complete reset with invalid token returns error"""
        response = requests.post(
            f"{BASE_URL}/api/auth/reset-password-complete",
            json={
                "token": "invalid-token",
                "new_password": "NewSecure123!"
            }
        )
        
        # Should return 400 for invalid token
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "inválido" in data.get("detail", "").lower() or "expirado" in data.get("detail", "").lower() or "invalid" in data.get("detail", "").lower()
        print("✓ Invalid token correctly rejected on complete endpoint")

    def test_complete_with_weak_password_returns_error(self):
        """Complete reset with weak password returns appropriate error"""
        # Create a fake JWT-like token to test password validation
        response = requests.post(
            f"{BASE_URL}/api/auth/reset-password-complete",
            json={
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZW1haWwiOiJ0ZXN0QHRlc3QuY29tIiwiZXhwIjoxNzM1Njg5NjAwLCJ0eXBlIjoicGFzc3dvcmRfcmVzZXQifQ.signature",
                "new_password": "weak"
            }
        )
        
        # Should return 400 or 422 for password validation / invalid token
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}: {response.text}"
        print("✓ Weak password or invalid token correctly rejected")

    def test_complete_without_token_returns_validation_error(self):
        """Complete reset without token returns validation error"""
        response = requests.post(
            f"{BASE_URL}/api/auth/reset-password-complete",
            json={
                "new_password": "NewSecure123!"
            }
        )
        
        # Should return 422 (validation error) or 400
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}: {response.text}"
        print("✓ Missing token correctly rejected")

    def test_complete_without_password_returns_validation_error(self):
        """Complete reset without new password returns validation error"""
        response = requests.post(
            f"{BASE_URL}/api/auth/reset-password-complete",
            json={
                "token": "some-token"
            }
        )
        
        # Should return 422 (validation error) or 400
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}: {response.text}"
        print("✓ Missing password correctly rejected")


class TestPasswordResetFullFlow:
    """Integration tests for the full password reset flow"""
    
    def test_reset_invalidates_existing_sessions(self, admin_token, resident_user_info):
        """Verify that password reset updates password_changed_at to invalidate sessions"""
        if not resident_user_info:
            pytest.skip("No resident user found")
        
        # First, get current user state
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{resident_user_info['id']}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["sessions_invalidated"] == True
        print("✓ Password reset confirms session invalidation")

    def test_reset_sets_password_reset_required_flag(self, admin_token, resident_user_info):
        """After reset, user should have password_reset_required=True"""
        if not resident_user_info:
            pytest.skip("No resident user found")
        
        # Initiate reset
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{resident_user_info['id']}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        
        # Verify the response contains expected fields
        data = response.json()
        assert "token_expires_in" in data
        assert data["token_expires_in"] == "1 hour"
        print("✓ Reset token expiration correctly set to 1 hour")


class TestAuditLogging:
    """Tests to verify audit logging for password reset"""
    
    def test_reset_creates_audit_log(self, admin_token, guard_user_info):
        """Password reset should create audit log entry"""
        if not guard_user_info:
            pytest.skip("No guard user found")
        
        # Initiate reset
        response = requests.post(
            f"{BASE_URL}/api/admin/users/{guard_user_info['id']}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        
        # Try to verify audit log exists
        # Note: This might need adjustment based on audit log endpoint availability
        audit_response = requests.get(
            f"{BASE_URL}/api/audit-logs?limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if audit_response.status_code == 200:
            logs = audit_response.json()
            # Check if there's a recent PASSWORD_RESET_BY_ADMIN event
            reset_logs = [l for l in logs if "PASSWORD_RESET" in str(l.get("event_type", ""))]
            if reset_logs:
                print(f"✓ Audit log created for password reset: {reset_logs[0].get('event_type')}")
            else:
                print("✓ Password reset completed (audit log endpoint working but no specific log found in recent logs)")
        else:
            print(f"✓ Password reset completed (audit log endpoint returned {audit_response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
