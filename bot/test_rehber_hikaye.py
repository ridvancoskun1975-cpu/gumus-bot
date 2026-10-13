"""bot/rehber_hikaye.py → kareleri_planla() sınamaları (tarayıcısız; öğe yükseklikleri sahte).

Çalıştırma: python bot/test_rehber_hikaye.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rehber_hikaye as rh  # noqa: E402

KARE = 100            # bir karenin sahte yüksekliği
BOY = {"bas": 20, "devam": 6, "buyuk": 25, "formul": 15, "satir": 10, "madde": 20, "not": 8}
SAYFA_ARASI = 10      # aynı karede ikinci sayfanın başlığı öncesi boşluk


def sigar_mi(ogeler):
    toplam = sum(BOY[o["tip"]] for o in ogeler)
    toplam += SAYFA_ARASI * sum(1 for i, o in enumerate(ogeler) if i and o["tip"] in ("bas", "devam"))
    return toplam <= KARE


def bolum(*sayfalar):
    return {"sayfalar": list(sayfalar)}


def sayfa(baslik, maddeler=0, satirlar=0, buyuk=False):
    s = {"baslik": baslik, "maddeler": [f"{baslik} m{i + 1}" for i in range(maddeler)]}
    if satirlar:
        s["tablo"] = [(f"{baslik} e{i + 1}", "1") for i in range(satirlar)]
    if buyuk:
        s["buyuk"], s["buyuk_alt"] = "999", "alt"
    return s


def planla(b):
    return rh.kareleri_planla(rh.sayfalari_cikar(b), sigar_mi)


def icerik(kareler):
    """Kareler boyunca devam satırları hariç öğelerin sırası (hiçbir şey kaybolmamalı, sıra bozulmamalı)."""
    return [(o["tip"], o.get("metin") or o.get("etiket") or o.get("baslik")) for k in kareler for o in k
            if o["tip"] != "devam"]


def beklenen(b):
    return [(o["tip"], o.get("metin") or o.get("etiket") or o.get("baslik"))
            for s in rh.sayfalari_cikar(b) for u in s["birimler"] for o in u]


def kontrol(ad, b, kare_sayisi=None, ek=None):
    kareler = planla(b)
    hatalar = []
    if icerik(kareler) != beklenen(b):
        hatalar.append("öğeler kayıp ya da sırası bozuk")
    for i, k in enumerate(kareler):
        if not sigar_mi(k):
            hatalar.append(f"kare {i + 2} taşıyor")
        if k[-1]["tip"] == "bas":
            hatalar.append(f"kare {i + 2} başlıkla bitiyor")
        if k[0]["tip"] not in ("bas", "devam"):
            hatalar.append(f"kare {i + 2} başlıksız başlıyor")
    if kare_sayisi is not None and len(kareler) != kare_sayisi:
        hatalar.append(f"kare sayısı {len(kareler)}, beklenen {kare_sayisi}")
    if ek:
        hatalar += ek(kareler)
    print(("TAMAM " if not hatalar else "HATA  ") + ad + ("" if not hatalar else ": " + "; ".join(hatalar)))
    return not hatalar


def tipler(k):
    return [o["tip"] for o in k]


def main():
    sonuc = []
    # 1) Her sayfa bir kareye sığıyor, ama iki sayfa birlikte sığmıyor: sayfa başına 1 kare
    sonuc.append(kontrol("olağan bölüm: sayfa başına bir kare",
                         bolum(sayfa("A", 3), sayfa("B", 3), sayfa("C", 3)), 3))
    # 2) Kısa sayfalar aynı karede birleşir (kare sayısı azalır): A+B bir karede (40+10+40), C sığmaz
    sonuc.append(kontrol("kısa sayfalar birleşir",
                         bolum(sayfa("A", 1), sayfa("B", 1), sayfa("C", 1)), 2,
                         lambda ks: [] if tipler(ks[0]) == ["bas", "madde", "bas", "madde"] else ["birleşmedi"]))
    # 3) Uzun sayfa bölünür, devam karesi "(devam)" ile başlar (kare sayısı artar)
    sonuc.append(kontrol("uzun sayfa bölünür", bolum(sayfa("A", 9)), 3,
                         lambda ks: [] if all(k[0]["tip"] == "devam" for k in ks[1:]) else ["devam satırı yok"]))
    # 4) Dengeleme: büyük sayı + 3 madde (55+60=... sığmaz) → [bas+büyük+m1] [devam+m2+m3], tek madde kalmaz
    sonuc.append(kontrol("bölünen sayfa dengelenir",
                         {"sayfalar": [{"baslik": "A", "buyuk": "999", "buyuk_alt": "x",
                                        "maddeler": ["m1", "m2", "m3"]}]}, 2,
                         lambda ks: [] if [tipler(k) for k in ks] == [["bas", "buyuk", "madde"],
                                                                     ["devam", "madde", "madde"]]
                         else [f"dağılım {[tipler(k) for k in ks]}"]))
    # 5) Başlık karenin dibinde yalnız kalmaz: A dolu bir kareyi bitirir, B ayrı karede başlar
    sonuc.append(kontrol("başlık yalnız kalmaz", bolum(sayfa("A", 3, satirlar=1), sayfa("B", 2)), 2))
    # 6) Bölünen sayfanın son parçasına sonraki kısa sayfa bütünüyle sığarsa aynı karede devam eder
    sonuc.append(kontrol("bölünmüş sayfanın kalan boşluğuna kısa sayfa sığar",
                         bolum(sayfa("A", 5), sayfa("B", satirlar=1)), 2))
    # 7) Tablo + madde + kaynak notu sırası korunur
    b = {"sayfalar": [{"baslik": "A", "tablo": [("e1", "1"), ("e2", "2")], "maddeler": ["m1"], "kaynak": "k"}]}
    sonuc.append(kontrol("tablo, madde, not sırası", b, 1,
                         lambda ks: [] if tipler(ks[0]) == ["bas", "satir", "satir", "madde", "not"] else ["sıra"]))
    # 8) Gerçek bölümler: hiçbir öğe kaybolmaz (sahte yüksekliklerle)
    import bilgi
    for no, gb in enumerate(bilgi.BOLUMLER, 1):
        sonuc.append(kontrol(f"bölüm {no} ({gb['baslik']})", gb))
    print(f"\n{sum(sonuc)}/{len(sonuc)} sınama geçti")
    sys.exit(0 if all(sonuc) else 1)


if __name__ == "__main__":
    main()
