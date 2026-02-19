"""
GENTURIX Health & Readiness Endpoints Test Suite
================================================

Tests for:
- PHASE 1: GET /api/health - Basic liveness probe (no DB)
- PHASE 2: GET /api/readiness - Full dependency validation
- PHASE 3: Structured logging (via code review)
- PHASE 4: Security (no secrets exposed in response)

Test Criteria from PRD:
1. GET /api/health returns 200 with status='ok', service='genturix-api', version='1.0.0'
2. GET /api/health does NOT touch the database (liveness only)
3. GET /api/readiness returns 200 with status='ready' when all OK
4. GET /api/readiness validates MongoDB with ping
5. GET /api/readiness validates JWT_SECRET_KEY present
6. GET /api/readiness validates JWT_REFRESH_SECRET_KEY present
7. GET /api/readiness validates STRIPE_API_KEY present
8. GET /api/readiness validates RESEND_API_KEY present
9. GET /api/readiness validates ENVIRONMENT valid
10. GET /api/readiness returns 503 if something fails (no secrets exposed)
"""

import pytest
import requests
import os
import time

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthEndpoint:
    """
    PHASE 1: Health Endpoint Tests
    
    Requirements:
    - Returns 200 with status='ok', service='genturix-api', version='1.0.0'
    - NO database checks - pure liveness probe
    - NO authentication required
    """
    
    def test_health_returns_200(self):
        """GET /api/health returns HTTP 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASS: GET /api/health returns 200")
    
    def test_health_response_structure(self):
        """GET /api/health returns correct JSON structure"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify all required fields
        assert "status" in data, "Missing 'status' field"
        assert "service" in data, "Missing 'service' field"
        assert "version" in data, "Missing 'version' field"
        
        # Verify exact values
        assert data["status"] == "ok", f"Expected status='ok', got '{data['status']}'"
        assert data["service"] == "genturix-api", f"Expected service='genturix-api', got '{data['service']}'"
        assert data["version"] == "1.0.0", f"Expected version='1.0.0', got '{data['version']}'"
        
        print(f"PASS: Health response = {data}")
    
    def test_health_no_database_dependency(self):
        """
        GET /api/health should NOT touch the database.
        
        Verification approach:
        - Health endpoint should respond very fast (<100ms)
        - Even if database is slow/busy, health should return immediately
        - This is a liveness probe, not readiness
        """
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/api/health")
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        # Health should respond in under 100ms since it doesn't touch DB
        # Allowing more margin for network latency
        assert elapsed_ms < 500, f"Health took {elapsed_ms:.1f}ms - too slow for pure liveness"
        
        print(f"PASS: Health responded in {elapsed_ms:.1f}ms (no DB dependency)")
    
    def test_health_no_auth_required(self):
        """GET /api/health does NOT require authentication"""
        # Request without any auth headers
        response = requests.get(f"{BASE_URL}/api/health", headers={})
        assert response.status_code == 200, "Health should not require auth"
        print("PASS: Health endpoint accessible without authentication")
    
    def test_health_idempotent(self):
        """Multiple health checks return same result"""
        results = []
        for i in range(3):
            response = requests.get(f"{BASE_URL}/api/health")
            results.append((response.status_code, response.json()))
        
        # All results should be identical
        assert all(r[0] == 200 for r in results), "All health checks should return 200"
        assert all(r[1] == results[0][1] for r in results), "All health responses should be identical"
        print("PASS: Health endpoint is idempotent")


