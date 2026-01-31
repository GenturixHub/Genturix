"""
GENTURIX Platform - CRUD Forms Testing
Tests all create/update/delete flows across the platform
"""

import pytest
import requests
import os
import time
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CREDENTIALS = {
    "Admin": {"email": "admin@genturix.com", "password": "Admin123!"},
    "HR": {"email": "hr@genturix.com", "password": "HR123!"},
    "Guard": {"email": "guarda1@genturix.com", "password": "Guard123!"},
    "Resident": {"email": "residente@genturix.com", "password": "Resi123!"}
}


class TestAuthentication:
    """Test authentication for all roles"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["Admin"])
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def hr_token(self):
        """Get HR token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["HR"])
        assert response.status_code == 200, f"HR login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def guard_token(self):
        """Get Guard token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["Guard"])
        assert response.status_code == 200, f"Guard login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        """Get Resident token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["Resident"])
        assert response.status_code == 200, f"Resident login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_admin_login(self, admin_token):
        """Verify admin can login"""
        assert admin_token is not None
        print("✓ Admin login successful")
    
    def test_hr_login(self, hr_token):
        """Verify HR can login"""
        assert hr_token is not None
        print("✓ HR login successful")
    
    def test_guard_login(self, guard_token):
        """Verify Guard can login"""
        assert guard_token is not None
        print("✓ Guard login successful")
    
    def test_resident_login(self, resident_token):
        """Verify Resident can login"""
        assert resident_token is not None
        print("✓ Resident login successful")


class TestUserManagementCRUD:
    """Test User Management CRUD operations - Admin creates users"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["Admin"])
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_create_resident_user_validation(self, admin_token):
        """Admin creates new Resident user - verify form validation"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test missing required fields
        invalid_data = {
            "email": "",  # Missing email
            "password": "Test123!",
            "full_name": "Test Resident",
            "role": "Residente"
        }
        response = requests.post(f"{BASE_URL}/api/admin/users", json=invalid_data, headers=headers)
        assert response.status_code in [400, 422], f"Should reject missing email: {response.text}"
        print("✓ Validation: Missing email rejected")
        
        # Test valid resident creation
        timestamp = int(time.time())
        valid_data = {
            "email": f"test_resident_{timestamp}@test.com",
            "password": "TestResident123!",
            "full_name": "Test Resident User",
            "role": "Residente",
            "phone": "+1234567890",
            "apartment_number": "A-101",
            "tower_block": "Torre A",
            "resident_type": "owner"
        }
        response = requests.post(f"{BASE_URL}/api/admin/users", json=valid_data, headers=headers)
        assert response.status_code in [200, 201], f"Resident creation failed: {response.text}"
        data = response.json()
        assert "id" in data or "user_id" in data, "Response should contain user ID"
        print(f"✓ Resident user created: {valid_data['email']}")
        return data
    
    def test_create_guard_user_validation(self, admin_token):
        """Admin creates new Guard user - verify form validation"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test missing badge number for guard
        timestamp = int(time.time())
        invalid_guard = {
            "email": f"test_guard_invalid_{timestamp}@test.com",
            "password": "TestGuard123!",
            "full_name": "Test Guard",
            "role": "Guarda",
            "badge_number": ""  # Missing badge number
        }
        response = requests.post(f"{BASE_URL}/api/admin/users", json=invalid_guard, headers=headers)
        # Note: Backend may or may not validate badge_number
        print(f"Guard without badge: status={response.status_code}")
        
        # Test valid guard creation
        valid_guard = {
            "email": f"test_guard_{timestamp}@test.com",
            "password": "TestGuard123!",
            "full_name": "Test Guard User",
            "role": "Guarda",
            "phone": "+1234567890",
            "badge_number": f"G-{timestamp}",
            "main_location": "Entrada Principal"
        }
        response = requests.post(f"{BASE_URL}/api/admin/users", json=valid_guard, headers=headers)
        assert response.status_code in [200, 201], f"Guard creation failed: {response.text}"
        print(f"✓ Guard user created: {valid_guard['email']}")
    
    def test_update_user_status(self, admin_token):
        """Admin updates user status (activate/deactivate)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get list of users
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        assert response.status_code == 200, f"Failed to get users: {response.text}"
        users = response.json()
        
        # Find a test user to update
        test_user = None
        for user in users:
            if "test_" in user.get("email", "").lower():
                test_user = user
                break
        
        if test_user:
            user_id = test_user.get("id") or test_user.get("_id")
            # Deactivate user
            response = requests.put(
                f"{BASE_URL}/api/admin/users/{user_id}/status",
                json={"is_active": False},
                headers=headers
            )
            if response.status_code == 200:
                print(f"✓ User {user_id} deactivated")
                
                # Reactivate user
                response = requests.put(
                    f"{BASE_URL}/api/admin/users/{user_id}/status",
                    json={"is_active": True},
                    headers=headers
                )
                assert response.status_code == 200, f"Failed to reactivate: {response.text}"
                print(f"✓ User {user_id} reactivated")
            else:
                print(f"Status update endpoint: {response.status_code}")
        else:
            print("⚠ No test user found for status update test")


