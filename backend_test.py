#!/usr/bin/env python3
"""
GENTURIX Enterprise Platform - Backend API Testing
Tests all backend endpoints for functionality and integration
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class GenturixAPITester:
    def __init__(self, base_url: str = "https://fixphase.preview.emergentagent.com"):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.refresh_token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

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
                    expected_status: int = 200, use_auth: bool = True) -> tuple[bool, Dict]:
        """Make HTTP request and validate response"""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        headers = {}
        
        if use_auth and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, headers=headers)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, headers=headers)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=headers)
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

    def test_health_check(self):
        """Test basic health endpoints"""
        print("\n🔍 Testing Health Endpoints...")
        
        # Test root endpoint
        success, data = self.make_request('GET', '/', use_auth=False)
        self.log_test("Root API endpoint", success, 
                     f"Response: {data.get('message', 'No message')}" if success else f"Error: {data}")
        
        # Test health endpoint
        success, data = self.make_request('GET', '/health', use_auth=False)
        self.log_test("Health check endpoint", success,
                     f"Status: {data.get('status', 'Unknown')}" if success else f"Error: {data}")

    def test_demo_data_seeding(self):
        """Test demo data seeding"""
        print("\n🌱 Testing Demo Data Seeding...")
        
        success, data = self.make_request('POST', '/seed-demo-data', use_auth=False)
        # Accept both 200 (new data) and 409 (already exists) as success
        if not success and data.get('status_code') != 409:
            success = False
        else:
            success = True
            
        self.log_test("Demo data seeding", success,
                     f"Message: {data.get('message', 'Seeded successfully')}" if success else f"Error: {data}")

    def test_authentication(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication...")
        
        # Test login with demo credentials
        login_data = {
            "email": "admin@genturix.com",
            "password": "Admin123!"
        }
        
        success, data = self.make_request('POST', '/auth/login', login_data, use_auth=False)
        if success and 'access_token' in data:
            self.token = data['access_token']
            self.refresh_token = data['refresh_token']
            self.user_data = data['user']
            self.session.headers.update({'Authorization': f'Bearer {self.token}'})
        
        self.log_test("Admin login", success,
                     f"User: {data.get('user', {}).get('full_name', 'Unknown')}" if success else f"Error: {data}")
        
        # Test invalid login
        invalid_login = {
            "email": "invalid@test.com",
            "password": "wrongpassword"
        }
        success, data = self.make_request('POST', '/auth/login', invalid_login, expected_status=401, use_auth=False)
        self.log_test("Invalid login rejection", success,
                     "Correctly rejected invalid credentials" if success else f"Error: {data}")
        
        # Test get current user
        if self.token:
            success, data = self.make_request('GET', '/auth/me')
            self.log_test("Get current user", success,
                         f"User ID: {data.get('id', 'Unknown')}" if success else f"Error: {data}")

    def test_dashboard_endpoints(self):
        """Test dashboard endpoints"""
        print("\n📊 Testing Dashboard Endpoints...")
        
        # Test dashboard stats
        success, data = self.make_request('GET', '/dashboard/stats')
        self.log_test("Dashboard stats", success,
                     f"Users: {data.get('total_users', 0)}, Guards: {data.get('active_guards', 0)}" if success else f"Error: {data}")
        
        # Test recent activity
        success, data = self.make_request('GET', '/dashboard/recent-activity')
        self.log_test("Recent activity", success,
                     f"Activities: {len(data) if isinstance(data, list) else 0}" if success else f"Error: {data}")

    def test_security_module(self):
        """Test security module endpoints"""
        print("\n🛡️ Testing Security Module...")
        
        # Test security stats
        success, data = self.make_request('GET', '/security/dashboard-stats')
        self.log_test("Security stats", success,
                     f"Active alerts: {data.get('active_alerts', 0)}" if success else f"Error: {data}")
        
        # Test panic events
        success, data = self.make_request('GET', '/security/panic-events')
        self.log_test("Get panic events", success,
                     f"Events: {len(data) if isinstance(data, list) else 0}" if success else f"Error: {data}")
        
        # Test access logs
        success, data = self.make_request('GET', '/security/access-logs')
        self.log_test("Get access logs", success,
                     f"Logs: {len(data) if isinstance(data, list) else 0}" if success else f"Error: {data}")
        
        # Test trigger panic (create)
        panic_data = {
            "panic_type": "emergencia_general",
            "location": "Test Location - API Test",
            "description": "Automated test panic event"
        }
        success, data = self.make_request('POST', '/security/panic', panic_data)
        panic_event_id = data.get('event_id') if success else None
        self.log_test("Trigger panic event", success,
                     f"Event ID: {panic_event_id}" if success else f"Error: {data}")

    def test_hr_module(self):
        """Test HR module endpoints"""
        print("\n👥 Testing HR Module...")
        
        # Test get guards
        success, data = self.make_request('GET', '/hr/guards')
        self.log_test("Get guards", success,
                     f"Guards: {len(data) if isinstance(data, list) else 0}" if success else f"Error: {data}")
        
        # Test get shifts
        success, data = self.make_request('GET', '/hr/shifts')
        self.log_test("Get shifts", success,
                     f"Shifts: {len(data) if isinstance(data, list) else 0}" if success else f"Error: {data}")
        
        # Test payroll
        success, data = self.make_request('GET', '/hr/payroll')
        self.log_test("Get payroll", success,
                     f"Payroll entries: {len(data) if isinstance(data, list) else 0}" if success else f"Error: {data}")

    def test_school_module(self):
        """Test school module endpoints"""
        print("\n🎓 Testing School Module...")
        
        # Test get courses
        success, data = self.make_request('GET', '/school/courses')
        courses = data if isinstance(data, list) else []
        self.log_test("Get courses", success,
                     f"Courses: {len(courses)}" if success else f"Error: {data}")
        
        # Test get enrollments
        success, data = self.make_request('GET', '/school/enrollments')
        self.log_test("Get enrollments", success,
                     f"Enrollments: {len(data) if isinstance(data, list) else 0}" if success else f"Error: {data}")
        
        # Test get certificates
        success, data = self.make_request('GET', '/school/certificates')
        self.log_test("Get certificates", success,
                     f"Certificates: {len(data) if isinstance(data, list) else 0}" if success else f"Error: {data}")
        
        # Test enrollment (if courses exist)
        if courses and len(courses) > 0:
            enrollment_data = {
                "course_id": courses[0]['id'],
                "student_id": self.user_data['id'] if self.user_data else "test-student-id"
            }
            success, data = self.make_request('POST', '/school/enroll', enrollment_data)
            # Accept both success and "already enrolled" error
            if not success and "already enrolled" in str(data).lower():
                success = True
                data = {"message": "Already enrolled (expected)"}
            self.log_test("Course enrollment", success,
                         f"Enrollment: {data.get('message', 'Success')}" if success else f"Error: {data}")

    def test_payments_module(self):
        """Test payments module endpoints"""
        print("\n💳 Testing Payments Module...")
        
        # Test get pricing info
        success, data = self.make_request('GET', '/payments/pricing')
        self.log_test("Get pricing info", success,
                     f"Price per user: ${data.get('price_per_user', 0)}" if success else f"Error: {data}")
        
        # Test payment history
        success, data = self.make_request('GET', '/payments/history')
        self.log_test("Get payment history", success,
                     f"Transactions: {len(data) if isinstance(data, list) else 0}" if success else f"Error: {data}")
        
        # Note: Not testing actual Stripe checkout as it requires real Stripe setup

    def test_audit_module(self):
        """Test audit module endpoints"""
        print("\n📋 Testing Audit Module...")
        
        # Test get audit logs
        success, data = self.make_request('GET', '/audit/logs')
        self.log_test("Get audit logs", success,
                     f"Logs: {len(data) if isinstance(data, list) else 0}" if success else f"Error: {data}")
        
        # Test audit stats
        success, data = self.make_request('GET', '/audit/stats')
        self.log_test("Get audit stats", success,
                     f"Total events: {data.get('total_events', 0)}" if success else f"Error: {data}")

    def test_user_management(self):
        """Test user management endpoints (admin only)"""
        print("\n👤 Testing User Management...")
        
        # Test get users
        success, data = self.make_request('GET', '/users')
        self.log_test("Get users", success,
                     f"Users: {len(data) if isinstance(data, list) else 0}" if success else f"Error: {data}")

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting GENTURIX Backend API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Run test suites in order
        self.test_health_check()
        self.test_demo_data_seeding()
        self.test_authentication()
        
        if self.token:  # Only run authenticated tests if login succeeded
            self.test_dashboard_endpoints()
            self.test_security_module()
            self.test_hr_module()
            self.test_school_module()
            self.test_payments_module()
            self.test_audit_module()
            self.test_user_management()
        else:
            print("\n❌ Skipping authenticated tests - login failed")
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
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
    tester = GenturixAPITester()
    success = tester.run_all_tests()
    
    # Return appropriate exit code
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())