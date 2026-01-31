"""
GENTURIX - Onboarding Wizard Tests
Tests for Super Admin Onboarding Wizard feature:
- GET /api/super-admin/onboarding/timezones
- POST /api/super-admin/onboarding/create-condominium
- Rollback on failure
- Admin credentials generation
- Module configuration
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN_EMAIL = "superadmin@genturix.com"
SUPER_ADMIN_PASSWORD = "SuperAdmin123!"
REGULAR_ADMIN_EMAIL = "admin@genturix.com"
REGULAR_ADMIN_PASSWORD = "Admin123!"


@pytest.fixture(scope="module")
def super_admin_token():
    """Get SuperAdmin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPER_ADMIN_EMAIL,
        "password": SUPER_ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"SuperAdmin login failed: {response.status_code}")
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def regular_admin_token():
    """Get regular Admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": REGULAR_ADMIN_EMAIL,
        "password": REGULAR_ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.status_code}")
    return response.json()["access_token"]


class TestOnboardingTimezones:
    """Tests for GET /api/super-admin/onboarding/timezones"""
    
    def test_get_timezones_success(self, super_admin_token):
        """SuperAdmin can get list of timezones"""
        response = requests.get(
            f"{BASE_URL}/api/super-admin/onboarding/timezones",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "timezones" in data
        assert isinstance(data["timezones"], list)
        assert len(data["timezones"]) > 0
        
        # Verify timezone structure
        first_tz = data["timezones"][0]
        assert "value" in first_tz
        assert "label" in first_tz
        assert "offset" in first_tz
        
        # Verify expected timezones are present
        tz_values = [tz["value"] for tz in data["timezones"]]
        assert "America/Mexico_City" in tz_values
        assert "America/Bogota" in tz_values
        assert "America/Lima" in tz_values
        print(f"✓ Got {len(data['timezones'])} timezones")
    
    def test_get_timezones_regular_admin_forbidden(self, regular_admin_token):
        """Regular Admin cannot access timezones endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/super-admin/onboarding/timezones",
            headers={"Authorization": f"Bearer {regular_admin_token}"}
        )
        
        assert response.status_code == 403
        print("✓ Regular admin correctly forbidden from timezones endpoint")
    
    def test_get_timezones_unauthenticated(self):
        """Unauthenticated request fails"""
        response = requests.get(f"{BASE_URL}/api/super-admin/onboarding/timezones")
        
        assert response.status_code in [401, 403]
        print("✓ Unauthenticated request correctly rejected")