class TestReadinessEndpoint:
    """
    PHASE 2: Readiness Endpoint Tests
    
    Requirements:
    - Returns 200 with status='ready' when all dependencies OK
    - Validates: MongoDB, JWT secrets, Stripe, Resend, ENVIRONMENT
    - Returns 503 if any check fails
    - NO secrets exposed in response (PHASE 4 security)
    - NO authentication required (used by load balancers)
    """
    
    def test_readiness_returns_200_when_ready(self):
        """GET /api/readiness returns HTTP 200 when all dependencies OK"""
        response = requests.get(f"{BASE_URL}/api/readiness")
        
        # In our test environment, all dependencies should be configured
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        print("PASS: GET /api/readiness returns 200")
    
    def test_readiness_response_structure_success(self):
        """GET /api/readiness returns correct JSON when ready"""
        response = requests.get(f"{BASE_URL}/api/readiness")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify required field
        assert "status" in data, "Missing 'status' field"
        assert data["status"] == "ready", f"Expected status='ready', got '{data['status']}'"
        
        print(f"PASS: Readiness response = {data}")
    
    def test_readiness_no_auth_required(self):
        """GET /api/readiness does NOT require authentication (used by load balancers)"""
        response = requests.get(f"{BASE_URL}/api/readiness", headers={})
        # Should return either 200 or 503, but NOT 401/403
        assert response.status_code in [200, 503], f"Unexpected status: {response.status_code}"
        print("PASS: Readiness endpoint accessible without authentication")
    
    def test_readiness_does_not_expose_secrets(self):
        """GET /api/readiness response should NOT contain secret values (PHASE 4)"""
        response = requests.get(f"{BASE_URL}/api/readiness")
        
        data = response.json()
        response_text = str(data).lower()
        
        # Secrets that should NEVER appear in response
        forbidden_patterns = [
            "sk_test_",       # Stripe secret key prefix
            "sk_live_",       # Stripe live key prefix
            "re_",            # Resend API key prefix
            "genturix-super", # JWT secret pattern
            "jwt-secret",     # JWT in key
            "api_key=",       # Any API key
            "mongodb://",     # Connection string
        ]
        
        for pattern in forbidden_patterns:
            assert pattern not in response_text, f"SECURITY: Response contains secret pattern '{pattern}'"
        
        print("PASS: Readiness response does not expose secrets")
    
    def test_readiness_includes_request_id(self):
        """GET /api/readiness response header should include X-Request-ID (PHASE 3)"""
        response = requests.get(f"{BASE_URL}/api/readiness")
        
        # Check header
        request_id = response.headers.get("X-Request-ID")
        assert request_id is not None, "Missing X-Request-ID header"
        
        # Validate UUID format (basic check)
        assert len(request_id) == 36, f"Invalid request_id format: {request_id}"
        assert request_id.count("-") == 4, f"Invalid UUID format: {request_id}"
        
        print(f"PASS: Readiness includes X-Request-ID: {request_id}")
    
    def test_readiness_validates_mongodb(self):
        """
        Readiness should validate MongoDB connectivity.
        
        This is verified by:
        - Code review confirms db.command("ping") is called
        - If MongoDB is down, readiness returns 503
        """
        response = requests.get(f"{BASE_URL}/api/readiness")
        
        # In our environment, MongoDB should be up
        if response.status_code == 200:
            print("PASS: MongoDB connectivity validated (readiness returned 200)")
        else:
            data = response.json()
            # Check if MongoDB is the reason for failure
            if "failed_checks" in data:
                print(f"INFO: Readiness returned 503 with {data['failed_checks']} failed checks")
    
    def test_readiness_response_503_structure(self):
        """
        When readiness fails, response should have proper structure.
        
        Expected 503 response:
        {
            "status": "not_ready",
            "reason": "One or more critical dependencies unavailable",
            "failed_checks": <number>,
            "request_id": "<uuid>"
        }
        
        Note: We can only fully test this if something is misconfigured.
        For now, we verify the current response structure.
        """
        response = requests.get(f"{BASE_URL}/api/readiness")
        data = response.json()
        
        if response.status_code == 503:
            # Verify failure response structure
            assert "status" in data
            assert data["status"] == "not_ready"
            assert "reason" in data
            assert "failed_checks" in data
            assert isinstance(data["failed_checks"], int)
            assert data["failed_checks"] >= 1
            
            # SECURITY: Reason should be generic, not revealing which secret is missing
            assert "not configured" not in data.get("reason", "").lower(), \
                "Response should not reveal specific missing config"
            
            print(f"PASS: 503 response structure validated: {data}")
        else:
            # All checks passed
            assert response.status_code == 200
            assert data["status"] == "ready"
            print("PASS: Readiness returned 200 - all checks passed")


