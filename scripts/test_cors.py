#!/usr/bin/env python3
"""
Test CORS configuration between frontend and backend.
"""
import requests
import sys

def test_cors_preflight():
    """Test OPTIONS preflight request from frontend origin."""
    print("Testing CORS Preflight Request...")
    print("-" * 60)
    
    url = "http://localhost:8000/transactions"
    headers = {
        "Origin": "http://localhost:8080",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    
    try:
        response = requests.options(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Access-Control-Allow-Origin: {response.headers.get('access-control-allow-origin')}")
        print(f"Access-Control-Allow-Credentials: {response.headers.get('access-control-allow-credentials')}")
        print(f"Access-Control-Allow-Methods: {response.headers.get('access-control-allow-methods')}")
        print(f"Access-Control-Allow-Headers: {response.headers.get('access-control-allow-headers')}")
        
        # Check if CORS is properly configured
        if response.status_code == 200:
            origin = response.headers.get('access-control-allow-origin')
            credentials = response.headers.get('access-control-allow-credentials')
            
            if origin == "http://localhost:8080" and credentials == "true":
                print("\n✅ CORS preflight test PASSED!")
                return True
            else:
                print(f"\n❌ CORS preflight test FAILED!")
                print(f"   Expected origin: http://localhost:8080, got: {origin}")
                print(f"   Expected credentials: true, got: {credentials}")
                return False
        else:
            print(f"\n❌ CORS preflight test FAILED with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Is the backend running on http://localhost:8000?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_actual_request():
    """Test actual GET request with Origin header."""
    print("\n\nTesting Actual Request with CORS...")
    print("-" * 60)
    
    url = "http://localhost:8000/health"
    headers = {
        "Origin": "http://localhost:8080",
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Access-Control-Allow-Origin: {response.headers.get('access-control-allow-origin')}")
        
        if response.status_code == 200:
            origin = response.headers.get('access-control-allow-origin')
            if origin == "http://localhost:8080":
                print(f"Response: {response.json()}")
                print("\n✅ Actual request test PASSED!")
                return True
            else:
                print(f"\n❌ Actual request test FAILED!")
                print(f"   Expected origin: http://localhost:8080, got: {origin}")
                return False
        else:
            print(f"\n❌ Actual request test FAILED with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_cors_origins_config():
    """Test that CORS origins configuration includes frontend URL."""
    print("\n\nTesting CORS Configuration...")
    print("-" * 60)
    
    url = "http://localhost:8000/health/config"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            config = response.json()
            cors_origins = config.get("api", {}).get("cors_origins", [])
            
            print(f"CORS Origins: {cors_origins}")
            
            if "http://localhost:8080" in cors_origins:
                print("\n✅ CORS configuration test PASSED!")
                print("   Frontend origin (http://localhost:8080) is in allowed origins")
                return True
            else:
                print("\n❌ CORS configuration test FAILED!")
                print("   Frontend origin (http://localhost:8080) NOT in allowed origins")
                return False
        else:
            print(f"❌ Failed to fetch config (status {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("CORS Configuration Test")
    print("=" * 60)
    
    results = []
    
    # Test 1: CORS configuration
    results.append(("CORS Configuration", test_cors_origins_config()))
    
    # Test 2: Preflight request
    results.append(("CORS Preflight", test_cors_preflight()))
    
    # Test 3: Actual request
    results.append(("Actual Request", test_actual_request()))
    
    # Summary
    print("\n\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All CORS tests passed!")
        print("\nYour frontend (http://localhost:8080) can now communicate")
        print("with your backend (http://localhost:8000) without CORS errors.")
        return 0
    else:
        print("\n⚠️  Some CORS tests failed. Please check the configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