class TestOnboardingCreateCondominium:
    """Tests for POST /api/super-admin/onboarding/create-condominium"""
    
    def test_create_condominium_success(self, super_admin_token):
        """SuperAdmin can create a new condominium with admin and modules"""
        unique_id = str(uuid.uuid4())[:8]
        
        wizard_data = {
            "condominium": {
                "name": f"TEST_Residencial Wizard {unique_id}",
                "address": "Av. Test #123, Ciudad Test",
                "country": "Mexico",
                "timezone": "America/Mexico_City"
            },
            "admin": {
                "full_name": f"Admin Test {unique_id}",
                "email": f"admin.test.{unique_id}@demo.com"
            },
            "modules": {
                "security": True,
                "hr": True,
                "reservations": True,
                "school": False,
                "payments": False,
                "cctv": False
            },
            "areas": [
                {
                    "name": "Piscina Test",
                    "capacity": 30,
                    "requires_approval": False
                },
                {
                    "name": "Gimnasio Test",
                    "capacity": 20,
                    "requires_approval": True
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json=wizard_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify success response
        assert data["success"] == True
        assert "condominium" in data
        assert "admin_credentials" in data
        assert "modules_enabled" in data
        assert "areas_created" in data
        
        # Verify condominium data
        assert data["condominium"]["name"] == wizard_data["condominium"]["name"]
        assert data["condominium"]["address"] == wizard_data["condominium"]["address"]
        assert "id" in data["condominium"]
        
        # Verify admin credentials returned
        assert data["admin_credentials"]["email"] == wizard_data["admin"]["email"]
        assert "password" in data["admin_credentials"]
        assert len(data["admin_credentials"]["password"]) >= 8
        assert "warning" in data["admin_credentials"]
        
        # Verify modules enabled (security always enabled)
        assert "security" in data["modules_enabled"]
        assert "hr" in data["modules_enabled"]
        assert "reservations" in data["modules_enabled"]
        
        # Verify areas created
        assert len(data["areas_created"]) == 2
        area_names = [a["name"] for a in data["areas_created"]]
        assert "Piscina Test" in area_names
        assert "Gimnasio Test" in area_names
        
        print(f"✓ Created condominium: {data['condominium']['name']}")
        print(f"✓ Admin email: {data['admin_credentials']['email']}")
        print(f"✓ Password generated: {data['admin_credentials']['password'][:4]}****")
        print(f"✓ Modules enabled: {data['modules_enabled']}")
        print(f"✓ Areas created: {len(data['areas_created'])}")
        
        # Store for cleanup
        return data
    
    def test_admin_password_reset_required(self, super_admin_token):
        """Verify created admin has password_reset_required=true"""
        unique_id = str(uuid.uuid4())[:8]
        
        wizard_data = {
            "condominium": {
                "name": f"TEST_Condo PwdReset {unique_id}",
                "address": "Av. Password Reset #456",
                "country": "Colombia",
                "timezone": "America/Bogota"
            },
            "admin": {
                "full_name": f"Admin PwdReset {unique_id}",
                "email": f"admin.pwdreset.{unique_id}@demo.com"
            },
            "modules": {
                "security": True,
                "hr": False,
                "reservations": False,
                "school": False,
                "payments": False,
                "cctv": False
            },
            "areas": []
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json=wizard_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Login with the new admin credentials
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": data["admin_credentials"]["email"],
            "password": data["admin_credentials"]["password"]
        })
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        
        # Verify password_reset_required flag
        assert login_data["password_reset_required"] == True
        assert login_data["user"]["password_reset_required"] == True
        
        print(f"✓ Admin login successful with generated password")
        print(f"✓ password_reset_required = {login_data['password_reset_required']}")
    
    def test_security_module_always_enabled(self, super_admin_token):
        """Security module is always enabled even if set to false"""
        unique_id = str(uuid.uuid4())[:8]
        
        wizard_data = {
            "condominium": {
                "name": f"TEST_Condo Security {unique_id}",
                "address": "Av. Security Test #789",
                "country": "Peru",
                "timezone": "America/Lima"
            },
            "admin": {
                "full_name": f"Admin Security {unique_id}",
                "email": f"admin.security.{unique_id}@demo.com"
            },
            "modules": {
                "security": False,  # Try to disable - should still be enabled
                "hr": False,
                "reservations": False,
                "school": False,
                "payments": False,
                "cctv": False
            },
            "areas": []
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json=wizard_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Security should always be in enabled modules
        assert "security" in data["modules_enabled"]
        print(f"✓ Security module always enabled: {data['modules_enabled']}")
    
    def test_rollback_on_duplicate_email(self, super_admin_token):
        """Rollback if admin email already exists"""
        # Use an email that already exists
        existing_email = "admin@genturix.com"
        unique_id = str(uuid.uuid4())[:8]
        
        wizard_data = {
            "condominium": {
                "name": f"TEST_Condo Rollback {unique_id}",
                "address": "Av. Rollback Test #999",
                "country": "Argentina",
                "timezone": "America/Buenos_Aires"
            },
            "admin": {
                "full_name": "Admin Duplicate",
                "email": existing_email  # This email already exists
            },
            "modules": {
                "security": True,
                "hr": False,
                "reservations": False,
                "school": False,
                "payments": False,
                "cctv": False
            },
            "areas": []
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json=wizard_data
        )
        
        # Should fail with 400 (email already registered)
        assert response.status_code == 400
        data = response.json()
        assert "email" in data["detail"].lower() or "registrado" in data["detail"].lower()
        
        # Verify condominium was NOT created (rollback)
        condos_response = requests.get(
            f"{BASE_URL}/api/condominiums",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        condos = condos_response.json()
        condo_names = [c["name"] for c in condos]
        assert f"TEST_Condo Rollback {unique_id}" not in condo_names
        
        print(f"✓ Rollback successful - duplicate email rejected")
        print(f"✓ Condominium was not created")
    
    def test_rollback_on_duplicate_condo_name(self, super_admin_token):
        """Rollback if condominium name already exists"""
        # First create a condominium
        unique_id = str(uuid.uuid4())[:8]
        condo_name = f"TEST_Condo Duplicate Name {unique_id}"
        
        wizard_data_1 = {
            "condominium": {
                "name": condo_name,
                "address": "Av. First #111",
                "country": "Chile",
                "timezone": "America/Santiago"
            },
            "admin": {
                "full_name": f"Admin First {unique_id}",
                "email": f"admin.first.{unique_id}@demo.com"
            },
            "modules": {"security": True, "hr": False, "reservations": False, "school": False, "payments": False, "cctv": False},
            "areas": []
        }
        
        response_1 = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json=wizard_data_1
        )
        assert response_1.status_code == 200
        
        # Try to create another with same name
        wizard_data_2 = {
            "condominium": {
                "name": condo_name,  # Same name
                "address": "Av. Second #222",
                "country": "Chile",
                "timezone": "America/Santiago"
            },
            "admin": {
                "full_name": f"Admin Second {unique_id}",
                "email": f"admin.second.{unique_id}@demo.com"
            },
            "modules": {"security": True, "hr": False, "reservations": False, "school": False, "payments": False, "cctv": False},
            "areas": []
        }
        
        response_2 = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json=wizard_data_2
        )
        
        # Should fail with 400 (name already exists)
        assert response_2.status_code == 400
        data = response_2.json()
        assert "nombre" in data["detail"].lower() or "existe" in data["detail"].lower()
        
        print(f"✓ Duplicate condominium name correctly rejected")
    
    def test_regular_admin_cannot_create_condominium(self, regular_admin_token):
        """Regular Admin cannot access onboarding endpoint"""
        wizard_data = {
            "condominium": {
                "name": "TEST_Unauthorized Condo",
                "address": "Av. Unauthorized #000",
                "country": "Mexico",
                "timezone": "America/Mexico_City"
            },
            "admin": {
                "full_name": "Admin Unauthorized",
                "email": "admin.unauthorized@demo.com"
            },
            "modules": {"security": True, "hr": False, "reservations": False, "school": False, "payments": False, "cctv": False},
            "areas": []
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers={"Authorization": f"Bearer {regular_admin_token}"},
            json=wizard_data
        )
        
        assert response.status_code == 403
        print("✓ Regular admin correctly forbidden from creating condominiums")
    
    def test_create_condominium_without_areas(self, super_admin_token):
        """Can create condominium without areas (reservations disabled)"""
        unique_id = str(uuid.uuid4())[:8]
        
        wizard_data = {
            "condominium": {
                "name": f"TEST_Condo NoAreas {unique_id}",
                "address": "Av. No Areas #333",
                "country": "Venezuela",
                "timezone": "America/Caracas"
            },
            "admin": {
                "full_name": f"Admin NoAreas {unique_id}",
                "email": f"admin.noareas.{unique_id}@demo.com"
            },
            "modules": {
                "security": True,
                "hr": True,
                "reservations": False,  # Disabled
                "school": False,
                "payments": False,
                "cctv": False
            },
            "areas": []  # No areas
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json=wizard_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert len(data["areas_created"]) == 0
        assert "reservations" not in data["modules_enabled"]
        
        print(f"✓ Created condominium without areas")
        print(f"✓ Modules enabled: {data['modules_enabled']}")
    
    def test_areas_stored_in_reservation_areas_collection(self, super_admin_token):
        """Verify areas are stored in reservation_areas collection"""
        unique_id = str(uuid.uuid4())[:8]
        
        wizard_data = {
            "condominium": {
                "name": f"TEST_Condo AreasCheck {unique_id}",
                "address": "Av. Areas Check #444",
                "country": "Brasil",
                "timezone": "America/Sao_Paulo"
            },
            "admin": {
                "full_name": f"Admin AreasCheck {unique_id}",
                "email": f"admin.areascheck.{unique_id}@demo.com"
            },
            "modules": {
                "security": True,
                "hr": False,
                "reservations": True,
                "school": False,
                "payments": False,
                "cctv": False
            },
            "areas": [
                {"name": "Salón de Eventos", "capacity": 50, "requires_approval": True},
                {"name": "Cancha de Tenis", "capacity": 4, "requires_approval": False}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json=wizard_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Login as the new admin to check areas
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": data["admin_credentials"]["email"],
            "password": data["admin_credentials"]["password"]
        })
        assert login_response.status_code == 200
        admin_token = login_response.json()["access_token"]
        
        # Get areas for this condominium
        areas_response = requests.get(
            f"{BASE_URL}/api/reservations/areas",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert areas_response.status_code == 200
        areas = areas_response.json()
        
        # Verify areas were created
        area_names = [a["name"] for a in areas]
        assert "Salón de Eventos" in area_names
        assert "Cancha de Tenis" in area_names
        
        print(f"✓ Areas stored in reservation_areas collection")
        print(f"✓ Found areas: {area_names}")
    
    def test_validation_short_condo_name(self, super_admin_token):
        """Validation: Condominium name too short"""
        wizard_data = {
            "condominium": {
                "name": "A",  # Too short (min 2)
                "address": "Av. Valid Address #123",
                "country": "Mexico",
                "timezone": "America/Mexico_City"
            },
            "admin": {
                "full_name": "Admin Valid",
                "email": "admin.valid@demo.com"
            },
            "modules": {"security": True, "hr": False, "reservations": False, "school": False, "payments": False, "cctv": False},
            "areas": []
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json=wizard_data
        )
        
        assert response.status_code == 422  # Validation error
        print("✓ Short condominium name correctly rejected")
    
    def test_validation_invalid_email(self, super_admin_token):
        """Validation: Invalid admin email format"""
        unique_id = str(uuid.uuid4())[:8]
        
        wizard_data = {
            "condominium": {
                "name": f"TEST_Condo InvalidEmail {unique_id}",
                "address": "Av. Valid Address #123",
                "country": "Mexico",
                "timezone": "America/Mexico_City"
            },
            "admin": {
                "full_name": "Admin Valid",
                "email": "not-an-email"  # Invalid email
            },
            "modules": {"security": True, "hr": False, "reservations": False, "school": False, "payments": False, "cctv": False},
            "areas": []
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json=wizard_data
        )
        
        assert response.status_code == 422  # Validation error
        print("✓ Invalid email format correctly rejected")


class TestOnboardingIntegration:
    """Integration tests for the complete onboarding flow"""
    
    def test_full_onboarding_flow(self, super_admin_token):
        """Complete onboarding flow: create condo, login as admin, verify modules"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Step 1: Create condominium via wizard
        wizard_data = {
            "condominium": {
                "name": f"TEST_Full Flow Condo {unique_id}",
                "address": "Av. Full Flow #555",
                "country": "España",
                "timezone": "Europe/Madrid"
            },
            "admin": {
                "full_name": f"Admin Full Flow {unique_id}",
                "email": f"admin.fullflow.{unique_id}@demo.com"
            },
            "modules": {
                "security": True,
                "hr": True,
                "reservations": True,
                "school": True,
                "payments": True,
                "cctv": False
            },
            "areas": [
                {"name": "Piscina Olímpica", "capacity": 100, "requires_approval": False}
            ]
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json=wizard_data
        )
        
        assert create_response.status_code == 200
        create_data = create_response.json()
        
        # Step 2: Login as the new admin
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": create_data["admin_credentials"]["email"],
            "password": create_data["admin_credentials"]["password"]
        })
        
        assert login_response.status_code == 200
        login_data = login_response.json()
        admin_token = login_data["access_token"]
        
        # Verify password reset required
        assert login_data["password_reset_required"] == True
        
        # Step 3: Get admin profile
        profile_response = requests.get(
            f"{BASE_URL}/api/profile",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        
        # Verify admin is assigned to the correct condominium
        assert profile_data["condominium_id"] == create_data["condominium"]["id"]
        assert "Administrador" in profile_data["roles"]
        
        # Step 4: Verify condominium modules
        condo_response = requests.get(
            f"{BASE_URL}/api/condominiums/{create_data['condominium']['id']}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        
        assert condo_response.status_code == 200
        condo_data = condo_response.json()
        
        # Verify modules configuration
        assert condo_data["modules"]["security"] == True
        assert condo_data["modules"]["hr"] == True
        assert condo_data["modules"]["reservations"] == True
        
        print(f"✓ Full onboarding flow completed successfully")
        print(f"✓ Condominium: {condo_data['name']}")
        print(f"✓ Admin: {profile_data['full_name']}")
        print(f"✓ Modules: {[k for k, v in condo_data['modules'].items() if v]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
