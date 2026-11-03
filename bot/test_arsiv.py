"""Geçmiş fiyat arşivi sınamaları (bot/arsiv.py + bot/dar_sayfalar.py geçmiş bölümü).

  python bot/test_arsiv.py
"""
import json
import re
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import arsiv  # noqa: E402
import main as bot  # noqa: E402
import sayfa  # noqa: E402

GECEN = 0


def kontrol(kosul, mesaj):
    global GECEN
    if not kosul:
        print(f"HATA: {mesaj}")
        sys.exit(1)
    GECEN += 1
    print(f"TAMAM {mesaj}")


# ---- Sabit yıllık veriler
kontrol(set(arsiv.YILLIK_ONS) == set(arsiv.YILLIK_KUR), "USGS ons ve ECB kur yılları aynı")
yillar = sorted(arsiv.YILLIK_ONS)
kontrol(yillar == list(range(yillar[0], yillar[-1] + 1)), "yıllık tabloda boş yıl yok")
kontrol(all(5 < v < 100 for v in arsiv.YILLIK_ONS.values()), "ons değerleri makul aralıkta")
kontrol(all(1 < v < 100 for v in arsiv.YILLIK_KUR.values()), "kur değerleri makul aralıkta")
kontrol(all(arsiv.YILLIK_KUR[y] < arsiv.YILLIK_KUR[y + 1] for y in yillar[:-1] if y != 2009),
        "dolar/TL yıllık ortalaması 2010'dan beri her yıl yükseliyor (yazım hatası denetimi)")
kontrol(arsiv.YILLIK_ONS[2025] == 40.08 and arsiv.YILLIK_ONS[2011] == 35.26, "USGS 2025 ve 2011 rakamları")

# ---- Günlük kayıtlar: MetalCharts kapanışı × o gün ya da öncesindeki son ECB kuru
metal = {"XAG": {date(2026, 1, 1): 70.0, date(2026, 1, 2): 72.0, date(2026, 1, 3): 73.0, date(2026, 1, 5): 74.0,
                 date(2026, 10, 13): 80.0},
         "XAU": {date(2026, 1, 2): 4300.0}}
ecb = {date(2025, 12, 31): 43.0, date(2026, 1, 2): 43.1, date(2026, 1, 5): 43.2, date(2026, 10, 13): 50.0}
g = arsiv.gunluk_kayitlar(metal, ecb, sinir=date(2026, 10, 13))
kontrol(set(g) == {"2026-01-01", "2026-01-02", "2026-01-05"}, "hafta sonu ve sınır günü arşive girmez")
kontrol(g["2026-01-01"]["kur_tarihi"] == "2025-12-31" and g["2026-01-01"]["dolar"] == 43.0,
        "ECB tatilinde (1 Ocak) önceki son kur kullanılır")
kontrol(abs(g["2026-01-02"]["gram"] - 72.0 * 43.1 / 31.1035) < 1e-3, "gram = ons × kur ÷ 31,1035")
kontrol(g["2026-01-02"]["altin"] == 4300.0 and g["2026-01-05"]["altin"] is None, "altın yoksa boş kalır")
kontrol(not arsiv.gunluk_kayitlar(metal, {date(2025, 1, 1): 40.0}), "7 günden eski kur kullanılmaz")

# ---- Birleştirme: botun kayıtları üstün, arşiv yalnız ilk kayıttan önce
kendi = {"2026-01-05": {"gumus": 99.0, "dolar": 43.0, "gram": 137.0}, "2026-01-06": {"gumus": 75, "dolar": 43, "gram": 103}}
arsiv.AY_EN_AZ_GUN, _eski_az = 1, arsiv.AY_EN_AZ_GUN   # bu küçük örnekte ilk ay kırpması kapalı
b = arsiv.birlesik(kendi, g)
arsiv.AY_EN_AZ_GUN = _eski_az
kontrol(list(b) == ["2026-01-01", "2026-01-02", "2026-01-05", "2026-01-06"], "birleşik sıralı")
kontrol(b["2026-01-05"]["gumus"] == 99.0 and "kaynak" not in b["2026-01-05"], "aynı günde botun kaydı kalır")
kontrol(b["2026-01-01"]["kaynak"] == arsiv.KAYNAK, "arşiv günü işaretli")
kontrol(arsiv.birlesik(kendi, {}) == kendi, "arşiv yoksa yalnız botun kayıtları")
tek = {"2025-10-31": g["2026-01-02"], **{f"2025-11-{d:02d}": g["2026-01-02"] for d in (3, 4, 5, 6, 7, 10)}}
kontrol(min(arsiv.birlesik({"2026-10-13": kendi["2026-01-06"]}, tek)) == "2025-11-03",
        "arşivin birkaç günlük ilk ayı (31 Ekim 2025) atılır")

