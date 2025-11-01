"""Debug script to analyze MAS page structure"""
from bs4 import BeautifulSoup
from pathlib import Path

# Read the HTML
html = Path("mas_new_page.html").read_text(encoding="utf-8")
soup = BeautifulSoup(html, 'lxml')

# Check for the old structure
print("=== Checking OLD structure ===")
old_cards = soup.select("article.mas-search-card")
print(f"Found {len(old_cards)} article.mas-search-card elements")

old_links = soup.select("a.ola-link.mas-link")
print(f"Found {len(old_links)} a.ola-link.mas-link elements")

# Find all article tags
print("\n=== All article tags ===")
articles = soup.find_all("article")
print(f"Found {len(articles)} article elements")
if articles:
    print(f"First article classes: {articles[0].get('class', [])}")
    
# Find all links
print("\n=== Link analysis ===")
all_links = soup.find_all('a', href=True)
print(f"Total links: {len(all_links)}")

pdf_links = [a for a in all_links if '.pdf' in a.get('href', '').lower()]
print(f"PDF links: {len(pdf_links)}")

if pdf_links:
    print("\nFirst 5 PDF links:")
    for i, link in enumerate(pdf_links[:5]):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        print(f"{i+1}. {href[:80]}...")
        print(f"   Text: {text[:60]}...")
        print(f"   Classes: {link.get('class', [])}")
        print()

# Look for common search result patterns
print("\n=== Common patterns ===")
divs_with_result = soup.find_all('div', class_=lambda x: x and 'result' in str(x).lower())
print(f"Divs with 'result' in class: {len(divs_with_result)}")

divs_with_card = soup.find_all('div', class_=lambda x: x and 'card' in str(x).lower())
print(f"Divs with 'card' in class: {len(divs_with_card)}")

# Check for list items
list_items = soup.find_all('li')
print(f"Total list items: {len(list_items)}")
