"""
SaaS Billing Module Tests
Tests for seat-based billing model with Stripe integration

Features tested:
1. GET /api/billing/info - Returns billing info for condominium
2. GET /api/billing/can-create-user - Check if can create new user
3. POST /api/admin/users - Blocked with 403 when seat limit reached
4. POST /api/admin/users - Succeeds when seats available
5. PATCH /api/super-admin/condominiums/{id}/billing - Update paid_seats
6. GET /api/super-admin/billing/overview - All condos billing overview
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "SuperAdmin123!"

# Known condominium ID from context
CONDO_ID = "46b9d344-a735-443a-8c9c-0e3d69c07824"  # Residencial Las Palmas


class TestBillingEndpoints:
    """Test billing API endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def superadmin_token(self):
        """Get superadmin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"SuperAdmin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def superadmin_headers(self, superadmin_token):
        return {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}

    # ==================== BILLING INFO TESTS ====================
    
    def test_get_billing_info_returns_correct_fields(self, admin_headers):
        """GET /api/billing/info returns paid_seats, active_users, remaining_seats, can_create_users"""
        response = requests.get(f"{BASE_URL}/api/billing/info", headers=admin_headers)
        
        assert response.status_code == 200, f"Failed to get billing info: {response.text}"
        data = response.json()
        
        # Verify all required fields are present
        assert "paid_seats" in data, "Missing paid_seats field"
        assert "active_users" in data, "Missing active_users field"
        assert "remaining_seats" in data, "Missing remaining_seats field"
        assert "can_create_users" in data, "Missing can_create_users field"
        assert "billing_status" in data, "Missing billing_status field"
        assert "condominium_id" in data, "Missing condominium_id field"
        assert "condominium_name" in data, "Missing condominium_name field"
        assert "price_per_seat" in data, "Missing price_per_seat field"
        assert "monthly_cost" in data, "Missing monthly_cost field"
        
        # Verify data types
        assert isinstance(data["paid_seats"], int), "paid_seats should be int"
        assert isinstance(data["active_users"], int), "active_users should be int"
        assert isinstance(data["remaining_seats"], int), "remaining_seats should be int"
        assert isinstance(data["can_create_users"], bool), "can_create_users should be bool"
        
        # Verify calculation: remaining_seats = paid_seats - active_users
        expected_remaining = max(0, data["paid_seats"] - data["active_users"])
        assert data["remaining_seats"] == expected_remaining, \
            f"remaining_seats calculation wrong: {data['remaining_seats']} != {expected_remaining}"
        
        print(f"✓ Billing info: {data['active_users']}/{data['paid_seats']} users, can_create={data['can_create_users']}")
    
    def test_can_create_user_endpoint(self, admin_headers):
        """GET /api/billing/can-create-user returns correct boolean based on seat limit"""
        response = requests.get(f"{BASE_URL}/api/billing/can-create-user", headers=admin_headers)
        
        assert response.status_code == 200, f"Failed to check can-create-user: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "can_create" in data, "Missing can_create field"
        assert "paid_seats" in data, "Missing paid_seats field"
        assert "active_users" in data, "Missing active_users field"
        assert "remaining_seats" in data, "Missing remaining_seats field"
        
        # Verify can_create logic
        expected_can_create = data["active_users"] < data["paid_seats"]
        assert data["can_create"] == expected_can_create, \
            f"can_create should be {expected_can_create} when {data['active_users']}/{data['paid_seats']}"
        
        print(f"✓ Can create user: {data['can_create']} ({data['remaining_seats']} seats remaining)")

    # ==================== SUPERADMIN BILLING TESTS ====================
    
    def test_superadmin_billing_overview(self, superadmin_headers):
        """GET /api/super-admin/billing/overview returns all condos with billing info"""
        response = requests.get(f"{BASE_URL}/api/super-admin/billing/overview", headers=superadmin_headers)
        
        assert response.status_code == 200, f"Failed to get billing overview: {response.text}"
        data = response.json()
        
        # Verify structure - API uses "totals" not "summary"
        assert "condominiums" in data, "Missing condominiums array"
        assert "totals" in data, "Missing totals object"
        assert isinstance(data["condominiums"], list), "condominiums should be a list"
        
        # Verify totals fields
        totals = data["totals"]
        assert "total_condominiums" in totals, "Missing total_condominiums in totals"
        assert "total_paid_seats" in totals, "Missing total_paid_seats in totals"
        assert "total_active_users" in totals, "Missing total_active_users in totals"
        assert "total_monthly_revenue" in totals, "Missing total_monthly_revenue in totals"
        
        # Verify each condominium has billing fields - API uses "condominium_id" not "id"
        for condo in data["condominiums"]:
            assert "condominium_id" in condo, "Missing condominium_id in condo"
            assert "condominium_name" in condo, "Missing condominium_name in condo"
            assert "paid_seats" in condo, "Missing paid_seats in condo"
            assert "active_users" in condo, "Missing active_users in condo"
            assert "remaining_seats" in condo, "Missing remaining_seats in condo"
            assert "billing_status" in condo, "Missing billing_status in condo"
        
        print(f"✓ Billing overview: {len(data['condominiums'])} condos, ${totals['total_monthly_revenue']}/month")
    
    def test_superadmin_update_paid_seats(self, superadmin_headers):
        """PATCH /api/super-admin/condominiums/{id}/billing updates paid_seats"""
        # First get current billing info
        response = requests.get(f"{BASE_URL}/api/super-admin/billing/overview", headers=superadmin_headers)
        assert response.status_code == 200
        
        # Find our test condo - API uses "condominium_id" not "id"
        condos = response.json()["condominiums"]
        test_condo = next((c for c in condos if c["condominium_id"] == CONDO_ID), None)
        
        if not test_condo:
            pytest.skip(f"Test condominium {CONDO_ID} not found")
        
        original_seats = test_condo["paid_seats"]
        new_seats = original_seats + 5
        
        # Update paid_seats
        response = requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{CONDO_ID}/billing?paid_seats={new_seats}",
            headers=superadmin_headers
        )
        
        assert response.status_code == 200, f"Failed to update paid_seats: {response.text}"
        data = response.json()
        
        # Verify update - API returns updates in "updates" field
        updates = data.get("updates", data)
        assert updates.get("paid_seats") == new_seats, f"paid_seats not updated: {updates.get('paid_seats')} != {new_seats}"
        
        # Restore original value
        response = requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{CONDO_ID}/billing?paid_seats={original_seats}",
            headers=superadmin_headers
        )
        assert response.status_code == 200, "Failed to restore original paid_seats"
        
        print(f"✓ Updated paid_seats: {original_seats} -> {new_seats} -> {original_seats} (restored)")
    
    def test_superadmin_cannot_downgrade_below_active_users(self, superadmin_headers):
        """PATCH /api/super-admin/condominiums/{id}/billing prevents downgrade below active_users"""
        # Get current billing info
        response = requests.get(f"{BASE_URL}/api/super-admin/billing/overview", headers=superadmin_headers)
        assert response.status_code == 200
        
        condos = response.json()["condominiums"]
        test_condo = next((c for c in condos if c["condominium_id"] == CONDO_ID), None)
        
        if not test_condo:
            pytest.skip(f"Test condominium {CONDO_ID} not found")
        
        active_users = test_condo["active_users"]
        
        if active_users == 0:
            pytest.skip("No active users to test downgrade prevention")
        
        # Try to set paid_seats below active_users
        invalid_seats = active_users - 1
        response = requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{CONDO_ID}/billing?paid_seats={invalid_seats}",
            headers=superadmin_headers
        )
        
        # Should fail with 400
        assert response.status_code == 400, \
            f"Should reject downgrade below active users, got {response.status_code}: {response.text}"
        
        error_data = response.json()
        assert "detail" in error_data, "Error response should have detail"
        assert str(active_users) in error_data["detail"], \
            f"Error should mention active users count: {error_data['detail']}"
        
        print(f"✓ Correctly blocked downgrade to {invalid_seats} seats (have {active_users} active users)")


class TestSeatLimitEnforcement:
    """Test user creation blocked when seat limit reached"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def superadmin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def superadmin_headers(self, superadmin_token):
        return {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}
    
    def test_user_creation_blocked_at_seat_limit(self, admin_headers, superadmin_headers):
        """POST /api/admin/users returns 403 when seat limit reached"""
        # Step 1: Get current billing info
        response = requests.get(f"{BASE_URL}/api/billing/info", headers=admin_headers)
        assert response.status_code == 200
        billing = response.json()
        
        original_paid_seats = billing["paid_seats"]
        active_users = billing["active_users"]
        
        print(f"Current state: {active_users}/{original_paid_seats} users")
        
        # Step 2: Set paid_seats equal to active_users (at limit)
        response = requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{CONDO_ID}/billing?paid_seats={active_users}",
            headers=superadmin_headers
        )
        assert response.status_code == 200, f"Failed to set seat limit: {response.text}"
        
        try:
            # Step 3: Try to create a user - should fail with 403
            test_email = f"test_blocked_{uuid.uuid4().hex[:8]}@test.com"
            user_data = {
                "email": test_email,
                "password": "TestPass123!",
                "full_name": "Test Blocked User",
                "role": "Residente",
                "apartment_number": "TEST-999"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/admin/users",
                headers=admin_headers,
                json=user_data
            )
            
            # Should be 403 Forbidden
            assert response.status_code == 403, \
                f"Expected 403 when at seat limit, got {response.status_code}: {response.text}"
            
            error_data = response.json()
            assert "detail" in error_data, "Error should have detail message"
            assert "límite" in error_data["detail"].lower() or "limit" in error_data["detail"].lower(), \
                f"Error should mention limit: {error_data['detail']}"
            
            print(f"✓ User creation correctly blocked with 403: {error_data['detail']}")
            
        finally:
            # Step 4: Restore original paid_seats
            response = requests.patch(
                f"{BASE_URL}/api/super-admin/condominiums/{CONDO_ID}/billing?paid_seats={original_paid_seats}",
                headers=superadmin_headers
            )
            assert response.status_code == 200, "Failed to restore paid_seats"
            print(f"✓ Restored paid_seats to {original_paid_seats}")
    
    def test_user_creation_succeeds_with_available_seats(self, admin_headers, superadmin_headers):
        """POST /api/admin/users succeeds when seats available and updates active_users count"""
        # Step 1: Get current billing info
        response = requests.get(f"{BASE_URL}/api/billing/info", headers=admin_headers)
        assert response.status_code == 200
        billing_before = response.json()
        
        # Ensure we have available seats
        if billing_before["remaining_seats"] <= 0:
            # Add more seats
            new_seats = billing_before["paid_seats"] + 5
            response = requests.patch(
                f"{BASE_URL}/api/super-admin/condominiums/{CONDO_ID}/billing?paid_seats={new_seats}",
                headers=superadmin_headers
            )
            assert response.status_code == 200
        
        # Step 2: Create a user
        test_email = f"test_billing_{uuid.uuid4().hex[:8]}@test.com"
        user_data = {
            "email": test_email,
            "password": "TestPass123!",
            "full_name": "Test Billing User",
            "role": "Residente",
            "apartment_number": "BILLING-001"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/users",
            headers=admin_headers,
            json=user_data
        )
        
        # API returns 200 for successful user creation (not 201)
        assert response.status_code in [200, 201], f"User creation failed: {response.text}"
        created_user = response.json()
        
        # Step 3: Verify active_users count increased
        response = requests.get(f"{BASE_URL}/api/billing/info", headers=admin_headers)
        assert response.status_code == 200
        billing_after = response.json()
        
        assert billing_after["active_users"] == billing_before["active_users"] + 1, \
            f"active_users should increase by 1: {billing_before['active_users']} -> {billing_after['active_users']}"
        
        assert billing_after["remaining_seats"] == billing_before["remaining_seats"] - 1, \
            f"remaining_seats should decrease by 1"
        
        print(f"✓ User created successfully, active_users: {billing_before['active_users']} -> {billing_after['active_users']}")
        print(f"✓ Created user: {created_user.get('email')}")