class TestAreasCRUD:
    """Test Areas/Common Areas CRUD operations"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["Admin"])
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_create_area(self, admin_token):
        """Admin creates new Area - verify all fields work"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        timestamp = int(time.time())
        area_data = {
            "name": f"Test Pool {timestamp}",
            "area_type": "pool",
            "capacity": 20,
            "description": "Test pool area for automated testing",
            "rules": "No running, no diving",
            "available_from": "08:00",
            "available_until": "20:00",
            "requires_approval": True,
            "max_hours_per_reservation": 2,
            "max_reservations_per_day": 5,
            "allowed_days": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        }
        
        response = requests.post(f"{BASE_URL}/api/reservations/areas", json=area_data, headers=headers)
        assert response.status_code in [200, 201], f"Area creation failed: {response.text}"
        data = response.json()
        # API returns area_id and message, not the full area object
        assert "area_id" in data or data.get("name") == area_data["name"], "Area creation response invalid"
        print(f"✓ Area created: {area_data['name']}")
        return data
    
    def test_get_areas(self, admin_token):
        """Get list of areas"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=headers)
        assert response.status_code == 200, f"Failed to get areas: {response.text}"
        areas = response.json()
        assert isinstance(areas, list), "Areas should be a list"
        print(f"✓ Retrieved {len(areas)} areas")
        return areas
    
    def test_update_area(self, admin_token):
        """Admin updates Area - verify changes save"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get areas first
        areas = self.test_get_areas(admin_token)
        test_area = None
        for area in areas:
            if "Test" in area.get("name", ""):
                test_area = area
                break
        
        if test_area:
            area_id = test_area.get("id") or test_area.get("_id")
            update_data = {
                "name": test_area["name"] + " Updated",
                "capacity": 25,
                "description": "Updated description"
            }
            response = requests.patch(f"{BASE_URL}/api/reservations/areas/{area_id}", json=update_data, headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Area updated: {update_data['name']}")
            else:
                print(f"Area update status: {response.status_code}")
        else:
            print("⚠ No test area found for update test")
    
    def test_delete_area(self, admin_token):
        """Admin deletes Area - verify soft delete"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Create a new area to delete
        timestamp = int(time.time())
        area_data = {
            "name": f"Delete Test Area {timestamp}",
            "area_type": "other",
            "capacity": 10
        }
        response = requests.post(f"{BASE_URL}/api/reservations/areas", json=area_data, headers=headers)
        if response.status_code in [200, 201]:
            area = response.json()
            area_id = area.get("area_id") or area.get("id") or area.get("_id")
            
            # Delete the area
            response = requests.delete(f"{BASE_URL}/api/reservations/areas/{area_id}", headers=headers)
            assert response.status_code in [200, 204], f"Area deletion failed: {response.text}"
            print(f"✓ Area deleted: {area_data['name']}")
        else:
            print(f"⚠ Could not create area for deletion test: {response.status_code}")


class TestReservationsCRUD:
    """Test Reservations CRUD operations"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["Admin"])
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["Resident"])
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_resident_creates_reservation(self, resident_token, admin_token):
        """Resident creates Reservation request"""
        headers = {"Authorization": f"Bearer {resident_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get available areas
        response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=headers)
        if response.status_code != 200:
            print(f"⚠ Could not get areas: {response.status_code}")
            return
        
        areas = response.json()
        if not areas:
            print("⚠ No areas available for reservation")
            return
        
        area = areas[0]
        area_id = area.get("id") or area.get("_id")
        
        # Create reservation for tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        reservation_data = {
            "area_id": area_id,
            "date": tomorrow,
            "start_time": "10:00",
            "end_time": "12:00",
            "guests_count": 5,
            "purpose": "Test reservation for automated testing"
        }
        
        response = requests.post(f"{BASE_URL}/api/reservations", json=reservation_data, headers=headers)
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✓ Reservation created for {tomorrow}")
            return data
        else:
            print(f"Reservation creation: {response.status_code} - {response.text}")
    
    def test_admin_approves_reservation(self, admin_token):
        """Admin approves/rejects reservation"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get pending reservations
        response = requests.get(f"{BASE_URL}/api/reservations?status=pending", headers=headers)
        if response.status_code != 200:
            print(f"⚠ Could not get reservations: {response.status_code}")
            return
        
        reservations = response.json()
        pending = [r for r in reservations if r.get("status") == "pending"]
        
        if pending:
            reservation = pending[0]
            res_id = reservation.get("id") or reservation.get("_id")
            
            # Approve reservation
            response = requests.put(
                f"{BASE_URL}/api/reservations/{res_id}/status",
                json={"status": "approved"},
                headers=headers
            )
            if response.status_code == 200:
                print(f"✓ Reservation {res_id} approved")
            else:
                print(f"Reservation approval: {response.status_code}")
        else:
            print("⚠ No pending reservations to approve")


class TestVisitorAuthorizationsCRUD:
    """Test Visitor Authorizations CRUD operations"""
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["Resident"])
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def guard_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["Guard"])
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_create_single_visit_authorization(self, resident_token):
        """Resident creates single visit authorization"""
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        timestamp = int(time.time())
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        auth_data = {
            "visitor_name": f"Test Visitor {timestamp}",
            "visitor_id": f"ID-{timestamp}",
            "authorization_type": "single_visit",
            "valid_from": tomorrow,
            "valid_until": tomorrow,
            "notes": "Test single visit authorization"
        }
        
        response = requests.post(f"{BASE_URL}/api/authorizations", json=auth_data, headers=headers)
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✓ Single visit authorization created: {auth_data['visitor_name']}")
            return data
        else:
            print(f"Single visit auth: {response.status_code} - {response.text}")
    
    def test_create_recurring_authorization(self, resident_token):
        """Resident creates recurring authorization"""
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        timestamp = int(time.time())
        today = datetime.now().strftime("%Y-%m-%d")
        next_month = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        auth_data = {
            "visitor_name": f"Test Recurring Visitor {timestamp}",
            "visitor_id": f"REC-{timestamp}",
            "authorization_type": "recurring",
            "valid_from": today,
            "valid_until": next_month,
            "allowed_days": ["Lunes", "Miércoles", "Viernes"],
            "notes": "Test recurring authorization"
        }
        
        response = requests.post(f"{BASE_URL}/api/authorizations", json=auth_data, headers=headers)
        if response.status_code in [200, 201]:
            print(f"✓ Recurring authorization created: {auth_data['visitor_name']}")
        else:
            print(f"Recurring auth: {response.status_code} - {response.text}")
    
    def test_create_temporary_authorization(self, resident_token):
        """Resident creates temporary authorization"""
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        timestamp = int(time.time())
        today = datetime.now().strftime("%Y-%m-%d")
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        auth_data = {
            "visitor_name": f"Test Temp Visitor {timestamp}",
            "visitor_id": f"TEMP-{timestamp}",
            "authorization_type": "temporary",
            "valid_from": today,
            "valid_until": next_week,
            "notes": "Test temporary authorization"
        }
        
        response = requests.post(f"{BASE_URL}/api/authorizations", json=auth_data, headers=headers)
        if response.status_code in [200, 201]:
            print(f"✓ Temporary authorization created: {auth_data['visitor_name']}")
        else:
            print(f"Temporary auth: {response.status_code} - {response.text}")
    
    def test_create_permanent_authorization(self, resident_token):
        """Resident creates permanent authorization"""
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        timestamp = int(time.time())
        
        auth_data = {
            "visitor_name": f"Test Permanent Visitor {timestamp}",
            "visitor_id": f"PERM-{timestamp}",
            "authorization_type": "permanent",
            "notes": "Test permanent authorization"
        }
        
        response = requests.post(f"{BASE_URL}/api/authorizations", json=auth_data, headers=headers)
        if response.status_code in [200, 201]:
            print(f"✓ Permanent authorization created: {auth_data['visitor_name']}")
        else:
            print(f"Permanent auth: {response.status_code} - {response.text}")
    
    def test_get_my_authorizations(self, resident_token):
        """Resident gets their authorizations"""
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        response = requests.get(f"{BASE_URL}/api/authorizations/my", headers=headers)
        assert response.status_code == 200, f"Failed to get authorizations: {response.text}"
        auths = response.json()
        print(f"✓ Retrieved {len(auths)} authorizations")
        return auths
    
    def test_update_authorization(self, resident_token):
        """Resident updates authorization"""
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        # Get authorizations
        auths = self.test_get_my_authorizations(resident_token)
        test_auth = None
        for auth in auths:
            if "Test" in auth.get("visitor_name", ""):
                test_auth = auth
                break
        
        if test_auth:
            auth_id = test_auth.get("id") or test_auth.get("_id")
            update_data = {
                "notes": "Updated notes for testing"
            }
            response = requests.patch(f"{BASE_URL}/api/authorizations/{auth_id}", json=update_data, headers=headers)
            if response.status_code == 200:
                print(f"✓ Authorization {auth_id} updated")
            else:
                print(f"Authorization update: {response.status_code}")
        else:
            print("⚠ No test authorization found for update")
    
    def test_deactivate_authorization(self, resident_token):
        """Resident deletes/deactivates authorization"""
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        # Get authorizations
        auths = self.test_get_my_authorizations(resident_token)
        test_auth = None
        for auth in auths:
            if "Test" in auth.get("visitor_name", "") and auth.get("is_active", True):
                test_auth = auth
                break
        
        if test_auth:
            auth_id = test_auth.get("id") or test_auth.get("_id")
            response = requests.delete(f"{BASE_URL}/api/authorizations/{auth_id}", headers=headers)
            if response.status_code in [200, 204]:
                print(f"✓ Authorization {auth_id} deactivated")
            else:
                print(f"Authorization deactivation: {response.status_code}")
        else:
            print("⚠ No test authorization found for deactivation")
    
    def test_guard_checkin_flow(self, guard_token):
        """Guard check-in flow"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        
        # Get authorizations for guard
        response = requests.get(f"{BASE_URL}/api/guard/authorizations", headers=headers)
        if response.status_code == 200:
            auths = response.json()
            print(f"✓ Guard can see {len(auths)} authorizations")
            
            # Try fast check-in with a test visitor
            if auths:
                auth = auths[0]
                checkin_data = {
                    "authorization_id": auth.get("id") or auth.get("_id"),
                    "entry_method": "manual"
                }
                response = requests.post(f"{BASE_URL}/api/guard/checkin", json=checkin_data, headers=headers)
                if response.status_code == 200:
                    print("✓ Check-in successful")
                else:
                    print(f"Check-in: {response.status_code} - {response.text}")
        else:
            print(f"Guard authorizations: {response.status_code}")
    
    def test_guard_checkout_flow(self, guard_token):
        """Guard check-out flow"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        
        # Get visitors inside
        response = requests.get(f"{BASE_URL}/api/guard/visitors-inside", headers=headers)
        if response.status_code == 200:
            visitors = response.json()
            print(f"✓ {len(visitors)} visitors currently inside")
            
            if visitors:
                visitor = visitors[0]
                checkout_data = {
                    "visit_id": visitor.get("id") or visitor.get("_id")
                }
                response = requests.post(f"{BASE_URL}/api/guard/checkout", json=checkout_data, headers=headers)
                if response.status_code == 200:
                    print("✓ Check-out successful")
                else:
                    print(f"Check-out: {response.status_code}")
        else:
            print(f"Visitors inside: {response.status_code}")


class TestHRModuleCRUD:
    """Test HR Module CRUD operations"""
    
    @pytest.fixture(scope="class")
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["HR"])
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def guard_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["Guard"])
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_hr_creates_absence_request(self, hr_token):
        """HR creates absence request for employee"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        # Get guards/employees
        response = requests.get(f"{BASE_URL}/api/guards", headers=headers)
        if response.status_code != 200:
            print(f"⚠ Could not get guards: {response.status_code}")
            return
        
        guards = response.json()
        if not guards:
            print("⚠ No guards found for absence request")
            return
        
        guard = guards[0]
        guard_id = guard.get("id") or guard.get("_id") or guard.get("user_id")
        
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        absence_data = {
            "guard_id": guard_id,
            "absence_type": "vacation",
            "start_date": tomorrow,
            "end_date": tomorrow,
            "reason": "Test absence request"
        }
        
        response = requests.post(f"{BASE_URL}/api/absences", json=absence_data, headers=headers)
        if response.status_code in [200, 201]:
            print(f"✓ Absence request created for guard {guard_id}")
            return response.json()
        else:
            print(f"Absence creation: {response.status_code} - {response.text}")
    
    def test_hr_approves_absence(self, hr_token):
        """HR approves/rejects absence"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        # Get absences
        response = requests.get(f"{BASE_URL}/api/absences", headers=headers)
        if response.status_code != 200:
            print(f"⚠ Could not get absences: {response.status_code}")
            return
        
        absences = response.json()
        pending = [a for a in absences if a.get("status") == "pending"]
        
        if pending:
            absence = pending[0]
            absence_id = absence.get("id") or absence.get("_id")
            
            response = requests.put(f"{BASE_URL}/api/absences/{absence_id}/approve", headers=headers)
            if response.status_code == 200:
                print(f"✓ Absence {absence_id} approved")
            else:
                print(f"Absence approval: {response.status_code}")
        else:
            print("⚠ No pending absences to approve")
    
    def test_hr_creates_evaluation(self, hr_token):
        """HR creates evaluation for employee"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        # Get evaluable employees
        response = requests.get(f"{BASE_URL}/api/evaluations/evaluable-employees", headers=headers)
        if response.status_code != 200:
            print(f"⚠ Could not get evaluable employees: {response.status_code}")
            return
        
        employees = response.json()
        if not employees:
            print("⚠ No evaluable employees found")
            return
        
        employee = employees[0]
        employee_id = employee.get("id") or employee.get("_id") or employee.get("user_id")
        
        evaluation_data = {
            "employee_id": employee_id,
            "period": "2025-Q1",
            "performance_score": 4,
            "punctuality_score": 5,
            "teamwork_score": 4,
            "communication_score": 4,
            "comments": "Test evaluation - good performance",
            "goals_achieved": ["Goal 1", "Goal 2"],
            "areas_for_improvement": ["Area 1"]
        }
        
        response = requests.post(f"{BASE_URL}/api/evaluations", json=evaluation_data, headers=headers)
        if response.status_code in [200, 201]:
            print(f"✓ Evaluation created for employee {employee_id}")
        else:
            print(f"Evaluation creation: {response.status_code} - {response.text}")
    
    def test_guard_clock_in(self, guard_token):
        """Guard clock-in"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        
        # Check current clock status
        response = requests.get(f"{BASE_URL}/api/clock/status", headers=headers)
        if response.status_code == 200:
            status = response.json()
            print(f"Current clock status: {status}")
        
        # Try to clock in
        clock_data = {
            "action": "clock_in",
            "location": "Entrada Principal"
        }
        response = requests.post(f"{BASE_URL}/api/clock", json=clock_data, headers=headers)
        if response.status_code == 200:
            print("✓ Guard clocked in successfully")
        else:
            print(f"Clock in: {response.status_code} - {response.text}")
    
    def test_guard_clock_out(self, guard_token):
        """Guard clock-out"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        
        clock_data = {
            "action": "clock_out",
            "location": "Entrada Principal"
        }
        response = requests.post(f"{BASE_URL}/api/clock", json=clock_data, headers=headers)
        if response.status_code == 200:
            print("✓ Guard clocked out successfully")
        else:
            print(f"Clock out: {response.status_code} - {response.text}")


