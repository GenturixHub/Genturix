"""
Test suite for GENTURIX Onboarding Wizard with Billing Engine Integration
Tests the new 6-step wizard including Step 4: Plan y Facturación

Features tested:
- Billing preview API
- Onboarding wizard API with billing data
- Validation endpoints
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable is required")

SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "Admin123!"


class TestAuthAndSetup:
    """Authentication and setup tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for SuperAdmin"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        
        if response.status_code != 200:
            pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
        
        data = response.json()
        assert "access_token" in data, "Response missing access_token"
        return data["access_token"]
    
    def test_health_check(self):
        """Test basic health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        print("PASS: Health check endpoint working")
    
    def test_superadmin_login(self, auth_token):
        """Test SuperAdmin can login"""
        assert auth_token is not None
        assert len(auth_token) > 10
        print("PASS: SuperAdmin login successful")


class TestBillingPreviewAPI:
    """Tests for the billing preview endpoint - Step 4 support"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for SuperAdmin"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Authentication failed: {response.status_code}")
        return response.json()["access_token"]
    
    def test_billing_preview_monthly(self, auth_token):
        """Test billing preview for monthly cycle"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/billing/preview",
            headers=headers,
            json={"initial_units": 10, "billing_cycle": "monthly"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "seats" in data, "Missing 'seats' in response"
        assert "price_per_seat" in data, "Missing 'price_per_seat' in response"
        assert "billing_cycle" in data, "Missing 'billing_cycle' in response"
        assert "monthly_amount" in data, "Missing 'monthly_amount' in response"
        assert "effective_amount" in data, "Missing 'effective_amount' in response"
        
        # Validate values
        assert data["seats"] == 10, f"Expected 10 seats, got {data['seats']}"
        assert data["billing_cycle"] == "monthly", f"Expected monthly cycle, got {data['billing_cycle']}"
        assert data["price_per_seat"] > 0, "Price per seat should be > 0"
        assert data["monthly_amount"] > 0, "Monthly amount should be > 0"
        
        print(f"PASS: Billing preview monthly - seats: {data['seats']}, amount: ${data['effective_amount']}")
    
    def test_billing_preview_yearly(self, auth_token):
        """Test billing preview for yearly cycle with discount"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/billing/preview",
            headers=headers,
            json={"initial_units": 50, "billing_cycle": "yearly"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate yearly discount exists
        assert "yearly_discount_percent" in data, "Missing 'yearly_discount_percent' in response"
        assert data["billing_cycle"] == "yearly"
        
        # Yearly effective amount should be less than 12x monthly if there's a discount
        if data["yearly_discount_percent"] > 0:
            expected_without_discount = data["monthly_amount"] * 12
            assert data["effective_amount"] < expected_without_discount, "Yearly discount not applied correctly"
        
        print(f"PASS: Billing preview yearly - discount: {data['yearly_discount_percent']}%, effective: ${data['effective_amount']}")
    
    def test_billing_preview_min_units(self, auth_token):
        """Test billing preview with minimum units (1)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/billing/preview",
            headers=headers,
            json={"initial_units": 1, "billing_cycle": "monthly"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["seats"] == 1
        print("PASS: Billing preview with 1 unit works")
    
    def test_billing_preview_max_units(self, auth_token):
        """Test billing preview with high units (500)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/billing/preview",
            headers=headers,
            json={"initial_units": 500, "billing_cycle": "monthly"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["seats"] == 500
        print(f"PASS: Billing preview with 500 units - amount: ${data['effective_amount']}")


class TestOnboardingValidation:
    """Tests for onboarding validation endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for SuperAdmin"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Authentication failed: {response.status_code}")
        return response.json()["access_token"]
    
    def test_validate_unique_email(self, auth_token):
        """Test email validation rejects duplicate"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # SuperAdmin email should already exist
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/validate",
            headers=headers,
            json={"field": "email", "value": SUPERADMIN_EMAIL}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["valid"] == False, "Existing email should be marked as invalid"
        print("PASS: Email validation rejects existing email")
    
    def test_validate_new_email(self, auth_token):
        """Test email validation accepts new email"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        unique_email = f"newadmin_{uuid.uuid4().hex[:8]}@test.com"
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/validate",
            headers=headers,
            json={"field": "email", "value": unique_email}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["valid"] == True, f"New email should be valid, got: {data}"
        print("PASS: Email validation accepts new email")
    
    def test_get_timezones(self, auth_token):
        """Test timezones endpoint returns valid data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/super-admin/onboarding/timezones",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "timezones" in data, "Missing 'timezones' in response"
        assert len(data["timezones"]) > 0, "Should have at least one timezone"
        
        # Check timezone structure
        tz = data["timezones"][0]
        assert "value" in tz, "Timezone missing 'value'"
        assert "label" in tz, "Timezone missing 'label'"
        print(f"PASS: Timezones endpoint returned {len(data['timezones'])} timezones")


class TestOnboardingWizardE2E:
    """End-to-end tests for creating condominium via wizard"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for SuperAdmin"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Authentication failed: {response.status_code}")
        return response.json()["access_token"]
    
    def test_create_condominium_full_flow(self, auth_token):
        """Test full wizard flow: Create condo with billing data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        unique_id = uuid.uuid4().hex[:8]
        
        # Full wizard payload matching frontend
        wizard_data = {
            "condominium": {
                "name": f"Test Condo {unique_id}",
                "address": "Test Address 123, Test City",
                "country": "Costa Rica",
                "timezone": "America/Costa_Rica"
            },
            "admin": {
                "full_name": f"Admin User {unique_id}",
                "email": f"admin_{unique_id}@testcondo.com"
            },
            "modules": {
                "security": True,
                "hr": False,
                "reservations": False,
                "school": False,
                "payments": False,
                "cctv": False
            },
            "areas": [],
            # BILLING ENGINE: Step 4 data
            "billing": {
                "initial_units": 25,
                "billing_cycle": "monthly",
                "billing_provider": "sinpe"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers=headers,
            json=wizard_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert data.get("success") == True, f"Expected success=true, got: {data}"
        assert "condominium" in data, "Missing 'condominium' in response"
        assert "admin_credentials" in data, "Missing 'admin_credentials' in response"
        
        # Validate condominium data
        condo = data["condominium"]
        assert condo["name"] == wizard_data["condominium"]["name"]
        assert condo.get("id") is not None, "Missing condominium ID"
        
        # Validate admin credentials
        creds = data["admin_credentials"]
        assert creds.get("email") is not None, "Missing admin email"
        assert creds.get("password") is not None, "Missing admin password"
        
        print(f"PASS: Created condominium '{condo['name']}' with ID: {condo['id']}")
        
        # Store condo_id for verification
        condo_id = condo["id"]
        return condo_id
    
    def test_create_condominium_with_yearly_billing(self, auth_token):
        """Test creating condo with yearly billing cycle"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        unique_id = uuid.uuid4().hex[:8]
        
        wizard_data = {
            "condominium": {
                "name": f"Yearly Condo {unique_id}",
                "address": "Yearly Test Address",
                "country": "Mexico",
                "timezone": "America/Mexico_City"
            },
            "admin": {
                "full_name": f"Yearly Admin {unique_id}",
                "email": f"yearly_{unique_id}@testcondo.com"
            },
            "modules": {
                "security": True,
                "hr": True,
                "reservations": True,
                "school": False,
                "payments": False,
                "cctv": False
            },
            "areas": [],
            "billing": {
                "initial_units": 100,
                "billing_cycle": "yearly",
                "billing_provider": "stripe"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers=headers,
            json=wizard_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        
        print(f"PASS: Created condominium with yearly billing - {data['condominium']['name']}")
    
    def test_create_condominium_with_areas(self, auth_token):
        """Test creating condo with areas (reservations module enabled)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        unique_id = uuid.uuid4().hex[:8]
        
        wizard_data = {
            "condominium": {
                "name": f"Areas Condo {unique_id}",
                "address": "Areas Test Address",
                "country": "Panama",
                "timezone": "America/Panama"
            },
            "admin": {
                "full_name": f"Areas Admin {unique_id}",
                "email": f"areas_{unique_id}@testcondo.com"
            },
            "modules": {
                "security": True,
                "hr": False,
                "reservations": True,  # Enable reservations
                "school": False,
                "payments": False,
                "cctv": False
            },
            "areas": [
                {"name": "Piscina", "capacity": 30, "requires_approval": False},
                {"name": "Gimnasio", "capacity": 20, "requires_approval": False}
            ],
            "billing": {
                "initial_units": 50,
                "billing_cycle": "monthly",
                "billing_provider": "manual"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers=headers,
            json=wizard_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        
        print(f"PASS: Created condominium with areas - {data['condominium']['name']}")


class TestVerifyPaidSeats:
    """Verify paid_seats is correctly saved in database"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for SuperAdmin"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Authentication failed: {response.status_code}")
        return response.json()["access_token"]
    
    def test_verify_paid_seats_saved(self, auth_token):
        """Create condo and verify paid_seats via billing overview endpoint"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        unique_id = uuid.uuid4().hex[:8]
        expected_seats = 42
        
        # Create condominium with specific seat count
        wizard_data = {
            "condominium": {
                "name": f"Seats Test {unique_id}",
                "address": "Seats Test Address",
                "country": "Costa Rica",
                "timezone": "America/Costa_Rica"
            },
            "admin": {
                "full_name": f"Seats Admin {unique_id}",
                "email": f"seats_{unique_id}@testcondo.com"
            },
            "modules": {
                "security": True,
                "hr": False,
                "reservations": False,
                "school": False,
                "payments": False,
                "cctv": False
            },
            "areas": [],
            "billing": {
                "initial_units": expected_seats,
                "billing_cycle": "monthly",
                "billing_provider": "sinpe"
            }
        }
        
        # Create condominium
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers=headers,
            json=wizard_data
        )
        
        assert response.status_code == 200, f"Failed to create condo: {response.text}"
        data = response.json()
        condo_id = data["condominium"]["id"]
        condo_name = data["condominium"]["name"]
        
        # Verify paid_seats from billing overview (SuperAdmin endpoint)
        billing_response = requests.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            headers=headers
        )
        
        assert billing_response.status_code == 200, f"Failed to get billing overview: {billing_response.text}"
        billing_data = billing_response.json()
        
        # Find our condo in the overview
        condos = billing_data.get("condominiums", [])
        our_condo = next((c for c in condos if c.get("id") == condo_id), None)
        
        assert our_condo is not None, f"Created condo not found in billing overview. Condo ID: {condo_id}"
        assert "paid_seats" in our_condo, f"Missing paid_seats in condo: {our_condo}"
        assert our_condo["paid_seats"] == expected_seats, f"Expected {expected_seats} seats, got {our_condo['paid_seats']}"
        
        print(f"PASS: Verified paid_seats={expected_seats} saved correctly for condo '{condo_name}' (ID: {condo_id})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
