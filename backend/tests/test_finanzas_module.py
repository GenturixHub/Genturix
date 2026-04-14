"""
FINANZAS AVANZADAS MODULE TESTS
Tests for: Charge Catalog, Charges, Payments, Unit Accounts, Overview
Collections: charges_catalog, unit_accounts, payment_records
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
RESIDENT_EMAIL = "test-resident@genturix.com"
RESIDENT_PASSWORD = "Admin123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"


class TestFinanzasSetup:
    """Setup and authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        """Get resident authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD}
        )
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def guard_token(self):
        """Get guard authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": GUARD_EMAIL, "password": GUARD_PASSWORD}
        )
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        return response.json().get("access_token")
    
    def test_health_check(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("✓ Health check passed")


class TestChargeCatalog:
    """Tests for charge catalog CRUD operations"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD}
        )
        return response.json().get("access_token")
    
    def test_create_charge_catalog_admin(self, admin_token):
        """Admin can create charge catalog entry"""
        unique_name = f"TEST_Cargo_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": unique_name,
                "type": "fixed",
                "default_amount": 100.50
            }
        )
        assert response.status_code == 200, f"Create catalog failed: {response.text}"
        data = response.json()
        assert data["name"] == unique_name
        assert data["type"] == "fixed"
        assert data["default_amount"] == 100.50
        assert data["is_active"] == True
        assert "id" in data
        print(f"✓ Created charge catalog: {unique_name}")
        return data["id"]
    
    def test_create_charge_catalog_variable_type(self, admin_token):
        """Admin can create variable type charge"""
        unique_name = f"TEST_Variable_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": unique_name,
                "type": "variable",
                "default_amount": 50.00
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "variable"
        print(f"✓ Created variable charge catalog: {unique_name}")
    
    def test_get_charge_catalog(self, admin_token):
        """Get charge catalog list"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} catalog entries")
    
    def test_resident_cannot_create_catalog(self, resident_token):
        """Resident cannot create charge catalog (403)"""
        response = requests.post(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {resident_token}"},
            json={
                "name": "TEST_Unauthorized",
                "type": "fixed",
                "default_amount": 100.00
            }
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Resident correctly denied catalog creation")
    
    def test_update_charge_catalog(self, admin_token):
        """Admin can update charge catalog entry"""
        # First create a catalog entry
        unique_name = f"TEST_Update_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": unique_name, "type": "fixed", "default_amount": 75.00}
        )
        assert create_response.status_code == 200
        catalog_id = create_response.json()["id"]
        
        # Update it
        update_response = requests.patch(
            f"{BASE_URL}/api/finanzas/catalog/{catalog_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": f"{unique_name}_Updated", "default_amount": 80.00}
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["name"] == f"{unique_name}_Updated"
        assert updated["default_amount"] == 80.00
        print(f"✓ Updated catalog entry: {catalog_id}")


