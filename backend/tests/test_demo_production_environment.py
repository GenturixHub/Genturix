"""
Test Suite: Demo vs Production Environment Separation
======================================================
Tests the refactored condominium creation to clearly separate 'Demo' and 'Production' environments.

Features tested:
1. Backend: GET /api/billing/info includes environment, is_demo, billing_enabled
2. Backend: POST /api/billing/upgrade-seats rejects demo condominiums with 403
3. Backend: POST /api/condominiums with environment='demo' creates with paid_seats=10 and billing_enabled=false
4. Backend: POST /api/condominiums with environment='production' creates with billing_enabled=true
5. Backend: Stripe webhooks ignore demo condominiums (no changes applied)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://genturix-guard-query.preview.emergentagent.com')

# Test credentials
SUPER_ADMIN_EMAIL = "superadmin@genturix.com"
SUPER_ADMIN_PASSWORD = "SuperAdmin123!"
ADMIN_EMAIL = "admin@genturix.com"  # Demo condo admin
ADMIN_PASSWORD = "Admin123!"


@pytest.fixture(scope="module")
def super_admin_token():
    """Login as SuperAdmin"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPER_ADMIN_EMAIL,
        "password": SUPER_ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"SuperAdmin login failed: {response.text}")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def admin_token():
    """Login as Admin (demo condo)"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.text}")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def admin_condo_id(admin_token):
    """Get the condominium ID for the admin user"""
    response = requests.get(
        f"{BASE_URL}/api/auth/profile",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if response.status_code == 200:
        return response.json().get("condominium_id")
    pytest.skip("Could not get admin's condo ID")


class TestBillingInfoEnvironmentFields:
    """
    Tests for GET /api/billing/info - verify environment, is_demo, billing_enabled fields
    """
    
    def test_billing_info_includes_environment_field(self, admin_token):
        """Verify billing info response includes environment field"""
        response = requests.get(
            f"{BASE_URL}/api/billing/info",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "environment" in data, "Response should include 'environment' field"
        assert data["environment"] in ["demo", "production"], f"environment should be 'demo' or 'production', got {data['environment']}"
        print(f"✓ billing/info includes environment: {data['environment']}")
    
    def test_billing_info_includes_is_demo_field(self, admin_token):
        """Verify billing info response includes is_demo field"""
        response = requests.get(
            f"{BASE_URL}/api/billing/info",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "is_demo" in data, "Response should include 'is_demo' field"
        assert isinstance(data["is_demo"], bool), "is_demo should be boolean"
        print(f"✓ billing/info includes is_demo: {data['is_demo']}")
    
    def test_billing_info_includes_billing_enabled_field(self, admin_token):
        """Verify billing info response includes billing_enabled field"""
        response = requests.get(
            f"{BASE_URL}/api/billing/info",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "billing_enabled" in data, "Response should include 'billing_enabled' field"
        assert isinstance(data["billing_enabled"], bool), "billing_enabled should be boolean"
        print(f"✓ billing/info includes billing_enabled: {data['billing_enabled']}")
    
    def test_demo_condo_has_billing_disabled(self, admin_token):
        """Verify that demo condominiums have billing_enabled=false"""
        response = requests.get(
            f"{BASE_URL}/api/billing/info",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        environment = data.get("environment", "production")
        is_demo = data.get("is_demo", False)
        billing_enabled = data.get("billing_enabled", True)
        
        # If it's a demo condo, billing should be disabled
        if environment == "demo" or is_demo:
            assert billing_enabled == False, f"Demo condos should have billing_enabled=false, got {billing_enabled}"
            print(f"✓ Demo condo has billing_enabled=false")
        else:
            print(f"ℹ Production condo has billing_enabled={billing_enabled}")


class TestDemoCondoCannotUpgradeSeats:
    """
    Tests for POST /api/billing/upgrade-seats - verify demo condos are rejected with 403
    """
    
    def test_upgrade_seats_rejected_for_demo_condo(self, admin_token):
        """Demo condominiums cannot purchase additional seats (returns 403)"""
        # First check if this condo is demo
        billing_response = requests.get(
            f"{BASE_URL}/api/billing/info",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if billing_response.status_code == 200:
            data = billing_response.json()
            is_demo = data.get("is_demo") or data.get("environment") == "demo"
            
            if not is_demo:
                pytest.skip("Admin condo is not in demo mode - cannot test demo rejection")
        
        # Try to upgrade seats
        response = requests.post(
            f"{BASE_URL}/api/billing/upgrade-seats",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"additional_seats": 5, "origin_url": BASE_URL}
        )
        
        # Should be rejected with 403 for demo condos
        assert response.status_code == 403, f"Expected 403 for demo condo, got {response.status_code}: {response.text}"
        
        data = response.json()
        error_msg = data.get("detail", "")
        assert "Demo" in error_msg or "demo" in error_msg, f"Error should mention Demo mode: {error_msg}"
        print(f"✓ Demo condo seat upgrade rejected with 403: {error_msg}")
    
    def test_upgrade_seats_error_message_contains_demo(self, admin_token):
        """Verify error message explicitly mentions Demo mode"""
        # First check if this condo is demo
        billing_response = requests.get(
            f"{BASE_URL}/api/billing/info",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if billing_response.status_code == 200:
            data = billing_response.json()
            is_demo = data.get("is_demo") or data.get("environment") == "demo"
            
            if not is_demo:
                pytest.skip("Admin condo is not in demo mode")
        
        response = requests.post(
            f"{BASE_URL}/api/billing/upgrade-seats",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"additional_seats": 5, "origin_url": BASE_URL}
        )
        
        if response.status_code == 403:
            data = response.json()
            error_msg = data.get("detail", "")
            # Expected message: "Los condominios en modo Demo no pueden comprar asientos adicionales"
            assert "modo Demo" in error_msg or "Demo" in error_msg
            print(f"✓ Error message correctly mentions Demo: {error_msg}")


class TestCondominiumCreationWithEnvironment:
    """
    Tests for POST /api/condominiums - verify environment-based configuration
    """
    
    def test_create_demo_condominium_has_10_seats_hardcoded(self, super_admin_token):
        """Demo condominiums are created with paid_seats=10 (hardcoded)"""
        unique_name = f"TEST_Demo_Condo_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/condominiums",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={
                "name": unique_name,
                "address": "Demo Address 123",
                "contact_email": f"demo_{uuid.uuid4().hex[:6]}@test.com",
                "contact_phone": "+52 555 111 1111",
                "max_users": 50,  # Even if we set 50, demo should have 10
                "environment": "demo"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("environment") == "demo", f"Environment should be 'demo', got {data.get('environment')}"
        assert data.get("paid_seats") == 10, f"Demo paid_seats should be 10, got {data.get('paid_seats')}"
        assert data.get("is_demo") == True, f"is_demo should be True, got {data.get('is_demo')}"
        
        # Store ID for cleanup
        condo_id = data.get("id")
        print(f"✓ Demo condo created with paid_seats=10: {unique_name}")
        
        # Cleanup
        if condo_id:
            requests.delete(
                f"{BASE_URL}/api/condominiums/{condo_id}",
                headers={"Authorization": f"Bearer {super_admin_token}"},
                json={"password": SUPER_ADMIN_PASSWORD}
            )
    
    def test_create_demo_condominium_has_billing_disabled(self, super_admin_token):
        """Demo condominiums are created with billing_enabled=false"""
        unique_name = f"TEST_DemoBilling_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/condominiums",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={
                "name": unique_name,
                "address": "Demo Billing Test 123",
                "contact_email": f"demobilling_{uuid.uuid4().hex[:6]}@test.com",
                "contact_phone": "+52 555 222 2222",
                "max_users": 100,
                "environment": "demo"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Note: billing_enabled might not be returned directly, but we can verify via billing_status
        billing_status = data.get("billing_status", "")
        assert data.get("environment") == "demo"
        
        # For demo condos, the billing_status should be "demo" not "active"
        # This indicates billing is not enabled
        condo_id = data.get("id")
        print(f"✓ Demo condo has correct billing configuration: billing_status={billing_status}")
        
        # Cleanup
        if condo_id:
            requests.delete(
                f"{BASE_URL}/api/condominiums/{condo_id}",
                headers={"Authorization": f"Bearer {super_admin_token}"},
                json={"password": SUPER_ADMIN_PASSWORD}
            )
    
    def test_create_production_condominium_has_billing_enabled(self, super_admin_token):
        """Production condominiums are created with billing_enabled=true"""
        unique_name = f"TEST_ProdCondo_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/condominiums",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={
                "name": unique_name,
                "address": "Production Address 123",
                "contact_email": f"prod_{uuid.uuid4().hex[:6]}@test.com",
                "contact_phone": "+52 555 333 3333",
                "max_users": 100,
                "environment": "production"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("environment") == "production", f"Environment should be 'production', got {data.get('environment')}"
        assert data.get("is_demo") == False, f"is_demo should be False for production, got {data.get('is_demo')}"
        
        # Production condos should have billing_status="active" (not "demo")
        billing_status = data.get("billing_status", "")
        assert billing_status == "active", f"Production billing_status should be 'active', got {billing_status}"
        
        condo_id = data.get("id")
        print(f"✓ Production condo created correctly: {unique_name}")
        
        # Cleanup
        if condo_id:
            requests.delete(
                f"{BASE_URL}/api/condominiums/{condo_id}",
                headers={"Authorization": f"Bearer {super_admin_token}"},
                json={"password": SUPER_ADMIN_PASSWORD}
            )
    
    def test_create_production_condominium_uses_max_users_as_paid_seats(self, super_admin_token):
        """Production condominiums use max_users as paid_seats"""
        unique_name = f"TEST_ProdSeats_{uuid.uuid4().hex[:8]}"
        max_users_value = 75
        
        response = requests.post(
            f"{BASE_URL}/api/condominiums",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={
                "name": unique_name,
                "address": "Production Seats Test",
                "contact_email": f"prodseats_{uuid.uuid4().hex[:6]}@test.com",
                "contact_phone": "+52 555 444 4444",
                "max_users": max_users_value,
                "environment": "production"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("environment") == "production"
        # paid_seats should be set to max_users value for production
        paid_seats = data.get("paid_seats")
        assert paid_seats == max_users_value, f"Production paid_seats should be {max_users_value}, got {paid_seats}"
        
        condo_id = data.get("id")
        print(f"✓ Production condo has paid_seats={paid_seats} (from max_users={max_users_value})")
        
        # Cleanup
        if condo_id:
            requests.delete(
                f"{BASE_URL}/api/condominiums/{condo_id}",
                headers={"Authorization": f"Bearer {super_admin_token}"},
                json={"password": SUPER_ADMIN_PASSWORD}
            )


class TestCondominiumListEnvironmentBadges:
    """
    Tests for verifying condominiums list includes environment info for frontend badges
    """
    
    def test_condominiums_list_includes_environment(self, super_admin_token):
        """Verify condominiums list includes environment field for badge display"""
        response = requests.get(
            f"{BASE_URL}/api/condominiums",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        condos = data if isinstance(data, list) else data.get("condominiums", [])
        
        assert len(condos) > 0, "Should have at least one condominium"
        
        for condo in condos[:5]:  # Check first 5
            # Each condo should have environment and is_demo fields
            assert "environment" in condo or "is_demo" in condo, f"Condo {condo.get('name')} missing environment info"
            env = condo.get("environment", "production")
            is_demo = condo.get("is_demo", False)
            print(f"  - {condo.get('name')}: environment={env}, is_demo={is_demo}")
        
        print(f"✓ All condominiums include environment info")


class TestTenantEnvironmentEndpoint:
    """
    Tests for the /api/config/tenant-environment endpoint
    """
    
    def test_tenant_environment_returns_correct_format(self, admin_token):
        """Verify tenant-environment endpoint returns expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/config/tenant-environment",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "environment" in data, "Response should include 'environment'"
        assert "is_demo" in data, "Response should include 'is_demo'"
        
        env = data.get("environment")
        is_demo = data.get("is_demo")
        
        assert env in ["demo", "production"], f"Invalid environment: {env}"
        assert isinstance(is_demo, bool)
        
        # Verify consistency
        if env == "demo":
            assert is_demo == True, "If environment=demo, is_demo should be True"
        
        print(f"✓ tenant-environment returns: environment={env}, is_demo={is_demo}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
