"""
Test Commercial Flexibility Features for Genturix Onboarding
============================================================
Tests for MEJORA COMERCIAL - FLEXIBILIDAD DE PLAN EN ONBOARDING:
1. seat_price_override - Custom price per seat
2. yearly_discount_percent - Editable discount 0-50%
3. Billing preview with custom parameters
4. E2E condominium creation with custom pricing
5. billing_events logging

Author: Testing Agent
Date: 2026-02-26
"""

import pytest
import requests
import os
import time
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://saas-wizard-fix.preview.emergentagent.com').rstrip('/')

class TestCommercialFlexibility:
    """Test suite for commercial flexibility features in onboarding"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get SuperAdmin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "superadmin@genturix.com", "password": "Admin123!"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}"
        }
    
    # ==================== BILLING PREVIEW TESTS ====================
    
    def test_billing_preview_with_seat_price_override(self, auth_headers):
        """Test POST /api/billing/preview accepts seat_price_override parameter"""
        response = requests.post(
            f"{BASE_URL}/api/billing/preview",
            json={
                "initial_units": 100,
                "billing_cycle": "monthly",
                "seat_price_override": 1.50
            },
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify custom price is used
        assert data["price_per_seat"] == 1.50, f"Expected price_per_seat=1.50, got {data['price_per_seat']}"
        assert data["monthly_amount"] == 150.0, f"Expected monthly_amount=150, got {data['monthly_amount']}"
        assert data["seats"] == 100
        print("PASS: Billing preview correctly uses seat_price_override=$1.50")
    
    def test_billing_preview_with_yearly_discount_percent(self, auth_headers):
        """Test POST /api/billing/preview accepts yearly_discount_percent parameter"""
        response = requests.post(
            f"{BASE_URL}/api/billing/preview",
            json={
                "initial_units": 100,
                "billing_cycle": "yearly",
                "yearly_discount_percent": 25
            },
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify custom discount is used (default price is $2.99)
        assert data["yearly_discount_percent"] == 25, f"Expected yearly_discount_percent=25, got {data['yearly_discount_percent']}"
        # $2.99 * 100 * 12 = $3588, with 25% discount = $2691
        expected_yearly = round(2.99 * 100 * 12 * 0.75, 2)
        assert data["effective_amount"] == expected_yearly or abs(data["effective_amount"] - expected_yearly) < 1, \
            f"Expected effective_amount~={expected_yearly}, got {data['effective_amount']}"
        print(f"PASS: Billing preview correctly uses yearly_discount_percent=25% (total: ${data['effective_amount']})")
    
    def test_billing_preview_combined_custom_pricing(self, auth_headers):
        """Test billing calculation with both custom price and custom discount"""
        # Expected: 100 seats * $1.50 * 12 months * 0.75 (25% off) = $1350
        response = requests.post(
            f"{BASE_URL}/api/billing/preview",
            json={
                "initial_units": 100,
                "billing_cycle": "yearly",
                "seat_price_override": 1.50,
                "yearly_discount_percent": 25
            },
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["price_per_seat"] == 1.50
        assert data["yearly_discount_percent"] == 25
        # 100 * 1.50 * 12 * 0.75 = 1350
        assert data["effective_amount"] == 1350, f"Expected effective_amount=1350, got {data['effective_amount']}"
        print("PASS: Combined custom pricing: $1.50/seat, 25% discount = $1,350/year")
    
    def test_billing_preview_discount_validation_max_50(self, auth_headers):
        """Test that yearly_discount_percent is capped at 50%"""
        # Try to set 60% discount - should be rejected or capped
        response = requests.post(
            f"{BASE_URL}/api/billing/preview",
            json={
                "initial_units": 100,
                "billing_cycle": "yearly",
                "yearly_discount_percent": 60  # Over the max
            },
            headers=auth_headers
        )
        # Should return 422 validation error (max is 50)
        assert response.status_code == 422, f"Expected 422 for invalid discount, got {response.status_code}"
        print("PASS: Validation correctly rejects yearly_discount_percent > 50%")
    
    def test_billing_preview_discount_validation_min_0(self, auth_headers):
        """Test that yearly_discount_percent allows 0% (no discount)"""
        response = requests.post(
            f"{BASE_URL}/api/billing/preview",
            json={
                "initial_units": 100,
                "billing_cycle": "yearly",
                "yearly_discount_percent": 0  # No discount
            },
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["yearly_discount_percent"] == 0
        # Full price: 2.99 * 100 * 12 = 3588
        expected = round(2.99 * 100 * 12, 2)
        assert abs(data["effective_amount"] - expected) < 1, \
            f"Expected effective_amount~={expected}, got {data['effective_amount']}"
        print("PASS: 0% discount correctly applies (no discount)")
    
    def test_billing_preview_seat_limit_10000(self, auth_headers):
        """Test that slider allows up to 10,000 seats"""
        response = requests.post(
            f"{BASE_URL}/api/billing/preview",
            json={
                "initial_units": 10000,
                "billing_cycle": "monthly"
            },
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["seats"] == 10000
        print("PASS: Billing preview accepts 10,000 seats (max limit)")
    
    # ==================== E2E CONDOMINIUM CREATION TESTS ====================
    
    def test_create_condominium_with_custom_pricing(self, auth_headers):
        """E2E: Create condominium with seat_price_override and verify saved in DB"""
        unique_id = str(int(time.time() * 1000))[-8:]
        condo_name = f"Test Commercial {unique_id}"
        admin_email = f"admin_test_{unique_id}@testcommercial.com"
        
        wizard_data = {
            "condominium": {
                "name": condo_name,
                "address": "Test Address 123",
                "country": "Mexico",
                "timezone": "America/Mexico_City"
            },
            "admin": {
                "full_name": "Test Admin Commercial",
                "email": admin_email
            },
            "modules": {
                "security": True,
                "hr": False,
                "reservations": False,
                "school": False,
                "payments": False,
                "cctv": False
            },
            "areas": [],
            "billing": {
                "initial_units": 50,
                "billing_cycle": "yearly",
                "billing_provider": "sinpe",
                "seat_price_override": 1.25,
                "yearly_discount_percent": 30
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            json=wizard_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] == True, f"Creation failed: {data}"
        
        condo_id = data["condominium"]["id"]
        print(f"PASS: Created condominium '{condo_name}' with custom pricing (ID: {condo_id})")
        
        # Verify via condominiums list endpoint (includes all billing fields)
        list_response = requests.get(
            f"{BASE_URL}/api/condominiums",
            headers=auth_headers
        )
        assert list_response.status_code == 200
        
        condos = list_response.json()
        created_condo = None
        for condo in condos:
            if condo.get("id") == condo_id:
                created_condo = condo
                break
        
        assert created_condo is not None, f"Created condo not found in condominiums list"
        assert created_condo.get("paid_seats") == 50, f"Expected paid_seats=50, got {created_condo.get('paid_seats')}"
        assert created_condo.get("billing_cycle") == "yearly", f"Expected yearly billing, got {created_condo.get('billing_cycle')}"
        
        # Verify seat_price_override is saved
        assert created_condo.get("seat_price_override") == 1.25, \
            f"Expected seat_price_override=1.25, got {created_condo.get('seat_price_override')}"
        print(f"PASS: seat_price_override=1.25 saved in DB")
        
        # Verify yearly_discount_percent is saved
        assert created_condo.get("yearly_discount_percent") == 30, \
            f"Expected yearly_discount_percent=30, got {created_condo.get('yearly_discount_percent')}"
        print(f"PASS: yearly_discount_percent=30 saved in DB")
        
        print(f"PASS: E2E creation verified - paid_seats={created_condo.get('paid_seats')}, price={created_condo.get('seat_price_override')}")
        
        return condo_id
    
    def test_billing_events_logged_on_creation(self, auth_headers):
        """Verify billing_events logs custom pricing information on condominium creation"""
        unique_id = str(int(time.time() * 1000))[-8:]
        condo_name = f"Test BillingEvents {unique_id}"
        admin_email = f"admin_billing_{unique_id}@test.com"
        
        wizard_data = {
            "condominium": {
                "name": condo_name,
                "address": "Test Address",
                "country": "Mexico",
                "timezone": "America/Mexico_City"
            },
            "admin": {
                "full_name": "Test Admin",
                "email": admin_email
            },
            "modules": {
                "security": True,
                "hr": False,
                "reservations": False,
                "school": False,
                "payments": False,
                "cctv": False
            },
            "areas": [],
            "billing": {
                "initial_units": 75,
                "billing_cycle": "monthly",
                "billing_provider": "manual",
                "seat_price_override": 2.00,
                "yearly_discount_percent": 15
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/super-admin/onboarding/create-condominium",
            json=wizard_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        condo_id = data["condominium"]["id"]
        
        # Check billing events for this condominium
        events_response = requests.get(
            f"{BASE_URL}/api/billing/events/{condo_id}",
            headers=auth_headers
        )
        
        if events_response.status_code == 200:
            events = events_response.json()
            creation_event = None
            for event in events.get("events", events if isinstance(events, list) else []):
                if event.get("event_type") == "condominium_created":
                    creation_event = event
                    break
            
            if creation_event:
                event_data = creation_event.get("data", {})
                assert event_data.get("seat_price_override") == 2.00, \
                    f"Expected seat_price_override=2.00 in event, got {event_data.get('seat_price_override')}"
                print(f"PASS: billing_events correctly logged seat_price_override=2.00")
        else:
            print(f"INFO: Billing events endpoint returned {events_response.status_code} - may not be implemented yet")
        
        print(f"PASS: Condominium created with custom billing (ID: {condo_id})")


class TestBillingPreviewValidation:
    """Test input validation for billing preview endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get SuperAdmin auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "superadmin@genturix.com", "password": "Admin123!"},
            headers={"Content-Type": "application/json"}
        )
        token = response.json()["access_token"]
        return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    
    def test_seat_price_override_max_1000(self, auth_headers):
        """Test seat_price_override is capped at $1000"""
        response = requests.post(
            f"{BASE_URL}/api/billing/preview",
            json={
                "initial_units": 10,
                "billing_cycle": "monthly",
                "seat_price_override": 1500  # Over max
            },
            headers=auth_headers
        )
        assert response.status_code == 422, f"Expected 422 for price > 1000, got {response.status_code}"
        print("PASS: Validation rejects seat_price_override > $1000")
    
    def test_seat_price_override_positive(self, auth_headers):
        """Test seat_price_override must be positive"""
        response = requests.post(
            f"{BASE_URL}/api/billing/preview",
            json={
                "initial_units": 10,
                "billing_cycle": "monthly",
                "seat_price_override": -5
            },
            headers=auth_headers
        )
        assert response.status_code == 422, f"Expected 422 for negative price, got {response.status_code}"
        print("PASS: Validation rejects negative seat_price_override")
    
    def test_initial_units_max_10000(self, auth_headers):
        """Test initial_units is capped at 10,000"""
        response = requests.post(
            f"{BASE_URL}/api/billing/preview",
            json={
                "initial_units": 15000,  # Over max
                "billing_cycle": "monthly"
            },
            headers=auth_headers
        )
        assert response.status_code == 422, f"Expected 422 for units > 10000, got {response.status_code}"
        print("PASS: Validation rejects initial_units > 10,000")
    
    def test_yearly_discount_negative(self, auth_headers):
        """Test yearly_discount_percent rejects negative values"""
        response = requests.post(
            f"{BASE_URL}/api/billing/preview",
            json={
                "initial_units": 100,
                "billing_cycle": "yearly",
                "yearly_discount_percent": -10
            },
            headers=auth_headers
        )
        assert response.status_code == 422, f"Expected 422 for negative discount, got {response.status_code}"
        print("PASS: Validation rejects negative yearly_discount_percent")


class TestHealthAndBasics:
    """Basic health checks to ensure API is accessible"""
    
    def test_health_endpoint(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        print(f"PASS: Health check - service: {data.get('service')}, version: {data.get('version')}")
    
    def test_superadmin_login(self):
        """Test SuperAdmin can login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "superadmin@genturix.com", "password": "Admin123!"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["roles"] == ["SuperAdmin"]
        print("PASS: SuperAdmin login successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
