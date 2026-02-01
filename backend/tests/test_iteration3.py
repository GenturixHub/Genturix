"""
GENTURIX - Iteration 3 Backend Tests
Testing:
- Multi-Tenant API (condominiums CRUD, modules, billing)
- Auth with condominium_id
- RRHH module endpoints (guards, shifts)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://saas-dashboard-31.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"
RESIDENT_EMAIL = "residente@genturix.com"
RESIDENT_PASSWORD = "Resi123!"

class TestAuthWithCondominiumId:
    """Test that login response includes condominium_id"""
    
    def test_login_returns_condominium_id_field(self):
        """Login response should include condominium_id (even if null)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Verify user object has condominium_id field
        assert "user" in data, "Response missing 'user' field"
        user = data["user"]
        assert "condominium_id" in user, "User object missing 'condominium_id' field"
        print(f"✓ Login returns condominium_id: {user.get('condominium_id')}")
    
    def test_login_guard_returns_condominium_id(self):
        """Guard login should also include condominium_id"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "condominium_id" in data["user"]
        print(f"✓ Guard login returns condominium_id: {data['user'].get('condominium_id')}")
    
    def test_login_resident_returns_condominium_id(self):
        """Resident login should also include condominium_id"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "condominium_id" in data["user"]
        print(f"✓ Resident login returns condominium_id: {data['user'].get('condominium_id')}")


