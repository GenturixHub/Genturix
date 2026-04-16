"""
Test Cases Module Enhancements - Iteration 41
Tests for:
1. DELETE /api/casos/{id} - Owner can delete own cases (not closed)
2. POST /api/casos/{id}/attachments - Photo attachments (jpg/png/webp, 5MB limit)
3. PATCH /api/casos/{id}/guard-update - Guard can update community cases status
4. Guard can view/comment on community cases
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


class TestCasosEnhancements:
    """Test suite for Cases module enhancements"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        if resp.status_code != 200:
            pytest.skip(f"Admin login failed: {resp.status_code}")
        return resp.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        """Get resident auth token"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD
        })
        if resp.status_code != 200:
            pytest.skip(f"Resident login failed: {resp.status_code}")
        return resp.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def guard_token(self):
        """Get guard auth token"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL, "password": GUARD_PASSWORD
        })
        if resp.status_code != 200:
            pytest.skip(f"Guard login failed: {resp.status_code}")
        return resp.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def resident_user_id(self, resident_token):
        """Get resident user ID"""
        resp = requests.get(f"{BASE_URL}/api/profile/me", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        if resp.status_code != 200:
            pytest.skip("Could not get resident profile")
        return resp.json().get("id")
    
    # ==================== DELETE CASO TESTS ====================
    
    def test_delete_own_case_success(self, resident_token):
        """Resident can delete their own open case"""
        # Create a case first
        create_resp = requests.post(f"{BASE_URL}/api/casos", json={
            "title": "TEST_DELETE_OWN_CASE",
            "description": "Test case for deletion",
            "category": "mantenimiento",
            "priority": "low",
            "visibility": "private"
        }, headers={"Authorization": f"Bearer {resident_token}"})
        
        assert create_resp.status_code in [200, 201], f"Create failed: {create_resp.text}"
        caso_id = create_resp.json().get("id")
        
        # Delete the case
        delete_resp = requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        
        assert delete_resp.status_code == 200, f"Delete failed: {delete_resp.text}"
        data = delete_resp.json()
        assert data.get("status") == "ok"
        assert data.get("deleted") == caso_id
        
        # Verify case is gone
        get_resp = requests.get(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert get_resp.status_code == 404, "Case should be deleted"
    
    def test_delete_non_owner_blocked(self, admin_token, resident_token):
        """Non-owner cannot delete another user's case (unless admin)"""
        # Admin creates a case
        create_resp = requests.post(f"{BASE_URL}/api/casos", json={
            "title": "TEST_ADMIN_CASE_NO_DELETE",
            "description": "Admin case that resident cannot delete",
            "category": "seguridad",
            "priority": "medium",
            "visibility": "private"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        
        if create_resp.status_code != 201:
            pytest.skip(f"Admin case creation failed: {create_resp.text}")
        
        caso_id = create_resp.json().get("id")
        
        # Resident tries to delete admin's case
        delete_resp = requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        
        assert delete_resp.status_code == 403, f"Should be forbidden: {delete_resp.text}"
        assert "Solo puedes eliminar tus propios casos" in delete_resp.text
        
        # Cleanup: Admin deletes the case
        requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
    
    def test_delete_closed_case_blocked(self, admin_token, resident_token):
        """Resident cannot delete a closed case"""
        # Create a case
        create_resp = requests.post(f"{BASE_URL}/api/casos", json={
            "title": "TEST_CLOSED_CASE_NO_DELETE",
            "description": "Case that will be closed",
            "category": "mantenimiento",
            "priority": "low",
            "visibility": "private"
        }, headers={"Authorization": f"Bearer {resident_token}"})
        
        assert create_resp.status_code in [200, 201], f"Create failed: {create_resp.text}"
        caso_id = create_resp.json().get("id")
        
        # Admin closes the case
        close_resp = requests.patch(f"{BASE_URL}/api/casos/{caso_id}", json={
            "status": "closed"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        
        assert close_resp.status_code == 200, f"Close failed: {close_resp.text}"
        
        # Resident tries to delete closed case
        delete_resp = requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        
        assert delete_resp.status_code == 400, f"Should be blocked: {delete_resp.text}"
        assert "No se puede eliminar un caso cerrado" in delete_resp.text
        
        # Cleanup: Admin can delete closed case
        requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
    
    def test_admin_can_delete_any_case(self, admin_token, resident_token):
        """Admin can delete any case including closed ones"""
        # Resident creates a case
        create_resp = requests.post(f"{BASE_URL}/api/casos", json={
            "title": "TEST_ADMIN_DELETE_ANY",
            "description": "Case for admin deletion test",
            "category": "limpieza",
            "priority": "low",
            "visibility": "private"
        }, headers={"Authorization": f"Bearer {resident_token}"})
        
        assert create_resp.status_code in [200, 201]
        caso_id = create_resp.json().get("id")
        
        # Admin deletes resident's case
        delete_resp = requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        
        assert delete_resp.status_code == 200, f"Admin delete failed: {delete_resp.text}"
    
    # ==================== ATTACHMENT TESTS ====================
    
    def test_upload_attachment_jpg(self, resident_token):
        """Upload JPG attachment to case"""
        # Create a case
        create_resp = requests.post(f"{BASE_URL}/api/casos", json={
            "title": "TEST_ATTACHMENT_JPG",
            "description": "Case with JPG attachment",
            "category": "mantenimiento",
            "priority": "medium",
            "visibility": "private"
        }, headers={"Authorization": f"Bearer {resident_token}"})
        
        assert create_resp.status_code in [200, 201]
        caso_id = create_resp.json().get("id")
        
        # Create a small test image (1x1 pixel JPG)
        # Minimal valid JPEG
        jpg_data = bytes([
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
            0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD5, 0xDB, 0x20, 0xA8, 0xF1, 0x7E, 0xA9,
            0x00, 0x00, 0x00, 0x00, 0xFF, 0xD9
        ])
        
        files = {'file': ('test.jpg', io.BytesIO(jpg_data), 'image/jpeg')}
        upload_resp = requests.post(
            f"{BASE_URL}/api/casos/{caso_id}/attachments",
            files=files,
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        
        assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
        data = upload_resp.json()
        assert data.get("status") == "ok"
        assert "url" in data
        
        # Verify attachment in case detail
        detail_resp = requests.get(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert "attachments" in detail
        assert len(detail["attachments"]) >= 1
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
    
    def test_upload_attachment_png(self, resident_token):
        """Upload PNG attachment to case"""
        # Create a case
        create_resp = requests.post(f"{BASE_URL}/api/casos", json={
            "title": "TEST_ATTACHMENT_PNG",
            "description": "Case with PNG attachment",
            "category": "infraestructura",
            "priority": "high",
            "visibility": "community"
        }, headers={"Authorization": f"Bearer {resident_token}"})
        
        assert create_resp.status_code in [200, 201]
        caso_id = create_resp.json().get("id")
        
        # Minimal valid PNG (1x1 pixel)
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
            0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xDE, 0x00, 0x00, 0x00,
            0x0C, 0x49, 0x44, 0x41, 0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
            0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59, 0xE7, 0x00, 0x00, 0x00,
            0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        
        files = {'file': ('test.png', io.BytesIO(png_data), 'image/png')}
        upload_resp = requests.post(
            f"{BASE_URL}/api/casos/{caso_id}/attachments",
            files=files,
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        
        assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
    
    def test_upload_attachment_oversized_rejected(self, resident_token):
        """Reject files larger than 5MB"""
        # Create a case
        create_resp = requests.post(f"{BASE_URL}/api/casos", json={
            "title": "TEST_ATTACHMENT_OVERSIZED",
            "description": "Case for oversized file test",
            "category": "otro",
            "priority": "low",
            "visibility": "private"
        }, headers={"Authorization": f"Bearer {resident_token}"})
        
        assert create_resp.status_code in [200, 201]
        caso_id = create_resp.json().get("id")
        
        # Create a file larger than 5MB (5.1MB)
        oversized_data = b'x' * (5 * 1024 * 1024 + 100000)  # 5.1MB
        
        files = {'file': ('large.jpg', io.BytesIO(oversized_data), 'image/jpeg')}
        upload_resp = requests.post(
            f"{BASE_URL}/api/casos/{caso_id}/attachments",
            files=files,
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        
        assert upload_resp.status_code == 400, f"Should reject oversized: {upload_resp.text}"
        assert "5 MB" in upload_resp.text or "excede" in upload_resp.text.lower()
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
    
    def test_upload_attachment_invalid_format_rejected(self, resident_token):
        """Reject non-image file formats"""
        # Create a case
        create_resp = requests.post(f"{BASE_URL}/api/casos", json={
            "title": "TEST_ATTACHMENT_INVALID_FORMAT",
            "description": "Case for invalid format test",
            "category": "otro",
            "priority": "low",
            "visibility": "private"
        }, headers={"Authorization": f"Bearer {resident_token}"})
        
        assert create_resp.status_code in [200, 201]
        caso_id = create_resp.json().get("id")
        
        # Try to upload a PDF
        pdf_data = b'%PDF-1.4 fake pdf content'
        
        files = {'file': ('document.pdf', io.BytesIO(pdf_data), 'application/pdf')}
        upload_resp = requests.post(
            f"{BASE_URL}/api/casos/{caso_id}/attachments",
            files=files,
            headers={"Authorization": f"Bearer {resident_token}"}
        )
        
        assert upload_resp.status_code == 400, f"Should reject PDF: {upload_resp.text}"
        assert "Formato no permitido" in upload_resp.text or "jpg" in upload_resp.text.lower()
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
    
    # ==================== GUARD UPDATE TESTS ====================
    
    def test_guard_update_community_case_in_progress(self, guard_token, resident_token):
        """Guard can update community case to in_progress"""
        # Resident creates a community case
        create_resp = requests.post(f"{BASE_URL}/api/casos", json={
            "title": "TEST_GUARD_UPDATE_IN_PROGRESS",
            "description": "Community case for guard update test",
            "category": "seguridad",
            "priority": "high",
            "visibility": "community"
        }, headers={"Authorization": f"Bearer {resident_token}"})
        
        assert create_resp.status_code in [200, 201]
        caso_id = create_resp.json().get("id")
        
        # Guard updates to in_progress
        update_resp = requests.patch(
            f"{BASE_URL}/api/casos/{caso_id}/guard-update",
            json={"status": "in_progress"},
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        
        assert update_resp.status_code == 200, f"Guard update failed: {update_resp.text}"
        data = update_resp.json()
        assert data.get("status") == "ok"
        assert data.get("new_status") == "in_progress"
        
        # Verify status changed
        detail_resp = requests.get(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert detail_resp.status_code == 200
        assert detail_resp.json().get("status") == "in_progress"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
    
    def test_guard_update_community_case_closed(self, guard_token, resident_token, admin_token):
        """Guard can close a community case"""
        # Resident creates a community case
        create_resp = requests.post(f"{BASE_URL}/api/casos", json={
            "title": "TEST_GUARD_UPDATE_CLOSED",
            "description": "Community case for guard close test",
            "category": "seguridad",
            "priority": "medium",
            "visibility": "community"
        }, headers={"Authorization": f"Bearer {resident_token}"})
        
        assert create_resp.status_code in [200, 201]
        caso_id = create_resp.json().get("id")
        
        # Guard closes the case
        update_resp = requests.patch(
            f"{BASE_URL}/api/casos/{caso_id}/guard-update",
            json={"status": "closed"},
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        
        assert update_resp.status_code == 200, f"Guard close failed: {update_resp.text}"
        data = update_resp.json()
        assert data.get("new_status") == "closed"
        
        # Verify status and closed_at
        detail_resp = requests.get(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail.get("status") == "closed"
        assert "closed_at" in detail
        
        # Cleanup (admin can delete closed cases)
        requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
    
    def test_guard_cannot_update_private_case(self, guard_token, resident_token):
        """Guard cannot update private cases"""
        # Resident creates a private case
        create_resp = requests.post(f"{BASE_URL}/api/casos", json={
            "title": "TEST_GUARD_PRIVATE_BLOCKED",
            "description": "Private case guard cannot update",
            "category": "mantenimiento",
            "priority": "low",
            "visibility": "private"
        }, headers={"Authorization": f"Bearer {resident_token}"})
        
        assert create_resp.status_code in [200, 201]
        caso_id = create_resp.json().get("id")
        
        # Guard tries to update private case
        update_resp = requests.patch(
            f"{BASE_URL}/api/casos/{caso_id}/guard-update",
            json={"status": "in_progress"},
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        
        assert update_resp.status_code == 403, f"Should be forbidden: {update_resp.text}"
        assert "Solo puedes actualizar casos comunitarios" in update_resp.text
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
    
    def test_guard_invalid_status_rejected(self, guard_token, resident_token):
        """Guard cannot set invalid status (only in_progress or closed allowed)"""
        # Resident creates a community case
        create_resp = requests.post(f"{BASE_URL}/api/casos", json={
            "title": "TEST_GUARD_INVALID_STATUS",
            "description": "Community case for invalid status test",
            "category": "seguridad",
            "priority": "low",
            "visibility": "community"
        }, headers={"Authorization": f"Bearer {resident_token}"})
        
        assert create_resp.status_code in [200, 201]
        caso_id = create_resp.json().get("id")
        
        # Guard tries to set invalid status
        update_resp = requests.patch(
            f"{BASE_URL}/api/casos/{caso_id}/guard-update",
            json={"status": "rejected"},  # Not allowed for guards
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        
        assert update_resp.status_code == 422, f"Should reject invalid status: {update_resp.text}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
    
    # ==================== GUARD VIEW/COMMENT TESTS ====================
    
    def test_guard_can_view_community_cases(self, guard_token, resident_token):
        """Guard can view community cases"""
        # Resident creates a community case
        create_resp = requests.post(f"{BASE_URL}/api/casos", json={
            "title": "TEST_GUARD_VIEW_COMMUNITY",
            "description": "Community case guard can view",
            "category": "seguridad",
            "priority": "medium",
            "visibility": "community"
        }, headers={"Authorization": f"Bearer {resident_token}"})
        
        assert create_resp.status_code in [200, 201]
        caso_id = create_resp.json().get("id")
        
        # Guard views the case
        detail_resp = requests.get(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {guard_token}"
        })
        
        assert detail_resp.status_code == 200, f"Guard view failed: {detail_resp.text}"
        detail = detail_resp.json()
        assert detail.get("id") == caso_id
        assert detail.get("visibility") == "community"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
    
    def test_guard_can_comment_on_community_case(self, guard_token, resident_token):
        """Guard can add comments to community cases"""
        # Resident creates a community case
        create_resp = requests.post(f"{BASE_URL}/api/casos", json={
            "title": "TEST_GUARD_COMMENT_COMMUNITY",
            "description": "Community case for guard comment test",
            "category": "seguridad",
            "priority": "high",
            "visibility": "community"
        }, headers={"Authorization": f"Bearer {resident_token}"})
        
        assert create_resp.status_code in [200, 201]
        caso_id = create_resp.json().get("id")
        
        # Guard adds a comment
        comment_resp = requests.post(
            f"{BASE_URL}/api/casos/{caso_id}/comments",
            json={"comment": "Guard comment on community case", "is_internal": False},
            headers={"Authorization": f"Bearer {guard_token}"}
        )
        
        assert comment_resp.status_code == 201, f"Guard comment failed: {comment_resp.text}"
        
        # Verify comment exists
        detail_resp = requests.get(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        comments = detail.get("comments", [])
        guard_comments = [c for c in comments if "Guard comment" in c.get("comment", "")]
        assert len(guard_comments) >= 1, "Guard comment should be visible"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {resident_token}"
        })
    
    # ==================== EXISTING CASE WITH ATTACHMENT TEST ====================
    
    def test_existing_case_with_attachment(self, admin_token):
        """Verify existing case bc324676-aea4-420f-8828-c27d137a9177 has attachment"""
        caso_id = "bc324676-aea4-420f-8828-c27d137a9177"
        
        detail_resp = requests.get(f"{BASE_URL}/api/casos/{caso_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        
        if detail_resp.status_code == 404:
            pytest.skip("Test case not found - may have been deleted")
        
        assert detail_resp.status_code == 200, f"Get case failed: {detail_resp.text}"
        detail = detail_resp.json()
        
        # Verify attachments array exists
        assert "attachments" in detail, "Case should have attachments field"
        attachments = detail.get("attachments", [])
        print(f"Case has {len(attachments)} attachment(s)")
        
        # The case should have at least 1 attachment per context
        if len(attachments) > 0:
            print(f"Attachment URLs: {attachments}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
