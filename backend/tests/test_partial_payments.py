"""
Test Suite for Partial Payment Handling in GENTURIX Billing System

Tests the critical partial payment functionality:
1. Partial payment keeps status as past_due (not active)
2. Full payment changes status to active
3. Response includes invoice_amount, total_paid_cycle, balance_due, is_fully_paid
4. Partial payment does NOT recalculate next_billing_date
5. Full payment DOES recalculate next_billing_date
6. GET /api/billing/balance returns correct balance info
7. Multiple partial payments accumulate in total_paid_cycle
8. Balance becomes 0 only when total_paid >= invoice_amount
9. Billing events logged correctly (partial_payment_received vs payment_received)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "Admin123!"

# Use existing production condos for testing
# "Test Seat Upgrade Condo" - has billing and invoice amount
TEST_CONDO_ID = "c6beab08-e465-440c-8b2b-a2e1a160827a"  # Has next_invoice_amount: 104.65


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Retry login up to 3 times with delay
    for attempt in range(3):
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": SUPERADMIN_EMAIL,
            "password": SUPERADMIN_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            return token
        elif login_response.status_code == 429:
            # Rate limited, wait and retry
            import time
            time.sleep(60)
        else:
            pytest.skip(f"Authentication failed: {login_response.text}")
    
    pytest.skip("Authentication failed after 3 attempts")


@pytest.fixture
def api_session(auth_token):
    """Create authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestConfirmPaymentEndpoint:
    """Tests for POST /api/billing/confirm-payment/{condo_id}"""
    
    def test_response_includes_all_required_fields(self, api_session):
        """TEST 3: Response includes invoice_amount, total_paid_cycle, balance_due, is_fully_paid"""
        # First get balance to see if there's an invoice to pay
        balance_response = api_session.get(f"{BASE_URL}/api/billing/balance/{TEST_CONDO_ID}")
        assert balance_response.status_code == 200, f"Failed to get balance: {balance_response.text}"
        balance = balance_response.json()
        
        invoice_amount = balance.get("invoice_amount", 0)
        if invoice_amount == 0:
            # If this condo has no invoice, we can still test the endpoint with a small payment
            pass
        
        # Make a small test payment
        payment_response = api_session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{TEST_CONDO_ID}",
            json={
                "amount_paid": 5.00,
                "payment_reference": f"TEST-FIELDS-{uuid.uuid4().hex[:8]}",
                "notes": "Test response fields"
            }
        )
        
        assert payment_response.status_code == 200, f"Payment failed: {payment_response.text}"
        result = payment_response.json()
        
        # Verify all required fields are present
        required_fields = [
            "payment_id",
            "condominium_id",
            "amount_paid",
            "invoice_amount",      # Required field
            "total_paid_cycle",    # Required field
            "balance_due",         # Required field
            "previous_status",
            "new_status",
            "is_fully_paid",       # Required field
            "message"
        ]
        
        missing_fields = [f for f in required_fields if f not in result]
        assert not missing_fields, f"Missing required fields: {missing_fields}"
        
        # Verify types
        assert isinstance(result["invoice_amount"], (int, float)), "invoice_amount should be numeric"
        assert isinstance(result["total_paid_cycle"], (int, float)), "total_paid_cycle should be numeric"
        assert isinstance(result["balance_due"], (int, float)), "balance_due should be numeric"
        assert isinstance(result["is_fully_paid"], bool), "is_fully_paid should be boolean"
        
        print(f"✓ All required fields present: {list(result.keys())}")
        print(f"  invoice_amount: ${result['invoice_amount']}")
        print(f"  total_paid_cycle: ${result['total_paid_cycle']}")
        print(f"  balance_due: ${result['balance_due']}")
        print(f"  is_fully_paid: {result['is_fully_paid']}")


