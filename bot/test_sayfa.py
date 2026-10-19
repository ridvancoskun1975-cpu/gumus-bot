"""Bilgi sayfası sınamaları (18 Ekim 2026 düzeni): son pazar analizi düğmesi, 404 sayfası, kaldırılan tablolar.
Ağa çıkmaz. Çalıştır: python bot/test_sayfa.py"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sayfa  # noqa: E402

bot = sayfa.bot
gecen = 0


def kontrol(ad, kosul, ek=""):
    global gecen
    if not kosul:
        print("HATA", ad, ek)
        sys.exit(1)
    gecen += 1
    print("TAMAM", ad)


B = sayfa.PAZAR_BASLIK
MEDYA = {"data": [
    {"caption": "Gram gümüş 90 ₺ ...", "media_type": "VIDEO", "permalink": "https://i/p/reels-pzt/",
     "timestamp": "2026-10-19T07:05:00+0000"},
    {"caption": f"{B} · 18 Ekim 2026\n...", "media_type": "VIDEO", "permalink": "https://i/reel/yorum-reels/",
     "timestamp": "2026-10-18T08:09:00+0000"},
    {"caption": f"{B} · 18 Ekim 2026\n...", "media_type": "CAROUSEL_ALBUM", "permalink": "https://i/p/yorum-kay/",
     "timestamp": "2026-10-18T08:07:00+0000"},
    {"caption": f"{B} · 11 Ekim 2026", "media_type": "CAROUSEL_ALBUM", "permalink": "https://i/p/eski/",
     "timestamp": "2026-10-11T08:07:00+0000"},
]}

os.environ.pop("IG_TOKEN", None)
kontrol("anahtar yoksa düğme yok", sayfa.son_pazar_analizi() is None)
os.environ["IG_TOKEN"] = "deneme"
bot._istek = lambda *a, **kw: MEDYA
kontrol("en yeni pazarın kaydırmalısı", sayfa.son_pazar_analizi() == {"url": "https://i/p/yorum-kay/", "tarih": "18 Ekim"},
        sayfa.son_pazar_analizi())
bot._istek = lambda *a, **kw: {"data": [MEDYA["data"][1]]}
kontrol("kaydırmalı yoksa Reels", sayfa.son_pazar_analizi()["url"] == "https://i/reel/yorum-reels/")
bot._istek = lambda *a, **kw: {"data": [MEDYA["data"][0]]}
bot._istek = lambda *a, **kw: {"data": [dict(MEDYA["data"][2], caption=sayfa.ESKI_PAZAR_BASLIK + " · 18 Ekim 2026")]}
kontrol("eski başlıklı yorum da bulunur", (sayfa.son_pazar_analizi() or {}).get("url") == "https://i/p/yorum-kay/")
bot._istek = lambda *a, **kw: {"data": [MEDYA["data"][0]]}
kontrol("yorum yoksa düğme yok", sayfa.son_pazar_analizi() is None)


def hata(*a, **kw):
    raise RuntimeError("Instagram API hatası (500)")


bot._istek = hata
kontrol("istek hatasında düğme yok, sayfa durmaz", sayfa.son_pazar_analizi() is None)

# Pazar yorumunun açıklaması bu başlıkla başlıyor mu (bot/yorum.py → aciklama)
kontrol("yorum açıklaması PAZAR_BASLIK ile başlar",
        f'f"{B} · ' in (Path(__file__).resolve().parent / "yorum.py").read_text(encoding="utf-8"))

# Sayfa üretimi: örnek kayıtlarla, düğmeli ve düğmesiz
cikti = Path(tempfile.mkdtemp())
gecmis = sayfa.ornek_gecmis()
sayfa.uret(cikti, gecmis, pazar={"url": "https://i/p/yorum-kay/", "tarih": "18 Ekim"}, kati=True)
ana = (cikti / "index.html").read_text(encoding="utf-8")
kontrol("düğme ana sayfada", "Son pazar analizi · 18 Ekim" in ana and 'href="https://i/p/yorum-kay/"' in ana)
hesap = (cikti / "hesap" / "100-gram-gumus-kac-tl" / "index.html").read_text(encoding="utf-8")
kontrol("düğme alt sayfalarda da (tanıtım kartı)", "Son pazar analizi · 18 Ekim" in hesap)
kontrol("tablolar ve üstteki Hesap makinesi düğmesi yok",
        "Kaç gram eder?</caption>" not in ana and "Kaç lira eder?" not in ana and 'href="#hesap-makinesi"' not in ana)
kontrol("hesap makinesi ve Bütün hesaplar duruyor", 'id="hesap"' in ana and 'href="hesap/"' in ana)
bulunamadi = (cikti / "404.html").read_text(encoding="utf-8")
url = sayfa.site_adresi()
kontrol("404: noindex, yönlendirme, tam adresler",
        'name="robots" content="noindex"' in bulunamadi and f'content="5; url={url}"' in bulunamadi
        and f"url('{url}fonts/" in bulunamadi and f'href="{url}hesap/"' in bulunamadi and "Sayfa bulunamadı" in bulunamadi)
kontrol("robots.txt site haritasını gösterir",
        (cikti / "robots.txt").read_text(encoding="utf-8") == f"User-agent: *\nAllow: /\n\nSitemap: {url}sitemap.xml\n")
import bilgi  # noqa: E402
kontrol("paylaşımlardaki site adı bilgi sayfasının alan adıyla aynı", sayfa.ALAN_ADI == f"https://{bilgi.SITE}/")
kontrol("adres alan adı", url == "https://gunlukgumus.com/" and "github.io" not in ana
        and "github.io" not in (cikti / "sitemap.xml").read_text(encoding="utf-8"))
cikti2 = Path(tempfile.mkdtemp())
sayfa.uret(cikti2, gecmis, pazar=None, kati=True)
kontrol("pazar yoksa düğme yok", "Son pazar analizi" not in (cikti2 / "index.html").read_text(encoding="utf-8"))

print(f"\ntest_sayfa: {gecen} sınama geçti")
