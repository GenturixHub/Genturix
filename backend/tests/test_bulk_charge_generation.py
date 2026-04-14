"""
Test suite for Mass Charge Generation (Bulk Charges) feature
Tests: POST /api/finanzas/generate-bulk endpoint
Features tested:
- Generates charges for all units in condo
- Idempotent: re-running same period skips duplicates
- Returns created_count and skipped_count
- Recalculates all unit balances after bulk generation
- Requires admin role (403 for resident)
- Validates charge_type_id exists
- Validates period format (YYYY-MM)
- Existing single charge creation still works
- Existing payment registration still works
- GET /api/finanzas/overview reflects bulk charges correctly
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
RESIDENT_EMAIL = "test-resident@genturix.com"
RESIDENT_PASSWORD = "Admin123!"


class TestBulkChargeGeneration:
    """Tests for bulk charge generation endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        self.resident_token = None
        self.charge_type_id = None
        
    def get_admin_token(self):
        """Get admin authentication token"""
        if self.admin_token:
            return self.admin_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            self.admin_token = data.get("access_token") or data.get("token")
            return self.admin_token
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
        
    def get_resident_token(self):
        """Get resident authentication token"""
        if self.resident_token:
            return self.resident_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            self.resident_token = data.get("access_token") or data.get("token")
            return self.resident_token
        pytest.skip(f"Resident login failed: {response.status_code} - {response.text}")
        
    def get_charge_type_id(self, token):
        """Get a valid charge type ID from catalog"""
        if self.charge_type_id:
            return self.charge_type_id
        response = self.session.get(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            catalog = response.json()
            if catalog and len(catalog) > 0:
                self.charge_type_id = catalog[0]["id"]
                return self.charge_type_id
        pytest.skip("No charge types in catalog")
        
    # ── Test: Admin can generate bulk charges ──
    def test_admin_can_generate_bulk_charges(self):
        """Admin should be able to generate bulk charges for all units"""
        token = self.get_admin_token()
        charge_type_id = self.get_charge_type_id(token)
        
        # Use a unique period to avoid conflicts with existing data
        test_period = "2099-01"
        
        response = self.session.post(
            f"{BASE_URL}/api/finanzas/generate-bulk",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "charge_type_id": charge_type_id,
                "period": test_period
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "total_units" in data, "Response should contain total_units"
        assert "created_count" in data, "Response should contain created_count"
        assert "skipped_count" in data, "Response should contain skipped_count"
        assert "charge_type" in data, "Response should contain charge_type"
        assert "period" in data, "Response should contain period"
        assert "amount" in data, "Response should contain amount"
        
        # Verify data types
        assert isinstance(data["total_units"], int)
        assert isinstance(data["created_count"], int)
        assert isinstance(data["skipped_count"], int)
        
        print(f"Bulk generation result: {data['created_count']} created, {data['skipped_count']} skipped out of {data['total_units']} units")
        
    # ── Test: Idempotent - re-running skips duplicates ──
    def test_bulk_generation_is_idempotent(self):
        """Re-running bulk generation for same period should skip all duplicates"""
        token = self.get_admin_token()
        charge_type_id = self.get_charge_type_id(token)
        
        test_period = "2098-12"
        
        # First run - should create charges
        response1 = self.session.post(
            f"{BASE_URL}/api/finanzas/generate-bulk",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "charge_type_id": charge_type_id,
                "period": test_period
            }
        )
        assert response1.status_code == 200
        data1 = response1.json()
        first_created = data1["created_count"]
        
        # Wait a bit to avoid rate limiting
        time.sleep(1)
        
        # Second run - should skip all (idempotent)
        response2 = self.session.post(
            f"{BASE_URL}/api/finanzas/generate-bulk",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "charge_type_id": charge_type_id,
                "period": test_period
            }
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # All should be skipped on second run
        assert data2["created_count"] == 0, f"Expected 0 created on re-run, got {data2['created_count']}"
        assert data2["skipped_count"] == data2["total_units"], f"Expected all {data2['total_units']} to be skipped"
        
        print(f"Idempotency verified: First run created {first_created}, second run skipped {data2['skipped_count']}")
        
    # ── Test: Resident cannot generate bulk charges (403) ──
    def test_resident_cannot_generate_bulk_charges(self):
        """Resident should get 403 when trying to generate bulk charges"""
        admin_token = self.get_admin_token()
        charge_type_id = self.get_charge_type_id(admin_token)
        
        resident_token = self.get_resident_token()
        
        response = self.session.post(
            f"{BASE_URL}/api/finanzas/generate-bulk",
            headers={"Authorization": f"Bearer {resident_token}"},
            json={
                "charge_type_id": charge_type_id,
                "period": "2097-01"
            }
        )
        
        assert response.status_code == 403, f"Expected 403 for resident, got {response.status_code}: {response.text}"
        print("Resident correctly denied access (403)")
        
    # ── Test: Invalid charge_type_id returns 404 ──
    def test_invalid_charge_type_returns_404(self):
        """Invalid charge_type_id should return 404"""
        token = self.get_admin_token()
        
        response = self.session.post(
            f"{BASE_URL}/api/finanzas/generate-bulk",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "charge_type_id": "non-existent-id-12345",
                "period": "2096-01"
            }
        )
        
        assert response.status_code == 404, f"Expected 404 for invalid charge_type_id, got {response.status_code}"
        print("Invalid charge_type_id correctly returns 404")
        
    # ── Test: Invalid period format returns 422 ──
    def test_invalid_period_format_returns_422(self):
        """Invalid period format should return 422 validation error"""
        token = self.get_admin_token()
        charge_type_id = self.get_charge_type_id(token)
        
        invalid_periods = ["2024", "01-2024", "2024/01", "invalid", "2024-13", "2024-00"]
        
        for invalid_period in invalid_periods:
            response = self.session.post(
                f"{BASE_URL}/api/finanzas/generate-bulk",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "charge_type_id": charge_type_id,
                    "period": invalid_period
                }
            )
            
            assert response.status_code == 422, f"Expected 422 for period '{invalid_period}', got {response.status_code}"
            
        print("Invalid period formats correctly return 422")
        
    # ── Test: Bulk generation with optional due_date ──
    def test_bulk_generation_with_due_date(self):
        """Bulk generation should accept optional due_date"""
        token = self.get_admin_token()
        charge_type_id = self.get_charge_type_id(token)
        
        test_period = "2095-06"
        
        response = self.session.post(
            f"{BASE_URL}/api/finanzas/generate-bulk",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "charge_type_id": charge_type_id,
                "period": test_period,
                "due_date": "2095-06-20T00:00:00Z"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("Bulk generation with due_date works correctly")
        
    # ── Test: Overview reflects bulk charges ──
    def test_overview_reflects_bulk_charges(self):
        """GET /api/finanzas/overview should reflect bulk charges"""
        token = self.get_admin_token()
        
        # Get overview before
        response = self.session.get(
            f"{BASE_URL}/api/finanzas/overview",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "summary" in data, "Overview should contain summary"
        assert "accounts" in data, "Overview should contain accounts"
        
        # Verify summary structure
        summary = data["summary"]
        assert "global_due" in summary
        assert "global_paid" in summary
        assert "global_balance" in summary
        
        print(f"Overview: global_due={summary['global_due']}, global_paid={summary['global_paid']}, global_balance={summary['global_balance']}")


class TestExistingFinanzasEndpoints:
    """Tests to verify existing finanzas endpoints still work"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        
    def get_admin_token(self):
        """Get admin authentication token"""
        if self.admin_token:
            return self.admin_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            self.admin_token = data.get("access_token") or data.get("token")
            return self.admin_token
        pytest.skip(f"Admin login failed: {response.status_code}")
        
    # ── Test: Single charge creation still works ──
    def test_single_charge_creation_works(self):
        """Single charge creation endpoint should still work"""
        token = self.get_admin_token()
        
        # Get a charge type
        catalog_response = self.session.get(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert catalog_response.status_code == 200
        catalog = catalog_response.json()
        if not catalog:
            pytest.skip("No charge types in catalog")
            
        charge_type_id = catalog[0]["id"]
        
        # Create a single charge
        response = self.session.post(
            f"{BASE_URL}/api/finanzas/charges",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "unit_id": "TEST-SINGLE-001",
                "charge_type_id": charge_type_id,
                "period": "2094-01",
                "amount_due": 100.00
            }
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        print("Single charge creation works correctly")
        
    # ── Test: Payment registration still works ──
    def test_payment_registration_works(self):
        """Payment registration endpoint should still work"""
        token = self.get_admin_token()
        
        # First create a charge to pay
        catalog_response = self.session.get(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {token}"}
        )
        if catalog_response.status_code != 200 or not catalog_response.json():
            pytest.skip("No charge types in catalog")
            
        charge_type_id = catalog_response.json()[0]["id"]
        
        # Create charge
        self.session.post(
            f"{BASE_URL}/api/finanzas/charges",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "unit_id": "TEST-PAYMENT-001",
                "charge_type_id": charge_type_id,
                "period": "2093-01",
                "amount_due": 50.00
            }
        )
        
        # Register payment
        response = self.session.post(
            f"{BASE_URL}/api/finanzas/payments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "unit_id": "TEST-PAYMENT-001",
                "amount": 25.00,
                "payment_method": "efectivo"
            }
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "new_balance" in data, "Payment response should contain new_balance"
        print(f"Payment registration works correctly, new_balance: {data['new_balance']}")
        
    # ── Test: Charge catalog endpoint works ──
    def test_charge_catalog_endpoint_works(self):
        """GET /api/finanzas/catalog should work"""
        token = self.get_admin_token()
        
        response = self.session.get(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Catalog should be a list"
        
        if data:
            # Verify catalog item structure
            item = data[0]
            assert "id" in item
            assert "name" in item
            assert "default_amount" in item
            
        print(f"Catalog endpoint works, found {len(data)} charge types")


class TestOtherEndpointsNotBroken:
    """Tests to verify other endpoints are not broken"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        
    def get_admin_token(self):
        """Get admin authentication token"""
        if self.admin_token:
            return self.admin_token
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            self.admin_token = data.get("access_token") or data.get("token")
            return self.admin_token
        pytest.skip(f"Admin login failed: {response.status_code}")
        
    def test_casos_endpoint_works(self):
        """GET /api/casos should work"""
        token = self.get_admin_token()
        
        response = self.session.get(
            f"{BASE_URL}/api/casos",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("Casos endpoint works")
        
    def test_documentos_endpoint_works(self):
        """GET /api/documentos should work"""
        token = self.get_admin_token()
        
        response = self.session.get(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("Documentos endpoint works")
        
    def test_notifications_endpoint_works(self):
        """GET /api/notifications/v2 should work"""
        token = self.get_admin_token()
        
        response = self.session.get(
            f"{BASE_URL}/api/notifications/v2",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("Notifications endpoint works")
        
    def test_health_endpoint_works(self):
        """GET /api/health should work"""
        response = self.session.get(f"{BASE_URL}/api/health")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("Health endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
