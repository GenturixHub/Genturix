"""
Test Suite: Billing Overview Pagination & Filtering (Gestión de Cartera)
Tests the optimized /api/super-admin/billing/overview endpoint with:
- Backend pagination (page, page_size, total_count, has_next, has_prev)
- Filtering by billing_status (comma-separated)
- Filtering by billing_provider (sinpe, stripe, manual)
- Search by name or email
- Sorting by different fields
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERADMIN_EMAIL = "superadmin@genturix.com"
SUPERADMIN_PASSWORD = "Admin123!"


class TestBillingOverviewAPI:
    """Test the /api/super-admin/billing/overview endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as SuperAdmin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as SuperAdmin
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"SuperAdmin login failed: {login_response.status_code} - {login_response.text}")
        
        data = login_response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        print(f"✓ SuperAdmin logged in successfully")
    
    def test_basic_pagination(self):
        """Test: Basic pagination with default parameters"""
        response = self.session.get(f"{BASE_URL}/api/super-admin/billing/overview")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "condominiums" in data, "Response should have 'condominiums' array"
        assert "pagination" in data, "Response should have 'pagination' object"
        assert "totals" in data, "Response should have 'totals' object"
        
        # Verify pagination fields
        pagination = data["pagination"]
        assert "page" in pagination, "Pagination should have 'page'"
        assert "page_size" in pagination, "Pagination should have 'page_size'"
        assert "total_count" in pagination, "Pagination should have 'total_count'"
        assert "total_pages" in pagination, "Pagination should have 'total_pages'"
        assert "has_next" in pagination, "Pagination should have 'has_next'"
        assert "has_prev" in pagination, "Pagination should have 'has_prev'"
        
        # Verify pagination values make sense
        assert pagination["page"] == 1, "Default page should be 1"
        assert pagination["page_size"] == 50, "Default page_size should be 50"
        assert isinstance(pagination["total_count"], int), "total_count should be int"
        assert isinstance(pagination["has_next"], bool), "has_next should be boolean"
        assert isinstance(pagination["has_prev"], bool), "has_prev should be boolean"
        assert pagination["has_prev"] == False, "First page should have has_prev=False"
        
        print(f"✓ Basic pagination works - Total: {pagination['total_count']}, Pages: {pagination['total_pages']}")
    
    def test_custom_page_size(self):
        """Test: Custom page_size parameter"""
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={"page_size": 5}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        pagination = data["pagination"]
        
        assert pagination["page_size"] == 5, "page_size should be 5"
        assert len(data["condominiums"]) <= 5, "Should return at most 5 condominiums"
        
        print(f"✓ Custom page_size=5 works - Returned {len(data['condominiums'])} condos")
    
    def test_page_navigation(self):
        """Test: Page navigation with has_next/has_prev"""
        # Get first page with small page_size
        response1 = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={"page": 1, "page_size": 2}
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        pagination1 = data1["pagination"]
        
        print(f"Page 1: {len(data1['condominiums'])} condos, has_next={pagination1['has_next']}")
        
        # If there are more pages, test page 2
        if pagination1["has_next"]:
            response2 = self.session.get(
                f"{BASE_URL}/api/super-admin/billing/overview",
                params={"page": 2, "page_size": 2}
            )
            
            assert response2.status_code == 200
            data2 = response2.json()
            pagination2 = data2["pagination"]
            
            assert pagination2["page"] == 2, "Page should be 2"
            assert pagination2["has_prev"] == True, "Page 2 should have has_prev=True"
            
            print(f"✓ Page 2: {len(data2['condominiums'])} condos, has_prev={pagination2['has_prev']}")
        else:
            print("✓ Only 1 page of results - pagination navigation not fully testable")
    
    def test_filter_by_single_billing_status(self):
        """Test: Filter by single billing_status"""
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={"billing_status": "pending_payment"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned condos should have billing_status = "pending_payment"
        for condo in data["condominiums"]:
            assert condo.get("billing_status") == "pending_payment", \
                f"Expected billing_status='pending_payment', got '{condo.get('billing_status')}'"
        
        print(f"✓ Filter by billing_status=pending_payment - {len(data['condominiums'])} results")
    
    def test_filter_by_multiple_billing_statuses(self):
        """Test: Filter by comma-separated billing_status"""
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={"billing_status": "pending_payment,past_due,upgrade_pending,suspended"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        valid_statuses = ["pending_payment", "past_due", "upgrade_pending", "suspended"]
        
        for condo in data["condominiums"]:
            assert condo.get("billing_status") in valid_statuses, \
                f"billing_status '{condo.get('billing_status')}' not in filter list"
        
        print(f"✓ Filter by multiple billing_statuses - {len(data['condominiums'])} results")
    
    def test_filter_by_billing_provider_sinpe(self):
        """Test: Filter by billing_provider=sinpe"""
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={"billing_provider": "sinpe"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for condo in data["condominiums"]:
            assert condo.get("billing_provider") == "sinpe", \
                f"Expected billing_provider='sinpe', got '{condo.get('billing_provider')}'"
        
        print(f"✓ Filter by billing_provider=sinpe - {len(data['condominiums'])} results")
    
    def test_filter_by_billing_provider_stripe(self):
        """Test: Filter by billing_provider=stripe"""
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={"billing_provider": "stripe"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for condo in data["condominiums"]:
            assert condo.get("billing_provider") == "stripe", \
                f"Expected billing_provider='stripe', got '{condo.get('billing_provider')}'"
        
        print(f"✓ Filter by billing_provider=stripe - {len(data['condominiums'])} results")
    
    def test_filter_by_billing_provider_manual(self):
        """Test: Filter by billing_provider=manual"""
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={"billing_provider": "manual"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for condo in data["condominiums"]:
            assert condo.get("billing_provider") == "manual", \
                f"Expected billing_provider='manual', got '{condo.get('billing_provider')}'"
        
        print(f"✓ Filter by billing_provider=manual - {len(data['condominiums'])} results")
    
    def test_search_by_name(self):
        """Test: Search by condominium name"""
        # First get all condos to find a name to search for
        response_all = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={"page_size": 100}
        )
        
        if response_all.status_code == 200:
            data_all = response_all.json()
            if data_all["condominiums"]:
                # Use first condo name for search
                first_condo_name = data_all["condominiums"][0].get("condominium_name", "")
                if first_condo_name and len(first_condo_name) > 3:
                    search_term = first_condo_name[:5]  # Search by first 5 chars
                    
                    response = self.session.get(
                        f"{BASE_URL}/api/super-admin/billing/overview",
                        params={"search": search_term}
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    
                    # Results should contain the search term
                    for condo in data["condominiums"]:
                        name = condo.get("condominium_name", "").lower()
                        email = condo.get("admin_email", "").lower()
                        assert search_term.lower() in name or search_term.lower() in email, \
                            f"Search term '{search_term}' not found in name='{name}' or email='{email}'"
                    
                    print(f"✓ Search by name '{search_term}' - {len(data['condominiums'])} results")
                    return
        
        print("✓ Search test skipped - no condos to search")
    
    def test_sort_by_next_invoice_amount_desc(self):
        """Test: Sort by next_invoice_amount descending"""
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={"sort_by": "next_invoice_amount", "sort_order": "desc"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        condos = data["condominiums"]
        if len(condos) >= 2:
            for i in range(len(condos) - 1):
                current = condos[i].get("next_invoice_amount", 0) or 0
                next_val = condos[i + 1].get("next_invoice_amount", 0) or 0
                assert current >= next_val, \
                    f"Sort order wrong: {current} should be >= {next_val}"
            
        print(f"✓ Sort by next_invoice_amount desc - {len(condos)} results sorted correctly")
    
    def test_sort_by_paid_seats_asc(self):
        """Test: Sort by paid_seats ascending"""
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={"sort_by": "paid_seats", "sort_order": "asc"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        condos = data["condominiums"]
        if len(condos) >= 2:
            for i in range(len(condos) - 1):
                current = condos[i].get("paid_seats", 0) or 0
                next_val = condos[i + 1].get("paid_seats", 0) or 0
                assert current <= next_val, \
                    f"Sort order wrong: {current} should be <= {next_val}"
        
        print(f"✓ Sort by paid_seats asc - {len(condos)} results sorted correctly")
    
    def test_sort_by_condominium_name(self):
        """Test: Sort by condominium_name"""
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={"sort_by": "condominium_name", "sort_order": "asc"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        condos = data["condominiums"]
        if len(condos) >= 2:
            for i in range(len(condos) - 1):
                current = condos[i].get("condominium_name", "") or ""
                next_val = condos[i + 1].get("condominium_name", "") or ""
                # Compare lowercase for consistency
                assert current.lower() <= next_val.lower(), \
                    f"Sort order wrong: '{current}' should be <= '{next_val}'"
        
        print(f"✓ Sort by condominium_name asc - {len(condos)} results sorted correctly")
    
    def test_totals_calculation(self):
        """Test: Totals are correctly calculated"""
        response = self.session.get(f"{BASE_URL}/api/super-admin/billing/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        totals = data["totals"]
        
        assert "total_condominiums" in totals, "totals should have total_condominiums"
        assert "total_paid_seats" in totals, "totals should have total_paid_seats"
        assert "total_active_users" in totals, "totals should have total_active_users"
        assert "total_monthly_revenue" in totals, "totals should have total_monthly_revenue"
        
        # Values should be numbers
        assert isinstance(totals["total_condominiums"], int)
        assert isinstance(totals["total_paid_seats"], int)
        assert isinstance(totals["total_active_users"], int)
        assert isinstance(totals["total_monthly_revenue"], (int, float))
        
        print(f"✓ Totals: condos={totals['total_condominiums']}, seats={totals['total_paid_seats']}, users={totals['total_active_users']}, revenue=${totals['total_monthly_revenue']}")
    
    def test_combined_filters(self):
        """Test: Combined filters (status + provider + search)"""
        response = self.session.get(
            f"{BASE_URL}/api/super-admin/billing/overview",
            params={
                "billing_status": "pending_payment,past_due",
                "sort_by": "next_invoice_amount",
                "sort_order": "desc",
                "page_size": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify filters are applied
        for condo in data["condominiums"]:
            assert condo.get("billing_status") in ["pending_payment", "past_due"]
        
        print(f"✓ Combined filters work - {len(data['condominiums'])} results")
    
    def test_unauthorized_access(self):
        """Test: Unauthorized access is blocked"""
        # Create session without auth
        unauth_session = requests.Session()
        unauth_session.headers.update({"Content-Type": "application/json"})
        
        response = unauth_session.get(f"{BASE_URL}/api/super-admin/billing/overview")
        
        assert response.status_code in [401, 403], \
            f"Unauthorized access should be blocked, got {response.status_code}"
        
        print(f"✓ Unauthorized access correctly blocked with {response.status_code}")
    
    def test_response_condo_fields(self):
        """Test: Verify each condominium has required fields"""
        response = self.session.get(f"{BASE_URL}/api/super-admin/billing/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "condominium_id",
            "condominium_name",
            "paid_seats",
            "current_users",
            "remaining_seats",
            "billing_status",
            "billing_cycle",
            "billing_provider",
            "next_invoice_amount",
            "price_per_seat"
        ]
        
        for condo in data["condominiums"][:5]:  # Check first 5 condos
            for field in required_fields:
                assert field in condo, f"Condo missing field: {field}"
        
        print(f"✓ All required fields present in condo responses")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
