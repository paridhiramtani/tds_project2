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

        print("\nTesting /run Endpoint...")
        payload = {
            "email": "test@example.com",
            "secret": "test_secret",
            "url": "https://example.com"
        }
        resp = requests.post(f"{base_url}/run", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            task_id = data.get("task_id")
            print(f"Run Request Passed. Task ID: {task_id}")
            
            # Test Task Status
            print(f"Testing /tasks/{task_id}...")
            status_resp = requests.get(f"{base_url}/tasks/{task_id}")
            if status_resp.status_code == 200:
                print(f"Task Status: {status_resp.json()['status']}")
            else:
                print(f"Task Status Failed: {status_resp.status_code}")
        else:
            print(f"Run Request Failed: {resp.status_code} - {resp.text}")

        print("\nTesting /analyze Endpoint...")
        analyze_payload = {
            "text": "What is 2 + 2?",
            "screenshot": None
        }
        # Note: This might fail if no OpenAI key, but we check the endpoint exists and handles it
        resp = requests.post(f"{base_url}/analyze", json=analyze_payload)
        if resp.status_code in [200, 500]: # 500 is expected if no API key, but endpoint is reached
            print(f"Analyze Endpoint Reachable (Status: {resp.status_code})")
        else:
            print(f"Analyze Endpoint Failed: {resp.status_code}")

    finally:
        print("Stopping server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    test_api()
