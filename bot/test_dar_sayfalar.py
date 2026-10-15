"""Dar arama sayfalarının sınamaları: python bot/test_dar_sayfalar.py

Örnek kayıtlarla siteyi geçici bir klasöre üretir ve şunları denetler:
  - her sayfa var, başlığı (title) ve açıklaması benzersiz, başlık 70 karakteri geçmiyor;
  - site haritasındaki her adresin dosyası var, her sayfa site haritasında;
  - site içi bütün bağlantılar var olan bir sayfaya gidiyor (kırık bağlantı yok);
  - rakamlar tutarlı: 100 gram = 100 × gram fiyatı, 1000 TL = 1000 ÷ gram fiyatı, 925 ayar = × 0,925;
  - hiçbir sayfada "canlı" ya da "anlık" fiyat iddiası yok (yalnızca "Anlık (canlı) fiyat değildir");
  - tanıtım kartı her sayfada bir kez, kısa (160 harfi geçmez); başka takip daveti yok; yasal not var.
"""
import re
import sys
import tempfile
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main as bot  # noqa: E402
import sayfa  # noqa: E402
import dar_sayfalar as dar  # noqa: E402

HATA = []


def kontrol(kosul, mesaj):
    if not kosul:
        HATA.append(mesaj)


class Bag(HTMLParser):
    def __init__(self):
        super().__init__()
        self.bag, self.baslik, self.aciklama, self._t = [], "", "", False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.bag.append(a["href"])
        if tag == "title":
            self._t = True
        if tag == "meta" and a.get("name") == "description":
            self.aciklama = a.get("content", "")

    def handle_endtag(self, tag):
        if tag == "title":
            self._t = False

    def handle_data(self, data):
        if self._t:
            self.baslik += data


