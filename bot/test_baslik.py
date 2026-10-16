"""Günlük başlık ve özel gün kurallarının sınaması: python bot/test_baslik.py

Paket gerektirmez. Her durum, bugünden geriye doğru iş günlerine dizilen örnek kayıtlarla kurulur.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import baslik  # noqa: E402


def seri_kur(gun, degerler):
    """degerler (eskiden yeniye) bugünden önceki iş günlerine dizilir."""
    seri, g = {}, gun
    for v in reversed(degerler):
        g = baslik.onceki_is_gunu(g)
        seri[g] = v
    return seri


def bak(gun, degerler, bugun):
    return baslik.degerlendir(seri_kur(gun, degerler), gun, bugun)


SALI = date(2026, 11, 17)
PAZARTESI = date(2026, 11, 16)
DUZ = [95.0, 95.4, 95.1, 95.3, 95.2]
sayac = 0


def esit(ad, gercek, beklenen):
    global sayac
    sayac += 1
    if gercek != beklenen:
        raise AssertionError(f"{ad}: beklenen {beklenen!r}, gelen {gercek!r}")


def metin(s):
    return s["baslik"] and s["baslik"]["metin"]


# ---- kayıt yok ya da eski: hiçbir şey çıkmaz
esit("kayıt yok", baslik.degerlendir({}, SALI, 95.0), {"ozel": None, "baslik": None, "not": None})
esit("kayıt eski", baslik.degerlendir({SALI - timedelta(days=9): 90.0}, SALI, 95.0)["baslik"], None)

# ---- sakin gün: başlık yok, not yok
s = bak(SALI, [96.0, 95.0, 95.6, 95.2], 95.4)
esit("sakin gün", (s["ozel"], s["baslik"], s["not"]), (None, None, None))

# ---- seri
s = bak(SALI, [97.0, 96.9, 95.0, 95.3, 95.6], 95.9)
esit("3 gün yükseliş", metin(s), "Üst üste 3. gün yükseliş")
esit("seri yönü", s["baslik"]["yon"], "artis")
s = bak(SALI, [93.0, 93.2, 96.0, 95.7, 95.3, 95.0], 94.6)
esit("4 gün düşüş", metin(s), "Üst üste 4. gün düşüş")
s = bak(SALI, [97.0, 96.9, 95.0, 95.3], 95.6)
esit("2 gün yetmez", metin(s), None)
# arada kayıtsız iş günü seriyi keser
k = seri_kur(SALI, [97.0, 96.9, 95.0, 95.3, 95.6])
del k[baslik.onceki_is_gunu(baslik.onceki_is_gunu(SALI))]
esit("eksik gün seriyi keser", baslik.degerlendir(k, SALI, 95.9)["baslik"], None)
# görselde aynı yazılan değer (2 ondalık) değişim sayılmaz
s = bak(SALI, [97.0, 96.9, 95.0, 95.3, 95.6], 95.601)
esit("değişim yok", metin(s), None)

# ---- dönüş
s = bak(SALI, [97.0, 94.0, 94.5, 95.0, 95.5], 95.2)
esit("yükseliş sona erdi", metin(s), "3 günlük yükseliş sona erdi")
esit("dönüş yönü", s["baslik"]["yon"], "dusus")
s = bak(SALI, [93.0, 96.5, 96.0, 95.5, 95.0, 94.5], 94.8)
esit("düşüş sona erdi", metin(s), "4 günlük düşüş sona erdi")

# ---- hafta başı
s = bak(PAZARTESI, [96.0, 95.0, 95.6, 95.2], 95.4)
esit("haftaya yükselişle", metin(s), "Haftaya yükselişle başladı")
s = bak(PAZARTESI, [94.0, 95.0, 95.6, 95.2], 95.0)
esit("haftaya düşüşle", metin(s), "Haftaya düşüşle başladı")
s = bak(PAZARTESI, [97.0, 96.9, 95.0, 95.3, 95.6], 95.9)
esit("pazartesi de seri önce gelir", metin(s), "Üst üste 3. gün yükseliş")

# ---- pencere: kayıtlar pencereyi kapsamalı
s = bak(SALI, [95.0, 95.4, 95.1, 95.3], 96.0)            # 4 iş günü: 1 haftayı kapsamıyor
esit("kayıt kısa, pencere yok", metin(s), None)
s = bak(SALI, [99.0, 95.0, 95.4, 95.1, 95.3, 95.2], 96.0)  # 6 iş günü: 9 Kasım'dan beri
esit("1 haftanın en yükseği", metin(s), "Son 1 haftanın en yükseği")
s = bak(SALI, [90.0, 95.0, 95.4, 95.1, 95.3, 95.6], 94.8)
esit("1 haftanın en düşüğü", metin(s), "Son 1 haftanın en düşüğü")
esit("düşük yönü", s["baslik"]["yon"], "dusus")
s = bak(SALI, [99.0] + DUZ * 3, 96.0)                      # 16 iş günü ≈ 3 hafta
esit("3 haftanın en yükseği", metin(s), "Son 3 haftanın en yükseği")
esit("3 hafta özel değil", s["ozel"], None)
esit("not var", s["not"].startswith("Başlık botun günlük kayıtlarına göredir"), True)
# eşit değer "en yüksek" sayılmaz
s = bak(SALI, [99.0, 95.0, 96.0, 95.1, 95.3, 95.2], 96.0)
esit("eşitlik en yüksek değil", metin(s), None)
# aynı pencere dün de geçerliyse ve seri sürüyorsa seri yazılır
s = bak(SALI, [99.0, 95.0, 95.4, 95.1, 95.3, 95.9, 96.2, 96.5], 96.9)
esit("pencere yinelenmez, seri yazılır", metin(s), "Üst üste 5. gün yükseliş")

# ---- sabah Reels'i (Rıdvan, 16 Ekim 2026 23:00): bugünü tamamlanmış gün sayan başlıklar çıkmaz
def bak_sabah(gun, degerler, bugun):
    return baslik.degerlendir(seri_kur(gun, degerler), gun, bugun, sabah=True)


esit("sabah seri yok", metin(bak_sabah(SALI, [97.0, 96.9, 95.0, 95.3, 95.6], 95.9)), None)
esit("sabah dönüş yok", metin(bak_sabah(SALI, [97.0, 94.0, 94.5, 95.0, 95.5], 95.2)), None)
esit("sabah haftaya başlangıç var", metin(bak_sabah(PAZARTESI, [96.0, 95.0, 95.6, 95.2], 95.4)),
     "Haftaya yükselişle başladı")
esit("sabah pazartesi seri yerine hafta başı", metin(bak_sabah(PAZARTESI, [97.0, 96.9, 95.0, 95.3, 95.6], 95.9)),
     "Haftaya yükselişle başladı")
esit("sabah pencere var", metin(bak_sabah(SALI, [99.0, 95.0, 95.4, 95.1, 95.3, 95.2], 96.0)), "Son 1 haftanın en yükseği")
esit("sabah seri yerine pencere", metin(bak_sabah(SALI, [99.0, 95.0, 95.4, 95.1, 95.3, 95.9, 96.2, 96.5], 96.9)),
     "Son 1 haftanın en yükseği")
esit("sabah özel gün aynı", bak_sabah(SALI, [99.0] + DUZ * 5, 96.0)["ozel"]["tur"], "zirve")
esit("akşam değişmedi", metin(bak(SALI, [97.0, 96.9, 95.0, 95.3, 95.6], 95.9)), "Üst üste 3. gün yükseliş")

# ---- özel: en az 1 aylık en yüksek
uzun = [99.0] + DUZ * 5                                     # 26 iş günü ≈ 5 hafta
s = bak(SALI, uzun, 96.0)
esit("1 ayın en yükseği özel", s["ozel"]["tur"], "zirve")
esit("zirve etiketi", s["ozel"]["etiket"], "SON 1 AYIN EN YÜKSEĞİ")
esit("zirve manşeti", s["ozel"]["manset"], "Gram gümüş son 1 ayın en yükseğinde")
esit("zirve alt", s["ozel"]["alt"].startswith("Önceki en yüksek: 95,40 ₺ ("), True)
esit("zirve çizgisi", s["ozel"]["cizgi"], 95.4)
esit("grafik bugünle biter", s["ozel"]["grafik"][-1], (SALI, 96.0))
# ertesi gün yine en yüksek: özel yinelenmez
s = bak(SALI, uzun + [96.0], 96.3)
esit("zirve ertesi gün yinelenmez", s["ozel"], None)
esit("ertesi gün başlık", metin(s), "Son 1 ayın en yükseği")
# 6 iş günü sonra yeniden: özel olur
s = bak(SALI, uzun + [96.0, 95.5, 95.4, 95.6, 95.5, 95.3], 96.4)
esit("zirve 6 iş günü sonra yeniden", s["ozel"] and s["ozel"]["tur"], "zirve")
# pencere büyüdüyse bekleme aranmaz (1 ay → 2 ay)
iki_ay = [97.0] + DUZ * 4 + [96.5] + DUZ * 5                # 97 en başta; 96,5 beş hafta önce
s = bak(SALI, iki_ay + [96.6], 96.8)                        # dün 1 ayın en yükseği, bugün de 1 ay
esit("aynı pencere yinelenmez", s["ozel"], None)
# en düşük özel olmaz, başlık olur
s = bak(SALI, [90.0] + DUZ * 5, 94.0)
esit("1 ayın en düşüğü özel değil", s["ozel"], None)
esit("1 ayın en düşüğü başlık", metin(s), "Son 1 ayın en düşüğü")

# ---- özel: eşik
s = bak(SALI, [98.0, 98.5, 99.2], 100.4)
esit("eşik özel", s["ozel"]["tur"], "esik")
esit("eşik manşeti", s["ozel"]["manset"], "Gram gümüş 100 lirayı aştı")
esit("eşik değeri", s["ozel"]["esik"], 100)
esit("kısa kayıtta 'ilk kez' denmez", s["ozel"]["alt"], None)
s = bak(SALI, [94.0] + DUZ * 5 + [95.0], 100.4)
esit("uzun kayıtta ilk kez + en yüksek", s["ozel"]["alt"], "Günlük kayıtlarımızda ilk kez · Son 1 ayın en yükseği")
s = bak(SALI, [94.0] + DUZ * 5 + [99.2], 100.4)            # dün de 1 ayın en yükseğiydi
esit("dün de en yüksekse yalnız ilk kez", s["ozel"]["alt"], "Günlük kayıtlarımızda ilk kez")
s = bak(SALI, [98.0, 98.5, 99.2], 100.0)
esit("tam eşikte aşılmış sayılmaz", s["ozel"], None)
s = bak(SALI, [98.0, 98.5, 100.0], 100.4)
esit("tam eşikten sonra aşılır", s["ozel"]["tur"], "esik")
s = bak(SALI, [98.0, 98.5, 99.2], 111.0)
esit("iki eşik birden: üstteki", s["ozel"]["esik"], 110)
s = bak(SALI, [1008.0, 1009.0], 1010.5)
esit("binlik yazım", s["ozel"]["manset"], "Gram gümüş 1.010 lirayı aştı")
# eşik daha önce aşılmışsa özel değil; son 5 kayıt altındaysa sakin başlık
s = bak(SALI, [101.0, 99.0, 98.0, 98.5, 99.1, 99.2], 100.4)
esit("yeniden aşma özel değil", s["ozel"], None)
esit("yeniden aşma başlığı", metin(s), "Yeniden 100 liranın üzerinde")
s = bak(SALI, [101.0, 98.5, 99.2], 100.4)
esit("gidip gelme başlık olmaz", metin(s), None)
# aşağı geçiş
s = bak(SALI, [101.0, 100.6, 100.9, 100.2, 100.3], 99.6)
esit("altına indi", metin(s), "100 liranın altına indi")
esit("altına indi yönü", s["baslik"]["yon"], "dusus")
s = bak(SALI, [99.5, 100.6, 100.9, 100.2, 100.3], 99.6)
esit("aşağı gidip gelme başlık olmaz", bool(s["baslik"] and s["baslik"]["kural"] == "esik"), False)

# ---- yardımcılar
esit("önceki iş günü (pazartesi → cuma)", baslik.onceki_is_gunu(PAZARTESI), date(2026, 11, 13))
esit("büyük harf", baslik.tr_buyuk("Son 1 yılın en yükseği"), "SON 1 YILIN EN YÜKSEĞİ")
esit("seri_say", baslik.seri_say(seri_kur(SALI, [1.0, 2.0, 3.0]), SALI, 4.0), ("artis", 3))

print(f"Tamam: {sayac} sınama geçti.")
