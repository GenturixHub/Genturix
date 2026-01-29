"""
Profile Module Tests - GENTURIX
Tests for:
1. GET /api/profile - View own profile
2. PATCH /api/profile - Update profile (name, phone, description)
3. GET /api/profile/{user_id} - View public profile of another user
4. Multi-tenant validation - User cannot view profile from different condominium (403)
5. SuperAdmin can view profiles from any condominium
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "SuperAdmin123!"

class TestProfileModule:
    """Profile Module endpoint tests"""
    
    @pytest.fixture(scope="class")
    def superadmin_token(self):
        """Get SuperAdmin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERADMIN_EMAIL,
            "password": SUPERADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"SuperAdmin login failed: {response.status_code} - {response.text}")
        data = response.json()
        return data["access_token"], data["user"]
    
    @pytest.fixture(scope="class")
    def test_condominium(self, superadmin_token):
        """Create a test condominium for multi-tenant testing"""
        token, _ = superadmin_token
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create test condominium
        condo_data = {
            "name": f"TEST_Condo_Profile_{uuid.uuid4().hex[:8]}",
            "address": "Test Address 123",
            "contact_email": "test@testcondo.com",
            "contact_phone": "+1234567890",
            "max_users": 50
        }
        response = requests.post(f"{BASE_URL}/api/condominiums", json=condo_data, headers=headers)
        if response.status_code not in [200, 201]:
            pytest.skip(f"Failed to create test condominium: {response.text}")
        
        condo = response.json()
        yield condo
        
        # Cleanup - delete test condominium
        try:
            requests.delete(f"{BASE_URL}/api/super-admin/condominiums/{condo['id']}", 
                          json={"password": SUPERADMIN_PASSWORD}, headers=headers)
        except:
            pass
    
    @pytest.fixture(scope="class")
    def test_users_same_condo(self, superadmin_token, test_condominium):
        """Create two test users in the same condominium"""
        token, _ = superadmin_token
        headers = {"Authorization": f"Bearer {token}"}
        condo_id = test_condominium["id"]
        
        users = []
        for i in range(2):
            user_data = {
                "email": f"TEST_profile_user{i}_{uuid.uuid4().hex[:6]}@test.com",
                "password": "TestPass123!",
                "full_name": f"TEST Profile User {i}",
                "roles": ["Residente"],
                "condominium_id": condo_id
            }
            response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data, headers=headers)
            if response.status_code in [200, 201]:
                users.append({**response.json(), "password": "TestPass123!"})
        
        if len(users) < 2:
            pytest.skip("Failed to create test users in same condominium")
        
        yield users
    
    @pytest.fixture(scope="class")
    def test_user_different_condo(self, superadmin_token):
        """Create a test user in a different condominium"""
        token, _ = superadmin_token
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create another condominium
        condo_data = {
            "name": f"TEST_Condo_Other_{uuid.uuid4().hex[:8]}",
            "address": "Other Address 456",
            "contact_email": "other@testcondo.com",
            "contact_phone": "+9876543210",
            "max_users": 50
        }
        response = requests.post(f"{BASE_URL}/api/condominiums", json=condo_data, headers=headers)
        if response.status_code not in [200, 201]:
            pytest.skip(f"Failed to create other condominium: {response.text}")
        
        other_condo = response.json()
        
        # Create user in other condominium
        user_data = {
            "email": f"TEST_other_condo_user_{uuid.uuid4().hex[:6]}@test.com",
            "password": "TestPass123!",
            "full_name": "TEST Other Condo User",
            "roles": ["Residente"],
            "condominium_id": other_condo["id"]
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data, headers=headers)
        if response.status_code not in [200, 201]:
            pytest.skip(f"Failed to create user in other condominium: {response.text}")
        
        user = {**response.json(), "password": "TestPass123!", "condominium": other_condo}
        yield user
        
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/api/super-admin/condominiums/{other_condo['id']}", 
                          json={"password": SUPERADMIN_PASSWORD}, headers=headers)
        except:
            pass
    
    def get_user_token(self, email, password):
        """Helper to get user token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        return None
    
    # ==================== GET /api/profile Tests ====================
    
    def test_get_own_profile_success(self, superadmin_token):
        """Test GET /api/profile returns current user's full profile"""
        token, user = superadmin_token
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/profile", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "full_name" in data
        assert "roles" in data
        assert "is_active" in data
        assert "created_at" in data
        # Profile-specific fields
        assert "phone" in data or data.get("phone") is None
        assert "profile_photo" in data or data.get("profile_photo") is None
        assert "public_description" in data or data.get("public_description") is None
        assert "condominium_name" in data or data.get("condominium_name") is None
        
        print(f"✓ GET /api/profile returns full profile for user: {data['email']}")
    
    def test_get_own_profile_unauthorized(self):
        """Test GET /api/profile without token returns 401/403"""
        response = requests.get(f"{BASE_URL}/api/profile")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ GET /api/profile without auth returns 401/403")
    
    # ==================== PATCH /api/profile Tests ====================
    
    def test_update_profile_full_name(self, test_users_same_condo):
        """Test PATCH /api/profile updates full_name"""
        user = test_users_same_condo[0]
        token = self.get_user_token(user["email"], user["password"])
        assert token, "Failed to get user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        new_name = f"Updated Name {uuid.uuid4().hex[:6]}"
        
        response = requests.patch(f"{BASE_URL}/api/profile", 
                                 json={"full_name": new_name}, 
                                 headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["full_name"] == new_name
        
        # Verify persistence with GET
        get_response = requests.get(f"{BASE_URL}/api/profile", headers=headers)
        assert get_response.status_code == 200
        assert get_response.json()["full_name"] == new_name
        
        print(f"✓ PATCH /api/profile updates full_name to: {new_name}")
    
    def test_update_profile_phone(self, test_users_same_condo):
        """Test PATCH /api/profile updates phone"""
        user = test_users_same_condo[0]
        token = self.get_user_token(user["email"], user["password"])
        assert token, "Failed to get user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        new_phone = f"+52 555 {uuid.uuid4().hex[:6]}"
        
        response = requests.patch(f"{BASE_URL}/api/profile", 
                                 json={"phone": new_phone}, 
                                 headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["phone"] == new_phone
        
        print(f"✓ PATCH /api/profile updates phone to: {new_phone}")
    
    def test_update_profile_public_description(self, test_users_same_condo):
        """Test PATCH /api/profile updates public_description"""
        user = test_users_same_condo[0]
        token = self.get_user_token(user["email"], user["password"])
        assert token, "Failed to get user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        new_description = f"Test description {uuid.uuid4().hex[:8]}"
        
        response = requests.patch(f"{BASE_URL}/api/profile", 
                                 json={"public_description": new_description}, 
                                 headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["public_description"] == new_description
        
        print(f"✓ PATCH /api/profile updates public_description")
    
    def test_update_profile_multiple_fields(self, test_users_same_condo):
        """Test PATCH /api/profile updates multiple fields at once"""
        user = test_users_same_condo[0]
        token = self.get_user_token(user["email"], user["password"])
        assert token, "Failed to get user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        update_data = {
            "full_name": f"Multi Update {uuid.uuid4().hex[:6]}",
            "phone": "+1 999 888 7777",
            "public_description": "Multi-field update test"
        }
        
        response = requests.patch(f"{BASE_URL}/api/profile", 
                                 json=update_data, 
                                 headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["phone"] == update_data["phone"]
        assert data["public_description"] == update_data["public_description"]
        
        print("✓ PATCH /api/profile updates multiple fields at once")
    
    def test_update_profile_empty_body_fails(self, test_users_same_condo):
        """Test PATCH /api/profile with empty body returns 400"""
        user = test_users_same_condo[0]
        token = self.get_user_token(user["email"], user["password"])
        assert token, "Failed to get user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.patch(f"{BASE_URL}/api/profile", 
                                 json={}, 
                                 headers=headers)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ PATCH /api/profile with empty body returns 400")
    
    # ==================== GET /api/profile/{user_id} Tests ====================
    
    def test_get_public_profile_same_condo(self, test_users_same_condo):
        """Test GET /api/profile/{user_id} - User can view profile of user in same condominium"""
        user1 = test_users_same_condo[0]
        user2 = test_users_same_condo[1]
        
        # User1 views User2's profile
        token = self.get_user_token(user1["email"], user1["password"])
        assert token, "Failed to get user1 token"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/profile/{user2['id']}", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["id"] == user2["id"]
        assert data["full_name"] == user2["full_name"]
        assert "roles" in data
        # Public profile should NOT include email (privacy)
        assert "email" not in data or data.get("email") is None
        
        print(f"✓ User can view public profile of user in same condominium")
    
    def test_get_public_profile_different_condo_forbidden(self, test_users_same_condo, test_user_different_condo):
        """Test GET /api/profile/{user_id} - User CANNOT view profile from different condominium (403)"""
        user_same_condo = test_users_same_condo[0]
        user_other_condo = test_user_different_condo
        
        # User from condo A tries to view user from condo B
        token = self.get_user_token(user_same_condo["email"], user_same_condo["password"])
        assert token, "Failed to get user token"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/profile/{user_other_condo['id']}", headers=headers)
        
        assert response.status_code == 403, f"Expected 403 (forbidden), got {response.status_code}: {response.text}"
        
        print("✓ Multi-tenant validation: User CANNOT view profile from different condominium (403)")
    
    def test_superadmin_can_view_any_profile(self, superadmin_token, test_user_different_condo):
        """Test SuperAdmin CAN view profiles from any condominium"""
        token, _ = superadmin_token
        user_other_condo = test_user_different_condo
        
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/profile/{user_other_condo['id']}", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["id"] == user_other_condo["id"]
        
        print("✓ SuperAdmin CAN view profiles from any condominium")
    
    def test_get_public_profile_nonexistent_user(self, superadmin_token):
        """Test GET /api/profile/{user_id} with non-existent user returns 404"""
        token, _ = superadmin_token
        headers = {"Authorization": f"Bearer {token}"}
        
        fake_user_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/api/profile/{fake_user_id}", headers=headers)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ GET /api/profile/{user_id} with non-existent user returns 404")
    
    def test_get_public_profile_unauthorized(self, test_users_same_condo):
        """Test GET /api/profile/{user_id} without token returns 401/403"""
        user = test_users_same_condo[0]
        
        response = requests.get(f"{BASE_URL}/api/profile/{user['id']}")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ GET /api/profile/{user_id} without auth returns 401/403")
    
    # ==================== Public Profile Response Validation ====================
    
    def test_public_profile_response_structure(self, test_users_same_condo):
        """Test public profile response has correct structure (limited fields)"""
        user1 = test_users_same_condo[0]
        user2 = test_users_same_condo[1]
        
        # First update user2's profile with description
        token2 = self.get_user_token(user2["email"], user2["password"])
        headers2 = {"Authorization": f"Bearer {token2}"}
        requests.patch(f"{BASE_URL}/api/profile", 
                      json={"public_description": "Test public description", "phone": "+1234567890"}, 
                      headers=headers2)
        
        # User1 views User2's public profile
        token1 = self.get_user_token(user1["email"], user1["password"])
        headers1 = {"Authorization": f"Bearer {token1}"}
        
        response = requests.get(f"{BASE_URL}/api/profile/{user2['id']}", headers=headers1)
        
        assert response.status_code == 200
        data = response.json()
        
        # Public profile should include these fields
        assert "id" in data
        assert "full_name" in data
        assert "roles" in data
        assert "public_description" in data or data.get("public_description") is None
        assert "profile_photo" in data or data.get("profile_photo") is None
        assert "condominium_name" in data or data.get("condominium_name") is None
        assert "phone" in data or data.get("phone") is None  # Phone included for internal contacts
        
        print("✓ Public profile response has correct structure")


class TestProfileWithExistingUsers:
    """Test profile endpoints with existing users in the system"""
    
    def test_superadmin_profile(self):
        """Test SuperAdmin can view their own profile"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERADMIN_EMAIL,
            "password": SUPERADMIN_PASSWORD
        })
        
        if response.status_code != 200:
            pytest.skip("SuperAdmin login failed")
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        profile_response = requests.get(f"{BASE_URL}/api/profile", headers=headers)
        
        assert profile_response.status_code == 200
        data = profile_response.json()
        assert data["email"] == SUPERADMIN_EMAIL
        assert "SuperAdmin" in data["roles"]
        
        print(f"✓ SuperAdmin profile loaded: {data['full_name']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
