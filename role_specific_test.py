#!/usr/bin/env python3
"""
GENTURIX Role-Specific Testing
Tests role-based authentication and access control
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class GenturixRolesTester:
    def __init__(self, base_url: str = "https://secure-condo-1.preview.emergentagent.com"):
        self.base_url = base_url.rstrip('/')
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # Test credentials from the review request
        self.credentials = {
            "admin": {"email": "admin@genturix.com", "password": "Admin123!"},
            "guarda": {"email": "guarda1@genturix.com", "password": "Guard123!"},
            "residente": {"email": "residente@genturix.com", "password": "Resi123!"}
        }

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    {details}")
        
        if success:
            self.tests_passed += 1
        else:
            self.failed_tests.append({"name": name, "details": details})

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                    expected_status: int = 200, token: str = None) -> tuple[bool, Dict]:
        """Make HTTP request and validate response"""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        headers = {}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, headers=headers)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, headers=headers)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}
            
            return success, response_data
            
        except Exception as e:
            return False, {"error": str(e)}

    def test_role_authentication(self):
        """Test authentication for all roles"""
        print("\n🔐 Testing Role-Based Authentication...")
        
        tokens = {}
        
        for role, creds in self.credentials.items():
            success, data = self.make_request('POST', '/auth/login', creds, token=None)
            
            if success and 'access_token' in data:
                tokens[role] = data['access_token']
                user_roles = data.get('user', {}).get('roles', [])
                self.log_test(f"{role.capitalize()} login", success,
                             f"User: {data.get('user', {}).get('full_name', 'Unknown')}, Roles: {user_roles}")
            else:
                self.log_test(f"{role.capitalize()} login", success, f"Error: {data}")
        
        return tokens

    def test_resident_panic_functionality(self, token: str):
        """Test resident panic button functionality"""
        print("\n🚨 Testing Resident Panic Functionality...")
        
        # Test triggering different types of panic
        panic_types = ["emergencia_medica", "actividad_sospechosa", "emergencia_general"]
        
        for panic_type in panic_types:
            panic_data = {
                "panic_type": panic_type,
                "location": f"Residencia Test - {panic_type}",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "description": f"Test {panic_type} from resident"
            }
            
            success, data = self.make_request('POST', '/security/panic', panic_data, token=token)
            self.log_test(f"Trigger {panic_type}", success,
                         f"Event ID: {data.get('event_id', 'Unknown')}, Guards notified: {data.get('notified_guards', 0)}" if success else f"Error: {data}")

    def test_guard_emergency_response(self, token: str):
        """Test guard emergency response functionality"""
        print("\n👮 Testing Guard Emergency Response...")
        
        # Test getting panic events (guard should see active emergencies)
        success, data = self.make_request('GET', '/security/panic-events', token=token)
        events = data if isinstance(data, list) else []
        active_events = [e for e in events if e.get('status') == 'active']
        
        self.log_test("View active emergencies", success,
                     f"Total events: {len(events)}, Active: {len(active_events)}" if success else f"Error: {data}")
        
        # Test resolving a panic event (if any active)
        if active_events:
            event_id = active_events[0]['id']
            success, data = self.make_request('PUT', f'/security/panic/{event_id}/resolve', token=token)
            self.log_test("Resolve emergency", success,
                         f"Resolved event: {event_id}" if success else f"Error: {data}")

    def test_admin_dashboard_access(self, token: str):
        """Test admin dashboard functionality"""
        print("\n👑 Testing Admin Dashboard Access...")
        
        # Test dashboard stats
        success, data = self.make_request('GET', '/dashboard/stats', token=token)
        self.log_test("Dashboard stats access", success,
                     f"Users: {data.get('total_users', 0)}, Guards: {data.get('active_guards', 0)}" if success else f"Error: {data}")
        
        # Test user management (admin only)
        success, data = self.make_request('GET', '/users', token=token)
        self.log_test("User management access", success,
                     f"Users: {len(data) if isinstance(data, list) else 0}" if success else f"Error: {data}")
        
        # Test audit logs (admin only)
        success, data = self.make_request('GET', '/audit/logs', token=token)
        self.log_test("Audit logs access", success,
                     f"Logs: {len(data) if isinstance(data, list) else 0}" if success else f"Error: {data}")

    def test_payments_pricing_model(self, token: str):
        """Test GENTURIX $1/user pricing model"""
        print("\n💰 Testing GENTURIX Pricing Model...")
        
        # Test pricing info
        success, data = self.make_request('GET', '/payments/pricing', token=token)
        self.log_test("Get pricing model", success,
                     f"Price per user: ${data.get('price_per_user', 0)}, Model: {data.get('model', 'Unknown')}" if success else f"Error: {data}")
        
        # Test price calculation
        calc_data = {"user_count": 10}
        success, data = self.make_request('POST', '/payments/calculate', calc_data, token=token)
        self.log_test("Price calculation", success,
                     f"10 users = ${data.get('total', 0)}" if success else f"Error: {data}")

    def test_role_based_access_control(self, tokens: Dict[str, str]):
        """Test role-based access control"""
        print("\n🛡️ Testing Role-Based Access Control...")
        
        # Test resident trying to access admin endpoints (should fail)
        if 'residente' in tokens:
            success, data = self.make_request('GET', '/users', expected_status=403, token=tokens['residente'])
            self.log_test("Resident blocked from user management", success,
                         "Correctly blocked access" if success else f"Unexpected access granted: {data}")
        
        # Test guard accessing security endpoints (should work)
        if 'guarda' in tokens:
            success, data = self.make_request('GET', '/security/panic-events', token=tokens['guarda'])
            self.log_test("Guard access to security module", success,
                         f"Events accessible: {len(data) if isinstance(data, list) else 0}" if success else f"Error: {data}")

    def run_all_tests(self):
        """Run all role-specific tests"""
        print("🚀 Starting GENTURIX Role-Specific Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test authentication for all roles
        tokens = self.test_role_authentication()
        
        # Test role-specific functionality
        if 'residente' in tokens:
            self.test_resident_panic_functionality(tokens['residente'])
        
        if 'guarda' in tokens:
            self.test_guard_emergency_response(tokens['guarda'])
        
        if 'admin' in tokens:
            self.test_admin_dashboard_access(tokens['admin'])
            self.test_payments_pricing_model(tokens['admin'])
        
        # Test access control
        self.test_role_based_access_control(tokens)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 ROLE-SPECIFIC TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {len(self.failed_tests)}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"  - {test['name']}: {test['details']}")
        
        return len(self.failed_tests) == 0

def main():
    """Main test execution"""
    tester = GenturixRolesTester()
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())