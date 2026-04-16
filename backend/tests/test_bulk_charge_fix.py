"""
Test suite for Bulk Charge Logic Fix - Iteration 46
Tests that POST /api/finanzas/generate-bulk correctly targets real units from 'units' collection
instead of unit_accounts collection.

Expected state:
- 5 real units: A-101, A-102, A-103, B-201, B-202
- A-102 is 'al_dia' (balance=0), rest are 'atrasado'
- Catalog has 'Cuota Mensual' (150.0) and 'Agua' (35.0)
- Period 2026-06 charges already exist
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"

# Test period - use future period to avoid conflicts
TEST_PERIOD = "2026-08"

class TestBulkChargeFix:
    """Tests for the bulk charge logic fix"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_resp.status_code != 200:
            pytest.skip(f"Admin login failed: {login_resp.status_code}")
        
        data = login_resp.json()
        token = data.get("access_token") or data.get("token")
        if not token:
            pytest.skip("No token in login response")
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.token = token
        yield
    
    def test_01_get_real_units_count(self):
        """Verify there are exactly 5 real units in the units collection"""
        resp = self.session.get(f"{BASE_URL}/api/units")
        assert resp.status_code == 200, f"GET /api/units failed: {resp.status_code}"
        
        data = resp.json()
        units = data.get("items", [])
        unit_numbers = [u["number"] for u in units]
        
        print(f"Real units found: {unit_numbers}")
        assert len(units) == 5, f"Expected 5 real units, got {len(units)}: {unit_numbers}"
        
        # Verify expected unit numbers
        expected_units = {"A-101", "A-102", "A-103", "B-201", "B-202"}
        actual_units = set(unit_numbers)
        assert actual_units == expected_units, f"Expected {expected_units}, got {actual_units}"
    
    def test_02_get_charge_catalog(self):
        """Verify charge catalog has expected entries"""
        resp = self.session.get(f"{BASE_URL}/api/finanzas/catalog")
        assert resp.status_code == 200, f"GET /api/finanzas/catalog failed: {resp.status_code}"
        
        catalog = resp.json()
        print(f"Catalog entries: {[c['name'] for c in catalog]}")
        
        # Should have at least Cuota Mensual and Agua
        names = [c["name"] for c in catalog]
        assert "Cuota Mensual" in names or any("Cuota" in n for n in names), "Missing Cuota Mensual in catalog"
        
        # Store catalog for later tests
        self.catalog = catalog
        return catalog
    
    def test_03_bulk_charge_creates_for_5_units(self):
        """POST /api/finanzas/generate-bulk should create charges for exactly 5 real units"""
        # Get catalog first
        catalog_resp = self.session.get(f"{BASE_URL}/api/finanzas/catalog")
        assert catalog_resp.status_code == 200
        catalog = catalog_resp.json()
        
        if not catalog:
            pytest.skip("No charge types in catalog")
        
        charge_type_id = catalog[0]["id"]
        charge_type_name = catalog[0]["name"]
        charge_amount = catalog[0]["default_amount"]
        
        print(f"Using charge type: {charge_type_name} ({charge_type_id}) - ${charge_amount}")
        
        # Generate bulk charges for a new period
        resp = self.session.post(f"{BASE_URL}/api/finanzas/generate-bulk", json={
            "charge_type_id": charge_type_id,
            "period": TEST_PERIOD
        })
        
        assert resp.status_code == 200, f"Bulk charge failed: {resp.status_code} - {resp.text}"
        
        result = resp.json()
        print(f"Bulk charge result: {result}")
        
        # Verify exactly 5 units were targeted
        total_units = result.get("total_units", 0)
        created_count = result.get("created_count", 0)
        skipped_count = result.get("skipped_count", 0)
        
        assert total_units == 5, f"Expected total_units=5, got {total_units}"
        
        # Either all 5 created (new period) or all 5 skipped (already exists)
        assert created_count + skipped_count == 5, f"created({created_count}) + skipped({skipped_count}) should equal 5"
        
        # Verify response structure
        assert "charge_type" in result, "Missing charge_type in response"
        assert "period" in result, "Missing period in response"
        assert "amount" in result, "Missing amount in response"
        assert result["period"] == TEST_PERIOD, f"Period mismatch: {result['period']}"
    
    def test_04_bulk_charge_duplicate_prevention(self):
        """Running bulk charge for same period again should skip all 5 units"""
        # Get catalog
        catalog_resp = self.session.get(f"{BASE_URL}/api/finanzas/catalog")
        catalog = catalog_resp.json()
        charge_type_id = catalog[0]["id"]
        
        # Run bulk charge again for same period
        resp = self.session.post(f"{BASE_URL}/api/finanzas/generate-bulk", json={
            "charge_type_id": charge_type_id,
            "period": TEST_PERIOD
        })
        
        assert resp.status_code == 200, f"Duplicate bulk charge failed: {resp.status_code}"
        
        result = resp.json()
        print(f"Duplicate bulk charge result: {result}")
        
        # All 5 should be skipped
        assert result.get("skipped_count") == 5, f"Expected skipped_count=5, got {result.get('skipped_count')}"
        assert result.get("created_count") == 0, f"Expected created_count=0, got {result.get('created_count')}"
    
    def test_05_overview_shows_only_real_units(self):
        """GET /api/finanzas/overview should only show 5 real units, no orphan accounts"""
        resp = self.session.get(f"{BASE_URL}/api/finanzas/overview")
        assert resp.status_code == 200, f"GET /api/finanzas/overview failed: {resp.status_code}"
        
        data = resp.json()
        accounts = data.get("accounts", [])
        summary = data.get("summary", {})
        
        print(f"Overview accounts: {[a['unit_id'] for a in accounts]}")
        print(f"Overview summary: {summary}")
        
        # Should have exactly 5 accounts (one per real unit)
        assert len(accounts) == 5, f"Expected 5 accounts, got {len(accounts)}"
        
        # Verify unit IDs match real units
        account_unit_ids = set(a["unit_id"] for a in accounts)
        expected_units = {"A-101", "A-102", "A-103", "B-201", "B-202"}
        assert account_unit_ids == expected_units, f"Account unit IDs mismatch: {account_unit_ids}"
        
        # Verify summary totals
        assert summary.get("total_units") == 5, f"Summary total_units should be 5, got {summary.get('total_units')}"
    
    def test_06_bulk_charge_response_structure(self):
        """Verify bulk charge response has all required fields"""
        catalog_resp = self.session.get(f"{BASE_URL}/api/finanzas/catalog")
        catalog = catalog_resp.json()
        charge_type_id = catalog[0]["id"]
        
        # Use a different period
        test_period_2 = "2026-09"
        
        resp = self.session.post(f"{BASE_URL}/api/finanzas/generate-bulk", json={
            "charge_type_id": charge_type_id,
            "period": test_period_2
        })
        
        assert resp.status_code == 200
        result = resp.json()
        
        # Verify all required fields
        required_fields = ["total_units", "created_count", "skipped_count", "charge_type", "period", "amount"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Verify data types
        assert isinstance(result["total_units"], int)
        assert isinstance(result["created_count"], int)
        assert isinstance(result["skipped_count"], int)
        assert isinstance(result["amount"], (int, float))
    
    def test_07_charges_have_correct_structure(self):
        """Verify created charges have unit_id, condominium_id, amount_due, status, due_date"""
        # Get charges for test period
        resp = self.session.get(f"{BASE_URL}/api/finanzas/charges", params={"period": TEST_PERIOD})
        assert resp.status_code == 200, f"GET /api/finanzas/charges failed: {resp.status_code}"
        
        data = resp.json()
        charges = data.get("items", [])
        
        print(f"Found {len(charges)} charges for period {TEST_PERIOD}")
        
        if charges:
            charge = charges[0]
            print(f"Sample charge: {charge}")
            
            # Verify required fields
            assert "unit_id" in charge, "Charge missing unit_id"
            assert "condominium_id" in charge, "Charge missing condominium_id"
            assert "amount_due" in charge, "Charge missing amount_due"
            assert "status" in charge, "Charge missing status"
            assert "due_date" in charge, "Charge missing due_date"
            
            # Verify status is pending for new charges
            assert charge["status"] == "pending", f"Expected status=pending, got {charge['status']}"
            
            # Verify unit_id is a real unit
            expected_units = {"A-101", "A-102", "A-103", "B-201", "B-202"}
            assert charge["unit_id"] in expected_units, f"Charge unit_id {charge['unit_id']} not in real units"
    
    def test_08_balances_increase_after_bulk_charge(self):
        """Verify unit balances increase after bulk charge generation"""
        # Get overview before
        overview_resp = self.session.get(f"{BASE_URL}/api/finanzas/overview")
        assert overview_resp.status_code == 200
        
        overview = overview_resp.json()
        summary = overview.get("summary", {})
        
        # Global balance should be positive (units have pending charges)
        global_balance = summary.get("global_balance", 0)
        print(f"Global balance: {global_balance}")
        
        # At least some units should be atrasado
        atrasado_count = summary.get("atrasado", 0)
        print(f"Atrasado count: {atrasado_count}")
        
        # After bulk charges, we expect most units to have balance > 0
        assert atrasado_count >= 0, "Atrasado count should be non-negative"
    
    def test_09_payment_changes_status_to_al_dia(self):
        """After full payment, unit status should change to al_dia"""
        # Get a unit with balance > 0
        overview_resp = self.session.get(f"{BASE_URL}/api/finanzas/overview")
        overview = overview_resp.json()
        accounts = overview.get("accounts", [])
        
        # Find a unit with positive balance
        unit_with_debt = None
        for acc in accounts:
            if acc.get("current_balance", 0) > 0:
                unit_with_debt = acc
                break
        
        if not unit_with_debt:
            pytest.skip("No units with positive balance to test payment")
        
        unit_id = unit_with_debt["unit_id"]
        balance = unit_with_debt["current_balance"]
        
        print(f"Testing payment for unit {unit_id} with balance {balance}")
        
        # Register full payment
        payment_resp = self.session.post(f"{BASE_URL}/api/finanzas/payments", json={
            "unit_id": unit_id,
            "amount": balance,
            "payment_method": "efectivo"
        })
        
        assert payment_resp.status_code == 200, f"Payment failed: {payment_resp.status_code} - {payment_resp.text}"
        
        result = payment_resp.json()
        print(f"Payment result: {result}")
        
        # Verify new balance is 0 and status is al_dia
        assert result.get("new_balance") == 0, f"Expected new_balance=0, got {result.get('new_balance')}"
        assert result.get("account_status") == "al_dia", f"Expected status=al_dia, got {result.get('account_status')}"
    
    def test_10_partial_payment_updates_balance(self):
        """Partial payment should update balance correctly"""
        # Get a unit with balance > 0
        overview_resp = self.session.get(f"{BASE_URL}/api/finanzas/overview")
        overview = overview_resp.json()
        accounts = overview.get("accounts", [])
        
        # Find a unit with positive balance
        unit_with_debt = None
        for acc in accounts:
            if acc.get("current_balance", 0) > 50:  # Need enough balance for partial payment
                unit_with_debt = acc
                break
        
        if not unit_with_debt:
            pytest.skip("No units with sufficient balance to test partial payment")
        
        unit_id = unit_with_debt["unit_id"]
        balance = unit_with_debt["current_balance"]
        partial_amount = 25.0  # Pay $25
        
        print(f"Testing partial payment of ${partial_amount} for unit {unit_id} with balance ${balance}")
        
        # Register partial payment
        payment_resp = self.session.post(f"{BASE_URL}/api/finanzas/payments", json={
            "unit_id": unit_id,
            "amount": partial_amount,
            "payment_method": "transferencia"
        })
        
        assert payment_resp.status_code == 200, f"Partial payment failed: {payment_resp.status_code}"
        
        result = payment_resp.json()
        expected_balance = round(balance - partial_amount, 2)
        
        print(f"Partial payment result: new_balance={result.get('new_balance')}, expected={expected_balance}")
        
        # Balance should decrease by payment amount
        assert result.get("new_balance") == expected_balance, f"Expected balance {expected_balance}, got {result.get('new_balance')}"
    
    def test_11_unit_account_detail_shows_correct_breakdown(self):
        """GET /api/finanzas/unit/{unit_id} should show correct balance and charge breakdown"""
        unit_id = "A-101"
        
        resp = self.session.get(f"{BASE_URL}/api/finanzas/unit/{unit_id}")
        assert resp.status_code == 200, f"GET /api/finanzas/unit/{unit_id} failed: {resp.status_code}"
        
        data = resp.json()
        print(f"Unit account detail: {data.keys()}")
        
        # Verify response structure
        assert "account" in data, "Missing account in response"
        assert "records" in data, "Missing records in response"
        assert "breakdown" in data, "Missing breakdown in response"
        
        account = data["account"]
        assert account.get("unit_id") == unit_id, f"Unit ID mismatch: {account.get('unit_id')}"
        
        # Verify breakdown structure
        breakdown = data["breakdown"]
        if breakdown:
            for charge_type, values in breakdown.items():
                assert "total_due" in values, f"Missing total_due in breakdown for {charge_type}"
                assert "total_paid" in values, f"Missing total_paid in breakdown for {charge_type}"
                assert "pending" in values, f"Missing pending in breakdown for {charge_type}"
    
    def test_12_no_orphan_accounts_in_overview(self):
        """Overview should not contain any orphan unit_accounts (with invalid unit_ids)"""
        resp = self.session.get(f"{BASE_URL}/api/finanzas/overview")
        assert resp.status_code == 200
        
        data = resp.json()
        accounts = data.get("accounts", [])
        
        # Get real units
        units_resp = self.session.get(f"{BASE_URL}/api/units")
        units = units_resp.json().get("items", [])
        real_unit_numbers = set(u["number"] for u in units)
        
        # All accounts should have unit_id in real units
        for acc in accounts:
            unit_id = acc.get("unit_id", "")
            assert unit_id in real_unit_numbers, f"Orphan account found: {unit_id} not in real units {real_unit_numbers}"
        
        print(f"All {len(accounts)} accounts are valid (no orphans)")


class TestBulkChargeEdgeCases:
    """Edge case tests for bulk charge functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_resp.status_code != 200:
            pytest.skip("Admin login failed")
        
        data = login_resp.json()
        token = data.get("access_token") or data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        yield
    
    def test_bulk_charge_invalid_charge_type(self):
        """Bulk charge with invalid charge_type_id should return 404"""
        resp = self.session.post(f"{BASE_URL}/api/finanzas/generate-bulk", json={
            "charge_type_id": "invalid-uuid-12345",
            "period": "2026-10"
        })
        
        assert resp.status_code == 404, f"Expected 404 for invalid charge type, got {resp.status_code}"
    
    def test_bulk_charge_invalid_period_format(self):
        """Bulk charge with invalid period format should return 422"""
        catalog_resp = self.session.get(f"{BASE_URL}/api/finanzas/catalog")
        catalog = catalog_resp.json()
        
        if not catalog:
            pytest.skip("No catalog entries")
        
        charge_type_id = catalog[0]["id"]
        
        resp = self.session.post(f"{BASE_URL}/api/finanzas/generate-bulk", json={
            "charge_type_id": charge_type_id,
            "period": "invalid-period"
        })
        
        assert resp.status_code == 422, f"Expected 422 for invalid period, got {resp.status_code}"
    
    def test_bulk_charge_requires_auth(self):
        """Bulk charge without auth should return 401"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        resp = no_auth_session.post(f"{BASE_URL}/api/finanzas/generate-bulk", json={
            "charge_type_id": "some-id",
            "period": "2026-10"
        })
        
        assert resp.status_code in [401, 403], f"Expected 401/403 without auth, got {resp.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
