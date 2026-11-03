"""Geçmiş fiyat arşivi: yıl yıl ve botun kayıtlarından önceki aylar (gunlukgumus.com/gecmis/).

Rıdvan, 3 Kasım 2026: "Kullanıcılar geçmiş bilgilerle erişmek istiyor. Ay ay yıl yil" · "Web sayfasından olabilir"
→ seçenekler arasından "1 ve 2", "Abonelik bitince elinizde en az geçmiş 3 ay kalacak", "Metalcharts a email gerek
yok şimdilik. Abonelik bitince tekrar değerlendirelim".

1) Yıl yıl (YILLIK_ONS, YILLIK_KUR): ABD Jeolojik Araştırma Kurumu'nun (USGS) yıllık ortalama gümüş fiyatı
   (kamu malı) × ECB yıllık ortalama dolar/TL → yaklaşık yıllık ortalama gram (₺). Geçmiş yıllar değişmediği için
   sabit; içinde bulunulan yıl (USGS rakamı yokken) günlük verilerin yılbaşından bu yana ortalamasıdır.
2) Son ~12 ay ay ay: MetalCharts Starter aboneliğinin 1 yıllık günlük geçmişi (kapanış) × o günün ECB kuru.
   Yalnız botun kendi kayıtlarından (13 Ekim 2026) önceki günler için. Bir kez alınır (`doldur`), özel gumus-kayit
   deposunda `arsiv/metalcharts-gunluk.json` olarak durur; site her üretimde oradan okur (`indir`, yedek.py
   birlestir adımında). Herkese açık bot deposuna ve iş akışı günlüklerine fiyat yazılmaz.
   MetalCharts API şartları (19 Eylül 2026): verinin kullanıcılara gösterilmesine ve ürünün işlemesi için makul süre
   önbellekte tutulmasına izin var; toplu indirip başka yerde yeniden dağıtmak yasak. Abonelik Ocak 2027'de
   bitince Rıdvan yeniden değerlendirecek (11 Ocak hatırlatması). Kapatmak için ARSIV_ACIK = False: sayfalar
   yalnız botun kendi kayıtlarıyla üretilir.

Kullanım:
  python bot/arsiv.py doldur   → MetalCharts 1Y geçmiş + ECB kuru → gumus-kayit/arsiv/metalcharts-gunluk.json
                                 (METALCHARTS_KEY, KAYIT_PAT; gecmis-kontrol.yml → işlem: arsiv)
  python bot/arsiv.py indir    → özel depodaki arşivi veri/arsiv.json'a indirir (KAYIT_PAT)
"""
import base64
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

KOK = Path(__file__).resolve().parent.parent
YEREL = KOK / "veri" / "arsiv.json"
HEDEF = "arsiv/metalcharts-gunluk.json"
ARSIV_ACIK = True
KAYNAK = "metalcharts-gecmis"
ONS_GRAM = 31.1035

# USGS yıllık ortalama gümüş fiyatı, dolar/ons (Engelhard külçe kotasyonları; USGS'nin kaynağı Platts Metals Week).
# Her yıl için USGS'nin bulunabilen en son (kesinleşmiş) rakamı; okuma 3 Kasım 2026:
#   2009: Mineral Industry Surveys, Silver in May 2010, Tablo 2 (Engelhard 2009 ortalaması)
#   2010–2013: Minerals Yearbook 2013, Silver, Tablo 1 (indexmundi aynasından okundu; LBMA yıllık ortalamalarıyla
#              tutarlı: 20,19 · 35,12 · 31,15 · 23,79)
#   2014–2017: Mineral Commodity Summaries 2019, Silver
#   2018: Mineral Industry Surveys, Silver in December 2019, Tablo 2 (Engelhard 2018 ortalaması; MCS 2019'daki
#         15,30 tahminiydi)
#   2019–2020: Mineral Commodity Summaries 2024, Silver
#   2021–2024: Mineral Commodity Summaries 2026, Silver
#   2025: Mineral Industry Surveys, Silver in December 2025 ("The full year 2025 average price was $40.08")
# 2005–2008: 2008'in kesinleşmiş USGS rakamı bulunamadığı için (MCS 2009'daki 15,85 yıl bitmeden yapılmış tahmin)
# tablo 2009'dan başlar; bulunursa eklenebilir (2005 7,34 · 2006 11,61 · 2007 13,38; Minerals Yearbook 2007).
YILLIK_ONS = {
    2009: 14.69, 2010: 20.20, 2011: 35.26, 2012: 31.21, 2013: 23.80, 2014: 19.09, 2015: 15.72, 2016: 17.20,
    2017: 17.07, 2018: 15.75, 2019: 16.24, 2020: 20.58, 2021: 25.23, 2022: 21.88, 2023: 23.54, 2024: 28.37,
    2025: 40.08,
}
# ECB USD/TRY referans kurlarının (EUR çaprazı, Frankfurter) yıllık ortalaması: o yılın bütün ECB iş günleri
# (255–258 gün). 3 Kasım 2026'da hesaplandı; geçmiş yıllar değişmez.
YILLIK_KUR = {
    2009: 1.5546, 2010: 1.5076, 2011: 1.6815, 2012: 1.8011, 2013: 1.9065, 2014: 2.1895, 2015: 2.7287,
    2016: 3.0240, 2017: 3.6481, 2018: 4.8549, 2019: 5.6806, 2020: 7.0321, 2021: 8.9233, 2022: 16.6119,
    2023: 23.8197, 2024: 32.8700, 2025: 39.5700,
}
YIL_EN_AZ_GUN = 20   # USGS rakamı olmayan yılın satırı için en az günlük veri
AY_EN_AZ_GUN = 5     # arşivin ilk ayı bundan az günse sayfalara girmez
USGS_KAYNAK_URL = ("https://www.usgs.gov/centers/national-minerals-information-center/"
                   "silver-statistics-and-information")