# ---- Okuma: kapalıyken ve bozuk dosyada boş
with tempfile.TemporaryDirectory() as d:
    eski_yol, arsiv.YEREL = arsiv.YEREL, Path(d) / "arsiv.json"
    try:
        kontrol(arsiv.oku() == {}, "dosya yoksa boş")
        arsiv.YEREL.write_text("bozuk", encoding="utf-8")
        kontrol(arsiv.oku() == {}, "bozuk dosyada boş")
        arsiv.YEREL.write_text(json.dumps({"2026-01-02": g["2026-01-02"], "x": {}, "2026-01-03": {"gumus": 0}}))
        kontrol(list(arsiv.oku()) == ["2026-01-02"], "geçersiz satırlar atlanır")
        arsiv.ARSIV_ACIK = False
        kontrol(arsiv.oku() == {}, "ARSIV_ACIK = False iken arşiv okunmaz")
    finally:
        arsiv.ARSIV_ACIK = True
        arsiv.YEREL = eski_yol

# ---- Yıllık satırlar
gecmis = sayfa.ornek_gecmis()
ornek_arsiv = arsiv.ornek(gecmis)
gunluk = arsiv.birlesik(gecmis, ornek_arsiv)
ys = arsiv.yillik_satirlar(gunluk, date(2026, 10, 13))
kontrol(ys[0]["yil"] == 2009 and ys[-1]["yil"] == 2026, "yıllar 2009'dan içinde bulunulan yıla")
kontrol(all(r["kaynak"] == "usgs" for r in ys if r["yil"] <= 2025), "2025'e kadar USGS")
kontrol(ys[-1]["kaynak"] == "gunluk" and ys[-1]["kismi"] and ys[-1]["gun"] >= arsiv.YIL_EN_AZ_GUN,
        "2026 günlük verilerden, kısmi")
kontrol(ys[0]["deg_once"] is None and ys[1]["deg_once"] == ys[0]["gram"], "değişim bir önceki yıla göre")
kontrol(abs(ys[-2]["gram"] - 40.08 * 39.57 / 31.1035) < 1e-9, "2025 gram ≈ ons × kur ÷ 31,1035")
az = {k: v for k, v in list(gunluk.items())[-5:]}
kontrol(arsiv.yillik_satirlar(az, date(2026, 10, 13))[-1]["yil"] == 2025, "az günlük veride içinde bulunulan yıl satırı çıkmaz")
# Yılı kapsamayan veri yıl ortalaması diye gösterilmez (arşiv inmediyse yalnız botun Ekim'den beri kayıtları kalır)
bot_kayit = {g: k for g, k in gunluk.items() if g >= "2026-09-01"}
kontrol(len(bot_kayit) >= arsiv.YIL_EN_AZ_GUN and arsiv.yillik_satirlar(bot_kayit, date(2026, 11, 3))[-1]["yil"] == 2025,
        "yalnız son haftaların kaydı varsa 2026 satırı çıkmaz (Ocak'tan başlamıyor)")
ocaktan = {g: k for g, k in gunluk.items() if g >= "2026-01-01"}
kontrol(arsiv.yillik_satirlar(ocaktan, date(2027, 3, 1))[-1]["yil"] == 2025,
        "biten yıl Aralık'a kadar sürmüyorsa yıl ortalaması diye gösterilmez")

