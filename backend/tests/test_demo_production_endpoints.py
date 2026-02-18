"""
Backend Tests for Demo/Production Condominium Separation
Tests the refactored endpoints:
- POST /api/condominiums - Production condos with billing
- POST /api/superadmin/condominiums/demo - Demo condos without billing
"""
import pytest
import requests
import os
import uuid

# Get the backend URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Super Admin credentials from review request
SUPER_ADMIN_EMAIL = "superadmin@genturix.com"
SUPER_ADMIN_PASSWORD = "SuperAdmin123!"


class TestDemoProductionEndpoints:
    """Test suite for Demo/Production condominium creation endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with SuperAdmin authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as SuperAdmin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPER_ADMIN_EMAIL,
            "password": SUPER_ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Cannot authenticate as SuperAdmin: {login_response.status_code}")
        
        login_data = login_response.json()
        self.token = login_data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        self.created_condos = []
        
        yield
        
        # Cleanup: Delete test condominiums
        for condo_id in self.created_condos:
            try:
                self.session.delete(f"{BASE_URL}/api/super-admin/condominiums/{condo_id}", json={"password": SUPER_ADMIN_PASSWORD})
            except:
                pass
    
    # ============================================
    # TEST DEMO ENDPOINT
    # ============================================
    
    def test_create_demo_condominium_endpoint_exists(self):
        """POST /api/superadmin/condominiums/demo endpoint should exist"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "name": f"Test Demo Condo {unique_id}",
            "contact_email": f"test_demo_{unique_id}@test.com"
        }
        
        response = self.session.post(f"{BASE_URL}/api/superadmin/condominiums/demo", json=payload)
        
        # Should not be 404 or 405
        assert response.status_code not in [404, 405], f"Demo endpoint not found or method not allowed"
        print(f"✅ PASS: Demo endpoint exists - Status: {response.status_code}")
    
    def test_create_demo_condominium_success(self):
        """Demo endpoint should create condo with correct properties"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "name": f"Demo Condo Test {unique_id}",
            "address": "Demo Test Address",
            "contact_email": f"demo_test_{unique_id}@test.com",
            "contact_phone": "+1234567890"
        }
        
        response = self.session.post(f"{BASE_URL}/api/superadmin/condominiums/demo", json=payload)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        self.created_condos.append(data.get("id"))
        
        # Verify demo properties
        assert data.get("is_demo") == True, "is_demo should be True for demo condos"
        assert data.get("environment") == "demo", f"environment should be 'demo', got {data.get('environment')}"
        assert data.get("billing_status") == "demo", f"billing_status should be 'demo', got {data.get('billing_status')}"
        assert data.get("paid_seats") == 10, f"paid_seats should be fixed at 10, got {data.get('paid_seats')}"
        
        print(f"✅ PASS: Demo condominium created successfully with correct properties")
        print(f"   - is_demo: {data.get('is_demo')}")
        print(f"   - environment: {data.get('environment')}")
        print(f"   - billing_status: {data.get('billing_status')}")
        print(f"   - paid_seats: {data.get('paid_seats')}")
    
    def test_demo_condominium_fixed_10_seats(self):
        """Demo condos should have fixed 10 seats regardless of payload"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "name": f"Demo Seats Test {unique_id}",
            "contact_email": f"demo_seats_{unique_id}@test.com"
            # Note: Demo endpoint should ignore any paid_seats in payload
        }
        
        response = self.session.post(f"{BASE_URL}/api/superadmin/condominiums/demo", json=payload)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"
        
        data = response.json()
        self.created_condos.append(data.get("id"))
        
        assert data.get("paid_seats") == 10, f"Demo condos should have exactly 10 seats, got {data.get('paid_seats')}"
        print(f"✅ PASS: Demo condominium has fixed 10 seats")
    
    def test_demo_condominium_billing_disabled(self):
        """Demo condos should have billing disabled (verified from database properties)"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "name": f"Demo Billing Test {unique_id}",
            "contact_email": f"demo_billing_{unique_id}@test.com"
        }
        
        response = self.session.post(f"{BASE_URL}/api/superadmin/condominiums/demo", json=payload)
        
        assert response.status_code in [200, 201]
        data = response.json()
        self.created_condos.append(data.get("id"))
        
        # Get the full condo details to verify billing fields
        get_response = self.session.get(f"{BASE_URL}/api/condominiums/{data.get('id')}")
        
        if get_response.status_code == 200:
            condo_details = get_response.json()
            # billing_status should be 'demo' (not 'active')
            assert condo_details.get("billing_status") == "demo", f"Expected billing_status='demo', got {condo_details.get('billing_status')}"
            print(f"✅ PASS: Demo condo has billing disabled (billing_status=demo)")
        else:
            # At least verify from create response
            assert data.get("billing_status") == "demo"
            print(f"✅ PASS: Demo condo billing_status is 'demo' (from create response)")
    
    # ============================================
    # TEST PRODUCTION ENDPOINT
    # ============================================
    
    def test_create_production_condominium_endpoint_exists(self):
        """POST /api/condominiums endpoint should exist"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "name": f"Test Prod Condo {unique_id}",
            "address": "Test Production Address",
            "contact_email": f"test_prod_{unique_id}@test.com",
            "contact_phone": "+1234567890",
            "paid_seats": 25
        }
        
        response = self.session.post(f"{BASE_URL}/api/condominiums", json=payload)
        
        # Should not be 404 or 405
        assert response.status_code not in [404, 405], f"Production endpoint not found"
        print(f"✅ PASS: Production endpoint exists - Status: {response.status_code}")
    
    def test_create_production_condominium_success(self):
        """Production endpoint should create condo with billing enabled"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "name": f"Production Condo Test {unique_id}",
            "address": "Production Test Address",
            "contact_email": f"prod_test_{unique_id}@test.com",
            "contact_phone": "+1234567890",
            "paid_seats": 50
        }
        
        response = self.session.post(f"{BASE_URL}/api/condominiums", json=payload)
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        self.created_condos.append(data.get("id"))
        
        # Verify production properties
        assert data.get("is_demo") == False, f"is_demo should be False for production, got {data.get('is_demo')}"
        assert data.get("environment") == "production", f"environment should be 'production', got {data.get('environment')}"
        assert data.get("billing_status") == "active", f"billing_status should be 'active' for production, got {data.get('billing_status')}"
        
        print(f"✅ PASS: Production condominium created successfully")
        print(f"   - is_demo: {data.get('is_demo')}")
        print(f"   - environment: {data.get('environment')}")
        print(f"   - billing_status: {data.get('billing_status')}")
    
    def test_production_condominium_configurable_seats(self):
        """Production condos should accept custom paid_seats value"""
        unique_id = str(uuid.uuid4())[:8]
        custom_seats = 75
        
        payload = {
            "name": f"Production Seats Test {unique_id}",
            "address": "Seats Test Address",
            "contact_email": f"prod_seats_{unique_id}@test.com",
            "contact_phone": "+1234567890",
            "paid_seats": custom_seats
        }
        
        response = self.session.post(f"{BASE_URL}/api/condominiums", json=payload)
        
        assert response.status_code in [200, 201]
        data = response.json()
        self.created_condos.append(data.get("id"))
        
        assert data.get("paid_seats") == custom_seats, f"paid_seats should be {custom_seats}, got {data.get('paid_seats')}"
        print(f"✅ PASS: Production condo accepts custom paid_seats ({custom_seats})")
    
    def test_production_condominium_billing_enabled(self):
        """Production condos should have billing enabled"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "name": f"Production Billing Test {unique_id}",
            "address": "Billing Test Address",
            "contact_email": f"prod_billing_{unique_id}@test.com",
            "contact_phone": "+1234567890",
            "paid_seats": 30
        }
        
        response = self.session.post(f"{BASE_URL}/api/condominiums", json=payload)
        
        assert response.status_code in [200, 201]
        data = response.json()
        self.created_condos.append(data.get("id"))
        
        # billing_status should be 'active' for production
        assert data.get("billing_status") == "active", f"Expected billing_status='active', got {data.get('billing_status')}"
        print(f"✅ PASS: Production condo has billing enabled (billing_status=active)")
    
    # ============================================
    # COMPARISON TESTS
    # ============================================
    
    def test_demo_vs_production_different_environments(self):
        """Demo and Production condos should have different environment values"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create Demo
        demo_payload = {
            "name": f"Demo Env Test {unique_id}",
            "contact_email": f"demo_env_{unique_id}@test.com"
        }
        demo_response = self.session.post(f"{BASE_URL}/api/superadmin/condominiums/demo", json=demo_payload)
        assert demo_response.status_code in [200, 201]
        demo_data = demo_response.json()
        self.created_condos.append(demo_data.get("id"))
        
        # Create Production
        prod_payload = {
            "name": f"Prod Env Test {unique_id}",
            "address": "Env Test Address",
            "contact_email": f"prod_env_{unique_id}@test.com",
            "contact_phone": "+1234567890"
        }
        prod_response = self.session.post(f"{BASE_URL}/api/condominiums", json=prod_payload)
        assert prod_response.status_code in [200, 201]
        prod_data = prod_response.json()
        self.created_condos.append(prod_data.get("id"))
        
        # Compare
        assert demo_data.get("environment") == "demo", f"Demo should have environment='demo'"
        assert prod_data.get("environment") == "production", f"Production should have environment='production'"
        assert demo_data.get("environment") != prod_data.get("environment"), "Environments should differ"
        
        print(f"✅ PASS: Demo (env=demo) vs Production (env=production) properly differentiated")
    
    def test_demo_vs_production_billing_status(self):
        """Demo should have billing_status='demo', Production should have billing_status='active'"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create Demo
        demo_payload = {
            "name": f"Demo Billing Status {unique_id}",
            "contact_email": f"demo_bs_{unique_id}@test.com"
        }
        demo_response = self.session.post(f"{BASE_URL}/api/superadmin/condominiums/demo", json=demo_payload)
        assert demo_response.status_code in [200, 201]
        demo_data = demo_response.json()
        self.created_condos.append(demo_data.get("id"))
        
        # Create Production
        prod_payload = {
            "name": f"Prod Billing Status {unique_id}",
            "address": "BS Test Address",
            "contact_email": f"prod_bs_{unique_id}@test.com",
            "contact_phone": "+1234567890"
        }
        prod_response = self.session.post(f"{BASE_URL}/api/condominiums", json=prod_payload)
        assert prod_response.status_code in [200, 201]
        prod_data = prod_response.json()
        self.created_condos.append(prod_data.get("id"))
        
        # Compare billing status
        assert demo_data.get("billing_status") == "demo", f"Demo billing_status should be 'demo'"
        assert prod_data.get("billing_status") == "active", f"Production billing_status should be 'active'"
        
        print(f"✅ PASS: Billing status differentiation correct (demo='demo', production='active')")
    
    def test_demo_is_demo_flag_true(self):
        """Demo condos should have is_demo=True"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "name": f"Demo Flag Test {unique_id}",
            "contact_email": f"demo_flag_{unique_id}@test.com"
        }
        
        response = self.session.post(f"{BASE_URL}/api/superadmin/condominiums/demo", json=payload)
        assert response.status_code in [200, 201]
        data = response.json()
        self.created_condos.append(data.get("id"))
        
        assert data.get("is_demo") == True, f"is_demo should be True, got {data.get('is_demo')}"
        print(f"✅ PASS: Demo condo has is_demo=True")
    
    def test_production_is_demo_flag_false(self):
        """Production condos should have is_demo=False"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "name": f"Prod Flag Test {unique_id}",
            "address": "Flag Test Address",
            "contact_email": f"prod_flag_{unique_id}@test.com",
            "contact_phone": "+1234567890"
        }
        
        response = self.session.post(f"{BASE_URL}/api/condominiums", json=payload)
        assert response.status_code in [200, 201]
        data = response.json()
        self.created_condos.append(data.get("id"))
        
        assert data.get("is_demo") == False, f"is_demo should be False, got {data.get('is_demo')}"
        print(f"✅ PASS: Production condo has is_demo=False")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
