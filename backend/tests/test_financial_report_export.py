"""
Test Financial Report Export (PDF + CSV) for Genturix
Tests the GET /api/finanzas/report endpoint with format and period parameters
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
RESIDENT_EMAIL = "test-resident@genturix.com"
RESIDENT_PASSWORD = "Admin123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def resident_token():
    """Get resident authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Resident login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def guard_token():
    """Get guard authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": GUARD_EMAIL, "password": GUARD_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Guard login failed: {response.status_code} - {response.text}")


class TestFinancialReportExportCSV:
    """Tests for CSV financial report export"""

    def test_csv_export_returns_valid_csv(self, admin_token):
        """GET /api/finanzas/report?format=csv - Returns valid CSV with BOM, headers, and unit rows"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/report?format=csv",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("Content-Type", "").startswith("text/csv"), \
            f"Expected text/csv, got {response.headers.get('Content-Type')}"
        
        # Check Content-Disposition header for attachment
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, f"Expected attachment in Content-Disposition: {content_disp}"
        assert ".csv" in content_disp, f"Expected .csv in filename: {content_disp}"
        
        # Check CSV content
        content = response.content
        
        # Check for UTF-8 BOM (EF BB BF)
        assert content.startswith(b'\xef\xbb\xbf'), "CSV should start with UTF-8 BOM"
        
        # Decode and check content
        text = content.decode('utf-8-sig')
        lines = text.strip().split('\n')
        
        # Should have header info
        assert "Reporte Financiero" in lines[0], f"First line should contain 'Reporte Financiero': {lines[0]}"
        
        # Check for summary fields
        assert any("Total Cobrado" in line for line in lines), "CSV should contain 'Total Cobrado'"
        assert any("Total Pagado" in line for line in lines), "CSV should contain 'Total Pagado'"
        assert any("Total Pendiente" in line for line in lines), "CSV should contain 'Total Pendiente'"
        assert any("Total Crédito" in line for line in lines), "CSV should contain 'Total Crédito'"
        
        # Check for column headers
        assert any("Unidad,Total Cobrado,Total Pagado,Balance,Estado" in line for line in lines), \
            "CSV should contain column headers"
        
        print(f"CSV export successful - {len(lines)} lines, {len(content)} bytes")

    def test_csv_export_with_period_filter(self, admin_token):
        """GET /api/finanzas/report?format=csv&period=2026-04 - Filters by period"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/report?format=csv&period=2026-04",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        text = response.content.decode('utf-8-sig')
        
        # Check period is mentioned in the report
        assert "2026-04" in text, "Period should be mentioned in the report"
        
        print(f"CSV export with period filter successful")


class TestFinancialReportExportPDF:
    """Tests for PDF financial report export"""

    def test_pdf_export_returns_valid_pdf(self, admin_token):
        """GET /api/finanzas/report?format=pdf - Returns valid PDF (starts with %PDF-)"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/report?format=pdf",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("Content-Type", "").startswith("application/pdf"), \
            f"Expected application/pdf, got {response.headers.get('Content-Type')}"
        
        # Check Content-Disposition header for attachment
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, f"Expected attachment in Content-Disposition: {content_disp}"
        assert ".pdf" in content_disp, f"Expected .pdf in filename: {content_disp}"
        
        # Check PDF magic bytes
        content = response.content
        assert content.startswith(b'%PDF-'), "PDF should start with %PDF- magic bytes"
        
        # PDF should have reasonable size (at least 1KB)
        assert len(content) > 1000, f"PDF seems too small: {len(content)} bytes"
        
        print(f"PDF export successful - {len(content)} bytes")

    def test_pdf_export_with_period_filter(self, admin_token):
        """GET /api/finanzas/report?format=pdf&period=2026-05 - Filters by period"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/report?format=pdf&period=2026-05",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.content.startswith(b'%PDF-'), "PDF should start with %PDF- magic bytes"
        
        print(f"PDF export with period filter successful - {len(response.content)} bytes")


class TestFinancialReportAuthorization:
    """Tests for authorization on financial report endpoint"""

    def test_resident_cannot_access_report(self, resident_token):
        """Resident CANNOT access report endpoint (403)"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/report?format=csv",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        
        assert response.status_code == 403, \
            f"Resident should get 403, got {response.status_code}: {response.text}"
        
        print("Resident correctly blocked from report endpoint (403)")

    def test_guard_cannot_access_report(self, guard_token):
        """Guard CANNOT access report endpoint (403)"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/report?format=pdf",
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        
        assert response.status_code == 403, \
            f"Guard should get 403, got {response.status_code}: {response.text}"
        
        print("Guard correctly blocked from report endpoint (403)")

    def test_unauthenticated_cannot_access_report(self):
        """Unauthenticated user CANNOT access report endpoint (401 or 403)"""
        response = requests.get(f"{BASE_URL}/api/finanzas/report?format=csv")
        
        # API may return 401 or 403 for unauthenticated - both are valid security responses
        assert response.status_code in [401, 403], \
            f"Unauthenticated should get 401 or 403, got {response.status_code}: {response.text}"
        
        print(f"Unauthenticated correctly blocked from report endpoint ({response.status_code})")


class TestExistingFinancialEndpoints:
    """Tests to verify existing financial endpoints still work"""

    def test_finanzas_overview_still_works(self, admin_token):
        """GET /api/finanzas/overview - Still works"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/overview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "summary" in data or "accounts" in data, f"Response should have summary or accounts: {data}"
        
        print("Finanzas overview endpoint still works")

    def test_finanzas_catalog_still_works(self, admin_token):
        """GET /api/finanzas/catalog - Still works"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/catalog",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        print("Finanzas catalog endpoint still works")

    def test_finanzas_charges_still_works(self, admin_token):
        """GET /api/finanzas/charges - Still works"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/charges",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        print("Finanzas charges endpoint still works")

    def test_finanzas_payments_still_works(self, admin_token):
        """GET /api/finanzas/payments - Still works"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/payments",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        print("Finanzas payments endpoint still works")


class TestInvalidParameters:
    """Tests for invalid parameter handling"""

    def test_invalid_format_rejected(self, admin_token):
        """Invalid format parameter should be rejected"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/report?format=xlsx",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Should return 422 for invalid format
        assert response.status_code == 422, \
            f"Invalid format should get 422, got {response.status_code}: {response.text}"
        
        print("Invalid format correctly rejected (422)")

    def test_invalid_period_format_rejected(self, admin_token):
        """Invalid period format should be rejected"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/report?format=csv&period=2026-13",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Should return 422 for invalid period
        assert response.status_code == 422, \
            f"Invalid period should get 422, got {response.status_code}: {response.text}"
        
        print("Invalid period format correctly rejected (422)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