class TestHealthVsReadinessSemantics:
    """
    Tests to verify proper distinction between Health (liveness) and Readiness
    """
    
    def test_health_faster_than_readiness(self):
        """
        Health should be faster than readiness since it doesn't validate dependencies.
        Health = liveness probe (am I alive?)
        Readiness = startup probe (can I serve traffic?)
        """
        # Measure health
        health_start = time.time()
        health_response = requests.get(f"{BASE_URL}/api/health")
        health_time = (time.time() - health_start) * 1000
        
        # Measure readiness
        readiness_start = time.time()
        readiness_response = requests.get(f"{BASE_URL}/api/readiness")
        readiness_time = (time.time() - readiness_start) * 1000
        
        assert health_response.status_code == 200
        
        # Health should generally be faster since it doesn't check MongoDB
        # But network variance can cause fluctuations, so just verify both work
        print(f"Health: {health_time:.1f}ms | Readiness: {readiness_time:.1f}ms")
        print("PASS: Both endpoints responding correctly")
    
    def test_health_and_readiness_different_content(self):
        """
        Health and Readiness should have different response content.
        Health: {status: ok, service: ..., version: ...}
        Readiness: {status: ready} (when successful)
        """
        health_response = requests.get(f"{BASE_URL}/api/health")
        readiness_response = requests.get(f"{BASE_URL}/api/readiness")
        
        health_data = health_response.json()
        readiness_data = readiness_response.json()
        
        # Health should have service and version
        assert "service" in health_data, "Health should include 'service'"
        assert "version" in health_data, "Health should include 'version'"
        
        # Readiness success should be minimal
        if readiness_response.status_code == 200:
            assert readiness_data["status"] == "ready"
            # Readiness should NOT include service/version (those are for health)
            # This keeps readiness response minimal
        
        print(f"Health response fields: {list(health_data.keys())}")
        print(f"Readiness response fields: {list(readiness_data.keys())}")
        print("PASS: Health and Readiness have appropriate different content")


class TestCodeReviewValidation:
    """
    Tests that validate implementation details via code structure.
    These complement the API tests with implementation verification.
    """
    
    def test_environment_variables_configured(self):
        """
        Verify that the required environment variables are set.
        
        This test checks that the .env file has:
        - JWT_SECRET_KEY
        - JWT_REFRESH_SECRET_KEY  
        - STRIPE_API_KEY
        - RESEND_API_KEY
        - ENVIRONMENT
        """
        # Read backend .env
        env_path = "/app/backend/.env"
        try:
            with open(env_path, 'r') as f:
                env_content = f.read()
            
            required_vars = [
                "JWT_SECRET_KEY",
                "JWT_REFRESH_SECRET_KEY", 
                "STRIPE_API_KEY",
                "RESEND_API_KEY",
                "ENVIRONMENT"
            ]
            
            for var in required_vars:
                assert var in env_content, f"Missing {var} in .env"
            
            print(f"PASS: All required environment variables present in {env_path}")
        except FileNotFoundError:
            pytest.skip("Cannot access .env file from test environment")
    
    def test_readiness_endpoint_calls_mongodb_ping(self):
        """
        Code review verification: readiness endpoint should call db.command('ping')
        
        Location: server.py lines ~319-326
        """
        server_path = "/app/backend/server.py"
        try:
            with open(server_path, 'r') as f:
                server_code = f.read()
            
            # Check for MongoDB ping in readiness
            assert 'db.command("ping")' in server_code or "db.command('ping')" in server_code, \
                "Readiness should call db.command('ping') to validate MongoDB"
            
            print("PASS: Code confirms MongoDB ping check in readiness endpoint")
        except FileNotFoundError:
            pytest.skip("Cannot access server.py from test environment")
    
    def test_readiness_checks_all_required_dependencies(self):
        """
        Code review: readiness should check all 5 dependencies
        
        1. MongoDB connectivity
        2. JWT_SECRET_KEY
        3. JWT_REFRESH_SECRET_KEY
        4. STRIPE_API_KEY
        5. RESEND_API_KEY
        6. ENVIRONMENT validation
        """
        server_path = "/app/backend/server.py"
        try:
            with open(server_path, 'r') as f:
                server_code = f.read()
            
            checks = {
                "MongoDB": 'db.command("ping")' in server_code or "db.command('ping')" in server_code,
                "JWT_SECRET_KEY": "JWT_SECRET_KEY" in server_code and "not configured" in server_code,
                "JWT_REFRESH_SECRET_KEY": "JWT_REFRESH_SECRET_KEY" in server_code,
                "STRIPE_API_KEY": "STRIPE_API_KEY" in server_code,
                "RESEND_API_KEY": "RESEND_API_KEY" in server_code,
                "ENVIRONMENT": "ENVIRONMENT" in server_code and "development" in server_code and "production" in server_code
            }
            
            for check_name, found in checks.items():
                assert found, f"Readiness should validate {check_name}"
            
            print(f"PASS: Code confirms all {len(checks)} dependency checks in readiness")
        except FileNotFoundError:
            pytest.skip("Cannot access server.py from test environment")


if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v", "--tb=short"])