# ---- Okuma ve birleştirme (site üretimi)

def oku():
    """veri/arsiv.json → {"YYYY-AA-GG": kayıt}. Kapalıysa, dosya yoksa ya da bozuksa boş sözlük."""
    if not ARSIV_ACIK:
        return {}
    try:
        veri = json.loads(YEREL.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}
    if not isinstance(veri, dict):
        return {}
    temiz = {}
    for g, k in veri.items():
        try:
            date.fromisoformat(g)
            if all(float(k[a]) > 0 for a in ("gumus", "dolar", "gram")):
                temiz[g] = k
        except (KeyError, TypeError, ValueError):
            continue
    return temiz


def birlesik(gecmis, arsiv):
    """Arşivdeki günler (yalnız botun ilk kaydından önce) + botun kayıtları; tarihe göre sıralı sözlük.
    Botun kayıtları hiçbir zaman arşivle değişmez."""
    if not gecmis:
        return dict(sorted((arsiv or {}).items()))
    ilk = min(gecmis)
    once = {g: {**k, "kaynak": KAYNAK} for g, k in (arsiv or {}).items() if g < ilk}
    # Arşivin ilk ayı birkaç günse (MetalCharts 1 yıllık geçmişi ayın sonundan başlayabilir; 3 Kasım 2026'da
    # 31 Ekim 2025'ten başladı) o ay sayfası tek satırlık kalmasın diye atılır.
    if once:
        ilk_ay = min(once)[:7]
        if sum(1 for g in once if g.startswith(ilk_ay)) < AY_EN_AZ_GUN:
            once = {g: k for g, k in once.items() if not g.startswith(ilk_ay)}
    return dict(sorted({**once, **gecmis}.items()))


def yillik_satirlar(gunluk, bugun):
    """Yıllara göre ortalama: [{yil, ons, kur, gram, deg, kaynak, kismi, gun}] (eskiden yeniye).
    gunluk: birlesik() çıktısı. USGS rakamı olan yıllar sabit değerlerle; olmayan yıl(lar) günlük verilerle."""
    satirlar = []
    for yil in sorted(YILLIK_ONS):
        ons, kur = YILLIK_ONS[yil], YILLIK_KUR.get(yil)
        if kur is None:
            continue
        satirlar.append({"yil": yil, "ons": ons, "kur": kur, "gram": ons * kur / ONS_GRAM, "kaynak": "usgs",
                         "kismi": False, "gun": None})
    son_usgs = max(YILLIK_ONS)
    yillar = sorted({int(g[:4]) for g in gunluk if int(g[:4]) > son_usgs})
    for yil in yillar:
        kk = [k for g, k in gunluk.items() if g.startswith(f"{yil}-")]
        if len(kk) < YIL_EN_AZ_GUN:
            continue
        n = len(kk)
        satirlar.append({"yil": yil, "ons": sum(k["gumus"] for k in kk) / n, "kur": sum(k["dolar"] for k in kk) / n,
                         "gram": sum(k["gram"] for k in kk) / n, "kaynak": "gunluk",
                         "kismi": yil == bugun.year, "gun": n})
    for i, s in enumerate(satirlar):
        s["deg_once"] = satirlar[i - 1]["gram"] if i > 0 and satirlar[i - 1]["yil"] == s["yil"] - 1 else None
        s["ons_once"] = satirlar[i - 1]["ons"] if i > 0 and satirlar[i - 1]["yil"] == s["yil"] - 1 else None
    return satirlar


