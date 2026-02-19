"""
GENTURIX Pricing System Tests
Tests for: Global Pricing, Condominium Override Pricing, Dynamic Pricing in Payments
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "SuperAdmin123!"
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"

class TestPricingSystemSetup:
    """Setup and helper methods for pricing tests"""
    
    @pytest.fixture(scope="class")
    def superadmin_token(self):
        """Get SuperAdmin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERADMIN_EMAIL,
            "password": SUPERADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"SuperAdmin login failed: {response.status_code} - {response.text}")
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get Admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_condo_id(self, admin_token):
        """Get admin's condominium ID"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        if response.status_code != 200:
            pytest.skip("Could not get admin profile")
        return response.json().get("condominium_id")


class TestGlobalPricingEndpoints(TestPricingSystemSetup):
    """Tests for GET/PUT /api/super-admin/pricing/global"""
    
    def test_get_global_pricing_superadmin(self, superadmin_token):
        """GET /api/super-admin/pricing/global - SuperAdmin can view global pricing"""
        headers = {"Authorization": f"Bearer {superadmin_token}"}
        response = requests.get(f"{BASE_URL}/api/super-admin/pricing/global", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "default_seat_price" in data, "Response must include default_seat_price"
        assert "currency" in data, "Response must include currency"
        assert isinstance(data["default_seat_price"], (int, float)), "default_seat_price must be numeric"
        assert data["default_seat_price"] > 0, "default_seat_price must be greater than 0"
        print(f"✅ GET global pricing: ${data['default_seat_price']} {data['currency']}")
    
    def test_get_global_pricing_admin_forbidden(self, admin_token):
        """GET /api/super-admin/pricing/global - Admin should NOT access"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/super-admin/pricing/global", headers=headers)
        
        assert response.status_code in [401, 403], f"Expected 401/403 for non-SuperAdmin, got {response.status_code}"
        print("✅ Admin correctly blocked from global pricing endpoint")
    
    def test_get_global_pricing_unauthenticated(self):
        """GET /api/super-admin/pricing/global - Unauthenticated should fail"""
        response = requests.get(f"{BASE_URL}/api/super-admin/pricing/global")
        
        assert response.status_code in [401, 403], f"Expected 401/403 for unauthenticated, got {response.status_code}"
        print("✅ Unauthenticated correctly blocked")
    
    def test_update_global_pricing_valid(self, superadmin_token):
        """PUT /api/super-admin/pricing/global - Valid update"""
        headers = {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}
        
        # First get current price to restore later
        get_response = requests.get(f"{BASE_URL}/api/super-admin/pricing/global", headers=headers)
        original_price = get_response.json()["default_seat_price"] if get_response.status_code == 200 else 1.50
        
        # Update to new price
        new_price = 2.50
        response = requests.put(f"{BASE_URL}/api/super-admin/pricing/global", headers=headers, json={
            "default_seat_price": new_price,
            "currency": "USD"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("default_seat_price") == new_price, f"Expected price {new_price}, got {data.get('default_seat_price')}"
        print(f"✅ Updated global pricing to ${new_price}")
        
        # Verify update persisted
        verify_response = requests.get(f"{BASE_URL}/api/super-admin/pricing/global", headers=headers)
        assert verify_response.status_code == 200
        assert verify_response.json()["default_seat_price"] == new_price, "Price not persisted correctly"
        print("✅ Price update persisted and verified")
        
        # Restore original price (default is 1.50)
        requests.put(f"{BASE_URL}/api/super-admin/pricing/global", headers=headers, json={
            "default_seat_price": 1.50,
            "currency": "USD"
        })
    
    def test_update_global_pricing_invalid_zero(self, superadmin_token):
        """PUT /api/super-admin/pricing/global - Price = 0 should fail"""
        headers = {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}
        
        response = requests.put(f"{BASE_URL}/api/super-admin/pricing/global", headers=headers, json={
            "default_seat_price": 0,
            "currency": "USD"
        })
        
        assert response.status_code in [400, 422], f"Expected 400/422 for price=0, got {response.status_code}"
        print("✅ Price=0 correctly rejected")
    
    def test_update_global_pricing_invalid_negative(self, superadmin_token):
        """PUT /api/super-admin/pricing/global - Negative price should fail"""
        headers = {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}
        
        response = requests.put(f"{BASE_URL}/api/super-admin/pricing/global", headers=headers, json={
            "default_seat_price": -5.00,
            "currency": "USD"
        })
        
        assert response.status_code in [400, 422], f"Expected 400/422 for negative price, got {response.status_code}"
        print("✅ Negative price correctly rejected")
    
    def test_update_global_pricing_invalid_currency(self, superadmin_token):
        """PUT /api/super-admin/pricing/global - Invalid currency should fail"""
        headers = {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}
        
        response = requests.put(f"{BASE_URL}/api/super-admin/pricing/global", headers=headers, json={
            "default_seat_price": 1.50,
            "currency": "INVALID"
        })
        
        assert response.status_code == 400, f"Expected 400 for invalid currency, got {response.status_code}"
        print("✅ Invalid currency correctly rejected")


class TestCondominiumPricingList(TestPricingSystemSetup):
    """Tests for GET /api/super-admin/pricing/condominiums"""
    
    def test_get_condominiums_pricing_list(self, superadmin_token):
        """GET /api/super-admin/pricing/condominiums - Returns list with pricing info"""
        headers = {"Authorization": f"Bearer {superadmin_token}"}
        response = requests.get(f"{BASE_URL}/api/super-admin/pricing/condominiums", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "global_pricing" in data, "Response must include global_pricing"
        assert "condominiums" in data, "Response must include condominiums list"
        assert "total" in data, "Response must include total count"
        
        # Validate global_pricing structure
        global_pricing = data["global_pricing"]
        assert "default_seat_price" in global_pricing, "global_pricing must have default_seat_price"
        assert "currency" in global_pricing, "global_pricing must have currency"
        
        # Validate each condominium has required pricing fields
        if len(data["condominiums"]) > 0:
            condo = data["condominiums"][0]
            assert "id" in condo, "Each condo must have id"
            assert "name" in condo, "Each condo must have name"
            assert "effective_price" in condo, "Each condo must have effective_price"
            assert "uses_override" in condo, "Each condo must have uses_override"
            print(f"✅ First condo: {condo['name']}, effective_price: ${condo['effective_price']}, uses_override: {condo['uses_override']}")
        
        print(f"✅ GET condominiums pricing: {data['total']} condos returned")


class TestCondominiumPricingOverride(TestPricingSystemSetup):
    """Tests for PATCH /api/super-admin/condominiums/{id}/pricing"""
    
    def test_set_pricing_override(self, superadmin_token, admin_condo_id):
        """PATCH /api/super-admin/condominiums/{id}/pricing - Set override price"""
        if not admin_condo_id:
            pytest.skip("No condominium ID available for testing")
        
        headers = {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}
        
        # Set override price
        override_price = 2.00
        response = requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{admin_condo_id}/pricing",
            headers=headers,
            params={"seat_price_override": override_price}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✅ Set pricing override to ${override_price}")
        
        # Verify override is applied
        list_response = requests.get(f"{BASE_URL}/api/super-admin/pricing/condominiums", headers=headers)
        assert list_response.status_code == 200
        condos = list_response.json()["condominiums"]
        
        target_condo = next((c for c in condos if c["id"] == admin_condo_id), None)
        assert target_condo is not None, "Target condo not found in list"
        assert target_condo["uses_override"] == True, "uses_override should be True after setting override"
        assert target_condo["effective_price"] == override_price, f"effective_price should be {override_price}"
        print(f"✅ Verified override: effective_price=${target_condo['effective_price']}, uses_override={target_condo['uses_override']}")
    
    def test_remove_pricing_override(self, superadmin_token, admin_condo_id):
        """PATCH /api/super-admin/condominiums/{id}/pricing - Remove override (set to 0)"""
        if not admin_condo_id:
            pytest.skip("No condominium ID available for testing")
        
        headers = {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}
        
        # First set an override
        requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{admin_condo_id}/pricing",
            headers=headers,
            params={"seat_price_override": 3.00}
        )
        
        # Remove override by setting to 0
        response = requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{admin_condo_id}/pricing",
            headers=headers,
            params={"seat_price_override": 0}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✅ Removed pricing override (set to 0)")
        
        # Verify override is removed - should use global price
        list_response = requests.get(f"{BASE_URL}/api/super-admin/pricing/condominiums", headers=headers)
        condos = list_response.json()["condominiums"]
        global_price = list_response.json()["global_pricing"]["default_seat_price"]
        
        target_condo = next((c for c in condos if c["id"] == admin_condo_id), None)
        assert target_condo is not None
        assert target_condo["uses_override"] == False, "uses_override should be False after removing override"
        assert target_condo["effective_price"] == global_price, f"effective_price should be global price ${global_price}"
        print(f"✅ Verified: now using global price ${global_price}")


class TestEffectivePriceFunction(TestPricingSystemSetup):
    """Tests for get_effective_seat_price() function through payment endpoints"""
    
    def test_payments_pricing_uses_override(self, superadmin_token, admin_token, admin_condo_id):
        """GET /api/payments/pricing - Should use override when set"""
        if not admin_condo_id:
            pytest.skip("No condominium ID available")
        
        superadmin_headers = {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Set override price for admin's condo
        override_price = 2.75
        requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{admin_condo_id}/pricing",
            headers=superadmin_headers,
            params={"seat_price_override": override_price}
        )
        
        # Admin checks their pricing
        response = requests.get(f"{BASE_URL}/api/payments/pricing", headers=admin_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "price_per_user" in data, "Response must include price_per_user"
        assert "uses_override" in data, "Response must include uses_override"
        assert data["price_per_user"] == override_price, f"Expected {override_price}, got {data['price_per_user']}"
        assert data["uses_override"] == True, "uses_override should be True"
        print(f"✅ /payments/pricing returns override price: ${data['price_per_user']}")
        
        # Clean up - remove override
        requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{admin_condo_id}/pricing",
            headers=superadmin_headers,
            params={"seat_price_override": 0}
        )
    
    def test_payments_pricing_uses_global_default(self, superadmin_token, admin_token, admin_condo_id):
        """GET /api/payments/pricing - Should use global when no override"""
        if not admin_condo_id:
            pytest.skip("No condominium ID available")
        
        superadmin_headers = {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Remove any existing override
        requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{admin_condo_id}/pricing",
            headers=superadmin_headers,
            params={"seat_price_override": 0}
        )
        
        # Get global price
        global_response = requests.get(f"{BASE_URL}/api/super-admin/pricing/global", headers=superadmin_headers)
        global_price = global_response.json()["default_seat_price"]
        
        # Admin checks their pricing - should use global
        response = requests.get(f"{BASE_URL}/api/payments/pricing", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["price_per_user"] == global_price, f"Expected global price {global_price}, got {data['price_per_user']}"
        assert data["uses_override"] == False, "uses_override should be False"
        print(f"✅ /payments/pricing returns global price: ${data['price_per_user']}")


class TestPaymentsCalculateDynamicPricing(TestPricingSystemSetup):
    """Tests for POST /api/payments/calculate with dynamic pricing"""
    
    def test_payments_calculate_with_override(self, superadmin_token, admin_token, admin_condo_id):
        """POST /api/payments/calculate - Uses override price"""
        if not admin_condo_id:
            pytest.skip("No condominium ID available")
        
        superadmin_headers = {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}
        admin_headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        
        # Set override price
        override_price = 3.50
        requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{admin_condo_id}/pricing",
            headers=superadmin_headers,
            params={"seat_price_override": override_price}
        )
        
        # Calculate price for 10 users
        user_count = 10
        response = requests.post(f"{BASE_URL}/api/payments/calculate", headers=admin_headers, json={
            "user_count": user_count
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        expected_total = user_count * override_price
        assert data["price_per_user"] == override_price, f"Expected {override_price}, got {data['price_per_user']}"
        assert data["total"] == expected_total, f"Expected total {expected_total}, got {data['total']}"
        print(f"✅ /payments/calculate: {user_count} users × ${override_price} = ${data['total']}")
        
        # Clean up
        requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{admin_condo_id}/pricing",
            headers=superadmin_headers,
            params={"seat_price_override": 0}
        )
    
    def test_payments_calculate_with_global_price(self, superadmin_token, admin_token, admin_condo_id):
        """POST /api/payments/calculate - Uses global price when no override"""
        if not admin_condo_id:
            pytest.skip("No condominium ID available")
        
        superadmin_headers = {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}
        admin_headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        
        # Remove any override
        requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{admin_condo_id}/pricing",
            headers=superadmin_headers,
            params={"seat_price_override": 0}
        )
        
        # Get global price
        global_response = requests.get(f"{BASE_URL}/api/super-admin/pricing/global", headers=superadmin_headers)
        global_price = global_response.json()["default_seat_price"]
        
        # Calculate price
        user_count = 5
        response = requests.post(f"{BASE_URL}/api/payments/calculate", headers=admin_headers, json={
            "user_count": user_count
        })
        
        assert response.status_code == 200
        data = response.json()
        
        expected_total = round(user_count * global_price, 2)
        assert data["price_per_user"] == global_price, f"Expected global {global_price}, got {data['price_per_user']}"
        assert data["total"] == expected_total, f"Expected {expected_total}, got {data['total']}"
        print(f"✅ /payments/calculate with global price: {user_count} users × ${global_price} = ${data['total']}")


class TestSystemConfigCollection(TestPricingSystemSetup):
    """Tests to verify system_config collection has global_pricing document"""
    
    def test_global_pricing_exists_after_startup(self, superadmin_token):
        """Verify global_pricing document exists in system_config"""
        headers = {"Authorization": f"Bearer {superadmin_token}"}
        
        # This endpoint internally reads from system_config collection
        response = requests.get(f"{BASE_URL}/api/super-admin/pricing/global", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Default price should be $1.50 if not changed
        assert data["default_seat_price"] >= 0.01, "default_seat_price must be positive"
        assert data["currency"] in ["USD", "EUR", "MXN"], f"Invalid currency: {data['currency']}"
        print(f"✅ system_config.global_pricing exists: ${data['default_seat_price']} {data['currency']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
