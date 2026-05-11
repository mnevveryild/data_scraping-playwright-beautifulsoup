"""
Tanı scripti v2 — detay sayfası HTML yapısını inceler.
"""
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def ayrac(baslik):
    print(f"\n{'='*60}")
    print(f"  {baslik}")
    print('='*60)

def main():
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0]
        except:
            print("HATA: Chrome portu (9222) açık değil!")
            return

        # Liste sayfasından ilk ilanın URL'sini al
        liste_url = "https://www.hepsiemlak.com/ankara-kiralik?page=1"
        print(f"Liste sayfası yükleniyor...")
        page.goto(liste_url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        soup = BeautifulSoup(page.content(), 'html.parser')
        listings = soup.select('.listing-item')
        print(f"Bulunan ilan kartı: {len(listings)}")

        ilk = listings[0]
        article = ilk.find('article')
        ayrac("ARTICLE TAG")
        print(f"article id: {article.get('id') if article else 'YOK'}")
        print(f"article class: {article.get('class') if article else 'YOK'}")

        link = ilk.select_one('a.listingView__card-link')
        if not link:
            link = ilk.find('a', href=True)
        href = link['href'] if link else None
        detay_url = href if (href and href.startswith('http')) else "https://www.hepsiemlak.com" + href
        print(f"\nDetay URL: {detay_url}")

        # --- DETAY SAYFASI ---
        ayrac("DETAY SAYFASI YÜKLENİYOR (8 sn bekleniyor)...")
        dp = context.new_page()
        dp.goto(detay_url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(10)
        dsoup = BeautifulSoup(dp.content(), 'html.parser')

        # --- İLAN NO ---
        ayrac("İLAN NO — aday elementler")
        for sel in ['.ilan-no', '.listing-id', '[class*="ilanNo"]', '[class*="ilan-no"]',
                    '[class*="advert-id"]', '[class*="advertId"]', '.adNo', '[class*="adNo"]']:
            el = dsoup.select_one(sel)
            if el:
                print(f"  [{sel}] => '{el.get_text(strip=True)}' | attr: {dict(el.attrs)}")
        for attr in ['data-id', 'data-listing-id', 'data-advert-id', 'data-ilan-id']:
            tags = dsoup.find_all(attrs={attr: True})
            for t in tags[:2]:
                print(f"  {attr}='{t.get(attr)}' | <{t.name} class='{t.get('class')}'>")
        # URL'den ilan no
        print(f"\n  URL son segmenti: '{detay_url.rstrip('/').split('/')[-1]}'")

        # --- KAT SAYISI ---
        ayrac("KAT SAYISI — spec-item'ların tam yapısı")
        specs = dsoup.find_all('li', class_='spec-item')
        print(f"spec-item sayısı: {len(specs)}")
        for item in specs:
            print(f"\n  TEXT: {item.get_text(separator=' | ', strip=True)}")
            print(f"  HTML: {str(item)[:300]}")

        # spec-item yoksa alternatif dene
        if not specs:
            print("  spec-item YOK — alternatifler:")
            for sel in ['[class*="spec"]', '[class*="detail-spec"]', '[class*="property"]',
                        '.advert-info-list li', '.classifiedInfo li', 'table tr']:
                els = dsoup.select(sel)
                if els:
                    print(f"\n  [{sel}] => {len(els)} eleman")
                    for e in els[:5]:
                        print(f"    {e.get_text(separator='|', strip=True)[:150]}")

        # --- İLAN TARİHİ ---
        ayrac("İLAN TARİHİ — tüm <time> etiketleri")
        for t in dsoup.find_all('time'):
            print(f"  <time datetime='{t.get('datetime')}' class='{t.get('class')}'> => '{t.get_text(strip=True)}'")

        ayrac("İLAN TARİHİ — 'İlan Tarihi' metnini içeren elementler")
        for el in dsoup.find_all(string=lambda s: s and 'İlan Tarihi' in s):
            p = el.parent
            gp = p.parent if p else None
            print(f"  parent: <{p.name} class='{p.get('class')}'> => '{p.get_text(separator='|', strip=True)[:200]}'")
            if gp:
                print(f"  grandparent HTML: {str(gp)[:400]}")

        # --- KONUM ---
        ayrac("KONUM — .detail-info-location ve alternatifler")
        addr = dsoup.select_one('.detail-info-location')
        if addr:
            print(f"  BULUNDU:\n{addr.prettify()[:600]}")
        else:
            print("  .detail-info-location YOK — alternatifler:")
            for sel in ['[class*="location"]', '[class*="address"]', '[class*="konum"]',
                        '[class*="breadcrumb"]', '.he-breadcrumb', 'nav ol', 'nav ul']:
                el = dsoup.select_one(sel)
                if el:
                    print(f"\n  [{sel}]:")
                    print(f"  HTML: {str(el)[:500]}")

        dp.close()
        print("\n\nTanı tamamlandı.")

if __name__ == "__main__":
    main()
