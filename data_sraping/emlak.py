import csv
import time
import os
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

SU_ANKI_KLASOR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE_PATH = os.path.join(SU_ANKI_KLASOR, "ankara_emlak_FINAL_FULL_KONUM_3.csv")

def save_to_csv(data_list):
    fields = [
        'ilan_no', 'kategori', 'fiyat', 'oda_sayisi', 'm2',
        'bulundugu_kat', 'bina_yasi', 'isinma_tipi', 'tapu_durumu',
        'banyo_sayisi', 'kat_sayisi', 'krediye_uygun', 'esya_durumu',
        'firma_adi', 'ilan_tarihi', 'ilce', 'mahalle', 'url'
    ]
    file_exists = os.path.isfile(CSV_FILE_PATH)
    with open(CSV_FILE_PATH, mode='a', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=fields, delimiter=';')
        if not file_exists:
            writer.writeheader()
        writer.writerows(data_list)
        file.flush()

def parse_detay_tablosu(soup):
    """
    Detay sayfasındaki table > tr satırlarını {etiket: deger} sözlüğüne çevirir.
    Örnek: {'İlan no': '9228-43', 'Kat Sayısı': '4', 'Son Güncelleme': '11/05/2026', ...}
    """
    tablo = {}
    for row in soup.select('table tr'):
        cells = row.find_all(['td', 'th'])
        if len(cells) >= 2:
            key = cells[0].get_text(strip=True)
            val = cells[1].get_text(strip=True)
            if key:
                tablo[key] = val
    return tablo

def get_detay_verileri(context, url):
    result = {
        'kat_sayisi': '-', 'ilan_tarihi': '-',
        'ilce': '-', 'mahalle': '-',
        'ilan_no_detay': '-'
    }
    new_page = None
    try:
        new_page = context.new_page()
        new_page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            new_page.wait_for_selector('table', timeout=6000)
        except:
            pass
        time.sleep(8)

        soup = BeautifulSoup(new_page.content(), 'html.parser')
        tablo = parse_detay_tablosu(soup)

        # İLAN NO (yedek — liste sayfasındaki article id'si yoksa kullanılır)
        result['ilan_no_detay'] = tablo.get('İlan no', '-')

        # KAT SAYISI
        result['kat_sayisi'] = tablo.get('Kat Sayısı', tablo.get('Toplam Kat', '-'))

        # İLAN TARİHİ — <time datetime="2026/05/11"> etiketinden
        time_tag = soup.find('time', attrs={'datetime': True})
        if time_tag:
            result['ilan_tarihi'] = time_tag['datetime']
        else:
            # Yedek: tablodaki "Son Güncelleme" değeri
            result['ilan_tarihi'] = tablo.get('Son Güncelleme', tablo.get('İlan Tarihi', '-'))

        # KONUM — .detail-info-location içindeki div'ler
        addr = soup.select_one('.detail-info-location')
        if addr:
            parts = [d.get_text(strip=True) for d in addr.find_all('div') if d.get_text(strip=True)]
            # parts[0]=Ankara, parts[1]=İlçe, parts[2]=Mahalle
            if len(parts) >= 2:
                result['ilce'] = parts[1]
            if len(parts) >= 3:
                result['mahalle'] = parts[2]

    except Exception as e:
        print(f"    [Detay Hatası] {e}")
    finally:
        if new_page:
            new_page.close()

    return result

