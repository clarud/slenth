"""
Quick API test using curl command
"""
import subprocess
import json

# Create a small test PDF
test_pdf_content = b"%PDF-1.4\n%%EOF"
with open("test_upload.pdf", "wb") as f:
    f.write(test_pdf_content)

print("Testing document upload API endpoint...")
print("Note: Make sure uvicorn server is running on port 8000\n")

# Test standalone upload (no transaction_id)
print("=" * 80)
print("TEST: Standalone document upload (no transaction_id)")
print("=" * 80)

curl_cmd = [
    "curl",
    "-X", "POST",
    "http://localhost:8000/documents/upload",
    "-F", "file=@test_upload.pdf",
    "-F", "document_type=purchase_agreement"
]

try:
    result = subprocess.run(curl_cmd, capture_output=True, text=True)
    print(f"\nStatus Code: {result.returncode}")
    print(f"\nResponse:")
    try:
        response = json.loads(result.stdout)
        print(json.dumps(response, indent=2))
    except:
        print(result.stdout)
        print(result.stderr)
except Exception as e:
    print(f"Error: {e}")
    print("\nMake sure:")
    print("1. Uvicorn server is running: uvicorn app.main:app --reload")
    print("2. Curl is installed (or use PowerShell Invoke-WebRequest)")
