"""Analyze the MAS regulations page structure - new fetch"""
from bs4 import BeautifulSoup
from pathlib import Path

html = Path("mas_regs_new.html").read_text(encoding="utf-8")
soup = BeautifulSoup(html, 'lxml')

print("=== PAGE INFO ===")
print(f"Title: {soup.title.text if soup.title else 'None'}")
print(f"Content length: {len(html)}")

print("\n=== SEARCH RESULT PATTERNS ===")
# Look for cards
cards = soup.find_all('div', class_=lambda x: x and 'card' in str(x).lower())
print(f"Divs with 'card' in class: {len(cards)}")

# Look for results
results = soup.find_all(class_=lambda x: x and 'result' in str(x).lower())
print(f"Elements with 'result' in class: {len(results)}")

# Look for items
items = soup.find_all(class_=lambda x: x and 'item' in str(x).lower())
print(f"Elements with 'item' in class: {len(items)}")

print("\n=== LINKS ===")
all_links = soup.find_all('a', href=True)
print(f"Total links: {len(all_links)}")

# Circular links
circ_links = [a for a in all_links if 'circular' in a.get('href', '').lower()]
print(f"Links with 'circular' in URL: {len(circ_links)}")

# PDF links
pdf_links = [a for a in all_links if '.pdf' in a.get('href', '').lower()]
print(f"Direct PDF links: {len(pdf_links)}")

if circ_links:
    print("\n=== FIRST 5 CIRCULAR LINKS ===")
    for i, link in enumerate(circ_links[:5]):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        parent = link.parent
        print(f"\n{i+1}. Text: {text[:80]}...")
        print(f"   URL: {href[:100]}")
        print(f"   Link classes: {link.get('class', [])}")
        print(f"   Parent tag: {parent.name}")
        print(f"   Parent classes: {parent.get('class', [])}")

print("\n=== MAS SPECIFIC CLASSES ===")
mas_elements = soup.find_all(class_=lambda x: x and 'mas-' in str(x).lower())
unique_mas_classes = set()
for elem in mas_elements:
    for cls in elem.get('class', []):
        if 'mas-' in cls.lower():
            unique_mas_classes.add(cls)
print(f"Unique MAS classes found: {len(unique_mas_classes)}")
print(f"Sample: {sorted(list(unique_mas_classes))[:15]}")

# Check for list structure
print("\n=== LIST STRUCTURES ===")
uls = soup.find_all('ul')
print(f"Total <ul> elements: {len(uls)}")
if uls:
    for i, ul in enumerate(uls[:5]):
        ul_classes = ul.get('class', [])
        if ul_classes and any('result' in str(c).lower() or 'list' in str(c).lower() for c in ul_classes):
            print(f"\nUL {i}: classes={ul_classes}")
            lis = ul.find_all('li', recursive=False)
            print(f"  Direct <li> children: {len(lis)}")
            if lis:
                first_li = lis[0]
                print(f"  First <li> classes: {first_li.get('class', [])}")
                links_in_li = first_li.find_all('a', href=True)
                print(f"  Links in first <li>: {len(links_in_li)}")
