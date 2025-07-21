#!/usr/bin/env python3
"""
Manual test for key LAILA features
"""

import requests
import time

BASE_URL = "http://localhost:5001"

def test_basic_connectivity():
    """Test if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/api/test", timeout=10)
        print(f"Server connectivity: {response.status_code} - {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Server connectivity failed: {e}")
        return False

def test_login_flow():
    """Test login and session management"""
    session = requests.Session()
    
    # Test admin login
    login_data = {"email": "me@saqr.me", "password": "password123"}
    login_response = session.post(f"{BASE_URL}/login", data=login_data)
    
    print(f"Login response: {login_response.status_code}")
    if login_response.status_code == 200:
        print("✓ Login successful")
        
        # Test admin page access
        admin_response = session.get(f"{BASE_URL}/admin.html")
        print(f"Admin page access: {admin_response.status_code}")
        
        # Test system settings API
        settings_response = session.get(f"{BASE_URL}/api/system-settings")
        print(f"System settings API: {settings_response.status_code}")
        
        if settings_response.status_code == 200:
            print("✓ Admin API working")
            print(f"Settings: {settings_response.json()}")
        else:
            print("✗ Admin API not working")
        
        return True
    else:
        print("✗ Login failed")
        return False

def test_data_interpreter():
    """Test data interpreter API"""
    session = requests.Session()
    
    # Login first
    login_data = {"email": "me@saqr.me", "password": "password123"}
    login_response = session.post(f"{BASE_URL}/login", data=login_data)
    
    if login_response.status_code != 200:
        print("✗ Cannot login for data interpreter test")
        return False
    
    # Test data interpretation
    test_data = {
        "data": "Test statistical data for interpretation",
        "data_type": "text",
        "research_context": "Test context",
        "analysis_type": "statistical_test",
        "target_insights": "Test insights",
        "audience_level": "graduate"
    }
    
    interpret_response = session.post(f"{BASE_URL}/api/interpret-data", json=test_data)
    print(f"Data interpretation: {interpret_response.status_code}")
    
    if interpret_response.status_code == 200:
        print("✓ Data interpretation working")
        return True
    else:
        print("✗ Data interpretation failed")
        try:
            print(f"Error: {interpret_response.text}")
        except:
            pass
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("LAILA MANUAL TEST")
    print("=" * 50)
    
    print("\n1. Testing server connectivity...")
    if not test_basic_connectivity():
        print("Server not running. Please start the app first.")
        exit(1)
    
    print("\n2. Testing login and admin access...")
    login_ok = test_login_flow()
    
    print("\n3. Testing data interpreter...")
    interpreter_ok = test_data_interpreter()
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Login/Admin: {'✓' if login_ok else '✗'}")
    print(f"Data Interpreter: {'✓' if interpreter_ok else '✗'}")
    
    if login_ok and interpreter_ok:
        print("\n🎉 Core functionality is working!")
    else:
        print("\n⚠️ Some issues remain. Check the output above.") 