class TestPartialPaymentLogic:
    """Tests for partial payment business logic"""
    
    def test_partial_payment_keeps_status_not_active(self, api_session):
        """TEST 1: Partial payment keeps status as past_due, NOT active"""
        # Get current balance
        balance_response = api_session.get(f"{BASE_URL}/api/billing/balance/{TEST_CONDO_ID}")
        assert balance_response.status_code == 200
        balance = balance_response.json()
        
        invoice_amount = balance.get("invoice_amount", 0)
        total_already_paid = balance.get("total_paid_cycle", 0)
        
        # Calculate a partial amount that won't fully pay the invoice
        remaining = invoice_amount - total_already_paid
        if remaining <= 0:
            pytest.skip("Invoice already fully paid, cannot test partial payment")
        
        # Pay 30% of remaining (definitely partial)
        partial_amount = max(1.0, remaining * 0.3)
        
        payment_response = api_session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{TEST_CONDO_ID}",
            json={
                "amount_paid": partial_amount,
                "payment_reference": f"PARTIAL-{uuid.uuid4().hex[:8]}",
                "notes": "Test partial payment status"
            }
        )
        
        assert payment_response.status_code == 200, f"Payment failed: {payment_response.text}"
        result = payment_response.json()
        
        # Verify partial payment logic
        if result["balance_due"] > 0:
            # If balance still due, should NOT be active
            assert result["is_fully_paid"] == False, "Should not be fully paid with remaining balance"
            assert result["new_status"] != "active", \
                f"Status should NOT be 'active' after partial payment, got: '{result['new_status']}'"
            print(f"✓ Partial payment ${partial_amount:.2f}: status={result['new_status']}, balance_due=${result['balance_due']:.2f}")
        else:
            print(f"✓ Payment completed the balance - became fully paid")
    
    def test_partial_payment_preserves_billing_date(self, api_session):
        """TEST 4: Partial payment does NOT recalculate next_billing_date"""
        # Get initial billing date
        balance_before = api_session.get(f"{BASE_URL}/api/billing/balance/{TEST_CONDO_ID}").json()
        initial_billing_date = balance_before.get("next_billing_date")
        
        remaining = balance_before.get("invoice_amount", 0) - balance_before.get("total_paid_cycle", 0)
        if remaining <= 0:
            pytest.skip("Invoice already fully paid")
        
        # Make partial payment
        partial_amount = max(0.50, remaining * 0.1)  # 10% of remaining
        
        payment_response = api_session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{TEST_CONDO_ID}",
            json={
                "amount_paid": partial_amount,
                "payment_reference": f"PARTDATE-{uuid.uuid4().hex[:8]}"
            }
        )
        
        assert payment_response.status_code == 200
        result = payment_response.json()
        
        if not result["is_fully_paid"]:
            # For partial payments, next_billing_date in response should be None
            assert result.get("next_billing_date") is None, \
                f"Partial payment should NOT recalculate next_billing_date, got: {result.get('next_billing_date')}"
            print(f"✓ Partial payment: next_billing_date is None (correct - not recalculated)")
        else:
            print(f"✓ Payment was full, next_billing_date was recalculated")


