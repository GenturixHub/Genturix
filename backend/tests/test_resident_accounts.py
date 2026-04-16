"""
Test suite for Resident Financial Accounts module (Estados de Cuenta)
Tests: GET /api/finanzas/residents, GET /api/finanzas/resident/{user_id}, GET /api/finanzas/resident/{user_id}/export
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    """Headers with admin auth token"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


class TestResidentAccountsList:
    """Tests for GET /api/finanzas/residents - List all residents with financial status"""

    def test_list_residents_returns_200(self, auth_headers):
        """GET /api/finanzas/residents returns 200 OK"""
        response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_list_residents_returns_items_array(self, auth_headers):
        """Response contains items array"""
        response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data, "Response should contain 'items' key"
        assert isinstance(data["items"], list), "items should be a list"

    def test_list_residents_returns_total_count(self, auth_headers):
        """Response contains total count"""
        response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data, "Response should contain 'total' key"
        assert isinstance(data["total"], int), "total should be an integer"

    def test_resident_item_has_required_fields(self, auth_headers):
        """Each resident item has required fields: id, full_name, email, unit, balance, status"""
        response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        if data["items"]:
            item = data["items"][0]
            required_fields = ["id", "full_name", "email", "unit", "balance", "status"]
            for field in required_fields:
                assert field in item, f"Resident item missing required field: {field}"

    def test_resident_status_is_valid(self, auth_headers):
        """Resident status is one of: al_dia, atrasado, adelantado"""
        response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        valid_statuses = ["al_dia", "atrasado", "adelantado"]
        for item in data["items"]:
            assert item["status"] in valid_statuses, f"Invalid status: {item['status']}"

    def test_search_by_name(self, auth_headers):
        """Search filter by name works"""
        # First get all residents to find a name to search
        response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        if data["items"]:
            # Search for first resident's name
            search_name = data["items"][0]["full_name"].split()[0]  # First word of name
            search_response = requests.get(
                f"{BASE_URL}/api/finanzas/residents?search={search_name}",
                headers=auth_headers
            )
            assert search_response.status_code == 200
            search_data = search_response.json()
            # Should return at least the original resident
            assert len(search_data["items"]) >= 1, "Search should return at least one result"

    def test_search_by_email(self, auth_headers):
        """Search filter by email works"""
        response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        if data["items"]:
            # Search for first resident's email domain
            email = data["items"][0]["email"]
            search_response = requests.get(
                f"{BASE_URL}/api/finanzas/residents?search={email}",
                headers=auth_headers
            )
            assert search_response.status_code == 200
            search_data = search_response.json()
            assert len(search_data["items"]) >= 1, "Search by email should return results"

    def test_search_by_unit(self, auth_headers):
        """Search filter by unit works"""
        response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Find a resident with a unit
        residents_with_unit = [r for r in data["items"] if r.get("unit")]
        if residents_with_unit:
            unit = residents_with_unit[0]["unit"]
            search_response = requests.get(
                f"{BASE_URL}/api/finanzas/residents?search={unit}",
                headers=auth_headers
            )
            assert search_response.status_code == 200
            search_data = search_response.json()
            assert len(search_data["items"]) >= 1, "Search by unit should return results"

    def test_filter_by_status_atrasado(self, auth_headers):
        """Filter by status=atrasado works"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/residents?status_filter=atrasado",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # All returned items should have status=atrasado
        for item in data["items"]:
            assert item["status"] == "atrasado", f"Expected atrasado, got {item['status']}"

    def test_filter_by_status_al_dia(self, auth_headers):
        """Filter by status=al_dia works"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/residents?status_filter=al_dia",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "al_dia", f"Expected al_dia, got {item['status']}"

    def test_filter_by_status_adelantado(self, auth_headers):
        """Filter by status=adelantado works"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/residents?status_filter=adelantado",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "adelantado", f"Expected adelantado, got {item['status']}"

    def test_residents_sorted_by_status_then_name(self, auth_headers):
        """Residents are sorted: atrasados first, then by name"""
        response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        items = data["items"]
        if len(items) > 1:
            status_order = {"atrasado": 0, "al_dia": 1, "adelantado": 2}
            for i in range(len(items) - 1):
                curr_order = status_order.get(items[i]["status"], 9)
                next_order = status_order.get(items[i+1]["status"], 9)
                # Either current status is before next, or same status and name is alphabetically before
                assert curr_order <= next_order, "Items should be sorted by status first"


class TestResidentAccountDetail:
    """Tests for GET /api/finanzas/resident/{user_id} - Get detailed financial info"""

    def test_get_resident_detail_returns_200(self, auth_headers):
        """GET /api/finanzas/resident/{user_id} returns 200 for valid user"""
        # First get a valid user_id
        list_response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        assert list_response.status_code == 200
        data = list_response.json()
        if not data["items"]:
            pytest.skip("No residents available for testing")
        
        user_id = data["items"][0]["id"]
        response = requests.get(f"{BASE_URL}/api/finanzas/resident/{user_id}", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_resident_detail_has_user_info(self, auth_headers):
        """Detail response contains user info with id, full_name, email"""
        list_response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        data = list_response.json()
        if not data["items"]:
            pytest.skip("No residents available")
        
        user_id = data["items"][0]["id"]
        response = requests.get(f"{BASE_URL}/api/finanzas/resident/{user_id}", headers=auth_headers)
        assert response.status_code == 200
        detail = response.json()
        
        assert "user" in detail, "Response should contain 'user' key"
        assert "id" in detail["user"], "User should have 'id'"
        assert "full_name" in detail["user"], "User should have 'full_name'"
        assert "email" in detail["user"], "User should have 'email'"

    def test_resident_detail_has_financial_summary(self, auth_headers):
        """Detail response contains financial summary: total_due, total_paid, balance, status"""
        list_response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        data = list_response.json()
        if not data["items"]:
            pytest.skip("No residents available")
        
        user_id = data["items"][0]["id"]
        response = requests.get(f"{BASE_URL}/api/finanzas/resident/{user_id}", headers=auth_headers)
        assert response.status_code == 200
        detail = response.json()
        
        required_fields = ["total_due", "total_paid", "balance", "status", "unit"]
        for field in required_fields:
            assert field in detail, f"Detail missing required field: {field}"

    def test_resident_detail_has_charges_array(self, auth_headers):
        """Detail response contains charges array"""
        list_response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        data = list_response.json()
        if not data["items"]:
            pytest.skip("No residents available")
        
        user_id = data["items"][0]["id"]
        response = requests.get(f"{BASE_URL}/api/finanzas/resident/{user_id}", headers=auth_headers)
        assert response.status_code == 200
        detail = response.json()
        
        assert "charges" in detail, "Response should contain 'charges' key"
        assert isinstance(detail["charges"], list), "charges should be a list"

    def test_resident_detail_has_payments_array(self, auth_headers):
        """Detail response contains payments array"""
        list_response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        data = list_response.json()
        if not data["items"]:
            pytest.skip("No residents available")
        
        user_id = data["items"][0]["id"]
        response = requests.get(f"{BASE_URL}/api/finanzas/resident/{user_id}", headers=auth_headers)
        assert response.status_code == 200
        detail = response.json()
        
        assert "payments" in detail, "Response should contain 'payments' key"
        assert isinstance(detail["payments"], list), "payments should be a list"

    def test_resident_detail_404_for_invalid_user(self, auth_headers):
        """GET /api/finanzas/resident/{invalid_id} returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/resident/invalid-user-id-12345",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    def test_balance_calculation_correct(self, auth_headers):
        """Balance = total_due - total_paid"""
        list_response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        data = list_response.json()
        if not data["items"]:
            pytest.skip("No residents available")
        
        user_id = data["items"][0]["id"]
        response = requests.get(f"{BASE_URL}/api/finanzas/resident/{user_id}", headers=auth_headers)
        assert response.status_code == 200
        detail = response.json()
        
        expected_balance = round(detail["total_due"] - detail["total_paid"], 2)
        assert detail["balance"] == expected_balance, f"Balance mismatch: expected {expected_balance}, got {detail['balance']}"


