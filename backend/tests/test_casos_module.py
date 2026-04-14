"""
Test suite for Casos/Incidencias module - Optimized for rate limiting
Tests: CRUD operations, access control, comments, notifications
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
ADMIN_CREDS = {"email": "admin@genturix.com", "password": "Admin123!"}
RESIDENT_CREDS = {"email": "test-resident@genturix.com", "password": "Admin123!"}
GUARD_CREDS = {"email": "guarda1@genturix.com", "password": "Guard123!"}


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


@pytest.fixture(scope="module")
def guard_token(session, resident_token):
    """Get guard token once for all tests"""
    time.sleep(12)  # Wait for rate limit
    response = session.post(f"{BASE_URL}/api/auth/login", json=GUARD_CREDS)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Guard login failed: {response.text}")


def get_auth_header(token):
    """Return authorization header"""
    return {"Authorization": f"Bearer {token}"}


# ==================== AUTHENTICATION TESTS ====================

def test_01_admin_login(admin_token):
    """Admin can login successfully"""
    assert admin_token is not None, "Admin login failed"
    print(f"✓ Admin login successful")


def test_02_resident_login(resident_token):
    """Resident can login successfully"""
    assert resident_token is not None, "Resident login failed"
    print(f"✓ Resident login successful")


def test_03_guard_login(guard_token):
    """Guard can login successfully"""
    assert guard_token is not None, "Guard login failed"
    print(f"✓ Guard login successful")


# ==================== CREATE CASO TESTS ====================

def test_10_resident_create_caso(session, resident_token):
    """Resident can create a new case"""
    payload = {
        "title": "TEST_Fuga de agua en pasillo B",
        "description": "Hay una fuga de agua en el pasillo B cerca del ascensor.",
        "category": "mantenimiento",
        "priority": "high"
    }
    
    response = session.post(
        f"{BASE_URL}/api/casos",
        json=payload,
        headers=get_auth_header(resident_token)
    )
    
    assert response.status_code == 200, f"Create caso failed: {response.text}"
    data = response.json()
    
    assert "id" in data, "Response missing 'id'"
    assert data["title"] == payload["title"]
    assert data["status"] == "open"
    assert "condominium_id" in data
    
    print(f"✓ Resident created caso: {data['id']}")


def test_11_admin_create_caso(session, admin_token):
    """Admin can create a new case"""
    payload = {
        "title": "TEST_Problema de seguridad",
        "description": "La puerta principal no cierra correctamente.",
        "category": "seguridad",
        "priority": "urgent"
    }
    
    response = session.post(
        f"{BASE_URL}/api/casos",
        json=payload,
        headers=get_auth_header(admin_token)
    )
    
    assert response.status_code == 200, f"Create caso failed: {response.text}"
    data = response.json()
    assert data["status"] == "open"
    assert data["priority"] == "urgent"
    
    print(f"✓ Admin created caso: {data['id']}")


def test_12_create_caso_validation(session, resident_token):
    """Create caso validates required fields"""
    # Missing title
    response = session.post(
        f"{BASE_URL}/api/casos",
        json={"description": "Test", "category": "otro"},
        headers=get_auth_header(resident_token)
    )
    assert response.status_code == 422, "Should reject missing title"
    
    # Invalid category
    response = session.post(
        f"{BASE_URL}/api/casos",
        json={"title": "Test", "description": "Test", "category": "invalid"},
        headers=get_auth_header(resident_token)
    )
    assert response.status_code == 422, "Should reject invalid category"
    
    print(f"✓ Create caso validation working correctly")


# ==================== GET CASOS TESTS ====================

def test_20_admin_get_all_casos(session, admin_token):
    """Admin can see all cases in condominium"""
    response = session.get(
        f"{BASE_URL}/api/casos",
        headers=get_auth_header(admin_token)
    )
    
    assert response.status_code == 200, f"Get casos failed: {response.text}"
    data = response.json()
    
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "total_pages" in data
    
    print(f"✓ Admin can see {data['total']} casos")


def test_21_resident_get_own_casos(session, resident_token):
    """Resident can only see their own cases"""
    response = session.get(
        f"{BASE_URL}/api/casos",
        headers=get_auth_header(resident_token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    print(f"✓ Resident can see {data['total']} of their own casos")


def test_22_filter_casos_by_status(session, admin_token):
    """Can filter cases by status"""
    response = session.get(
        f"{BASE_URL}/api/casos?status=open",
        headers=get_auth_header(admin_token)
    )
    
    assert response.status_code == 200
    data = response.json()
    
    for item in data.get("items", []):
        assert item["status"] == "open"
    
    print(f"✓ Filter by status working: {len(data.get('items', []))} open casos")


# ==================== STATS ENDPOINT TESTS ====================

def test_30_admin_get_stats(session, admin_token):
    """Admin can access stats endpoint"""
    response = session.get(
        f"{BASE_URL}/api/casos/stats",
        headers=get_auth_header(admin_token)
    )
    
    assert response.status_code == 200, f"Get stats failed: {response.text}"
    data = response.json()
    
    assert "total" in data
    assert "open" in data
    assert "in_progress" in data
    assert "closed" in data
    assert "urgent" in data
    
    print(f"✓ Admin stats: total={data['total']}, open={data['open']}, urgent={data['urgent']}")


def test_31_resident_cannot_access_stats(session, resident_token):
    """Resident cannot access stats endpoint (403)"""
    response = session.get(
        f"{BASE_URL}/api/casos/stats",
        headers=get_auth_header(resident_token)
    )
    
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    print(f"✓ Resident correctly denied access to stats (403)")


def test_32_guard_cannot_access_stats(session, guard_token):
    """Guard cannot access stats endpoint (403)"""
    response = session.get(
        f"{BASE_URL}/api/casos/stats",
        headers=get_auth_header(guard_token)
    )
    
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    print(f"✓ Guard correctly denied access to stats (403)")


# ==================== CASO DETAIL & UPDATE TESTS ====================

def test_40_get_caso_detail(session, resident_token):
    """Can get case detail with comments"""
    # Create a caso
    create_response = session.post(
        f"{BASE_URL}/api/casos",
        json={
            "title": "TEST_Caso para detalle",
            "description": "Descripción del caso",
            "category": "limpieza",
            "priority": "medium"
        },
        headers=get_auth_header(resident_token)
    )
    assert create_response.status_code == 200
    caso_id = create_response.json()["id"]
    
    # Get detail
    response = session.get(
        f"{BASE_URL}/api/casos/{caso_id}",
        headers=get_auth_header(resident_token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == caso_id
    assert "comments" in data
    
    print(f"✓ Got caso detail with {len(data['comments'])} comments")


def test_41_resident_cannot_see_others_caso(session, admin_token, resident_token):
    """Resident cannot see another user's case"""
    # Create caso as admin
    create_response = session.post(
        f"{BASE_URL}/api/casos",
        json={
            "title": "TEST_Admin caso privado",
            "description": "Este caso fue creado por admin",
            "category": "otro",
            "priority": "low"
        },
        headers=get_auth_header(admin_token)
    )
    assert create_response.status_code == 200
    caso_id = create_response.json()["id"]
    
    # Try to access as resident
    response = session.get(
        f"{BASE_URL}/api/casos/{caso_id}",
        headers=get_auth_header(resident_token)
    )
    
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    print(f"✓ Resident correctly denied access to admin's caso (403)")


