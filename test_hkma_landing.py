"""
Find the actual PDF download link on the HKMA document landing page
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

# Test URL - the landing page
landing_url = "https://brdr.hkma.gov.hk/eng/doc-ldg/docId/20250109-1-EN"

print(f"Inspecting landing page: {landing_url}\n")

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--ignore-certificate-errors")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    driver.get(landing_url)
    time.sleep(3)
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'lxml')
    
    # Look for download buttons or PDF links
    print("Looking for PDF download links...")
    
    # Method 1: Look for buttons with "Download" text
    download_buttons = soup.find_all(['a', 'button'], string=lambda text: text and 'download' in text.lower())
    print(f"\nFound {len(download_buttons)} elements with 'download' text:")
    for btn in download_buttons[:5]:
        print(f"  - Tag: {btn.name}, Text: {btn.get_text(strip=True)[:50]}, href: {btn.get('href', 'N/A')}")
    
    # Method 2: Look for links ending in .pdf
    pdf_links = soup.find_all('a', href=lambda href: href and '.pdf' in href.lower())
    print(f"\nFound {len(pdf_links)} links with .pdf:")
    for link in pdf_links[:5]:
        print(f"  - {link.get('href')}")
    
    # Method 3: Look for iframes (PDF viewers)
    iframes = soup.find_all('iframe')
    print(f"\nFound {len(iframes)} iframes:")
    for iframe in iframes[:3]:
        print(f"  - src: {iframe.get('src', 'N/A')}")
    
    # Method 4: Try to click download button with Selenium
    try:
        # Common download button selectors
        selectors = [
            "//button[contains(text(), 'Download')]",
            "//a[contains(text(), 'Download')]",
            "//button[contains(@class, 'download')]",
            "//a[contains(@class, 'download')]",
            "//button[@id='download']",
            "//a[@id='download']",
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    print(f"\nFound element with selector: {selector}")
                    elem = elements[0]
                    print(f"  - Text: {elem.text}")
                    print(f"  - Tag: {elem.tag_name}")
                    if elem.get_attribute('href'):
                        print(f"  - href: {elem.get_attribute('href')}")
                    if elem.get_attribute('onclick'):
                        print(f"  - onclick: {elem.get_attribute('onclick')}")
                    break
            except:
                continue
                
    except Exception as e:
        print(f"Error finding download button: {e}")
    
finally:
    driver.quit()
