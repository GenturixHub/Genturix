"""
Test Suite: Admin Onboarding via Invite Link / QR
Tests for invitation creation, access request submission, and approval/rejection flows.

Features tested:
- Admin can create invitation with different expiration options (7/30/90/365 days)
- Admin can create invitation with different usage limits (single/unlimited/fixed)
- Admin can revoke an active invitation
- Invitation list shows correct status (Active/Expired/Revoked)
- Public /join/{token} page displays condominium name correctly
- Resident can submit access request via public form
- Access request appears in Admin's Solicitudes tab with badge count
- Admin can approve request - user is created
- Admin can reject request
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


class TestInvitationAccessRequests:
    """Test suite for invitation and access request functionality"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get headers with admin auth token"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    # ==================== INVITATION CREATION TESTS ====================
    
    def test_create_invitation_7_days_single_use(self, admin_headers):
        """Test creating invitation with 7 days expiration and single use"""
        response = requests.post(f"{BASE_URL}/api/invitations", 
            headers=admin_headers,
            json={
                "expiration_days": 7,
                "usage_limit_type": "single",
                "max_uses": 1,
                "notes": "TEST_7day_single"
            }
        )
        assert response.status_code == 200, f"Failed to create invitation: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "token" in data
        assert data["usage_limit_type"] == "single"
        assert data["max_uses"] == 1
        assert data["current_uses"] == 0
        assert data["is_active"] == True
        assert data["is_expired"] == False
        assert "invite_url" in data
        assert data["notes"] == "TEST_7day_single"
        
        print(f"✓ Created 7-day single-use invitation: {data['token'][:16]}...")
    
    def test_create_invitation_30_days_unlimited(self, admin_headers):
        """Test creating invitation with 30 days expiration and unlimited uses"""
        response = requests.post(f"{BASE_URL}/api/invitations", 
            headers=admin_headers,
            json={
                "expiration_days": 30,
                "usage_limit_type": "unlimited",
                "notes": "TEST_30day_unlimited"
            }
        )
        assert response.status_code == 200, f"Failed to create invitation: {response.text}"
        data = response.json()
        
        assert data["usage_limit_type"] == "unlimited"
        assert data["max_uses"] == 999999  # Effectively unlimited
        assert data["is_active"] == True
        
        print(f"✓ Created 30-day unlimited invitation: {data['token'][:16]}...")
    
    def test_create_invitation_90_days_fixed_uses(self, admin_headers):
        """Test creating invitation with 90 days expiration and fixed number of uses"""
        response = requests.post(f"{BASE_URL}/api/invitations", 
            headers=admin_headers,
            json={
                "expiration_days": 90,
                "usage_limit_type": "fixed",
                "max_uses": 10,
                "notes": "TEST_90day_fixed10"
            }
        )
        assert response.status_code == 200, f"Failed to create invitation: {response.text}"
        data = response.json()
        
        assert data["usage_limit_type"] == "fixed"
        assert data["max_uses"] == 10
        assert data["is_active"] == True
        
        print(f"✓ Created 90-day fixed-10-uses invitation: {data['token'][:16]}...")
    
    def test_create_invitation_365_days(self, admin_headers):
        """Test creating invitation with 365 days (1 year) expiration"""
        response = requests.post(f"{BASE_URL}/api/invitations", 
            headers=admin_headers,
            json={
                "expiration_days": 365,
                "usage_limit_type": "single",
                "notes": "TEST_365day"
            }
        )
        assert response.status_code == 200, f"Failed to create invitation: {response.text}"
        data = response.json()
        
        assert data["is_active"] == True
        assert data["is_expired"] == False
        
        print(f"✓ Created 365-day invitation: {data['token'][:16]}...")
    
    # ==================== INVITATION LIST TESTS ====================
    
    def test_get_invitations_list(self, admin_headers):
        """Test getting list of all invitations"""
        response = requests.get(f"{BASE_URL}/api/invitations", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get invitations: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0, "Expected at least one invitation"
        
        # Verify each invitation has required fields
        for inv in data:
            assert "id" in inv
            assert "token" in inv
            assert "is_active" in inv
            assert "is_expired" in inv
            assert "expires_at" in inv
            assert "usage_limit_type" in inv
            assert "max_uses" in inv
            assert "current_uses" in inv
        
        print(f"✓ Retrieved {len(data)} invitations")
    
    # ==================== INVITATION REVOCATION TESTS ====================
    
    def test_revoke_invitation(self, admin_headers):
        """Test revoking an active invitation"""
        # First create an invitation to revoke
        create_response = requests.post(f"{BASE_URL}/api/invitations", 
            headers=admin_headers,
            json={
                "expiration_days": 7,
                "usage_limit_type": "single",
                "notes": "TEST_to_revoke"
            }
        )
        assert create_response.status_code == 200
        invitation = create_response.json()
        invitation_id = invitation["id"]
        
        # Revoke the invitation
        revoke_response = requests.delete(
            f"{BASE_URL}/api/invitations/{invitation_id}",
            headers=admin_headers
        )
        assert revoke_response.status_code == 200, f"Failed to revoke: {revoke_response.text}"
        
        # Verify it's revoked by checking the list
        list_response = requests.get(f"{BASE_URL}/api/invitations", headers=admin_headers)
        invitations = list_response.json()
        
        revoked_inv = next((inv for inv in invitations if inv["id"] == invitation_id), None)
        assert revoked_inv is not None
        assert revoked_inv["is_active"] == False
        
        print(f"✓ Successfully revoked invitation: {invitation_id[:16]}...")
    
    # ==================== PUBLIC INVITATION INFO TESTS ====================
    
    def test_get_public_invitation_info(self, admin_headers):
        """Test getting public invitation info (no auth required)"""
        # Create a fresh invitation
        create_response = requests.post(f"{BASE_URL}/api/invitations", 
            headers=admin_headers,
            json={
                "expiration_days": 7,
                "usage_limit_type": "unlimited",
                "notes": "TEST_public_info"
            }
        )
        assert create_response.status_code == 200
        invitation = create_response.json()
        token = invitation["token"]
        
        # Get public info (no auth)
        info_response = requests.get(f"{BASE_URL}/api/invitations/{token}/info")
        assert info_response.status_code == 200, f"Failed to get public info: {info_response.text}"
        data = info_response.json()
        
        assert "condominium_name" in data
        assert data["is_valid"] == True
        assert len(data["condominium_name"]) > 0
        
        print(f"✓ Public invitation info shows condominium: {data['condominium_name']}")
    
    def test_invalid_token_returns_404(self):
        """Test that invalid token returns 404"""
        response = requests.get(f"{BASE_URL}/api/invitations/invalid-token-12345/info")
        assert response.status_code == 404
        print("✓ Invalid token correctly returns 404")
    
    def test_revoked_invitation_returns_error(self, admin_headers):
        """Test that revoked invitation returns error"""
        # Create and revoke an invitation
        create_response = requests.post(f"{BASE_URL}/api/invitations", 
            headers=admin_headers,
            json={
                "expiration_days": 7,
                "usage_limit_type": "single",
                "notes": "TEST_revoked_check"
            }
        )
        invitation = create_response.json()
        token = invitation["token"]
        
        # Revoke it
        requests.delete(f"{BASE_URL}/api/invitations/{invitation['id']}", headers=admin_headers)
        
        # Try to get public info
        info_response = requests.get(f"{BASE_URL}/api/invitations/{token}/info")
        assert info_response.status_code == 400
        assert "revocada" in info_response.json().get("detail", "").lower()
        
        print("✓ Revoked invitation correctly returns error")
    
    # ==================== ACCESS REQUEST SUBMISSION TESTS ====================
    
    def test_submit_access_request(self, admin_headers):
        """Test submitting an access request via public form"""
        # Create a fresh invitation
        create_response = requests.post(f"{BASE_URL}/api/invitations", 
            headers=admin_headers,
            json={
                "expiration_days": 7,
                "usage_limit_type": "unlimited",
                "notes": "TEST_access_request"
            }
        )
        invitation = create_response.json()
        token = invitation["token"]
        
        # Submit access request (no auth)
        unique_email = f"test_resident_{uuid.uuid4().hex[:8]}@example.com"
        request_response = requests.post(
            f"{BASE_URL}/api/invitations/{token}/request",
            json={
                "full_name": "TEST Resident User",
                "email": unique_email,
                "phone": "+52 555 123 4567",
                "apartment_number": "TEST-101",
                "tower_block": "Torre A",
                "resident_type": "owner",
                "notes": "Test access request"
            }
        )
        assert request_response.status_code == 200, f"Failed to submit request: {request_response.text}"
        data = request_response.json()
        
        assert "id" in data
        assert data["status"] == "pending_approval"
        assert "message" in data
        
        print(f"✓ Access request submitted: {data['id'][:16]}...")
        return data["id"], unique_email
    
    def test_duplicate_email_rejected(self, admin_headers):
        """Test that duplicate email is rejected"""
        # Create invitation
        create_response = requests.post(f"{BASE_URL}/api/invitations", 
            headers=admin_headers,
            json={
                "expiration_days": 7,
                "usage_limit_type": "unlimited",
                "notes": "TEST_duplicate_check"
            }
        )
        invitation = create_response.json()
        token = invitation["token"]
        
        # Submit first request
        unique_email = f"test_dup_{uuid.uuid4().hex[:8]}@example.com"
        first_response = requests.post(
            f"{BASE_URL}/api/invitations/{token}/request",
            json={
                "full_name": "TEST First User",
                "email": unique_email,
                "apartment_number": "TEST-201"
            }
        )
        assert first_response.status_code == 200
        
        # Try to submit duplicate
        dup_response = requests.post(
            f"{BASE_URL}/api/invitations/{token}/request",
            json={
                "full_name": "TEST Duplicate User",
                "email": unique_email,
                "apartment_number": "TEST-202"
            }
        )
        assert dup_response.status_code == 400
        assert "pendiente" in dup_response.json().get("detail", "").lower()
        
        print("✓ Duplicate email correctly rejected")
    
    # ==================== ACCESS REQUEST COUNT TESTS ====================
    
    def test_access_requests_count(self, admin_headers):
        """Test getting pending access requests count"""
        response = requests.get(f"{BASE_URL}/api/access-requests/count", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get count: {response.text}"
        data = response.json()
        
        assert "pending" in data
        assert isinstance(data["pending"], int)
        assert data["pending"] >= 0
        
        print(f"✓ Pending access requests count: {data['pending']}")
    
    # ==================== ACCESS REQUEST LIST TESTS ====================
    
    def test_get_access_requests_list(self, admin_headers):
        """Test getting list of access requests"""
        response = requests.get(f"{BASE_URL}/api/access-requests", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get requests: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        
        # Verify structure of each request
        for req in data:
            assert "id" in req
            assert "full_name" in req
            assert "email" in req
            assert "status" in req
            assert "apartment_number" in req
            assert "created_at" in req
        
        print(f"✓ Retrieved {len(data)} access requests")
    
    def test_filter_access_requests_by_status(self, admin_headers):
        """Test filtering access requests by status"""
        # Get pending requests
        pending_response = requests.get(
            f"{BASE_URL}/api/access-requests?status=pending_approval",
            headers=admin_headers
        )
        assert pending_response.status_code == 200
        pending_data = pending_response.json()
        
        # All should be pending
        for req in pending_data:
            assert req["status"] == "pending_approval"
        
        print(f"✓ Filtered pending requests: {len(pending_data)}")
    
    # ==================== ACCESS REQUEST APPROVAL TESTS ====================
    
    def test_approve_access_request(self, admin_headers):
        """Test approving an access request - user should be created"""
        # Create invitation and submit request
        create_response = requests.post(f"{BASE_URL}/api/invitations", 
            headers=admin_headers,
            json={
                "expiration_days": 7,
                "usage_limit_type": "unlimited",
                "notes": "TEST_approval"
            }
        )
        invitation = create_response.json()
        token = invitation["token"]
        
        # Submit access request
        unique_email = f"test_approve_{uuid.uuid4().hex[:8]}@example.com"
        request_response = requests.post(
            f"{BASE_URL}/api/invitations/{token}/request",
            json={
                "full_name": "TEST Approved User",
                "email": unique_email,
                "apartment_number": "TEST-301",
                "tower_block": "Torre B",
                "resident_type": "tenant"
            }
        )
        request_id = request_response.json()["id"]
        
        # Approve the request
        approve_response = requests.post(
            f"{BASE_URL}/api/access-requests/{request_id}/action",
            headers=admin_headers,
            json={
                "action": "approve",
                "message": "Bienvenido al condominio",
                "send_email": False  # Don't send email in test
            }
        )
        assert approve_response.status_code == 200, f"Failed to approve: {approve_response.text}"
        data = approve_response.json()
        
        assert "user_id" in data
        assert "credentials" in data
        assert data["credentials"]["email"] == unique_email
        
        # Verify user was created by trying to login
        # (Note: password_reset_required will be True)
        
        print(f"✓ Access request approved, user created: {data['user_id'][:16]}...")
        
        # Verify request status changed
        requests_list = requests.get(f"{BASE_URL}/api/access-requests", headers=admin_headers).json()
        approved_req = next((r for r in requests_list if r["id"] == request_id), None)
        assert approved_req is not None
        assert approved_req["status"] == "approved"
        
        print("✓ Request status updated to 'approved'")
    
    # ==================== ACCESS REQUEST REJECTION TESTS ====================
    
    def test_reject_access_request(self, admin_headers):
        """Test rejecting an access request"""
        # Create invitation and submit request
        create_response = requests.post(f"{BASE_URL}/api/invitations", 
            headers=admin_headers,
            json={
                "expiration_days": 7,
                "usage_limit_type": "unlimited",
                "notes": "TEST_rejection"
            }
        )
        invitation = create_response.json()
        token = invitation["token"]
        
        # Submit access request
        unique_email = f"test_reject_{uuid.uuid4().hex[:8]}@example.com"
        request_response = requests.post(
            f"{BASE_URL}/api/invitations/{token}/request",
            json={
                "full_name": "TEST Rejected User",
                "email": unique_email,
                "apartment_number": "TEST-401"
            }
        )
        request_id = request_response.json()["id"]
        
        # Reject the request
        reject_response = requests.post(
            f"{BASE_URL}/api/access-requests/{request_id}/action",
            headers=admin_headers,
            json={
                "action": "reject",
                "message": "No se pudo verificar la información proporcionada",
                "send_email": False
            }
        )
        assert reject_response.status_code == 200, f"Failed to reject: {reject_response.text}"
        
        # Verify request status changed
        requests_list = requests.get(f"{BASE_URL}/api/access-requests", headers=admin_headers).json()
        rejected_req = next((r for r in requests_list if r["id"] == request_id), None)
        assert rejected_req is not None
        assert rejected_req["status"] == "rejected"
        assert rejected_req["status_message"] == "No se pudo verificar la información proporcionada"
        
        print(f"✓ Access request rejected: {request_id[:16]}...")
    
    # ==================== REQUEST STATUS CHECK TESTS ====================
    
    def test_check_request_status(self, admin_headers):
        """Test checking request status via public endpoint"""
        # Create invitation and submit request
        create_response = requests.post(f"{BASE_URL}/api/invitations", 
            headers=admin_headers,
            json={
                "expiration_days": 7,
                "usage_limit_type": "unlimited",
                "notes": "TEST_status_check"
            }
        )
        invitation = create_response.json()
        token = invitation["token"]
        
        # Submit access request
        unique_email = f"test_status_{uuid.uuid4().hex[:8]}@example.com"
        requests.post(
            f"{BASE_URL}/api/invitations/{token}/request",
            json={
                "full_name": "TEST Status Check User",
                "email": unique_email,
                "apartment_number": "TEST-501"
            }
        )
        
        # Check status (no auth)
        status_response = requests.get(
            f"{BASE_URL}/api/invitations/{token}/request-status?email={unique_email}"
        )
        assert status_response.status_code == 200, f"Failed to check status: {status_response.text}"
        data = status_response.json()
        
        assert data["status"] == "pending_approval"
        assert "created_at" in data
        
        print(f"✓ Request status check works: {data['status']}")
    
    # ==================== SINGLE USE LIMIT TESTS ====================
    
    def test_single_use_invitation_limit(self, admin_headers):
        """Test that single-use invitation can only be used once"""
        # Create single-use invitation
        create_response = requests.post(f"{BASE_URL}/api/invitations", 
            headers=admin_headers,
            json={
                "expiration_days": 7,
                "usage_limit_type": "single",
                "notes": "TEST_single_use_limit"
            }
        )
        invitation = create_response.json()
        token = invitation["token"]
        
        # First request should succeed
        first_email = f"test_first_{uuid.uuid4().hex[:8]}@example.com"
        first_response = requests.post(
            f"{BASE_URL}/api/invitations/{token}/request",
            json={
                "full_name": "TEST First Single Use",
                "email": first_email,
                "apartment_number": "TEST-601"
            }
        )
        assert first_response.status_code == 200
        
        # Second request should fail (limit reached)
        second_email = f"test_second_{uuid.uuid4().hex[:8]}@example.com"
        second_response = requests.post(
            f"{BASE_URL}/api/invitations/{token}/request",
            json={
                "full_name": "TEST Second Single Use",
                "email": second_email,
                "apartment_number": "TEST-602"
            }
        )
        assert second_response.status_code == 400
        assert "límite" in second_response.json().get("detail", "").lower()
        
        print("✓ Single-use invitation correctly limits to one use")
    
    # ==================== CLEANUP ====================
    
    @pytest.fixture(scope="class", autouse=True)
    def cleanup_test_data(self, admin_headers):
        """Cleanup test data after all tests complete"""
        yield
        # Note: In a real scenario, we'd clean up TEST_ prefixed data
        # For now, we leave the data as it doesn't affect other tests
        print("\n✓ Test suite completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
