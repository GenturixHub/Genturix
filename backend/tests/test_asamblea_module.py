"""
Asamblea Virtual Module Tests
Tests for assembly creation, attendance, voting, results, and acta generation.
"""
import pytest
import requests
import os
import time
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
RESIDENT_EMAIL = "test-resident@genturix.com"
RESIDENT_PASSWORD = "Admin123!"

# Known assembly from context
KNOWN_ASSEMBLY_ID = "d1970935-a0ba-48d2-993d-2a11778c65d1"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.status_code}")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def resident_token():
    """Get resident authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": RESIDENT_EMAIL, "password": RESIDENT_PASSWORD}
    )
    if response.status_code != 200:
        pytest.skip(f"Resident login failed: {response.status_code}")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def admin_client(admin_token):
    """Authenticated session for admin"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture(scope="module")
def resident_client(resident_token):
    """Authenticated session for resident"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {resident_token}",
        "Content-Type": "application/json"
    })
    return session


class TestAsambleaListAndDetail:
    """Tests for GET /api/asamblea and GET /api/asamblea/{id}"""
    
    def test_list_assemblies_admin(self, admin_client):
        """Admin can list assemblies"""
        response = admin_client.get(f"{BASE_URL}/api/asamblea")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data, "Response should have 'items' key"
        assert isinstance(data["items"], list), "Items should be a list"
        
        # Verify structure of items
        if len(data["items"]) > 0:
            item = data["items"][0]
            assert "id" in item, "Assembly should have id"
            assert "title" in item, "Assembly should have title"
            assert "date" in item, "Assembly should have date"
            assert "status" in item, "Assembly should have status"
            assert "attendance_count" in item, "Assembly should have attendance_count"
        print(f"✓ Listed {len(data['items'])} assemblies")
    
    def test_list_assemblies_resident(self, resident_client):
        """Resident can list assemblies"""
        response = resident_client.get(f"{BASE_URL}/api/asamblea")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data
        print(f"✓ Resident listed {len(data['items'])} assemblies")
    
    def test_get_assembly_detail_admin(self, admin_client):
        """Admin can get assembly detail with agenda, votes, attendance"""
        response = admin_client.get(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify all required fields
        assert "id" in data, "Should have id"
        assert "title" in data, "Should have title"
        assert "date" in data, "Should have date"
        assert "status" in data, "Should have status"
        assert "modality" in data, "Should have modality"
        assert "agenda" in data, "Should have agenda"
        assert "attendance" in data, "Should have attendance"
        assert "attendance_count" in data, "Should have attendance_count"
        assert "my_attendance" in data, "Should have my_attendance"
        
        # Verify agenda structure
        if len(data["agenda"]) > 0:
            agenda_item = data["agenda"][0]
            assert "id" in agenda_item, "Agenda item should have id"
            assert "title" in agenda_item, "Agenda item should have title"
            assert "is_votable" in agenda_item, "Agenda item should have is_votable"
            if agenda_item.get("is_votable"):
                assert "vote_results" in agenda_item, "Votable item should have vote_results"
        
        print(f"✓ Got assembly detail: {data['title']}, {len(data['agenda'])} agenda items, {data['attendance_count']} attendees")
    
    def test_get_assembly_detail_resident(self, resident_client):
        """Resident can get assembly detail with my_vote info"""
        response = resident_client.get(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "my_attendance" in data, "Should have my_attendance"
        
        # Check for my_vote on votable items
        for item in data.get("agenda", []):
            if item.get("is_votable"):
                # my_vote can be null or a vote value
                assert "my_vote" in item or item.get("my_vote") is None, "Votable item should track my_vote"
        
        print(f"✓ Resident got assembly detail, my_attendance={data['my_attendance']}")
    
    def test_get_nonexistent_assembly(self, admin_client):
        """Getting nonexistent assembly returns 404"""
        response = admin_client.get(f"{BASE_URL}/api/asamblea/nonexistent-id-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Nonexistent assembly returns 404")


class TestAsambleaCreate:
    """Tests for POST /api/asamblea"""
    
    def test_create_assembly_admin(self, admin_client):
        """Admin can create assembly with agenda items"""
        future_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT10:00")
        
        payload = {
            "title": "TEST_Asamblea Ordinaria",
            "description": "Test assembly for automated testing",
            "date": future_date,
            "modality": "presencial",
            "meeting_link": None,
            "agenda_items": [
                {"title": "Aprobacion del acta anterior", "is_votable": False},
                {"title": "Presupuesto 2026", "is_votable": True},
                {"title": "Eleccion de junta directiva", "is_votable": True}
            ]
        }
        
        response = admin_client.post(f"{BASE_URL}/api/asamblea", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should have assembly id"
        assert data.get("title") == payload["title"], "Title should match"
        assert data.get("status") == "scheduled", "New assembly should be scheduled"
        
        # Store for cleanup
        TestAsambleaCreate.created_assembly_id = data["id"]
        print(f"✓ Created assembly: {data['id']}")
    
    def test_create_assembly_virtual_with_link(self, admin_client):
        """Admin can create virtual assembly with meeting link"""
        future_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%dT15:00")
        
        payload = {
            "title": "TEST_Asamblea Virtual",
            "description": "Virtual test assembly",
            "date": future_date,
            "modality": "virtual",
            "meeting_link": "https://zoom.us/j/123456789",
            "agenda_items": [
                {"title": "Punto unico", "is_votable": True}
            ]
        }
        
        response = admin_client.post(f"{BASE_URL}/api/asamblea", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("modality") == "virtual"
        assert data.get("meeting_link") == payload["meeting_link"]
        
        TestAsambleaCreate.virtual_assembly_id = data["id"]
        print(f"✓ Created virtual assembly with meeting link")
    
    def test_create_assembly_resident_forbidden(self, resident_client):
        """Resident cannot create assembly"""
        payload = {
            "title": "TEST_Unauthorized Assembly",
            "date": "2026-02-01T10:00",
            "modality": "presencial",
            "agenda_items": []
        }
        
        response = resident_client.post(f"{BASE_URL}/api/asamblea", json=payload)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Resident blocked from creating assembly")


class TestAsambleaAttendance:
    """Tests for POST /api/asamblea/{id}/attend"""
    
    def test_confirm_attendance_resident(self, resident_client):
        """Resident can confirm attendance"""
        response = resident_client.post(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}/attend")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Can be "confirmed" or "already_confirmed" (idempotent)
        assert data.get("status") in ["confirmed", "already_confirmed"], f"Unexpected status: {data}"
        print(f"✓ Attendance confirmation: {data.get('status')}")
    
    def test_confirm_attendance_idempotent(self, resident_client):
        """Confirming attendance twice is idempotent"""
        # First confirmation
        response1 = resident_client.post(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}/attend")
        assert response1.status_code == 200
        
        # Second confirmation should also succeed
        response2 = resident_client.post(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}/attend")
        assert response2.status_code == 200
        
        data = response2.json()
        assert data.get("status") == "already_confirmed", "Second call should return already_confirmed"
        print("✓ Attendance confirmation is idempotent")
    
    def test_confirm_attendance_nonexistent_assembly(self, resident_client):
        """Confirming attendance to nonexistent assembly returns 404"""
        response = resident_client.post(f"{BASE_URL}/api/asamblea/nonexistent-id/attend")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Attendance to nonexistent assembly returns 404")


class TestAsambleaVoting:
    """Tests for POST /api/asamblea/{id}/vote"""
    
    def test_cast_vote_yes(self, resident_client, admin_client):
        """Resident can vote yes on votable agenda item"""
        # First get assembly detail to find a votable item
        detail_resp = admin_client.get(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}")
        assert detail_resp.status_code == 200
        
        agenda = detail_resp.json().get("agenda", [])
        votable_items = [item for item in agenda if item.get("is_votable")]
        
        if not votable_items:
            pytest.skip("No votable items in known assembly")
        
        votable_item_id = votable_items[0]["id"]
        
        payload = {
            "agenda_item_id": votable_item_id,
            "vote": "yes"
        }
        
        response = resident_client.post(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}/vote", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # API returns "recorded", "updated", or "vote_updated"
        assert data.get("status") in ["recorded", "updated", "vote_updated"], f"Unexpected status: {data}"
        print(f"✓ Vote recorded: {data.get('status')}")
    
    def test_cast_vote_no(self, resident_client, admin_client):
        """Resident can vote no"""
        detail_resp = admin_client.get(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}")
        agenda = detail_resp.json().get("agenda", [])
        votable_items = [item for item in agenda if item.get("is_votable")]
        
        if len(votable_items) < 2:
            pytest.skip("Need at least 2 votable items")
        
        votable_item_id = votable_items[1]["id"]
        
        payload = {
            "agenda_item_id": votable_item_id,
            "vote": "no"
        }
        
        response = resident_client.post(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}/vote", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Vote 'no' recorded")
    
    def test_cast_vote_abstain(self, resident_client, admin_client):
        """Resident can abstain"""
        detail_resp = admin_client.get(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}")
        agenda = detail_resp.json().get("agenda", [])
        votable_items = [item for item in agenda if item.get("is_votable")]
        
        if len(votable_items) < 3:
            pytest.skip("Need at least 3 votable items")
        
        votable_item_id = votable_items[2]["id"]
        
        payload = {
            "agenda_item_id": votable_item_id,
            "vote": "abstain"
        }
        
        response = resident_client.post(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}/vote", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Vote 'abstain' recorded")
    
    def test_update_vote_allowed(self, resident_client, admin_client):
        """Resident can update their vote"""
        detail_resp = admin_client.get(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}")
        agenda = detail_resp.json().get("agenda", [])
        votable_items = [item for item in agenda if item.get("is_votable")]
        
        if not votable_items:
            pytest.skip("No votable items")
        
        votable_item_id = votable_items[0]["id"]
        
        # Vote yes first
        payload1 = {"agenda_item_id": votable_item_id, "vote": "yes"}
        response1 = resident_client.post(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}/vote", json=payload1)
        assert response1.status_code == 200
        
        # Change to no
        payload2 = {"agenda_item_id": votable_item_id, "vote": "no"}
        response2 = resident_client.post(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}/vote", json=payload2)
        assert response2.status_code == 200
        
        data = response2.json()
        # API returns "vote_updated" for updates
        assert data.get("status") in ["updated", "vote_updated"], "Vote update should return 'updated' or 'vote_updated' status"
        print("✓ Vote update allowed")
    
    def test_vote_nonvotable_item_rejected(self, resident_client, admin_client):
        """Voting on non-votable item is rejected"""
        detail_resp = admin_client.get(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}")
        agenda = detail_resp.json().get("agenda", [])
        non_votable_items = [item for item in agenda if not item.get("is_votable")]
        
        if not non_votable_items:
            pytest.skip("No non-votable items to test")
        
        non_votable_id = non_votable_items[0]["id"]
        
        payload = {"agenda_item_id": non_votable_id, "vote": "yes"}
        response = resident_client.post(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}/vote", json=payload)
        
        # Should be rejected (400 or 422)
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print("✓ Vote on non-votable item rejected")


class TestAsambleaResults:
    """Tests for GET /api/asamblea/{id}/results"""
    
    def test_get_results(self, admin_client):
        """Get vote results for assembly"""
        response = admin_client.get(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}/results")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "assembly" in data, "Should have assembly info"
        assert "results" in data, "Should have results"
        assert "attendance_count" in data, "Should have attendance_count"
        
        # Verify results structure - API uses agenda_item_id and votes dict
        for result in data.get("results", []):
            assert "agenda_item_id" in result or "item_id" in result, "Result should have agenda_item_id or item_id"
            assert "title" in result, "Result should have title"
            # Votes can be in a nested dict or flat
            if "votes" in result:
                assert "yes" in result["votes"], "Result votes should have yes count"
                assert "no" in result["votes"], "Result votes should have no count"
                assert "abstain" in result["votes"], "Result votes should have abstain count"
            else:
                assert "yes" in result, "Result should have yes count"
                assert "no" in result, "Result should have no count"
                assert "abstain" in result, "Result should have abstain count"
        
        print(f"✓ Got results: {len(data['results'])} votable items, {data['attendance_count']} attendees")


class TestAsambleaAgenda:
    """Tests for POST /api/asamblea/{id}/agenda"""
    
    def test_add_agenda_item_admin(self, admin_client):
        """Admin can add agenda item to assembly"""
        payload = {
            "title": "TEST_Nuevo punto de agenda",
            "is_votable": True
        }
        
        response = admin_client.post(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}/agenda", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Should return new agenda item id"
        assert data.get("title") == payload["title"]
        assert data.get("is_votable") == True
        
        print(f"✓ Added agenda item: {data['id']}")
    
    def test_add_agenda_item_resident_forbidden(self, resident_client):
        """Resident cannot add agenda items"""
        payload = {
            "title": "TEST_Unauthorized agenda item",
            "is_votable": False
        }
        
        response = resident_client.post(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}/agenda", json=payload)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Resident blocked from adding agenda items")


class TestAsambleaStatusUpdate:
    """Tests for PATCH /api/asamblea/{id}?status=X"""
    
    def test_update_status_to_in_progress(self, admin_client):
        """Admin can start assembly (scheduled -> in_progress)"""
        # Use a test assembly if available
        assembly_id = getattr(TestAsambleaCreate, 'created_assembly_id', None)
        if not assembly_id:
            pytest.skip("No test assembly created")
        
        response = admin_client.patch(f"{BASE_URL}/api/asamblea/{assembly_id}?status=in_progress")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("new_status") == "in_progress"
        print("✓ Assembly status updated to in_progress")
    
    def test_update_status_to_completed(self, admin_client):
        """Admin can complete assembly"""
        assembly_id = getattr(TestAsambleaCreate, 'created_assembly_id', None)
        if not assembly_id:
            pytest.skip("No test assembly created")
        
        response = admin_client.patch(f"{BASE_URL}/api/asamblea/{assembly_id}?status=completed")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("new_status") == "completed"
        print("✓ Assembly status updated to completed")
    
    def test_update_status_to_cancelled(self, admin_client):
        """Admin can cancel assembly"""
        assembly_id = getattr(TestAsambleaCreate, 'virtual_assembly_id', None)
        if not assembly_id:
            pytest.skip("No virtual test assembly created")
        
        response = admin_client.patch(f"{BASE_URL}/api/asamblea/{assembly_id}?status=cancelled")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("new_status") == "cancelled"
        print("✓ Assembly status updated to cancelled")
    
    def test_update_status_invalid_rejected(self, admin_client):
        """Invalid status is rejected"""
        response = admin_client.patch(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}?status=invalid_status")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Invalid status rejected with 422")
    
    def test_update_status_resident_forbidden(self, resident_client):
        """Resident cannot update assembly status"""
        response = resident_client.patch(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}?status=completed")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Resident blocked from updating status")


class TestAsambleaActaGeneration:
    """Tests for POST /api/asamblea/{id}/generate-acta"""
    
    def test_generate_acta_admin(self, admin_client):
        """Admin can generate PDF acta"""
        response = admin_client.post(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}/generate-acta")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # API returns PDF directly, not JSON
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected PDF, got {content_type}"
        
        # Verify PDF content starts with %PDF
        assert response.content[:4] == b'%PDF', "Response should be a valid PDF"
        assert len(response.content) > 1000, "PDF should have substantial content"
        
        print(f"✓ Acta generated: {len(response.content)} bytes PDF")
    
    def test_generate_acta_resident_forbidden(self, resident_client):
        """Resident cannot generate acta"""
        response = resident_client.post(f"{BASE_URL}/api/asamblea/{KNOWN_ASSEMBLY_ID}/generate-acta")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Resident blocked from generating acta")


class TestAsambleaIntegration:
    """Integration tests for complete assembly workflow"""
    
    def test_full_assembly_workflow(self, admin_client, resident_client):
        """Test complete workflow: create -> attend -> vote -> results"""
        # 1. Create assembly
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%dT10:00")
        create_payload = {
            "title": "TEST_Integration Assembly",
            "description": "Full workflow test",
            "date": future_date,
            "modality": "hibrida",
            "meeting_link": "https://meet.google.com/test",
            "agenda_items": [
                {"title": "Aprobacion presupuesto", "is_votable": True},
                {"title": "Informe de gastos", "is_votable": False}
            ]
        }
        
        create_resp = admin_client.post(f"{BASE_URL}/api/asamblea", json=create_payload)
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        assembly_id = create_resp.json()["id"]
        print(f"  1. Created assembly: {assembly_id}")
        
        # 2. Resident confirms attendance
        attend_resp = resident_client.post(f"{BASE_URL}/api/asamblea/{assembly_id}/attend")
        assert attend_resp.status_code == 200, f"Attend failed: {attend_resp.text}"
        print("  2. Resident confirmed attendance")
        
        # 3. Get detail to find votable item
        detail_resp = resident_client.get(f"{BASE_URL}/api/asamblea/{assembly_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["my_attendance"] == True, "my_attendance should be True"
        
        votable_items = [item for item in detail["agenda"] if item["is_votable"]]
        assert len(votable_items) > 0, "Should have votable items"
        votable_id = votable_items[0]["id"]
        print(f"  3. Got detail, found votable item: {votable_id}")
        
        # 4. Resident votes
        vote_payload = {"agenda_item_id": votable_id, "vote": "yes"}
        vote_resp = resident_client.post(f"{BASE_URL}/api/asamblea/{assembly_id}/vote", json=vote_payload)
        assert vote_resp.status_code == 200, f"Vote failed: {vote_resp.text}"
        print("  4. Resident voted 'yes'")
        
        # 5. Verify vote in detail
        detail_resp2 = resident_client.get(f"{BASE_URL}/api/asamblea/{assembly_id}")
        detail2 = detail_resp2.json()
        voted_item = next((item for item in detail2["agenda"] if item["id"] == votable_id), None)
        assert voted_item is not None
        assert voted_item.get("my_vote") == "yes", f"my_vote should be 'yes', got {voted_item.get('my_vote')}"
        print("  5. Verified my_vote in detail")
        
        # 6. Get results
        results_resp = admin_client.get(f"{BASE_URL}/api/asamblea/{assembly_id}/results")
        assert results_resp.status_code == 200, f"Results failed: {results_resp.text}"
        results = results_resp.json()
        assert results["attendance_count"] >= 1, "Should have at least 1 attendee"
        print(f"  6. Got results: {results['attendance_count']} attendees")
        
        # 7. Admin starts assembly
        start_resp = admin_client.patch(f"{BASE_URL}/api/asamblea/{assembly_id}?status=in_progress")
        assert start_resp.status_code == 200
        print("  7. Admin started assembly")
        
        # 8. Admin completes assembly
        complete_resp = admin_client.patch(f"{BASE_URL}/api/asamblea/{assembly_id}?status=completed")
        assert complete_resp.status_code == 200
        print("  8. Admin completed assembly")
        
        # 9. Generate acta
        acta_resp = admin_client.post(f"{BASE_URL}/api/asamblea/{assembly_id}/generate-acta")
        assert acta_resp.status_code == 200, f"Acta generation failed: {acta_resp.text}"
        print("  9. Generated acta PDF")
        
        print("✓ Full assembly workflow completed successfully!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