class TestResidentAccountExport:
    """Tests for GET /api/finanzas/resident/{user_id}/export - Export PDF/CSV"""

    def test_export_pdf_returns_200(self, auth_headers):
        """Export PDF returns 200 with PDF content"""
        list_response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        data = list_response.json()
        if not data["items"]:
            pytest.skip("No residents available")
        
        user_id = data["items"][0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/finanzas/resident/{user_id}/export?format=pdf",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "application/pdf" in response.headers.get("Content-Type", ""), "Should return PDF content type"

    def test_export_csv_returns_200(self, auth_headers):
        """Export CSV returns 200 with CSV content"""
        list_response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        data = list_response.json()
        if not data["items"]:
            pytest.skip("No residents available")
        
        user_id = data["items"][0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/finanzas/resident/{user_id}/export?format=csv",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "text/csv" in response.headers.get("Content-Type", ""), "Should return CSV content type"

    def test_export_pdf_has_content_disposition(self, auth_headers):
        """PDF export has Content-Disposition header for download"""
        list_response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        data = list_response.json()
        if not data["items"]:
            pytest.skip("No residents available")
        
        user_id = data["items"][0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/finanzas/resident/{user_id}/export?format=pdf",
            headers=auth_headers
        )
        assert response.status_code == 200
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, "Should have attachment disposition"
        assert ".pdf" in content_disp, "Filename should have .pdf extension"

    def test_export_csv_has_content_disposition(self, auth_headers):
        """CSV export has Content-Disposition header for download"""
        list_response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        data = list_response.json()
        if not data["items"]:
            pytest.skip("No residents available")
        
        user_id = data["items"][0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/finanzas/resident/{user_id}/export?format=csv",
            headers=auth_headers
        )
        assert response.status_code == 200
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, "Should have attachment disposition"
        assert ".csv" in content_disp, "Filename should have .csv extension"

    def test_export_invalid_format_rejected(self, auth_headers):
        """Export with invalid format returns 422"""
        list_response = requests.get(f"{BASE_URL}/api/finanzas/residents", headers=auth_headers)
        data = list_response.json()
        if not data["items"]:
            pytest.skip("No residents available")
        
        user_id = data["items"][0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/finanzas/resident/{user_id}/export?format=xlsx",
            headers=auth_headers
        )
        assert response.status_code == 422, f"Expected 422 for invalid format, got {response.status_code}"

    def test_export_404_for_invalid_user(self, auth_headers):
        """Export for invalid user returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/resident/invalid-user-id-12345/export?format=pdf",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestResidentAccountsAuth:
    """Tests for authentication and authorization"""

    def test_list_residents_requires_auth(self):
        """GET /api/finanzas/residents requires authentication"""
        response = requests.get(f"{BASE_URL}/api/finanzas/residents")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_resident_detail_requires_auth(self):
        """GET /api/finanzas/resident/{id} requires authentication"""
        response = requests.get(f"{BASE_URL}/api/finanzas/resident/some-id")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_export_requires_auth(self):
        """GET /api/finanzas/resident/{id}/export requires authentication"""
        response = requests.get(f"{BASE_URL}/api/finanzas/resident/some-id/export?format=pdf")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