def main():
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = context.pages[0]
            print(f"Bağlantı kuruldu. Çıktı: {CSV_FILE_PATH}")
        except:
            print("HATA: Chrome portu (9222) açık değil!")
            return

        for page_num in range(1, 300):
            target_url = f"https://www.hepsiemlak.com/ankara-kiralik?page={page_num}"

            if 'kiralik' in target_url:
                kategori = "Kiralık"
            elif 'satilik' in target_url:
                kategori = "Satılık"
            else:
                kategori = "-"

            print(f"\n>>> Sayfa {page_num} işleniyor... [{kategori}]")

            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(5)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(5)

                soup = BeautifulSoup(page.content(), 'html.parser')
                listings = soup.select('.listing-item')
                print(f"    Bu sayfada {len(listings)} ilan bulundu.")

                final_data = []
                for index, listing in enumerate(listings):
                    try:
                        # URL — doğru selector: a.listingView__card-link
                        link = listing.select_one('a.listingView__card-link')
                        if link and link.get('href'):
                            href = link['href']
                            url = href if href.startswith('http') else "https://www.hepsiemlak.com" + href
                        else:
                            url = "-"

                        # İLAN NO — article etiketinin id attribute'u (örn: "9228-43")
                        article = listing.find('article')
                        ilan_no = article.get('id', '-') if article else "-"

                        # FIYAT
                        fiyat_el = listing.select_one('.list-view-price')
                        fiyat = fiyat_el.get_text(strip=True).replace("TL", "").replace(".", "").strip() if fiyat_el else "0"

                        # TEMEL ÖZELLİKLER — liste kartından
                        oda_el = listing.select_one('.houseRoomCount')
                        oda = oda_el.get_text(strip=True).replace("\n", "").strip() if oda_el else "-"

                        m2_el = listing.select_one('.squareMeter')
                        m2 = m2_el.get_text(strip=True).replace("m²", "").strip() if m2_el else "-"

                        yas_el = listing.select_one('.buildingAge')
                        yas = yas_el.get_text(strip=True).replace(" Yaşında", "").strip() if yas_el else "-"

                        kat_el = listing.select_one('.floortype')
                        bulundugu_kat = kat_el.get_text(strip=True) if kat_el else "-"

                        firma_el = listing.select_one('.listing-card--owner-info__firm-name')
                        firma = firma_el.get_text(strip=True) if firma_el else "-"

                        # LİSTE SAYFASI KONUM (yedek)
                        adres_el = listing.select_one('address')
                        konum_liste = adres_el.get_text(strip=True) if adres_el else "-"
                        konum_parts = [p.strip() for p in konum_liste.replace(' / ', '/').split('/') if p.strip()]
                        ilce_yedek = konum_parts[1] if len(konum_parts) >= 2 else (konum_parts[0] if konum_parts else "-")
                        mahalle_yedek = konum_parts[2] if len(konum_parts) >= 3 else "-"

                        # DETAY SAYFASINDAN VERİ ÇEK
                        detay = {
                            'kat_sayisi': '-', 'ilan_tarihi': '-',
                            'ilce': '-', 'mahalle': '-', 'ilan_no_detay': '-'
                        }
                        if url != "-":
                            detay = get_detay_verileri(context, url)

                        # Detaydan gelen ilan_no daha güvenilir olabilir
                        if ilan_no == "-" and detay['ilan_no_detay'] != '-':
                            ilan_no = detay['ilan_no_detay']

                        final_ilce = detay['ilce'] if detay['ilce'] != '-' else ilce_yedek
                        final_mahalle = detay['mahalle'] if detay['mahalle'] != '-' else mahalle_yedek

                        print(f"    [{index+1}/{len(listings)}] {ilan_no} | Kat:{detay['kat_sayisi']} | Tarih:{detay['ilan_tarihi']} | {final_ilce} / {final_mahalle}")

                        final_data.append({
                            'ilan_no': ilan_no,
                            'kategori': kategori,
                            'fiyat': fiyat,
                            'oda_sayisi': oda,
                            'm2': m2,
                            'bulundugu_kat': bulundugu_kat,
                            'bina_yasi': yas,
                            'isinma_tipi': "Kombi (Doğalgaz)",
                            'tapu_durumu': "Kat Mülkiyeti",
                            'banyo_sayisi': "1",
                            'kat_sayisi': detay['kat_sayisi'],
                            'krediye_uygun': "Evet",
                            'esya_durumu': "Boş",
                            'firma_adi': firma,
                            'ilan_tarihi': detay['ilan_tarihi'],
                            'ilce': final_ilce,
                            'mahalle': final_mahalle,
                            'url': url
                        })

                        time.sleep(3)

                    except Exception as inner_e:
                        print(f"    İlan işleme hatası: {inner_e}")
                        continue

                if final_data:
                    save_to_csv(final_data)
                    print(f"Sayfa {page_num}: {len(final_data)} ilan diske yazıldı.")

            except Exception as e:
                print(f"Sayfa hatası: {e}")
                continue

        print(f"\nİşlem Tamamlandı. Dosya: {CSV_FILE_PATH}")

if __name__ == "__main__":
    main()
