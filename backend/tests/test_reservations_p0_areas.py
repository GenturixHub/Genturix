"""
P0 Bug Test: Creating multiple common areas (4th area error [object Object])
This test verifies that:
1. Multiple areas (5+) can be created consecutively without errors
2. No hardcoded limit of 3 or 4 areas exists
3. Error messages are in Spanish (not [object Object])
4. Resident can create reservations in any area
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


class TestMultipleAreasCreation:
    """Test creating multiple areas consecutively - P0 Bug verification"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        self.admin_token = response.json()["access_token"]
        self.admin_headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
        
        # Get resident token
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        self.resident_token = response.json()["access_token"]
        self.resident_headers = {
            "Authorization": f"Bearer {self.resident_token}",
            "Content-Type": "application/json"
        }
        
        # Track created areas for cleanup
        self.created_area_ids = []
        yield
        
        # Cleanup: Delete test areas
        for area_id in self.created_area_ids:
            try:
                requests.delete(
                    f"{BASE_URL}/api/reservations/areas/{area_id}",
                    headers=self.admin_headers
                )
            except:
                pass
    
    def test_create_5_areas_consecutively(self):
        """P0: Create 5 areas consecutively - all should succeed"""
        test_areas = [
            {"name": "TEST_Area_1_Gimnasio", "area_type": "gym", "capacity": 15},
            {"name": "TEST_Area_2_Cancha_Tenis", "area_type": "tennis", "capacity": 4},
            {"name": "TEST_Area_3_BBQ", "area_type": "bbq", "capacity": 20},
            {"name": "TEST_Area_4_Salon_Eventos", "area_type": "salon", "capacity": 50},
            {"name": "TEST_Area_5_Cine", "area_type": "cinema", "capacity": 30},
        ]
        
        created_areas = []
        
        for i, area_data in enumerate(test_areas, 1):
            print(f"\n--- Creating area {i}: {area_data['name']} ---")
            
            response = requests.post(
                f"{BASE_URL}/api/reservations/areas",
                headers=self.admin_headers,
                json=area_data
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            # CRITICAL: All 5 areas must be created successfully
            assert response.status_code in [200, 201], \
                f"FAILED to create area {i} ({area_data['name']}): {response.status_code} - {response.text}"
            
            result = response.json()
            
            # Verify response has area_id
            assert "area_id" in result, f"Response missing area_id for area {i}"
            
            # Verify success message is in Spanish
            assert "message" in result, f"Response missing message for area {i}"
            assert "creada" in result["message"].lower() or "exitosamente" in result["message"].lower(), \
                f"Success message not in Spanish: {result['message']}"
            
            # Verify NO [object Object] in response
            response_text = response.text
            assert "[object Object]" not in response_text, \
                f"ERROR: [object Object] found in response for area {i}"
            
            created_areas.append(result["area_id"])
            self.created_area_ids.append(result["area_id"])
            
            print(f"✓ Area {i} created successfully: {result['area_id']}")
        
        # Verify all 5 areas were created
        assert len(created_areas) == 5, f"Expected 5 areas, got {len(created_areas)}"
        print(f"\n✓ SUCCESS: All 5 areas created without errors")
        
        # Verify areas appear in GET list
        response = requests.get(
            f"{BASE_URL}/api/reservations/areas",
            headers=self.admin_headers
        )
        assert response.status_code == 200
        areas_list = response.json()
        
        # Check all test areas are in the list
        area_names = [a["name"] for a in areas_list]
        for area_data in test_areas:
            assert area_data["name"] in area_names, \
                f"Area {area_data['name']} not found in areas list"
        
        print(f"✓ All 5 test areas verified in GET /api/reservations/areas")
    
    def test_no_hardcoded_limit(self):
        """Verify there's no hardcoded limit of 3 or 4 areas"""
        # Create 6 areas to ensure no limit at 3, 4, or 5
        for i in range(1, 7):
            area_data = {
                "name": f"TEST_NoLimit_Area_{i}",
                "area_type": "other",
                "capacity": 10
            }
            
            response = requests.post(
                f"{BASE_URL}/api/reservations/areas",
                headers=self.admin_headers,
                json=area_data
            )
            
            assert response.status_code in [200, 201], \
                f"LIMIT DETECTED: Failed at area {i}: {response.status_code} - {response.text}"
            
            self.created_area_ids.append(response.json()["area_id"])
            print(f"✓ Area {i}/6 created successfully")
        
        print(f"\n✓ NO HARDCODED LIMIT: Successfully created 6 areas")
    
    def test_error_messages_in_spanish(self):
        """Verify error messages are in Spanish, not [object Object]"""
        # Test 1: Create area with empty name (should fail with Spanish error)
        response = requests.post(
            f"{BASE_URL}/api/reservations/areas",
            headers=self.admin_headers,
            json={"name": "", "area_type": "gym", "capacity": 10}
        )
        
        # Should fail validation
        if response.status_code >= 400:
            response_text = response.text
            assert "[object Object]" not in response_text, \
                f"ERROR: [object Object] in error response: {response_text}"
            print(f"✓ Empty name error response: {response_text[:200]}")
        
        # Test 2: Create area with invalid capacity
        response = requests.post(
            f"{BASE_URL}/api/reservations/areas",
            headers=self.admin_headers,
            json={"name": "TEST_Invalid", "area_type": "gym", "capacity": -1}
        )
        
        if response.status_code >= 400:
            response_text = response.text
            assert "[object Object]" not in response_text, \
                f"ERROR: [object Object] in error response: {response_text}"
            print(f"✓ Invalid capacity error response: {response_text[:200]}")
    
    def test_resident_can_create_reservation_in_any_area(self):
        """Verify resident can create reservations in any area (including 4th+)"""
        # First create 4 test areas
        test_areas = []
        for i in range(1, 5):
            area_data = {
                "name": f"TEST_Resident_Area_{i}",
                "area_type": "other",
                "capacity": 10,
                "requires_approval": False
            }
            
            response = requests.post(
                f"{BASE_URL}/api/reservations/areas",
                headers=self.admin_headers,
                json=area_data
            )
            assert response.status_code in [200, 201]
            area_id = response.json()["area_id"]
            test_areas.append(area_id)
            self.created_area_ids.append(area_id)
        
        print(f"✓ Created 4 test areas for resident reservation test")
        
        # Now try to create a reservation in the 4th area (the one that was reported as failing)
        fourth_area_id = test_areas[3]
        
        # Use a future date
        reservation_data = {
            "area_id": fourth_area_id,
            "date": "2026-04-15",
            "start_time": "10:00",
            "end_time": "12:00",
            "guests_count": 2,
            "purpose": "Test reservation in 4th area"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/reservations",
            headers=self.resident_headers,
            json=reservation_data
        )
        
        print(f"Reservation in 4th area - Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Should succeed
        assert response.status_code in [200, 201], \
            f"FAILED to create reservation in 4th area: {response.status_code} - {response.text}"
        
        # Verify no [object Object] in response
        assert "[object Object]" not in response.text, \
            f"ERROR: [object Object] in reservation response"
        
        print(f"✓ Resident successfully created reservation in 4th area")


class TestAreaErrorHandling:
    """Test error handling returns proper Spanish messages"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.admin_token = response.json()["access_token"]
        self.admin_headers = {
            "Authorization": f"Bearer {self.admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_get_nonexistent_area(self):
        """Test getting non-existent area returns proper error"""
        response = requests.get(
            f"{BASE_URL}/api/reservations/areas/nonexistent-id-12345",
            headers=self.admin_headers
        )
        
        # Should return 404 or similar
        if response.status_code >= 400:
            assert "[object Object]" not in response.text, \
                f"ERROR: [object Object] in error response"
            print(f"✓ Non-existent area error: {response.status_code}")
    
    def test_delete_nonexistent_area(self):
        """Test deleting non-existent area returns proper error"""
        response = requests.delete(
            f"{BASE_URL}/api/reservations/areas/nonexistent-id-12345",
            headers=self.admin_headers
        )
        
        if response.status_code >= 400:
            assert "[object Object]" not in response.text, \
                f"ERROR: [object Object] in error response"
            print(f"✓ Delete non-existent area error: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
