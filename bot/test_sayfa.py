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

# Gün içi güncelleme (Rıdvan, 20 Ekim 2026): bugünün değeri daha yeni gün içi noktadan, gecmis.json'a yazılmaz
from datetime import datetime as _dt  # noqa: E402
import re as _re  # noqa: E402
_s = _dt(2026, 10, 20, 12, 40, tzinfo=bot.TR_SAAT)
_g = {"2026-10-19": {"saat": "20:10", "gumus": 57.0, "altin": 4150.0, "dolar": 49.5, "kur_tarihi": "2026-10-19", "gram": 90.7},
      "2026-10-20": {"saat": "10:25", "gumus": 57.7, "altin": 4180.0, "dolar": 49.5, "kur_tarihi": "2026-10-19", "gram": 91.8}}
_n = {"gumus": 58.1, "altin": 4190.0, "dolar": 49.5, "kur_tarihi": "2026-10-19", "gram": 92.47}
_gi = {"gunler": {"2026-10-20": [{"saat": "10:25", **_n}, {"saat": "12:35", "kaynak": "kayit", **_n}]}}
_m = sayfa.gun_ici_ile(_g, _s, _gi)
kontrol("gün içi: bugünün değeri 12:35 noktası", _m["2026-10-20"]["saat"] == "12:35" and _m["2026-10-20"]["gram"] == 92.47
        and "kaynak" not in _m["2026-10-20"])
kontrol("gün içi: gecmis değişmedi", _g["2026-10-20"]["saat"] == "10:25" and _m["2026-10-19"] == _g["2026-10-19"])
kontrol("gün içi: akşam kaydı daha yeniyse dokunmaz",
        sayfa.gun_ici_ile({**_g, "2026-10-20": {**_g["2026-10-20"], "saat": "20:05"}}, _s.replace(hour=20, minute=30), _gi)["2026-10-20"]["saat"] == "20:05")
kontrol("gün içi: eksik nokta atlanır",
        sayfa.gun_ici_ile(_g, _s, {"gunler": {"2026-10-20": [{"saat": "12:35", "gram": 92.0}]}}) is _g)
kontrol("gün içi: hafta sonu dokunmaz", sayfa.gun_ici_ile(_g, _s.replace(day=24), _gi) is _g)
kontrol("gün içi: dosya yoksa günlük kayıtlar", sayfa.gun_ici_ile(_g, _s, {}) is _g)
_c3 = Path(tempfile.mkdtemp())
_v = sayfa.uret(_c3, _m, simdi=_s, pazar=None, kati=True)
_ana = (_c3 / "index.html").read_text(encoding="utf-8")
kontrol("gün içi: sayfada 12:35 fiyatı", "92,47" in _ana and "12:35" in _v["guncelleme"])
kontrol("güncelleme saatleri metni", sayfa._site_guncelleme({"guncelleme": "Hafta içi ~10:00 ve ~20:00"})
        == "Hafta içi ~10:00, ~12:35, ~16:35 ve ~20:00" and "~10:00, ~12:35, ~16:35 ve ~20:00" in _ana)
_y = (bot.KOK / ".github" / "workflows" / "kaydet.yml").read_text(encoding="utf-8")
_cron = _re.search(r"cron: '(\d+) ([\d,]+) ", _y)
_tr = {f"{int(h) + 3:02d}:{int(_cron.group(1)):02d}" for h in _cron.group(2).split(",")}
kontrol("site saatleri gün içi kayıt saatlerinde", set(sayfa.SITE_ARA_SAATLER) <= _tr and "14:35" not in sayfa.SITE_ARA_SAATLER
        and "sayfa.yml/dispatches" in _y)

kontrol("tanıtım kartı: gün içinde güncellenen fiyat",
        _v["tanitim"]["satir"][0] == "Gün içinde güncellenen fiyat" and "<span>Gün içinde güncellenen fiyat</span>" in _ana
        and "sık" not in " ".join(_v["tanitim"]["satir"]))
kontrol("Google açıklaması: gün içinde güncellenen fiyat",
        _re.search(r'<meta name="description" content="Gram gümüş fiyatı [^"]*\. Gün içinde güncellenen fiyat\. Gram', _ana) is not None)

print(f"\ntest_sayfa: {gecen} sınama geçti")
