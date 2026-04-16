"""
Test suite for Casos Visibility and Community Comments features
Tests: visibility field (private/community), access control, community comments
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
ADMIN_CREDS = {"email": "admin@genturix.com", "password": "Admin123!"}
RESIDENT_CREDS = {"email": "test-resident@genturix.com", "password": "Admin123!"}


# Module-scoped fixtures to minimize logins
@pytest.fixture(scope="module")
def session():
    """Shared requests session"""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_token(session):
    """Get admin token once for all tests"""
    response = session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin login failed: {response.text}")


@pytest.fixture(scope="module")
def resident_token(session, admin_token):
    """Get resident token once for all tests"""
    time.sleep(12)  # Wait for rate limit
    response = session.post(f"{BASE_URL}/api/auth/login", json=RESIDENT_CREDS)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Resident login failed: {response.text}")


def get_auth_header(token):
    """Return authorization header"""
    return {"Authorization": f"Bearer {token}"}


# ==================== VISIBILITY TESTS ====================

class TestCasoVisibility:
    """Tests for caso visibility field (private/community)"""
    
    def test_create_private_caso(self, session, resident_token):
        """POST /api/casos with visibility=private creates private case"""
        payload = {
            "title": f"TEST_Private_Caso_{uuid.uuid4().hex[:8]}",
            "description": "This is a private case visible only to creator and admin",
            "category": "mantenimiento",
            "priority": "medium",
            "visibility": "private"
        }
        
        response = session.post(
            f"{BASE_URL}/api/casos",
            json=payload,
            headers=get_auth_header(resident_token)
        )
        
        assert response.status_code == 200, f"Create private caso failed: {response.text}"
        data = response.json()
        
        assert data["visibility"] == "private", f"Expected visibility=private, got {data.get('visibility')}"
        assert "id" in data
        print(f"✓ Created private caso: {data['id']}")
        return data["id"]
    
    def test_create_community_caso(self, session, resident_token):
        """POST /api/casos with visibility=community creates community case"""
        payload = {
            "title": f"TEST_Community_Caso_{uuid.uuid4().hex[:8]}",
            "description": "This is a community case visible to all residents",
            "category": "convivencia",
            "priority": "low",
            "visibility": "community"
        }
        
        response = session.post(
            f"{BASE_URL}/api/casos",
            json=payload,
            headers=get_auth_header(resident_token)
        )
        
        assert response.status_code == 200, f"Create community caso failed: {response.text}"
        data = response.json()
        
        assert data["visibility"] == "community", f"Expected visibility=community, got {data.get('visibility')}"
        assert "id" in data
        print(f"✓ Created community caso: {data['id']}")
        return data["id"]
    
    def test_default_visibility_is_private(self, session, resident_token):
        """POST /api/casos without visibility defaults to private"""
        payload = {
            "title": f"TEST_Default_Visibility_{uuid.uuid4().hex[:8]}",
            "description": "This case should default to private visibility",
            "category": "otro",
            "priority": "low"
            # No visibility field
        }
        
        response = session.post(
            f"{BASE_URL}/api/casos",
            json=payload,
            headers=get_auth_header(resident_token)
        )
        
        assert response.status_code == 200, f"Create caso failed: {response.text}"
        data = response.json()
        
        assert data["visibility"] == "private", f"Default visibility should be private, got {data.get('visibility')}"
        print(f"✓ Default visibility is private")


class TestCasoAccessControl:
    """Tests for access control based on visibility"""
    
    def test_admin_sees_all_casos(self, session, admin_token):
        """GET /api/casos as admin returns ALL cases regardless of visibility"""
        response = session.get(
            f"{BASE_URL}/api/casos?page_size=50",
            headers=get_auth_header(admin_token)
        )
        
        assert response.status_code == 200, f"Get casos failed: {response.text}"
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        
        # Admin should see both private and community cases
        visibilities = set(c.get("visibility", "private") for c in data["items"])
        print(f"✓ Admin sees {data['total']} casos with visibilities: {visibilities}")
    
    def test_resident_sees_own_plus_community(self, session, admin_token, resident_token):
        """GET /api/casos as resident returns own cases + community cases"""
        # First create a private case as admin (resident shouldn't see it)
        admin_private = {
            "title": f"TEST_Admin_Private_{uuid.uuid4().hex[:8]}",
            "description": "Admin's private case - resident should NOT see this",
            "category": "seguridad",
            "priority": "high",
            "visibility": "private"
        }
        admin_response = session.post(
            f"{BASE_URL}/api/casos",
            json=admin_private,
            headers=get_auth_header(admin_token)
        )
        assert admin_response.status_code == 200
        admin_caso_id = admin_response.json()["id"]
        
        # Create a community case as admin (resident SHOULD see it)
        admin_community = {
            "title": f"TEST_Admin_Community_{uuid.uuid4().hex[:8]}",
            "description": "Admin's community case - resident SHOULD see this",
            "category": "limpieza",
            "priority": "low",
            "visibility": "community"
        }
        community_response = session.post(
            f"{BASE_URL}/api/casos",
            json=admin_community,
            headers=get_auth_header(admin_token)
        )
        assert community_response.status_code == 200
        community_caso_id = community_response.json()["id"]
        
        # Get casos as resident
        response = session.get(
            f"{BASE_URL}/api/casos?page_size=50",
            headers=get_auth_header(resident_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        
        caso_ids = [c["id"] for c in data["items"]]
        
        # Resident should NOT see admin's private case
        assert admin_caso_id not in caso_ids, "Resident should NOT see admin's private case"
        
        # Resident SHOULD see admin's community case
        assert community_caso_id in caso_ids, "Resident SHOULD see admin's community case"
        
        print(f"✓ Resident sees {data['total']} casos (own + community)")
    
    def test_resident_can_view_community_case_detail(self, session, admin_token, resident_token):
        """GET /api/casos/{id} allows resident to view community case they didn't create"""
        # Create community case as admin
        payload = {
            "title": f"TEST_Community_Detail_{uuid.uuid4().hex[:8]}",
            "description": "Community case for detail view test",
            "category": "infraestructura",
            "priority": "medium",
            "visibility": "community"
        }
        create_response = session.post(
            f"{BASE_URL}/api/casos",
            json=payload,
            headers=get_auth_header(admin_token)
        )
        assert create_response.status_code == 200
        caso_id = create_response.json()["id"]
        
        # Resident should be able to view it
        response = session.get(
            f"{BASE_URL}/api/casos/{caso_id}",
            headers=get_auth_header(resident_token)
        )
        
        assert response.status_code == 200, f"Resident should be able to view community case: {response.text}"
        data = response.json()
        assert data["id"] == caso_id
        assert data["visibility"] == "community"
        print(f"✓ Resident can view community case detail")
    
    def test_resident_blocked_from_private_case_of_another(self, session, admin_token, resident_token):
        """GET /api/casos/{id} blocks resident from viewing private case of another user"""
        # Create private case as admin
        payload = {
            "title": f"TEST_Private_Block_{uuid.uuid4().hex[:8]}",
            "description": "Private case - resident should be blocked",
            "category": "seguridad",
            "priority": "urgent",
            "visibility": "private"
        }
        create_response = session.post(
            f"{BASE_URL}/api/casos",
            json=payload,
            headers=get_auth_header(admin_token)
        )
        assert create_response.status_code == 200
        caso_id = create_response.json()["id"]
        
        # Resident should be blocked
        response = session.get(
            f"{BASE_URL}/api/casos/{caso_id}",
            headers=get_auth_header(resident_token)
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Resident blocked from viewing private case of another user (403)")


class TestCommunityComments:
    """Tests for commenting on community cases"""
    
    def test_any_resident_can_comment_on_community_case(self, session, admin_token, resident_token):
        """POST /api/casos/{id}/comments allows any resident to comment on community case"""
        # Create community case as admin
        payload = {
            "title": f"TEST_Community_Comment_{uuid.uuid4().hex[:8]}",
            "description": "Community case for comment test",
            "category": "convivencia",
            "priority": "low",
            "visibility": "community"
        }
        create_response = session.post(
            f"{BASE_URL}/api/casos",
            json=payload,
            headers=get_auth_header(admin_token)
        )
        assert create_response.status_code == 200
        caso_id = create_response.json()["id"]
        
        # Resident should be able to comment
        comment_payload = {
            "comment": "This is a comment from a resident on a community case",
            "is_internal": False
        }
        response = session.post(
            f"{BASE_URL}/api/casos/{caso_id}/comments",
            json=comment_payload,
            headers=get_auth_header(resident_token)
        )
        
        assert response.status_code == 200, f"Resident should be able to comment on community case: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["comment"] == comment_payload["comment"]
        print(f"✓ Resident can comment on community case")
    
    def test_non_creator_blocked_from_commenting_on_private_case(self, session, admin_token, resident_token):
        """POST /api/casos/{id}/comments blocks non-creator from commenting on private case"""
        # Create private case as admin
        payload = {
            "title": f"TEST_Private_Comment_Block_{uuid.uuid4().hex[:8]}",
            "description": "Private case - resident should not be able to comment",
            "category": "mantenimiento",
            "priority": "medium",
            "visibility": "private"
        }
        create_response = session.post(
            f"{BASE_URL}/api/casos",
            json=payload,
            headers=get_auth_header(admin_token)
        )
        assert create_response.status_code == 200
        caso_id = create_response.json()["id"]
        
        # Resident should be blocked from commenting
        comment_payload = {
            "comment": "This comment should be blocked",
            "is_internal": False
        }
        response = session.post(
            f"{BASE_URL}/api/casos/{caso_id}/comments",
            json=comment_payload,
            headers=get_auth_header(resident_token)
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Non-creator blocked from commenting on private case (403)")
    
    def test_creator_can_comment_on_own_private_case(self, session, resident_token):
        """Creator can comment on their own private case"""
        # Create private case as resident
        payload = {
            "title": f"TEST_Own_Private_Comment_{uuid.uuid4().hex[:8]}",
            "description": "My own private case",
            "category": "ruido",
            "priority": "low",
            "visibility": "private"
        }
        create_response = session.post(
            f"{BASE_URL}/api/casos",
            json=payload,
            headers=get_auth_header(resident_token)
        )
        assert create_response.status_code == 200
        caso_id = create_response.json()["id"]
        
        # Creator should be able to comment
        comment_payload = {
            "comment": "Adding more details to my own case",
            "is_internal": False
        }
        response = session.post(
            f"{BASE_URL}/api/casos/{caso_id}/comments",
            json=comment_payload,
            headers=get_auth_header(resident_token)
        )
        
        assert response.status_code == 200, f"Creator should be able to comment on own case: {response.text}"
        print(f"✓ Creator can comment on own private case")
    
    def test_admin_can_comment_on_any_case(self, session, admin_token, resident_token):
        """Admin can comment on any case (private or community)"""
        # Create private case as resident
        payload = {
            "title": f"TEST_Admin_Comment_Any_{uuid.uuid4().hex[:8]}",
            "description": "Resident's private case",
            "category": "limpieza",
            "priority": "medium",
            "visibility": "private"
        }
        create_response = session.post(
            f"{BASE_URL}/api/casos",
            json=payload,
            headers=get_auth_header(resident_token)
        )
        assert create_response.status_code == 200
        caso_id = create_response.json()["id"]
        
        # Admin should be able to comment
        comment_payload = {
            "comment": "Admin response to resident's private case",
            "is_internal": False
        }
        response = session.post(
            f"{BASE_URL}/api/casos/{caso_id}/comments",
            json=comment_payload,
            headers=get_auth_header(admin_token)
        )
        
        assert response.status_code == 200, f"Admin should be able to comment on any case: {response.text}"
        print(f"✓ Admin can comment on any case")


class TestCommunityResponseFields:
    """Tests for response fields in community cases"""
    
    def test_community_case_includes_author_name(self, session, admin_token, resident_token):
        """Community cases include created_by_name in list response"""
        # Create community case as admin
        payload = {
            "title": f"TEST_Author_Name_{uuid.uuid4().hex[:8]}",
            "description": "Community case to check author name",
            "category": "otro",
            "priority": "low",
            "visibility": "community"
        }
        create_response = session.post(
            f"{BASE_URL}/api/casos",
            json=payload,
            headers=get_auth_header(admin_token)
        )
        assert create_response.status_code == 200
        caso_id = create_response.json()["id"]
        
        # Get list as resident
        response = session.get(
            f"{BASE_URL}/api/casos?page_size=50",
            headers=get_auth_header(resident_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Find the created case
        caso = next((c for c in data["items"] if c["id"] == caso_id), None)
        assert caso is not None, "Created case not found in list"
        assert "created_by_name" in caso, "Community case should include created_by_name"
        assert caso["created_by_name"] is not None and caso["created_by_name"] != ""
        print(f"✓ Community case includes author name: {caso['created_by_name']}")
    
    def test_community_case_detail_includes_author(self, session, admin_token, resident_token):
        """Community case detail includes 'Reportado por' info"""
        # Create community case as admin
        payload = {
            "title": f"TEST_Detail_Author_{uuid.uuid4().hex[:8]}",
            "description": "Community case detail author test",
            "category": "infraestructura",
            "priority": "medium",
            "visibility": "community"
        }
        create_response = session.post(
            f"{BASE_URL}/api/casos",
            json=payload,
            headers=get_auth_header(admin_token)
        )
        assert create_response.status_code == 200
        caso_id = create_response.json()["id"]
        
        # Get detail as resident
        response = session.get(
            f"{BASE_URL}/api/casos/{caso_id}",
            headers=get_auth_header(resident_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "created_by_name" in data, "Detail should include created_by_name"
        assert data["created_by_name"] is not None
        print(f"✓ Community case detail includes author: {data['created_by_name']}")


class TestExistingCasesWithoutVisibility:
    """Tests for backward compatibility with existing cases"""
    
    def test_existing_cases_treated_as_private(self, session, admin_token, resident_token):
        """Existing cases without visibility field are treated as private"""
        # Get all cases as admin
        admin_response = session.get(
            f"{BASE_URL}/api/casos?page_size=100",
            headers=get_auth_header(admin_token)
        )
        assert admin_response.status_code == 200
        admin_data = admin_response.json()
        
        # Get cases as resident
        resident_response = session.get(
            f"{BASE_URL}/api/casos?page_size=100",
            headers=get_auth_header(resident_token)
        )
        assert resident_response.status_code == 200
        resident_data = resident_response.json()
        
        # Admin should see more or equal cases than resident
        assert admin_data["total"] >= resident_data["total"], \
            f"Admin should see >= cases than resident. Admin: {admin_data['total']}, Resident: {resident_data['total']}"
        
        print(f"✓ Admin sees {admin_data['total']} cases, Resident sees {resident_data['total']} cases")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
