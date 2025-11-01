"""
Test script to debug HKMA PDF download issue
"""
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

# Test URL
test_url = "https://www.hkma.gov.hk/media/eng/doc/key-information/guidelines-and-circular/2024/20241220e1.pdf"

print(f"Testing URL: {test_url}\n")

# Method 1: Direct requests
print("Method 1: Direct requests")
response = requests.get(test_url, timeout=30, verify=False)
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type')}")
print(f"Content length: {len(response.content)}")
print(f"First 500 chars: {response.content[:500]}")
print()

# Method 2: Selenium with redirect following
print("\nMethod 2: Selenium")
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--ignore-certificate-errors")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    driver.get(test_url)
    time.sleep(3)
    
    final_url = driver.current_url
    print(f"Initial URL: {test_url}")
    print(f"Final URL after redirects: {final_url}")
    print(f"Page title: {driver.title}")
    
    # Check if there's a download link in the page
    page_source = driver.page_source[:1000]
    print(f"Page source (first 1000 chars): {page_source}")
    
finally:
    driver.quit()
