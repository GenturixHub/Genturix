"""
Test Visitor Type Authorization Feature for Residents
Tests the new visitor_type, company, service_type fields in visitor authorizations
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
RESIDENT_EMAIL = "residente@genturix.com"
RESIDENT_PASSWORD = "Resi123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"


class TestVisitorTypeAuthorization:
    """Test visitor type fields in resident authorizations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_auth_ids = []
        yield
        # Cleanup created authorizations
        for auth_id in self.created_auth_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/authorizations/{auth_id}")
            except:
                pass
    
    def login_as_resident(self):
        """Login as resident and return token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        token = response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        return token
    
    def login_as_guard(self):
        """Login as guard and return token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        token = response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        return token
    
    # ==================== BACKEND API TESTS ====================
    
    def test_create_delivery_authorization(self):
        """Test creating a Delivery type authorization with company"""
        self.login_as_resident()
        
        payload = {
            "visitor_name": "TEST_Repartidor_Juan",
            "visitor_type": "delivery",
            "company": "Rappi",
            "service_type": "Comida",
            "authorization_type": "temporary",
            "valid_from": "2026-02-02",
            "valid_to": "2026-02-02"
        }
        
        response = self.session.post(f"{BASE_URL}/api/authorizations", json=payload)
        assert response.status_code in [200, 201], f"Failed to create delivery auth: {response.text}"
        
        data = response.json()
        self.created_auth_ids.append(data["id"])
        
        # Verify visitor_type, company, service_type are saved
        assert data["visitor_type"] == "delivery", f"Expected visitor_type='delivery', got '{data.get('visitor_type')}'"
        assert data["company"] == "Rappi", f"Expected company='Rappi', got '{data.get('company')}'"
        assert data["service_type"] == "Comida", f"Expected service_type='Comida', got '{data.get('service_type')}'"
        assert data["visitor_name"] == "TEST_Repartidor_Juan"
        print(f"✓ Delivery authorization created: {data['id']}")
    
    def test_create_maintenance_authorization(self):
        """Test creating a Maintenance type authorization"""
        self.login_as_resident()
        
        payload = {
            "visitor_name": "TEST_Tecnico_Pedro",
            "visitor_type": "maintenance",
            "company": "Plomeros Express",
            "service_type": "Plomería",
            "authorization_type": "temporary",
            "valid_from": "2026-02-02",
            "valid_to": "2026-02-03"
        }
        
        response = self.session.post(f"{BASE_URL}/api/authorizations", json=payload)
        assert response.status_code in [200, 201], f"Failed to create maintenance auth: {response.text}"
        
        data = response.json()
        self.created_auth_ids.append(data["id"])
        
        assert data["visitor_type"] == "maintenance"
        assert data["company"] == "Plomeros Express"
        assert data["service_type"] == "Plomería"
        print(f"✓ Maintenance authorization created: {data['id']}")
    
    def test_create_technical_authorization(self):
        """Test creating a Technical Service type authorization"""
        self.login_as_resident()
        
        payload = {
            "visitor_name": "TEST_Tecnico_Internet",
            "visitor_type": "technical",
            "company": "Claro",
            "service_type": "Internet/Cable",
            "authorization_type": "temporary",
            "valid_from": "2026-02-02",
            "valid_to": "2026-02-02"
        }
        
        response = self.session.post(f"{BASE_URL}/api/authorizations", json=payload)
        assert response.status_code in [200, 201], f"Failed to create technical auth: {response.text}"
        
        data = response.json()
        self.created_auth_ids.append(data["id"])
        
        assert data["visitor_type"] == "technical"
        assert data["company"] == "Claro"
        assert data["service_type"] == "Internet/Cable"
        print(f"✓ Technical authorization created: {data['id']}")
    
    def test_create_cleaning_authorization(self):
        """Test creating a Cleaning type authorization"""
        self.login_as_resident()
        
        payload = {
            "visitor_name": "TEST_Limpieza_Maria",
            "visitor_type": "cleaning",
            "company": "Limpieza Total",
            "service_type": "Apartamento",
            "authorization_type": "recurring",
            "allowed_days": ["Lunes", "Miércoles", "Viernes"]
        }
        
        response = self.session.post(f"{BASE_URL}/api/authorizations", json=payload)
        assert response.status_code in [200, 201], f"Failed to create cleaning auth: {response.text}"
        
        data = response.json()
        self.created_auth_ids.append(data["id"])
        
        assert data["visitor_type"] == "cleaning"
        assert data["company"] == "Limpieza Total"
        assert data["service_type"] == "Apartamento"
        assert data["authorization_type"] == "recurring"
        print(f"✓ Cleaning authorization created: {data['id']}")
    
    def test_create_other_authorization(self):
        """Test creating an 'Other' type authorization"""
        self.login_as_resident()
        
        payload = {
            "visitor_name": "TEST_Otro_Servicio",
            "visitor_type": "other",
            "company": "Empresa XYZ",
            "service_type": "Otro",
            "authorization_type": "temporary",
            "valid_from": "2026-02-02",
            "valid_to": "2026-02-02"
        }
        
        response = self.session.post(f"{BASE_URL}/api/authorizations", json=payload)
        assert response.status_code in [200, 201], f"Failed to create other auth: {response.text}"
        
        data = response.json()
        self.created_auth_ids.append(data["id"])
        
        assert data["visitor_type"] == "other"
        assert data["company"] == "Empresa XYZ"
        print(f"✓ Other authorization created: {data['id']}")
    
    def test_create_visitor_authorization_default_type(self):
        """Test that default visitor_type is 'visitor' when not specified"""
        self.login_as_resident()
        
        payload = {
            "visitor_name": "TEST_Visitante_Normal",
            "authorization_type": "temporary",
            "valid_from": "2026-02-02",
            "valid_to": "2026-02-02"
        }
        
        response = self.session.post(f"{BASE_URL}/api/authorizations", json=payload)
        assert response.status_code in [200, 201], f"Failed to create visitor auth: {response.text}"
        
        data = response.json()
        self.created_auth_ids.append(data["id"])
        
        # Default should be 'visitor'
        assert data["visitor_type"] == "visitor", f"Expected default visitor_type='visitor', got '{data.get('visitor_type')}'"
        print(f"✓ Default visitor type is 'visitor': {data['id']}")
    
    def test_get_authorization_returns_visitor_type_fields(self):
        """Test that GET authorization returns visitor_type, company, service_type"""
        self.login_as_resident()
        
        # Create a delivery authorization
        payload = {
            "visitor_name": "TEST_Get_Delivery",
            "visitor_type": "delivery",
            "company": "Uber Eats",
            "service_type": "Paquete",
            "authorization_type": "temporary",
            "valid_from": "2026-02-02",
            "valid_to": "2026-02-02"
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/authorizations", json=payload)
        assert create_response.status_code == 201
        auth_id = create_response.json()["id"]
        self.created_auth_ids.append(auth_id)
        
        # Get my authorizations
        get_response = self.session.get(f"{BASE_URL}/api/authorizations/my")
        assert get_response.status_code == 200
        
        authorizations = get_response.json()
        created_auth = next((a for a in authorizations if a["id"] == auth_id), None)
        
        assert created_auth is not None, "Created authorization not found in list"
        assert created_auth["visitor_type"] == "delivery"
        assert created_auth["company"] == "Uber Eats"
        assert created_auth["service_type"] == "Paquete"
        print(f"✓ GET authorization returns visitor_type fields correctly")
    
    def test_update_authorization_visitor_type(self):
        """Test updating visitor_type, company, service_type fields"""
        self.login_as_resident()
        
        # Create initial authorization
        payload = {
            "visitor_name": "TEST_Update_Auth",
            "visitor_type": "delivery",
            "company": "Rappi",
            "service_type": "Comida",
            "authorization_type": "temporary",
            "valid_from": "2026-02-02",
            "valid_to": "2026-02-02"
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/authorizations", json=payload)
        assert create_response.status_code == 201
        auth_id = create_response.json()["id"]
        self.created_auth_ids.append(auth_id)
        
        # Update to maintenance type
        update_payload = {
            "visitor_type": "maintenance",
            "company": "Electricistas SA",
            "service_type": "Electricidad"
        }
        
        update_response = self.session.put(f"{BASE_URL}/api/authorizations/{auth_id}", json=update_payload)
        assert update_response.status_code == 200, f"Failed to update auth: {update_response.text}"
        
        updated_data = update_response.json()
        assert updated_data["visitor_type"] == "maintenance"
        assert updated_data["company"] == "Electricistas SA"
        assert updated_data["service_type"] == "Electricidad"
        print(f"✓ Authorization updated with new visitor_type fields")


class TestGuardViewsVisitorTypeAuthorizations:
    """Test that guards can see visitor_type fields in authorizations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.created_auth_ids = []
        yield
        # Cleanup
        self.login_as_resident()
        for auth_id in self.created_auth_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/authorizations/{auth_id}")
            except:
                pass
    
    def login_as_resident(self):
        """Login as resident"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        return response.status_code == 200
    
    def login_as_guard(self):
        """Login as guard"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        return response.status_code == 200
    
    def test_guard_sees_visitor_type_in_authorizations(self):
        """Test that guard can see visitor_type fields when viewing authorizations"""
        # Create authorization as resident
        self.login_as_resident()
        
        payload = {
            "visitor_name": "TEST_Guard_View_Delivery",
            "visitor_type": "delivery",
            "company": "DHL",
            "service_type": "Documentos",
            "authorization_type": "temporary",
            "valid_from": "2026-02-02",
            "valid_to": "2026-02-05"
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/authorizations", json=payload)
        assert create_response.status_code == 201
        auth_id = create_response.json()["id"]
        self.created_auth_ids.append(auth_id)
        
        # Login as guard and view authorizations
        self.login_as_guard()
        
        # Get all authorizations (guard view)
        guard_response = self.session.get(f"{BASE_URL}/api/authorizations")
        assert guard_response.status_code == 200
        
        authorizations = guard_response.json()
        created_auth = next((a for a in authorizations if a["id"] == auth_id), None)
        
        assert created_auth is not None, "Authorization not visible to guard"
        assert created_auth["visitor_type"] == "delivery"
        assert created_auth["company"] == "DHL"
        assert created_auth["service_type"] == "Documentos"
        print(f"✓ Guard can see visitor_type fields in authorizations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
