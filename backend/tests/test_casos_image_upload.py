"""
Test suite for Casos Image Upload and Proxy features
Tests: POST /api/casos, POST /api/casos/{id}/attachments, GET /api/casos/image-proxy,
       POST /api/casos/{id}/comments, POST /api/casos/{id}/comments/{comment_id}/images
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
RESIDENT_EMAIL = "test-resident@genturix.com"
RESIDENT_PASSWORD = "Admin123!"
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"

# Minimal valid JPEG bytes (smallest valid JPEG)
MINIMAL_JPEG = bytes([
    0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
    0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
    0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
    0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
    0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
    0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
    0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
    0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
    0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
    0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
    0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
    0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
    0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
    0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
    0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
    0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
    0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
    0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
    0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
    0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
    0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
    0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
    0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
    0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
    0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
    0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
    0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5, 0xDB, 0x20, 0xA8, 0xF1, 0x7E, 0xCD,
    0xBF, 0xFF, 0xD9
])


@pytest.fixture(scope="module")
def resident_token():
    """Get resident auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": RESIDENT_EMAIL,
        "password": RESIDENT_PASSWORD
    })
    if resp.status_code == 200:
        return resp.json().get("access_token")
    pytest.skip(f"Resident login failed: {resp.status_code} - {resp.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if resp.status_code == 200:
        return resp.json().get("access_token")
    pytest.skip(f"Admin login failed: {resp.status_code} - {resp.text}")


@pytest.fixture(scope="module")
def resident_session(resident_token):
    """Authenticated session for resident"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {resident_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture(scope="module")
def admin_session(admin_token):
    """Authenticated session for admin"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    })
    return session


class TestCasoCreation:
    """Test case creation endpoint"""
    
    def test_create_caso_success(self, resident_session):
        """POST /api/casos - Create a case with JSON body"""
        payload = {
            "title": "TEST_Image_Upload_Case",
            "description": "Test case for image upload testing",
            "category": "mantenimiento",
            "priority": "medium",
            "visibility": "private"
        }
        resp = resident_session.post(f"{BASE_URL}/api/casos", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "id" in data
        assert data["title"] == payload["title"]
        assert data["description"] == payload["description"]
        assert data["category"] == payload["category"]
        assert data["priority"] == payload["priority"]
        assert data["visibility"] == payload["visibility"]
        assert data["status"] == "open"
        assert "attachments" in data
        assert isinstance(data["attachments"], list)
        
        # Store for later tests
        TestCasoCreation.caso_id = data["id"]
        print(f"Created caso: {data['id']}")
    
    def test_create_caso_community_visibility(self, resident_session):
        """POST /api/casos - Create a community case"""
        payload = {
            "title": "TEST_Community_Case",
            "description": "Community visible case for testing",
            "category": "seguridad",
            "priority": "high",
            "visibility": "community"
        }
        resp = resident_session.post(f"{BASE_URL}/api/casos", json=payload)
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["visibility"] == "community"
        TestCasoCreation.community_caso_id = data["id"]


class TestCasoAttachmentUpload:
    """Test case attachment upload endpoint"""
    
    def test_upload_attachment_success(self, resident_token):
        """POST /api/casos/{id}/attachments - Upload image file"""
        caso_id = getattr(TestCasoCreation, 'caso_id', None)
        if not caso_id:
            pytest.skip("No caso_id from previous test")
        
        files = {'file': ('test_image.jpg', io.BytesIO(MINIMAL_JPEG), 'image/jpeg')}
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        resp = requests.post(
            f"{BASE_URL}/api/casos/{caso_id}/attachments",
            files=files,
            headers=headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("status") == "ok"
        assert "url" in data
        
        # Store the attachment path for proxy test
        TestCasoAttachmentUpload.attachment_path = data["url"]
        print(f"Uploaded attachment: {data['url']}")
    
    def test_upload_attachment_invalid_format(self, resident_token):
        """POST /api/casos/{id}/attachments - Reject invalid file format"""
        caso_id = getattr(TestCasoCreation, 'caso_id', None)
        if not caso_id:
            pytest.skip("No caso_id from previous test")
        
        files = {'file': ('test.txt', io.BytesIO(b'not an image'), 'text/plain')}
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        resp = requests.post(
            f"{BASE_URL}/api/casos/{caso_id}/attachments",
            files=files,
            headers=headers
        )
        assert resp.status_code == 400
        assert "Formato no permitido" in resp.json().get("detail", "")
    
    def test_upload_attachment_empty_file(self, resident_token):
        """POST /api/casos/{id}/attachments - Reject empty file"""
        caso_id = getattr(TestCasoCreation, 'caso_id', None)
        if not caso_id:
            pytest.skip("No caso_id from previous test")
        
        files = {'file': ('empty.jpg', io.BytesIO(b''), 'image/jpeg')}
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        resp = requests.post(
            f"{BASE_URL}/api/casos/{caso_id}/attachments",
            files=files,
            headers=headers
        )
        assert resp.status_code == 400
        assert "vacio" in resp.json().get("detail", "").lower()
    
    def test_upload_attachment_nonexistent_caso(self, resident_token):
        """POST /api/casos/{id}/attachments - 404 for nonexistent case"""
        files = {'file': ('test.jpg', io.BytesIO(MINIMAL_JPEG), 'image/jpeg')}
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        resp = requests.post(
            f"{BASE_URL}/api/casos/nonexistent-caso-id/attachments",
            files=files,
            headers=headers
        )
        assert resp.status_code == 404


class TestImageProxy:
    """Test image proxy endpoint security and functionality"""
    
    def test_image_proxy_success(self, resident_token):
        """GET /api/casos/image-proxy - Proxy serve image from Object Storage"""
        attachment_path = getattr(TestCasoAttachmentUpload, 'attachment_path', None)
        if not attachment_path:
            pytest.skip("No attachment_path from previous test")
        
        resp = requests.get(
            f"{BASE_URL}/api/casos/image-proxy",
            params={"path": attachment_path, "token": resident_token}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        # Verify content type is image
        content_type = resp.headers.get("Content-Type", "")
        assert "image" in content_type, f"Expected image content type, got {content_type}"
        
        # Verify Cache-Control header exists (may be max-age or no-cache)
        cache_control = resp.headers.get("Cache-Control", "")
        assert cache_control, "Expected Cache-Control header"
        
        # Verify binary content
        assert len(resp.content) > 0
        print(f"Proxy returned {len(resp.content)} bytes, Content-Type: {content_type}")
    
    def test_image_proxy_with_auth_header(self, resident_token):
        """GET /api/casos/image-proxy - Auth via Authorization header"""
        attachment_path = getattr(TestCasoAttachmentUpload, 'attachment_path', None)
        if not attachment_path:
            pytest.skip("No attachment_path from previous test")
        
        headers = {"Authorization": f"Bearer {resident_token}"}
        resp = requests.get(
            f"{BASE_URL}/api/casos/image-proxy",
            params={"path": attachment_path},
            headers=headers
        )
        assert resp.status_code == 200
    
    def test_image_proxy_missing_token(self):
        """GET /api/casos/image-proxy - Reject missing token (401)"""
        resp = requests.get(
            f"{BASE_URL}/api/casos/image-proxy",
            params={"path": "genturix/casos/test/test.jpg"}
        )
        assert resp.status_code == 401
        assert "Token requerido" in resp.json().get("detail", "")
    
    def test_image_proxy_invalid_token(self):
        """GET /api/casos/image-proxy - Reject invalid token (401)"""
        resp = requests.get(
            f"{BASE_URL}/api/casos/image-proxy",
            params={"path": "genturix/casos/test/test.jpg", "token": "invalid-token"}
        )
        assert resp.status_code == 401
        assert "invalido" in resp.json().get("detail", "").lower()
    
    def test_image_proxy_path_traversal(self, resident_token):
        """GET /api/casos/image-proxy - Reject path traversal (400)"""
        resp = requests.get(
            f"{BASE_URL}/api/casos/image-proxy",
            params={"path": "../../../etc/passwd", "token": resident_token}
        )
        assert resp.status_code == 400
        assert "invalida" in resp.json().get("detail", "").lower()
    
    def test_image_proxy_path_traversal_encoded(self, resident_token):
        """GET /api/casos/image-proxy - Reject encoded path traversal"""
        resp = requests.get(
            f"{BASE_URL}/api/casos/image-proxy",
            params={"path": "genturix/casos/../../../etc/passwd", "token": resident_token}
        )
        assert resp.status_code == 400
    
    def test_image_proxy_wrong_condominium(self, resident_token):
        """GET /api/casos/image-proxy - Reject wrong condominium path (403)"""
        # Try to access a different condominium's files
        resp = requests.get(
            f"{BASE_URL}/api/casos/image-proxy",
            params={"path": "genturix/casos/wrong-condo-id/test.jpg", "token": resident_token}
        )
        assert resp.status_code == 403
        assert "denegado" in resp.json().get("detail", "").lower()
    
    def test_image_proxy_absolute_path(self, resident_token):
        """GET /api/casos/image-proxy - Reject absolute path"""
        resp = requests.get(
            f"{BASE_URL}/api/casos/image-proxy",
            params={"path": "/etc/passwd", "token": resident_token}
        )
        assert resp.status_code == 400


class TestCasoComments:
    """Test case comment endpoints"""
    
    def test_add_comment_success(self, resident_session):
        """POST /api/casos/{id}/comments - Add comment to a case"""
        caso_id = getattr(TestCasoCreation, 'caso_id', None)
        if not caso_id:
            pytest.skip("No caso_id from previous test")
        
        payload = {"comment": "TEST_Comment for image upload testing", "is_internal": False}
        resp = resident_session.post(f"{BASE_URL}/api/casos/{caso_id}/comments", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "id" in data
        assert data["comment"] == payload["comment"]
        assert data["is_internal"] == False
        assert "images" in data
        assert isinstance(data["images"], list)
        
        TestCasoComments.comment_id = data["id"]
        print(f"Created comment: {data['id']}")
    
    def test_add_comment_nonexistent_caso(self, resident_session):
        """POST /api/casos/{id}/comments - 404 for nonexistent case"""
        payload = {"comment": "Test comment", "is_internal": False}
        resp = resident_session.post(f"{BASE_URL}/api/casos/nonexistent-id/comments", json=payload)
        assert resp.status_code == 404


class TestCommentImageUpload:
    """Test comment image upload endpoint"""
    
    def test_upload_comment_image_success(self, resident_token):
        """POST /api/casos/{id}/comments/{comment_id}/images - Upload image to comment"""
        caso_id = getattr(TestCasoCreation, 'caso_id', None)
        comment_id = getattr(TestCasoComments, 'comment_id', None)
        if not caso_id or not comment_id:
            pytest.skip("No caso_id or comment_id from previous tests")
        
        files = {'file': ('comment_image.jpg', io.BytesIO(MINIMAL_JPEG), 'image/jpeg')}
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        resp = requests.post(
            f"{BASE_URL}/api/casos/{caso_id}/comments/{comment_id}/images",
            files=files,
            headers=headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("status") == "ok"
        assert "url" in data
        
        TestCommentImageUpload.comment_image_path = data["url"]
        print(f"Uploaded comment image: {data['url']}")
    
    def test_upload_comment_image_invalid_format(self, resident_token):
        """POST /api/casos/{id}/comments/{comment_id}/images - Reject invalid format"""
        caso_id = getattr(TestCasoCreation, 'caso_id', None)
        comment_id = getattr(TestCasoComments, 'comment_id', None)
        if not caso_id or not comment_id:
            pytest.skip("No caso_id or comment_id from previous tests")
        
        files = {'file': ('test.pdf', io.BytesIO(b'%PDF-1.4'), 'application/pdf')}
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        resp = requests.post(
            f"{BASE_URL}/api/casos/{caso_id}/comments/{comment_id}/images",
            files=files,
            headers=headers
        )
        assert resp.status_code == 400
    
    def test_upload_comment_image_nonexistent_comment(self, resident_token):
        """POST /api/casos/{id}/comments/{comment_id}/images - 404 for nonexistent comment"""
        caso_id = getattr(TestCasoCreation, 'caso_id', None)
        if not caso_id:
            pytest.skip("No caso_id from previous test")
        
        files = {'file': ('test.jpg', io.BytesIO(MINIMAL_JPEG), 'image/jpeg')}
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        resp = requests.post(
            f"{BASE_URL}/api/casos/{caso_id}/comments/nonexistent-comment-id/images",
            files=files,
            headers=headers
        )
        assert resp.status_code == 404


class TestCasoDetailWithAttachments:
    """Test case detail returns attachments and comments with images"""
    
    def test_caso_detail_includes_attachments(self, resident_session):
        """GET /api/casos/{id} - Case detail returns attachments array"""
        caso_id = getattr(TestCasoCreation, 'caso_id', None)
        if not caso_id:
            pytest.skip("No caso_id from previous test")
        
        resp = resident_session.get(f"{BASE_URL}/api/casos/{caso_id}")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "attachments" in data
        assert isinstance(data["attachments"], list)
        assert len(data["attachments"]) >= 1, "Expected at least 1 attachment"
        
        # Verify attachment path format
        attachment = data["attachments"][0]
        assert "genturix/casos" in attachment
        print(f"Case has {len(data['attachments'])} attachment(s)")
    
    def test_caso_detail_includes_comments_with_images(self, resident_session):
        """GET /api/casos/{id} - Case detail returns comments with images array"""
        caso_id = getattr(TestCasoCreation, 'caso_id', None)
        if not caso_id:
            pytest.skip("No caso_id from previous test")
        
        resp = resident_session.get(f"{BASE_URL}/api/casos/{caso_id}")
        assert resp.status_code == 200
        
        data = resp.json()
        assert "comments" in data
        assert isinstance(data["comments"], list)
        assert len(data["comments"]) >= 1, "Expected at least 1 comment"
        
        # Find our test comment
        test_comment = None
        for c in data["comments"]:
            if "TEST_Comment" in c.get("comment", ""):
                test_comment = c
                break
        
        assert test_comment is not None, "Test comment not found"
        assert "images" in test_comment
        assert isinstance(test_comment["images"], list)
        assert len(test_comment["images"]) >= 1, "Expected at least 1 image in comment"
        print(f"Comment has {len(test_comment['images'])} image(s)")


class TestExistingTestCase:
    """Test the existing test case mentioned in context"""
    
    def test_existing_caso_detail(self, resident_session):
        """GET /api/casos/{id} - Verify existing test case 'Test imagen'"""
        caso_id = "8b63e1e1-4de2-4dce-8890-870b8f10c0c7"
        
        resp = resident_session.get(f"{BASE_URL}/api/casos/{caso_id}")
        # May return 404 if case doesn't exist or 403 if not accessible
        if resp.status_code == 404:
            pytest.skip("Existing test case not found")
        if resp.status_code == 403:
            pytest.skip("Existing test case not accessible to resident")
        
        assert resp.status_code == 200
        data = resp.json()
        
        print(f"Existing case: {data.get('title')}")
        print(f"Attachments: {len(data.get('attachments', []))}")
        print(f"Comments: {len(data.get('comments', []))}")
        
        # Verify structure
        assert "attachments" in data
        assert "comments" in data
    
    def test_existing_caso_image_proxy(self, resident_token):
        """GET /api/casos/image-proxy - Verify proxy works for existing case images"""
        # Known attachment path from context
        attachment_path = "genturix/casos/46b9d344-a735-443a-8c9c-0e3d69c07824/8b63e1e1-4de2-4dce-8890-870b8f10c0c7/f1f03254-f0ea-4f3a-8f4b-a6113b01cec8.jpg"
        
        resp = requests.get(
            f"{BASE_URL}/api/casos/image-proxy",
            params={"path": attachment_path, "token": resident_token}
        )
        
        if resp.status_code == 404:
            pytest.skip("Existing attachment not found in storage")
        
        assert resp.status_code == 200
        assert "image" in resp.headers.get("Content-Type", "")
        print(f"Existing attachment proxy returned {len(resp.content)} bytes")


class TestCleanup:
    """Cleanup test data"""
    
    def test_delete_test_caso(self, resident_session):
        """DELETE /api/casos/{id} - Cleanup test case"""
        caso_id = getattr(TestCasoCreation, 'caso_id', None)
        if not caso_id:
            pytest.skip("No caso_id to delete")
        
        resp = resident_session.delete(f"{BASE_URL}/api/casos/{caso_id}")
        assert resp.status_code in [200, 204], f"Delete failed: {resp.status_code}"
        print(f"Deleted test caso: {caso_id}")
    
    def test_delete_community_caso(self, resident_session):
        """DELETE /api/casos/{id} - Cleanup community test case"""
        caso_id = getattr(TestCasoCreation, 'community_caso_id', None)
        if not caso_id:
            pytest.skip("No community_caso_id to delete")
        
        resp = resident_session.delete(f"{BASE_URL}/api/casos/{caso_id}")
        assert resp.status_code in [200, 204]
        print(f"Deleted community caso: {caso_id}")
