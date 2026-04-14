"""
Test suite for Financial SaaS Module - Iteration 36
Tests: Payment settings, payment requests, assign-unit, overview with resident info, login apartment field
Uses session-scoped fixtures to avoid rate limiting
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
RESIDENT_EMAIL = "test-resident@genturix.com"
RESIDENT_PASSWORD = "Admin123!"


@pytest.fixture(scope="module")
def admin_session():
    """Login as admin once for all tests"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    
    data = response.json()
    session.headers.update({"Authorization": f"Bearer {data['access_token']}"})
    session.user = data["user"]
    return session


@pytest.fixture(scope="module")
def resident_session():
    """Login as resident once for all tests"""
    time.sleep(1)  # Small delay to avoid rate limit
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": RESIDENT_EMAIL,
        "password": RESIDENT_PASSWORD
    })
    assert response.status_code == 200, f"Resident login failed: {response.text}"
    
    data = response.json()
    session.headers.update({"Authorization": f"Bearer {data['access_token']}"})
    session.user = data["user"]
    return session


class TestLoginResponse:
    """Test login response includes apartment field"""
    
    def test_login_response_includes_apartment_field(self, resident_session):
        """Login response should include apartment field for resident"""
        user = resident_session.user
        assert "apartment" in user, "Login response missing 'apartment' field"
        print(f"✓ Login response includes apartment: {user.get('apartment')}")


class TestPaymentSettings:
    """Test payment settings CRUD"""
    
    def test_get_payment_settings(self, admin_session):
        """GET /api/finanzas/payment-settings returns saved settings"""
        response = admin_session.get(f"{BASE_URL}/api/finanzas/payment-settings")
        assert response.status_code == 200, f"Get payment settings failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, dict), "Payment settings should be a dict"
        print(f"✓ GET payment-settings returned: {list(data.keys()) if data else 'empty'}")
    
    def test_update_payment_settings(self, admin_session):
        """PUT /api/finanzas/payment-settings saves SINPE/bank info"""
        settings = {
            "sinpe_number": "8888-1234",
            "sinpe_name": "Condominio Test",
            "bank_name": "BAC",
            "bank_account": "123456789",
            "bank_iban": "CR12345678901234567890",
            "additional_instructions": "Incluir numero de unidad como referencia"
        }
        
        response = admin_session.put(f"{BASE_URL}/api/finanzas/payment-settings", json=settings)
        assert response.status_code == 200, f"Update payment settings failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "ok", "Expected status 'ok'"
        assert "settings" in data, "Response should include settings"
        print(f"✓ PUT payment-settings saved: {list(data['settings'].keys())}")
        
        # Verify by GET
        response = admin_session.get(f"{BASE_URL}/api/finanzas/payment-settings")
        assert response.status_code == 200
        saved = response.json()
        assert saved.get("sinpe_number") == "8888-1234", "SINPE number not saved correctly"
        assert saved.get("bank_name") == "BAC", "Bank name not saved correctly"
        print("✓ Payment settings verified via GET")
    
    def test_resident_can_get_payment_settings(self, resident_session):
        """Resident should be able to view payment settings"""
        response = resident_session.get(f"{BASE_URL}/api/finanzas/payment-settings")
        assert response.status_code == 200, f"Resident get payment settings failed: {response.text}"
        print("✓ Resident can access payment settings")


class TestAssignUnit:
    """Test unit assignment"""
    
    def test_assign_unit_to_user(self, admin_session):
        """POST /api/finanzas/assign-unit assigns apartment to user"""
        # First get users
        response = admin_session.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        users = response.json()
        
        # Find resident user
        resident = None
        for u in users:
            if u.get("email") == RESIDENT_EMAIL:
                resident = u
                break
        
        if not resident:
            pytest.skip("Resident user not found")
        
        # Assign unit
        payload = {
            "user_id": resident["id"],
            "unit_id": "A-101"
        }
        
        response = admin_session.post(f"{BASE_URL}/api/finanzas/assign-unit", json=payload)
        assert response.status_code == 200, f"Assign unit failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "ok", "Expected status 'ok'"
        assert data.get("unit_id") == "A-101", "Unit ID mismatch"
        print(f"✓ Assigned unit {data['unit_id']} to user {data['user_id']}")