class TestBillingStatusEffects:
    """Test billing status affects user creation"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def superadmin_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    @pytest.fixture(scope="class")
    def superadmin_headers(self, superadmin_token):
        return {"Authorization": f"Bearer {superadmin_token}", "Content-Type": "application/json"}
    
    def test_billing_status_active_allows_creation(self, admin_headers, superadmin_headers):
        """Verify billing_status='active' allows user creation"""
        # Ensure status is active
        response = requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{CONDO_ID}/billing?billing_status=active",
            headers=superadmin_headers
        )
        assert response.status_code == 200
        
        # Check can_create_users
        response = requests.get(f"{BASE_URL}/api/billing/info", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        
        # If we have remaining seats, can_create_users should be True
        if data["remaining_seats"] > 0:
            assert data["can_create_users"] == True, \
                f"can_create_users should be True with active status and {data['remaining_seats']} remaining seats"
        
        print(f"✓ billing_status=active, can_create_users={data['can_create_users']}")
    
    def test_billing_status_trialing_allows_creation(self, admin_headers, superadmin_headers):
        """Verify billing_status='trialing' allows user creation"""
        # Get original status
        response = requests.get(f"{BASE_URL}/api/billing/info", headers=admin_headers)
        original_status = response.json().get("billing_status", "active")
        
        # Set to trialing
        response = requests.patch(
            f"{BASE_URL}/api/super-admin/condominiums/{CONDO_ID}/billing?billing_status=trialing",
            headers=superadmin_headers
        )
        assert response.status_code == 200
        
        try:
            # Check can_create_users
            response = requests.get(f"{BASE_URL}/api/billing/info", headers=admin_headers)
            assert response.status_code == 200
            data = response.json()
            
            if data["remaining_seats"] > 0:
                assert data["can_create_users"] == True, \
                    f"can_create_users should be True with trialing status"
            
            print(f"✓ billing_status=trialing, can_create_users={data['can_create_users']}")
            
        finally:
            # Restore original status
            response = requests.patch(
                f"{BASE_URL}/api/super-admin/condominiums/{CONDO_ID}/billing?billing_status={original_status}",
                headers=superadmin_headers
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
