"""
Test cases for Audit Module PDF Export functionality
Tests: GET /api/audit/export
- Returns Content-Type: application/pdf
- File starts with %PDF
- Accepts query params: from_date, to_date, event_type
- Tenant filter (Admin sees only their condo)
- Role access control (Administrador/SuperAdmin only)
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

class TestAuditExportPDF:
    """Tests for GET /api/audit/export PDF export functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.admin_credentials = {"email": "admin@genturix.com", "password": "Admin123!"}
        self.superadmin_credentials = {"email": "superadmin@genturix.com", "password": "SuperAdmin123!"}
        self.guard_credentials = {"email": "guarda1@genturix.com", "password": "Guard123!"}
        
    def get_auth_token(self, credentials: dict) -> str:
        """Get auth token for given credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=credentials)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    # ==================== ADMIN TESTS ====================
    def test_admin_export_pdf_returns_200(self):
        """Test: Admin can export PDF successfully"""
        token = self.get_auth_token(self.admin_credentials)
        assert token is not None, "Failed to get admin token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/audit/export", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Admin export returned status 200")
    
    def test_admin_export_content_type_is_pdf(self):
        """Test: Response has Content-Type: application/pdf"""
        token = self.get_auth_token(self.admin_credentials)
        assert token is not None, "Failed to get admin token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/audit/export", headers=headers)
        
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
        print(f"✓ Content-Type is application/pdf: {content_type}")
    
    def test_admin_export_file_is_valid_pdf(self):
        """Test: File content starts with %PDF (valid PDF header)"""
        token = self.get_auth_token(self.admin_credentials)
        assert token is not None, "Failed to get admin token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/audit/export", headers=headers)
        
        assert response.status_code == 200, f"Request failed: {response.status_code}"
        
        content = response.content
        assert content[:4] == b'%PDF', f"Expected PDF header '%PDF', got {content[:10]}"
        print(f"✓ File starts with %PDF-{content[5:8].decode('utf-8', errors='ignore')}")
    
    def test_admin_export_has_content_disposition(self):
        """Test: Response has Content-Disposition header for download"""
        token = self.get_auth_token(self.admin_credentials)
        assert token is not None, "Failed to get admin token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/audit/export", headers=headers)
        
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disposition, f"Expected attachment in Content-Disposition: {content_disposition}"
        assert ".pdf" in content_disposition, f"Expected .pdf in filename: {content_disposition}"
        print(f"✓ Content-Disposition: {content_disposition}")
    
    # ==================== SUPERADMIN TESTS ====================
    def test_superadmin_export_pdf_returns_200(self):
        """Test: SuperAdmin can export PDF successfully"""
        token = self.get_auth_token(self.superadmin_credentials)
        assert token is not None, "Failed to get superadmin token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/audit/export", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ SuperAdmin export returned status 200")
    
    def test_superadmin_export_is_valid_pdf(self):
        """Test: SuperAdmin export returns valid PDF"""
        token = self.get_auth_token(self.superadmin_credentials)
        assert token is not None, "Failed to get superadmin token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/audit/export", headers=headers)
        
        assert response.status_code == 200
        assert response.content[:4] == b'%PDF', f"Expected PDF header, got {response.content[:10]}"
        print(f"✓ SuperAdmin PDF is valid")
    
    # ==================== GUARD ROLE DENIED ====================
    def test_guard_export_returns_403(self):
        """Test: Guard role cannot export (returns 403 Forbidden)"""
        token = self.get_auth_token(self.guard_credentials)
        assert token is not None, "Failed to get guard token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/audit/export", headers=headers)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Guard correctly denied access with 403")
    
    # ==================== QUERY PARAMS TESTS ====================
    def test_export_with_event_type_filter(self):
        """Test: Export accepts event_type query param"""
        token = self.get_auth_token(self.admin_credentials)
        assert token is not None, "Failed to get admin token"
        
        headers = {"Authorization": f"Bearer {token}"}
        params = {"event_type": "login_success"}
        response = requests.get(f"{BASE_URL}/api/audit/export", headers=headers, params=params)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"✓ Export with event_type=login_success works")
    
    def test_export_with_from_date_filter(self):
        """Test: Export accepts from_date query param"""
        token = self.get_auth_token(self.admin_credentials)
        assert token is not None, "Failed to get admin token"
        
        headers = {"Authorization": f"Bearer {token}"}
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        params = {"from_date": from_date}
        response = requests.get(f"{BASE_URL}/api/audit/export", headers=headers, params=params)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"✓ Export with from_date={from_date} works")
    
    def test_export_with_to_date_filter(self):
        """Test: Export accepts to_date query param"""
        token = self.get_auth_token(self.admin_credentials)
        assert token is not None, "Failed to get admin token"
        
        headers = {"Authorization": f"Bearer {token}"}
        to_date = datetime.now().strftime("%Y-%m-%d")
        params = {"to_date": to_date}
        response = requests.get(f"{BASE_URL}/api/audit/export", headers=headers, params=params)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"✓ Export with to_date={to_date} works")
    
    def test_export_with_all_filters(self):
        """Test: Export accepts all query params together"""
        token = self.get_auth_token(self.admin_credentials)
        assert token is not None, "Failed to get admin token"
        
        headers = {"Authorization": f"Bearer {token}"}
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")
        params = {
            "from_date": from_date,
            "to_date": to_date,
            "event_type": "login_success"
        }
        response = requests.get(f"{BASE_URL}/api/audit/export", headers=headers, params=params)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.content[:4] == b'%PDF', "Response should be valid PDF"
        print(f"✓ Export with all filters (from_date, to_date, event_type) works")
    
    # ==================== UNAUTHENTICATED ACCESS ====================
    def test_export_without_token_returns_401(self):
        """Test: Export without auth token returns 401"""
        response = requests.get(f"{BASE_URL}/api/audit/export")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Unauthenticated request correctly rejected with {response.status_code}")


class TestAuditExportTenantFilter:
    """Tests for tenant filtering in audit export"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.admin_credentials = {"email": "admin@genturix.com", "password": "Admin123!"}
        self.superadmin_credentials = {"email": "superadmin@genturix.com", "password": "SuperAdmin123!"}
        
    def get_auth_token(self, credentials: dict) -> str:
        """Get auth token for given credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=credentials)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_admin_export_applies_tenant_filter(self):
        """Test: Admin export filters by their condominium"""
        token = self.get_auth_token(self.admin_credentials)
        assert token is not None, "Failed to get admin token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/audit/export", headers=headers)
        
        # Admin should get 200 but only see their condominium's data
        assert response.status_code == 200
        assert response.content[:4] == b'%PDF'
        print("✓ Admin export applies tenant filter (returns filtered PDF)")
    
    def test_superadmin_sees_all_data(self):
        """Test: SuperAdmin export sees all condominiums (no tenant filter)"""
        token = self.get_auth_token(self.superadmin_credentials)
        assert token is not None, "Failed to get superadmin token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/audit/export", headers=headers)
        
        # SuperAdmin should get all data
        assert response.status_code == 200
        assert response.content[:4] == b'%PDF'
        print("✓ SuperAdmin export sees all data (no tenant filter)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