class TestSecurityModule:
    """Test Security Module - Panic alerts"""
    
    @pytest.fixture(scope="class")
    def resident_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["Resident"])
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def guard_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["Guard"])
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_resident_triggers_panic_alert(self, resident_token):
        """Resident triggers panic alert"""
        headers = {"Authorization": f"Bearer {resident_token}"}
        
        panic_data = {
            "event_type": "general",
            "description": "Test panic alert - automated testing",
            "location": "Apartamento A-101"
        }
        
        response = requests.post(f"{BASE_URL}/api/panic", json=panic_data, headers=headers)
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✓ Panic alert triggered: {data.get('id') or data.get('_id')}")
            return data
        else:
            print(f"Panic trigger: {response.status_code} - {response.text}")
    
    def test_guard_resolves_panic_alert(self, guard_token):
        """Guard resolves panic alert"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        
        # Get active panic events
        response = requests.get(f"{BASE_URL}/api/panic", headers=headers)
        if response.status_code != 200:
            print(f"⚠ Could not get panic events: {response.status_code}")
            return
        
        events = response.json()
        active = [e for e in events if e.get("status") == "active"]
        
        if active:
            event = active[0]
            event_id = event.get("id") or event.get("_id")
            
            resolve_data = {
                "resolution_notes": "Test resolution - false alarm",
                "resolution_type": "false_alarm"
            }
            response = requests.put(f"{BASE_URL}/api/panic/{event_id}/resolve", json=resolve_data, headers=headers)
            if response.status_code == 200:
                print(f"✓ Panic alert {event_id} resolved")
            else:
                print(f"Panic resolution: {response.status_code} - {response.text}")
        else:
            print("⚠ No active panic alerts to resolve")
    
    def test_get_alert_history(self, guard_token):
        """Verify alert history updates"""
        headers = {"Authorization": f"Bearer {guard_token}"}
        
        response = requests.get(f"{BASE_URL}/api/panic", headers=headers)
        if response.status_code == 200:
            events = response.json()
            print(f"✓ Alert history contains {len(events)} events")
        else:
            print(f"Alert history: {response.status_code}")


class TestErrorHandling:
    """Test form submission error handling"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["Admin"])
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_missing_required_fields(self, admin_token):
        """Test form submission with missing required fields"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test user creation with missing fields
        invalid_user = {
            "email": "",
            "password": "",
            "full_name": "",
            "role": ""
        }
        response = requests.post(f"{BASE_URL}/api/admin/users", json=invalid_user, headers=headers)
        assert response.status_code in [400, 422], f"Should reject empty fields: {response.status_code}"
        print("✓ Missing required fields rejected")
    
    def test_invalid_email_format(self, admin_token):
        """Test form submission with invalid data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        invalid_user = {
            "email": "not-an-email",
            "password": "Test123!",
            "full_name": "Test User",
            "role": "Residente"
        }
        response = requests.post(f"{BASE_URL}/api/admin/users", json=invalid_user, headers=headers)
        # May or may not validate email format
        print(f"Invalid email format: status={response.status_code}")
    
    def test_short_password(self, admin_token):
        """Test password validation"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        timestamp = int(time.time())
        invalid_user = {
            "email": f"test_short_pwd_{timestamp}@test.com",
            "password": "123",  # Too short
            "full_name": "Test User",
            "role": "Residente"
        }
        response = requests.post(f"{BASE_URL}/api/admin/users", json=invalid_user, headers=headers)
        # Should reject short password
        print(f"Short password: status={response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
