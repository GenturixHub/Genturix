"""
GENTURIX - Visitor Flow Backend Tests (Iteration 5)
Testing the corrected visitor flow:
- Resident CREATES pre-registration
- Guard EXECUTES entry/exit
- Admin AUDITS everything

Endpoints tested:
- POST /api/visitors/pre-register - Resident creates visitor
- GET /api/visitors/my-visitors - Resident sees their visitors
- DELETE /api/visitors/{id} - Resident cancels pending visitor
- GET /api/visitors/pending - Guard sees expected visitors
- POST /api/visitors/{id}/entry - Guard registers entry
- POST /api/visitors/{id}/exit - Guard registers exit
- GET /api/visitors/all - Admin sees all visitors
- GET /api/audit/logs - Admin audits visitor events
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://visits-multlang.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@genturix.com"
ADMIN_PASSWORD = "Admin123!"
GUARD_EMAIL = "guarda1@genturix.com"
GUARD_PASSWORD = "Guard123!"
RESIDENT_EMAIL = "residente@genturix.com"
RESIDENT_PASSWORD = "Resi123!"


class TestVisitorPreRegistration:
    """Test Resident pre-registration flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get resident token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.created_visitor_ids = []
    
    def test_pre_register_visitor_full_data(self):
        """POST /api/visitors/pre-register - Create visitor with all fields"""
        unique_id = str(uuid.uuid4())[:8]
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        visitor_data = {
            "full_name": f"TEST_Visitante_{unique_id}",
            "national_id": f"ID-{unique_id}",
            "vehicle_plate": f"ABC-{unique_id[:3].upper()}",
            "visit_type": "familiar",
            "expected_date": tomorrow,
            "expected_time": "14:00",
            "notes": "Test visitor for automated testing"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/visitors/pre-register",
            headers=self.headers,
            json=visitor_data
        )
        
        assert response.status_code == 200, f"Pre-register failed: {response.text}"
        data = response.json()
        
        # Verify response
        assert "id" in data, "Response missing 'id'"
        assert data["status"] == "pending", f"Expected status 'pending', got '{data.get('status')}'"
        assert "message" in data
        
        self.created_visitor_ids.append(data["id"])
        print(f"✓ Pre-registered visitor: {visitor_data['full_name']} (ID: {data['id']})")
        return data["id"]
    
    def test_pre_register_visitor_minimal_data(self):
        """POST /api/visitors/pre-register - Create visitor with minimal required fields"""
        unique_id = str(uuid.uuid4())[:8]
        today = datetime.now().strftime("%Y-%m-%d")
        
        visitor_data = {
            "full_name": f"TEST_MinimalVisitor_{unique_id}",
            "expected_date": today,
            "visit_type": "friend"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/visitors/pre-register",
            headers=self.headers,
            json=visitor_data
        )
        
        assert response.status_code == 200, f"Pre-register failed: {response.text}"
        data = response.json()
        assert data["status"] == "pending"
        
        self.created_visitor_ids.append(data["id"])
        print(f"✓ Pre-registered minimal visitor: {visitor_data['full_name']}")
        return data["id"]
    
    def test_pre_register_all_visit_types(self):
        """Test all visit types: familiar, friend, delivery, service, other"""
        visit_types = ["familiar", "friend", "delivery", "service", "other"]
        today = datetime.now().strftime("%Y-%m-%d")
        
        for visit_type in visit_types:
            unique_id = str(uuid.uuid4())[:8]
            response = requests.post(
                f"{BASE_URL}/api/visitors/pre-register",
                headers=self.headers,
                json={
                    "full_name": f"TEST_{visit_type}_{unique_id}",
                    "expected_date": today,
                    "visit_type": visit_type
                }
            )
            assert response.status_code == 200, f"Failed for visit_type '{visit_type}': {response.text}"
            self.created_visitor_ids.append(response.json()["id"])
            print(f"✓ Visit type '{visit_type}' accepted")
    
    def test_get_my_visitors(self):
        """GET /api/visitors/my-visitors - Resident sees their visitors"""
        # First create a visitor
        unique_id = str(uuid.uuid4())[:8]
        today = datetime.now().strftime("%Y-%m-%d")
        
        create_response = requests.post(
            f"{BASE_URL}/api/visitors/pre-register",
            headers=self.headers,
            json={
                "full_name": f"TEST_MyVisitor_{unique_id}",
                "expected_date": today,
                "visit_type": "friend"
            }
        )
        assert create_response.status_code == 200
        created_id = create_response.json()["id"]
        self.created_visitor_ids.append(created_id)
        
        # Get my visitors
        response = requests.get(
            f"{BASE_URL}/api/visitors/my-visitors",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get my visitors failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        
        # Find our created visitor
        found = False
        for visitor in data:
            if visitor.get("id") == created_id:
                found = True
                assert visitor["status"] == "pending"
                assert "created_by_name" in visitor
                assert "expected_date" in visitor
                break
        
        assert found, f"Created visitor {created_id} not found in my-visitors list"
        print(f"✓ Found {len(data)} visitors in my-visitors list")
    
    def test_cancel_pending_visitor(self):
        """DELETE /api/visitors/{id} - Resident cancels pending visitor"""
        # First create a visitor
        unique_id = str(uuid.uuid4())[:8]
        today = datetime.now().strftime("%Y-%m-%d")
        
        create_response = requests.post(
            f"{BASE_URL}/api/visitors/pre-register",
            headers=self.headers,
            json={
                "full_name": f"TEST_ToCancel_{unique_id}",
                "expected_date": today,
                "visit_type": "other"
            }
        )
        assert create_response.status_code == 200
        visitor_id = create_response.json()["id"]
        
        # Cancel the visitor
        response = requests.delete(
            f"{BASE_URL}/api/visitors/{visitor_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Cancel failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"✓ Cancelled visitor: {visitor_id}")
        
        # Verify it's cancelled in my-visitors
        my_visitors = requests.get(
            f"{BASE_URL}/api/visitors/my-visitors",
            headers=self.headers
        ).json()
        
        for visitor in my_visitors:
            if visitor.get("id") == visitor_id:
                assert visitor["status"] == "cancelled", f"Expected 'cancelled', got '{visitor['status']}'"
                print(f"✓ Verified visitor status is 'cancelled'")
                break


class TestGuardVisitorExecution:
    """Test Guard entry/exit execution flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get guard and resident tokens"""
        # Guard token
        guard_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        assert guard_response.status_code == 200, f"Guard login failed: {guard_response.text}"
        self.guard_token = guard_response.json()["access_token"]
        self.guard_headers = {
            "Authorization": f"Bearer {self.guard_token}",
            "Content-Type": "application/json"
        }
        
        # Resident token (to create visitors)
        resident_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        assert resident_response.status_code == 200
        self.resident_token = resident_response.json()["access_token"]
        self.resident_headers = {
            "Authorization": f"Bearer {self.resident_token}",
            "Content-Type": "application/json"
        }
    
    def _create_test_visitor(self):
        """Helper to create a test visitor as resident"""
        unique_id = str(uuid.uuid4())[:8]
        today = datetime.now().strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/visitors/pre-register",
            headers=self.resident_headers,
            json={
                "full_name": f"TEST_GuardTest_{unique_id}",
                "national_id": f"ID-{unique_id}",
                "vehicle_plate": f"XYZ-{unique_id[:3].upper()}",
                "expected_date": today,
                "expected_time": "10:00",
                "visit_type": "friend",
                "notes": "Test visitor for guard execution"
            }
        )
        assert response.status_code == 200
        return response.json()["id"]
    
    def test_get_pending_visitors(self):
        """GET /api/visitors/pending - Guard sees expected visitors"""
        # Create a visitor first
        visitor_id = self._create_test_visitor()
        
        # Guard gets pending visitors
        response = requests.get(
            f"{BASE_URL}/api/visitors/pending",
            headers=self.guard_headers
        )
        
        assert response.status_code == 200, f"Get pending failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Guard sees {len(data)} pending/inside visitors")
        
        # Verify structure
        if len(data) > 0:
            visitor = data[0]
            assert "id" in visitor
            assert "full_name" in visitor
            assert "status" in visitor
            assert "created_by_name" in visitor  # Resident name
            assert "expected_date" in visitor
    
    def test_search_pending_visitors_by_name(self):
        """GET /api/visitors/pending?search=name - Search by visitor name"""
        # Create a visitor with unique name
        unique_id = str(uuid.uuid4())[:8]
        today = datetime.now().strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/visitors/pre-register",
            headers=self.resident_headers,
            json={
                "full_name": f"TEST_SearchName_{unique_id}",
                "expected_date": today,
                "visit_type": "friend"
            }
        )
        assert response.status_code == 200
        
        # Search by name
        search_response = requests.get(
            f"{BASE_URL}/api/visitors/pending?search=SearchName_{unique_id}",
            headers=self.guard_headers
        )
        
        assert search_response.status_code == 200
        data = search_response.json()
        assert len(data) >= 1, "Should find at least 1 visitor"
        print(f"✓ Search by name found {len(data)} visitors")
    
    def test_search_pending_visitors_by_plate(self):
        """GET /api/visitors/pending?search=plate - Search by vehicle plate"""
        unique_id = str(uuid.uuid4())[:8]
        today = datetime.now().strftime("%Y-%m-%d")
        plate = f"PLT-{unique_id[:3].upper()}"
        
        response = requests.post(
            f"{BASE_URL}/api/visitors/pre-register",
            headers=self.resident_headers,
            json={
                "full_name": f"TEST_SearchPlate_{unique_id}",
                "vehicle_plate": plate,
                "expected_date": today,
                "visit_type": "friend"
            }
        )
        assert response.status_code == 200
        
        # Search by plate
        search_response = requests.get(
            f"{BASE_URL}/api/visitors/pending?search={plate}",
            headers=self.guard_headers
        )
        
        assert search_response.status_code == 200
        data = search_response.json()
        assert len(data) >= 1, "Should find at least 1 visitor by plate"
        print(f"✓ Search by plate found {len(data)} visitors")
    
    def test_register_visitor_entry(self):
        """POST /api/visitors/{id}/entry - Guard registers entry"""
        # Create visitor
        visitor_id = self._create_test_visitor()
        
        # Register entry
        response = requests.post(
            f"{BASE_URL}/api/visitors/{visitor_id}/entry",
            headers=self.guard_headers,
            json={
                "visitor_id": visitor_id,
                "notes": "Entry registered by test"
            }
        )
        
        assert response.status_code == 200, f"Entry registration failed: {response.text}"
        data = response.json()
        
        assert "entry_at" in data, "Response missing 'entry_at'"
        assert "message" in data
        print(f"✓ Entry registered at {data['entry_at']}")
        
        # Verify status changed
        pending = requests.get(
            f"{BASE_URL}/api/visitors/pending",
            headers=self.guard_headers
        ).json()
        
        for v in pending:
            if v.get("id") == visitor_id:
                assert v["status"] == "entry_registered", f"Expected 'entry_registered', got '{v['status']}'"
                assert v.get("entry_by_name") is not None, "Missing entry_by_name"
                print(f"✓ Visitor status is 'entry_registered', recorded by {v.get('entry_by_name')}")
                break
        
        return visitor_id
    
    def test_register_visitor_exit(self):
        """POST /api/visitors/{id}/exit - Guard registers exit"""
        # Create visitor and register entry first
        visitor_id = self._create_test_visitor()
        
        # Register entry
        entry_response = requests.post(
            f"{BASE_URL}/api/visitors/{visitor_id}/entry",
            headers=self.guard_headers,
            json={"visitor_id": visitor_id, "notes": ""}
        )
        assert entry_response.status_code == 200
        
        # Register exit
        response = requests.post(
            f"{BASE_URL}/api/visitors/{visitor_id}/exit",
            headers=self.guard_headers,
            json={
                "visitor_id": visitor_id,
                "notes": "Exit registered by test"
            }
        )
        
        assert response.status_code == 200, f"Exit registration failed: {response.text}"
        data = response.json()
        
        assert "exit_at" in data, "Response missing 'exit_at'"
        assert "message" in data
        print(f"✓ Exit registered at {data['exit_at']}")
        
        # Verify in resident's my-visitors
        my_visitors = requests.get(
            f"{BASE_URL}/api/visitors/my-visitors",
            headers=self.resident_headers
        ).json()
        
        for v in my_visitors:
            if v.get("id") == visitor_id:
                assert v["status"] == "exit_registered", f"Expected 'exit_registered', got '{v['status']}'"
                assert v.get("exit_by_name") is not None, "Missing exit_by_name"
                print(f"✓ Visitor status is 'exit_registered', recorded by {v.get('exit_by_name')}")
                break
    
    def test_cannot_register_entry_twice(self):
        """Cannot register entry for visitor already inside"""
        visitor_id = self._create_test_visitor()
        
        # First entry
        requests.post(
            f"{BASE_URL}/api/visitors/{visitor_id}/entry",
            headers=self.guard_headers,
            json={"visitor_id": visitor_id, "notes": ""}
        )
        
        # Second entry should fail
        response = requests.post(
            f"{BASE_URL}/api/visitors/{visitor_id}/entry",
            headers=self.guard_headers,
            json={"visitor_id": visitor_id, "notes": ""}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Cannot register entry twice (400 error)")
    
    def test_cannot_register_exit_without_entry(self):
        """Cannot register exit for visitor who hasn't entered"""
        visitor_id = self._create_test_visitor()
        
        # Try exit without entry
        response = requests.post(
            f"{BASE_URL}/api/visitors/{visitor_id}/exit",
            headers=self.guard_headers,
            json={"visitor_id": visitor_id, "notes": ""}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Cannot register exit without entry (400 error)")


class TestAdminVisitorAudit:
    """Test Admin audit capabilities for visitor events"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_get_all_visitors(self):
        """GET /api/visitors/all - Admin sees all visitor records"""
        response = requests.get(
            f"{BASE_URL}/api/visitors/all",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get all visitors failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Admin sees {len(data)} total visitor records")
        
        # Verify structure
        if len(data) > 0:
            visitor = data[0]
            assert "id" in visitor
            assert "full_name" in visitor
            assert "status" in visitor
            assert "created_by" in visitor
            assert "created_by_name" in visitor
            assert "created_at" in visitor
    
    def test_get_all_visitors_filter_by_status(self):
        """GET /api/visitors/all?status=pending - Filter by status"""
        response = requests.get(
            f"{BASE_URL}/api/visitors/all?status=pending",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for visitor in data:
            assert visitor["status"] == "pending", f"Expected 'pending', got '{visitor['status']}'"
        
        print(f"✓ Filtered to {len(data)} pending visitors")
    
    def test_audit_logs_contain_visitor_events(self):
        """GET /api/audit/logs?module=visitors - Audit logs for visitor events"""
        response = requests.get(
            f"{BASE_URL}/api/audit/logs?module=visitors",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get audit logs failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Found {len(data)} visitor-related audit events")
        
        # Verify structure
        if len(data) > 0:
            log = data[0]
            assert "event_type" in log
            assert "user_id" in log
            assert "module" in log
            assert log["module"] == "visitors"
            assert "details" in log
            assert "timestamp" in log
            
            # Check for visitor-specific details
            details = log.get("details", {})
            if "action" in details:
                print(f"  - Action: {details['action']}")
            if "visitor" in details:
                print(f"  - Visitor: {details['visitor']}")
            if "resident" in details:
                print(f"  - Resident: {details['resident']}")
            if "guard" in details:
                print(f"  - Guard: {details['guard']}")


class TestVisitorFlowEndToEnd:
    """End-to-end test of complete visitor flow"""
    
    def test_complete_visitor_flow(self):
        """Test: Resident creates → Guard enters → Guard exits → Admin audits"""
        unique_id = str(uuid.uuid4())[:8]
        today = datetime.now().strftime("%Y-%m-%d")
        visitor_name = f"TEST_E2E_Visitor_{unique_id}"
        
        # 1. Resident creates pre-registration
        resident_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": RESIDENT_EMAIL,
            "password": RESIDENT_PASSWORD
        })
        resident_token = resident_response.json()["access_token"]
        resident_headers = {"Authorization": f"Bearer {resident_token}", "Content-Type": "application/json"}
        
        create_response = requests.post(
            f"{BASE_URL}/api/visitors/pre-register",
            headers=resident_headers,
            json={
                "full_name": visitor_name,
                "national_id": f"E2E-{unique_id}",
                "vehicle_plate": f"E2E-{unique_id[:3].upper()}",
                "expected_date": today,
                "expected_time": "15:00",
                "visit_type": "friend",
                "notes": "End-to-end test visitor"
            }
        )
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        visitor_id = create_response.json()["id"]
        print(f"✓ Step 1: Resident created visitor '{visitor_name}' (ID: {visitor_id})")
        
        # 2. Guard sees visitor in pending list
        guard_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": GUARD_EMAIL,
            "password": GUARD_PASSWORD
        })
        guard_token = guard_response.json()["access_token"]
        guard_headers = {"Authorization": f"Bearer {guard_token}", "Content-Type": "application/json"}
        
        pending_response = requests.get(
            f"{BASE_URL}/api/visitors/pending",
            headers=guard_headers
        )
        assert pending_response.status_code == 200
        pending_visitors = pending_response.json()
        found_pending = any(v.get("id") == visitor_id for v in pending_visitors)
        assert found_pending, "Visitor not found in guard's pending list"
        print(f"✓ Step 2: Guard sees visitor in pending list")
        
        # 3. Guard registers entry
        entry_response = requests.post(
            f"{BASE_URL}/api/visitors/{visitor_id}/entry",
            headers=guard_headers,
            json={"visitor_id": visitor_id, "notes": "E2E entry"}
        )
        assert entry_response.status_code == 200, f"Entry failed: {entry_response.text}"
        entry_time = entry_response.json()["entry_at"]
        print(f"✓ Step 3: Guard registered entry at {entry_time}")
        
        # 4. Resident sees visitor status as 'entry_registered'
        my_visitors = requests.get(
            f"{BASE_URL}/api/visitors/my-visitors",
            headers=resident_headers
        ).json()
        visitor_status = next((v["status"] for v in my_visitors if v.get("id") == visitor_id), None)
        assert visitor_status == "entry_registered", f"Expected 'entry_registered', got '{visitor_status}'"
        print(f"✓ Step 4: Resident sees visitor status as 'entry_registered'")
        
        # 5. Guard registers exit
        exit_response = requests.post(
            f"{BASE_URL}/api/visitors/{visitor_id}/exit",
            headers=guard_headers,
            json={"visitor_id": visitor_id, "notes": "E2E exit"}
        )
        assert exit_response.status_code == 200, f"Exit failed: {exit_response.text}"
        exit_time = exit_response.json()["exit_at"]
        print(f"✓ Step 5: Guard registered exit at {exit_time}")
        
        # 6. Resident sees visitor status as 'exit_registered'
        my_visitors = requests.get(
            f"{BASE_URL}/api/visitors/my-visitors",
            headers=resident_headers
        ).json()
        visitor_status = next((v["status"] for v in my_visitors if v.get("id") == visitor_id), None)
        assert visitor_status == "exit_registered", f"Expected 'exit_registered', got '{visitor_status}'"
        print(f"✓ Step 6: Resident sees visitor status as 'exit_registered'")
        
        # 7. Admin can see visitor in all visitors
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        admin_token = admin_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        
        all_visitors = requests.get(
            f"{BASE_URL}/api/visitors/all",
            headers=admin_headers
        ).json()
        found_visitor = next((v for v in all_visitors if v.get("id") == visitor_id), None)
        assert found_visitor is not None, "Visitor not found in admin's all visitors"
        assert found_visitor["status"] == "exit_registered"
        assert found_visitor.get("entry_at") is not None
        assert found_visitor.get("exit_at") is not None
        assert found_visitor.get("entry_by_name") is not None
        assert found_visitor.get("exit_by_name") is not None
        print(f"✓ Step 7: Admin sees complete visitor record with entry/exit timestamps and guard names")
        
        # 8. Admin can see visitor events in audit logs
        audit_logs = requests.get(
            f"{BASE_URL}/api/audit/logs?module=visitors",
            headers=admin_headers
        ).json()
        
        visitor_events = [log for log in audit_logs if log.get("details", {}).get("visitor_id") == visitor_id or visitor_name in str(log.get("details", {}))]
        print(f"✓ Step 8: Admin found {len(visitor_events)} audit events for this visitor")
        
        print("\n✅ COMPLETE VISITOR FLOW E2E TEST PASSED!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
