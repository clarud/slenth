"""
Comprehensive Test Suite for All Regulatory Crawlers
Tests HKMA, MAS, and FINMA crawlers

Usage:
    python test_all_crawlers.py
    python test_all_crawlers.py --live  # Use live URLs instead of cached HTML
    python test_all_crawlers.py --full  # Test more documents per crawler
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from crawlers.hkma import HKMACrawler
from crawlers.mas import MASCrawler
from crawlers.finma import FINMACrawler


class CrawlerTester:
    """Test runner for regulatory crawlers"""
    
    def __init__(self, use_cached=True, test_limit=3):
        self.use_cached = use_cached
        self.test_limit = test_limit
        self.results = {
            'hkma': {'status': 'pending', 'links': 0, 'success': 0, 'failed': 0},
            'mas': {'status': 'pending', 'links': 0, 'success': 0, 'failed': 0},
            'finma': {'status': 'pending', 'links': 0, 'success': 0, 'failed': 0},
        }
    
    def print_header(self, title):
        """Print formatted header"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)
    
    def print_section(self, title):
        """Print formatted section"""
        print(f"\n{title}")
        print("-" * 80)
    
    def test_hkma(self):
        """Test HKMA crawler"""
        self.print_header("HKMA Crawler Test (Hong Kong Monetary Authority)")
        
        try:
            # Initialize crawler
            crawler = HKMACrawler(use_cached_html=self.use_cached)
            print(f"Mode: {'Cached HTML' if self.use_cached else 'Live Fetch'}")
            print(f"URL: {crawler.base_url}")
            
            # Get HTML content
            if self.use_cached:
                html_file = Path("hkma_test.html")
                if not html_file.exists():
                    print(f"ERROR: Cached file not found: {html_file}")
                    self.results['hkma']['status'] = 'error'
                    return
                with open(html_file, encoding='utf-8') as f:
                    html_content = f.read()
            else:
                import requests
                response = requests.get(crawler.base_url, timeout=30, verify=False)
                html_content = response.text
            
            # Discover links
            self.print_section("1. Link Discovery")
            pdf_links = crawler._discover_pdf_links(html_content)
            direct_pdfs = [l for l in pdf_links if not l.get('is_brdr')]
            brdr_links = [l for l in pdf_links if l.get('is_brdr')]
            
            print(f"Total links found: {len(pdf_links)}")
            print(f"  - Direct PDFs: {len(direct_pdfs)}")
            print(f"  - BRDR links: {len(brdr_links)}")
            
            self.results['hkma']['links'] = len(pdf_links)
            
            # Test PDF parsing
            self.print_section("2. PDF Parsing")
            test_links = direct_pdfs[:self.test_limit]
            
            for i, link in enumerate(test_links, 1):
                title = link['title'][:60] + "..." if len(link['title']) > 60 else link['title']
                print(f"\n[{i}/{len(test_links)}] {title}")
                
                try:
                    start_time = time.time()
                    content = crawler._parse_pdf(link['url'], link.get('is_brdr', False))
                    elapsed = time.time() - start_time
                    
                    if content and len(content) > 100:
                        words = len(content.split())
                        print(f"  SUCCESS: {words:,} words in {elapsed:.1f}s")
                        self.results['hkma']['success'] += 1
                    else:
                        print(f"  WARNING: Empty content")
                        self.results['hkma']['failed'] += 1
                        
                except Exception as e:
                    print(f"  FAILED: {str(e)[:70]}")
                    self.results['hkma']['failed'] += 1
            
            self.results['hkma']['status'] = 'completed'
            
        except Exception as e:
            print(f"\nERROR: HKMA crawler test failed: {e}")
            self.results['hkma']['status'] = 'error'
    
    def test_mas(self):
        """Test MAS crawler"""
        self.print_header("MAS Crawler Test (Monetary Authority of Singapore)")
        
        try:
            # Initialize crawler
            crawler = MASCrawler(use_cached_html=self.use_cached)
            print(f"Mode: {'Cached HTML' if self.use_cached else 'Live Fetch'}")
            print(f"URL: {crawler.base_url}")
            
            # Crawl and parse
            self.print_section("1. Crawling and PDF Parsing")
            
            start_time = time.time()
            notices = crawler.crawl()
            elapsed = time.time() - start_time
            
            print(f"\nTotal notices crawled: {len(notices)}")
            print(f"Time taken: {elapsed:.1f}s")
            
            self.results['mas']['links'] = len(notices)
            
            if not notices:
                print("\nWARNING: No notices found!")
                self.results['mas']['status'] = 'completed'
                return
            
            # Display results for first N notices
            self.print_section("2. Sample Results")
            test_notices = notices[:self.test_limit]
            
            for i, notice in enumerate(test_notices, 1):
                title = notice['title'][:60] + "..." if len(notice['title']) > 60 else notice['title']
                content = notice.get('content', '')
                
                print(f"\n[{i}/{len(test_notices)}] {title}")
                
                if content and len(content) > 100:
                    words = len(content.split())
                    print(f"  SUCCESS: {words:,} words")
                    self.results['mas']['success'] += 1
                else:
                    print(f"  WARNING: Empty or minimal content")
                    self.results['mas']['failed'] += 1
            
            self.results['mas']['status'] = 'completed'
            
        except FileNotFoundError as e:
            print(f"\nERROR: {e}")
            print("Please ensure mas.html exists for cached testing")
            self.results['mas']['status'] = 'error'
        except Exception as e:
            print(f"\nERROR: MAS crawler test failed: {e}")
            import traceback
            traceback.print_exc()
            self.results['mas']['status'] = 'error'
    
    def test_finma(self):
        """Test FINMA crawler"""
        self.print_header("FINMA Crawler Test (Swiss Financial Market Supervisory Authority)")
        
        try:
            # Initialize crawler
            crawler = FINMACrawler(use_cached_html=self.use_cached)
            print(f"Mode: {'Cached HTML' if self.use_cached else 'Live Fetch'}")
            print(f"URL: {crawler.base_url}")
            
            # Crawl and parse
            self.print_section("1. Crawling and PDF Parsing")
            
            start_time = time.time()
            circulars = crawler.crawl()
            elapsed = time.time() - start_time
            
            print(f"\nTotal circulars crawled: {len(circulars)}")
            print(f"Time taken: {elapsed:.1f}s")
            
            self.results['finma']['links'] = len(circulars)
            
            if not circulars:
                print("\nWARNING: No circulars found!")
                self.results['finma']['status'] = 'completed'
                return
            
            # Display results for first N circulars
            self.print_section("2. Sample Results")
            test_circulars = circulars[:self.test_limit]
            
            for i, circular in enumerate(test_circulars, 1):
                title = circular['title'][:60] + "..." if len(circular['title']) > 60 else circular['title']
                content = circular.get('content', '')
                
                print(f"\n[{i}/{len(test_circulars)}] {title}")
                
                if content and len(content) > 100:
                    words = len(content.split())
                    print(f"  SUCCESS: {words:,} words")
                    self.results['finma']['success'] += 1
                else:
                    print(f"  WARNING: Empty or minimal content")
                    self.results['finma']['failed'] += 1
            
            self.results['finma']['status'] = 'completed'
            
        except FileNotFoundError as e:
            print(f"\nERROR: {e}")
            print("Please ensure finma.html exists for cached testing")
            self.results['finma']['status'] = 'error'
        except Exception as e:
            print(f"\nERROR: FINMA crawler test failed: {e}")
            import traceback
            traceback.print_exc()
            self.results['finma']['status'] = 'error'
    
    def print_summary(self):
        """Print test summary"""
        self.print_header("TEST SUMMARY")
        
        print("\nResults:")
        print("-" * 80)
        
        for crawler_name, result in self.results.items():
            status = result['status']
            status_emoji = {
                'completed': 'PASS',
                'error': 'FAIL',
                'not_implemented': 'TODO',
                'pending': '....'
            }.get(status, '????')
            
            print(f"\n{crawler_name.upper():10} [{status_emoji}]")
            
            if status == 'completed':
                total_tested = result['success'] + result['failed']
                success_rate = (result['success'] / total_tested * 100) if total_tested > 0 else 0
                print(f"  Links found: {result['links']}")
                print(f"  Tested: {total_tested}")
                print(f"  Success: {result['success']}")
                print(f"  Failed: {result['failed']}")
                print(f"  Success rate: {success_rate:.1f}%")
            elif status == 'not_implemented':
                print(f"  Status: Pending implementation")
            elif status == 'error':
                print(f"  Status: Test encountered error")
        
        # Overall summary
        completed = sum(1 for r in self.results.values() if r['status'] == 'completed')
        total = len(self.results)
        
        print("\n" + "-" * 80)
        print(f"Crawlers tested: {completed}/{total}")
        print(f"Status: {'All tests passed!' if completed == total else 'Some crawlers pending'}")
    
    def run_all(self):
        """Run all crawler tests"""
        self.print_header(f"REGULATORY CRAWLER TEST SUITE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\nConfiguration:")
        print(f"  Mode: {'Cached HTML' if self.use_cached else 'Live Fetch'}")
        print(f"  Test limit: {self.test_limit} PDFs per crawler")
        
        # Run tests
        self.test_hkma()
        self.test_mas()
        self.test_finma()
        
        # Print summary
        self.print_summary()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test all regulatory crawlers')
    parser.add_argument('--live', action='store_true', help='Fetch from live URLs instead of cached HTML')
    parser.add_argument('--full', action='store_true', help='Test more documents (10 instead of 3)')
    args = parser.parse_args()
    
    use_cached = not args.live
    test_limit = 10 if args.full else 3
    
    tester = CrawlerTester(use_cached=use_cached, test_limit=test_limit)
    tester.run_all()


if __name__ == "__main__":
    main()
