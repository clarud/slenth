import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

async def test_finma():
    # Wait longer to let AJAX complete
    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, delay_before_return_html=5.0, page_timeout=120000)
    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(url='https://www.finma.ch/en/documentation/finma-circulars/', config=config)
        html = result.html
        
        # Check if content loaded
        print(f"HTML length: {len(html)}")
        print(f"Contains 'Nature-related financial risks': {'Nature-related financial risks' in html}")
        print(f"Contains 'FINMA Circular': {'FINMA Circular' in html}")
        print(f"Contains '2026/01': {'2026/01' in html}")
        print(f"Count of 'document-teaser-box-title': {html.count('document-teaser-box-title')}")
        
        # Save for inspection
        with open('finma_loaded.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("\\nSaved to finma_loaded.html")

asyncio.run(test_finma())
