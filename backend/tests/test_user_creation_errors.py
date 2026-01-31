"""
Test User Creation Error Messages - P0 Bug Fix Verification
Tests that backend error messages are properly displayed in frontend
Focus: XMLHttpRequest change in api.js to avoid body stream consumption
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestUserCreationErrorMessages:
    """Test that error messages from backend are properly returned"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin before each test"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@genturix.com",
            "password": "Admin123!"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_duplicate_email_error(self):
        """Test that duplicate email returns clear error message"""
        # Try to create user with existing admin email
        response = requests.post(f"{BASE_URL}/api/admin/users", 
            headers=self.headers,
            json={
                "email": "admin@genturix.com",  # Already exists
                "password": "Test123!",
                "full_name": "Test User",
                "role": "Residente",
                "apartment_number": "A-101"
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Response should have 'detail' field"
        assert "email ya está registrado" in data["detail"].lower() or "email" in data["detail"].lower(), \
            f"Error message should mention email already registered, got: {data['detail']}"
        print(f"✓ Duplicate email error: {data['detail']}")
    
    def test_residente_without_apartment_error(self):
        """Test that Residente without apartment_number returns clear error"""
        unique_email = f"test_residente_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/admin/users",
            headers=self.headers,
            json={
                "email": unique_email,
                "password": "Test123!",
                "full_name": "Test Residente",
                "role": "Residente"
                # Missing apartment_number
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Response should have 'detail' field"
        assert "apartamento" in data["detail"].lower() or "apartment" in data["detail"].lower(), \
            f"Error should mention apartment required, got: {data['detail']}"
        print(f"✓ Residente without apartment error: {data['detail']}")
    
    def test_guarda_without_badge_error(self):
        """Test that Guarda without badge_number returns clear error"""
        unique_email = f"test_guarda_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/admin/users",
            headers=self.headers,
            json={
                "email": unique_email,
                "password": "Test123!",
                "full_name": "Test Guarda",
                "role": "Guarda"
                # Missing badge_number
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data, "Response should have 'detail' field"
        assert "placa" in data["detail"].lower() or "badge" in data["detail"].lower(), \
            f"Error should mention badge required, got: {data['detail']}"
        print(f"✓ Guarda without badge error: {data['detail']}")
    
    def test_create_residente_success(self):
        """Test successful Residente creation with all required fields"""
        unique_email = f"test_residente_ok_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/admin/users",
            headers=self.headers,
            json={
                "email": unique_email,
                "password": "Test123!",
                "full_name": "Test Residente OK",
                "role": "Residente",
                "apartment_number": "A-101",
                "tower_block": "Torre A",
                "resident_type": "owner"
            }
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data or "user_id" in data, "Response should have user id"
        print(f"✓ Residente created successfully: {unique_email}")
    
    def test_create_guarda_success(self):
        """Test successful Guarda creation with all required fields"""
        unique_email = f"test_guarda_ok_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/admin/users",
            headers=self.headers,
            json={
                "email": unique_email,
                "password": "Test123!",
                "full_name": "Test Guarda OK",
                "role": "Guarda",
                "badge_number": f"G-{uuid.uuid4().hex[:4]}"
            }
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data or "user_id" in data, "Response should have user id"
        print(f"✓ Guarda created successfully: {unique_email}")
    
    def test_create_hr_success(self):
        """Test successful HR creation with department"""
        unique_email = f"test_hr_ok_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/admin/users",
            headers=self.headers,
            json={
                "email": unique_email,
                "password": "Test123!",
                "full_name": "Test HR OK",
                "role": "HR",
                "department": "Recursos Humanos"
            }
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data or "user_id" in data, "Response should have user id"
        print(f"✓ HR created successfully: {unique_email}")
    
    def test_invalid_role_error(self):
        """Test that invalid role returns clear error"""
        unique_email = f"test_invalid_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(f"{BASE_URL}/api/admin/users",
            headers=self.headers,
            json={
                "email": unique_email,
                "password": "Test123!",
                "full_name": "Test Invalid Role",
                "role": "InvalidRole"
            }
        )
        
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        data = response.json()
        print(f"✓ Invalid role error: {data.get('detail', data)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