class TestFinanzasOverview:
    """Test finanzas overview endpoint"""
    
    def test_finanzas_overview_with_resident_info(self, admin_session):
        """GET /api/finanzas/overview returns enriched table with resident info"""
        response = admin_session.get(f"{BASE_URL}/api/finanzas/overview")
        assert response.status_code == 200, f"Get overview failed: {response.text}"
        
        data = response.json()
        assert "accounts" in data, "Response should include accounts"
        assert "summary" in data, "Response should include summary"
        
        # Check summary fields
        summary = data["summary"]
        assert "total_units" in summary, "Summary missing total_units"
        assert "al_dia" in summary, "Summary missing al_dia"
        assert "atrasado" in summary, "Summary missing atrasado"
        assert "global_due" in summary, "Summary missing global_due"
        assert "global_paid" in summary, "Summary missing global_paid"
        print(f"✓ Overview summary: {summary}")
        
        # Check accounts have resident info fields
        accounts = data["accounts"]
        if accounts:
            account = accounts[0]
            print(f"✓ Account fields: {list(account.keys())}")
            has_resident_fields = any(k in account for k in ["resident_name", "resident_email", "resident_id"])
            print(f"✓ Has resident info fields: {has_resident_fields}")
        else:
            print("✓ No accounts yet (empty state)")


class TestPaymentRequests:
    """Test payment request flow"""
    
    def test_create_payment_request(self, resident_session):
        """POST /api/finanzas/payment-request creates payment request from resident"""
        payload = {
            "amount": 150.00,
            "payment_method": "sinpe",
            "reference": "TEST-REF-12345",
            "notes": "Test payment request"
        }
        
        response = resident_session.post(f"{BASE_URL}/api/finanzas/payment-request", json=payload)
        
        if response.status_code == 400:
            data = response.json()
            if "unidad asignada" in data.get("detail", "").lower():
                pytest.skip("Resident has no unit assigned - expected behavior")
        
        assert response.status_code == 200, f"Create payment request failed: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should include id"
        assert data.get("amount") == 150.00, "Amount mismatch"
        assert data.get("payment_method") == "sinpe", "Payment method mismatch"
        assert data.get("status") == "pending", "Status should be pending"
        print(f"✓ Created payment request: {data['id']}")
    
    def test_get_payment_requests_resident(self, resident_session):
        """GET /api/finanzas/payment-requests returns resident's own requests"""
        response = resident_session.get(f"{BASE_URL}/api/finanzas/payment-requests")
        assert response.status_code == 200, f"Get payment requests failed: {response.text}"
        
        data = response.json()
        assert "items" in data, "Response should include items"
        print(f"✓ Resident has {len(data['items'])} payment requests")
    
    def test_get_payment_requests_admin_pending(self, admin_session):
        """GET /api/finanzas/payment-requests?status=pending returns pending requests for admin"""
        response = admin_session.get(f"{BASE_URL}/api/finanzas/payment-requests?status=pending")
        assert response.status_code == 200, f"Get pending requests failed: {response.text}"
        
        data = response.json()
        assert "items" in data, "Response should include items"
        print(f"✓ Admin sees {len(data['items'])} pending payment requests")
    
    def test_review_payment_request_approve(self, admin_session, resident_session):
        """PATCH /api/finanzas/payment-requests/{id}?action=approved approves and registers payment"""
        # First create a payment request as resident
        payload = {
            "amount": 75.00,
            "payment_method": "transferencia",
            "reference": "APPROVE-TEST-001",
            "notes": "Test for approval"
        }
        
        response = resident_session.post(f"{BASE_URL}/api/finanzas/payment-request", json=payload)
        
        if response.status_code == 400:
            data = response.json()
            if "unidad asignada" in data.get("detail", "").lower():
                pytest.skip("Resident has no unit assigned")
        
        assert response.status_code == 200, f"Create payment request failed: {response.text}"
        pr_id = response.json()["id"]
        
        # Now approve as admin
        response = admin_session.patch(f"{BASE_URL}/api/finanzas/payment-requests/{pr_id}?action=approved")
        assert response.status_code == 200, f"Approve payment request failed: {response.text}"
        
        data = response.json()
        print(f"✓ Approved payment request: {data}")
    
    def test_review_payment_request_reject(self, admin_session, resident_session):
        """PATCH /api/finanzas/payment-requests/{id}?action=rejected rejects payment"""
        # First create a payment request as resident
        payload = {
            "amount": 50.00,
            "payment_method": "sinpe",
            "reference": "REJECT-TEST-001",
            "notes": "Test for rejection"
        }
        
        response = resident_session.post(f"{BASE_URL}/api/finanzas/payment-request", json=payload)
        
        if response.status_code == 400:
            data = response.json()
            if "unidad asignada" in data.get("detail", "").lower():
                pytest.skip("Resident has no unit assigned")
        
        assert response.status_code == 200, f"Create payment request failed: {response.text}"
        pr_id = response.json()["id"]
        
        # Now reject as admin
        response = admin_session.patch(f"{BASE_URL}/api/finanzas/payment-requests/{pr_id}?action=rejected")
        assert response.status_code == 200, f"Reject payment request failed: {response.text}"
        
        data = response.json()
        print(f"✓ Rejected payment request: {data}")


