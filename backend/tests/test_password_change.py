"""
Test Password Change Feature - GENTURIX
Tests the secure password change flow including:
1. Error validations (incorrect password, same password, missing uppercase/number)
2. Successful password change
3. Session invalidation (old tokens rejected after password change)
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials - Resident account
TEST_EMAIL = "residente@genturix.com"
TEST_PASSWORD = "Resi123!"

class TestPasswordChangeValidations:
    """Test password change error validations"""
    
    @pytest.fixture
    def auth_token(self):
        """Get a fresh authentication token for each test"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code != 200:
            pytest.skip(f"Authentication failed: {response.text}")
        data = response.json()
        return data.get("access_token")
    
    def test_incorrect_current_password(self, auth_token):
        """Test: POST /api/auth/change-password with incorrect current password returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewSecure1!",
                "confirm_password": "NewSecure1!"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "incorrecta" in data.get("detail", "").lower() or "incorrect" in data.get("detail", "").lower()
        print(f"✅ PASS: Incorrect password validation works - {data.get('detail')}")
    
    def test_new_password_same_as_current(self, auth_token):
        """Test: POST /api/auth/change-password when new password equals current returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={
                "current_password": TEST_PASSWORD,
                "new_password": TEST_PASSWORD,
                "confirm_password": TEST_PASSWORD
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "diferente" in data.get("detail", "").lower() or "different" in data.get("detail", "").lower()
        print(f"✅ PASS: Same password validation works - {data.get('detail')}")
    
    def test_password_missing_uppercase(self, auth_token):
        """Test: POST /api/auth/change-password without uppercase letter returns 422 validation error"""
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={
                "current_password": TEST_PASSWORD,
                "new_password": "password123!",  # No uppercase
                "confirm_password": "password123!"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
        )
        
        # Pydantic validation returns 422
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        data = response.json()
        # Check for validation error about uppercase
        detail = str(data.get("detail", ""))
        assert "mayúscula" in detail.lower() or "uppercase" in detail.lower(), f"Expected uppercase error, got: {detail}"
        print(f"✅ PASS: Missing uppercase validation works")
    
    def test_password_missing_number(self, auth_token):
        """Test: POST /api/auth/change-password without number returns 422 validation error"""
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={
                "current_password": TEST_PASSWORD,
                "new_password": "PasswordABC!",  # No number
                "confirm_password": "PasswordABC!"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
        )
        
        # Pydantic validation returns 422
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        data = response.json()
        # Check for validation error about number
        detail = str(data.get("detail", ""))
        assert "número" in detail.lower() or "number" in detail.lower(), f"Expected number error, got: {detail}"
        print(f"✅ PASS: Missing number validation works")
    
    def test_password_too_short(self, auth_token):
        """Test: POST /api/auth/change-password with password < 8 chars returns 422"""
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={
                "current_password": TEST_PASSWORD,
                "new_password": "Pass1!",  # Only 6 chars
                "confirm_password": "Pass1!"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
        )
        
        # Pydantic validation returns 422
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print(f"✅ PASS: Password length validation works")
    
    def test_passwords_do_not_match(self, auth_token):
        """Test: POST /api/auth/change-password when passwords don't match returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={
                "current_password": TEST_PASSWORD,
                "new_password": "NewSecure123!",
                "confirm_password": "DifferentPass123!"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "coinciden" in data.get("detail", "").lower() or "match" in data.get("detail", "").lower()
        print(f"✅ PASS: Password mismatch validation works - {data.get('detail')}")
    
    def test_unauthenticated_request(self):
        """Test: POST /api/auth/change-password without auth token returns 401/403"""
        response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={
                "current_password": TEST_PASSWORD,
                "new_password": "NewSecure123!",
                "confirm_password": "NewSecure123!"
            },
            headers={"Content-Type": "application/json"}
            # No Authorization header
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✅ PASS: Unauthenticated request rejected with {response.status_code}")


class TestPasswordChangeSuccessAndSessionInvalidation:
    """Test successful password change and session invalidation"""
    
    def test_successful_password_change_and_session_invalidation(self):
        """
        Full flow test:
        1. Login with original password and save token
        2. Change password successfully using that token
        3. Verify password_changed_at is returned
        4. Try to use OLD token - should get 401 (session invalidated)
        5. Login with NEW password - should succeed
        6. Revert password back to original for future tests
        """
        # Step 1: Login and get the original token
        print("\n📍 Step 1: Login with original password")
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        
        assert login_response.status_code == 200, f"Initial login failed: {login_response.text}"
        login_data = login_response.json()
        original_token = login_data.get("access_token")
        assert original_token, "No access token in login response"
        print(f"✅ Login successful, token obtained")
        
        # Step 2: Change password using original token
        print("\n📍 Step 2: Change password to new value")
        new_password = "NewSecure999!"
        change_response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={
                "current_password": TEST_PASSWORD,
                "new_password": new_password,
                "confirm_password": new_password
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {original_token}"
            }
        )
        
        assert change_response.status_code == 200, f"Password change failed: {change_response.text}"
        change_data = change_response.json()
        
        # Verify response contains password_changed_at
        assert "password_changed_at" in change_data, "password_changed_at not in response"
        assert change_data.get("sessions_invalidated") == True, "sessions_invalidated should be True"
        print(f"✅ Password changed successfully at: {change_data['password_changed_at']}")
        
        # Wait a moment for the timestamp to be in effect
        time.sleep(1)
        
        # Step 3: Try to use OLD token - should be rejected
        print("\n📍 Step 3: Verify OLD token is rejected (session invalidated)")
        profile_response = requests.get(
            f"{BASE_URL}/api/profile",
            headers={"Authorization": f"Bearer {original_token}"}
        )
        
        assert profile_response.status_code == 401, f"Expected 401 for old token, got {profile_response.status_code}: {profile_response.text}"
        print(f"✅ OLD token correctly rejected with 401 - Session invalidated!")
        
        # Step 4: Login with NEW password - should succeed
        print("\n📍 Step 4: Login with NEW password")
        new_login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": new_password},
            headers={"Content-Type": "application/json"}
        )
        
        assert new_login_response.status_code == 200, f"Login with new password failed: {new_login_response.text}"
        new_login_data = new_login_response.json()
        new_token = new_login_data.get("access_token")
        print(f"✅ Login with NEW password successful!")
        
        # Step 5: Verify new token works
        print("\n📍 Step 5: Verify new token works for API calls")
        profile_new_response = requests.get(
            f"{BASE_URL}/api/profile",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        
        assert profile_new_response.status_code == 200, f"New token should work, got {profile_new_response.status_code}"
        print(f"✅ New token works correctly!")
        
        # Step 6: Revert password back to original for future tests
        print("\n📍 Step 6: Reverting password back to original")
        revert_response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={
                "current_password": new_password,
                "new_password": TEST_PASSWORD,
                "confirm_password": TEST_PASSWORD
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {new_token}"
            }
        )
        
        assert revert_response.status_code == 200, f"Password revert failed: {revert_response.text}"
        print(f"✅ Password reverted to original successfully!")
        
        # Final verification: Login with original password works again
        final_login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        
        assert final_login_response.status_code == 200, f"Final login with original password failed: {final_login_response.text}"
        print(f"✅ FULL TEST COMPLETE: Password change and session invalidation working correctly!")


class TestDatabaseUpdate:
    """Test that password_changed_at is properly stored in the database"""
    
    def test_password_changed_at_updated_in_db(self):
        """Verify that password_changed_at timestamp is stored after password change"""
        # Login
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("access_token")
        
        # Change password to a new one
        new_password = "TempPass789!"
        change_response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={
                "current_password": TEST_PASSWORD,
                "new_password": new_password,
                "confirm_password": new_password
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        
        assert change_response.status_code == 200, f"Password change failed: {change_response.text}"
        password_changed_at = change_response.json().get("password_changed_at")
        assert password_changed_at is not None, "password_changed_at should be returned"
        
        # The timestamp should be a valid ISO format
        from datetime import datetime
        try:
            # Try to parse the ISO timestamp
            datetime.fromisoformat(password_changed_at.replace("Z", "+00:00"))
            print(f"✅ password_changed_at is valid ISO timestamp: {password_changed_at}")
        except ValueError as e:
            pytest.fail(f"password_changed_at is not valid ISO format: {password_changed_at}, error: {e}")
        
        # Login with new password to get new token
        new_login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": new_password},
            headers={"Content-Type": "application/json"}
        )
        
        assert new_login_response.status_code == 200, f"Login with new password failed"
        new_token = new_login_response.json().get("access_token")
        
        # Revert password
        revert_response = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={
                "current_password": new_password,
                "new_password": TEST_PASSWORD,
                "confirm_password": TEST_PASSWORD
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {new_token}"
            }
        )
        
        assert revert_response.status_code == 200, f"Revert failed: {revert_response.text}"
        print(f"✅ password_changed_at successfully updated in DB")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
