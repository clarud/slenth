"""Analyze the new MAS regulations page structure"""
from bs4 import BeautifulSoup
from pathlib import Path

# Read the HTML
html = Path("mas_regulations_page.html").read_text(encoding="utf-8")
soup = BeautifulSoup(html, 'lxml')

# Check page title
title = soup.find('title')
print(f"Page title: {title.get_text() if title else 'No title'}")
print(f"Is maintenance page: {'Maintenance' in html}\n")

# Check for search cards (old structure)
old_cards = soup.select("article.mas-search-card")
print(f"Old structure (article.mas-search-card): {len(old_cards)}")

# Look for common patterns
print("\n=== Looking for content patterns ===")

# Check for any articles
articles = soup.find_all("article")
print(f"Total article tags: {len(articles)}")
if articles:
    print(f"First article classes: {articles[0].get('class', [])}")

# Check for divs with common class patterns
result_divs = soup.find_all('div', class_=lambda x: x and ('result' in str(x).lower() or 'card' in str(x).lower() or 'item' in str(x).lower()))
print(f"Divs with result/card/item in class: {len(result_divs)}")
if result_divs:
    print(f"First div classes: {result_divs[0].get('class', [])[:3]}")

# Check for links
all_links = soup.find_all('a', href=True)
print(f"\nTotal links: {len(all_links)}")

# Check for PDF links
pdf_links = [a for a in all_links if '.pdf' in a.get('href', '').lower()]
print(f"Direct PDF links: {len(pdf_links)}")

# Check for regulation/circular links
reg_links = [a for a in all_links if '/regulation/' in a.get('href', '').lower() or '/circular' in a.get('href', '').lower()]
print(f"Regulation/circular links: {len(reg_links)}")

# Show first few regulation links
if reg_links:
    print("\nFirst 5 regulation/circular links:")
    for i, link in enumerate(reg_links[:5]):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        classes = link.get('class', [])
        print(f"{i+1}. {text[:60]}...")
        print(f"   URL: {href[:80]}...")
        print(f"   Classes: {classes}")
        print()

# Look for list items
list_items = soup.find_all('li')
print(f"Total list items: {len(list_items)}")

# Check for specific MAS components
mas_components = soup.find_all(class_=lambda x: x and 'mas-' in str(x).lower())
print(f"Elements with 'mas-' prefix: {len(mas_components)}")
if mas_components:
    unique_classes = set()
    for comp in mas_components[:20]:
        classes = comp.get('class', [])
        for cls in classes:
            if 'mas-' in cls.lower():
                unique_classes.add(cls)
    print(f"Sample MAS classes: {list(unique_classes)[:10]}")