# ---- Özel depo (gumus-kayit)

def _github(yontem, yol, **kw):
    import yedek
    return yedek._github(yontem, yol, **kw)


def uzak_oku():
    """(kayıtlar, sha); yoksa ({}, None). Hata yedek.YedekHatasi fırlatır."""
    import yedek
    r = _github("GET", f"/contents/{HEDEF}")
    if r.status_code == 404:
        return {}, None
    if r.status_code >= 400:
        raise yedek.YedekHatasi(f"arşiv okunamadı ({r.status_code})")
    veri = r.json()
    try:
        if veri.get("encoding") == "base64" and veri.get("content"):
            metin = base64.b64decode(veri["content"]).decode("utf-8")
        else:   # 1 MB üstü: ham içerik ayrıca
            import os
            import requests
            ham = requests.get(veri["download_url"], timeout=30,
                               headers={"Authorization": f"Bearer {os.environ['KAYIT_PAT'].strip()}"})
            if ham.status_code >= 400:
                raise yedek.YedekHatasi(f"arşiv okunamadı ({ham.status_code})")
            metin = ham.text
        kayitlar = json.loads(metin)
    except (ValueError, KeyError) as e:
        raise yedek.YedekHatasi(f"arşiv okunamadı ({type(e).__name__})")
    if not isinstance(kayitlar, dict):
        raise yedek.YedekHatasi("arşiv dosyası beklenen biçimde değil")
    return kayitlar, veri.get("sha")


def _ozet(k):
    return f"{len(k)} gün, {min(k)} – {max(k)}" if k else "0 gün"


def indir():
    """Özel depodaki arşivi veri/arsiv.json'a yazar. Kapalıysa ya da yoksa dosya yazılmaz (sayfalar kendi kayıtlarla)."""
    if not ARSIV_ACIK:
        print("Geçmiş arşivi kapalı (arsiv.ARSIV_ACIK = False); sayfalar yalnız botun kayıtlarıyla.")
        return
    kayitlar, _ = uzak_oku()
    if not kayitlar:
        print("Geçmiş arşivi henüz yok (gecmis-kontrol.yml → işlem: arsiv ile doldurulur).")
        return
    YEREL.parent.mkdir(parents=True, exist_ok=True)
    YEREL.write_text(json.dumps(kayitlar, ensure_ascii=False), encoding="utf-8")
    print(f"Geçmiş arşivi indirildi ({_ozet(kayitlar)}).")


def gunluk_kayitlar(metal, ecb, sinir=None):
    """MetalCharts geçmişi {"XAG": {gün: kapanış}, "XAU": {...}} + ECB {gün: USD/TRY} → {"YYYY-AA-GG": kayıt}.
    Yalnız hafta içi; kur o gün ya da öncesindeki son ECB kuru (bot/yorum.py → seri_kur ile aynı kural).
    sinir verilirse yalnız ondan önceki günler."""
    ecb_gunler = sorted(ecb)
    sonuc = {}
    for g, gumus in sorted(metal.get("XAG", {}).items()):
        if g.weekday() >= 5 or (sinir and g >= sinir) or not gumus or gumus <= 0:
            continue
        onceki = [d for d in ecb_gunler if d <= g]
        if not onceki or (g - onceki[-1]).days > 7:
            continue
        kur_gunu = onceki[-1]
        dolar = ecb[kur_gunu]
        altin = metal.get("XAU", {}).get(g)
        sonuc[g.isoformat()] = {"gumus": round(gumus, 4), "altin": round(altin, 2) if altin else None,
                                "dolar": dolar, "kur_tarihi": kur_gunu.isoformat(),
                                "gram": round(gumus * dolar / ONS_GRAM, 4)}
    return sonuc