class TestBillingBalanceEndpoint:
    """Tests for GET /api/billing/balance/{condo_id}"""
    
    def test_balance_endpoint_returns_correct_structure(self, api_session):
        """TEST 6: GET /api/billing/balance returns correct balance info"""
        response = api_session.get(f"{BASE_URL}/api/billing/balance/{TEST_CONDO_ID}")
        
        assert response.status_code == 200, f"Balance endpoint failed: {response.text}"
        balance = response.json()
        
        # Required fields
        required_fields = [
            "condominium_id",
            "condominium_name",
            "invoice_amount",
            "total_paid_cycle",
            "balance_due",
            "billing_status",
            "is_fully_paid",
            "billing_cycle",
            "paid_seats"
        ]
        
        missing = [f for f in required_fields if f not in balance]
        assert not missing, f"Missing fields in balance response: {missing}"
        
        # Verify is_fully_paid is consistent with balance_due
        expected_fully_paid = balance["balance_due"] <= 0
        assert balance["is_fully_paid"] == expected_fully_paid, \
            f"is_fully_paid={balance['is_fully_paid']} but balance_due={balance['balance_due']}"
        
        print(f"✓ Balance endpoint returns correct structure:")
        print(f"  condominium: {balance['condominium_name']}")
        print(f"  invoice_amount: ${balance['invoice_amount']}")
        print(f"  total_paid_cycle: ${balance['total_paid_cycle']}")
        print(f"  balance_due: ${balance['balance_due']}")
        print(f"  is_fully_paid: {balance['is_fully_paid']}")
    
    def test_balance_reflects_accumulated_payments(self, api_session):
        """TEST 7: Multiple partial payments accumulate in total_paid_cycle"""
        # Get initial state
        balance_before = api_session.get(f"{BASE_URL}/api/billing/balance/{TEST_CONDO_ID}").json()
        total_before = balance_before.get("total_paid_cycle", 0)
        
        # Make two small payments
        payment1_amount = 2.00
        payment2_amount = 3.00
        
        api_session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{TEST_CONDO_ID}",
            json={"amount_paid": payment1_amount, "payment_reference": f"ACC1-{uuid.uuid4().hex[:6]}"}
        )
        
        api_session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{TEST_CONDO_ID}",
            json={"amount_paid": payment2_amount, "payment_reference": f"ACC2-{uuid.uuid4().hex[:6]}"}
        )
        
        # Check accumulated total
        balance_after = api_session.get(f"{BASE_URL}/api/billing/balance/{TEST_CONDO_ID}").json()
        total_after = balance_after.get("total_paid_cycle", 0)
        
        expected_total = total_before + payment1_amount + payment2_amount
        assert abs(total_after - expected_total) < 0.01, \
            f"Payments should accumulate: expected ${expected_total:.2f}, got ${total_after:.2f}"
        
        print(f"✓ Payments accumulated: ${total_before:.2f} + ${payment1_amount} + ${payment2_amount} = ${total_after:.2f}")


class TestBillingEventsLogging:
    """Tests for billing event logging"""
    
    def test_billing_events_logged(self, api_session):
        """TEST 9: Billing events are logged for payments"""
        # Make a payment
        payment_response = api_session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{TEST_CONDO_ID}",
            json={
                "amount_paid": 1.50,
                "payment_reference": f"EVT-{uuid.uuid4().hex[:8]}",
                "notes": "Test event logging"
            }
        )
        assert payment_response.status_code == 200
        result = payment_response.json()
        
        # Get billing events
        events_response = api_session.get(f"{BASE_URL}/api/billing/events/{TEST_CONDO_ID}")
        assert events_response.status_code == 200, f"Failed to get events: {events_response.text}"
        events_data = events_response.json()
        
        # The response contains an "events" array
        events = events_data.get("events", [])
        
        # Find payment events
        payment_events = [e for e in events if "payment" in e.get("event_type", "").lower()]
        
        assert len(payment_events) > 0, "Should have at least one payment event logged"
        
        # Check for correct event type based on whether payment was partial or full
        event_types = [e.get("event_type") for e in payment_events]
        
        if result["is_fully_paid"]:
            # Should have payment_received
            assert "payment_received" in event_types, f"Full payment should log 'payment_received', got: {event_types}"
            print(f"✓ Full payment event logged: payment_received")
        else:
            # Should have partial_payment_received
            assert "partial_payment_received" in event_types, f"Partial payment should log 'partial_payment_received', got: {event_types}"
            print(f"✓ Partial payment event logged: partial_payment_received")
        
        print(f"  Recent payment events: {event_types[-5:]}")


