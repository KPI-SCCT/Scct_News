# debug_g1_playwright.py
from scrapers.g1_scraper import G1Scraper

if __name__ == "__main__":
    scraper = G1Scraper()
    items = scraper.fetch_from_url("https://g1.globo.com", uf="SP", limit=30)
    for i, item in enumerate(items, start=1):
        print(
            f"{i:02d} - {item.published_at} - {item.title} - {item.url} - {item.uf}"
        )