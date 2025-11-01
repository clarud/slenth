import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

url = 'https://www.finma.ch/en/documentation/circulars/'
r = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r.content, 'lxml')

# Find all PDF links
pdf_links = [a for a in soup.find_all('a', href=True) if '.pdf' in a['href'].lower()]
print(f'Total PDF links found: {len(pdf_links)}\n')

# Filter for rundschreiben and English
en_rundschreiben = []
for a in pdf_links:
    abs_url = urljoin(url, a['href'])
    if '/rundschreiben/' in abs_url.lower():
        # Check if it's English or no language specified
        if 'sc_lang=' not in abs_url or 'sc_lang=en' in abs_url:
            text = a.get_text(strip=True)
            # Skip if text is just language codes
            if text and text not in ['DE', 'FR', 'IT', 'EN'] and len(text) > 3:
                en_rundschreiben.append((abs_url, text))

print(f'English rundschreiben PDFs with titles: {len(en_rundschreiben)}\n')
for i, (url, text) in enumerate(en_rundschreiben[:10]):
    print(f'{i+1}. {text[:80]}')
    print(f'   {url[:100]}...')
    print()