def test_50_admin_update_caso_status(session, admin_token, resident_token):
    """Admin can update case status"""
    # Create caso as resident
    create_response = session.post(
        f"{BASE_URL}/api/casos",
        json={
            "title": "TEST_Caso para actualizar",
            "description": "Este caso será actualizado",
            "category": "ruido",
            "priority": "medium"
        },
        headers=get_auth_header(resident_token)
    )
    assert create_response.status_code == 200
    caso_id = create_response.json()["id"]
    
    # Update as admin
    response = session.patch(
        f"{BASE_URL}/api/casos/{caso_id}",
        json={"status": "in_progress"},
        headers=get_auth_header(admin_token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"
    
    print(f"✓ Admin updated caso status to 'in_progress'")


def test_52_resident_cannot_update_caso(session, resident_token):
    """Resident cannot update case status (403)"""
    # Create caso
    create_response = session.post(
        f"{BASE_URL}/api/casos",
        json={
            "title": "TEST_Caso que residente no puede actualizar",
            "description": "Residente no debería poder cambiar el estado",
            "category": "convivencia",
            "priority": "low"
        },
        headers=get_auth_header(resident_token)
    )
    assert create_response.status_code == 200
    caso_id = create_response.json()["id"]
    
    # Try to update as resident
    response = session.patch(
        f"{BASE_URL}/api/casos/{caso_id}",
        json={"status": "closed"},
        headers=get_auth_header(resident_token)
    )
    
    assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    print(f"✓ Resident correctly denied from updating caso status (403)")


def test_53_close_caso_sets_closed_at(session, admin_token, resident_token):
    """Closing a caso sets closed_at timestamp"""
    # Create caso
    create_response = session.post(
        f"{BASE_URL}/api/casos",
        json={
            "title": "TEST_Caso para cerrar",
            "description": "Este caso será cerrado",
            "category": "infraestructura",
            "priority": "medium"
        },
        headers=get_auth_header(resident_token)
    )
    assert create_response.status_code == 200
    caso_id = create_response.json()["id"]
    
    # Close as admin
    response = session.patch(
        f"{BASE_URL}/api/casos/{caso_id}",
        json={"status": "closed"},
        headers=get_auth_header(admin_token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "closed"
    assert data.get("closed_at") is not None
    
    print(f"✓ Closing caso sets closed_at timestamp")


# ==================== COMMENTS TESTS ====================

def test_60_add_comment_to_caso(session, resident_token):
    """Can add comment to a case"""
    # Create caso
    create_response = session.post(
        f"{BASE_URL}/api/casos",
        json={
            "title": "TEST_Caso con comentarios",
            "description": "Este caso tendrá comentarios",
            "category": "mantenimiento",
            "priority": "medium"
        },
        headers=get_auth_header(resident_token)
    )
    assert create_response.status_code == 200
    caso_id = create_response.json()["id"]
    
    # Add comment
    response = session.post(
        f"{BASE_URL}/api/casos/{caso_id}/comments",
        json={"comment": "Este es un comentario de prueba", "is_internal": False},
        headers=get_auth_header(resident_token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["comment"] == "Este es un comentario de prueba"
    assert data["is_internal"] == False
    
    print(f"✓ Added comment to caso")


def test_61_admin_add_internal_comment(session, admin_token, resident_token):
    """Admin can add internal comment"""
    # Create caso as resident
    create_response = session.post(
        f"{BASE_URL}/api/casos",
        json={
            "title": "TEST_Caso con nota interna",
            "description": "Este caso tendrá una nota interna",
            "category": "seguridad",
            "priority": "high"
        },
        headers=get_auth_header(resident_token)
    )
    assert create_response.status_code == 200
    caso_id = create_response.json()["id"]
    
    # Add internal comment as admin
    response = session.post(
        f"{BASE_URL}/api/casos/{caso_id}/comments",
        json={"comment": "Nota interna: revisar con mantenimiento", "is_internal": True},
        headers=get_auth_header(admin_token)
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_internal"] == True
    
    print(f"✓ Admin added internal comment")


def test_62_resident_cannot_see_internal_comments(session, admin_token, resident_token):
    """Resident cannot see internal comments"""
    # Create caso as resident
    create_response = session.post(
        f"{BASE_URL}/api/casos",
        json={
            "title": "TEST_Caso con comentarios mixtos",
            "description": "Este caso tendrá comentarios públicos e internos",
            "category": "limpieza",
            "priority": "low"
        },
        headers=get_auth_header(resident_token)
    )
    assert create_response.status_code == 200
    caso_id = create_response.json()["id"]
    
    # Add public comment as resident
    session.post(
        f"{BASE_URL}/api/casos/{caso_id}/comments",
        json={"comment": "Comentario público", "is_internal": False},
        headers=get_auth_header(resident_token)
    )
    
    # Add internal comment as admin
    session.post(
        f"{BASE_URL}/api/casos/{caso_id}/comments",
        json={"comment": "INTERNO: No mostrar al residente", "is_internal": True},
        headers=get_auth_header(admin_token)
    )
    
    # Get detail as resident
    detail_response = session.get(
        f"{BASE_URL}/api/casos/{caso_id}",
        headers=get_auth_header(resident_token)
    )
    
    assert detail_response.status_code == 200
    data = detail_response.json()
    
    # Resident should NOT see internal comments
    for comment in data.get("comments", []):
        assert comment["is_internal"] == False, "Resident should not see internal comments"
    
    print(f"✓ Resident cannot see internal comments")


def test_63_admin_can_see_internal_comments(session, admin_token):
    """Admin can see internal comments"""
    # Create caso
    create_response = session.post(
        f"{BASE_URL}/api/casos",
        json={
            "title": "TEST_Caso para admin ver internos",
            "description": "Admin verá todos los comentarios",
            "category": "otro",
            "priority": "medium"
        },
        headers=get_auth_header(admin_token)
    )
    assert create_response.status_code == 200
    caso_id = create_response.json()["id"]
    
    # Add internal comment
    session.post(
        f"{BASE_URL}/api/casos/{caso_id}/comments",
        json={"comment": "Comentario interno visible para admin", "is_internal": True},
        headers=get_auth_header(admin_token)
    )
    
    # Get detail as admin
    detail_response = session.get(
        f"{BASE_URL}/api/casos/{caso_id}",
        headers=get_auth_header(admin_token)
    )
    
    assert detail_response.status_code == 200
    data = detail_response.json()
    
    # Admin should see internal comments
    internal_comments = [c for c in data.get("comments", []) if c["is_internal"]]
    assert len(internal_comments) > 0, "Admin should see internal comments"
    
    print(f"✓ Admin can see internal comments")


# ==================== LEGACY NOTIFICATIONS TESTS ====================

def test_70_legacy_notifications_still_work(session, admin_token):
    """Legacy /api/notifications endpoint still works"""
    response = session.get(
        f"{BASE_URL}/api/notifications",
        headers=get_auth_header(admin_token)
    )
    
    assert response.status_code == 200, f"Legacy notifications broken: {response.status_code}"
    print(f"✓ Legacy /api/notifications endpoint still works")


def test_71_legacy_unread_count_still_works(session, admin_token):
    """Legacy /api/notifications/unread-count endpoint still works"""
    response = session.get(
        f"{BASE_URL}/api/notifications/unread-count",
        headers=get_auth_header(admin_token)
    )
    
    assert response.status_code == 200, f"Legacy unread-count broken: {response.status_code}"
    print(f"✓ Legacy /api/notifications/unread-count endpoint still works")


def test_72_notifications_v2_still_work(session, admin_token):
    """Notifications V2 endpoints still work"""
    response = session.get(
        f"{BASE_URL}/api/notifications/v2",
        headers=get_auth_header(admin_token)
    )
    
    assert response.status_code == 200, f"Notifications V2 broken: {response.status_code}"
    data = response.json()
    assert "items" in data
    print(f"✓ Notifications V2 endpoints still work")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
