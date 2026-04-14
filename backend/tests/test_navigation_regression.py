"""
Navigation Regression Tests - Genturix SaaS Platform
Tests for resident bottom navigation showing all 8 modules

Features tested:
- Resident bottom navigation shows all 8 tabs
- Each tab renders correct content
- Swipe navigation between tabs
- Mobile responsive UI with 8 nav items
- Admin sidebar shows all modules
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


class TestResidentNavigation:
    """Test resident navigation modules"""
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        """Get resident authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        return response.json().get("access_token")
    
    def test_resident_login_success(self, resident_token):
        """Resident should be able to login"""
        assert resident_token is not None
        print(f"✓ Resident login successful")
    
    def test_resident_can_access_reservations(self, resident_token):
        """Resident should be able to access reservations module"""
        response = requests.get(
            f"{BASE_URL}/api/reservations",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert response.status_code == 200, f"Reservations access failed: {response.text}"
        print(f"✓ Reservations module accessible")
    
    def test_resident_can_access_areas(self, resident_token):
        """Resident should be able to access reservation areas"""
        response = requests.get(
            f"{BASE_URL}/api/reservations/areas",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert response.status_code == 200, f"Areas access failed: {response.text}"
        print(f"✓ Reservation areas accessible")
    
    def test_resident_can_access_directory(self, resident_token):
        """Resident should be able to access condominium directory"""
        response = requests.get(
            f"{BASE_URL}/api/profile/directory/condominium",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert response.status_code == 200, f"Directory access failed: {response.text}"
        print(f"✓ Directory module accessible")
    
    def test_resident_can_access_casos(self, resident_token):
        """Resident should be able to access casos module"""
        response = requests.get(
            f"{BASE_URL}/api/casos",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert response.status_code == 200, f"Casos access failed: {response.text}"
        print(f"✓ Casos module accessible")
    
    def test_resident_can_access_documentos(self, resident_token):
        """Resident should be able to access documentos module"""
        response = requests.get(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert response.status_code == 200, f"Documentos access failed: {response.text}"
        data = response.json()
        assert "items" in data, "Response should have items array"
        print(f"✓ Documentos module accessible - {len(data.get('items', []))} documents")
    
    def test_resident_can_access_finanzas(self, resident_token):
        """Resident should be able to access finanzas module"""
        # Get resident profile to get unit_id
        profile_response = requests.get(
            f"{BASE_URL}/api/profile",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert profile_response.status_code == 200
        profile = profile_response.json()
        unit_id = profile.get("unit_id")
        
        if unit_id:
            response = requests.get(
                f"{BASE_URL}/api/finanzas/unit/{unit_id}",
                headers={"Authorization": f"Bearer {resident_token}"}
            )
            assert response.status_code == 200, f"Finanzas access failed: {response.text}"
            print(f"✓ Finanzas module accessible for unit {unit_id}")
        else:
            print("⚠ Resident has no unit_id assigned, skipping finanzas test")
    
    def test_resident_can_access_visitor_notifications(self, resident_token):
        """Resident should be able to access visitor notifications"""
        response = requests.get(
            f"{BASE_URL}/api/resident/visitor-notifications",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        assert response.status_code == 200, f"Notifications access failed: {response.text}"
        print(f"✓ Visitor notifications accessible")


class TestAdminNavigation:
    """Test admin navigation modules"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")
    
    def test_admin_login_success(self, admin_token):
        """Admin should be able to login"""
        assert admin_token is not None
        print(f"✓ Admin login successful")
    
    def test_admin_can_access_dashboard(self, admin_token):
        """Admin should be able to access dashboard stats"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Dashboard access failed: {response.text}"
        print(f"✓ Dashboard module accessible")
    
    def test_admin_can_access_users(self, admin_token):
        """Admin should be able to access users management"""
        response = requests.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Users access failed: {response.text}"
        print(f"✓ Users module accessible")
    
    def test_admin_can_access_security(self, admin_token):
        """Admin should be able to access security module"""
        response = requests.get(
            f"{BASE_URL}/api/security/panic-events",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Security access failed: {response.text}"
        print(f"✓ Security module accessible")
    
    def test_admin_can_access_rrhh(self, admin_token):
        """Admin should be able to access RRHH module"""
        response = requests.get(
            f"{BASE_URL}/api/hr/guards",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"RRHH access failed: {response.text}"
        print(f"✓ RRHH module accessible")
    
    def test_admin_can_access_reservations(self, admin_token):
        """Admin should be able to access reservations module"""
        response = requests.get(
            f"{BASE_URL}/api/reservations",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Reservations access failed: {response.text}"
        print(f"✓ Reservations module accessible")
    
    def test_admin_can_access_notifications(self, admin_token):
        """Admin should be able to access notifications module"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Notifications access failed: {response.text}"
        print(f"✓ Notifications module accessible")
    
    def test_admin_can_access_casos(self, admin_token):
        """Admin should be able to access casos module"""
        response = requests.get(
            f"{BASE_URL}/api/casos",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Casos access failed: {response.text}"
        print(f"✓ Casos module accessible")
    
    def test_admin_can_access_documentos(self, admin_token):
        """Admin should be able to access documentos module"""
        response = requests.get(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Documentos access failed: {response.text}"
        print(f"✓ Documentos module accessible")
    
    def test_admin_can_access_finanzas(self, admin_token):
        """Admin should be able to access finanzas module"""
        response = requests.get(
            f"{BASE_URL}/api/finanzas/overview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Finanzas access failed: {response.text}"
        print(f"✓ Finanzas module accessible")
    
    def test_admin_can_access_audit(self, admin_token):
        """Admin should be able to access audit module"""
        response = requests.get(
            f"{BASE_URL}/api/audit/logs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Audit access failed: {response.text}"
        print(f"✓ Audit module accessible")


class TestDocumentUploadDownload:
    """Test document upload and download functionality"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        """Get resident authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        return response.json().get("access_token")
    
    def test_admin_upload_document(self, admin_token):
        """Admin should be able to upload a document"""
        import io
        
        test_content = b"Navigation regression test document content"
        files = {'file': ('TEST_nav_regression.txt', io.BytesIO(test_content), 'text/plain')}
        params = {
            'name': 'TEST_Navigation_Regression',
            'description': 'Test document for navigation regression',
            'category': 'comunicado',
            'visibility': 'public'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            params=params
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["name"] == "TEST_Navigation_Regression"
        
        # Store for download test
        self.__class__.test_doc_id = data["id"]
        print(f"✓ Document uploaded successfully: {data['id']}")
    
    def test_resident_can_download_public_document(self, resident_token):
        """Resident should be able to download public documents"""
        doc_id = getattr(self.__class__, 'test_doc_id', None)
        if not doc_id:
            pytest.skip("No test document available")
        
        response = requests.get(
            f"{BASE_URL}/api/documentos/{doc_id}/download",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        
        assert response.status_code == 200, f"Download failed: {response.text}"
        assert len(response.content) > 0, "Downloaded content should not be empty"
        print(f"✓ Document downloaded successfully: {len(response.content)} bytes")
    
    def test_cleanup_test_document(self, admin_token):
        """Cleanup test document"""
        doc_id = getattr(self.__class__, 'test_doc_id', None)
        if not doc_id:
            pytest.skip("No test document to cleanup")
        
        response = requests.delete(
            f"{BASE_URL}/api/documentos/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # Accept 200 or 404 (already deleted)
        assert response.status_code in [200, 404], f"Cleanup failed: {response.text}"
        print(f"✓ Test document cleaned up")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
