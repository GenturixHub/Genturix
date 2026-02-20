"""
Test: SaaS Pricing Management Feature
Tests for GET/PUT /api/super-admin/pricing/global 
and GET/PATCH /api/super-admin/condominiums/{id}/pricing
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "SuperAdmin123!"


class TestPricingFeature:
    """SaaS Pricing Management Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login as SuperAdmin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERADMIN_EMAIL,
            "password": SUPERADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        self.token = data["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
        
        # Cleanup: Reset global price to default
        self.session.put(f"{BASE_URL}/api/super-admin/pricing/global", json={
            "default_seat_price": 1.50,
            "currency": "USD"
        })
    
    def test_get_global_pricing_returns_current_pricing(self):
        """GET /api/super-admin/pricing/global returns current global pricing"""
        response = self.session.get(f"{BASE_URL}/api/super-admin/pricing/global")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "default_seat_price" in data
        assert "currency" in data
        assert isinstance(data["default_seat_price"], (int, float))
        assert data["default_seat_price"] > 0
        assert data["currency"] in ["USD", "EUR", "MXN"]
        print(f"[PASS] Global pricing: ${data['default_seat_price']} {data['currency']}")
    
    def test_put_global_pricing_updates_successfully(self):
        """PUT /api/super-admin/pricing/global updates global price"""
        # Get current price first
        get_response = self.session.get(f"{BASE_URL}/api/super-admin/pricing/global")
        original_price = get_response.json()["default_seat_price"]
        
        # Update to new price
        new_price = 2.50
        response = self.session.put(f"{BASE_URL}/api/super-admin/pricing/global", json={
            "default_seat_price": new_price,
            "currency": "USD"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["default_seat_price"] == new_price
        
        # Verify persistence
        verify_response = self.session.get(f"{BASE_URL}/api/super-admin/pricing/global")
        assert verify_response.json()["default_seat_price"] == new_price
        
        # Reset to original
        self.session.put(f"{BASE_URL}/api/super-admin/pricing/global", json={
            "default_seat_price": original_price,
            "currency": "USD"
        })
        print(f"[PASS] Updated global price to ${new_price}, then reset")
    
    def test_get_condominiums_pricing_returns_list(self):
        """GET /api/super-admin/pricing/condominiums returns list with pricing info"""
        response = self.session.get(f"{BASE_URL}/api/super-admin/pricing/condominiums")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate structure
        assert "global_pricing" in data
        assert "condominiums" in data
        assert "total" in data
        assert isinstance(data["condominiums"], list)
        
        # Check each condo has required fields
        if len(data["condominiums"]) > 0:
            condo = data["condominiums"][0]
            required_fields = ["id", "name", "effective_price", "uses_override", "global_price", "currency"]
            for field in required_fields:
                assert field in condo, f"Missing field: {field}"
        
        print(f"[PASS] Got {data['total']} condominiums with pricing info")
    
    def test_patch_set_price_override(self):
        """PATCH /api/super-admin/condominiums/{id}/pricing sets price override"""
        # Get a condo to test with
        condos_response = self.session.get(f"{BASE_URL}/api/super-admin/pricing/condominiums")
        condos = condos_response.json()["condominiums"]
        assert len(condos) > 0, "No condominiums to test"
        
        test_condo = condos[0]
        condo_id = test_condo["id"]
        override_price = 0.75
        
        # Set override
        response = self.session.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{condo_id}/pricing?seat_price_override={override_price}"
        )
        
        assert response.status_code == 200
        
        # Verify override applied
        verify_response = self.session.get(f"{BASE_URL}/api/super-admin/pricing/condominiums")
        updated_condo = next(c for c in verify_response.json()["condominiums"] if c["id"] == condo_id)
        
        assert updated_condo["uses_override"] == True
        assert updated_condo["override_price"] == override_price
        assert updated_condo["effective_price"] == override_price
        
        # Cleanup: Remove override
        self.session.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{condo_id}/pricing?seat_price_override=0"
        )
        print(f"[PASS] Override ${override_price} set and verified for {test_condo['name']}")
    
    def test_patch_remove_price_override(self):
        """PATCH with seat_price_override=0 removes override"""
        # Get a condo
        condos_response = self.session.get(f"{BASE_URL}/api/super-admin/pricing/condominiums")
        condos = condos_response.json()["condominiums"]
        test_condo = condos[0]
        condo_id = test_condo["id"]
        
        # First set an override
        self.session.patch(f"{BASE_URL}/api/super-admin/condominiums/{condo_id}/pricing?seat_price_override=1.25")
        
        # Now remove it with 0
        response = self.session.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{condo_id}/pricing?seat_price_override=0"
        )
        
        assert response.status_code == 200
        
        # Verify override removed
        verify_response = self.session.get(f"{BASE_URL}/api/super-admin/pricing/condominiums")
        updated_condo = next(c for c in verify_response.json()["condominiums"] if c["id"] == condo_id)
        
        assert updated_condo["uses_override"] == False
        assert updated_condo["override_price"] is None
        print(f"[PASS] Override removed from {test_condo['name']}")
    
    def test_put_global_rejects_zero_price(self):
        """PUT /api/super-admin/pricing/global rejects price <= 0"""
        response = self.session.put(f"{BASE_URL}/api/super-admin/pricing/global", json={
            "default_seat_price": 0,
            "currency": "USD"
        })
        
        # Should be rejected (either 400 or 422)
        assert response.status_code in [400, 422]
        print("[PASS] Zero price rejected")
    
    def test_put_global_rejects_negative_price(self):
        """PUT /api/super-admin/pricing/global rejects negative price"""
        response = self.session.put(f"{BASE_URL}/api/super-admin/pricing/global", json={
            "default_seat_price": -5.00,
            "currency": "USD"
        })
        
        assert response.status_code in [400, 422]
        print("[PASS] Negative price rejected")
    
    def test_put_global_rejects_invalid_currency(self):
        """PUT /api/super-admin/pricing/global rejects invalid currency"""
        response = self.session.put(f"{BASE_URL}/api/super-admin/pricing/global", json={
            "default_seat_price": 1.50,
            "currency": "GBP"  # Not in allowed list
        })
        
        assert response.status_code == 400
        print("[PASS] Invalid currency rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