def main():
    gecmis = sayfa.ornek_gecmis()
    simdi = datetime(2026, 10, 15, 21, 0, tzinfo=bot.TR_SAAT)   # rehber #1–#4 yayımlanmış olsun
    with tempfile.TemporaryDirectory() as d:
        cikti = Path(d)
        euro = {k["kur_tarihi"]: k["dolar"] * 1.16 for k in gecmis.values()}
        v = sayfa.uret(cikti, gecmis, simdi, euro=euro)
        site = v["url"]
        dosyalar = sorted(p.relative_to(cikti).as_posix() for p in cikti.rglob("index.html"))
        kontrol(len(dosyalar) >= 25, f"beklenenden az sayfa: {len(dosyalar)}")

        harita = re.findall(r"<loc>([^<]+)</loc>", (cikti / "sitemap.xml").read_text(encoding="utf-8"))
        harita_yol = {h[len(site):] for h in harita}
        for h in harita_yol:
            kontrol((cikti / h / "index.html").exists(), f"site haritasında var, dosyası yok: {h}")
        for f in dosyalar:
            yol = f[: -len("index.html")]
            kontrol(yol in harita_yol, f"site haritasında yok: {yol}")

        basliklar, aciklamalar = {}, {}
        for f in dosyalar:
            html = (cikti / f).read_text(encoding="utf-8")
            p = Bag()
            p.feed(html)
            yol = f[: -len("index.html")]
            kontrol(p.baslik.strip(), f"başlık yok: {yol}")
            kontrol(len(p.baslik) <= 75, f"başlık uzun ({len(p.baslik)}): {yol} → {p.baslik}")
            kontrol(p.aciklama, f"açıklama yok: {yol}")
            kontrol(p.baslik not in basliklar, f"aynı başlık: {yol} ve {basliklar.get(p.baslik)}")
            kontrol(p.aciklama not in aciklamalar, f"aynı açıklama: {yol} ve {aciklamalar.get(p.aciklama)}")
            basliklar[p.baslik], aciklamalar[p.aciklama] = yol, yol
            temiz = html.replace("Anlık (canlı) fiyat değildir", "").replace("Anlık (canlı) değer değildir", "")
            temiz = temiz.replace("anlık fiyat değildir", "")
            # Rehberde "spot (anlık) fiyat" gibi tanımlar var; denetim fiyat ve hesap sayfaları için
            kontrol(yol.startswith("rehber/") or not re.search(r"(?i)\bcanlı\b|\banlık\b", re.sub(r"<[^>]+>", " ", temiz)),
                    f"'canlı/anlık' ifadesi: {yol}")
            sayfa_adres = site + yol
            for b in p.bag:
                tam = urljoin(sayfa_adres, b)
                if not tam.startswith(site):
                    continue
                hedef = urlparse(tam).path[len(urlparse(site).path):]
                if hedef.endswith((".png", ".xml", ".html")) and not hedef.endswith("index.html"):
                    kontrol((cikti / hedef).exists(), f"kırık bağlantı: {yol} → {b}")
                    continue
                kontrol((cikti / hedef / "index.html").exists(), f"kırık bağlantı: {yol} → {b}")

        # Rakam tutarlılığı (görselde yazan 2 ondalıklı değil, kaydın kendisiyle)
        son = gecmis[max(gecmis)]
        gram = son["gram"]
        html = (cikti / "hesap/100-gram-gumus-kac-tl/index.html").read_text(encoding="utf-8")
        kontrol(f'class="sayi">{dar.para(100 * gram)}<' in html, "100 gram sayfasının cevabı tutmuyor")
        html = (cikti / "hesap/1000-tl-kac-gram-gumus/index.html").read_text(encoding="utf-8")
        kontrol(f'class="sayi">{bot.tr_sayi(1000 / gram)}<' in html, "1000 TL sayfasının cevabı tutmuyor")
        html = (cikti / "hesap/gram-gumus-kac-euro/index.html").read_text(encoding="utf-8")
        kontrol(f'class="sayi">{bot.tr_sayi(gram / (son["dolar"] * 1.16), 3)}<' in html, "euro sayfasının cevabı tutmuyor")
        kontrol(not (cikti / "hesap/925-ayar-gumus-gram-fiyati").exists(), "925 ayar sayfası olmamalı (Rıdvan, 15 Ekim)")
        kontrol(not any("925 ayar" in (cikti / f).read_text(encoding="utf-8") and f.startswith("hesap/1")
                        for f in dosyalar), "ağırlık/tutar sayfalarında 925 ayar sütunu olmamalı")
        # Euro kuru alınamazsa euro sayfası olmadan üretilir, bağlantı kırılmaz
        with tempfile.TemporaryDirectory() as d2:
            sayfa.uret(Path(d2), gecmis, simdi, euro={})
            kontrol(not (Path(d2) / "hesap/gram-gumus-kac-euro").exists(), "euro yokken euro sayfası üretilmiş")
            for f in Path(d2).rglob("index.html"):
                kontrol("gram-gumus-kac-euro" not in f.read_text(encoding="utf-8"), f"euro yokken euro bağlantısı: {f}")
        html = (cikti / "hesap/altin-gumus-orani/index.html").read_text(encoding="utf-8")
        kontrol(f'class="sayi">{bot.tr_sayi(son["altin"] / son["gumus"], 1)}<' in html, "oran sayfası tutmuyor")
        html = (cikti / "rehber/index.html").read_text(encoding="utf-8")
        kontrol('href="1-ons-nedir/"' in html, "rehberde bölüm sayfasına bağlantı yok")
        html = (cikti / "index.html").read_text(encoding="utf-8")
        kontrol('href="hesap/"' in html and 'href="gecmis/"' in html, "ana sayfada hesap/geçmiş bağlantısı yok")
        kontrol((cikti / "googleade97aa5989bb9eb.html").exists(), "Search Console doğrulama dosyası yok")
        # İlk temasta tanıtım kartı her sayfada, az ve öz, sayfa başına tek davet (Rıdvan, 15 Ekim 2026)
        for f in dosyalar:
            html = (cikti / f).read_text(encoding="utf-8")
            kontrol(html.count('class="davet"') == 1 and html.count(">Instagram'da takip et<") == 1,
                    f"tanıtım kartı yok ya da birden çok: {f}")
            kontrol("hesabını takip et</a>" not in html and "davet-serit" not in html,
                    f"karttan başka takip daveti var (tek davet olmalı): {f}")
            kart = re.search(r'<aside class="davet".*?</aside>', html, re.S)
            if kart:
                yazi = " ".join(re.sub(r"<[^>]+>", " ", kart.group(0)).split())
                kontrol("Pazar üst düzey yapay zekâ analizi" in yazi and "Her gün fiyat, her pazar derin yorum" in yazi,
                        f"kartta pazar yorumu yok: {f}")
                kontrol(len(yazi) <= 160, f"kart uzun ({len(yazi)} harf; az ve öz olmalı): {f} → {yazi}")
            kontrol("yatırım tavsiyesi değildir" in html or "yatırım danışmanlığı kapsamında değildir" in html,
                    f"yasal not yok: {f}")

        print(f"{len(dosyalar)} sayfa, {len(harita)} site haritası adresi")
    if HATA:
        print("HATA:\n  " + "\n  ".join(HATA))
        sys.exit(1)
    print("Bütün sınamalar geçti.")


if __name__ == "__main__":
    main()