def _ecb_aralik(baslangic):
    """baslangic'tan bugüne ECB USD/TRY: {date: kur}. Bot'la aynı uç (Frankfurter, yalnız ECB)."""
    import requests
    import main as bot
    son_hata = None
    for deneme in range(3):
        try:
            r = requests.get(bot.KUR_URL, timeout=120, headers={"User-Agent": bot.TARAYICI, "Accept": "application/json"},
                             params={"base": "USD", "quotes": "TRY", "from": baslangic.isoformat()})
            r.raise_for_status()
            kur = {date.fromisoformat(x["date"]): float(x["rate"]) for x in r.json() if x.get("quote") == "TRY"}
            if len(kur) < 100 or not all(1 < k < 1000 for k in kur.values()):
                raise ValueError(f"beklenmeyen kur serisi ({len(kur)} gün)")
            return kur
        except (requests.RequestException, ValueError, KeyError, TypeError) as e:
            son_hata = e
            bot._bekle(deneme)
    raise RuntimeError(f"ECB kur geçmişi alınamadı: {son_hata}")


def doldur():
    """MetalCharts 1 yıllık geçmişi ile arşivi doldurur (yalnız botun ilk kaydından önceki günler). Var olan günler
    korunur, arşiv hiç küçülmez. Günlüğe fiyat yazılmaz (herkese açık depo)."""
    import main as bot
    import yedek
    metal = bot.metal_gecmisi()
    if not metal or not metal.get("XAG"):
        print("::error::MetalCharts geçmişi gelmedi (abonelik bitmiş ya da hata); arşiv değişmedi.")
        sys.exit(1)
    try:
        kendi, _ = yedek.yedegi_al()
    except yedek.YedekHatasi as e:
        print(f"::error::Botun kayıtları okunamadı ({e}); hangi günlerin arşive gireceği belirlenemedi.")
        sys.exit(1)
    sinir = date.fromisoformat(min(kendi)) if kendi else None
    ecb = _ecb_aralik(min(metal["XAG"]) - timedelta(days=10))
    yeni = gunluk_kayitlar(metal, ecb, sinir)
    if not yeni:
        print("::error::Arşive girecek gün çıkmadı; arşiv değişmedi.")
        sys.exit(1)
    for _ in range(2):
        eski, sha = uzak_oku()
        sonuc = dict(sorted({**yeni, **eski}.items()))   # var olan gün korunur
        if sonuc == eski:
            print(f"Arşiv zaten güncel ({_ozet(eski)}).")
            return
        govde = {"message": f"Geçmiş arşivi: MetalCharts günlük kapanış ({min(sonuc)} – {max(sonuc)})",
                 "content": base64.b64encode(json.dumps(sonuc, ensure_ascii=False, indent=0).encode()).decode()}
        if sha:
            govde["sha"] = sha
        r = _github("PUT", f"/contents/{HEDEF}", json=govde)
        if r.status_code in (409, 422):
            continue
        if r.status_code >= 400:
            print(f"::error::Arşiv yazılamadı ({r.status_code}).")
            sys.exit(1)
        print(f"Geçmiş arşivi yazıldı: {yedek.DEPO}/{HEDEF} ({_ozet(sonuc)}; MetalCharts {_ozet({g.isoformat(): 1 for g in metal['XAG']})}"
              f"; botun ilk kaydı {sinir}).")
        return
    print("::error::Arşiv yazılamadı (aynı anda başka bir yazım).")
    sys.exit(1)


def ornek(gecmis):
    """Yerel önizleme için örnek arşiv: botun örnek kayıtlarından önceki ~10 ay (gerçek veri değildir)."""
    import math
    ilk = date.fromisoformat(min(gecmis))
    gun, i, kayit = ilk - timedelta(days=1), 0, {}
    while gun >= ilk - timedelta(days=310):
        if gun.weekday() < 5:
            gumus = 62.0 - 0.06 * i + 9 * math.exp(-((i - 190) / 18) ** 2) + 1.4 * math.sin(i / 4.3)
            dolar = 48.9 - 0.035 * i
            kayit[gun.isoformat()] = {"gumus": gumus, "altin": gumus * 70, "dolar": dolar,
                                      "kur_tarihi": gun.isoformat(), "gram": gumus * dolar / ONS_GRAM}
            i += 1
        gun -= timedelta(days=1)
    return kayit


def main():
    komut = sys.argv[1] if len(sys.argv) > 1 else ""
    if komut == "doldur":
        doldur()
    elif komut == "indir":
        import yedek
        try:
            indir()
        except yedek.YedekHatasi as e:
            print(f"::warning::Geçmiş arşivi indirilemedi ({e}); sayfalar yalnız botun kayıtlarıyla.")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