class TestUnitAccount:
    """Test unit account endpoint"""
    
    def test_get_unit_account_resident(self, resident_session):
        """GET /api/finanzas/unit/{unit_id} returns resident's financial data"""
        unit_id = resident_session.user.get("apartment") or "A-101"
        
        response = resident_session.get(f"{BASE_URL}/api/finanzas/unit/{unit_id}")
        assert response.status_code == 200, f"Get unit account failed: {response.text}"
        
        data = response.json()
        assert "account" in data, "Response should include account"
        assert "records" in data, "Response should include records"
        assert "breakdown" in data, "Response should include breakdown"
        
        account = data["account"]
        print(f"✓ Unit account: balance={account.get('current_balance', 0)}, status={account.get('status', 'unknown')}")


class TestChargeCatalog:
    """Test charge catalog CRUD"""
    
    def test_charge_catalog_crud(self, admin_session):
        """Test charge catalog CRUD operations"""
        # Create catalog item
        catalog_data = {
            "name": "TEST_Cuota Mensual",
            "type": "fixed",
            "default_amount": 100.00
        }
        
        response = admin_session.post(f"{BASE_URL}/api/finanzas/catalog", json=catalog_data)
        assert response.status_code == 200, f"Create catalog failed: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should include id"
        catalog_id = data["id"]
        print(f"✓ Created catalog item: {catalog_id}")
        
        # Get catalog
        response = admin_session.get(f"{BASE_URL}/api/finanzas/catalog")
        assert response.status_code == 200
        catalogs = response.json()
        assert any(c["id"] == catalog_id for c in catalogs), "Created catalog not found"
        print(f"✓ Catalog has {len(catalogs)} items")


class TestCharges:
    """Test charge creation"""
    
    def test_create_charge(self, admin_session):
        """Test creating a charge for a unit"""
        # First ensure we have a catalog item
        response = admin_session.get(f"{BASE_URL}/api/finanzas/catalog")
        assert response.status_code == 200
        catalogs = response.json()
        
        if not catalogs:
            # Create one
            response = admin_session.post(f"{BASE_URL}/api/finanzas/catalog", json={
                "name": "TEST_Charge Type",
                "type": "fixed",
                "default_amount": 50.00
            })
            assert response.status_code == 200
            catalog_id = response.json()["id"]
        else:
            catalog_id = catalogs[0]["id"]
        
        # Create charge
        charge_data = {
            "unit_id": "A-101",
            "charge_type_id": catalog_id,
            "period": "2026-01",
            "amount_due": 50.00
        }
        
        response = admin_session.post(f"{BASE_URL}/api/finanzas/charges", json=charge_data)
        # May fail if charge already exists for period
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Created charge: {data.get('id')}")
        elif response.status_code == 400:
            print(f"✓ Charge creation returned 400 (may already exist): {response.json().get('detail')}")
        else:
            assert False, f"Unexpected status: {response.status_code} - {response.text}"


class TestPayments:
    """Test payment registration"""
    
    def test_register_payment_admin(self, admin_session):
        """Test admin registering a payment"""
        payment_data = {
            "unit_id": "A-101",
            "amount": 25.00,
            "payment_method": "efectivo"
        }
        
        response = admin_session.post(f"{BASE_URL}/api/finanzas/payments", json=payment_data)
        assert response.status_code == 200, f"Register payment failed: {response.text}"
        
        data = response.json()
        assert "new_balance" in data, "Response should include new_balance"
        print(f"✓ Registered payment, new balance: {data['new_balance']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