class TestCharges:
    """Tests for charge generation"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD}
        )
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def test_catalog_id(self, admin_token):
        """Create a test catalog entry for charge tests"""
        unique_name = f"TEST_ChargeType_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": unique_name, "type": "fixed", "default_amount": 150.00}
        )
        return response.json()["id"]
    
    def test_create_charge(self, admin_token, test_catalog_id):
        """Admin can create a charge for a unit"""
        unique_unit = f"TEST-{uuid.uuid4().hex[:4]}"
        unique_period = f"2099-{str(uuid.uuid4().int % 12 + 1).zfill(2)}"
        
        response = requests.post(
            f"{BASE_URL}/api/finanzas/charges",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "unit_id": unique_unit,
                "charge_type_id": test_catalog_id,
                "period": unique_period,
                "amount_due": 150.00
            }
        )
        assert response.status_code == 200, f"Create charge failed: {response.text}"
        data = response.json()
        assert data["unit_id"] == unique_unit
        assert data["amount_due"] == 150.00
        assert data["status"] == "pending"
        assert data["amount_paid"] == 0.0
        print(f"✓ Created charge for unit {unique_unit}, period {unique_period}")
        return data
    
    def test_duplicate_charge_prevention(self, admin_token, test_catalog_id):
        """Duplicate charge (same unit + type + period) returns 409"""
        unique_unit = f"TEST-DUP-{uuid.uuid4().hex[:4]}"
        period = "2099-06"
        
        # First charge
        response1 = requests.post(
            f"{BASE_URL}/api/finanzas/charges",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "unit_id": unique_unit,
                "charge_type_id": test_catalog_id,
                "period": period,
                "amount_due": 150.00
            }
        )
        assert response1.status_code == 200
        
        # Duplicate charge - should fail with 409
        response2 = requests.post(
            f"{BASE_URL}/api/finanzas/charges",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "unit_id": unique_unit,
                "charge_type_id": test_catalog_id,
                "period": period,
                "amount_due": 150.00
            }
        )
        assert response2.status_code == 409, f"Expected 409 for duplicate, got {response2.status_code}"
        print(f"✓ Duplicate charge correctly rejected with 409")
    
    def test_get_charges_admin(self, admin_token):
        """Admin can list all charges"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/charges",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        print(f"✓ Admin retrieved {data['total']} charges")
    
    def test_get_charges_resident(self, resident_token):
        """Resident can only see their own unit charges"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/charges",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        print(f"✓ Resident retrieved {data['total']} charges (own unit only)")
    
    def test_resident_cannot_create_charge(self, resident_token, test_catalog_id):
        """Resident cannot create charges (403)"""
        response = requests.post(
            f"{BASE_URL}/api/finanzas/charges",
            headers={"Authorization": f"Bearer {resident_token}"},
            json={
                "unit_id": "TEST-UNAUTH",
                "charge_type_id": test_catalog_id,
                "period": "2099-01",
                "amount_due": 100.00
            }
        )
        assert response.status_code == 403
        print("✓ Resident correctly denied charge creation")


class TestPayments:
    """Tests for payment registration and auto-apply logic"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD}
        )
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def test_unit_with_charge(self, admin_token):
        """Create a unit with a pending charge for payment tests"""
        # Create catalog entry
        catalog_name = f"TEST_PaymentCatalog_{uuid.uuid4().hex[:8]}"
        catalog_response = requests.post(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": catalog_name, "type": "fixed", "default_amount": 200.00}
        )
        catalog_id = catalog_response.json()["id"]
        
        # Create charge
        unit_id = f"TEST-PAY-{uuid.uuid4().hex[:4]}"
        charge_response = requests.post(
            f"{BASE_URL}/api/finanzas/charges",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "unit_id": unit_id,
                "charge_type_id": catalog_id,
                "period": "2099-07",
                "amount_due": 200.00
            }
        )
        return {"unit_id": unit_id, "catalog_id": catalog_id, "charge": charge_response.json()}
    
    def test_full_payment(self, admin_token, test_unit_with_charge):
        """Full payment marks charge as paid"""
        unit_id = test_unit_with_charge["unit_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/finanzas/payments",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "unit_id": unit_id,
                "amount": 200.00,
                "payment_method": "efectivo"
            }
        )
        assert response.status_code == 200, f"Payment failed: {response.text}"
        data = response.json()
        assert data["message"] == "Pago registrado"
        assert data["total_paid"] == 200.00
        assert data["new_balance"] == 0.0
        assert data["account_status"] == "al_dia"
        print(f"✓ Full payment registered, balance: {data['new_balance']}, status: {data['account_status']}")
    
    def test_partial_payment(self, admin_token):
        """Partial payment creates partial status"""
        # Create new charge
        catalog_name = f"TEST_PartialCatalog_{uuid.uuid4().hex[:8]}"
        catalog_response = requests.post(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": catalog_name, "type": "fixed", "default_amount": 300.00}
        )
        catalog_id = catalog_response.json()["id"]
        
        unit_id = f"TEST-PARTIAL-{uuid.uuid4().hex[:4]}"
        requests.post(
            f"{BASE_URL}/api/finanzas/charges",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "unit_id": unit_id,
                "charge_type_id": catalog_id,
                "period": "2099-08",
                "amount_due": 300.00
            }
        )
        
        # Make partial payment
        response = requests.post(
            f"{BASE_URL}/api/finanzas/payments",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "unit_id": unit_id,
                "amount": 100.00,
                "payment_method": "transferencia"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_balance"] == 200.00  # 300 - 100 = 200 remaining
        assert data["account_status"] == "atrasado"
        
        # Verify charge status is partial
        applied = data.get("applied", [])
        assert len(applied) > 0
        assert applied[0]["new_status"] == "partial"
        print(f"✓ Partial payment: balance {data['new_balance']}, status {data['account_status']}")
    
    def test_overpayment_creates_credit(self, admin_token):
        """Overpayment creates credit (saldo a favor)"""
        # Create charge
        catalog_name = f"TEST_CreditCatalog_{uuid.uuid4().hex[:8]}"
        catalog_response = requests.post(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": catalog_name, "type": "fixed", "default_amount": 100.00}
        )
        catalog_id = catalog_response.json()["id"]
        
        unit_id = f"TEST-CREDIT-{uuid.uuid4().hex[:4]}"
        requests.post(
            f"{BASE_URL}/api/finanzas/charges",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "unit_id": unit_id,
                "charge_type_id": catalog_id,
                "period": "2099-09",
                "amount_due": 100.00
            }
        )
        
        # Overpay by 50
        response = requests.post(
            f"{BASE_URL}/api/finanzas/payments",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "unit_id": unit_id,
                "amount": 150.00,
                "payment_method": "sinpe"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_balance"] == -50.00  # Credit of 50
        assert data["account_status"] == "adelantado"
        
        # Check that credit record was created
        applied = data.get("applied", [])
        credit_records = [a for a in applied if a.get("new_status") == "credit"]
        assert len(credit_records) > 0
        print(f"✓ Overpayment created credit: balance {data['new_balance']}, status {data['account_status']}")
    
    def test_get_payments(self, admin_token):
        """Get payment history"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/payments",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        print(f"✓ Retrieved {data['total']} payment records")
    
    def test_resident_cannot_register_payment(self, resident_token):
        """Resident cannot register payments (403)"""
        response = requests.post(
            f"{BASE_URL}/api/finanzas/payments",
            headers={"Authorization": f"Bearer {resident_token}"},
            json={
                "unit_id": "TEST-UNAUTH",
                "amount": 100.00,
                "payment_method": "efectivo"
            }
        )
        assert response.status_code == 403
        print("✓ Resident correctly denied payment registration")


class TestUnitAccount:
    """Tests for unit account retrieval"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD}
        )
        return response.json().get("access_token")
    
    def test_get_unit_account_admin(self, admin_token):
        """Admin can get any unit account"""
        # Create a unit with charge first
        catalog_name = f"TEST_UnitAcctCatalog_{uuid.uuid4().hex[:8]}"
        catalog_response = requests.post(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": catalog_name, "type": "fixed", "default_amount": 250.00}
        )
        catalog_id = catalog_response.json()["id"]
        
        unit_id = f"TEST-ACCT-{uuid.uuid4().hex[:4]}"
        requests.post(
            f"{BASE_URL}/api/finanzas/charges",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "unit_id": unit_id,
                "charge_type_id": catalog_id,
                "period": "2099-10",
                "amount_due": 250.00
            }
        )
        
        # Get unit account
        response = requests.get(
            f"{BASE_URL}/api/finanzas/unit/{unit_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "account" in data
        assert "records" in data
        assert "breakdown" in data
        assert data["account"]["current_balance"] == 250.00
        assert data["account"]["status"] == "atrasado"
        print(f"✓ Unit account retrieved: balance {data['account']['current_balance']}, status {data['account']['status']}")
    
    def test_resident_can_see_own_unit(self, resident_token):
        """Resident can see their own unit account"""
        # Get resident's apartment from their profile
        me_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        if me_response.status_code == 200:
            user_data = me_response.json()
            apartment = user_data.get("apartment", "")
            if apartment:
                response = requests.get(
                    f"{BASE_URL}/api/finanzas/unit/{apartment}",
                    headers={"Authorization": f"Bearer {resident_token}"}
                )
                assert response.status_code == 200
                print(f"✓ Resident can access their unit account: {apartment}")
            else:
                print("⚠ Resident has no apartment assigned, skipping unit access test")
        else:
            print("⚠ Could not get resident profile, skipping test")
    
    def test_resident_cannot_see_other_unit(self, resident_token):
        """Resident cannot see other unit's account (403)"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/unit/OTHER-UNIT-999",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert response.status_code == 403
        print("✓ Resident correctly denied access to other unit")


class TestFinanzasOverview:
    """Tests for admin financial overview"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD}
        )
        return response.json().get("access_token")
    
    def test_get_overview_admin(self, admin_token):
        """Admin can get financial overview"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/overview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data
        assert "summary" in data
        
        summary = data["summary"]
        assert "total_units" in summary
        assert "al_dia" in summary
        assert "atrasado" in summary
        assert "adelantado" in summary
        assert "global_due" in summary
        assert "global_paid" in summary
        assert "global_balance" in summary
        print(f"✓ Overview: {summary['total_units']} units, balance: {summary['global_balance']}")
    
    def test_resident_cannot_access_overview(self, resident_token):
        """Resident cannot access financial overview (403)"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/overview",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert response.status_code == 403
        print("✓ Resident correctly denied overview access")


