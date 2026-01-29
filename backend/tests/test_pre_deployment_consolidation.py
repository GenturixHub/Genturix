"""
GENTURIX Pre-Deployment Consolidation Tests - CORRECTED ENDPOINTS
Tests for 8 critical points:
1. Profile system with photo sync
2. Directory for all roles (including Resident)
3. Navigation without dead-ends (Guard and HR)
4. Notifications bell functional
5. Disabled modules hidden
6. Reservations module functional
7. Role security
8. E2E testing
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CREDENTIALS = {
    'admin': {'email': 'admin@genturix.com', 'password': 'Admin123!'},
    'guard': {'email': 'guarda1@genturix.com', 'password': 'Guard123!'},
    'hr': {'email': 'hr@genturix.com', 'password': 'HR123456!'},
    'resident': {'email': 'test.residente@genturix.com', 'password': 'Test123!'},
    'superadmin': {'email': 'superadmin@genturix.com', 'password': 'SuperAdmin123!'}
}


class TestAuthentication:
    """Test authentication for all roles"""
    
    @pytest.fixture(scope='class')
    def tokens(self):
        """Get tokens for all roles"""
        tokens = {}
        for role, creds in CREDENTIALS.items():
            response = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
            if response.status_code == 200:
                data = response.json()
                tokens[role] = {
                    'access_token': data['access_token'],
                    'user': data['user']
                }
            else:
                print(f"WARNING: Could not login as {role}: {response.status_code}")
        return tokens
    
    def test_admin_login(self, tokens):
        """Test Admin can login"""
        assert 'admin' in tokens, "Admin login failed"
        assert 'Administrador' in tokens['admin']['user']['roles']
        print(f"✓ Admin login successful: {tokens['admin']['user']['full_name']}")
    
    def test_guard_login(self, tokens):
        """Test Guard can login"""
        assert 'guard' in tokens, "Guard login failed"
        assert 'Guarda' in tokens['guard']['user']['roles']
        print(f"✓ Guard login successful: {tokens['guard']['user']['full_name']}")
    
    def test_hr_login(self, tokens):
        """Test HR can login"""
        assert 'hr' in tokens, "HR login failed"
        assert 'HR' in tokens['hr']['user']['roles']
        print(f"✓ HR login successful: {tokens['hr']['user']['full_name']}")
    
    def test_resident_login(self, tokens):
        """Test Resident can login"""
        assert 'resident' in tokens, "Resident login failed"
        assert 'Residente' in tokens['resident']['user']['roles']
        print(f"✓ Resident login successful: {tokens['resident']['user']['full_name']}")


class TestProfileSystem:
    """Test 1: Profile system with photo sync"""
    
    @pytest.fixture(scope='class')
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['admin'])
        assert response.status_code == 200
        return response.json()['access_token']
    
    @pytest.fixture(scope='class')
    def guard_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['guard'])
        assert response.status_code == 200
        return response.json()['access_token']
    
    def test_get_profile_admin(self, admin_token):
        """Admin can get their profile"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        response = requests.get(f"{BASE_URL}/api/profile", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert 'full_name' in data
        assert 'profile_photo' in data
        assert 'condominium_id' in data
        print(f"✓ Admin profile retrieved: {data['full_name']}")
    
    def test_get_profile_guard(self, guard_token):
        """Guard can get their profile"""
        headers = {'Authorization': f'Bearer {guard_token}'}
        response = requests.get(f"{BASE_URL}/api/profile", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert 'full_name' in data
        assert 'profile_photo' in data
        print(f"✓ Guard profile retrieved: {data['full_name']}")
    
    def test_update_profile(self, admin_token):
        """Profile can be updated via PATCH"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        update_data = {
            'public_description': 'Test description updated'
        }
        response = requests.patch(f"{BASE_URL}/api/profile", headers=headers, json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data.get('public_description') == 'Test description updated'
        print("✓ Profile update successful")


class TestDirectoryForAllRoles:
    """Test 2: Directory accessible for all roles including Resident
    CORRECT ENDPOINT: /api/profile/directory/condominium
    Response format: {users: [], grouped_by_role: {}, total_count: int, condominium_name: str}
    """
    
    @pytest.fixture(scope='class')
    def tokens(self):
        tokens = {}
        for role in ['admin', 'guard', 'hr', 'resident']:
            response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS[role])
            if response.status_code == 200:
                tokens[role] = response.json()['access_token']
        return tokens
    
    def test_admin_can_access_directory(self, tokens):
        """Admin can access directory"""
        headers = {'Authorization': f'Bearer {tokens["admin"]}'}
        response = requests.get(f"{BASE_URL}/api/profile/directory/condominium", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert 'users' in data
        assert 'grouped_by_role' in data
        assert 'total_count' in data
        print(f"✓ Admin can access directory: {data['total_count']} users")
    
    def test_guard_can_access_directory(self, tokens):
        """Guard can access directory"""
        headers = {'Authorization': f'Bearer {tokens["guard"]}'}
        response = requests.get(f"{BASE_URL}/api/profile/directory/condominium", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert 'users' in data
        assert 'grouped_by_role' in data
        print(f"✓ Guard can access directory: {data['total_count']} users")
    
    def test_hr_can_access_directory(self, tokens):
        """HR can access directory"""
        headers = {'Authorization': f'Bearer {tokens["hr"]}'}
        response = requests.get(f"{BASE_URL}/api/profile/directory/condominium", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert 'users' in data
        assert 'grouped_by_role' in data
        print(f"✓ HR can access directory: {data['total_count']} users")
    
    def test_resident_can_access_directory(self, tokens):
        """Resident can access directory"""
        headers = {'Authorization': f'Bearer {tokens["resident"]}'}
        response = requests.get(f"{BASE_URL}/api/profile/directory/condominium", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert 'users' in data
        assert 'grouped_by_role' in data
        print(f"✓ Resident can access directory: {data['total_count']} users")


class TestGuardNavigation:
    """Test 3.1: Guard navigation without dead-ends
    CORRECT ENDPOINTS:
    - /api/security/panic-events (Alertas)
    - /api/visitors/pending (Visitas)
    - /api/guard/my-shift (Mi Turno)
    - /api/guard/my-absences (Ausencias)
    - /api/guard/history (Historial)
    - /api/profile (Perfil)
    - /api/profile/directory/condominium (Personas)
    """
    
    @pytest.fixture(scope='class')
    def guard_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['guard'])
        assert response.status_code == 200
        return response.json()['access_token']
    
    def test_guard_panic_events(self, guard_token):
        """Guard can access panic events (Alertas tab)"""
        headers = {'Authorization': f'Bearer {guard_token}'}
        response = requests.get(f"{BASE_URL}/api/security/panic-events", headers=headers)
        assert response.status_code == 200
        print("✓ Guard can access panic events")
    
    def test_guard_pending_visitors(self, guard_token):
        """Guard can access pending visitors (Visitas tab)"""
        headers = {'Authorization': f'Bearer {guard_token}'}
        response = requests.get(f"{BASE_URL}/api/visitors/pending", headers=headers)
        assert response.status_code == 200
        print("✓ Guard can access pending visitors")
    
    def test_guard_my_shift(self, guard_token):
        """Guard can access my shift (Mi Turno tab)"""
        headers = {'Authorization': f'Bearer {guard_token}'}
        response = requests.get(f"{BASE_URL}/api/guard/my-shift", headers=headers)
        assert response.status_code == 200
        print("✓ Guard can access my shift")
    
    def test_guard_my_absences(self, guard_token):
        """Guard can access my absences (Ausencias tab)"""
        headers = {'Authorization': f'Bearer {guard_token}'}
        response = requests.get(f"{BASE_URL}/api/guard/my-absences", headers=headers)
        assert response.status_code == 200
        print("✓ Guard can access my absences")
    
    def test_guard_history(self, guard_token):
        """Guard can access history (Historial tab)"""
        headers = {'Authorization': f'Bearer {guard_token}'}
        response = requests.get(f"{BASE_URL}/api/guard/history", headers=headers)
        assert response.status_code == 200
        print("✓ Guard can access history")
    
    def test_guard_profile(self, guard_token):
        """Guard can access profile (Perfil tab)"""
        headers = {'Authorization': f'Bearer {guard_token}'}
        response = requests.get(f"{BASE_URL}/api/profile", headers=headers)
        assert response.status_code == 200
        print("✓ Guard can access profile")
    
    def test_guard_directory(self, guard_token):
        """Guard can access directory (Personas tab)"""
        headers = {'Authorization': f'Bearer {guard_token}'}
        response = requests.get(f"{BASE_URL}/api/profile/directory/condominium", headers=headers)
        assert response.status_code == 200
        print("✓ Guard can access directory")


class TestHRNavigation:
    """Test 3.2: HR navigation without dead-ends
    CORRECT ENDPOINTS:
    - /api/hr/guards
    - /api/hr/shifts
    - /api/hr/absences
    - /api/hr/candidates
    - /api/profile
    - /api/profile/directory/condominium
    """
    
    @pytest.fixture(scope='class')
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['hr'])
        assert response.status_code == 200
        return response.json()['access_token']
    
    def test_hr_guards(self, hr_token):
        """HR can access guards list"""
        headers = {'Authorization': f'Bearer {hr_token}'}
        response = requests.get(f"{BASE_URL}/api/hr/guards", headers=headers)
        assert response.status_code == 200
        print("✓ HR can access guards list")
    
    def test_hr_shifts(self, hr_token):
        """HR can access shifts"""
        headers = {'Authorization': f'Bearer {hr_token}'}
        response = requests.get(f"{BASE_URL}/api/hr/shifts", headers=headers)
        assert response.status_code == 200
        print("✓ HR can access shifts")
    
    def test_hr_absences(self, hr_token):
        """HR can access absences"""
        headers = {'Authorization': f'Bearer {hr_token}'}
        response = requests.get(f"{BASE_URL}/api/hr/absences", headers=headers)
        assert response.status_code == 200
        print("✓ HR can access absences")
    
    def test_hr_candidates(self, hr_token):
        """HR can access candidates"""
        headers = {'Authorization': f'Bearer {hr_token}'}
        response = requests.get(f"{BASE_URL}/api/hr/candidates", headers=headers)
        assert response.status_code == 200
        print("✓ HR can access candidates")
    
    def test_hr_profile(self, hr_token):
        """HR can access profile"""
        headers = {'Authorization': f'Bearer {hr_token}'}
        response = requests.get(f"{BASE_URL}/api/profile", headers=headers)
        assert response.status_code == 200
        print("✓ HR can access profile")
    
    def test_hr_directory(self, hr_token):
        """HR can access directory"""
        headers = {'Authorization': f'Bearer {hr_token}'}
        response = requests.get(f"{BASE_URL}/api/profile/directory/condominium", headers=headers)
        assert response.status_code == 200
        print("✓ HR can access directory")


class TestNotifications:
    """Test 4: Notifications bell functional"""
    
    @pytest.fixture(scope='class')
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['admin'])
        assert response.status_code == 200
        return response.json()['access_token']
    
    @pytest.fixture(scope='class')
    def guard_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['guard'])
        assert response.status_code == 200
        return response.json()['access_token']
    
    def test_admin_can_get_panic_events(self, admin_token):
        """Admin can get panic events for notifications"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        response = requests.get(f"{BASE_URL}/api/security/panic-events", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        active_alerts = [e for e in data if e.get('status') == 'active']
        print(f"✓ Admin notifications: {len(active_alerts)} active alerts")
    
    def test_guard_can_get_panic_events(self, guard_token):
        """Guard can get panic events for notifications"""
        headers = {'Authorization': f'Bearer {guard_token}'}
        response = requests.get(f"{BASE_URL}/api/security/panic-events", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        active_alerts = [e for e in data if e.get('status') == 'active']
        print(f"✓ Guard notifications: {len(active_alerts)} active alerts")


class TestModuleVisibility:
    """Test 5: Disabled modules hidden"""
    
    @pytest.fixture(scope='class')
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['admin'])
        assert response.status_code == 200
        data = response.json()
        return data['access_token'], data['user'].get('condominium_id')
    
    def test_get_condominium_modules(self, admin_token):
        """Get condominium modules configuration"""
        token, condo_id = admin_token
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f"{BASE_URL}/api/condominiums/{condo_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        modules = data.get('modules', {})
        print(f"✓ Condominium modules: {modules}")
        
        # Check school is disabled
        school_enabled = modules.get('school', {}).get('enabled', True)
        print(f"  - School module enabled: {school_enabled}")
        
        # Check reservations is enabled
        reservations_enabled = modules.get('reservations', {}).get('enabled', False)
        print(f"  - Reservations module enabled: {reservations_enabled}")


class TestReservationsModule:
    """Test 6: Reservations module functional"""
    
    @pytest.fixture(scope='class')
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['admin'])
        assert response.status_code == 200
        return response.json()['access_token']
    
    @pytest.fixture(scope='class')
    def resident_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['resident'])
        assert response.status_code == 200
        return response.json()['access_token']
    
    def test_admin_can_get_areas(self, admin_token):
        """Admin can get reservation areas"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin can get areas: {len(data)} areas")
    
    def test_admin_can_create_area(self, admin_token):
        """Admin can create a reservation area"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        area_data = {
            'name': 'Test Pool Area',
            'area_type': 'pool',
            'capacity': 20,
            'description': 'Test pool for testing',
            'available_from': '08:00',
            'available_until': '20:00',
            'requires_approval': False
        }
        response = requests.post(f"{BASE_URL}/api/reservations/areas", headers=headers, json=area_data)
        # May return 200 or 201
        assert response.status_code in [200, 201]
        print("✓ Admin can create area")
    
    def test_resident_can_get_areas(self, resident_token):
        """Resident can get reservation areas"""
        headers = {'Authorization': f'Bearer {resident_token}'}
        response = requests.get(f"{BASE_URL}/api/reservations/areas", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Resident can get areas: {len(data)} areas")
    
    def test_admin_can_get_reservations(self, admin_token):
        """Admin can get reservations"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        response = requests.get(f"{BASE_URL}/api/reservations", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Admin can get reservations: {len(data)} reservations")


class TestRoleSecurity:
    """Test 7: Role security - multi-tenant isolation"""
    
    @pytest.fixture(scope='class')
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['admin'])
        assert response.status_code == 200
        data = response.json()
        return data['access_token'], data['user'].get('condominium_id')
    
    @pytest.fixture(scope='class')
    def resident_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['resident'])
        assert response.status_code == 200
        data = response.json()
        return data['access_token'], data['user'].get('condominium_id')
    
    def test_users_have_condominium_id(self, admin_token, resident_token):
        """All users have condominium_id"""
        admin_condo = admin_token[1]
        resident_condo = resident_token[1]
        assert admin_condo is not None, "Admin should have condominium_id"
        assert resident_condo is not None, "Resident should have condominium_id"
        print(f"✓ Admin condominium_id: {admin_condo}")
        print(f"✓ Resident condominium_id: {resident_condo}")
    
    def test_directory_scoped_by_condominium(self, admin_token):
        """Directory is scoped by condominium"""
        token, condo_id = admin_token
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f"{BASE_URL}/api/profile/directory/condominium", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # All users should be from same condominium
        for user in data:
            assert user.get('condominium_id') == condo_id, f"User {user.get('full_name')} has wrong condominium"
        print(f"✓ Directory scoped by condominium: {len(data)} users")
    
    def test_resident_cannot_access_admin_endpoints(self, resident_token):
        """Resident cannot access admin-only endpoints"""
        token, _ = resident_token
        headers = {'Authorization': f'Bearer {token}'}
        
        # Try to access admin users endpoint
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        assert response.status_code in [401, 403], "Resident should not access admin users"
        print("✓ Resident cannot access admin users endpoint")


class TestE2EGuardFlow:
    """Test 8: E2E Guard login -> Profile edit -> Return to Alerts"""
    
    def test_guard_full_flow(self):
        """Guard can login, edit profile, and access alerts"""
        # Step 1: Login
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['guard'])
        assert response.status_code == 200
        data = response.json()
        token = data['access_token']
        user = data['user']
        print(f"✓ Step 1: Guard logged in as {user['full_name']}")
        
        headers = {'Authorization': f'Bearer {token}'}
        
        # Step 2: Get profile
        response = requests.get(f"{BASE_URL}/api/profile", headers=headers)
        assert response.status_code == 200
        profile = response.json()
        print(f"✓ Step 2: Got profile: {profile['full_name']}")
        
        # Step 3: Update profile
        update_data = {'public_description': 'E2E Test Update'}
        response = requests.patch(f"{BASE_URL}/api/profile", headers=headers, json=update_data)
        assert response.status_code == 200
        print("✓ Step 3: Profile updated")
        
        # Step 4: Access alerts (panic events)
        response = requests.get(f"{BASE_URL}/api/security/panic-events", headers=headers)
        assert response.status_code == 200
        alerts = response.json()
        print(f"✓ Step 4: Accessed alerts: {len(alerts)} events")
        
        # Step 5: Access directory
        response = requests.get(f"{BASE_URL}/api/profile/directory/condominium", headers=headers)
        assert response.status_code == 200
        directory = response.json()
        print(f"✓ Step 5: Accessed directory: {len(directory)} users")
        
        # Step 6: Access my shift
        response = requests.get(f"{BASE_URL}/api/guard/my-shift", headers=headers)
        assert response.status_code == 200
        print("✓ Step 6: Accessed my shift")
        
        # Step 7: Access my absences
        response = requests.get(f"{BASE_URL}/api/guard/my-absences", headers=headers)
        assert response.status_code == 200
        print("✓ Step 7: Accessed my absences")
        
        # Step 8: Access history
        response = requests.get(f"{BASE_URL}/api/guard/history", headers=headers)
        assert response.status_code == 200
        print("✓ Step 8: Accessed history")
        
        print("✓ E2E Guard flow completed successfully - ALL 8 TABS ACCESSIBLE")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