class TestMultiTenantCondominiums:
    """Test Multi-Tenant Condominium Management APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.created_condo_id = None
    
    def test_create_condominium(self):
        """POST /api/condominiums - Create new condominium"""
        unique_id = str(uuid.uuid4())[:8]
        condo_data = {
            "name": f"TEST_Condominio_{unique_id}",
            "address": "Calle Test 123, Ciudad",
            "contact_email": f"test_{unique_id}@genturix.com",
            "contact_phone": "+1234567890",
            "max_users": 50
        }
        
        response = requests.post(
            f"{BASE_URL}/api/condominiums",
            headers=self.headers,
            json=condo_data
        )
        
        assert response.status_code == 200, f"Create failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Response missing 'id'"
        assert data["name"] == condo_data["name"]
        assert data["address"] == condo_data["address"]
        assert data["contact_email"] == condo_data["contact_email"]
        assert data["max_users"] == 50
        assert data["current_users"] == 0
        assert data["is_active"] == True
        assert "modules" in data
        assert "price_per_user" in data
        assert data["price_per_user"] == 1.0  # $1 per user
        
        self.created_condo_id = data["id"]
        print(f"✓ Created condominium: {data['name']} (ID: {data['id']})")
        return data["id"]
    
    def test_list_condominiums(self):
        """GET /api/condominiums - List all condominiums"""
        response = requests.get(
            f"{BASE_URL}/api/condominiums",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"List failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Listed {len(data)} condominiums")
        
        # Verify structure of items
        if len(data) > 0:
            condo = data[0]
            assert "id" in condo
            assert "name" in condo
            assert "modules" in condo
    
    def test_get_condominium_billing(self):
        """GET /api/condominiums/{id}/billing - Get billing info"""
        # First create a condominium
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(
            f"{BASE_URL}/api/condominiums",
            headers=self.headers,
            json={
                "name": f"TEST_Billing_{unique_id}",
                "address": "Billing Test Address",
                "contact_email": f"billing_{unique_id}@test.com",
                "contact_phone": "+1111111111",
                "max_users": 100
            }
        )
        assert create_response.status_code == 200
        condo_id = create_response.json()["id"]
        
        # Get billing
        response = requests.get(
            f"{BASE_URL}/api/condominiums/{condo_id}/billing",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Billing failed: {response.text}"
        data = response.json()
        
        # Verify billing structure
        assert data["condominium_id"] == condo_id
        assert "active_users" in data
        assert "price_per_user" in data
        assert data["price_per_user"] == 1.0  # $1 per user
        assert "monthly_cost_usd" in data
        assert data["billing_cycle"] == "monthly"
        assert data["currency"] == "USD"
        
        print(f"✓ Billing info: {data['active_users']} users × ${data['price_per_user']} = ${data['monthly_cost_usd']}/month")
    
    def test_update_module_config(self):
        """PATCH /api/condominiums/{id}/modules/{module} - Enable/disable modules"""
        # First create a condominium
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(
            f"{BASE_URL}/api/condominiums",
            headers=self.headers,
            json={
                "name": f"TEST_Modules_{unique_id}",
                "address": "Module Test Address",
                "contact_email": f"modules_{unique_id}@test.com",
                "contact_phone": "+2222222222",
                "max_users": 25
            }
        )
        assert create_response.status_code == 200
        condo_id = create_response.json()["id"]
        
        # Disable school module
        response = requests.patch(
            f"{BASE_URL}/api/condominiums/{condo_id}/modules/school",
            headers=self.headers,
            params={"enabled": False}
        )
        
        assert response.status_code == 200, f"Module update failed: {response.text}"
        data = response.json()
        assert "message" in data
        assert "disabled" in data["message"].lower() or "school" in data["message"].lower()
        print(f"✓ Module update: {data['message']}")
        
        # Enable school module
        response = requests.patch(
            f"{BASE_URL}/api/condominiums/{condo_id}/modules/school",
            headers=self.headers,
            params={"enabled": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data["message"].lower() or "school" in data["message"].lower()
        print(f"✓ Module re-enabled: {data['message']}")
    
    def test_invalid_module_returns_error(self):
        """PATCH with invalid module name should return 400"""
        # First create a condominium
        unique_id = str(uuid.uuid4())[:8]
        create_response = requests.post(
            f"{BASE_URL}/api/condominiums",
            headers=self.headers,
            json={
                "name": f"TEST_InvalidModule_{unique_id}",
                "address": "Invalid Module Test",
                "contact_email": f"invalid_{unique_id}@test.com",
                "contact_phone": "+3333333333",
                "max_users": 10
            }
        )
        assert create_response.status_code == 200
        condo_id = create_response.json()["id"]
        
        # Try invalid module
        response = requests.patch(
            f"{BASE_URL}/api/condominiums/{condo_id}/modules/invalid_module",
            headers=self.headers,
            params={"enabled": True}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Invalid module correctly returns 400 error")


class TestRRHHModule:
    """Test RRHH (HR) Module endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_get_guards(self):
        """GET /api/hr/guards - List all guards"""
        response = requests.get(
            f"{BASE_URL}/api/hr/guards",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get guards failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} guards")
        
        if len(data) > 0:
            guard = data[0]
            assert "id" in guard
            assert "user_name" in guard
            assert "badge_number" in guard
            assert "is_active" in guard
    
    def test_get_shifts(self):
        """GET /api/hr/shifts - List all shifts"""
        response = requests.get(
            f"{BASE_URL}/api/hr/shifts",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get shifts failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} shifts")
        
        if len(data) > 0:
            shift = data[0]
            assert "id" in shift
            assert "guard_id" in shift
            assert "start_time" in shift
            assert "end_time" in shift
            assert "location" in shift
    
    def test_get_payroll(self):
        """GET /api/hr/payroll - Get payroll data"""
        response = requests.get(
            f"{BASE_URL}/api/hr/payroll",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get payroll failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Payroll data for {len(data)} employees")
        
        if len(data) > 0:
            payroll = data[0]
            assert "guard_id" in payroll
            assert "guard_name" in payroll
            assert "hourly_rate" in payroll
            assert "total_hours" in payroll
            assert "total_pay" in payroll


class TestPanicButtonTypes:
    """Test panic button with 3 emergency types"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get resident token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_panic_medical_emergency(self):
        """POST /api/security/panic - Medical emergency (RED)"""
        response = requests.post(
            f"{BASE_URL}/api/security/panic",
            headers=self.headers,
            json={
                "panic_type": "emergencia_medica",
                "location": "TEST_Edificio A - Piso 5",
                "latitude": 19.4326,
                "longitude": -99.1332,
                "description": "TEST - Emergencia médica simulada"
            }
        )
        
        assert response.status_code == 200, f"Panic failed: {response.text}"
        data = response.json()
        
        assert "event_id" in data
        assert data["panic_type"] == "emergencia_medica"
        assert "notified_guards" in data
        print(f"✓ Medical emergency sent, {data['notified_guards']} guards notified")
    
    def test_panic_suspicious_activity(self):
        """POST /api/security/panic - Suspicious activity (AMBER)"""
        response = requests.post(
            f"{BASE_URL}/api/security/panic",
            headers=self.headers,
            json={
                "panic_type": "actividad_sospechosa",
                "location": "TEST_Estacionamiento Norte",
                "latitude": 19.4327,
                "longitude": -99.1333,
                "description": "TEST - Actividad sospechosa simulada"
            }
        )
        
        assert response.status_code == 200, f"Panic failed: {response.text}"
        data = response.json()
        
        assert data["panic_type"] == "actividad_sospechosa"
        print(f"✓ Suspicious activity alert sent, {data['notified_guards']} guards notified")
    
    def test_panic_general_emergency(self):
        """POST /api/security/panic - General emergency (ORANGE)"""
        response = requests.post(
            f"{BASE_URL}/api/security/panic",
            headers=self.headers,
            json={
                "panic_type": "emergencia_general",
                "location": "TEST_Área común",
                "latitude": 19.4328,
                "longitude": -99.1334,
                "description": "TEST - Emergencia general simulada"
            }
        )
        
        assert response.status_code == 200, f"Panic failed: {response.text}"
        data = response.json()
        
        assert data["panic_type"] == "emergencia_general"
        print(f"✓ General emergency sent, {data['notified_guards']} guards notified")
    
    def test_get_panic_events_as_guard(self):
        """GET /api/security/panic-events - Guards can see panic events"""
        # Login as guard
        guard_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        assert guard_response.status_code == 200
        guard_token = guard_response.json()["access_token"]
        
        response = requests.get(
            f"{BASE_URL}/api/security/panic-events",
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        
        assert response.status_code == 200, f"Get events failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Guard can view {len(data)} panic events")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