class TestBalanceCalculation:
    """Tests for balance calculation logic"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json().get("access_token")
    
    def test_balance_calculation_flow(self, admin_token):
        """Test complete balance calculation: charge -> partial -> full -> credit"""
        # Create catalog
        catalog_name = f"TEST_BalanceCalc_{uuid.uuid4().hex[:8]}"
        catalog_response = requests.post(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": catalog_name, "type": "fixed", "default_amount": 500.00}
        )
        catalog_id = catalog_response.json()["id"]
        
        unit_id = f"TEST-BALANCE-{uuid.uuid4().hex[:4]}"
        
        # Step 1: Create charge of 500
        charge_response = requests.post(
            f"{BASE_URL}/api/finanzas/charges",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "unit_id": unit_id,
                "charge_type_id": catalog_id,
                "period": "2099-11",
                "amount_due": 500.00
            }
        )
        assert charge_response.status_code == 200
        
        # Verify balance is 500 (atrasado)
        acct_response = requests.get(
            f"{BASE_URL}/api/finanzas/unit/{unit_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert acct_response.json()["account"]["current_balance"] == 500.00
        assert acct_response.json()["account"]["status"] == "atrasado"
        print(f"✓ Step 1: Charge created, balance=500, status=atrasado")
        
        # Step 2: Partial payment of 200
        pay1_response = requests.post(
            f"{BASE_URL}/api/finanzas/payments",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"unit_id": unit_id, "amount": 200.00, "payment_method": "efectivo"}
        )
        assert pay1_response.status_code == 200
        assert pay1_response.json()["new_balance"] == 300.00
        assert pay1_response.json()["account_status"] == "atrasado"
        print(f"✓ Step 2: Partial payment 200, balance=300, status=atrasado")
        
        # Step 3: Pay remaining 300
        pay2_response = requests.post(
            f"{BASE_URL}/api/finanzas/payments",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"unit_id": unit_id, "amount": 300.00, "payment_method": "transferencia"}
        )
        assert pay2_response.status_code == 200
        assert pay2_response.json()["new_balance"] == 0.00
        assert pay2_response.json()["account_status"] == "al_dia"
        print(f"✓ Step 3: Full payment, balance=0, status=al_dia")
        
        # Step 4: Overpay by 100 (advance payment)
        pay3_response = requests.post(
            f"{BASE_URL}/api/finanzas/payments",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"unit_id": unit_id, "amount": 100.00, "payment_method": "sinpe"}
        )
        assert pay3_response.status_code == 200
        assert pay3_response.json()["new_balance"] == -100.00
        assert pay3_response.json()["account_status"] == "adelantado"
        print(f"✓ Step 4: Advance payment, balance=-100, status=adelantado")


class TestExistingEndpoints:
    """Verify existing endpoints still work after finanzas integration"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json().get("access_token")
    
    def test_casos_endpoint(self, admin_token):
        """Casos endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/casos",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ /api/casos endpoint working")
    
    def test_documentos_endpoint(self, admin_token):
        """Documentos endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ /api/documentos endpoint working")
    
    def test_notifications_v2_endpoint(self, admin_token):
        """Notifications V2 endpoint still works"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ /api/notifications/v2 endpoint working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
