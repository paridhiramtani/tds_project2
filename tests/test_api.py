import requests
import os
import time
import subprocess
import sys
import signal

# Set env var for testing
os.environ["USER_SECRET"] = "test_secret"

def test_api():
    base_url = "http://localhost:8000"
    
    print("Starting server...")
    # Start server as a subprocess
    server_process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy()
    )
    
    try:
        # Wait for server to start
        print("Waiting for server to start...")
        time.sleep(10)
        
        print("Testing Health Check...")
        try:
            resp = requests.get(f"{base_url}/health")
            assert resp.status_code == 200
            print("Health Check Passed")
        except Exception as e:
            print(f"Health Check Failed: {e}")
            return

        print("\nTesting Frontend Serving...")
        resp = requests.get(f"{base_url}/")
        if resp.status_code == 200 and "<html" in resp.text:
            print("Frontend Served Successfully")
        else:
            print(f"Frontend Failed: {resp.status_code}")

        print("\nTesting /tasks Endpoint...")
        resp = requests.get(f"{base_url}/tasks")
        if resp.status_code == 200:
            print("Tasks Endpoint Reachable")
        else:
            print(f"Tasks Endpoint Failed: {resp.status_code}")

    finally:
        print("Stopping server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    test_api()