# ---- Sayfalar
simdi = datetime(2026, 10, 13, 20, 30, tzinfo=bot.TR_SAAT)
euro = {k["kur_tarihi"]: k["dolar"] * 1.16 for k in gecmis.values()}
with tempfile.TemporaryDirectory() as d:
    cikti = Path(d)
    sayfa.uret(cikti, gecmis, simdi, euro=euro, arsiv=ornek_arsiv)
    merkez = (cikti / "gecmis" / "index.html").read_text(encoding="utf-8")
    yillik = (cikti / "gecmis" / "yillik" / "index.html").read_text(encoding="utf-8")
    yil = (cikti / "gecmis" / "2026" / "index.html").read_text(encoding="utf-8")
    ilk_ay = min(ornek_arsiv)[:7]
    ay = (cikti / "gecmis" / ilk_ay / "index.html").read_text(encoding="utf-8")
    harita = (cikti / "sitemap.xml").read_text(encoding="utf-8")
    kontrol("Yıllara göre" in merkez and 'href="../gecmis/yillik/"' in merkez, "merkezde yıllar ve bütün yıllar bağlantısı")
    kontrol(merkez.count("<tr>") >= 6 + 10, "merkezde yıl ve ay satırları")
    kontrol("2009" in yillik and "40,08" in yillik and "USGS" in yillik, "yıllık sayfada USGS rakamları ve kaynağı")
    kontrol(yillik.count('class="cubuk') == 2 * len(ys), "iki çubuk grafiği, her yıla bir çubuk")
    kontrol("yaklaşık" in yillik and "yılbaşından bu yana" in yillik, "yıllık sayfada yöntem ve kısmi yıl notu")
    kontrol("2026 seyri" in yil and "<polyline" in yil, "yıl sayfasında grafik")
    kontrol("MetalCharts geçmiş verisi" in ay and "kısmidir" in ay, "arşiv ayında kaynak ve kısmi ay notu")
    for yol in ("gecmis/yillik/", "gecmis/2026/", "gecmis/2025/", f"gecmis/{ilk_ay}/"):
        kontrol(f"https://gunlukgumus.com/{yol}<" in harita, f"site haritasında {yol}")
    # Karışık ay (arşiv + botun kaydı) satırlarında † işareti
    ilk_kendi = min(gecmis)[:7]
    karisik = (cikti / "gecmis" / ilk_kendi / "index.html").read_text(encoding="utf-8")
    kontrol("† Günlük kapanış" in karisik and karisik.count('aria-label="günlük kapanış"') > 0,
            "karışık ayda arşiv satırları işaretli")
    # Model ya da şirket adı yok
    for metin in (merkez, yillik, yil, ay):
        kontrol(not re.search(r"Claude|Anthropic|Opus", metin), "geçmiş sayfalarında model/şirket adı yok")
    # Öteki sayfalar arşivden etkilenmez (ör. 1 ons sayfası ve ana sayfa yalnız botun kayıtlarını kullanır)
with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
    sayfa.uret(Path(d1), gecmis, simdi, euro=euro, arsiv=ornek_arsiv)
    sayfa.uret(Path(d2), gecmis, simdi, euro=euro, arsiv={})
    for yol in ("index.html", "hesap/1-ons-gumus-kac-tl/index.html", "hesap/altin-gumus-orani/index.html"):
        a = (Path(d1) / yol).read_text(encoding="utf-8")
        b_ = (Path(d2) / yol).read_text(encoding="utf-8")
        kontrol(a == b_, f"{yol} arşivden etkilenmez")
    kontrol(not (Path(d2) / "gecmis" / "2025").exists(), "arşiv yokken 2025 sayfası yok")
    kontrol((Path(d2) / "gecmis" / "yillik" / "index.html").exists(), "arşiv yokken de yıllık sayfa var (USGS)")

# ---- Çubuk grafiği eksen yazıları üst üste binmez
c = __import__("dar_sayfalar")._cubuk([(y, 1.0 + y - 2009) for y in range(2009, 2027)], bot.tr_sayi)
etiketli = [x["yil"] for x in c["cubuklar"] if x["etiket"]]
kontrol(etiketli == [2009, 2015, 2020, 2026], "eksende 2009, 2015, 2020, 2026")
kontrol(sum(1 for x in c["cubuklar"] if x["deger"]) == 2, "değer yazısı ilk ve son (en yüksek = son)")

print(f"\ntest_arsiv: {GECEN} sınama geçti")
