"""
Documentos Module Tests - Genturix SaaS Platform
Tests for document management with Emergent Object Storage

Features tested:
- Admin document upload (multipart/form-data)
- Document listing with category filter and pagination
- Document metadata retrieval (file_url NOT exposed)
- Document download through backend proxy
- Document metadata update (PATCH)
- Soft delete document
- Visibility control (public, private, roles-based)
- Role-based access control (admin can upload, resident cannot)
- Existing endpoints (casos, notifications/v2) still work
"""

import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
RESIDENT_EMAIL = "test-resident@genturix.com"
RESIDENT_PASSWORD = "Admin123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"


class TestDocumentosAuth:
    """Test authentication and role-based access for Documentos"""
    
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
    
    @pytest.fixture(scope="class")
    def guard_token(self):
        """Get guard authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        return response.json().get("access_token")
    
    def test_admin_can_upload_document(self, admin_token):
        """Admin should be able to upload documents"""
        # Create a test file
        test_content = b"Test document content for Genturix"
        files = {'file': ('TEST_documento.txt', io.BytesIO(test_content), 'text/plain')}
        params = {
            'name': 'TEST_Documento_Upload',
            'description': 'Test document for pytest',
            'category': 'otro',
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
        
        # Verify response structure
        assert "id" in data
        assert data["name"] == "TEST_Documento_Upload"
        assert data["category"] == "otro"
        assert data["visibility"] == "public"
        assert "file_url" not in data, "SECURITY: file_url should NOT be exposed"
        assert "file_name" in data
        assert "file_size" in data
        
        # Store doc_id for cleanup
        self.__class__.test_doc_id = data["id"]
        print(f"Created test document: {data['id']}")
    
    def test_resident_cannot_upload_document(self, resident_token):
        """Resident should NOT be able to upload documents (403)"""
        test_content = b"Resident trying to upload"
        files = {'file': ('resident_doc.txt', io.BytesIO(test_content), 'text/plain')}
        params = {'name': 'Resident Upload Attempt', 'category': 'otro', 'visibility': 'public'}
        
        response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {resident_token}"},
            files=files,
            params=params
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Resident correctly denied upload access (403)")
    
    def test_guard_cannot_upload_document(self, guard_token):
        """Guard should NOT be able to upload documents (403)"""
        test_content = b"Guard trying to upload"
        files = {'file': ('guard_doc.txt', io.BytesIO(test_content), 'text/plain')}
        params = {'name': 'Guard Upload Attempt', 'category': 'otro', 'visibility': 'public'}
        
        response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {guard_token}"},
            files=files,
            params=params
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("Guard correctly denied upload access (403)")


class TestDocumentosListing:
    """Test document listing with filters and pagination"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD
        })
        return response.json().get("access_token")
    
    def test_list_documents_admin(self, admin_token):
        """Admin can list all documents"""
        response = requests.get(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify pagination structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        
        # Verify file_url is NOT exposed in any document
        for doc in data["items"]:
            assert "file_url" not in doc, f"SECURITY: file_url exposed in doc {doc.get('id')}"
        
        print(f"Admin can see {data['total']} documents")
    
    def test_list_documents_with_category_filter(self, admin_token):
        """Test category filter works"""
        response = requests.get(
            f"{BASE_URL}/api/documentos?category=reglamento",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned docs should have category=reglamento
        for doc in data["items"]:
            assert doc["category"] == "reglamento", f"Wrong category: {doc['category']}"
        
        print(f"Category filter returned {len(data['items'])} reglamento documents")
    
    def test_list_documents_pagination(self, admin_token):
        """Test pagination works"""
        response = requests.get(
            f"{BASE_URL}/api/documentos?page=1&page_size=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert len(data["items"]) <= 5
        
        print(f"Pagination: page {data['page']}/{data['total_pages']}, {len(data['items'])} items")
    
    def test_resident_sees_only_visible_documents(self, resident_token, admin_token):
        """Resident should only see public docs and role-based docs they have access to"""
        # First, create a private document as admin
        test_content = b"Private admin document"
        files = {'file': ('private.txt', io.BytesIO(test_content), 'text/plain')}
        params = {'name': 'TEST_Private_Doc', 'category': 'otro', 'visibility': 'private'}
        
        admin_response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            params=params
        )
        assert admin_response.status_code == 200
        private_doc_id = admin_response.json()["id"]
        
        # Now check resident's view
        resident_response = requests.get(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        
        assert resident_response.status_code == 200
        resident_docs = resident_response.json()["items"]
        
        # Resident should NOT see the private document
        private_doc_ids = [d["id"] for d in resident_docs if d["visibility"] == "private"]
        assert private_doc_id not in [d["id"] for d in resident_docs], \
            "SECURITY: Resident can see private document!"
        
        # Verify all docs resident sees are either public or roles-based with Residente
        for doc in resident_docs:
            if doc["visibility"] == "private":
                pytest.fail(f"Resident can see private doc: {doc['id']}")
            if doc["visibility"] == "roles":
                assert "Residente" in doc.get("allowed_roles", []), \
                    f"Resident sees role-based doc without Residente role: {doc['id']}"
        
        print(f"Resident correctly sees {len(resident_docs)} documents (no private docs)")
        
        # Cleanup: delete the private doc
        requests.delete(
            f"{BASE_URL}/api/documentos/{private_doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )


class TestDocumentosDetail:
    """Test document detail and download endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def test_document(self, admin_token):
        """Create a test document for detail tests"""
        test_content = b"Test content for detail tests"
        files = {'file': ('TEST_detail.txt', io.BytesIO(test_content), 'text/plain')}
        params = {'name': 'TEST_Detail_Doc', 'category': 'comunicado', 'visibility': 'public'}
        
        response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            params=params
        )
        assert response.status_code == 200
        return response.json()
    
    def test_get_document_detail(self, admin_token, test_document):
        """Get document metadata (file_url NOT exposed)"""
        doc_id = test_document["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/documentos/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == doc_id
        assert data["name"] == "TEST_Detail_Doc"
        assert "file_url" not in data, "SECURITY: file_url should NOT be exposed in detail"
        
        print(f"Document detail retrieved: {data['name']}")
    
    def test_download_document(self, admin_token, test_document):
        """Download document content through backend proxy"""
        doc_id = test_document["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/documentos/{doc_id}/download",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        
        # Check Content-Disposition header
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, "Should have attachment disposition"
        
        # Verify content is returned
        assert len(response.content) > 0, "Download should return file content"
        
        print(f"Document downloaded: {len(response.content)} bytes")
    
    def test_resident_cannot_access_private_doc_detail(self, admin_token, resident_token):
        """Resident should get 403 when accessing private document detail"""
        # Create private doc
        test_content = b"Private content"
        files = {'file': ('private.txt', io.BytesIO(test_content), 'text/plain')}
        params = {'name': 'TEST_Private_Detail', 'category': 'otro', 'visibility': 'private'}
        
        admin_response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            params=params
        )
        private_doc_id = admin_response.json()["id"]
        
        # Resident tries to access
        resident_response = requests.get(
            f"{BASE_URL}/api/documentos/{private_doc_id}",
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        
        assert resident_response.status_code == 403, \
            f"Expected 403, got {resident_response.status_code}"
        
        print("Resident correctly denied access to private document detail (403)")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/documentos/{private_doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )


class TestDocumentosUpdate:
    """Test document metadata update (PATCH)"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def guard_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL, "password": GUARD_PASSWORD
        })
        return response.json().get("access_token")
    
    def test_admin_can_update_document(self, admin_token):
        """Admin can update document metadata"""
        # Create a test document first
        test_content = b"Test content for update tests"
        files = {'file': ('TEST_update.txt', io.BytesIO(test_content), 'text/plain')}
        params = {'name': 'TEST_Update_Doc', 'category': 'otro', 'visibility': 'public'}
        
        create_response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            params=params
        )
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        doc_id = create_response.json()["id"]
        
        update_data = {
            "name": "TEST_Updated_Name",
            "description": "Updated description",
            "category": "comunicado",
            "visibility": "roles",
            "allowed_roles": ["Residente", "Administrador"]
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/documentos/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "TEST_Updated_Name"
        assert data["description"] == "Updated description"
        assert data["category"] == "comunicado"
        assert data["visibility"] == "roles"
        assert "Residente" in data["allowed_roles"]
        assert "file_url" not in data, "SECURITY: file_url should NOT be in update response"
        
        print(f"Document updated: {data['name']}")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/documentos/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    
    def test_guard_cannot_update_document(self, admin_token, guard_token):
        """Guard should NOT be able to update documents (403)"""
        # Create a document first
        test_content = b"Test content for guard update test"
        files = {'file': ('TEST_guard_update.txt', io.BytesIO(test_content), 'text/plain')}
        params = {'name': 'TEST_Guard_Update', 'category': 'otro', 'visibility': 'public'}
        
        create_response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            params=params
        )
        doc_id = create_response.json()["id"]
        
        response = requests.patch(
            f"{BASE_URL}/api/documentos/{doc_id}",
            headers={"Authorization": f"Bearer {guard_token}"},
            json={"name": "Guard Update Attempt"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("Guard correctly denied update access (403)")
        
        # Cleanup
        requests.delete(
            f"{BASE_URL}/api/documentos/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )


class TestDocumentosDelete:
    """Test document soft delete"""
    
    def test_admin_can_delete_document(self):
        """Admin can soft-delete a document"""
        # Get fresh token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        admin_token = login_response.json().get("access_token")
        
        # Create a document to delete
        test_content = b"Document to delete"
        files = {'file': ('TEST_delete.txt', io.BytesIO(test_content), 'text/plain')}
        params = {'name': 'TEST_Delete_Doc', 'category': 'otro', 'visibility': 'public'}
        
        create_response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            params=params
        )
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        doc_id = create_response.json()["id"]
        
        # Delete the document
        delete_response = requests.delete(
            f"{BASE_URL}/api/documentos/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert delete_response.status_code == 200
        assert "eliminado" in delete_response.json().get("message", "").lower()
        
        # Verify document is no longer accessible
        get_response = requests.get(
            f"{BASE_URL}/api/documentos/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_response.status_code == 404, "Deleted document should return 404"
        
        print(f"Document {doc_id} soft-deleted successfully")
    
    def test_guard_cannot_delete_document(self):
        """Guard should NOT be able to delete documents (403)"""
        # Get fresh tokens
        admin_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        admin_token = admin_login.json().get("access_token")
        
        guard_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL, "password": GUARD_PASSWORD
        })
        guard_token = guard_login.json().get("access_token")
        
        # Create a document
        test_content = b"Document guard tries to delete"
        files = {'file': ('TEST_guard_delete.txt', io.BytesIO(test_content), 'text/plain')}
        params = {'name': 'TEST_Guard_Delete', 'category': 'otro', 'visibility': 'public'}
        
        create_response = requests.post(
            f"{BASE_URL}/api/documentos",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            params=params
        )
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        doc_id = create_response.json()["id"]
        
        # Guard tries to delete
        delete_response = requests.delete(
            f"{BASE_URL}/api/documentos/{doc_id}",
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        
        assert delete_response.status_code == 403, f"Expected 403, got {delete_response.status_code}"
        print("Guard correctly denied delete access (403)")
        
        # Cleanup: admin deletes
        requests.delete(
            f"{BASE_URL}/api/documentos/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )


class TestExistingEndpoints:
    """Verify existing endpoints still work (no breakage)"""
    
    def test_casos_endpoints_still_work(self):
        """Verify /api/casos endpoints still work"""
        # Get fresh token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        admin_token = login_response.json().get("access_token")
        """Verify /api/casos endpoints still work"""
        # Get casos list
        response = requests.get(
            f"{BASE_URL}/api/casos",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Casos list failed: {response.text}"
        
        # Get casos stats
        stats_response = requests.get(
            f"{BASE_URL}/api/casos/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert stats_response.status_code == 200, f"Casos stats failed: {stats_response.text}"
        
        print("Casos endpoints working correctly")
    
    def test_notifications_v2_endpoints_still_work(self):
        """Verify /api/notifications/v2 endpoints still work"""
        # Get fresh token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        admin_token = login_response.json().get("access_token")
        # Get notifications
        response = requests.get(
            f"{BASE_URL}/api/notifications/v2",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Notifications v2 failed: {response.text}"
        
        # Get unread count
        count_response = requests.get(
            f"{BASE_URL}/api/notifications/v2/unread-count",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert count_response.status_code == 200, f"Unread count failed: {count_response.text}"
        
        print("Notifications v2 endpoints working correctly")


class TestCleanup:
    """Cleanup test documents"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return response.json().get("access_token")
    
    def test_cleanup_test_documents(self, admin_token):
        """Delete all TEST_ prefixed documents"""
        response = requests.get(
            f"{BASE_URL}/api/documentos?page_size=50",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code == 200:
            docs = response.json().get("items", [])
            deleted = 0
            for doc in docs:
                if doc.get("name", "").startswith("TEST_"):
                    del_response = requests.delete(
                        f"{BASE_URL}/api/documentos/{doc['id']}",
                        headers={"Authorization": f"Bearer {admin_token}"}
                    )
                    if del_response.status_code == 200:
                        deleted += 1
            
            print(f"Cleanup: deleted {deleted} test documents")