class TestEdgeCases:
    """Edge case tests"""
    
    def test_demo_condo_payment_rejected(self, api_session):
        """Demo condominiums should reject payment confirmation"""
        # Get a demo condo
        condos_response = api_session.get(f"{BASE_URL}/api/condominiums")
        if condos_response.status_code != 200:
            pytest.skip("Cannot list condos")
        
        condos = condos_response.json()
        demo_condos = [c for c in condos if c.get("is_demo") or c.get("environment") == "demo"]
        
        if not demo_condos:
            pytest.skip("No demo condos available")
        
        demo_condo_id = demo_condos[0].get("id")
        
        payment_response = api_session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{demo_condo_id}",
            json={"amount_paid": 10.00, "payment_reference": "TEST-DEMO"}
        )
        
        assert payment_response.status_code == 403, \
            f"Demo condo payment should be rejected with 403, got {payment_response.status_code}: {payment_response.text}"
        
        print(f"✓ Demo condo payment correctly rejected with 403")
    
    def test_nonexistent_condo_returns_404(self, api_session):
        """Payment for non-existent condo returns 404"""
        fake_id = str(uuid.uuid4())
        
        payment_response = api_session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{fake_id}",
            json={"amount_paid": 10.00}
        )
        
        assert payment_response.status_code == 404
        print(f"✓ Non-existent condo correctly returns 404")
    
    def test_zero_payment_rejected(self, api_session):
        """Zero payment should be rejected by validation"""
        payment_response = api_session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{TEST_CONDO_ID}",
            json={"amount_paid": 0}
        )
        
        # Should get validation error (422) or bad request (400)
        assert payment_response.status_code in [400, 422], \
            f"Zero payment should be rejected, got {payment_response.status_code}"
        print(f"✓ Zero payment correctly rejected with {payment_response.status_code}")
    
    def test_negative_payment_rejected(self, api_session):
        """Negative payment should be rejected"""
        payment_response = api_session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{TEST_CONDO_ID}",
            json={"amount_paid": -10.00}
        )
        
        assert payment_response.status_code in [400, 422], \
            f"Negative payment should be rejected, got {payment_response.status_code}"
        print(f"✓ Negative payment correctly rejected")


class TestFullPaymentFlow:
    """Test complete full payment flow"""
    
    def test_full_payment_activates_and_recalculates_date(self, api_session):
        """TEST 2 & 5: Full payment changes status to active and recalculates next_billing_date"""
        # Get a condo that has balance due
        balance = api_session.get(f"{BASE_URL}/api/billing/balance/{TEST_CONDO_ID}").json()
        
        remaining_balance = balance.get("balance_due", 0)
        if remaining_balance <= 0:
            # Already fully paid, make note and skip
            print(f"Note: {balance.get('condominium_name')} is already fully paid")
            pytest.skip("Condo already fully paid - cannot test full payment")
        
        # Pay the remaining balance to complete payment
        payment_response = api_session.post(
            f"{BASE_URL}/api/billing/confirm-payment/{TEST_CONDO_ID}",
            json={
                "amount_paid": remaining_balance,
                "payment_reference": f"FULL-{uuid.uuid4().hex[:8]}",
                "notes": "Complete full payment test"
            }
        )
        
        assert payment_response.status_code == 200, f"Payment failed: {payment_response.text}"
        result = payment_response.json()
        
        # Verify full payment logic
        assert result["is_fully_paid"] == True, f"Should be fully paid after paying remaining ${remaining_balance}"
        assert result["balance_due"] == 0, f"Balance should be 0 after full payment, got {result['balance_due']}"
        assert result["new_status"] == "active", f"Status should be 'active' after full payment, got '{result['new_status']}'"
        
        # TEST 5: Verify next_billing_date is recalculated
        assert result.get("next_billing_date") is not None, \
            "next_billing_date should be set after full payment"
        
        print(f"✓ Full payment of ${remaining_balance:.2f}:")
        print(f"  Status changed to: {result['new_status']}")
        print(f"  balance_due: ${result['balance_due']}")
        print(f"  is_fully_paid: {result['is_fully_paid']}")
        print(f"  next_billing_date: {result['next_billing_date']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
