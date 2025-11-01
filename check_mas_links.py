"""Check MAS detail page links and PDF locations"""
from bs4 import BeautifulSoup
from pathlib import Path
import requests

# Read cached HTML
html = Path('mas.html').read_text(encoding='utf-8')
soup = BeautifulSoup(html, 'lxml')

# Find all search cards
cards = soup.select('article.mas-search-card')
print(f'Found {len(cards)} cards in cached HTML\n')

# Get first few detail page links
print('First 5 detail page links:')
for i, card in enumerate(cards[:5]):
    link = card.select_one('a.ola-link.mas-link')
    if link:
        href = link.get('href', '')
        title = link.get_text(strip=True)
        print(f'{i+1}. {title}')
        print(f'   URL: {href}')
        print(f'   Is PDF? {".pdf" in href.lower()}')
        print()

# Test fetching one detail page to see structure
print('\n=== Testing Detail Page Fetch ===')
first_card = cards[0]
first_link = first_card.select_one('a.ola-link.mas-link')
if first_link:
    detail_url = first_link.get('href', '')
    print(f'Fetching: {detail_url}')
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(detail_url, headers=headers, timeout=30, verify=False)
        print(f'Status: {response.status_code}')
        
        # Parse the detail page
        detail_soup = BeautifulSoup(response.text, 'lxml')
        
        # Look for PDF links
        pdf_links = []
        for a in detail_soup.find_all('a', href=True):
            href = a.get('href', '')
            if '.pdf' in href.lower():
                pdf_links.append(href)
        
        print(f'Found {len(pdf_links)} PDF links on detail page')
        if pdf_links:
            print('\nPDF links found:')
            for pdf in pdf_links[:3]:
                print(f'  - {pdf}')
    except Exception as e:
        print(f'Error: {e}')
